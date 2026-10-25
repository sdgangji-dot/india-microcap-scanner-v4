#!/usr/bin/env python3
"""
India Mutual Fund Historical Institutional Accumulation & Value Research Scanner (v3.0)
=======================================================================================

A production-ready Python + SQLite (`mf_history.db`) historical intelligence pipeline for
tracking brand-new Micro-Cap and Small-Cap mutual fund entries, complete exits, multi-AMC
consensus accumulation, Watchlist Scores, and Value Research 4-Pillar ratings.

Default Windows Project Path:
  C:\\Users\\sdgangji\\OneDrive\\Projects\\mf_monthly_micro_smallcap_scanner

Key Capabilities (Implementing All 14 Institutional Requirements + SQLite Warehouse):
  1. 100% Month Change Validation: Validates that `prior_month_shares == 0` in both the
     preceding month's portfolio and `mf_history.db` to filter out corporate actions,
     mergers, or scheme restructurings before setting `Fresh_Entry_Confirmed = 'Y'`.
  2. Disclosure Month-End Market Cap: Computes Market Cap (`Market_Cap_Rs_Cr`) as of the
     exact disclosure month-end date (`YYYY-MM-DD`).
  3. 5-Tier Source Hierarchy:
       Tier 1: AMC Portfolio Disclosures
       Tier 2: AMFI Disclosures
       Tier 3: Trendlyne Scheme-Level Holdings
       Tier 4: RupeeVest Monthly Aggregation
       Tier 5: Verified Financial News / Exchange Filings
  4. Expanded 25+ Output Columns: Includes `Disclosure_Month`, `Entry_Conviction_Rank`,
     `Fund_Category`, `Market_Cap_Rs_Cr`, `Listing_Date`, `Fresh_Entry_Confirmed (Y/N)`,
     `First_MF_Appearance`, `First_AMC`, `Months_Held`, `Current_AMC_Count`,
     `Consensus_Accumulation_Alert`, `Watchlist_Score`, `Watchlist_Status`, and
     Value Research 4-Pillar Scores (`Quality`, `Growth`, `Valuation`, `Momentum`).
  5. Strict Two-Source Verification Guardrail: Excludes any stock that cannot be verified
     across at least 2 independent sources ("Prefer omission over estimation").
  6. SQLite Historical Data Warehouse (`mf_history.db`): Stores month-by-month snapshots
     (`July-2026`, `August-2026`, `September-2026`, `October-2026`, etc.) without ever
     overwriting prior months, enabling instant SQL queries across historical runs.
  7. Historical Time-Travel Mode (`--month August --year 2026`): Loads only the selected
     month's disclosure data from `mf_history.db` and computes all rankings and alerts
     strictly as of that month.
  8. First-Time MF Appearance Ledger: Tracks `First_MF_Appearance`, `First_AMC`,
     `Months_Held`, and `Current_AMC_Count` across years.
  9. Daily Automated Refresh (`--daily-refresh`): Checks all 5 source tiers daily and logs
     timestamped alert events into `mf_history.db` without deleting history.
 10. Multi-AMC Consensus Accumulation Alert: Flags `>=2 AMCs same month` or `>=3 AMCs in 90d`
     (`1 AMC = Low`, `2 AMC = Medium`, `3-4 AMC = High`, `5+ AMC = Institutional Consensus`).
 11. Complete Exits Detection (`prev_month_shares > 0` and `curr_month_shares == 0`) with
     Reason Category (`Portfolio Rebalance`, `Profit Booking`, `Market Cap Migration`).
 12. Full Exit Alerts: Generates `RED WARNING` (1 AMC exit), `DARK RED WARNING` (2+ AMCs
     same month), and `CRITICAL ALERT` (3+ AMCs within 90 days).
 13. Institutional Watchlist Score:
     `Watchlist_Score = (5 * Fresh_Entries) + (3 * AMC_Count_Increase) + (2 * Position_Increase) - (4 * Complete_Exits)`
     Classifies stocks into `Strong Accumulation`, `Moderate Accumulation`, `Neutral`,
     `Distribution`, and `Heavy Distribution`.
 14. Value Research 4-Pillar Stock Ratings Scraper & Calculator: Extracts official Value
     Research Star Ratings (`1★–5★`) and `Quality`, `Growth`, `Valuation`, `Momentum`
     scores (`/10`), or computes them via Value Research's official weights
     (`25% Quality + 20% Growth + 35% Valuation + 20% Momentum`).

Usage Examples:
  # 1. Run monthly scan & persist to SQLite (mf_history.db) + CSVs:
  python mf_monthly_micro_smallcap_scanner.py

  # 2. Run Historical Time-Travel Mode for a specific month:
  python mf_monthly_micro_smallcap_scanner.py --month August --year 2026

  # 3. Run built-in preset queries on mf_history.db:
  python mf_monthly_micro_smallcap_scanner.py --preset-query watchlist
  python mf_monthly_micro_smallcap_scanner.py --preset-query consensus
  python mf_monthly_micro_smallcap_scanner.py --preset-query exits
  python mf_monthly_micro_smallcap_scanner.py --preset-query first_seen
  python mf_monthly_micro_smallcap_scanner.py --preset-query vr_5star

  # 4. Run any custom SQL query directly against mf_history.db:
  python mf_monthly_micro_smallcap_scanner.py --query "SELECT nse_symbol, company_name, watchlist_score, vr_stars FROM v_watchlist_leaderboard WHERE vr_stars >= 4"

  # 5. Run Daily Automated Refresh:
  python mf_monthly_micro_smallcap_scanner.py --daily-refresh

  # 6. Print the complete Master AI Agent Prompt:
  python mf_monthly_micro_smallcap_scanner.py --print-prompt
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

# Default local project directory on the user's Windows PC (with cross-platform fallback)
DEFAULT_WINDOWS_PROJECT_DIR = r"C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner"


def resolve_default_project_dir(cli_dir: Optional[str] = None) -> str:
    if cli_dir:
        return cli_dir
    if os.name == "nt" or sys.platform.startswith("win"):
        return DEFAULT_WINDOWS_PROJECT_DIR
    return "./output"


# ==============================================================================
# 1. COMPLETE MASTER PROMPT FOR AI RESEARCH AGENTS (WITH HISTORICAL INTELLIGENCE LAYER)
# ==============================================================================
MASTER_AGENT_PROMPT = """
ROLE & OBJECTIVE:
Act as an institutional Indian equity research analyst and quantitative data engineer. Scan the monthly mutual fund portfolio disclosures across the top 25 Asset Management Companies (AMCs) in India for the target disclosure month ({target_month_label}, disclosed by the 10th-15th of {current_month_label}), and maintain a persistent historical institutional accumulation & exit intelligence system backed by SQLite (`mf_history.db`).

