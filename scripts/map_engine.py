import json
import os
import numpy as np
import folium
from folium import plugins
import rasterio
from rasterio.mask import mask as raster_mask
import geopandas as gpd
from shapely.geometry import box, mapping
from typing import Dict, List, Tuple
import pyproj

try:
    from i18n import STRINGS
except ImportError:
    from scripts.b_i18n import STRINGS


PALETTE = {
    "violet":        "#7F00FF",
    "deep_purple":   "#2E003E",
    "lavender":      "#C8A2C8",
    "plum":          "#8E4585",
    "hot_pink":      "#FF007F",
    "shocking_pink": "#FF4DCC",
    "dark_pink":     "#C2185B",
    "soft_pink":     "#F8BBD0",
    "background":    "#0D0010",
    "text":          "#E8D5F5",
    "grid":          "#3D1A5E",
    "success":       "#3FB950",
    "warning":       "#F77F00",
    "border":        "#3D1A5E",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bbox_geometry_for_raster(bbox: list, raster_path: str) -> dict:
    """
    Return a masking geometry reprojected into the raster's native CRS.
    bbox = [south, west, north, east] in WGS84 decimal degrees.
    Sentinel-2 tiles are delivered in UTM — this handles the reprojection
    automatically so raster_mask never sees a CRS mismatch.
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


def _read_ndvi(b04_path: str, b08_path: str, bbox: list) -> Tuple[np.ndarray, int, int]:
    """
    Read B04 and B08, compute NDVI, return (ndvi_array, height, width).
    Array values are in [-1, 1]; invalid/nodata pixels set to NaN.
    Raises on unrecoverable error — callers handle exceptions.
    """
    geom = _bbox_geometry_for_raster(bbox, b08_path)
    with rasterio.open(b08_path) as src:
        nir_data, _ = raster_mask(src, [geom], crop=True, nodata=0)
        nir = nir_data[0].astype(float)
    with rasterio.open(b04_path) as src:
        red_data, _ = raster_mask(src, [geom], crop=True, nodata=0)
        red = red_data[0].astype(float)

    valid = (nir + red) > 0
    ndvi  = np.where(valid, (nir - red) / (nir + red + 1e-10), np.nan)
    h, w  = ndvi.shape
    return ndvi, h, w


def _pixel_to_wgs84(r: int, c: int, h: int, w: int, bbox: list) -> Tuple[float, float]:
    """Convert raster pixel (row, col) back to WGS84 lat/lon for Folium."""
    south, west, north, east = bbox
    lon = west  + (c / w) * (east  - west)
    lat = north - (r / h) * (north - south)
    return lat, lon


def _demand_label(score: int, lang: str = "ar") -> str:
    if score >= 65:
        return STRINGS["high_ar"] if lang == "ar" else STRINGS["high_en"]
    elif score >= 40:
        return STRINGS["medium_ar"] if lang == "ar" else STRINGS["medium_en"]
    else:
        return STRINGS["low_ar"] if lang == "ar" else STRINGS["low_en"]


def _score_color(score: int) -> str:
    if score >= 80:
        return PALETTE["shocking_pink"]
    elif score >= 65:
        return PALETTE["hot_pink"]
    elif score >= 50:
        return PALETTE["plum"]
    elif score >= 35:
        return PALETTE["lavender"]
    else:
        return PALETTE["violet"]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi    = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = (np.sin(dphi / 2) ** 2
         + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


# ── Layer builders ────────────────────────────────────────────────────────────

def _ndvi_grid(
    b04_path: str, b08_path: str, bbox: list, grid_size: int = 30
) -> Tuple[List, np.ndarray]:
    """
    Downsample NDVI raster to a coarse grid for the heatmap layer.
    Returns (points_list, full_ndvi_array).
    points_list entries: [lat, lon, ndvi_value]
    Coordinates are always WGS84 — safe for Folium.
    """
    try:
        ndvi, h, w = _read_ndvi(b04_path, b08_path, bbox)
        step_r = max(1, h // grid_size)
        step_c = max(1, w // grid_size)

        points = []
        for r in range(0, h, step_r):
            for c in range(0, w, step_c):
                val = float(ndvi[r, c])
                if np.isnan(val):
                    continue
                lat, lon = _pixel_to_wgs84(r, c, h, w, bbox)
                points.append([lat, lon, val])

        return points, ndvi

    except Exception as e:
        print(f"[map_engine] NDVI grid error: {e}")
        south, west, north, east = bbox
        lat_c = (south + north) / 2
        lon_c = (west  + east)  / 2
        return [[lat_c, lon_c, 0.1]], np.array([[0.1]])


def _demand_heatmap_points(
    b04_path: str, b08_path: str, bbox: list,
    signals: Dict, grid_size: int = 25
) -> List:
    """
    Build demand-weighted heatmap point list for Folium HeatMap.
    Intensity blends the category demand score with local NDVI,
    population proxy, and road accessibility signals.
    All output coordinates are WGS84.
    """
    base_score = signals.get("demand_score", 50) / 100.0
    pop  = signals.get("population_proxy",   0.3)
    road = signals.get("road_accessibility", 0.5)

    try:
        ndvi, h, w = _read_ndvi(b04_path, b08_path, bbox)
        step_r = max(1, h // grid_size)
        step_c = max(1, w // grid_size)

        points = []
        for r in range(0, h, step_r):
            for c in range(0, w, step_c):
                v = float(ndvi[r, c])
                if np.isnan(v):
                    v = 0.0
                intensity = (
                    base_score * 0.5
                    + v         * 0.3
                    + pop       * 0.1
                    + road      * 0.1
                )
                lat, lon = _pixel_to_wgs84(r, c, h, w, bbox)
                points.append([lat, lon, float(np.clip(intensity, 0, 1))])

        return points

    except Exception as e:
        print(f"[map_engine] Demand heatmap error: {e}")
        south, west, north, east = bbox
        return [[(south + north) / 2, (west + east) / 2, base_score]]


def _opportunity_zone_polygons(
    b04_path: str, b08_path: str, bbox: list,
    signals: Dict, threshold: float = 0.55
) -> List[Dict]:
    """
    Identify high-opportunity grid cells and return as WGS84 GeoJSON polygons.
    Each cell covers one pixel block; intensity = demand score × NDVI blend.
    Cells above threshold get a pink opportunity zone polygon on the map.
    """
    base_score = signals.get("demand_score", 50) / 100.0
    south, west, north, east = bbox

    try:
        ndvi, h, w = _read_ndvi(b04_path, b08_path, bbox)
        grid_size = 20
        step_r = max(1, h // grid_size)
        step_c = max(1, w // grid_size)

        polygons = []
        for r in range(0, h, step_r):
            for c in range(0, w, step_c):
                v = float(ndvi[r, c])
                if np.isnan(v):
                    v = 0.0
                intensity = base_score * 0.6 + v * 0.4

                if intensity < threshold:
                    continue

                # All four corners in WGS84
                lat0, lon0 = _pixel_to_wgs84(r,          c,          h, w, bbox)
                lat1, lon1 = _pixel_to_wgs84(r + step_r, c + step_c, h, w, bbox)

                cell_score = int(np.clip(intensity * 100, 0, 100))
                polygons.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon0, lat0], [lon1, lat0],
                            [lon1, lat1], [lon0, lat1],
                            [lon0, lat0],
                        ]]
                    },
                    "properties": {
                        "score":    cell_score,
                        "label_ar": STRINGS["opportunity_zone_ar"],
                    }
                })

        return polygons

    except Exception as e:
        print(f"[map_engine] Opportunity zone error: {e}")
        return []


def _osm_markers(osm_path: str, center: list, map_obj) -> None:
    """
    Add OSM POI markers directly to a Folium FeatureGroup (no clustering).
    Individual dots with Arabic popups are cleaner for a sparse rural area.
    Capped at 500 features to keep HTML file size manageable.
    """
    try:
        gdf   = gpd.read_file(osm_path)
        count = 0

        for _, row in gdf.iterrows():
            if row.geometry is None:
                continue

            geom_type = row.geometry.geom_type
            if geom_type == "Point":
                lat, lon = row.geometry.y, row.geometry.x
            elif geom_type in ("Polygon", "MultiPolygon"):
                c = row.geometry.centroid
                lat, lon = c.y, c.x
            else:
                # LineString roads etc — skip, they are not POIs
                continue

            name  = (row.get("name") or row.get("name:ar")
                     or row.get("name:en") or "")
            ptype = (row.get("amenity") or row.get("shop")
                     or row.get("highway") or row.get("landuse")
                     or row.get("tourism") or "POI")
            dist_km = _haversine(center[0], center[1], lat, lon)

            popup_html = (
                f'<div dir="rtl" style="font-family:Arial;min-width:160px">'
                f'<b>{name or "غير محدد"}</b><br>'
                f'النوع: {ptype}<br>'
                f'المسافة: {dist_km:.1f} كم'
                f'</div>'
            )
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color=PALETTE["lavender"],
                fill=True,
                fill_color=PALETTE["lavender"],
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=220),
            ).add_to(map_obj)

            count += 1
            if count >= 500:
                break

    except Exception as e:
        print(f"[map_engine] OSM marker error: {e}")


# ── Info panel ────────────────────────────────────────────────────────────────

def _info_panel_html(
    category_ar: str, category_en: str,
    macro_ar: str,    macro_en: str,
    score: int,       community_ar: str,
    explanation_ar: str,
) -> str:
    demand_lbl = _demand_label(score)
    color      = _score_color(score)
    return f"""
    <div id="basira-panel" style="
        position:fixed; top:10px; right:10px; z-index:9999;
        background:{PALETTE['background']};
        border:1px solid {PALETTE['border']};
        border-radius:12px; padding:16px 20px; width:280px;
        font-family:Cairo,Arial,sans-serif; color:{PALETTE['text']};
        direction:rtl;
        box-shadow:0 4px 24px rgba(127,0,255,0.3);
    ">
      <div style="font-size:22px;font-weight:bold;
                  color:{PALETTE['violet']};margin-bottom:2px;">
        بصيرة
        <span style="font-size:13px;color:{PALETTE['lavender']}">| Basira</span>
      </div>
      <div style="font-size:11px;color:{PALETTE['lavender']};margin-bottom:12px;">
        ذكاء السوق الجغرافي | Geospatial Market Intelligence
      </div>

      <div style="font-size:12px;margin-bottom:4px;">
        <span style="color:{PALETTE['lavender']}">الفئة:</span> {category_ar}
        <span style="color:{PALETTE['grid']};font-size:10px"> | {category_en}</span>
      </div>
      <div style="font-size:12px;margin-bottom:4px;">
        <span style="color:{PALETTE['lavender']}">المجموعة:</span> {macro_ar}
      </div>
      <div style="font-size:12px;margin-bottom:8px;">
        <span style="color:{PALETTE['lavender']}">المجتمع:</span> {community_ar}
      </div>

      <div style="margin-bottom:10px;">
        <div style="font-size:13px;font-weight:bold;margin-bottom:4px;">
          مؤشر الطلب:
          <span style="color:{color}">{score}/100 — {demand_lbl}</span>
        </div>
        <div style="background:{PALETTE['grid']};border-radius:6px;
                    height:10px;width:100%;">
          <div style="background:{color};width:{score}%;
                      height:10px;border-radius:6px;"></div>
        </div>
      </div>

      <div style="font-size:11px;color:{PALETTE['lavender']};
                  font-weight:bold;margin-bottom:4px;">
        لماذا هذه النتيجة؟
      </div>
      <div style="font-size:11px;line-height:1.6;
                  color:{PALETTE['text']};margin-bottom:10px;">
        {explanation_ar}
      </div>

      <div style="font-size:10px;color:{PALETTE['grid']};
                  border-top:1px solid {PALETTE['border']};padding-top:6px;">
        المصدر: سنتينل-2 · NASADEM · OSM · VIIRS<br>
        <span style="color:{PALETTE['success']};">
          ● معالجة محلية | Processing locally
        </span>
      </div>
    </div>
    """


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_map(
    community_config: Dict,
    subcategory: str,
    signals: Dict,
    explanation_ar: str,
    output_path: str = None,
) -> str:
    bbox   = community_config["bbox"]
    center = community_config["center"]
    b04    = community_config["sentinel2_b04"]
    b08    = community_config["sentinel2_b08"]
    osm    = community_config["osm_geojson"]
    score  = signals.get("demand_score", 0)

    cat_ar       = STRINGS["subcategories"][subcategory]["ar"]
    cat_en       = STRINGS["subcategories"][subcategory]["en"]
    macro_id     = subcategory.split(".")[0]
    macro_ar     = STRINGS["macro_groups"][macro_id]["ar"]
    macro_en     = STRINGS["macro_groups"][macro_id]["en"]
    community_ar = community_config.get("community_name_ar", "")

    # ── Base map ──────────────────────────────────────────────────────────────
    m = folium.Map(
        location=center,
        zoom_start=community_config.get("zoom_start", 11),
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    # ── Layer 1 — NDVI land classification ───────────────────────────────────
    ndvi_points, _ = _ndvi_grid(b04, b08, bbox, grid_size=30)
    ndvi_heat_pts  = [
        [p[0], p[1], max(0.0, p[2])]
        for p in ndvi_points
        if p[2] > 0.03          # filter absolute bare desert noise
    ]
    if ndvi_heat_pts:
        ndvi_layer = folium.FeatureGroup(
            name=(f"{STRINGS['layers']['ndvi_ar']} | "
                  f"{STRINGS['layers']['ndvi_en']}"),
            show=True,
        )
        plugins.HeatMap(
            ndvi_heat_pts,
            gradient={
                "0.0": "#2E003E",
                "0.3": "#7F00FF",
                "0.6": "#8E4585",
                "1.0": "#3FB950",
            },
            radius=12, blur=15, min_opacity=0.3,
        ).add_to(ndvi_layer)
        ndvi_layer.add_to(m)

    # ── Layer 2 — Demand heatmap ──────────────────────────────────────────────
    demand_pts = _demand_heatmap_points(b04, b08, bbox, signals, grid_size=25)
    if demand_pts:
        demand_layer = folium.FeatureGroup(
            name=(f"{STRINGS['layers']['heatmap_ar']} | "
                  f"{STRINGS['layers']['heatmap_en']}"),
            show=True,
        )
        plugins.HeatMap(
            demand_pts,
            gradient={
                "0.0":  "#2E003E",
                "0.25": "#7F00FF",
                "0.5":  "#8E4585",
                "0.75": "#FF007F",
                "1.0":  "#FF4DCC",
            },
            radius=18, blur=20, min_opacity=0.4,
        ).add_to(demand_layer)
        demand_layer.add_to(m)

    # ── Layer 3 — Opportunity zones ───────────────────────────────────────────
    # Lower threshold for high-scoring categories so zones actually appear
    threshold    = 0.48 if score >= 65 else 0.56
    opp_polygons = _opportunity_zone_polygons(
        b04, b08, bbox, signals, threshold=threshold
    )
    if opp_polygons:
        opp_layer = folium.FeatureGroup(
            name=(f"{STRINGS['layers']['zones_ar']} | "
                  f"{STRINGS['layers']['zones_en']}"),
            show=True,
        )
        for feat in opp_polygons:
            cell_score   = feat["properties"]["score"]
            tooltip_html = (
                f"<div dir='rtl' style='font-family:Cairo,Arial;font-size:12px;"
                f"color:#E8D5F5;background:#0D0010;padding:8px;border-radius:6px;'>"
                f"<b>{STRINGS['opportunity_zone_ar']}</b><br>"
                f"مؤشر الفرصة: {cell_score}٪<br>"
                f"<span style='font-size:10px;color:#C8A2C8'>"
                f"{STRINGS['opportunity_zone_en']}: {cell_score}%</span>"
                f"</div>"
            )
            folium.GeoJson(
                feat,
                style_function=lambda x: {
                    "fillColor":   PALETTE["hot_pink"],
                    "color":       PALETTE["shocking_pink"],
                    "weight":      1.5,
                    "fillOpacity": 0.35,
                },
                tooltip=folium.Tooltip(tooltip_html),
            ).add_to(opp_layer)
        opp_layer.add_to(m)

    # ── Layer 4 — OSM POIs ────────────────────────────────────────────────────
    poi_layer = folium.FeatureGroup(
        name=(f"{STRINGS['layers']['poi_ar']} | "
              f"{STRINGS['layers']['poi_en']}"),
        show=True,
    )
    _osm_markers(osm, center, poi_layer)
    poi_layer.add_to(m)

    # ── Controls ──────────────────────────────────────────────────────────────
    folium.LayerControl(collapsed=True,  position="bottomleft").add_to(m)
    plugins.MiniMap(toggle_display=True, position="bottomright").add_to(m)

    # ── Info panel ────────────────────────────────────────────────────────────
    m.get_root().html.add_child(
        folium.Element(
            _info_panel_html(
                cat_ar, cat_en, macro_ar, macro_en,
                score, community_ar, explanation_ar,
            )
        )
    )

    # Cairo font (online — falls back to Arial offline)
    m.get_root().header.add_child(folium.Element(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Cairo'
        ':wght@400;600;700&display=swap" rel="stylesheet">'
    ))

    # ── Save ──────────────────────────────────────────────────────────────────
    if output_path is None:
        output_path = os.path.join(
            "outputs",
            f"basira_map_{subcategory.replace('.', '_')}.html"
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    m.save(output_path)
    return output_path