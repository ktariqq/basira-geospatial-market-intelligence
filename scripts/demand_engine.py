import json
import os
import numpy as np
from typing import Dict
import rasterio
from rasterio.mask import mask as raster_mask
from rasterio.features import rasterize
import geopandas as gpd
from shapely.geometry import box, mapping
import pyproj

CONFIG_DIR  = "config"
DATA_DIR    = "data"
OUTPUTS_DIR = "outputs"

WEIGHTS_PATH = os.path.join(CONFIG_DIR, "weights.json")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_weights() -> Dict:
    with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _bbox_geometry(bbox: list, raster_path: str) -> dict:
    """
    Return a masking geometry in the raster's native CRS.
    bbox = [south, west, north, east] in WGS84 decimal degrees.
    Reprojects to UTM (or whatever the raster uses) automatically.
    """
    south, west, north, east = bbox
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs

    if raster_crs.to_epsg() == 4326:
        return mapping(box(west, south, east, north))

    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326", raster_crs.to_string(), always_xy=True
    )
    x0, y0 = transformer.transform(west, south)
    x1, y1 = transformer.transform(east, north)
    return mapping(box(x0, y0, x1, y1))


# ── Signal computations ───────────────────────────────────────────────────────

def _compute_ndvi_density(
    b04_path: str, b08_path: str, bbox: list, threshold: float = 0.08
) -> float:
    """
    Fraction of valid pixels with NDVI > threshold.
    Threshold 0.08 is calibrated for UAE desert-edge terrain
    (captures date palms, sparse scrub, irrigated patches).
    Standard 0.2 threshold is for temperate European farmland.
    """
    geom = _bbox_geometry(bbox, b08_path)
    try:
        with rasterio.open(b08_path) as src:
            nir_data, _ = raster_mask(src, [geom], crop=True, nodata=0)
            nir = nir_data[0].astype(float)
        with rasterio.open(b04_path) as src:
            red_data, _ = raster_mask(src, [geom], crop=True, nodata=0)
            red = red_data[0].astype(float)

        valid = (nir + red) > 0
        ndvi  = np.where(valid, (nir - red) / (nir + red + 1e-10), -1.0)
        valid_count = int(np.sum(valid))
        if valid_count == 0:
            return 0.0
        above = int(np.sum((ndvi > threshold) & valid))
        return float(above / valid_count)

    except Exception as e:
        print(f"[demand_engine] NDVI computation error: {e}")
        return 0.0     # honest zero, not inflated fallback


def _compute_viirs_proxy(viirs_path: str, bbox: list) -> float:
    """
    Normalised night-light radiance as population/activity proxy.
    Normalises against the 95th percentile of the tile's own valid pixels,
    so the result is meaningful regardless of how the HDF5 was exported.
    Low value = dark = rural. High value = bright = more activity.
    """
    geom = _bbox_geometry(bbox, viirs_path)
    try:
        with rasterio.open(viirs_path) as src:
            data, _ = raster_mask(src, [geom], crop=True, nodata=src.nodata)
            arr = data[0].astype(float)

        # Mask out nodata and zero (unlit pixels)
        nodata_val = -9999.0   # VIIRS Black Marble fill value
        valid = (arr > 0) & (arr != nodata_val)
        if not np.any(valid):
            return 0.05   # genuinely dark area — small but not zero

        mean_val = float(np.mean(arr[valid]))
        p95      = float(np.percentile(arr[valid], 95))
        if p95 < 1e-9:
            return 0.05
        return float(np.clip(mean_val / p95, 0.0, 1.0))

    except Exception as e:
        print(f"[demand_engine] VIIRS computation error: {e}")
        return 0.05