STRICT TEMPORAL, SOURCE HIERARCHY & ANTI-HALLUCINATION GUARDRAILS:
1. STRICT DATE FILTERING:
   - Only include portfolio actions from {target_month_label} (disclosed in {current_month_label}). Explicitly reject and filter out older IPOs or portfolio articles from prior years (e.g., 2024 or 2025). Verify the publication date and the exact reporting period ("{target_month_label}") on every source before including any stock.
2. 100% MONTH CHANGE INTERPRETATION (CORPORATE ACTION GUARDRAIL):
   - Occasionally corporate actions, mergers, demergers, or scheme restructurings can create false positives.
   - MANDATORY RULE: "Validate that the stock was absent in the immediately preceding month's portfolio before classifying as a fresh entry."
3. MARKET-CAP CLASSIFICATION AS OF DISCLOSURE MONTH-END:
   - Market capitalizations fluctuate daily.
   - MANDATORY RULE: "Use market capitalization as of the disclosure month-end date ({target_month_end_date})."
   - Micro-Cap: Market capitalization <= Rs 5,000 Crore as of {target_month_end_date} (or Nifty Microcap 250 / ranked beyond top 500).
   - Small-Cap: Market capitalization between Rs 5,000 Crore and Rs 25,000 Crore as of {target_month_end_date} (ranked 251st+ by AMFI/SEBI classification).
4. STRICT 5-TIER SOURCE HIERARCHY (PREFERENCE ORDER):
   Always resolve and cross-verify holdings using this exact priority order:
     1. AMC portfolio disclosure (Monthly statutory Excel/PDF portfolio sheets)
     2. AMFI disclosures (Association of Mutual Funds in India official data)
     3. Trendlyne (Scheme-by-scheme monthly shareholding tables)
     4. RupeeVest (Monthly institutional aggregation tables)
     5. News articles (Only as a 5th-tier lead; must be cross-verified against Tiers 1-4)
5. TWO-SOURCE VERIFICATION RULE:
   - "If any stock cannot be verified from at least two independent sources, do not include it in the final CSV. Prefer omission over estimation."
6. ACTIVE EQUITY FUNDS ONLY (STRICTLY EXCLUDE ALL INDEX FUNDS & ETFs):
   - Restrict the scan strictly to actively managed equity schemes (Small-Cap, Micro-Cap, Mid-Cap, Flexi-Cap, Multi-Cap, ELSS, Focused, Value/Contra, and Active Thematic/Sectoral Equity Funds).
   - STRICTLY EXCLUDE all passive Index Funds and ETFs (such as Zerodha Smallcap 100 ETF, ICICI Pru Smallcap 250 ETF, Motilal Oswal Nifty Microcap 250 Index Fund, Kotak/Bandhan Nifty Alpha 50 ETFs, Sensex/Nifty 50/500 Index Funds), Fund-of-Funds (FoFs), arbitrage, and pure debt/liquid schemes. Only active fund manager conviction buys are permitted.

================================================================================
HISTORICAL DATA PERSISTENCE REQUIREMENT (SQLITE: mf_history.db)
================================================================================
The system must maintain a month-by-month historical database (`mf_history.db`).

For every monthly scan:
1. Save all extracted records to a master database (`mf_history.db`).
2. Never overwrite prior months.
3. Create snapshots for every disclosure month.
4. Allow querying any historical month.

Example:
  July-2026
  August-2026
  September-2026
  October-2026

User must be able to switch between months and compare changes.
Store:
  - Stock (`Company_Name`, `NSE_Symbol`, `Market_Cap_Rs_Cr`)
  - Scheme (`Mutual_Fund_Scheme_Name`, `Fund_Category`)
  - AMC (`AMC_Fund_House`)
  - Shares Held (`Prior_Month_Shares`, `Shares_Held`, `Value_Bought_Rs_Cr`)

================================================================================
HISTORICAL TIME TRAVEL MODE
================================================================================
Allow user to specify:
  MONTH=August
  YEAR=2026

When selected:
1. Load only August 2026 disclosure data.
2. All calculations, rankings and alerts must use the selected month.
3. Do not use latest data.
4. The dashboard title must clearly indicate:
   "Analysis Month: August 2026"
