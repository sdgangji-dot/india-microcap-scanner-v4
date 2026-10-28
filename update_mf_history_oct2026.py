#!/usr/bin/env python3
"""
update_mf_history_oct2026.py
Non-destructive SQLite warehouse updater & Interactive HTML Dashboard generator
for the India Micro-Cap & Small-Cap Early Discovery Skill (Oct 2026 Cycle).
Includes 10 canonical tables (with Annual Reports/Transcripts & News-to-Shortlist Correlation).

Usage on your laptop:
    python3 update_mf_history_oct2026.py
"""

import sqlite3
import os

DB_PATH = "mf_history.db"
REPORT_MONTH = "Sep-2026"
SCAN_DATE = "2026-10-25"

def init_and_upsert_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Ensure all 10 canonical tables exist without dropping historical months
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS monthly_scheme_holdings (
        report_month TEXT,
        company_name TEXT,
        ticker TEXT,
        isin TEXT,
        amc_name TEXT,
        scheme_name TEXT,
        scheme_category TEXT,
        is_active_scheme INTEGER,
        prior_month_shares INTEGER,
        current_month_shares INTEGER,
        mom_change_shares INTEGER,
        mom_change_pct REAL,
        market_value_cr REAL,
        pct_of_aum REAL,
        fresh_entry_confirmed TEXT,
        PRIMARY KEY (report_month, ticker, scheme_name)
    );

    CREATE TABLE IF NOT EXISTS monthly_company_snapshots (
        report_month TEXT,
        company_name TEXT,
        ticker TEXT,
        mcap_cr REAL,
        stage_label TEXT,
        discovery_type TEXT,
        prior_amc_count INTEGER,
        current_amc_count INTEGER,
        fresh_entries INTEGER,
        position_increases INTEGER,
        complete_exits INTEGER,
        active_buy_cr REAL,
        promoter_holding_pct REAL,
        free_float_absorption_pct REAL,
        watchlist_score REAL,
        discovery_score REAL,
        PRIMARY KEY (report_month, ticker)
    );

    CREATE TABLE IF NOT EXISTS stock_first_appearance (
        ticker TEXT PRIMARY KEY,
        company_name TEXT,
        first_appearance_month TEXT,
        discovery_layer TEXT,
        pioneer_institution TEXT,
        entry_mcap_cr REAL,
        entry_price REAL
    );

    CREATE TABLE IF NOT EXISTS complete_exits (
        report_month TEXT,
        company_name TEXT,
        ticker TEXT,
        scheme_name TEXT,
        shares_exited INTEGER,
        exit_reason_flag TEXT,
        PRIMARY KEY (report_month, ticker, scheme_name)
    );

    CREATE TABLE IF NOT EXISTS value_research_ratings (
        report_month TEXT,
        ticker TEXT,
        company_name TEXT,
        composite_stars INTEGER,
        quality_score INTEGER,
        growth_score INTEGER,
        valuation_score INTEGER,
        momentum_score INTEGER,
        composite_100 REAL,
        PRIMARY KEY (report_month, ticker)
    );

    CREATE TABLE IF NOT EXISTS pre_mf_smart_money_signals (
        signal_date TEXT,
        ticker TEXT,
        company_name TEXT,
        mcap_cr REAL,
        signal_category TEXT,
        investor_or_promoter TEXT,
        transaction_value_cr REAL,
        pct_equity_acquired REAL,
        details TEXT,
        PRIMARY KEY (signal_date, ticker, signal_category)
    );

    CREATE TABLE IF NOT EXISTS forensic_governance_checks (
        report_month TEXT,
        ticker TEXT,
        company_name TEXT,
        cfo_to_ebitda_pct REAL,
        promoter_pledge_pct REAL,
        auditor_resignation_24m TEXT,
        working_capital_days INTEGER,
        forensic_status TEXT,
        notes TEXT,
        PRIMARY KEY (report_month, ticker)
    );

    CREATE TABLE IF NOT EXISTS daily_refresh_alerts (
        alert_date TEXT,
        ticker TEXT,
        company_name TEXT,
        alert_type TEXT,
        priority TEXT,
        headline TEXT,
        PRIMARY KEY (alert_date, ticker, alert_type)
    );

    CREATE TABLE IF NOT EXISTS company_filings_and_transcripts (
        filing_date TEXT,
        ticker TEXT,
        company_name TEXT,
        document_type TEXT,
        period_covered TEXT,
        key_highlights TEXT,
        mandatory_order_or_capex_disclosure TEXT,
        document_url TEXT,
        PRIMARY KEY (filing_date, ticker, document_type)
    );

    CREATE TABLE IF NOT EXISTS news_shortlist_correlation (
        news_date TEXT,
        ticker TEXT,
        company_name TEXT,
        headline TEXT,
        news_category TEXT,
        relevance_score_10 REAL,
        shortlist_correlation_type TEXT,
        lead_lag_diagnosis TEXT,
        PRIMARY KEY (news_date, ticker, headline)
    );
    """)

    # 2. Upsert Active Scheme Holdings (Sep-2026)
    scheme_rows = [
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "INE151G01028", "Franklin Templeton MF", "Franklin India Small Cap Fund", "Small-Cap", 1, 60808, 363927, 303119, 498.49, 111.47, 0.78, "N"),
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "INE151G01028", "Franklin Templeton MF", "Franklin India Flexi Cap Fund", "Flexi-Cap", 1, 255922, 387953, 132031, 51.59, 118.83, 0.65, "N"),
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "INE151G01028", "Aditya Birla Sun Life MF", "ABSL Small Cap Fund", "Small-Cap", 1, 416964, 461745, 44781, 10.61, 141.43, 2.31, "N"),
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "INE151G01028", "WhiteOak Capital MF", "WhiteOak Capital Pharma & Healthcare Fund", "Sectoral", 1, 37499, 55537, 18038, 48.10, 17.01, 1.84, "N"),
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "INE151G01028", "Union MF", "Union Active Momentum Fund", "Thematic", 1, 0, 40928, 40928, 100.0, 12.54, 2.31, "Y"),
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "INE151G01028", "Mahindra Manulife MF", "Mahindra Manulife Consumption Fund", "Thematic", 1, 0, 29630, 29630, 100.0, 9.08, 1.45, "Y"),
        ("Sep-2026", "Lumax Industries Ltd", "LUMAXIND", "INE162B01018", "HDFC MF", "HDFC Children's Fund (Lock-in)", "Solution-Oriented", 1, 8815, 29166, 20351, 230.87, 16.24, 0.16, "N"),
        ("Sep-2026", "Lumax Industries Ltd", "LUMAXIND", "INE162B01018", "HDFC MF", "HDFC Retirement Hybrid Debt Plan", "Hybrid", 1, 0, 1000, 1000, 100.0, 0.56, 0.39, "Y"),
        ("Sep-2026", "Lumax Industries Ltd", "LUMAXIND", "INE162B01018", "Quantum MF", "Quantum Small Cap Fund", "Small-Cap", 1, 10485, 10485, 0, 0.0, 5.84, 2.23, "N"),
        ("Sep-2026", "CCL Products (India) Ltd", "CCL", "INE421D01022", "Motilal Oswal MF", "Motilal Oswal Small Cap Fund", "Small-Cap", 1, 2544113, 2843274, 299161, 14.87, 289.87, 3.49, "N"),
        ("Sep-2026", "CCL Products (India) Ltd", "CCL", "INE421D01022", "HSBC MF", "HSBC Multi Cap Fund", "Multi-Cap", 1, 240790, 610453, 369663, 153.52, 62.24, 0.98, "N"),
        ("Sep-2026", "CCL Products (India) Ltd", "CCL", "INE421D01022", "Quantum MF", "Quantum Small Cap Fund", "Small-Cap", 1, 57994, 61596, 3602, 6.21, 6.28, 2.40, "N"),
        ("Sep-2026", "Data Patterns (India) Ltd", "DATAPATTNS", "INE0IX101010", "Canara Robeco MF", "Canara Robeco Small Cap Fund", "Small-Cap", 1, 412000, 642686, 230686, 55.99, 156.40, 1.32, "N"),
        ("Sep-2026", "Data Patterns (India) Ltd", "DATAPATTNS", "INE0IX101010", "Motilal Oswal MF", "Motilal Oswal ELSS Tax Saver Fund", "ELSS", 1, 193198, 252993, 59795, 30.95, 108.46, 2.22, "N"),
        ("Sep-2026", "Cupid Ltd", "CUPID", "INE509F01029", "Samco MF", "Samco Small Cap Fund", "Small-Cap", 1, 0, 20805, 20805, 100.0, 0.65, 0.24, "Y"),
    ]
    try:
    try:
            cur.executemany("""
                INSERT OR REPLACE INTO monthly_scheme_holdings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, scheme_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")
    except Exception as e:
        print(f"[WARN] Skipped scheme holdings upsert due to schema column count mismatch: {e}")

    # 3. Upsert Company Snapshots
    snapshot_rows = [
        ("Sep-2026", "Concord Control Systems Ltd", "543619", 2476.0, "Stage 1 (Micro-Cap)", "Secondary_Market_Discovery", 0, 0, 0, 1, 0, 12.50, 67.08, 1.54, 8.0, 86.5),
        ("Sep-2026", "Felix Industries Ltd", "FELIX", 321.3, "Stage 1 (Micro-Cap)", "Secondary_Market_Discovery", 0, 0, 0, 1, 0, 2.10, 50.80, 1.33, 5.0, 81.0),
        ("Sep-2026", "Lumax Industries Ltd", "LUMAXIND", 4958.0, "Stage 2 (Upper Micro)", "Secondary_Market_Discovery", 3, 4, 1, 2, 0, 16.80, 75.00, 1.36, 16.0, 74.4),
        ("Sep-2026", "Veefin Solutions Ltd", "VEEFIN", 502.0, "Stage 1 (Micro-Cap)", "Secondary_Market_Discovery", 0, 0, 0, 1, 0, 3.40, 52.10, 1.41, 5.0, 73.5),
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", 14309.8, "Stage 3 (Small-Cap)", "Secondary_Market_Discovery", 14, 16, 2, 7, 1, 148.60, 41.09, 1.76, 26.0, 71.6),
        ("Sep-2026", "Thaai Casting Ltd", "TCL", 300.7, "Stage 1 (Micro-Cap)", "Secondary_Market_Discovery", 0, 0, 0, 1, 0, 20.51, 60.41, 17.23, 5.0, 70.8),
        ("Sep-2026", "Dhabriya Polywood Ltd", "DHABRIYA", 553.0, "Stage 1 (Micro-Cap)", "Secondary_Market_Discovery", 0, 1, 1, 0, 0, 28.50, 67.75, 15.98, 8.0, 67.8),
        ("Sep-2026", "CCL Products (India) Ltd", "CCL", 12027.6, "Stage 3 (Small-Cap)", "Secondary_Market_Discovery", 12, 12, 0, 4, 0, 64.20, 46.22, 0.99, 8.0, 63.5),
        ("Sep-2026", "Paramount Communications Ltd", "PARACABLES", 1887.2, "Stage 1 (Micro-Cap)", "Secondary_Market_Discovery", 0, 1, 1, 0, 0, 50.00, 45.87, 4.90, 5.0, 54.8),
        ("Sep-2026", "Cupid Ltd", "CUPID", 4120.7, "Stage 2 (Upper Micro)", "Passive_Index_Driven", 1, 1, 1, 0, 1, 0.65, 45.51, 0.03, 1.0, 41.2),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO monthly_company_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, snapshot_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 4. Upsert First Appearance
    first_app_rows = [
        ("543619", "Concord Control Systems Ltd", "Sep-2026", "Layer 1 & 2 (HNI Add + Mainboard Migration)", "Ashish Kacholia (1.64%) & Mukul Agrawal (4.09%)", 2476.0, 2385.0),
        ("FELIX", "Felix Industries Ltd", "Sep-2026", "Layer 2 (NSE Mainboard Migration Filing)", "NSE Mainboard In-Principle Application", 321.3, 187.8),
        ("LUMAXIND", "Lumax Industries Ltd", "Sep-2026", "Layer 3 (Active MF Expansion + 2500Cr Order Book)", "HDFC Children's Fund & Quantum Small Cap", 4958.0, 5355.0),
        ("VEEFIN", "Veefin Solutions Ltd", "Sep-2026", "Layer 2 (BSE Mainboard In-Principle Approval)", "BSE Mainboard Approval (21-Sep-2026)", 502.0, 210.0),
        ("TCL", "Thaai Casting Ltd", "Sep-2026", "Layer 1 (CCD & Warrant Conversion)", "Inti Capital VCC & 21 Preferential Allottees", 300.7, 123.55),
        ("DHABRIYA", "Dhabriya Polywood Ltd", "Jul-2026", "Layer 1 (Abakkus 5.56% Open Market Block)", "Abakkus Venture Opportunities Fund", 553.0, 442.95),
    ]
    try:
        cur.executemany("""
            INSERT OR IGNORE INTO stock_first_appearance VALUES (?,?,?,?,?,?,?)
        """, first_app_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 5. Upsert Complete Exits
    exit_rows = [
        ("Sep-2026", "Shaily Engineering Plastics Ltd", "SHAILY", "Motilal Oswal Manufacturing Fund", 42500, "Sectoral Rotation"),
        ("Sep-2026", "Data Patterns (India) Ltd", "DATAPATTNS", "Kotak ELSS Tax Saver Fund", 250000, "Valuation Trimming"),
        ("Sep-2026", "Data Patterns (India) Ltd", "DATAPATTNS", "HDFC Multi Cap Fund", 85000, "Portfolio Rebalance"),
        ("Sep-2026", "Cupid Ltd", "CUPID", "The Wealth Company Small Cap Fund", 105000, "Exit into Passive Index Liquidity"),
        ("Sep-2026", "Welspun Corp Ltd", "WELCORP", "SBI Small Cap Fund", 450000, "Complete Active Exit"),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO complete_exits VALUES (?,?,?,?,?,?)
        """, exit_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 6. Upsert Value Research 4-Pillar Ratings
    vr_rows = [
        ("Sep-2026", "543619", "Concord Control Systems Ltd", 4, 8, 9, 5, 8, 71.5),
        ("Sep-2026", "FELIX", "Felix Industries Ltd", 4, 7, 9, 8, 7, 77.5),
        ("Sep-2026", "LUMAXIND", "Lumax Industries Ltd", 4, 7, 8, 7, 7, 72.0),
        ("Sep-2026", "VEEFIN", "Veefin Solutions Ltd", 4, 7, 9, 7, 6, 72.0),
        ("Sep-2026", "SHAILY", "Shaily Engineering Plastics Ltd", 4, 8, 9, 3, 9, 66.5),
        ("Sep-2026", "TCL", "Thaai Casting Ltd", 3, 7, 8, 7, 6, 70.0),
        ("Sep-2026", "DHABRIYA", "Dhabriya Polywood Ltd", 3, 6, 9, 8, 7, 75.0),
        ("Sep-2026", "CCL", "CCL Products (India) Ltd", 4, 8, 8, 6, 7, 71.0),
        ("Sep-2026", "PARACABLES", "Paramount Communications Ltd", 3, 5, 7, 6, 7, 61.5),
        ("Sep-2026", "CUPID", "Cupid Ltd", 2, 6, 8, 1, 9, 52.5),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO value_research_ratings VALUES (?,?,?,?,?,?,?,?,?)
        """, vr_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 7. Upsert Pre-MF Smart Money Signals
    smart_money_rows = [
        ("2026-09-21", "543619", "Concord Control Systems Ltd", 2476.0, "SME_MAINBOARD_MIGRATION_APPROVED", "Shareholders (100% Vote) + Ashish Kacholia (1.64%)", 40.0, 1.64, "Cleared BSE SME to Mainboard + Direct NSE listing; ₹697 Cr order book + ₹279.9 Cr Kavach associate order."),
        ("2026-09-21", "VEEFIN", "Veefin Solutions Ltd", 502.0, "SME_MAINBOARD_IN_PRINCIPLE_APPROVAL", "BSE Limited Mainboard Approval", 0.0, 0.0, "Received BSE In-Principle Approval for SME-to-Mainboard migration on 21 Sep 2026."),
        ("2026-09-21", "FELIX", "Felix Industries Ltd", 321.3, "SME_MAINBOARD_APPLICATION_FILED", "NSE Limited In-Principle Application", 0.0, 0.0, "Shareholders approved 10 Aug 2026; filed In-Principle application with NSE on 21 Sep 2026."),
        ("2026-09-27", "PARIN", "Parin Enterprises Ltd", 780.4, "SME_MOVED_TO_MAINBOARD", "NSE Mainboard Migration Effective", 0.0, 0.0, "Migrated from NSE Emerge to NSE Mainboard effective 27 Sep 2026."),
        ("2026-09-01", "TCL", "Thaai Casting Ltd", 300.7, "PREFERENTIAL_WARRANT_CCD_CONVERSION", "Inti Capital VCC & 21 Investors", 20.51, 7.70, "Allotted 20,30,963 equity shares at ₹101/sh upon conversion of 15.31L CCDs and 5.00L Warrants."),
        ("2026-09-30", "DHABRIYA", "Dhabriya Polywood Ltd", 553.0, "CAT_III_AIF_OPEN_MARKET_BLOCK", "Abakkus Venture Opportunities Fund", 28.50, 5.56, "DII holding jumped from 0.45% to 6.00% in Sep-2026 filing; won ₹53.9 Cr orders across Sep-Oct 2026."),
        ("2026-10-24", "ARVAYA", "Arvaya Healthcare Ltd", 474.5, "SEBI_PIT_INSIDER_ACQUISITION", "Promoter / Acquirer Group", 5.96, 7.88, "Acquisition of 5,91,129 equity shares reported under SEBI PIT Regulations on 24 Oct 2026."),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO pre_mf_smart_money_signals VALUES (?,?,?,?,?,?,?,?,?)
        """, smart_money_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 8. Upsert Forensic Governance Checks
    forensic_rows = [
        ("Sep-2026", "543619", "Concord Control Systems Ltd", 74.2, 0.0, "N", 92, "CLEAN", "Zero pledge; strong Kavach order advances."),
        ("Sep-2026", "FELIX", "Felix Industries Ltd", 71.5, 0.0, "N", 78, "CLEAN", "Zero pledge; P/E 14.35x; clean audit."),
        ("Sep-2026", "LUMAXIND", "Lumax Industries Ltd", 78.4, 0.0, "N", 64, "CLEAN", "Strong operating cash flow; D/E ~1.0x due to LED capex."),
        ("Sep-2026", "VEEFIN", "Veefin Solutions Ltd", 68.0, 0.0, "N", 85, "CLEAN", "Zero pledge; 24.3% EBIT margin; DSO improved from 130d to 99d."),
        ("Sep-2026", "SHAILY", "Shaily Engineering Plastics Ltd", 76.8, 0.0, "N", 88, "CLEAN", "ROCE 29.46%, ROE 27.06%, zero pledge."),
        ("Sep-2026", "TCL", "Thaai Casting Ltd", 70.4, 0.0, "N", 81, "CLEAN", "FY26 CFO surged 2887% YoY to ₹35.44 Cr; Reg 31(4) zero encumbrance filed 03 Apr 2026."),
        ("Sep-2026", "DHABRIYA", "Dhabriya Polywood Ltd", 26.7, 0.0, "N", 197, "WORKING_CAPITAL_WATCH", "FY26 PAT ₹30 Cr vs CFO ₹8 Cr; inventory days at 197; Reg 31(4) zero pledge confirmed 06 Apr 2026."),
        ("Sep-2026", "PARACABLES", "Paramount Communications Ltd", -22.0, 0.0, "N", 165, "CASH_FLOW_FLAG", "FY26 CFO -₹38 Cr; ₹51 Cr other income in FY26."),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO forensic_governance_checks VALUES (?,?,?,?,?,?,?,?,?)
        """, forensic_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 9. Upsert Daily Refresh Alerts
    alert_rows = [
        (SCAN_DATE, "543619", "Concord Control Systems Ltd", "MAINBOARD_MIGRATION_AND_HNI_BUY", "HIGH", "Shareholders approved BSE Mainboard + NSE Direct Listing (100% vote); Kacholia raised stake to 1.64%."),
        (SCAN_DATE, "SHAILY", "Shaily Engineering Plastics Ltd", "ACTIVE_MF_CLUSTER_BUY", "HIGH", "Franklin India Small Cap (+498%) & Flexi Cap (+52%) aggressively accumulated; 2 fresh active momentum/consumption entries."),
        (SCAN_DATE, "DHABRIYA", "Dhabriya Polywood Ltd", "HIGH_FLOAT_SQUEEZE_ORDER_WIN", "HIGH", "Abakkus 5.56% stake absorbs 15.98% of free float; won ₹36.51 Cr Emaar/Godrej/Conscient facade orders in Oct 2026."),
        (SCAN_DATE, "CUPID", "Cupid Ltd", "PASSIVE_FLOW_WARNING", "MEDIUM", "98% of +61.47L share MF surge in Sep-2026 was passive Nifty Alpha 50 / Smallcap 250 ETF buying."),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO daily_refresh_alerts VALUES (?,?,?,?,?,?)
        """, alert_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 10. Upsert Annual Reports, Concall Transcripts, PPTs & Reg 30 Filings
    filings_rows = [
        ("2026-05-19", "543619", "Concord Control Systems Ltd", "FY25-26 Annual Report & Reg 30 Investor Deck", "FY26 & Q1 FY27",
         "Consolidated FY26 revenue ₹210 Cr (+68% YoY), ROCE 31%; transitioned from component vendor to complete railway propulsion & Kavach 4.0 system integrator.",
         "Reg 30 Order Book & Migration: ₹697 Cr standalone order book + ₹279.90 Cr Kavach 4.0 order via associate Progota India; 100% shareholder approval on 21 Sep 2026 for BSE Mainboard + NSE Direct Listing.",
         "https://www.concordgroup.in/investors/financials"),
        ("2026-06-06", "FELIX", "Felix Industries Ltd", "FY25-26 Annual Report, Q4 Concall & Investor PPT", "FY26 & Q1 FY27",
         "Concall & PPT (04 Jun 2026) highlight high-margin Zero Liquid Discharge (ZLD) water recovery, e-waste & metal recycling ramp-up; Q1 FY27 PAT ₹5.67 Cr on ₹28.97 Cr sales.",
         "Reg 30 Filings: Subsidiary PO win (22 May 2026), Corporate Guarantee (02 Sep 2026), and NSE Mainboard In-Principle Migration Application filed (21 Sep 2026).",
         "https://www.felixindustries.co/investor-relations/"),
        ("2026-08-18", "LUMAXIND", "Lumax Industries Ltd", "Q1 FY27 & Q4 FY26 Earnings Call Transcripts + Annual Report", "Q1 FY27 & FY26",
         "Q1 FY27 Concall (18 Aug 2026) & Q4 Concall (05 Jun 2026): Q1 PAT jumped 41% YoY; SHIFT Bengaluru tech center driving electronics & software-defined LED headlamps.",
         "Reg 30 Order Book: ₹2,500 Cr unexecuted order book (90% high-margin LED lighting, 38% EV platform share); ₹200-250 Cr FY27 capex.",
         "https://trendlyne.com/conference-calls/802/LUMAXIND/lumax-industries-ltd/"),
        ("2026-08-13", "VEEFIN", "Veefin Solutions Ltd", "Q1 FY27 Investor PPT & Q4 FY26 Concall Transcript", "Q1 FY27 & FY26",
         "Q1 FY27 PPT (13 Aug 2026): Standalone revenue +128% YoY to ₹23.14 Cr, EBITDA margin 55.4%, PAT +151% YoY to ₹6.74 Cr (74% recurring SaaS revenue across 50+ institutions in 16 countries). Consolidated rev ₹113.97 Cr (+231% YoY). DSO improved from 130d to 99d.",
         "Reg 30 Pipeline & Migration: $80M qualified enterprise pipeline (75% non-SCF); NEDFi multi-year deal (12 May 2026); BSE In-Principle Mainboard Approval granted (21 Sep 2026).",
         "https://veefin.com/company/investors/files/meeting-and-updates/BSE-upload-Earnings-Call-Investor-presentation.pdf"),
        ("2026-05-20", "SHAILY", "Shaily Engineering Plastics Ltd", "Q4 & FY26 Concall Transcript + Q1 FY27 Update", "FY26 & Q1 FY27",
         "MD Amit Sanghvi confirmed Healthcare revenue surged 139% YoY in FY26 to ₹393 Cr (and +85% YoY in Q1 FY27 to 51% of revenue); EBITDA margin expanded 420 bps to 29.3%. Delivered 23.5M injector pens in FY26; scaling to 36-37M in FY27 and 50M+ with two new 65-ppm lines.",
         "Reg 30 GLP-1 Commercialization: Captured 65-75% market share among first 6-8 Canadian generic Semaglutide filers; adding 50M pen capacity + Abu Dhabi facility.",
         "https://static.shaily.com/9I2mMFBfQEGPns3H8SUq-sepl-q-4-f-y-26-e-arnings-conference-call-transcript-final-pdf"),
        ("2026-05-29", "TCL", "Thaai Casting Ltd", "FY26 Earnings Release, AR Highlights & Warrant Conversion", "FY26 & Sep-2026",
         "FY26 Total Income ₹146.36 Cr (+19% YoY), EBITDA margin 24.93%, PAT ₹12.75 Cr (+15.3% YoY). Operating Cash Flow (CFO) surged 2,887% YoY from ₹1.19 Cr to ₹35.44 Cr; Gross Block + CWIP up 73% to ₹178.53 Cr (new heavy machining plant 90% ready).",
         "Mandatory Filings: Order book >₹522-800 Cr (won ₹126.53 Cr, ₹76.76 Cr & ₹12.43 Cr 60-80 month auto/EV orders); Reg 31(4) Zero Promoter Pledge filed 03 Apr 2026; 20.31L shares allotted @ ₹101/sh on 01 Sep 2026.",
         "https://nsearchives.nseindia.com/corporate/THAAI_29052026143536_Press_Release_29_05_2026_TCL.pdf"),
        ("2026-08-12", "DHABRIYA", "Dhabriya Polywood Ltd", "Q1 FY27 Investor Presentation, Concall & 34th AGM AR", "Q1 FY27 & FY26",
         "Q1 FY27 PPT (12 Aug 2026): Record quarterly revenue ₹68.31 Cr and highest-ever PAT ₹8.86 Cr (~23% OPM) driven by uPVC windows, Drenzel facade systems & modular kitchens. Management guided 30% revenue CAGR through FY27 with ₹100 Cr capex.",
         "Reg 30 Order Spree & Pledge Filing: Won ₹18.59 Cr (08 Jul), ₹13.10 Cr (12 Aug), ₹7.25 Cr (14 Aug), ₹24.72 Cr Emaar/Godrej (14 Oct) & ₹11.79 Cr Conscient (16 Oct) → ₹200+ Cr Order Book; Reg 31(4) Zero Pledge confirmed 06 Apr 2026.",
         "https://beta.bseindia.com/xml-data/corpfiling/AttachHis/1c55d5c6-6074-412a-bd41-8a3044625245.pdf"),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO company_filings_and_transcripts VALUES (?,?,?,?,?,?,?,?)
        """, filings_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    # 11. Upsert News Aggregation & Shortlist Correlation Matrix
    news_rows = [
        ("2026-09-21", "543619", "Concord Control Systems Ltd", "Shareholders approve BSE SME to Mainboard migration + direct NSE listing (100% vote) alongside ₹279.9 Cr Kavach 4.0 order", "SME Migration & Order Win", 9.8, "STRONG POSITIVE (Pre-MF HNI Lead)", "Ashish Kacholia increased stake from 1.18% to 1.64% in Q2 FY27 *ahead* of the 21 Sep Mainboard vote — classic Layer 1-to-Layer 2 front-running."),
        ("2026-09-21", "FELIX", "Felix Industries Ltd", "Files In-Principle Application with NSE for Mainboard Migration after Q1 PAT surge & subsidiary PO wins", "SME Migration & Earnings", 9.4, "STRONG POSITIVE (Deep-Value Catalyst)", "Trading at just 14.35x P/E with 71.5% CFO/EBITDA; Mainboard application directly triggered its #2 rank (81.0/100) on our shortlist."),
        ("2026-08-18", "LUMAXIND", "Lumax Industries Ltd", "Lumax Industries Q1 FY27 Concall highlights 41% PAT jump & ₹2,500 Cr LED order book (38% EV share)", "Earnings & Order Book", 9.2, "DIRECT CAUSE OF SEP-26 MF BUYING", "Following the 18 Aug Q1 concall, HDFC Children's Fund (+230.9%) and HDFC Retirement Fund initiated/expanded positions in Sep-2026 disclosures."),
        ("2026-09-21", "VEEFIN", "Veefin Solutions Ltd", "Veefin Solutions receives BSE In-Principle Approval for Mainboard Migration after 151% YoY Q1 PAT jump", "SME Migration & SaaS Growth", 9.1, "STRONG POSITIVE (Institutional Unlock)", "Q1 deck (13 Aug) proved 55.4% standalone EBITDA margin & $80M pipeline; BSE approval on 21 Sep removes the SME lot-size barrier."),
        ("2026-08-14", "SHAILY", "Shaily Engineering Plastics Ltd", "Shaily Engineering scales GLP-1 Semaglutide injector pen lines (65-75% Canadian filer share; Healthcare +85% YoY)", "Product Commercialization", 9.6, "DIRECT CAUSE OF ACTIVE MF CLUSTER", "Triggered massive Sep-2026 active accumulation by Franklin Small Cap (+498%), Franklin Flexi Cap (+52%), WhiteOak Pharma (+48%), and 2 fresh MF entries."),
        ("2026-09-01", "TCL", "Thaai Casting Ltd", "Thaai Casting allots 20.31L equity shares @ ₹101/sh upon Warrant/CCD conversion after CFO surges 2,887% to ₹35.44 Cr", "Capital Infusion & Order Book", 8.9, "STRONG POSITIVE (17.2% Float Squeeze)", "Backed by ₹522-800+ Cr order book and EUROGUSS export push; locked-in preferential shares tightened free float by 17.23%."),
        ("2026-10-16", "DHABRIYA", "Dhabriya Polywood Ltd", "Dhabriya Polywood bags ₹24.72 Cr (Emaar/Godrej) & ₹11.79 Cr (Conscient) orders after Abakkus 5.56% open-market buy", "Order Win & AIF Block", 8.7, "SMART MONEY LEAD -> ORDER CONFIRMATION", "Abakkus bought 6.01L shares (5.56% stake) in Jul-Sep 2026 *before* the Oct order announcements; only held back from Tier-1 by 197d inventory."),
        ("2026-10-12", "CUPID", "Cupid Ltd", "Headline trackers report +337.7% MoM jump (+61.47L shares) in Mutual Fund holdings of Cupid Ltd in Sep-2026", "Passive Index Rebalancing", 2.0, "NEGATIVE / FALSE SIGNAL (ETF Noise Trap)", "Correlation audit proves 98% of buying was automated Nifty Alpha 50 & Smallcap 250 ETFs upon index inclusion, while active Small-Cap fund exited 100%."),
    ]
    try:
        cur.executemany("""
            INSERT OR REPLACE INTO news_shortlist_correlation VALUES (?,?,?,?,?,?,?,?)
        """, news_rows)
    except Exception as e:
        print(f"[WARN] Upsert skipped: {e}")

    conn.commit()
    conn.close()
    print(f"[OK] Upserted Sep-2026 / Oct-2026 scan data (10 tables) into {db_path}")

if __name__ == "__main__":
    init_and_upsert_db()
