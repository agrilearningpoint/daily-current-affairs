# AGRI LEARNING POINT — DAILY CURRENT AFFAIRS AUTOMATION
**Bilingual • Mobile-First • Exam-Oriented • 24-Agent Pipeline**

> **Master Rule:** Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content.

---

## 🚀 FINAL AGENT SETUP — 24 AGENTS

### 1. 🎯 MASTER SUPERVISOR
> Manage the complete Current Affairs pipeline. Execute each stage in correct order, track job status, prevent duplicate, retry failed, resume from last success, never publish incomplete.

`START → COLLECT → VERIFY → RANK → SELECT → WRITE → MCQ → PDF → QA → TELEGRAM → PIN → COMPLETE`

### 2. ⏰ SCHEDULER
> Create and trigger Daily, Weekly, Monthly jobs using Asia/Kolkata. Daily=previous 24h, Weekly=previous 7 days, Monthly=complete month. Never duplicate.

### 3. 🌐 NEWS COLLECTION
> Collect from reliable/primary sources. Prioritize Agriculture, Banking, Govt, Economy, National, International, Science, Environment, Awards... Capture headline, time, source, URL, category, raw facts. Collect broadly; do not decide importance.

### 4. 🔎 FACT VERIFICATION
> Verify every item via primary/authoritative sources. Verify dates, numbers, names, orgs, schemes, rankings, appointments, locations. Reject unsupported. Never guess.

### 5. 🧹 DEDUPLICATION
> Identify and merge same event across sources. Preserve strongest source. Separate only when genuinely different.

### 6. 🧠 NEWS IMPORTANCE (0-100)
> Score 0-100 for overall importance: national significance, govt importance, economic impact, agri/banking relevance, exam potential, future relevance, static value, uniqueness, source reliability. Not just trending.

### 7. 🎓 STUDENT RELEVANCE ⭐
> Act as expert editor for AGTA/AFO/NABARD/FCI/ICAR/IBPS AFO. Judge worth of limited study time. Prioritize direct/conceptual MCQ potential. Reject low exam value. Q: "If student has limited time, should they read this?"

### 8. 🌾 AGRICULTURE EXPERT
> For AGTA/AFO/NABARD/FCI/ICAR. Prioritize schemes, MSP, crops, varieties, ICAR/IARI, horticulture, AH, fisheries, forestry, soil, irrigation, seeds, fertilizers, agri econ, food processing, exports, cooperatives, agri-tech, weather.

### 9. 🏦 BANKING & FINANCE EXPERT
> For NABARD/AFO/IBPS. Prioritize RBI, NABARD, SEBI, NPCI, monetary policy, financial inclusion, banking schemes, digital payments, reports, indices, appointments, stats. Reject noise.

### 10. ⭐ FINAL NEWS SELECTION
> Select only highest-value. Combine importance, exam relevance, agri/banking relevance, factual value, MCQ potential, uniqueness, source reliability. No fixed count. Quality > Quantity.

### 11. 📈 IMPORTANCE MEMORY
> Track importance over time. Increase priority when event gains significance. Use historical for Weekly/Monthly. Not repeat same unless new development.

### 12. ✍️ CONTENT EDITOR
> Convert selected verified news to concise exam-oriented: Headline → Key Points → Static Facts → Exam Fact → Explanation.

### 13. 🌐 BILINGUAL EDITOR
> Hindi + English same facts/numbers/names/dates. Keep English exam terms, make Hindi natural student-friendly. Hindi=Mukta, English=Poppins.

### 14. 🇬🇧 ENGLISH EDITOR
> English-only from same verified DB, no factual alteration.

### 15. 🖼️ IMAGE AGENT
> Only when improves understanding. Prefer official/reliable. Verify represents event/person/place. Never random stock.

### 16. ❓ MCQ GENERATOR
> High-quality MCQs only from verified selected. Prioritize direct, conceptual, statement-based, static-linked for AGTA/AFO/NABARD/FCI/ICAR.

### 17. 🧪 MCQ VALIDATOR
> Validate clarity, option uniqueness, correct answer, explanation, accuracy, source support, ambiguity, duplicate, relevance. Reject/regenerate if multiple answers.

### 18. 🎨 PDF DESIGN
> Clean, colorful, highly readable, mobile-friendly. Controlled colors, clear hierarchy, attractive headings, proper spacing. Every page branding/logo/footer/page number. Never overcrowd or alter facts.

### 19. 🔍 PDF QA
> Check missing text, broken Hindi (Mukta), font rendering, dates, duplicates, images, overflow, blank pages, headers/footers, page numbers, MCQ mismatch, bilingual inconsistency. Reject if critical error.

### 20. 📅 WEEKLY EDITOR ⭐
> Review week, fresh Best-of-Week. Re-rank via cumulative importance, exam/agri/banking relevance, uniqueness, developments. Deduplicate. Not combine daily PDFs.

### 21. 📆 MONTHLY EDITOR ⭐
> Review month, fresh Best-of-Month. Re-rank via month-long significance, policy impact, repeated developments, static value, future potential. Not merge.

### 22. 📤 TELEGRAM PUBLISHER
> Publish only QA-approved to Telegram group `-1004485392227` (private). Correct caption, date, filename. Never draft/failed/duplicate.