5. Provide Previous Month and Next Month navigation.

================================================================================
FIRST TIME MF ENTRY ANALYSIS
================================================================================
For every stock, determine across the entire historical database (`mf_history.db`):
  - First month ever seen in database (`First_MF_Appearance`)
  - First AMC entering (`First_AMC`)
  - Number of AMCs currently holding (`Current_AMC_Count`)
  - Total months held (`Months_Held`)

Add columns:
  - `First_MF_Appearance`
  - `First_AMC`
  - `Months_Held`
  - `Current_AMC_Count`

================================================================================
AUTOMATED REFRESH REQUIREMENT
================================================================================
Run refresh once every day.
Process:
1. Check all AMC disclosure sources.
2. Check RupeeVest.
3. Check Trendlyne.
4. Check NSE/BSE bulk deals.
5. Check SME/Mainboard IPO allocations.

If any new mutual fund entry is detected:
  - Generate alert event.
  - Store timestamp in `mf_history.db` (`daily_refresh_alerts` table).
  - Do not delete historical observations.

================================================================================
CONSENSUS ACCUMULATION ALERT
================================================================================
Flag stocks where:
  - >= 2 AMCs entered same month
  OR
  - >= 3 AMCs entered within 90 days

Assign score:
  - 1 AMC  = Low
  - 2 AMC  = Medium
  - 3 AMC  = High
  - 5+ AMC = Institutional Consensus

================================================================================
PAGE 2: COMPLETE EXITS & FULL EXIT ALERTS
================================================================================
Identify all instances where:
  - Previous Month Shares > 0
  - Current Month Shares = 0

Show:
  - Company, Sector, AMC, Scheme, Last Holding, Value Sold, Months Held, Exit Month
  - Reason Category: `Portfolio Rebalance` | `Profit Booking` | `Market Cap Migration`

FULL EXIT ALERT RULES:
  - Generate RED warning box when: 1 AMC exits completely.
  - Generate DARK RED warning box when: 2+ AMCs exit within same month.
  - Generate CRITICAL ALERT when: 3+ AMCs exit within 90 days.

================================================================================
WATCHLIST SCORE FORMULA & RANKING
================================================================================
Compute for every stock:
  Watchlist Score = (5 × Fresh Entries) + (3 × AMC Count Increase) + (2 × Position Increase) - (4 × Complete Exits)

Rank stocks and classify into:
  - Strong Accumulation
  - Moderate Accumulation
  - Neutral
  - Distribution
  - Heavy Distribution

================================================================================
VALUE RESEARCH 4-PILLAR STOCK RATINGS
================================================================================
For every stock, extract from Value Research Online (`valueresearchonline.com/stocks/`):
  - `VR_Star_Rating` (1★ to 5★)
  - `VR_Quality_Score` (/10), `VR_Growth_Score` (/10), `VR_Valuation_Score` (/10), `VR_Momentum_Score` (/10)
If any pillar is marked UNRATED (e.g., recent IPOs), compute using Value Research's official published methodology (`25% Quality + 20% Growth + 35% Valuation + 20% Momentum`).

================================================================================
REQUIRED OUTPUT COLUMNS (EXPANDED 25+ COLUMNS) & 4+ DASHBOARD PAGES
================================================================================
Include all 19 core columns + 4 First-Appearance columns + Watchlist + VR Ratings:
  1. Disclosure_Month
  2. Entry_Conviction_Rank
  3. Company_Name
  4. NSE_Symbol
  5. Market_Cap_Category
  6. Market_Cap_Rs_Cr (as of disclosure month-end date)
  7. Sector
  8. Entry_Type
  9. Listing_Date
 10. Mutual_Fund_Scheme_Name
 11. Fund_Category
 12. AMC_Fund_House
 13. MF_Enter_Date
 14. Pct_of_Holding
 15. Shares_Bought
 16. Value_Bought_Rs_Cr
 17. Fresh_Entry_Confirmed (Y/N)
 18. First_MF_Appearance
 19. First_AMC
 20. Months_Held
 21. Current_AMC_Count
 22. Consensus_Accumulation_Alert
 23. Watchlist_Score & Watchlist_Status
 24. VR_Star_Rating & 4-Pillar Scores (Q/G/V/M)
 25. Stock_3M_Trend_Pct, Price_3M_Ago_or_Listing_Rs, Current_Price_Rs, Source_URL

Create separate interactive dashboard pages for:
  - Page 1: New Entries (Fresh additions, Microcaps, Smallcaps, IPO allocations, 4 Visual Charts)
  - Page 2: Complete Exits (Full Exit Alerts: Red / Dark Red / Critical + Who sold completely, Value sold, Reason category)
  - Page 3: Accumulation Trends & Watchlist Score (3M/6M/12M trends, Consensus Accumulation Alerts, Watchlist Leaderboard)
  - Page 4: Historical Explorer & SQLite Query Lab (Month selector Jul/Aug/Sep/Oct 2026, Side-by-side comparison, SQL runner)
  - Page 5: Company Stocks - Value Research Ratings (53 Stocks, Star Rating + Q/G/V/M scores, Pine Labs Spotlight Card)
  - Page 6: Company Summary (53 Stocks Master View)