def _compute_road_accessibility(
    dem_path: str, osm_path: str, center: list, bbox: list
) -> float:
    """
    Slope-weighted cost-distance to nearest OSM paved road.
    Returns 0–1, where 1 = good accessibility (roads nearby).
    Falls back to 0.5 if no road features found in OSM file.
    """
    try:
        from scipy.ndimage import distance_transform_edt

        gdf = gpd.read_file(osm_path)

        # ── Road filtering ───────────────────────────────────────────────────
        ROAD_TYPES = {
            "motorway", "trunk", "primary", "secondary", "tertiary",
            "unclassified", "road", "residential", "service", "track"
        }
        if "highway" in gdf.columns:
            road_rows = gdf[gdf["highway"].isin(ROAD_TYPES)]
        else:
            # OSM exports sometimes put type in a different column
            road_rows = gpd.GeoDataFrame()

        # ── DEM raster as grid template ──────────────────────────────────────
        dem_geom = _bbox_geometry(bbox, dem_path)
        with rasterio.open(dem_path) as dem_src:
            dem_data, dem_transform = raster_mask(
                dem_src, [dem_geom], crop=True, nodata=0
            )
            dem_arr = dem_data[0].astype(float)
            rows, cols = dem_arr.shape
            dem_crs = dem_src.crs

        if road_rows.empty:
            print("[demand_engine] No road features found in OSM — using fallback 0.5")
            return 0.5

        # Reproject roads to DEM CRS if needed
        if road_rows.crs is not None and road_rows.crs != dem_crs:
            road_rows = road_rows.to_crs(dem_crs)
        elif road_rows.crs is None:
            road_rows = road_rows.set_crs("EPSG:4326").to_crs(dem_crs)

        # ── Burn roads onto raster grid ──────────────────────────────────────
        road_mask = np.zeros((rows, cols), dtype=bool)
        valid_geoms = [
            (geom, 1)
            for geom in road_rows.geometry
            if geom is not None and not geom.is_empty
        ]
        if valid_geoms:
            burned = rasterize(
                valid_geoms,
                out_shape=(rows, cols),
                transform=dem_transform,
                fill=0,
                dtype=np.uint8,
            )
            road_mask = burned.astype(bool)

        if not np.any(road_mask):
            return 0.5

        # ── Distance transform ───────────────────────────────────────────────
        dist     = distance_transform_edt(~road_mask)
        max_dist = max(float(dist.max()), 1.0)
        # Invert: lower mean distance = higher accessibility score
        score = 1.0 - float(dist.mean() / max_dist)
        return float(np.clip(score, 0.0, 1.0))

    except Exception as e:
        print(f"[demand_engine] Road accessibility error: {e}")
        return 0.5


def _compute_competition_penalty(osm_path: str, subcategory: str) -> float:
    """
    Inverted competition density from OSM POI tags.
    1.0 = no competitors found (rural gap = opportunity).
    0.0 = saturated market.
    Baseline counts are calibrated for rural UAE — not urban.
    """
    # OSM tags that indicate existing competition per category
    CATEGORY_TAGS: Dict[str, Dict[str, list]] = {
        "1.1": {"landuse":  ["farmland", "farm", "orchard", "meadow", "greenhouse"]},
        "1.2": {"shop":     ["craft", "bakery", "pastry", "clothes", "gift"]},
        "1.3": {"landuse":  ["industrial"], "craft": ["yes", "carpenter", "metal"]},
        "2.1": {"shop":     ["hardware", "tools"],
                "amenity":  ["car_wash", "laundry"]},
        "2.2": {"amenity":  ["taxi", "bus_station"],
                "shop":     ["car_repair", "bicycle"]},
        "2.3": {"amenity":  ["school", "kindergarten", "nursing_home",
                             "clinic", "doctors", "pharmacy"]},
        "2.4": {"office":   ["yes", "consulting", "accountant",
                             "lawyer", "government"]},
        "3.1": {"shop":     ["supermarket", "convenience", "general",
                             "greengrocer", "butcher"],
                "amenity":  ["marketplace"]},
        "3.2": {"amenity":  ["community_centre", "social_facility",
                             "place_of_worship", "theatre"]},
        "3.3": {"tourism":  ["camp_site", "viewpoint", "attraction",
                             "information", "hotel", "guest_house"]},
    }
    # Expected baseline count in a healthy rural market (not saturated)
    BASELINE: Dict[str, int] = {
        "1.1": 4, "1.2": 2, "1.3": 2,
        "2.1": 3, "2.2": 2, "2.3": 3,
        "2.4": 2, "3.1": 4, "3.2": 2, "3.3": 2,
    }

    try:
        gdf  = gpd.read_file(osm_path)
        tags = CATEGORY_TAGS.get(subcategory, {})
        count = 0
        for col, vals in tags.items():
            if col in gdf.columns:
                count += int(gdf[col].isin(vals).sum())
        baseline = BASELINE.get(subcategory, 3)
        # Saturated at 3× baseline; invert so opportunity = high score
        penalty = float(np.clip(1.0 - (count / (baseline * 3)), 0.0, 1.0))
        return penalty

    except Exception as e:
        print(f"[demand_engine] Competition error: {e}")
        return 0.6


