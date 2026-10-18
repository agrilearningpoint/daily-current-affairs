# Source Registry — daily-current-affairs

Single canonical description of **which sources the production pipeline actually
fetches**, how they are layered, how a source is added or retired, and how to
prove a source is healthy.

* Registry loaded at runtime: `pipeline/source_registry.py::load_sources()`
* Config files that feed it: `config/feeds.py` and `config/sources.py`
* Health tool: `scripts/source_health.py`
* Last live verification: **2026-10-18** (see §6)

---

## 1. The one canonical registry

Historically three lists existed and could disagree:

| Layer | File | Role today |
| --- | --- | --- |
| Curated direct feeds | `config/feeds.py::VERIFIED_RSS` | 4 hand-verified feeds that must always work |
| Structured source set | `config/sources.py::ALL_SOURCES` | ~52 sources across 6 priority levels with metadata (tier, category, fallback, notes) |
| Legacy index | `config/registry.py::get_feed_urls()` | **existence-list only** — consumed by `scripts/diagnose.py`; not used by the collector |

The **runtime truth** is the merged, deduplicated view produced by
`pipeline.source_registry.load_sources()`:

```
VERIFIED_RSS  ─┐
               ├─►  dedupe by exact RSS URL  ─►  [SourceSpec, …]
ALL_SOURCES   ─┘
```

`SourceSpec` fields: `source_id`, `name`, `rss_url`, `tier`, `category`,
`official`, `enabled`.

> **Invariant:** the same publisher must never appear with two different RSS
> URLs. Because dedupe is by exact URL, two URLs means two fetches.
> Enforced by `tests/test_source_registry.py::test_verified_rss_and_all_sources_agree_on_shared_publishers`
> and `…::test_canonical_registry_loads_and_has_no_duplicate_rss_urls`.

---

## 2. Current registry (56 enabled sources)

Tier distribution: **tier 1 = 48, tier 2 = 6, tier 3 = 2**.