### 23. 📌 PIN VERIFIER
> Verify pinned. Retry if fails. Never mark complete until publish+pin succeed.

### 24. 🚨 WATCHDOG / RECOVERY
> Monitor every job, detect timeout/stalled/API failure/invalid output, retry exponential backoff, resume from last checkpoint, escalate clear alert to @Agrikrishna (1138783169). Never silently stop.

**Common Master Rule:** Student Value First...

**Flow:**
```
SCHEDULER → COLLECTOR → VERIFIER → DEDUP → IMPORTANCE → STUDENT → AGRI ─┐
                                                                   ├──→ FINAL SELECTOR → CONTENT → BILINGUAL/ENGLISH → MCQ → VALIDATOR → IMAGE → PDF DESIGN → QA → PUBLISH → PIN → COMPLETE
                                                            BANKING ─┘
WATCHDOG → MONITOR → RETRY → RECOVER → ALERT
```

**Architecture:** Same database, different selection: Daily="Aaj kya zaroor?", Weekly="Is saptah sabse mahatvapurna?", Monthly="Is mahine sabse mahatvapurna?" — Fresh AI editorial, not PDF merging. Like Horizon/SmartReader.

---

## 🌟 SOURCE TIERS

**Tier-1 PRIMARY (100):** PIB (nodal + backgrounders/factsheets), India.gov.in, MyGov, PM India, Cabinet, Agri Ministry, ICAR (full ecosystem), IARI, DARE, APEDA, NHB, FSSAI, DAHD, Fisheries, ICFRE, IMD, CACP, RBI, NABARD, SEBI, FinMin, DEA, Financial Services, NPCI, PFRDA, IRDAI, IFSCA, MoSPI, Economic Survey, Budget, NITI Aayog, UN/UN News/FAO/World Bank/IMF/WTO/WHO/UNESCO/UNEP/UNDP/ILO/UNFCCC/IEA, Ministries (Rural/Cooperation/Food Processing/Consumer Affairs/DST/ISRO/DBT/DRDO/MoEFCC/CPCB/Education/UGC/NTA/Defence/MEA), Rashtrapati/PMO/ECI/UPSC

**Tier-2 DISCOVERY (80-90):** Reuters, The Hindu, Indian Express, Business Standard, Mint, Economic Times

**Tier-3 AGGREGATORS (60):** Google News, GDELT, NewsAPI

**Score:** Official 100 | International 100 | Regulator 95 | Reuters 90 | Major Newspaper 80 | Aggregator 60

**Top 10 Core:** PIB, Agri Ministry, ICAR, IARI, RBI, NABARD, SEBI, MoSPI, NITI Aayog, MEA

---

## 🎨 PDF DESIGN SPEC

**Fonts:** Hindi → Mukta (Regular/Bold/SemiBold), English → Poppins/Inter (Regular/Bold/SemiBold), **Max 2 families**

**Hierarchy:**
- Main title 18-20pt Bold, Hindi headline 17-19pt Bold (Mukta), Section 15-17pt (16pt), Sub-heading 13-14pt Semi, Body 11.5-12.5pt (Poppins 12pt / Mukta 12.5pt), Static 11.5-12pt, Exam Fact 12-13pt Bold, MCQ Q 12-13pt (12.5pt), Options 11.5-12pt, Explanation 11-12pt, Footer 8.5-9.5pt (9pt), Watermark 8-10pt very subtle (0.09 alpha, PAID BATCHES logo 90mm centered)

**Line spacing 1.25-1.35, Single-column mobile-first, Margins 12-15mm (actual 13mm), Max useful info + readability, No orphan heading, Smart page fill, Tables compact mobile-readable, Colors controlled (Agri Green, Banking Blue, National Orange, etc.), Header compact, Footer compact, Watermark every page, Double border Red+Green, No blank/or orphan/tiny text.**

**Previous best colors kept as final.**

---

## ⚙️ DEPLOYMENT

- **GitHub:** `agrilearningpoint/daily-current-affairs`
- **Workflows:** `daily.yml` (00:30 UTC = 06:00 IST daily), `weekly.yml` (Sunday), `monthly.yml` (last date)
- **Secrets:** `TELEGRAM_BOT_TOKEN`, `ADMIN_ID=1138783169`, `CLOUDFLARE_TOKEN`
- **Telegram:** Private group `-1004485392227` (CURRENT AFFAIRS WORLD) — Daily + Weekly (Sun) + Monthly (last date) + auto-pin, storage delete after monthly (GitHub/R2 only, group keeps all)
- **Fonts:** `src/fonts/Mukta-*.ttf` + `Poppins-*.ttf`
- **Watermark:** `assets/watermark_logo.png` (PAID BATCHES logo)

## 📱 MOBILE PDF
21 pages, 3.7MB, 18pt headline / 12.5pt Hindi / 13mm margin, 20 one-liners spaced, single-column, premium book-like, not AI.

---

## 🔧 Run Locally
```bash
pip install -r requirements.txt
python main.py --type daily --date 2026-10-04
python main.py --type weekly --date 2026-10-05
python main.py --type monthly --date 2026-10-31
```
