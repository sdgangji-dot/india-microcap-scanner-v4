# India Mutual Fund Historical Institutional Accumulation & Value Research Scanner (v3.0 — SQLite `mf_history.db` + Web App)

This guide provides the complete setup for running a **Historical Institutional Accumulation, Exit & Value Research Rating System** across India's Top 25 Mutual Funds (AMCs), backed by a persistent **SQLite Data Warehouse (`mf_history.db`)**, automated daily/monthly Python pipelines, and a self-contained **Interactive Web App (`india_mf_micro_smallcap_sep2026_dashboard.html`)** that can be hosted privately behind your **Google Login (`Sign in with Google`)**.

## 1. Local PC Folder & Google Drive Storage Layout

Place all project files in your local OneDrive project folder (or sync directly with Google Drive):

```text
C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner\
├── mf_history.db                                          # Persistent SQLite Historical Data Warehouse (6 tables, 3 views)
├── mf_monthly_micro_smallcap_scanner.py                   # Python v3.0 Scanner, SQLite Warehouse & CLI SQL Runner
├── india_mf_micro_smallcap_sep2026_dashboard.html         # 6-Page Interactive Web App (Time-Travel + Exits + Watchlist + VR Ratings + SQL Lab)
├── india_mf_micro_smallcap_fresh_entries_sep2026.csv      # Expanded 33-Column Scheme-Level Fresh Entries CSV (128 rows)
├── india_mf_value_research_ratings_sep2026.csv            # 53-Company Value Research 4-Pillar Ratings & Watchlist CSV
├── india_mf_complete_exits_sep2026.csv                    # 18 Verified Complete Exits & Red/Dark Red/Critical Alerts CSV
└── README.md                                              # Master AI Agent Prompt, SQL Cookbook & Cloud Hosting Guide
```

## 2. Master Prompt for AI Research Agents (v3.0 — With Historical Intelligence Layer)

Copy-paste the following prompt on or after the **15th of every month** (or run `python mf_monthly_micro_smallcap_scanner.py --print-prompt` to generate a dynamically dated version):

