import json
import sys, os
import asyncio
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from scripts.classifier import classify, preload as preload_classifier
from scripts.demand_engine import load_demand_scores
from scripts.explainability import generate_full_explanation
from scripts.license_engine import get_license
from scripts.map_engine import generate_map
from scripts.voice_input import transcribe_bytes, preload as preload_whisper
from scripts.b_i18n import STRINGS

CONFIG_DIR = "config"
OUTPUTS_DIR = "outputs"

app = FastAPI(title="Basira | بصيرة", version="2.0")

_community_configs: dict = {}
_demand_cache: dict = {}


def _load_community(community_id: str) -> dict:
    if community_id not in _community_configs:
        path = os.path.join(CONFIG_DIR, f"{community_id}.json")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Community config not found: {community_id}")
        with open(path, "r", encoding="utf-8") as f:
            _community_configs[community_id] = json.load(f)
    return _community_configs[community_id]


def _get_demand(community_id: str) -> dict:
    if community_id not in _demand_cache:
        _demand_cache[community_id] = load_demand_scores(community_id)
    return _demand_cache[community_id]


@app.on_event("startup")
async def startup():
    print("[basira] Preloading classifier...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, preload_classifier)
    print("[basira] Classifier ready.")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join("static", "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/classify")
async def api_classify(
    text: str = Form(...),
    community_id: str = Form(default="alquaa"),
    lang: str = Form(default="ar"),
):
    community = _load_community(community_id)
    result = classify(text)
    demand = _get_demand(community_id)

    subcat = result["subcategory"]
    demand_data = demand.get(subcat, {})
    signals = demand_data.get("signals", {})
    signals["demand_score"] = demand_data.get("demand_score", 0)

    explanation = generate_full_explanation(signals, subcat)
    license_info = get_license(subcat)

    macro_id = result["macro_group"]

    return JSONResponse({
        "status": "ok",
        "input_text": text,
        "subcategory": subcat,
        "macro_group": macro_id,
        "subcategory_ar": STRINGS["subcategories"][subcat]["ar"],
        "subcategory_en": STRINGS["subcategories"][subcat]["en"],
        "macro_group_ar": STRINGS["macro_groups"][macro_id]["ar"],
        "macro_group_en": STRINGS["macro_groups"][macro_id]["en"],
        "confidence": result["confidence"],
        "confidence_level": result["confidence_level"],
        "top2": [{"cat": c, "score": round(s, 3)} for c, s in result["top2"]],
        "demand_score": signals.get("demand_score", 0),
        "signals": signals,
        "explanation": explanation,
        "license": license_info,
        "community": {
            "id": community_id,
            "name_ar": community.get("community_name_ar"),
            "name_en": community.get("community_name_en"),
        }
    })


@app.post("/api/voice")
async def api_voice(
    audio: UploadFile = File(...),
    community_id: str = Form(default="alquaa"),
):
    audio_bytes = await audio.read()
    suffix = os.path.splitext(audio.filename or ".wav")[1] or ".wav"
    text, detected_lang = transcribe_bytes(audio_bytes, suffix=suffix)
    if not text:
        raise HTTPException(status_code=422, detail="Could not transcribe audio.")
    result = classify(text)
    demand = _get_demand(community_id)
    subcat = result["subcategory"]
    demand_data = demand.get(subcat, {})
    signals = demand_data.get("signals", {})
    signals["demand_score"] = demand_data.get("demand_score", 0)
    explanation = generate_full_explanation(signals, subcat)
    license_info = get_license(subcat)
    macro_id = result["macro_group"]

    return JSONResponse({
        "status": "ok",
        "transcript": text,
        "detected_language": detected_lang,
        "subcategory": subcat,
        "macro_group": macro_id,
        "subcategory_ar": STRINGS["subcategories"][subcat]["ar"],
        "subcategory_en": STRINGS["subcategories"][subcat]["en"],
        "macro_group_ar": STRINGS["macro_groups"][macro_id]["ar"],
        "macro_group_en": STRINGS["macro_groups"][macro_id]["en"],
        "confidence": result["confidence"],
        "confidence_level": result["confidence_level"],
        "demand_score": signals.get("demand_score", 0),
        "signals": signals,
        "explanation": explanation,
        "license": license_info,
    })


@app.post("/api/map")
async def api_map(
    subcategory: str = Form(...),
    community_id: str = Form(default="alquaa"),
):
    community = _load_community(community_id)
    demand = _get_demand(community_id)
    demand_data = demand.get(subcategory, {})
    signals = demand_data.get("signals", {})
    signals["demand_score"] = demand_data.get("demand_score", 0)
    explanation = generate_full_explanation(signals, subcategory)
    out_path = os.path.join(OUTPUTS_DIR, f"basira_map_{community_id}_{subcategory.replace('.','_')}.html")
    map_path = generate_map(community, subcategory, signals, explanation["ar"], output_path=out_path)
    return JSONResponse({"status": "ok", "map_path": map_path, "map_url": f"/map/{os.path.basename(map_path)}"})


@app.get("/map/{filename}", response_class=HTMLResponse)
async def serve_map(filename: str):
    path = os.path.join(OUTPUTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Map not found")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/communities")
async def list_communities():
    configs = []
    for fn in os.listdir(CONFIG_DIR):
        if fn.endswith(".json") and fn not in ("weights.json", "licenses.json"):
            with open(os.path.join(CONFIG_DIR, fn), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            configs.append({
                "id": cfg.get("community_id"),
                "name_ar": cfg.get("community_name_ar"),
                "name_en": cfg.get("community_name_en"),
            })
    return JSONResponse(configs)


@app.get("/api/demand/{community_id}")
async def api_demand(community_id: str):
    try:
        demand = _get_demand(community_id)
        return JSONResponse(demand)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)