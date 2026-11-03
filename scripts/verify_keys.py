"""Verify repo secrets without printing their values. Prints name, status, short reason."""
import json, os, urllib.request, urllib.error

S = json.loads(os.environ.get("ALL_SECRETS", "{}"))
S.pop("github_token", None)
print("SECRET NAMES:", ", ".join(sorted(S)))


def req(url, data=None, headers=None, method=None, timeout=40):
    h = {"User-Agent": "verify-keys/1.0"}
    h.update(headers or {})
    body = json.dumps(data).encode() if data is not None else None
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(600).decode("utf-8", "replace")
    except Exception as e:  # noqa
        return 0, f"{type(e).__name__}: {e}"


def short(t):
    t = " ".join(str(t).split())
    for v in S.values():
        if v and len(v) > 6:
            t = t.replace(v, "***")
    return t[:220]


def chat_oai(base, key, model, extra=None):
    h = {"Authorization": f"Bearer {key}"}
    h.update(extra or {})
    return req(f"{base}/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Reply with OK"}], "max_tokens": 20}, h)


results = []


def rec(name, code, body, ok_codes=(200,)):
    status = "OK" if code in ok_codes else "FAIL"
    results.append((name, status, code, "" if status == "OK" else short(body)))


def g(*names):
    for n in names:
        if S.get(n):
            return S[n]
    return None


tested = set()

k = g("GEMINI_API_KEY", "GOOGLE_API_KEY"); tested |= {"GEMINI_API_KEY", "GOOGLE_API_KEY"}
if k:
    for m in ("gemini-3.5-flash-lite", "gemini-2.5-flash-lite"):
        c, b = req(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                   {"contents": [{"parts": [{"text": "Reply with OK"}]}]}, {"x-goog-api-key": k})
        rec(f"GEMINI ({m})", c, b)

k = g("GROQ_API_KEY"); tested.add("GROQ_API_KEY")
if k:
    for m in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"):
        c, b = chat_oai("https://api.groq.com/openai/v1", k, m); rec(f"GROQ ({m})", c, b)

k = g("MISTRAL_API_KEY"); tested.add("MISTRAL_API_KEY")
if k:
    c, b = chat_oai("https://api.mistral.ai/v1", k, "mistral-small-latest"); rec("MISTRAL", c, b)

k = g("NVIDIA_API_KEY"); tested.add("NVIDIA_API_KEY")
if k:
    c, b = req("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {k}"}); rec("NVIDIA (models list)", c, b)
    c, b = chat_oai("https://integrate.api.nvidia.com/v1", k, "meta/llama-3.1-8b-instruct"); rec("NVIDIA (chat llama-3.1-8b)", c, b)

k = g("OPENROUTER_API_KEY"); tested.add("OPENROUTER_API_KEY")
if k:
    c, b = req("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {k}"})
    try:
        d = json.loads(b).get("data", {})
        info = f"usage={d.get('usage')} limit={d.get('limit')} free_tier={d.get('is_free_tier')}"
    except Exception:
        info = b
    results.append(("OPENROUTER (key info)", "OK" if c == 200 else "FAIL", c, short(info)))
    c, b = chat_oai("https://openrouter.ai/api/v1", k, "google/gemma-4-26b-a4b-it:free"); rec("OPENROUTER (gemma free chat)", c, b)

k = g("OLLAMA_API_KEY"); tested.add("OLLAMA_API_KEY")
if k:
    c, b = req("https://ollama.com/api/chat", {"model": "gpt-oss:20b", "messages": [{"role": "user", "content": "Reply with OK"}], "stream": False},
               {"Authorization": f"Bearer {k}"}, timeout=60)
    rec("OLLAMA cloud (gpt-oss:20b)", c, b)

k = g("DEEPSEEK_API_KEY"); tested.add("DEEPSEEK_API_KEY")
if k:
    c, b = req("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {k}"})
    try:
        d = json.loads(b); info = f"is_available={d.get('is_available')} balance={[x.get('total_balance')+' '+x.get('currency') for x in d.get('balance_infos', [])]}"
    except Exception:
        info = b
    results.append(("DEEPSEEK (balance)", "OK" if c == 200 else "FAIL", c, short(info)))

k = g("SAMBANOVA_API_KEY"); tested.add("SAMBANOVA_API_KEY")
if k:
    for m in ("gpt-oss-120b", "Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3.1"):
        c, b = chat_oai("https://api.sambanova.ai/v1", k, m); rec(f"SAMBANOVA ({m})", c, b)

