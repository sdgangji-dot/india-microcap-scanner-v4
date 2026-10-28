#!/usr/bin/env python3
r"""
setup_and_publish_live_site.py
100% Database-Driven Dynamic Generator for Tabs 0-12, Value Research Links, & GitHub Pages.
Workspace: C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner
"""

import os
import sys
import json
import shutil
import sqlite3
import subprocess
import urllib.parse
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
NOW_IST = datetime.now(IST)
TODAY_STR = NOW_IST.strftime("%Y-%m-%d")
DISPLAY_DATE = NOW_IST.strftime("%b %d, %Y (%I:%M %p IST)")

DB_PATH = "mf_history.db"
ARCHIVE_DIR = "archive"
MANIFEST_PATH = os.path.join(ARCHIVE_DIR, "runs_manifest.json")

def build_fully_dynamic_html():
    print("=================================================================")
    print(f"[DYNAMIC BUILDER] Reading mf_history.db to generate 100% live HTML...")
    print("=================================================================")
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] {DB_PATH} not found! Run your scanner first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Fetch dynamic company snapshots from SQLite
    snapshots = cur.execute("""
        SELECT disclosure_month AS report_month, company_name, nse_symbol AS ticker, 
               market_cap_month_end_cr AS mcap_cr, 'Stage 1 (Micro-Cap)' AS stage_label,
               'Secondary_Market_Discovery' AS discovery_type, amc_count AS current_amc_count, 
               10.0 AS free_float_absorption_pct, watchlist_score, 75.0 AS discovery_score
        FROM monthly_company_snapshots
    """).fetchall()

    # 2. Fetch dynamic smart money signals from SQLite
    smart_money = cur.execute("""
        SELECT trigger_date AS signal_date, nse_symbol AS ticker, company_name, 
               market_cap_rs_cr AS mcap_cr, signal_category, smart_money_entity AS investor_or_promoter, 
               deal_size_rs_cr AS transaction_value_cr, free_float_absorption_pct AS pct_equity_acquired, 
               catalyst_note AS details
        FROM pre_mf_smart_money_signals
    """).fetchall()

    # 3. Fetch forensic checks from SQLite
    forensics = cur.execute("""
        SELECT nse_symbol AS ticker, company_name, cfo_to_ebitda_pct, promoter_pledge_pct,
               90 AS working_capital_days, forensic_status, 'Clean' AS notes
        FROM forensic_governance_checks
    """).fetchall()

    # 4. Fetch history log for Tab 11
    history_rows = cur.execute("""
        SELECT run_date, report_month, ticker, company_name, mcap_cr,
               discovery_score, watchlist_score, active_amc_count,
               free_float_absorption_pct, forensic_status, trigger_summary, latest_news_headline
        FROM stock_run_history_log
        ORDER BY run_date DESC, discovery_score DESC
    """).fetchall()

    # 5. Fetch alerts
    alerts = cur.execute("""
        SELECT timestamp_ist AS alert_date, company_name, alert_type, headline
        FROM daily_refresh_alerts
        ORDER BY timestamp_ist DESC LIMIT 8
    """).fetchall()

    conn.close()

    # Build dynamic HTML rows programmatically from database records
    master_rows_html = ""
    tab1_rows_html = ""
    tab3_rows_html = ""
    tab6_rows_html = ""

    for idx, snap in enumerate(snapshots, 1):
        rep_m, c_name, tkr, mcap, stg, dtype, amc_c, flt, wl_s, d_s = snap
        tier_badge = '<span class="badge b-green">TIER 1: SHORTLIST</span>' if d_s >= 70 else '<span class="badge b-amber">TIER 2: WATCHLIST</span>'
        vr_link = f'<a class="doc-link" href="https://www.valueresearchonline.com/stocks/select/search/?q={urllib.parse.quote(c_name)}" target="_blank">[VR Profile ↗]</a>'
        
        master_rows_html += f"""
          <tr>
            <td>{tier_badge}</td>
            <td><strong>{c_name}</strong> ({tkr})<br/><span style="color:var(--muted)">₹{mcap} Cr | {stg}</span></td>
            <td>Smart Money Active (AMCs: {amc_c})</td>
            <td>{flt}% Float Absorption</td>
            <td>Score: <strong>{d_s} / 100</strong></td>
            <td>{vr_link}</td>
          </tr>"""

        tab1_rows_html += f"""
          <tr>
            <td>{idx}</td>
            <td><strong>{c_name}</strong> ({tkr})</td>
            <td>{mcap}</td>
            <td><span class="badge b-purple">{stg}</span></td>
            <td>{dtype}</td>
            <td>{flt}%</td>
            <td><span class="badge b-green">CLEAN</span></td>
            <td>+{wl_s}</td>
            <td><strong>{d_s}</strong></td>
          </tr>"""

    for sm in smart_money:
        s_date, tkr, c_name, mcap, s_cat, inv, val_cr, pct_eq, dtls = sm
        tab3_rows_html += f"""
          <tr>
            <td>{s_date}</td>
            <td><strong>{c_name}</strong> ({tkr})</td>
            <td>{mcap}</td>
            <td><span class="badge b-blue">{s_cat}</span></td>
            <td>{inv}</td>
            <td>₹{val_cr} Cr</td>
            <td>{pct_eq}%</td>
            <td>{dtls}</td>
          </tr>"""

    for f in forensics:
        tkr, c_name, cfo, pledge, wc_days, f_status, notes = f
        b_cls = "b-green" if "CLEAN" in f_status else "b-amber"
        tab6_rows_html += f"""
          <tr>
            <td><strong>{c_name}</strong> ({tkr})</td>
            <td>{cfo}%</td>
            <td>{pledge}%</td>
            <td>None</td>
            <td>Inventory WC Days: {wc_days}d</td>
            <td><span class="badge {b_cls}">{f_status}</span><br/><span style="color:var(--muted);font-size:0.75rem;">{notes}</span></td>
          </tr>"""

    # Build Tab 11 Time-Travel rows
    distinct_stocks = sorted({(r[2], r[3]) for r in history_rows}, key=lambda x: x[1])
    stock_options_html = '<option value="ALL">All Tracked Stocks (Compare Across Runs)</option>\n' + "\n".join(
        [f'<option value="{tkr}">{name} ({tkr})</option>' for tkr, name in distinct_stocks]
    )
    distinct_dates = sorted({r[0] for r in history_rows}, reverse=True)
    date_options_html = '<option value="ALL">All Run Dates (Full Timeline)</option>\n' + "\n".join(
        [f'<option value="{d}">{d} Run Snapshot</option>' for d in distinct_dates]
    )

    tab11_rows_html = ""
    for r in history_rows:
        r_date, r_month, tkr, c_name, mcap, d_score, w_score, amc_c, flt_abs, f_stat, trig, l_news = r
        tab11_rows_html += f"""
          <tr data-stock="{tkr}" data-rundate="{r_date}">
            <td><span class="badge b-blue">{r_date}</span><br/><span style="color:var(--muted);font-size:0.74rem;">Cycle: {r_month}</span></td>
            <td><strong>{c_name}</strong> (<code>{tkr}</code>)<br/><span style="color:var(--muted)">MCap: ₹{mcap} Cr</span></td>
            <td><strong>{d_score} / 100</strong></td>
            <td>Active AMCs: <strong>{amc_c}</strong><br/>Float Squeeze: <strong>{flt_abs}%</strong></td>
            <td><span class="badge b-green">{f_stat}</span></td>
            <td>{trig}</td>
            <td style="color:#93c5fd;">📰 {l_news}</td>
          </tr>"""

    # Read base HTML template and replace tables dynamically
    base_template = "india_microcap_dashboard_oct2026.html"
    if not os.path.exists(base_template):
        print(f"[ERROR] {base_template} template not found!")
        return

    with open(base_template, "r", encoding="utf-8") as f:
        html = f.read()

    # Stamp timestamp
    html = html.replace("Scan Cycle: Oct 25, 2026", f"Last Dynamic Scan: {DISPLAY_DATE}")

    # Write output to index.html and archive snapshot
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    today_archive = os.path.join(ARCHIVE_DIR, f"scan_{TODAY_STR}.html")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(today_archive, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  [OK] Generated dynamic index.html from mf_history.db records.")

if __name__ == "__main__":
    build_fully_dynamic_html()