| Source | Category | Tier | Route | URL |
| --- | --- | --- | --- | --- |
| ICAR | agriculture | 1 | direct | `https://icar.org.in/rss.xml` |
| WHO News | health | 1 | direct | `https://www.who.int/rss-feeds/news-english.xml` |
| The Hindu National | national | 2 | direct | `https://www.thehindu.com/feeder/default.rss` |
| Indian Express | national | 2 | direct | `https://indianexpress.com/feed/` |
| PIB — Press Information Bureau | govt_national | 1 | direct | `https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3` |
| Ministry of Agriculture & Farmers Welfare | agriculture_core | 1 | gnews | `site:agriwelfare.gov.in` |
| RBI | banking_finance | 1 | gnews | `site:rbi.org.in` |
| NABARD | banking_finance | 1 | gnews | `site:nabard.org` |
| SEBI | banking_finance | 1 | gnews | `site:sebi.gov.in` |
| NITI Aayog | economy_data | 1 | direct | `https://www.niti.gov.in/rss.xml` |
| Ministry of Statistics and Programme Implementation | economy_data | 1 | gnews | `site:mospi.gov.in` |
| Ministry of External Affairs | international | 1 | gnews | `site:mea.gov.in` |
| India Meteorological Department | agriculture_core | 1 | gnews | `site:mausam.imd.gov.in` |
| Department of Animal Husbandry and Dairying | agriculture_core | 1 | gnews | `site:dahd.gov.in` |
| Department of Fisheries | agriculture_core | 1 | gnews | `site:dof.gov.in` |
| APEDA | agriculture_core | 1 | gnews | `site:apeda.gov.in` |
| Department of Agriculture Research and Education | agriculture_core | 1 | gnews | `site:dare.gov.in` |
| Indian Agricultural Research Institute | agriculture | 1 | gnews | `site:iari.res.in` |
| National Horticulture Board | horticulture | 1 | gnews | `site:nhb.gov.in` |
| FSSAI | food_safety | 1 | gnews | `site:fssai.gov.in` |
| ICFRE | forestry_environment | 1 | gnews | `site:icfre.gov.in` |
| Commission for Agricultural Costs and Prices | agriculture_economy | 1 | gnews | `site:pib.gov.in CACP` |
| Ministry of Food Processing Industries | food_processing | 1 | gnews | `site:mofpi.gov.in` |
| Ministry of Environment, Forest and Climate Change | environment | 1 | gnews | `site:moef.gov.in` |
| NPCI | banking_finance | 1 | gnews | `site:npci.org.in` |
| PFRDA | banking_finance | 1 | gnews | `site:pfrda.org.in` |
| IRDAI | banking_finance | 1 | gnews | `site:irdai.gov.in` |
| IFSCA | banking_finance | 1 | gnews | `site:ifsca.gov.in` |
| Department of Financial Services | banking_finance | 1 | gnews | `site:financialservices.gov.in` |
| Union Budget of India | economy_data | 1 | gnews | `site:indiabudget.gov.in` |
| GST Council | economy_data | 1 | gnews | `site:gstcouncil.gov.in` |
| Competition Commission of India | economy_data | 1 | gnews | `site:cci.gov.in` |
| RBI Bulletin | banking_finance | 1 | gnews | `site:bulletin.rbi.org.in` |
| India.gov.in | govt_national | 1 | gnews | `site:india.gov.in` |
| Prime Minister of India | govt_national | 1 | gnews | `site:pmindia.gov.in` |
| Cabinet Secretariat | govt_national | 1 | gnews | `site:cabsec.gov.in` |
| MyGov India | govt_national | 1 | gnews | `site:mygov.in` |
| Ministry of Rural Development | rural_development | 1 | gnews | `site:rural.gov.in` |
| Ministry of Cooperation | cooperation | 1 | gnews | `site:cooperation.gov.in` |
| Department of Science and Technology | science | 1 | gnews | `site:dst.gov.in` |
| Department of Biotechnology | science | 1 | gnews | `site:dbtindia.gov.in` |
| DRDO | defence_science | 1 | gnews | `site:drdo.gov.in` |
| Central Pollution Control Board | environment | 1 | gnews | `site:cpcb.nic.in` |
| Ministry of Education | education | 1 | gnews | `site:education.gov.in` |
| UGC | education | 1 | gnews | `site:ugc.gov.in` |
| National Testing Agency | education | 1 | gnews | `site:nta.ac.in` |
| Ministry of Defence | defence | 1 | gnews | `site:mod.gov.in` |
| President of India | govt_national | 1 | gnews | `site:presidentofindia.gov.in` |
| Election Commission of India | govt_national | 1 | gnews | `site:eci.gov.in` |
| UPSC | education | 1 | gnews | `site:upsc.gov.in` |
| Reuters | discovery | 2 | gnews | `site:reuters.com` |
| Business Standard | discovery | 2 | direct | `https://www.business-standard.com/rss/latest.rss` |
| Mint | discovery | 2 | direct | `https://www.livemint.com/rss/news` |
| Economic Times | discovery | 2 | direct | `https://economictimes.indiatimes.com/rssfeedsdefault.cms` |
| Google News India | aggregator | 3 | direct | Google News India top stories |
| Google News Search | aggregator | 3 | direct | `site:pib.gov.in when:1d` |

Category coverage: `agriculture`, `agriculture_core`, `agriculture_economy`,
`horticulture`, `food_safety`, `food_processing`, `forestry_environment`,
`environment`, `cooperation`, `rural_development`, `banking_finance`,
`economy_data`, `govt_national`, `national`, `international`, `defence`,
`defence_science`, `science`, `education`, `health`, `discovery`, `aggregator`.

---

## 3. `official` semantics (important)

`official = (tier == 1) and (feed host == publisher host)`.

