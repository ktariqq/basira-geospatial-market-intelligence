# Data Acquisition — Basira (بصيرة)

All data used in Basira is freely available from open public sources. No proprietary datasets, no paid APIs, no web scraping. Every file can be reproduced by following the steps below. All processing was done locally using QGIS and Python (rasterio).

---

## Data Sources Summary

| File | Source | Dataset | Resolution | Date Acquired | License |
|---|---|---|---|---|---|
| `osm_alquaa.geojson` | OpenStreetMap via Overpass Turbo | Administrative boundary + POIs | Vector | June 2026 | ODbL |
| `sentinel2_B04_alquaa.tif` | Copernicus Data Space | Sentinel-2 L2A Band 4 (Red) | 10m | Jan–Mar 2025 | Copernicus Open Access |
| `sentinel2_B08_alquaa.tif` | Copernicus Data Space | Sentinel-2 L2A Band 8 (NIR) | 10m | Jan–Mar 2025 | Copernicus Open Access |
| `dem_alquaa.tif` | OpenTopography / NASA | NASADEM (30m) | 30m | 2000, processed 2020 | NASA Open Data |
| `viirs_alquaa.tif` | NASA EarthData | VIIRS Black Marble VNP46A4 Annual | 500m | 2025 composite | NASA Open Data |

**Bounding box used for all datasets:**
```
West:  54.775°E
South: 23.049°N
East:  55.484°E
North: 23.549°N
```

---

## Step-by-Step Reproduction Guide

### Step 1 — Community Boundary (OpenStreetMap)