> **ROLE & OBJECTIVE:**
> Act as an institutional Indian equity research analyst and quantitative data engineer. Scan the latest monthly mutual fund portfolio disclosures across the top 25 Asset Management Companies (AMCs) in India for the most recently concluded disclosure month (e.g., if today is October 2026, scan **September 2026** disclosures released in mid-October 2026), and update the persistent historical database (`mf_history.db`).
>
> **STRICT TEMPORAL, SOURCE HIERARCHY & ANTI-HALLUCINATION GUARDRAILS:**
>
> 1. **Strict Year & Month Verification:** Only include portfolio actions from the target month and year. Explicitly reject and filter out older IPOs or portfolio articles from prior years (such as 2024 or 2025 articles that share the same month name). Verify both the article publication date and the reporting period header on every source before including any stock.
> 2. **100% Month Change Interpretation (Corporate Action Guardrail):** Occasionally corporate actions, mergers, demergers, or scheme restructurings can create false positives. **Validate that the stock was absent in the immediately preceding month's portfolio before classifying as a fresh entry.**
> 3. **Market-Cap Classification:** Market caps fluctuate daily. **Use market capitalization as of the disclosure month-end date.**
>    * **Micro-Cap:** Market capitalization $\le$ ₹5,000 Crore as of the disclosure month-end date (or Nifty Microcap 250 / ranked beyond top 500 by market cap).
>    * **Small-Cap:** Market capitalization between ₹5,000 Crore and ₹25,000 Crore as of the disclosure month-end date (ranked 251st+ by AMFI/SEBI classification).
> 4. **Strict 5-Tier Source Hierarchy (Preference Order):**
>    Always extract and cross-verify data in this strict priority order:
>    1. **AMC portfolio disclosure** (Statutory monthly Excel/PDF scheme portfolios)
>    2. **AMFI disclosures** (Association of Mutual Funds in India official disclosures)
>    3. **[Trendlyne](https://trendlyne.com/)** (Scheme-level monthly mutual fund shareholding tables)
>    4. **[RupeeVest](https://www.rupeevest.com/Mutual-Fund-Holdings)** (Monthly institutional holdings aggregation)
>    5. **News articles** (Only as a 5th-tier discovery lead; never include without Tier 1–4 verification)
> 5. **Strict Two-Source Verification Rule:** **"If any stock cannot be verified from at least two independent sources, do not include it in the final CSV. Prefer omission over estimation."**
> 6. **Strictly Active Equity Funds Only (Exclude All Index Funds & ETFs):** Restrict the scan strictly to actively managed equity schemes (Small-Cap, Micro-Cap, Mid-Cap, Flexi-Cap, Multi-Cap, ELSS, Focused, Value/Contra, and Active Thematic/Sectoral Equity Funds). **Strictly exclude all passive Index Funds and ETFs** (e.g., *Zerodha Smallcap 100 ETF*, *ICICI Pru Smallcap 250 ETF*, *Motilal Oswal Nifty Microcap 250 Index Fund*, *Kotak/Bandhan Nifty Alpha 50 ETFs*), Fund-of-Funds (FoFs), arbitrage, and debt/liquid schemes so only genuine active fund manager conviction is tracked.
>
> **HISTORICAL DATA PERSISTENCE REQUIREMENT (`mf_history.db`):**
> The system must maintain a month-by-month historical database (`mf_history.db`). For every monthly scan:
> 1. Save all extracted records to the master SQLite database (`mf_history.db`).
> 2. Never overwrite prior months.
> 3. Create snapshots for every disclosure month (`July-2026`, `August-2026`, `September-2026`, `October-2026`).
> 4. Allow querying any historical month and switching between months to compare changes.
> 5. Store: `Stock`, `Scheme`, `AMC`, `Shares Held`, `Value Bought (₹ Cr)`, and `Market Cap (₹ Cr)` as of month-end.
>
> **HISTORICAL TIME TRAVEL MODE:**
> Allow user to specify `MONTH=August` and `YEAR=2026`. When selected:
> 1. Load only August 2026 disclosure data.
> 2. All calculations, rankings, and alerts must use the selected month.
> 3. Do not leak future/latest data into historical views.
> 4. The dashboard title must clearly indicate `"Analysis Month: August 2026"`.
> 5. Provide `Previous Month` and `Next Month` navigation.
>
> **FIRST TIME MF ENTRY ANALYSIS:**
> For every stock, determine across the historical database:
> * First month ever seen in database (`First_MF_Appearance`)
> * First AMC entering (`First_AMC`)
> * Number of AMCs currently holding (`Current_AMC_Count`)
> * Total months held (`Months_Held`)
>
> **AUTOMATED REFRESH REQUIREMENT:**
> Run refresh once every day:
> 1. Check all AMC disclosure sources.
> 2. Check [RupeeVest](https://www.rupeevest.com/Mutual-Fund-Holdings).
> 3. Check [Trendlyne](https://trendlyne.com/).
> 4. Check NSE/BSE bulk deals.
> 5. Check SME/Mainboard IPO allocations.
> If any new mutual fund entry or exit is detected, generate a timestamped alert event in `mf_history.db` (`daily_refresh_alerts`) without deleting historical observations.
>
> **CONSENSUS ACCUMULATION ALERT:**
> Flag stocks where **$\ge 2$ AMCs entered in the same month** OR **$\ge 3$ AMCs entered within 90 days**. Assign score:
> * `1 AMC` = **Low**
> * `2 AMCs` = **Medium**
> * `3–4 AMCs` = **High**
> * `5+ AMCs` = **Institutional Consensus**
>
> **PAGE 2: COMPLETE EXITS & FULL EXIT ALERTS:**
> Identify all instances where `Previous Month Shares > 0` and `Current Month Shares = 0`. Show: `Company`, `Sector`, `AMC`, `Scheme`, `Last Holding`, `Value Sold`, `Months Held`, `Exit Month`, and `Reason Category` (`Portfolio Rebalance`, `Profit Booking`, `Market Cap Migration`).
> * Generate **RED warning box** when `1 AMC` exits completely.
> * Generate **DARK RED warning box** when `2+ AMCs` exit within the same month.
> * Generate **CRITICAL ALERT** when `3+ AMCs` exit within 90 days.
>
> **WATCHLIST SCORE FORMULA:**
> Compute and rank every stock by:
> $$\text{Watchlist Score} = (5 \times \text{Fresh Entries}) + (3 \times \text{AMC Count Increase}) + (2 \times \text{Position Increase}) - (4 \times \text{Complete Exits})$$
> Classify output into: **Strong Accumulation**, **Moderate Accumulation**, **Neutral**, **Distribution**, or **Heavy Distribution**.
>
> **VALUE RESEARCH 4-PILLAR STOCK RATINGS:**
> Extract from [Value Research Online](https://www.valueresearchonline.com/stock-rating-methodology/) for all stocks: **Overall Star Rating (`1★` to `5★`)**, **Quality Score (`/10`)**, **Growth Score (`/10`)**, **Valuation Score (`/10`)**, and **Momentum Score (`/10`)**. Where any pillar is marked `UNRATED` (e.g., recent IPOs), compute using Value Research's official weights (`25% Quality + 20% Growth + 35% Valuation + 20% Momentum`).
>
> **EXPANDED OUTPUT COLUMNS (25+ COLUMNS):**
> Include all original 15 columns plus: `Disclosure_Month`, `Entry_Conviction_Rank`, `Fund_Category`, `Market_Cap_Rs_Cr`, `Listing_Date`, `Fresh_Entry_Confirmed (Y/N)`, `First_MF_Appearance`, `First_AMC`, `Months_Held`, `Current_AMC_Count`, `Consensus_Accumulation_Alert`, `Watchlist_Score`, `Watchlist_Status`, and `VR_Star_Rating` (`Q/G/V/M`).
>
> **HISTORICAL INTELLIGENCE LAYER (SUMMARY):**
> In addition to the current disclosure month:
> 1. Persist every monthly snapshot in `mf_history.db`.
> 2. Maintain a complete historical database.
> 3. Enable month-by-month navigation.
> 4. Generate NEW ENTRY alerts.
> 5. Generate COMPLETE EXIT alerts.
> 6. Generate MULTI-AMC ACCUMULATION alerts.
> 7. Generate MULTI-AMC EXIT alerts.
> 8. Maintain watchlist scores across time.
> 9. Create separate dashboard pages for: **Fresh Entries**, **Complete Exits**, **Accumulation Trends**, **Historical Explorer**, **Value Research Ratings**, and **Company Summary**.
> 10. Refresh source data at least once daily while preserving all historical records.

## 3. Running & Querying `mf_history.db` on Your Windows PC

Open **PowerShell** or **Command Prompt** in `C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner`:

| Task | Command to Run |
| :--- | :--- |
| **1. Run Monthly Scan & Update `mf_history.db`** | `python mf_monthly_micro_smallcap_scanner.py --output-dir "C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner"` |
| **2. Historical Time-Travel Mode (`August 2026`)** | `python mf_monthly_micro_smallcap_scanner.py --month August --year 2026` |
| **3. Query Watchlist Score Leaderboard** | `python mf_monthly_micro_smallcap_scanner.py --preset-query watchlist` |
| **4. Query Multi-AMC Consensus Winners** | `python mf_monthly_micro_smallcap_scanner.py --preset-query consensus` |
| **5. Query Complete Exits & Red/Critical Alerts** | `python mf_monthly_micro_smallcap_scanner.py --preset-query exits` |
| **6. Query First-Time MF Appearance Ledger** | `python mf_monthly_micro_smallcap_scanner.py --preset-query first_seen` |
| **7. Query 4★ & 5★ Value Research Rated Stocks** | `python mf_monthly_micro_smallcap_scanner.py --preset-query vr_5star` |
| **8. Side-by-Side Month Comparison (`Jul` to `Oct`)** | `python mf_monthly_micro_smallcap_scanner.py --preset-query compare_months` |
| **9. Run Any Custom SQL Query on `mf_history.db`** | `python mf_monthly_micro_smallcap_scanner.py --query "SELECT nse_symbol, company_name, watchlist_score, vr_stars FROM v_watchlist_leaderboard WHERE vr_stars >= 4 ORDER BY watchlist_score DESC"` |
| **10. Run Daily Automated Refresh & Alert Check** | `python mf_monthly_micro_smallcap_scanner.py --daily-refresh` |

### Automated Daily Refresh on Windows (Task Scheduler)

Run this one-line command in PowerShell (as Administrator) to schedule the daily refresh every morning at **9:30 AM IST**:

```powershell
schtasks /create /tn "IndiaMF_Daily_Scanner" /tr "python C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner\mf_monthly_micro_smallcap_scanner.py --daily-refresh --output-dir C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner" /sc daily /st 09:30 /f
```

## 4. Hosting as a Live Refreshable Site With Your Google Login

### Option 1: Google Apps Script Web App (`Sign in with Google` Built-In, Zero Cost)

1. Go to [script.google.com](https://script.google.com/) while signed into your Google account and click **New Project**.
2. In `Code.gs`, paste:
   ```javascript
   function doGet(e) {
     return HtmlService.createHtmlOutputFromFile('Index')
       .setTitle('India MF Institutional Accumulation & Value Research Scanner')
       .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
   }
   ```
3. Click **+** next to Files $\rightarrow$ **HTML**, name it `Index` (creates `Index.html`), and paste the contents of `india_mf_micro_smallcap_sep2026_dashboard.html`.
4. Click **Deploy** $\rightarrow$ **New deployment** $\rightarrow$ Select type **Web app**:
   * **Execute as:** `Me`
   * **Who has access:** `Only myself` (enforces your personal Google Login on laptop and phone).

### Option 2: GitHub Actions + Cloudflare Pages + Cloudflare Zero Trust Google OAuth

1. Push this folder (`mf_monthly_micro_smallcap_scanner.py`, `mf_history.db`, `india_mf_micro_smallcap_sep2026_dashboard.html`) to a private GitHub repository.
2. Connect the repository to [Cloudflare Pages](https://pages.cloudflare.com/) for automatic deployment whenever the daily/monthly GitHub Action commits an updated `mf_history.db` and `.html`.
3. In **Cloudflare Zero Trust $\rightarrow$ Access $\rightarrow$ Applications**, add an Access Policy with **Identity Provider: Google** and an rule `Emails ending in: your-email@gmail.com` so only your Google login can open the site.


## 5. v4.0 Early Micro-Cap Discovery Upgrade & Custom Gemini Skill Invocation

### How to Invoke Your Saved Gemini Skill Next Time (1-Line Commands)

Your custom skill **`india-microcap-early-discovery`** is saved to your profile. In any future chat, simply paste any of the following commands:

1. **Monthly Full Scan + Early Micro-Cap Discovery:**
   `Use my india-microcap-early-discovery skill to run the latest monthly mutual fund & pre-MF smart money scan, update mf_history.db, and refresh the dashboard.`
2. **Pre-MF Micro-Cap Hunt (Under ₹3,500 Cr MCap):**
   `Run india-microcap-early-discovery and shortlist Indian micro-caps under ₹3,500 Cr showing SEBI SAST promoter buying, preferential warrants, SME-to-Mainboard migration, or Pioneer 1-2 AMC entry with >2% free-float absorption.`
3. **Single-Stock Forensic & Early-Stage Audit:**
   `Use india-microcap-early-discovery to evaluate [Stock Name / NSE Symbol] across the 4-Layer Early Discovery Funnel, Free-Float Absorption %, CWIP commissioning, and Forensic Cash Conversion.`

### New v4.0 Windows CLI Commands (`mf_history.db`)

| v4.0 Early-Discovery Task | Command to Run |
| :--- | :--- |
| **11. Query Early Micro-Cap Discovery Leaderboard (`v4.0`)** | `python mf_monthly_micro_smallcap_scanner.py --preset-query early_discovery` |
| **12. Query Pre-MF Smart Money & Catalyst Signals (`v4.0`)** | `python mf_monthly_micro_smallcap_scanner.py --preset-query pre_mf_signals` |
| **13. Custom SQL: Pioneer Micro-Caps (`<= ₹4,500 Cr`, Forensic `PASS`)** | `python mf_monthly_micro_smallcap_scanner.py --query "SELECT nse_symbol, company_name, market_cap_rs_cr, free_float_absorption_pct, early_discovery_score, pre_mf_signal FROM v_early_microcap_discovery WHERE market_cap_rs_cr <= 4500 AND forensic_status = 'PASS' ORDER BY early_discovery_score DESC"` |