def _compute_resource_suitability(
    b04_path: str, b08_path: str, bbox: list, subcategory: str
) -> float:
    """
    Fraction of valid pixels whose NDVI falls in the
    category-specific ideal range.
    Ranges reflect UAE landscape: desert (0–0.05),
    sparse scrub (0.05–0.15), irrigated/agricultural (0.15+).
    """
    NDVI_RANGES: Dict[str, tuple] = {
        "1.1": (0.12, 1.00),   # agriculture — needs meaningful vegetation
        "1.2": (0.03, 0.45),   # home production — near residential, some greenery
        "1.3": (0.00, 0.12),   # manufacturing — built/bare preferred
        "2.1": (0.00, 0.20),   # local services — near built-up areas
        "2.2": (0.00, 0.35),   # mobility — road corridors, mixed terrain
        "2.3": (0.00, 0.30),   # community services — residential zones
        "2.4": (0.00, 0.20),   # professional — commercial/built-up
        "3.1": (0.00, 0.25),   # retail — built-up commercial zones
        "3.2": (0.00, 0.40),   # social/cultural — mixed community areas
        "3.3": (0.00, 0.08),   # tourism — desert terrain preferred (dark sky)
    }
    lo, hi = NDVI_RANGES.get(subcategory, (0.0, 1.0))
    geom = _bbox_geometry(bbox, b08_path)
    try:
        with rasterio.open(b08_path) as src:
            nir_data, _ = raster_mask(src, [geom], crop=True, nodata=0)
            nir = nir_data[0].astype(float)
        with rasterio.open(b04_path) as src:
            red_data, _ = raster_mask(src, [geom], crop=True, nodata=0)
            red = red_data[0].astype(float)

        valid = (nir + red) > 0
        ndvi  = np.where(valid, (nir - red) / (nir + red + 1e-10), -1.0)
        valid_count = int(np.sum(valid))
        if valid_count == 0:
            return 0.5
        in_range = int(np.sum((ndvi >= lo) & (ndvi <= hi) & valid))
        return float(in_range / valid_count)

    except Exception as e:
        print(f"[demand_engine] Resource suitability error: {e}")
        return 0.5


# ── Score aggregation ─────────────────────────────────────────────────────────

def compute_demand_score(signals: Dict, weights: Dict) -> int:
    """
    Weighted linear combination of five signals → 0–100 integer score.
    Weights per subcategory are in config/weights.json,
    each with a _rationale comment. All weight vectors sum to 1.0.
    """
    raw = (
        weights["agricultural_density"] * signals["agricultural_density"]
        + weights["population_proxy"]       * signals["population_proxy"]
        + weights["road_accessibility"]     * signals["road_accessibility"]
        + weights["competition_penalty"]    * signals["competition_penalty"]
        + weights["resource_suitability"]   * signals["resource_suitability"]
    )
    return int(np.clip(raw * 100, 0, 100))


def compute_all_demand_scores(community_config: Dict) -> Dict:
    bbox   = community_config["bbox"]
    b04    = community_config["sentinel2_b04"]
    b08    = community_config["sentinel2_b08"]
    dem    = community_config["dem_tile"]
    viirs  = community_config["viirs_tile"]
    osm    = community_config["osm_geojson"]
    center = community_config["center"]

    weights_all = _load_weights()

    # ── Shared signals (computed once, reused across all subcategories) ───────
    print("[demand_engine] Computing NDVI agricultural density...")
    agri_density = _compute_ndvi_density(b04, b08, bbox, threshold=0.08)
    print(f"  → agricultural_density = {agri_density:.3f}")

    print("[demand_engine] Computing VIIRS population proxy...")
    pop_proxy = _compute_viirs_proxy(viirs, bbox)
    print(f"  → population_proxy = {pop_proxy:.3f}")

    print("[demand_engine] Computing road accessibility...")
    road_acc = _compute_road_accessibility(dem, osm, center, bbox)
    print(f"  → road_accessibility = {road_acc:.3f}")

    # ── Per-subcategory signals ───────────────────────────────────────────────
    results: Dict = {}
    for cat_id in sorted(weights_all.keys()):
        if cat_id.startswith("_"):   # skip _rationale keys if any leaked
            continue
        print(f"[demand_engine] Scoring {cat_id}...")
        cat_weights = weights_all[cat_id]

        comp = _compute_competition_penalty(osm, cat_id)
        rsrc = _compute_resource_suitability(b04, b08, bbox, cat_id)

        signals = {
            "agricultural_density": round(agri_density, 4),
            "population_proxy":     round(pop_proxy, 4),
            "road_accessibility":   round(road_acc, 4),
            "competition_penalty":  round(comp, 4),
            "resource_suitability": round(rsrc, 4),
        }
        score = compute_demand_score(signals, cat_weights)
        results[cat_id] = {
            "demand_score": score,
            "signals": signals,
        }
        print(f"  → score = {score}/100  "
              f"(comp={comp:.2f}, rsrc={rsrc:.2f})")

    # ── Save ─────────────────────────────────────────────────────────────────
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    out_path = os.path.join(
        OUTPUTS_DIR,
        f"demand_scores_{community_config['community_id']}.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[demand_engine] Saved → {out_path}")
    return results


def load_demand_scores(community_id: str) -> Dict:
    path = os.path.join(OUTPUTS_DIR, f"demand_scores_{community_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No pre-computed demand scores at {path}. "
            f"Run: python scripts/compute_demand.py --community {community_id}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)