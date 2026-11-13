# Deployment & GitHub Actions Configuration Guide

## 1. Applying the Enterprise Upgrade
Extract `agri_learning_point_enterprise_v2.zip` into the root of your cloned `daily-current-affairs` repository and run:
```powershell
python deploy_enterprise_v2.py
git add .
git commit -m "feat(enterprise): autonomous zero-error news, 16-format MCQ, per-key router & self-healer"
git push origin main
```

## 2. GitHub Repository Secrets
Configure in **Settings -> Secrets and variables -> Actions**:
- **Required for Telegram Delivery**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ADMIN_ID`
- **LLM Key Pool (Free-tier compatible)**: `GEMINI_API_KEY`, `GEMINI_API_KEY_1`..`7`, `GROQ_API_KEY`, `GROQ_API_KEY_1`..`2`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`
- **Optional Discovery Boosters**: `SERPER_API_KEY`, `GNEWS_API_KEY`, `NEWSDATA_API_KEY`, `JINA_API_KEY`