tok = g("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_TOKEN"); acc = g("CLOUDFLARE_ACCOUNT_ID")
tested |= {"CLOUDFLARE_API_TOKEN", "CLOUDFLARE_TOKEN", "CLOUDFLARE_ACCOUNT_ID"}
if tok:
    c, b = req("https://api.cloudflare.com/client/v4/user/tokens/verify", headers={"Authorization": f"Bearer {tok}"})
    rec("CLOUDFLARE (token verify)", c, b)
    if acc:
        for m in ("@cf/meta/llama-3.3-70b-instruct-fp8-fast", "@cf/openai/gpt-oss-120b"):
            c, b = chat_oai(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/v1", tok, m); rec(f"CLOUDFLARE AI ({m})", c, b)
    else:
        results.append(("CLOUDFLARE AI", "SKIP", 0, "CLOUDFLARE_ACCOUNT_ID missing"))

k = g("COHERE_API_KEY", "CO_API_KEY"); tested |= {"COHERE_API_KEY", "CO_API_KEY"}
if k:
    c, b = req("https://api.cohere.com/v2/chat", {"model": "command-r7b-12-2024", "messages": [{"role": "user", "content": "Reply with OK"}]},
               {"Authorization": f"Bearer {k}"}); rec("COHERE", c, b)

k = g("CEREBRAS_API_KEY"); tested.add("CEREBRAS_API_KEY")
if k:
    c, b = chat_oai("https://api.cerebras.ai/v1", k, "gpt-oss-120b"); rec("CEREBRAS", c, b)

k = g("SARVAM_API_KEY"); tested.add("SARVAM_API_KEY")
if k:
    c, b = req("https://api.sarvam.ai/translate", {"input": "Hello", "source_language_code": "en-IN", "target_language_code": "hi-IN"},
               {"api-subscription-key": k}); rec("SARVAM (translate)", c, b)

k = g("HF_TOKEN", "HUGGINGFACE_API_KEY", "HF_API_KEY"); tested |= {"HF_TOKEN", "HUGGINGFACE_API_KEY", "HF_API_KEY"}
if k:
    c, b = req("https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {k}"}); rec("HUGGINGFACE (whoami)", c, b)

k = g("ZHIPU_API_KEY", "ZAI_API_KEY", "GLM_API_KEY"); tested |= {"ZHIPU_API_KEY", "ZAI_API_KEY", "GLM_API_KEY"}
if k:
    c, b = chat_oai("https://open.bigmodel.cn/api/paas/v4", k, "glm-4-flash-250414"); rec("ZHIPU GLM", c, b)

k = g("OPENAI_API_KEY", "LLM_API_KEY"); tested |= {"OPENAI_API_KEY", "LLM_API_KEY"}
if k:
    c, b = req("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {k}"}); rec("OPENAI (models)", c, b)

k = g("JINA_API_KEY"); tested.add("JINA_API_KEY")
if k:
    c, b = req("https://r.jina.ai/https://example.com", headers={"Authorization": f"Bearer {k}"}); rec("JINA reader", c, b)

k = g("NEWSDATA_API_KEY"); tested.add("NEWSDATA_API_KEY")
if k:
    c, b = req(f"https://newsdata.io/api/1/latest?apikey={k}&country=in&language=en"); rec("NEWSDATA", c, b)

k = g("TELEGRAM_BOT_TOKEN"); tested.add("TELEGRAM_BOT_TOKEN")
if k:
    c, b = req(f"https://api.telegram.org/bot{k}/getMe"); rec("TELEGRAM bot getMe", c, b)
    for cid_name in ("TELEGRAM_CHAT_ID", "TELEGRAM_CHANNEL_ID", "ADMIN_ID"):
        tested.add(cid_name)
        if S.get(cid_name):
            c, b = req(f"https://api.telegram.org/bot{k}/getChat?chat_id={S[cid_name]}")
            title = ""
            try:
                r = json.loads(b).get("result", {}); title = f"type={r.get('type')} title={r.get('title') or r.get('first_name')}"
            except Exception:
                pass
            results.append((f"TELEGRAM getChat {cid_name}", "OK" if c == 200 else "FAIL", c, short(title if c == 200 else b)))

print("\nRESULTS")
for r in results:
    print("RESULT |", " | ".join(str(x) for x in r))
untested = sorted(n for n in S if n not in tested)
print("UNTESTED (present, no test):", ", ".join(untested) or "-")
