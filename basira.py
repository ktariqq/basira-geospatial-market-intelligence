#!/usr/bin/env python3
"""
Basira — offline CLI entry point.
Usage:
  python basira.py --community alquaa --text "أريد تربية الإبل"
  python basira.py --community alquaa --voice
  python basira.py --community alquaa  # launches web UI
"""
import argparse
import json
import os
import sys
import webbrowser

CONFIG_DIR = "config"


def _load_community(community_id: str) -> dict:
    path = os.path.join(CONFIG_DIR, f"{community_id}.json")
    if not os.path.exists(path):
        print(f"[ERROR] Community config not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_pipeline(text: str, community_id: str, open_map: bool = True):
    from scripts.classifier import classify
    from scripts.demand_engine import load_demand_scores
    from scripts.explainability import generate_full_explanation
    from scripts.license_engine import get_license
    from scripts.map_engine import generate_map
    from scripts.b_i18n import STRINGS

    community = _load_community(community_id)

    print(f"\n[basira] Input: {text}")
    result = classify(text)
    subcat = result["subcategory"]
    macro_id = result["macro_group"]
    conf = result["confidence"]
    level = result["confidence_level"]

    print(f"[basira] Classification: {subcat} — {STRINGS['subcategories'][subcat]['ar']} ({STRINGS['subcategories'][subcat]['en']})")
    print(f"[basira] Macro group:    {macro_id} — {STRINGS['macro_groups'][macro_id]['ar']}")
    print(f"[basira] Confidence:     {conf:.0%} ({level})")

    if level == "medium":
        top2 = result["top2"]
        print(f"\n[basira] Medium confidence. Top 2 matches:")
        for cat, sc in top2:
            print(f"  {cat}: {STRINGS['subcategories'][cat]['ar']} ({sc:.0%})")

    demand = load_demand_scores(community_id)
    demand_data = demand.get(subcat, {})
    signals = demand_data.get("signals", {})
    signals["demand_score"] = demand_data.get("demand_score", 0)

    explanation = generate_full_explanation(signals, subcat)
    license_info = get_license(subcat)

    print(f"\n[basira] Demand score: {signals['demand_score']}/100")
    print(f"[basira] Explanation (AR): {explanation['ar']}")
    print(f"[basira] Explanation (EN): {explanation['en']}")
    print(f"\n[basira] License: {license_info.get('license_type_en', 'N/A')}")
    print(f"[basira] Authority: {license_info.get('authority_en', 'N/A')}")
    print(f"[basira] Cost: AED {license_info.get('cost_range_aed', 'N/A')}")

    out_path = os.path.join("outputs", f"basira_map_{community_id}_{subcat.replace('.','_')}.html")
    print(f"\n[basira] Generating map → {out_path}")
    map_path = generate_map(community, subcat, signals, explanation["ar"], output_path=out_path)
    print(f"[basira] Map saved: {map_path}")

    if open_map:
        webbrowser.open(f"file://{os.path.abspath(map_path)}")


def main():
    parser = argparse.ArgumentParser(description="Basira | بصيرة — Offline Rural Economic Intelligence")
    parser.add_argument("--community", default="alquaa", help="Community ID")
    parser.add_argument("--text", default=None, help="Input text (Arabic or English)")
    parser.add_argument("--voice", action="store_true", help="Use microphone input")
    parser.add_argument("--web", action="store_true", help="Launch web UI (default if no text/voice)")
    parser.add_argument("--port", type=int, default=8000, help="Web UI port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    if args.voice:
        from scripts.voice_input import record_and_transcribe
        print("[basira] Recording voice input...")
        text, lang = record_and_transcribe(duration_seconds=7)
        if not text:
            print("[ERROR] Could not transcribe audio.")
            sys.exit(1)
        print(f"[basira] Transcribed ({lang}): {text}")
        _run_pipeline(text, args.community, open_map=not args.no_browser)

    elif args.text:
        _run_pipeline(args.text, args.community, open_map=not args.no_browser)

    else:
        # Launch web UI
        import uvicorn
        print(f"[basira] Starting web UI at http://localhost:{args.port}")
        if not args.no_browser:
            import threading, time
            def _open():
                time.sleep(1.5)
                webbrowser.open(f"http://localhost:{args.port}")
            threading.Thread(target=_open, daemon=True).start()
        uvicorn.run("app:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    main()