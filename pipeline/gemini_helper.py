# GK-Parchi style self-healing Gemini
import os, requests
MODEL_CANDIDATES = ["gemini-flash-latest","gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash"]
def get_available_models(api_key):
    try:
        r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}", timeout=15)
        r.raise_for_status()
        return [m["name"].replace("models/","") for m in r.json().get("models",[]) if "generateContent" in m.get("supportedGenerationMethods",[])]
    except: return []
def call_gemini(prompt, api_key):
    live = get_available_models(api_key)
    order = live + [m for m in MODEL_CANDIDATES if m not in live]
    for model in order:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            resp = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=45)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip(), model
        except Exception as e: print(f"Model {model} fail: {e}"); continue
    raise RuntimeError("All Gemini models failed")