**Tool:** Overpass Turbo — [overpass-turbo.eu](https://overpass-turbo.eu)
**Account required:** No

1. Go to [overpass-turbo.eu](https://overpass-turbo.eu)
2. Paste the following query into the editor:
```
[out:json][timeout:60];
(
  relation["name:en"="Al Qou'"]["boundary"="administrative"];
);
out body;
>;
out skel qt;
```
3. Click **Run**
4. Click **Export → GeoJSON**
5. Save as `osm_alquaa.geojson`

This file gives you the administrative boundary polygon for Al Qua'a. Extract the bounding box from the polygon coordinates to use in all subsequent downloads. For Al Qua'a this is `[23.049, 54.775, 23.549, 55.484]` (south, west, north, east).

To get POIs and roads inside the boundary, run this second query:
```
[out:json][timeout:60];
(
  node(23.049, 54.775, 23.549, 55.484);
  way(23.049, 54.775, 23.549, 55.484);
);
out body;
>;
out skel qt;
```
Export this as GeoJSON and merge with or append to your boundary file.

---

### Step 2 — Sentinel-2 Satellite Imagery (NDVI)

**Tool:** Copernicus Data Space Browser — [dataspace.copernicus.eu](https://dataspace.copernicus.eu)
**Account required:** Yes (free, takes 2 minutes)

1. Register a free account at [dataspace.copernicus.eu](https://dataspace.copernicus.eu)
2. Click **"Open Copernicus Browser"**
3. On the map, zoom to Al Qua'a and draw a rectangle over the area using the draw tool
4. In the left panel set these filters:
   - Collection: **Sentinel-2 L2A**
   - Date range: **January 2025 – March 2025** (use dry season for desert areas — lowest cloud cover)
   - Cloud coverage: **0% – 10%**
5. Click **Search**
6. In the results, hover over each result to see which tile it covers on the map. Select a tile that covers the **centre** of your community boundary. Note: Sentinel-2 tiles are fixed ~100km grid squares — your area will appear across 2–3 tiles. One central tile is sufficient.
7. Click the **three dots** next to the result → **"Analytical"** download
8. Select only **Band 4 (B04)** and **Band 8 (B08)**
9. Format: **GeoTIFF**, Resolution: **10m**
10. Download and save as `sentinel2_B04_alquaa.tif` and `sentinel2_B08_alquaa.tif`

NDVI is computed from these two bands at runtime:
```python
# NDVI = (B08 - B04) / (B08 + B04)
ndvi = (nir - red) / (nir + red + 1e-10)
```

---

### Step 3 — Digital Elevation Model (Terrain)

**Tool:** OpenTopography — [portal.opentopography.org](https://portal.opentopography.org)
**Account required:** No (email required for download notification)

1. Go to [portal.opentopography.org](https://portal.opentopography.org)
2. Click **"Find Data"** → **"Global and Regional DEMs"**
3. Select **"NASADEM Global Digital Elevation Model"** from the list
4. In the coordinate fields enter your bounding box:
   - Xmin: `54.775`
   - Ymin: `23.049`
   - Xmax: `55.484`
   - Ymax: `23.549`
5. Output format: **GeoTIFF**
6. Enter your email address and click **"Submit Job"**
7. You will receive a download link by email within a few minutes
8. Download and save as `dem_alquaa.tif`

---

### Step 4 — VIIRS Night Lights (Population Proxy)

**Tool:** NASA EarthData Search — [search.earthdata.nasa.gov](https://search.earthdata.nasa.gov)
**Account required:** Yes (free NASA EarthData account)

1. Register at [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov) (free)
2. Go to [search.earthdata.nasa.gov](https://search.earthdata.nasa.gov)
3. Search for: `VNP46A4`
4. In the left panel click **"Spatial"** → **"Bounding Box"** and enter:
   - W: `54.775`, S: `23.049`, E: `55.484`, N: `23.549`
5. Click **"Temporal"** and set: `2025-01-01` to `2025-12-31`
6. Select the result that intersects your area
7. Click **"Download"** → **"Direct Download"**
8. You will receive an `.h5` (HDF5) file — this is the correct format
9. Convert to GeoTIFF using QGIS:
   - Drag the `.h5` file into QGIS
   - When prompted for subdataset, select **`DNB_BRDF-Corrected_NTL`**
   - Right-click the layer → **Export → Save As**
   - Format: **GeoTIFF**, CRS: **EPSG:4326**
   - Save as `viirs_alquaa.tif`

---

## Clipping All Files to Your Boundary (Recommended)

Once all files are downloaded, clip them to your exact community boundary using QGIS to ensure consistent coverage and reduce file size:

1. Open QGIS and load `alquaa_boundary_polygon.geojson`
2. For each raster file: **Raster → Extraction → Clip Raster by Mask Layer**
3. Input layer: your raster file
4. Mask layer: `alquaa_boundary_polygon.geojson`
5. Save output with the same filename
```
data/
├── alquaa_boundary_polygon.geojson
├── osm_alquaa.geojson
├── dem_alquaa_clipped.tif
├── viirs_alquaa_clipped.tif
├── sentinel2_B04_clipped.tif
└── sentinel2_B08_clipped.tif
```

---

## Reproducing This for Any Other Community

Basira is designed to work with any rural community globally. To add a new community:

**1. Get the boundary**
Search Overpass Turbo for the community name and export the administrative boundary as GeoJSON. Extract the bounding box from the polygon coordinates.

**2. Download the same four datasets**
Use the exact same steps above, substituting your new bounding box coordinates in each download form.

**3. Create a community config file**
Copy `config/alquaa.json` and update all fields:
```json
{
  "community_id": "your_community_id",
  "community_name_ar": "اسم المجتمع",
  "community_name_en": "Community Name",
  "center": [LAT, LON],
  "bbox": [SOUTH, WEST, NORTH, EAST],
  "sentinel2_tile": "data/sentinel2_yourcommunity.tif",
  "dem_tile": "data/dem_yourcommunity.tif",
  "viirs_tile": "data/viirs_yourcommunity.tif",
  "osm_geojson": "data/osm_yourcommunity.geojson"
}
```

Total time to onboard a new community: approximately 30–60 minutes of data download and configuration. No code changes required.

---

## Data Licences

| Dataset | Licence | Commercial Use |
|---|---|---|
| OpenStreetMap | Open Database Licence (ODbL) | Yes, with attribution |
| Sentinel-2 | Copernicus Open Access | Yes, with attribution |
| NASADEM | NASA Open Data | Yes, with attribution |
| VIIRS Black Marble | NASA Open Data | Yes, with attribution |

All datasets are free, open, and require only attribution. No API keys required except a free Copernicus account for Sentinel-2 download.