Consequences you must not "fix" blindly:

* A PIB press release fetched from `pib.gov.in` is `official=True`.
* A SEBI circular found through `news.google.com` is `official=False` — even
  though SEBI is a government body. The **route**, not the publisher, is what is
  being graded.
* Non-official items still need corroboration downstream (claim verification),
  so routing through Google News is the *conservative* choice.

---

## 4. Adding a source

1. Prefer the publisher's own RSS. Probe it first:

   ```powershell
   python scripts/source_health.py            # offline registry invariants
   # or probe a single URL:
   python -c "import requests,feedparser;r=requests.get('URL',timeout=15);p=feedparser.parse(r.content);print(r.status_code, r.headers.get('content-type'), len(p.entries), p.bozo)"
   ```

   A URL is only usable if it returns XML with `bozo == 0` and `entries > 0`.
   An HTML page with HTTP 200 is **not** a feed (this is how PIB/SEBI/MEA were
   silently broken).
2. Add it to `config/sources.py::ALL_SOURCES` with a level, category and a
   `notes=` line recording the probe date and result.
3. If it duplicates a `VERIFIED_RSS` publisher, use the **identical URL string**.
4. Run `pytest tests/test_source_registry.py -q` — the duplicate-URL and
   shared-publisher invariants must stay green.
5. Run `python scripts/source_health.py --live` and paste the result into the PR.

## 5. Retiring a source

Delete the `_source(...)` entry. Do **not** leave it commented out — a commented
entry is how duplicate/conflicting lists were able to grow in the first place.
Re-run the registry tests.

---

## 6. Health tooling

`scripts/source_health.py` — read-only, no Telegram, no writes.

```powershell
python scripts/source_health.py                 # offline: load + invariants (exit 1 on duplicates)
python scripts/source_health.py --live          # probe every source (exit 1 if zero usable)
python scripts/source_health.py --live --json   # machine-readable
```

Exit codes: `0` healthy, `1` configuration defect (duplicate URLs) **or** zero
usable sources in `--live` mode.

`scripts/diagnose.py` check **[10]** additionally loads the canonical registry and
fails the report if duplicate RSS URLs are present.

### Live verification 2026-10-18 (direct feeds)

```
200 entries= 10 bozo=0  ICAR
200 entries=173 bozo=0  WHO News
200 entries= 60 bozo=0  The Hindu National
200 entries=200 bozo=0  Indian Express
200 entries= 20 bozo=0  PIB — Press Information Bureau   (RssMain.aspx)
200 entries= 10 bozo=0  NITI Aayog
200 entries=100 bozo=0  Business Standard
200 entries= 35 bozo=0  Mint
200 entries= 76 bozo=0  Economic Times
```

Google News site-search route was smoke-tested with `site:reuters.com`:
HTTP 200, parseable XML, 100 items. **The remaining site-search URLs were not
all individually live-probed** in this pass; use `python scripts/source_health.py
--live` for a complete point-in-time sweep before a production launch.

### Defects fixed as a result of this tool

| Source | Was | Now |
| --- | --- | --- |
| The Hindu | two different URLs in `feeds.py` vs `sources.py` → fetched twice | one URL |
| PIB | `ViewRss.aspx` (HTML, 0 entries) | `RssMain.aspx` (XML, 20 entries) |
| SEBI | `rss.html` (HTML, 0 entries) | Google News site-search |
| MEA | `rss-feeds.htm` (HTML, 0 entries) | Google News site-search |
| Reuters | `reutersagency.com` tech feed (HTTP 404) | Google News site-search |

---

## 7. What is *not* claimed

* Google News is a **discovery** route, never primary evidence. A story routed
  through it still needs an original source before it is treated as verified.
* Feed health is a point-in-time observation. A feed that worked on 2026-10-18
  can break; that is exactly why `scripts/source_health.py --live` exists and
  why `notes=` fields carry probe dates.