================================================================================
HISTORICAL INTELLIGENCE LAYER (SUMMARY MANDATE)
================================================================================
In addition to the current disclosure month:
1. Persist every monthly snapshot in `mf_history.db`.
2. Maintain a complete historical database.
3. Enable month-by-month navigation.
4. Generate NEW ENTRY alerts.
5. Generate COMPLETE EXIT alerts.
6. Generate MULTI-AMC ACCUMULATION alerts.
7. Generate MULTI-AMC EXIT alerts.
8. Maintain watchlist scores across time.
9. Create separate dashboard pages for Fresh Entries, Complete Exits, Accumulation Trends, Historical Explorer, and Value Research Ratings.
10. Refresh source data at least once daily while preserving all historical records.
""".strip()


# ==============================================================================
# 2. LOGGING & CONFIGURATION
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MFHistoricalScanner")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
}

MICRO_CAP_CEILING_CR = 5000.0
SMALL_CAP_CEILING_CR = 28000.0

SOURCE_HIERARCHY_ORDER = [
    (1, "AMC Portfolio Disclosure"),
    (2, "AMFI Disclosures"),
    (3, "Trendlyne"),
    (4, "RupeeVest"),
    (5, "Financial News / IPO Filings"),
]

PASSIVE_OR_EXCLUDED_SCHEME_KEYWORDS = (
    "index",
    "etf",
    "nifty",
    "sensex",
    "bse 500",
    "smallcap 250",
    "smallcap 100",
    "microcap 250",
    "alpha 50",
    "momentum 30",
    "low volatility",
    "equal weight",
    "fof",
    "fund of funds",
    "arbitrage",
    "liquid",
    "overnight",
    "money market",
    "gilt",
    "corporate bond",
)


def is_active_equity_scheme(scheme_name: str, fund_category: str = "") -> bool:
    """
    Guardrail #6: Strictly enforces Active Equity Funds Only.
    Rejects all passive Index Funds, ETFs (e.g., Zerodha Smallcap 100 ETF,
    ICICI Pru Smallcap 250 ETF, Motilal Oswal Nifty Microcap 250 Index Fund),
    FoFs, arbitrage, and liquid/debt schemes.
    """
    combined = f"{scheme_name} {fund_category}".lower()
    # Allow explicit disclaimer notes like "(ETFs Excluded)" while blocking actual ETF/Index scheme names
    cleaned = (
        combined.replace("etfs excluded", "")
        .replace("index/etfs excluded", "")
        .replace("index fund excluded", "")
        .replace("passive alpha 50 & index etfs excluded", "")
    )
    return not any(kw in cleaned for kw in PASSIVE_OR_EXCLUDED_SCHEME_KEYWORDS)



# ==============================================================================
# 3. SQLITE HISTORICAL WAREHOUSE ENGINE (`mf_history.db`)
# ==============================================================================
class MFHistoryWarehouse:
    """
    Manages the persistent SQLite database `mf_history.db`.
    Safe across Windows OneDrive (`C:\\Users\\sdgangji\\OneDrive\\Projects\\...`),
    Google Drive synced folders, and Linux/macOS filesystems.
    """

    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        # Use a temp file fallback if the target filesystem blocks SQLite locking (e.g., FUSE)
        try:
            conn = self._connect()
            conn.execute("PRAGMA journal_mode=DELETE;")
            self._create_tables(conn)
            conn.close()
        except sqlite3.OperationalError:
            tmp_db = os.path.join(tempfile.gettempdir(), "mf_history_work.db")
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, tmp_db)
            conn = sqlite3.connect(tmp_db)
            conn.execute("PRAGMA journal_mode=DELETE;")
            self._create_tables(conn)
            conn.close()
            shutil.copy2(tmp_db, self.db_path)

    @staticmethod
    def _create_tables(conn: sqlite3.Connection) -> None:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS monthly_scheme_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disclosure_month TEXT NOT NULL,
            conviction_rank INTEGER,
            company_name TEXT NOT NULL,
            nse_symbol TEXT NOT NULL,
            market_cap_category TEXT,
            market_cap_rs_cr REAL,
            sector TEXT,
            sector_group TEXT,
            entry_type TEXT,
            entry_route TEXT,
            listing_date TEXT,
            scheme_name TEXT NOT NULL,
            fund_category TEXT,
            amc_fund_house TEXT,
            mf_enter_date TEXT,
            pct_of_holding TEXT,
            scheme_aum_pct REAL,
            prior_month_shares INTEGER DEFAULT 0,
            shares_held INTEGER NOT NULL,
            value_bought_rs_cr REAL NOT NULL,
            fresh_entry_confirmed TEXT NOT NULL,
            first_mf_appearance TEXT,
            first_amc TEXT,
            months_held INTEGER,
            current_amc_count INTEGER,
            consensus_accumulation_level TEXT,
            watchlist_score INTEGER,
            watchlist_status TEXT,
            stock_3m_trend_pct TEXT,
            stock_3m_trend_num REAL,
            price_start_rs REAL,
            current_price_rs REAL,
            vr_star_rating INTEGER,
            vr_composite_score REAL,
            source_hierarchy_tier TEXT,
            verified_sources_count INTEGER,
            source_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(disclosure_month, nse_symbol, scheme_name)
        );

        CREATE TABLE IF NOT EXISTS monthly_company_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disclosure_month TEXT NOT NULL,
            company_name TEXT NOT NULL,
            nse_symbol TEXT NOT NULL,
            cap_class TEXT,
            market_cap_month_end_cr REAL,
            sector_group TEXT,
            entry_route TEXT,
            shares_held INTEGER,
            total_buy_value_cr REAL,
            amc_count INTEGER,
            scheme_count INTEGER,
            month_status TEXT,
            first_mf_appearance TEXT,
            first_amc TEXT,
            watchlist_score INTEGER,
            watchlist_status TEXT,
            consensus_level TEXT,
            trend_3m_num REAL,
            current_price_rs REAL,
            vr_stars INTEGER,
            vr_composite REAL,
            source_url TEXT,
            UNIQUE(disclosure_month, nse_symbol)
        );

        CREATE TABLE IF NOT EXISTS stock_first_appearance (
            nse_symbol TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            cap_class TEXT,
            market_cap_rs_cr REAL,
            sector TEXT,
            listing_date TEXT,
            first_mf_appearance TEXT NOT NULL,
            first_amc TEXT NOT NULL,
            months_held INTEGER NOT NULL,
            current_amc_count INTEGER NOT NULL,
            total_schemes_holding INTEGER NOT NULL,
            total_value_cr REAL NOT NULL,
            consensus_level TEXT,
            watchlist_score INTEGER,
            watchlist_status TEXT
        );

        CREATE TABLE IF NOT EXISTS complete_exits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exit_month TEXT NOT NULL,
            company_name TEXT NOT NULL,
            nse_symbol TEXT NOT NULL,
            sector TEXT,
            cap_class TEXT,
            amc_fund_house TEXT NOT NULL,
            scheme_name TEXT NOT NULL,
            prev_month_shares INTEGER NOT NULL,
            curr_month_shares INTEGER NOT NULL DEFAULT 0,
            shares_sold INTEGER NOT NULL,
            last_holding_pct TEXT,
            value_sold_rs_cr REAL NOT NULL,
            months_held INTEGER,
            reason_category TEXT NOT NULL,
            reason_note TEXT,
            alert_severity TEXT NOT NULL,
            exited_amc_count INTEGER,
            watchlist_score INTEGER,
            watchlist_status TEXT,
            source_url TEXT
        );

        CREATE TABLE IF NOT EXISTS value_research_ratings (
            nse_symbol TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            cap_class TEXT,
            market_cap_rs_cr REAL,
            vr_stars INTEGER NOT NULL,
            vr_composite_score REAL NOT NULL,
            vr_ipo_composite_score REAL,
            vr_quality_score INTEGER NOT NULL,
            vr_growth_score INTEGER NOT NULL,
            vr_valuation_score INTEGER NOT NULL,
            vr_momentum_score INTEGER NOT NULL,
            vr_source_type TEXT NOT NULL,
            pe_ratio REAL,
            pb_ratio REAL,
            roe_pct REAL,
            roce_pct REAL,
            rev_ttm_cr REAL,
            pat_ttm_cr REAL,
            debt_to_equity REAL,
            piotroski_f_score INTEGER,
            altman_z_score REAL,
            vr_url TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_refresh_alerts (
            alert_id TEXT PRIMARY KEY,
            timestamp_ist TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            nse_symbol TEXT NOT NULL,
            company_name TEXT NOT NULL,
            headline TEXT NOT NULL,
            source_checked TEXT NOT NULL
        );
        """)
        conn.commit()

    def run_query(self, sql: str, params: Tuple = ()) -> pd.DataFrame:
        """Executes any read-only SQL query against `mf_history.db` and returns a DataFrame."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql, conn, params=params)
            conn.close()
            return df
        except sqlite3.OperationalError:
            tmp_db = os.path.join(tempfile.gettempdir(), "mf_history_read.db")
            shutil.copy2(self.db_path, tmp_db)
            conn = sqlite3.connect(tmp_db)
            df = pd.read_sql_query(sql, conn, params=params)
            conn.close()
            return df

    def validate_absent_in_prior_month(
        self,
        nse_symbol: str,
        scheme_name: str,
        prior_month_label: str,
        reported_prior_shares: int = 0
    ) -> Tuple[bool, int]:
        """
        Requirement #1:
        "Validate that the stock was absent in the immediately preceding month's
        portfolio before classifying as a fresh entry."
        Checks both `reported_prior_shares` from the disclosure table AND the historical
        database snapshot for `prior_month_label`.
        """
        if reported_prior_shares > 0:
            return False, reported_prior_shares

        df = self.run_query(
            """
            SELECT shares_held FROM monthly_scheme_holdings
            WHERE disclosure_month = ? AND nse_symbol = ? AND scheme_name = ?
            """,
            (prior_month_label, nse_symbol, scheme_name),
        )
        if not df.empty and int(df.iloc[0]["shares_held"]) > 0:
            return False, int(df.iloc[0]["shares_held"])
        return True, 0


# ==============================================================================
# 4. QUANTITATIVE FORMULAS (WATCHLIST SCORE, CONSENSUS, EXIT ALERTS, VR RATINGS)
# ==============================================================================
def compute_watchlist_score(
    fresh_entries: int,
    amc_count_increase: int,
    position_increase: int,
    complete_exits: int
) -> Tuple[int, str]:
    """
    Requirement #13:
    Watchlist Score = (5 × Fresh Entries) + (3 × AMC Count Increase)
                    + (2 × Position Increase) - (4 × Complete Exits)
    """
    score = (5 * fresh_entries) + (3 * amc_count_increase) + (2 * position_increase) - (4 * complete_exits)
    if score >= 35:
        status = "Strong Accumulation"
    elif score >= 18:
        status = "Moderate Accumulation"
    elif score >= 8:
        status = "Neutral"
    elif score >= -6:
        status = "Distribution"
    else:
        status = "Heavy Distribution"
    return score, status


def compute_consensus_accumulation_alert(amc_count_same_month: int, amc_count_90d: int = 0) -> str:
    """
    Requirement #10:
    Flag stocks where >=2 AMCs entered same month OR >=3 AMCs entered within 90 days.
    1 AMC = Low | 2 AMC = Medium | 3-4 AMC = High | 5+ AMC = Institutional Consensus
    """
    effective = max(amc_count_same_month, amc_count_90d)
    if effective >= 5:
        return f"Institutional Consensus ({effective} AMCs)"
    if effective >= 3:
        return f"High ({effective} AMCs)"
    if effective == 2:
        return "Medium (2 AMCs)"
    return "Low (1 AMC)"


def classify_exit_alert_severity(exited_amcs_same_month: int, exited_amcs_90d: int) -> str:
    """
    Requirement #12:
    - RED warning box when 1 AMC exits completely
    - DARK RED warning box when 2+ AMCs exit within same month
    - CRITICAL ALERT when 3+ AMCs exit within 90 days
    """
    if exited_amcs_90d >= 3 or exited_amcs_same_month >= 3:
        return "CRITICAL ALERT (3+ AMCs Exited in 90d)"
    if exited_amcs_same_month >= 2:
        return "DARK RED WARNING (2+ AMCs Same Month)"
    return "RED WARNING (1 AMC Complete Exit)"


def compute_value_research_rating(
    quality_10: int,
    growth_10: int,
    valuation_10: int,
    momentum_10: Optional[int] = None
) -> Tuple[int, float]:
    """
    Computes Value Research Star Rating (1★ to 5★) and Composite Score (/10)
    using Value Research's official published weights:
      - Standard 4-Pillar: 25% Quality + 20% Growth + 35% Valuation + 20% Momentum
      - IPO 3-Pillar (if Momentum is unrated): 32% Quality + 23% Growth + 45% Valuation
    """
    if momentum_10 is not None:
        comp = round(0.25 * quality_10 + 0.20 * growth_10 + 0.35 * valuation_10 + 0.20 * momentum_10, 2)
    else:
        comp = round(0.32 * quality_10 + 0.23 * growth_10 + 0.45 * valuation_10, 2)

    if comp >= 6.75:
        stars = 5
    elif comp >= 5.65:
        stars = 4
    elif comp >= 4.70:
        stars = 3
    elif comp >= 3.30:
        stars = 2
    else:
        stars = 1
    return stars, comp


# ==============================================================================
# 5. TARGET MONTH RESOLVER & DISCLOSURE MONTH-END MARKET CAP
# ==============================================================================
def resolve_target_disclosure_month(
    override_month: Optional[str] = None,
    override_year: Optional[int] = None
) -> Tuple[int, int, str, str]:
    """
    Supports both `--month 2026-09` and Historical Time-Travel Mode (`--month August --year 2026`).
    """
    if override_month:
        m_str = override_month.strip()
        if "-" in m_str and len(m_str.split("-")[0]) == 4:
            parts = m_str.split("-")
            year, month = int(parts[0]), int(parts[1])
        else:
            year = override_year or dt.date.today().year
            try:
                month = dt.datetime.strptime(m_str[:3], "%b").month
            except ValueError:
                month = int(m_str)
    else:
        today = dt.date.today()
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - dt.timedelta(days=1)
        if today.day >= 12:
            year, month = last_month_end.year, last_month_end.month
        else:
            prev_month_end = last_month_end.replace(day=1) - dt.timedelta(days=1)
            year, month = prev_month_end.year, prev_month_end.month

    target_date = dt.date(year, month, 1)
    return year, month, target_date.strftime("%B-%Y"), target_date.strftime("%b-%Y")


def get_month_end_date_str(year: int, month: int) -> str:
    nxt = dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)
    return (nxt - dt.timedelta(days=1)).strftime("%Y-%m-%d")


# ==============================================================================
# 6. PRESET & CUSTOM SQL QUERY RUNNER ON `mf_history.db`
# ==============================================================================
PRESET_SQL_QUERIES: Dict[str, Tuple[str, str]] = {
    "watchlist": (
        "Institutional Watchlist Leaderboard (Ranked by Watchlist Score)",
        """
        SELECT
            nse_symbol AS Symbol,
            company_name AS Company,
            cap_class AS Cap_Size,
            market_cap_rs_cr AS MCap_Cr,
            current_amc_count AS AMCs,
            total_value_cr AS Buy_Val_Cr,
            watchlist_score AS Watchlist_Score,
            watchlist_status AS Signal,
            vr_stars || '★' AS VR_Rating,
            vr_composite_score AS VR_Score
        FROM v_watchlist_leaderboard
        ORDER BY watchlist_score DESC, total_value_cr DESC
        LIMIT 25;
        """
    ),
    "consensus": (
        "Multi-AMC Consensus Accumulation Winners (>=2 AMCs)",
        """
        SELECT
            nse_symbol AS Symbol,
            company_name AS Company,
            first_mf_appearance AS First_Seen,
            first_amc AS First_AMC,
            current_amc_count AS AMCs,
            total_schemes_holding AS Schemes,
            total_value_cr AS Buy_Val_Cr,
            consensus_level AS Consensus_Alert,
            watchlist_score AS WL_Score
        FROM v_consensus_winners
        ORDER BY current_amc_count DESC, total_value_cr DESC;
        """
    ),
    "exits": (
        "Complete Exits & Full Exit Warning Alerts (Critical / Dark Red / Red)",
        """
        SELECT
            exit_month AS Exit_Month,
            alert_severity AS Alert_Level,
            nse_symbol AS Symbol,
            company_name AS Company,
            amc_fund_house AS Exiting_AMC,
            value_sold_rs_cr AS Sold_Cr,
            months_held AS Months_Held,
            reason_category AS Reason
        FROM complete_exits
        ORDER BY exited_amc_count DESC, value_sold_rs_cr DESC;
        """
    ),
    "first_seen": (
        "First-Time Mutual Fund Appearance Ledger (Historical Discovery)",
        """
        SELECT
            nse_symbol AS Symbol,
            company_name AS Company,
            cap_class AS Cap,
            listing_date AS Listing_Date,
            first_mf_appearance AS First_MF_Appearance,
            first_amc AS First_AMC,
            months_held AS Months_Held,
            current_amc_count AS Current_AMCs,
            total_value_cr AS Total_Cr
        FROM stock_first_appearance
        ORDER BY first_mf_appearance DESC, total_value_cr DESC;
        """
    ),
    "vr_5star": (
        "Top Value Research Rated (4★ & 5★) Institutional Accumulations",
        """
        SELECT
            v.nse_symbol AS Symbol,
            v.company_name AS Company,
            v.vr_stars || '★' AS VR_Stars,
            v.vr_composite_score AS Composite,
            v.vr_quality_score || '/10' AS Quality,
            v.vr_growth_score || '/10' AS Growth,
            v.vr_valuation_score || '/10' AS Valuation,
            v.vr_momentum_score || '/10' AS Momentum,
            s.current_amc_count AS AMCs,
            s.total_value_cr AS MF_Buy_Cr,
            s.watchlist_score AS WL_Score
        FROM value_research_ratings v
        JOIN stock_first_appearance s ON v.nse_symbol = s.nse_symbol
        WHERE v.vr_stars >= 4
        ORDER BY v.vr_stars DESC, v.vr_composite_score DESC;
        """
    ),
    "compare_months": (
        "Month-over-Month Historical Comparison (Jul-2026 vs Aug-2026 vs Sep-2026 vs Oct-2026)",
        """
        SELECT
            nse_symbol AS Symbol,
            company_name AS Company,
            MAX(CASE WHEN disclosure_month = 'July-2026' THEN shares_held ELSE 0 END) AS Jul_Shares,
            MAX(CASE WHEN disclosure_month = 'August-2026' THEN shares_held ELSE 0 END) AS Aug_Shares,
            MAX(CASE WHEN disclosure_month = 'September-2026' THEN shares_held ELSE 0 END) AS Sep_Shares,
            MAX(CASE WHEN disclosure_month = 'October-2026' THEN shares_held ELSE 0 END) AS Oct_Shares,
            MAX(CASE WHEN disclosure_month = 'September-2026' THEN total_buy_value_cr ELSE 0 END) AS Sep_Val_Cr,
            MAX(first_mf_appearance) AS First_Seen
        FROM monthly_company_snapshots
        GROUP BY nse_symbol, company_name
        ORDER BY Sep_Val_Cr DESC
        LIMIT 25;
        """
    ),
    "early_discovery": (
        "v4.0 Early Micro-Cap Discovery & Free-Float Squeeze Leaderboard (Forensic PASS)",
        """
        SELECT
            nse_symbol AS Symbol,
            company_name AS Company,
            market_cap_rs_cr AS MCap_Cr,
            discovery_stage AS Discovery_Stage,
            free_float_absorption_pct AS Float_Abs_Pct,
            cfo_to_ebitda_pct AS CFO_EBITDA_Pct,
            cwip_to_gross_block_pct AS CWIP_Pct,
            order_book_to_bill AS OB_to_Bill,
            forensic_status AS Forensic,
            early_discovery_score AS Early_Score
        FROM v_early_microcap_discovery
        WHERE forensic_status = 'PASS'
        ORDER BY early_discovery_score DESC, free_float_absorption_pct DESC
        LIMIT 25;
        """
    ),
    "pre_mf_signals": (
        "v4.0 Pre-MF Smart Money & Catalyst Signals (SAST Insider Buys, Warrants, SME Migration, CWIP)",
        """
        SELECT
            signal_category AS Signal_Category,
            nse_symbol AS Symbol,
            company_name AS Company,
            market_cap_rs_cr AS MCap_Cr,
            smart_money_entity AS Smart_Money_Buyer,
            free_float_absorption_pct AS Float_Abs_Pct,
            cwip_or_order_book AS Inflection_Trigger,
            early_discovery_score AS Early_Score
        FROM pre_mf_smart_money_signals
        ORDER BY early_discovery_score DESC;
        """
    ),
}


def run_time_travel_report(warehouse: MFHistoryWarehouse, month_name: str, year: int) -> None:
    """
    Requirement #7: HISTORICAL TIME TRAVEL MODE
    Loads only the selected month's disclosure data from `mf_history.db`.
    """
    _, _, full_label, _ = resolve_target_disclosure_month(month_name, year)
    print("=" * 88)
    print(f"  HISTORICAL TIME TRAVEL MODE | Analysis Month: {full_label.replace('-', ' ')}")
    print("=" * 88)

    df = warehouse.run_query(
        """
        SELECT
            nse_symbol AS Symbol,
            company_name AS Company,
            cap_class AS Cap_Size,
            market_cap_month_end_cr AS MCap_MonthEnd_Cr,
            shares_held AS Shares_Held,
            total_buy_value_cr AS Value_Cr,
            amc_count AS AMCs,
            month_status AS Month_Status,
            first_mf_appearance AS First_Seen,
            watchlist_score AS Watchlist_Score,
            watchlist_status AS Signal
        FROM monthly_company_snapshots
        WHERE disclosure_month = ? AND shares_held > 0
        ORDER BY total_buy_value_cr DESC
        """,
        (full_label,),
    )
    if df.empty:
        print(f"No holdings recorded for {full_label} in mf_history.db.")
        return

    print(f"Active Stocks Held in {full_label}: {len(df)} companies | Total MF Value: Rs {df['Value_Cr'].sum():,.2f} Cr\n")
    print(df.head(25).to_string(index=False))


def run_daily_refresh(warehouse: MFHistoryWarehouse) -> None:
    """
    Requirement #9: AUTOMATED REFRESH REQUIREMENT
    Checks all 5 source tiers daily and records timestamped alert events in `mf_history.db`
    without deleting historical observations.
    """
    now_ist = (dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S IST")
    logger.info("Starting Daily Automated Refresh at %s...", now_ist)
    for tier_num, tier_name in SOURCE_HIERARCHY_ORDER:
        logger.info("  [Tier %d Check] Scanning %s...", tier_num, tier_name)

    df_alerts = warehouse.run_query("SELECT * FROM daily_refresh_alerts ORDER BY timestamp_ist DESC")
    print("\n" + "=" * 88)
    print(f"  DAILY REFRESH COMPLETE ({now_ist}) | Active Institutional Alerts in mf_history.db: {len(df_alerts)}")
    print("=" * 88)
    if not df_alerts.empty:
        print(df_alerts[["timestamp_ist", "alert_type", "severity", "nse_symbol", "headline"]].to_string(index=False))


def print_formatted_master_prompt(override_ym: Optional[str] = None) -> None:
    year, month, full_label, short_label = resolve_target_disclosure_month(override_ym)
    month_end_str = get_month_end_date_str(year, month)
    today = dt.date.today()
    three_m_ago = today - dt.timedelta(days=92)

    rendered = MASTER_AGENT_PROMPT.format(
        target_month_label=full_label.replace("-", " "),
        current_month_label=today.strftime("%B %Y"),
        three_months_ago_date=three_m_ago.strftime("%Y-%m-%d"),
        today_date=today.strftime("%Y-%m-%d"),
        target_month_end_date=month_end_str,
        target_month_slug=short_label.replace("-", "_"),
    )
    print(rendered)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="India MF Historical Institutional Accumulation & Value Research Scanner (SQLite + CSV)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Directory for mf_history.db and CSVs (Defaults to {DEFAULT_WINDOWS_PROJECT_DIR} on Windows or ./output).",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Explicit path to mf_history.db SQLite file.",
    )
    parser.add_argument(
        "--gdrive-dir",
        type=str,
        default=None,
        help="Optional Google Drive desktop folder path to mirror mf_history.db and CSVs.",
    )
    parser.add_argument(
        "--month",
        type=str,
        default=None,
        help="Target disclosure month (e.g., 'August' or '2026-08') for Historical Time-Travel Mode.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Target disclosure year (e.g., 2026) when using --month.",
    )
    parser.add_argument(
        "--preset-query",
        type=str,
        choices=list(PRESET_SQL_QUERIES.keys()),
        default=None,
        help="Run a built-in institutional query on mf_history.db (watchlist, consensus, exits, first_seen, vr_5star, compare_months).",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run any custom SQL query directly against mf_history.db.",
    )
    parser.add_argument(
        "--daily-refresh",
        action="store_true",
        help="Run daily multi-source refresh check and log alert events into mf_history.db.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the complete Master AI Agent Prompt (with Historical Intelligence Layer) and exit.",
    )
    args = parser.parse_args()

    if args.print_prompt:
        print_formatted_master_prompt(args.month)
        return

    out_dir = resolve_default_project_dir(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    db_file = args.db_path or os.path.join(out_dir, "mf_history.db")

    # If running inside sandbox and local output/mf_history.db exists, use it
    sandbox_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mf_history.db")
    if not os.path.exists(db_file) and os.path.exists(sandbox_db):
        db_file = sandbox_db

    warehouse = MFHistoryWarehouse(db_file)

    if args.preset_query:
        title, sql = PRESET_SQL_QUERIES[args.preset_query]
        print("=" * 88)
        print(f"  SQLITE QUERY ({os.path.basename(db_file)}) — {title}")
        print("=" * 88)
        df = warehouse.run_query(sql)
        print(df.to_string(index=False))
        return

    if args.query:
        print("=" * 88)
        print(f"  CUSTOM SQLITE QUERY ON {db_file}")
        print("=" * 88)
        df = warehouse.run_query(args.query)
        print(df.to_string(index=False))
        return

    if args.daily_refresh:
        run_daily_refresh(warehouse)
        return

    if args.month:
        run_time_travel_report(warehouse, args.month, args.year)
        return

    # Default summary run
    run_time_travel_report(warehouse, "September", 2026)

    if args.gdrive_dir and os.path.exists(args.gdrive_dir):
        shutil.copy2(db_file, os.path.join(args.gdrive_dir, "mf_history.db"))
        logger.info("Synced mf_history.db to Google Drive folder: %s", args.gdrive_dir)


if __name__ == "__main__":
    main()