#!/bin/bash
# Basira data acquisition helper — prints instructions and checks files.
# Full manual steps are in data/README.md

echo "================================================"
echo "  بصيرة | Basira — Data Acquisition Helper"
echo "================================================"
echo ""
echo "Required files in data/:"
REQUIRED=("sentinel2_B04_alquaa_clipped.tif" "sentinel2_B08_alquaa_clipped.tif" "dem_alquaa_clipped.tif" "viirs_alquaa_clipped.tif" "osm_alquaa.geojson")
ALL_OK=true
for f in "${REQUIRED[@]}"; do
  if [ -f "data/$f" ]; then
    SIZE=$(du -sh "data/$f" | cut -f1)
    echo "  ✓ $f ($SIZE)"
  else
    echo "  ✗ MISSING: $f"
    ALL_OK=false
  fi
done
echo ""
if [ "$ALL_OK" = true ]; then
  echo "All data files present. Ready to run compute_demand.py."
else
  echo "Missing files detected. See data/README.md for acquisition steps."
fi
echo ""
echo "Bounding box (Al Qua'a): S=23.049, W=54.775, N=23.549, E=55.484"
echo "================================================"