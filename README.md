
<div align="center">
![Left](assets/left-flourish.png) # بصيرة | Basira ![Right](assets/right-flourish.png)
**ذكاء السوق الجغرافي للمجتمعات الريفية**  
Geospatial Market Intelligence for Rural Entrepreneurs

![Offline Ready](https://img.shields.io/badge/Offline-Ready-7c3aed?style=flat-square&labelColor=1a0a2e)
![Arabic First](https://img.shields.io/badge/Arabic-First-7c3aed?style=flat-square&labelColor=1a0a2e)
![CPU Only](https://img.shields.io/badge/Inference-CPU_Only-7c3aed?style=flat-square&labelColor=1a0a2e)
![License](https://img.shields.io/badge/License-MIT-7c3aed?style=flat-square&labelColor=1a0a2e)
<br>
![Sentinel-2](https://img.shields.io/badge/Sentinel--2-L2A_10m-7c3aed?style=flat-square&labelColor=1a0a2e&logo=satellite&logoColor=white)
![NASADEM](https://img.shields.io/badge/NASADEM-30m_DEM-7c3aed?style=flat-square&labelColor=1a0a2e)
![VIIRS](https://img.shields.io/badge/VIIRS-Black_Marble-7c3aed?style=flat-square&labelColor=1a0a2e)
![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-ODbL-7c3aed?style=flat-square&labelColor=1a0a2e&logo=openstreetmap&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-7c3aed?style=flat-square&labelColor=1a0a2e&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-7c3aed?style=flat-square&labelColor=1a0a2e&logo=python&logoColor=white)


<br/>

━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

<br/>

## 🟣 The Challenge

**Tatweer Hackathon 2026 · Challenge 3 — The Data Gap for Local Entrepreneurs**

> *Entrepreneurs here often make decisions in the dark. There is little local data on customers, demand, or what the area actually needs, so people guess.*

Basira gives rural entrepreneurs in Al Qua'a — and any rural community globally — access to satellite-derived local data they could never otherwise gather or interpret. It turns environmental and spatial signals from real orbital instruments into evidence-based business decisions, delivered in Arabic, entirely offline.

<br/>

## 🟣 The Problem

A camel farmer in Al Qua'a who wants to expand into cheese production has no way to answer the most basic questions: Is there enough pasture within reach? How far is the nearest market? How saturated is the local food production space? There are no local surveys. No data teams. No market research firms operating here. Decisions are made on instinct and word of mouth.

This is not a technology access problem — people have phones. It is a **data interpretation gap**. The satellite data exists and is free. NASA, ESA, and OpenStreetMap collectively image the entire Earth at 10–500m resolution. No one has built the layer that makes that data legible to an entrepreneur who has never heard of NDVI.

Basira is that layer.

<br/>

## 🟣 What Basira Does

Basira takes a business idea — spoken aloud in Arabic or typed in either language — and returns a structured, evidence-based assessment of its local viability, grounded in four real satellite and geospatial datasets acquired specifically for Al Qua'a. It identifies the highest-opportunity locations on an interactive map, explains the demand score in plain Arabic, and provides the exact licensing pathway for that business type under UAE law. Everything runs locally on CPU with no internet connection required after a one-time model download.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Live Results — Al Qua'a

> The following figures are computed from real satellite data. To reproduce them exactly, run `python scripts/compute_demand.py --community alquaa`. Pre-computed output is committed to `outputs/demand_scores_alquaa.json`.

**Bounding box:** `23.049°N – 23.549°N, 54.775°E – 55.484°E`  
**Data acquisition:** January – June 2026  
**Processing:** rasterio, QGIS, scipy

| Signal | Computed Value | Source |
|--------|---------------|--------|
| NDVI agricultural density (threshold > 0.2) | computed from B04 + B08 | Sentinel-2 L2A |
| VIIRS mean night radiance | normalised against 100 nW/cm²/sr regional max | NASA Black Marble VNP46A4 |
| OSM POI count within bounding box | extracted from osm_alquaa.geojson | OpenStreetMap |
| Road accessibility score | slope-weighted cost-distance via scipy | NASADEM + OSM |

**Demand scores by subcategory** (0–100, higher = stronger opportunity signal):

| Category | Score | Top Signal |
|----------|-------|-----------|
| 🐪 Primary Resource (agriculture/livestock) | see `demand_scores_alquaa.json` | agricultural density + resource suitability |
| 🏠 Home-Based Production | see `demand_scores_alquaa.json` | population proxy + road access |
| 🛠 Micro Manufacturing | see `demand_scores_alquaa.json` | road accessibility + competition gap |
| 🧹 Essential Local Services | see `demand_scores_alquaa.json` | population proxy + competition |
| 🚗 Mobility & Field Services | see `demand_scores_alquaa.json` | road accessibility |
| 🏫 Community & Human Services | see `demand_scores_alquaa.json` | population proxy + POI gap |
| 💼 Professional Services | see `demand_scores_alquaa.json` | population proxy + built-up density |
| 🛒 Micro Retail & Distribution | see `demand_scores_alquaa.json` | population + competition gap |
| 🎉 Social & Cultural Economy | see `demand_scores_alquaa.json` | community POI gap |
| 🏜 Tourism & Environment | see `demand_scores_alquaa.json` | terrain + VIIRS darkness + road access |

> **Note on Tourism:** Al Qua'a is globally recognised as one of the darkest inhabited locations on Earth. The VIIRS Black Marble night radiance data for this bounding box directly captures this — low radiance = high tourism suitability score in Basira's model. The system responds to the community's actual geography.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 System Architecture
```
User Input (Voice OR Text — Arabic OR English, auto-detected)
│
▼
┌─────────────────────────────────────┐
│   faster-whisper small (CPU-only)   │  ← voice transcription, offline
│   Language auto-detection           │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│   Multilingual MiniLM Classifier    │  ← cosine similarity, <1s
│   paraphrase-multilingual-MiniLM    │
│   3 macro groups · 10 subcategories │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│       Demand Engine                 │  ← fully offline, pre-computed
│                                     │
│  Sentinel-2 NDVI  ──► agri density  │
│  VIIRS radiance   ──► pop proxy     │
│  NASADEM + OSM    ──► road access   │
│  OSM POI tags     ──► competition   │
│  NDVI threshold   ──► resource suit │
└─────────────────────────────────────┘
│
├──► Map Engine     → Folium interactive HTML (5 layers)
├──► License Engine → local JSON pathway (no internet)
└──► Decision Report → Arabic-primary structured output
```

**Performance targets (CPU-only, no GPU):**

| Component | Target | Method |
|-----------|--------|--------|
| End-to-end | < 8s | pre-loaded data |
| Classification | < 1s | MiniLM cosine similarity |
| Transcription | < 5s | faster-whisper small int8 |
| Map generation | < 3s | pre-computed demand grid |

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## Data Architecture & Falsifiability

Every demand signal in Basira is pinned to a named file, a named computation, and a documented output range. No vague formulas. No black boxes.

### Source Files
```
data/alquaa/
├── sentinel2_B04_alquaa_clipped.tif   # Sentinel-2 L2A Band 4 (Red),  10m, Jan–Mar 2025
├── sentinel2_B08_alquaa_clipped.tif   # Sentinel-2 L2A Band 8 (NIR),  10m, Jan–Mar 2025
├── dem_alquaa_clipped.tif             # NASADEM, 30m resolution, processed 2020
├── viirs_alquaa_clipped.tif           # VIIRS Black Marble VNP46A4, 500m, 2025 annual
└── osm_alquaa.geojson         # OpenStreetMap, acquired June 2026
```
All files are free, open, and reproducible. Full acquisition steps are in [`data/alquaa/README.md`](data/alquaa/README.md).

### Signal Computation Table

| Signal | Source File | Computation | Output Range |
|--------|-------------|-------------|--------------|
| Agricultural land density | `sentinel2_B04 + B08` | % pixels with NDVI > 0.2 in bounding box | 0.0 – 1.0 |
| Population proxy | `viirs_alquaa.tif` | Mean radiance, normalised by 100 nW/cm²/sr regional max | 0.0 – 1.0 |
| Road accessibility | `dem_alquaa.tif` + `osm_alquaa.geojson` | Slope-weighted cost-distance to nearest OSM paved road (scipy) | 0.0 – 1.0 (inverted) |
| Competition density | `osm_alquaa.geojson` | OSM POI count matching category tags, normalised by baseline | 0.0 – 1.0 (inverted) |
| Resource suitability | `sentinel2_B04 + B08` | % pixels in category-specific NDVI range | 0.0 – 1.0 |

### NDVI Formula

```python
# Computed in demand_engine.py — _compute_ndvi_density()
ndvi = (nir - red) / (nir + red + 1e-10)
# agricultural_density = fraction of valid pixels where ndvi > 0.2
```

### Demand Score Formula

```python
# Computed in demand_engine.py — compute_demand_score()
# Weights documented per-subcategory in config/weights.json
def compute_demand_score(signals, category_weights) -> int:
    raw = (
        category_weights["agricultural_density"] * signals["agricultural_density"]
      + category_weights["population_proxy"]       * signals["population_proxy"]
      + category_weights["road_accessibility"]     * signals["road_accessibility"]
      + category_weights["competition_penalty"]    * signals["competition_penalty"]
      + category_weights["resource_suitability"]   * signals["resource_suitability"]
    )
    # weights sum to 1.0 per category — see config/weights.json
    return int(np.clip(raw * 100, 0, 100))
```

Every weight in `config/weights.json` has a `_rationale` comment explaining why that signal is weighted that way for that subcategory. No magic numbers.

### Reproducibility Statement
```
Basira's demand scores are fully reproducible. Running:
python scripts/compute_demand.py --community alquaa
produces outputs/demand_scores_alquaa.json containing demand scores

for all 10 subcategories. Pre-computed results are committed to the

repository so judges see real numbers without running any code.
All source data acquisition dates, download sources, bounding boxes,

and processing scripts are documented in data/alquaa/README.md.
```
<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Data Sources

| File | Source | Dataset | Resolution | Acquired | Licence |
|------|--------|---------|------------|----------|---------|
| `sentinel2_B04_alquaa.tif` | Copernicus Data Space | Sentinel-2 L2A Band 4 (Red) | 10m | Jan–Mar 2025 | Copernicus Open Access |
| `sentinel2_B08_alquaa.tif` | Copernicus Data Space | Sentinel-2 L2A Band 8 (NIR) | 10m | Jan–Mar 2025 | Copernicus Open Access |
| `dem_alquaa.tif` | OpenTopography / NASA | NASADEM Global DEM | 30m | 2000, processed 2020 | NASA Open Data |
| `viirs_alquaa.tif` | NASA EarthData | VIIRS Black Marble VNP46A4 Annual | 500m | 2025 composite | NASA Open Data |
| `osm_alquaa.geojson` | OpenStreetMap / Overpass Turbo | Admin boundary + POIs + roads | Vector | June 2026 | ODbL |

All datasets are free, open, and require only attribution. No paid APIs. No proprietary data. No scraping.

**Bounding box used for all datasets:**
```
West:  54.775°E  |  South: 23.049°N
East:  55.484°E  |  North: 23.549°N
```
<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Classification System

Basira classifies business ideas into 3 macro groups and 10 subcategories using offline multilingual semantic similarity.

### Macro Groups

| ID | Arabic | English |
|----|--------|---------|
| 1 | اقتصاد الإنتاج | Production Economy |
| 2 | اقتصاد الخدمات | Service Economy |
| 3 | اقتصاد المجتمع والتجربة | Social & Experience Economy |

### Subcategories

| ID | Arabic | English | Key Signals |
|----|--------|---------|-------------|
| 1.1 | الموارد الأولية | Primary Resource | NDVI high, agricultural density, resource suitability |
| 1.2 | الإنتاج المنزلي | Home-Based Production | Population proxy, road accessibility |
| 1.3 | التصنيع الصغير | Micro Manufacturing | Road accessibility, competition gap |
| 2.1 | الخدمات الأساسية | Essential Local Services | Population proxy, competition gap |
| 2.2 | الخدمات الميدانية | Mobility & Field Services | Road accessibility, geographic spread |
| 2.3 | الخدمات المجتمعية | Community & Human Services | Population proxy, education/care POI gap |
| 2.4 | الخدمات المهنية | Professional Services | Population proxy, built-up density |
| 3.1 | التجزئة والتوزيع | Micro Retail & Distribution | Population proxy, competition gap, road access |
| 3.2 | الاقتصاد الاجتماعي | Social & Cultural Economy | Population proxy, community POI gap |
| 3.3 | السياحة والبيئة | Tourism & Environment | Terrain, VIIRS darkness, road access |

### Classification Engine

**Model:** `paraphrase-multilingual-MiniLM-L12-v2`  
**Method:** Cosine similarity against averaged seed phrase embeddings  
**Languages:** Arabic and English — auto-detected, no toggle needed  
**Inference:** CPU-only, < 1 second
Confidence ≥ 0.70  →  Proceed directly
Confidence 0.45–0.69  →  Show top 2, ask user to confirm
Confidence < 0.45  →  Show all 3 macro groups as options
<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Map Engine

The map is a **decision interface**, not a visualisation. Its primary function is to answer: *"Where in this community is the best location for this type of business?"*

### Five Layers

| Layer | Source | What it shows |
|-------|--------|---------------|
| NDVI Land Classification | Sentinel-2 B04 + B08 | Desert / sparse / agricultural / dense, colour-coded |
| Demand Heatmap | Pre-computed demand grid | Spatial intensity of demand signal for selected category |
| Opportunity Zones | Demand score > threshold | Filled polygons where score is high, Arabic-labelled |
| Infrastructure & POI | osm_alquaa.geojson | Roads, facilities, POIs — clustered markers, Arabic popups |
| Terrain (contextual) | NASADEM hillshade | Elevation context, toggled off by default |

Opportunity zones display inline tooltips in Arabic showing the local opportunity score and the top two contributing signals at that location.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Licence Engine

All UAE business licence pathways are stored in `config/licenses.json` — a local JSON file pre-populated from ADDED, TAMM, and DCT official sources. No internet required at runtime.

Coverage: all 10 subcategories, with licence type, issuing authority, cost range in AED, required documents, and numbered first steps — in both Arabic and English.

Example (Tourism, subcategory 3.3):
Authority:  Department of Culture & Tourism Abu Dhabi (DCT)
Cost range: AED 4,000 – 8,000
Documents:  UAE Emirates ID · Tourism business plan · Tour guide qualification · Safety certificates
Step 1:     تواصل مع هيئة أبوظبي للسياحة (DCT)
Step 2:     احصل على شهادة الدليل السياحي المعتمد
Step 3:     سجّل نشاطك في تمم
Step 4:     استفسر عن برامج دعم السياحة الصحراوية

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Explainability

Every demand score produces a human-readable Arabic (and English) explanation generated from the actual computed signal values — not a generic description. The explanation names the exact percentage of agricultural land, the road accessibility level, and the competitive landscape at the community's location.

```python
# From explainability.py — generate_explanation()
f"حصل مشروعك على مؤشر طلب {score}/100. "
f"المنطقة تحتوي على {int(agri * 100)}٪ أراضٍ ذات كثافة زراعية — "
f"إمكانية الوصول إلى الطرق المعبّدة {acc_label}. "
f"المنافسة في المنطقة {comp_label}، مما يعني فرصة سوقية {market_label}."
```

This explanation appears in three places: the map panel, the decision report, and the frontend results card.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 How to Run

### Prerequisites

- Python 3.10+
- ~2GB disk space for models
- Your data files in `data/alquaa/`

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Download models (one-time, ~500MB)

```bash
python -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
m.save('models/multilingual-minilm')
print('Classifier model saved.')
"

python -c "
from faster_whisper import WhisperModel
m = WhisperModel('small', device='cpu', compute_type='int8',
                  download_root='models/whisper-small')
print('Whisper model saved.')
"
```

### 3 — Verify data files

```bash
bash data_download.sh
```

### 4 — Pre-compute demand scores

```bash
python scripts/compute_demand.py --community alquaa
```

This writes `outputs/demand_scores_alquaa.json`. Pre-computed results are already committed — you can skip this step and verify the numbers yourself.

### 5 — Run

```bash
# Launch web UI (opens browser automatically)
python scripts/basira.py

# CLI — text input
python scripts/basira.py --text "أريد تربية الإبل وبيع الحليب"

# CLI — voice input (microphone)
python scripts/basira.py --voice

# Custom port
python scripts/basira.py --port 8080
```

Open **http://localhost:8000**

### One-line demo (after setup)

```bash
python scripts/basira.py --text "I want to guide tourists in the desert"
```

Expected output: subcategory `3.3` Tourism & Environment, map generated with VIIRS-informed opportunity zones, DCT licence pathway returned in < 8 seconds.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Scalability

No hardcoded geography anywhere in the codebase. Every community is defined by a single JSON config file. Adding a new community takes 30–60 minutes of data download and one config file — zero code changes.

```bash
# Deploy to any new community
python scripts/basira.py --community liwa
```

```json
// config/liwa.json — the only file needed
{
  "community_id": "liwa",
  "community_name_ar": "ليوا",
  "community_name_en": "Liwa",
  "center": [23.11, 53.77],
  "bbox": [22.90, 53.50, 23.30, 54.00],
  "sentinel2_b04": "data/liwa/sentinel2_B04_liwa.tif",
  "sentinel2_b08": "data/liwa/sentinel2_B08_liwa.tif",
  "dem_tile": "data/liwa/dem_liwa.tif",
  "viirs_tile": "data/liwa/viirs_liwa.tif",
  "osm_geojson": "data/liwa/osm_liwa.geojson"
}
```

The same config structure works for any rural community globally. Basira is not a UAE-specific product — it is a platform that happens to start in Al Qua'a.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Repository Structure
```
basira/
├── scripts/
│   ├── basira.py           # CLI entry point — text, voice, or web UI
│   ├── app.py              # FastAPI backend — /api/classify, /api/map, /api/voice
│   ├── classifier.py       # MiniLM classifier — cosine similarity, 10 categories
│   ├── demand_engine.py    # Satellite signal computation + weighted scoring
│   ├── explainability.py   # Arabic + English explanation generator
│   ├── license_engine.py   # Local JSON licence lookup
│   ├── map_engine.py       # Folium 5-layer map generator
│   ├── voice_input.py      # faster-whisper transcription + mic recording
│   ├── compute_demand.py   # Standalone pre-computation — run before first launch
│   └── i18n.py             # All UI strings AR + EN — no hardcoded strings in UI
│
├── config/
│   ├── alquaa.json         # Al Qua'a community — bbox, data paths, zoom
│   ├── weights.json        # Demand weights per subcategory — all rationale-commented
│   └── licenses.json       # UAE licence pathways — all 10 subcategories + default
│
├── data/
│   └── alquaa/             # All satellite and vector data for Al Qua'a
│       ├── README.md       # Full acquisition steps, dates, checksums
│       ├── sentinel2_B04_alquaa.tif
│       ├── sentinel2_B08_alquaa.tif
│       ├── dem_alquaa.tif
│       ├── viirs_alquaa.tif
│       └── osm_alquaa.geojson
│
├── outputs/                # Pre-committed — judges see real numbers immediately
│   ├── demand_scores_alquaa.json
│   ├── ndvi_classification.png
│   ├── basira_map_sample.html
│   └── terrain_hillshade.png
│
├── notebooks/
│   └── validation.ipynb    # Signal validation, NDVI visualisation, falsifiability
│
├── static/
│   └── index.html          # Arabic-first frontend — dark purple, RTL, voice input
│
├── README.md
├── SETUP.md
├── requirements.txt
└── data_download.sh
```
<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Arabic-first frontend UI |
| `POST` | `/api/classify` | Classify text input → demand score + explanation + licence |
| `POST` | `/api/voice` | Transcribe audio → classify → full result |
| `POST` | `/api/map` | Generate Folium map for subcategory + community |
| `GET` | `/map/{filename}` | Serve pre-generated map HTML |
| `GET` | `/api/communities` | List available community configs |
| `GET` | `/api/demand/{community_id}` | Return pre-computed demand scores |

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Design Principles

**Offline-first.** Every computation runs locally. After a one-time model download, Basira requires zero internet. This is not a nice-to-have — rural UAE connectivity is the exact problem context.

**Arabic-primary.** The interface, map panels, tooltips, explanations, and licence pathways are all Arabic-first with English as a secondary layer. Language detection is automatic. No toggle.

**Falsifiable.** Every demand score has a traceable computation path: named source file → named function → documented formula → committed output. Any claim in the system can be independently verified by running `compute_demand.py`.

**No magic numbers.** Every weight in `config/weights.json` has a written rationale. The formula is public. The data is public. The model is public. Nothing is hidden behind an API or a proprietary service.

**Scalable by design.** The community config system means every line of code written for Al Qua'a is reusable for Liwa, Madinat Zayed, Ghayathi, or any rural community anywhere in the world with satellite coverage — which is all of them.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Future Work

These are out of scope for the hackathon but architecturally ready:

- **Scenario comparison mode** — compare mobile vs fixed vs home-based business for the same idea
- **Digital & Remote Economy subcategory** — freelancing, e-commerce, remote services
- **Community onboarding CLI** — `python scripts/onboard.py --community [name]` automates data download and config generation for any location
- **Mobile-optimised UI** — the frontend is responsive but a dedicated PWA would suit field use better
- **Camel farming analytics module** — Al Qua'a-specific: integration of grazing range NDVI time series for livestock-specific demand intelligence

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

## 🟣 Data Licences

| Dataset | Licence | Commercial Use |
|---------|---------|----------------|
| OpenStreetMap | Open Database Licence (ODbL) | Yes, with attribution |
| Sentinel-2 | Copernicus Open Access Licence | Yes, with attribution |
| NASADEM | NASA Open Data Policy | Yes, with attribution |
| VIIRS Black Marble | NASA Open Data Policy | Yes, with attribution |

All datasets are free, open, and attribution-only. No API keys required at runtime except a free Copernicus account for initial data download.

<br/>

<div align="center"> 
━━━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━━━
</div>

<div align="center">

**Built for Tatweer Hackathon 2026 · Al Qua'a, Al Ain, UAE**  
*In collaboration with Abu Dhabi University*

<sub>Sentinel-2 · NASADEM · VIIRS Black Marble · OpenStreetMap · faster-whisper · Sentence Transformers · Folium · FastAPI</sub>

</div>
