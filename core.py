"""
NIFTY PE*PB Tracker — yfinance + direct-NSE hybrid version.

WHY HYBRID (please read before using):
yfinance/Yahoo Finance does NOT publish PE / PB / Dividend-yield ratios for
NSE indices — that data is computed and published only by NSE itself
(niftyindices.com). So there is no yfinance substitute for that part; any
tool claiming otherwise would just be silently wrong.

What was actually breaking in your original script: nsepython's
index_pe_pb_div() calls
    https://niftyindices.com/Backpage.aspx/getpepbHistoricaldataDBtoString
and that endpoint has been intermittently returning
    {"Message": "There was an error processing the request."}
This is a known, recurring issue on NSE's side (see aeron7/nsepython GitHub
issues), not something specific to your setup.

This script:
  1. Fetches PRICE data via yfinance (reliable swap for nsepython's
     index_history()).
  2. Fetches PE/PB data via a hardened direct session to niftyindices.com
     (same source nsepython uses under the hood), with a proper cookie
     handshake + retries/backoff, and normalizes output columns to your
     OLD style: DATE, pe, pb (+ div if NSE returns it) — so it merges into
     your existing CSVs with zero downstream changes.

If your old CSV columns differ from DATE/pe/pb, tell me the exact header
row and I'll adjust the normalization step below.
"""

import time
import json
import datetime
from datetime import timedelta

import pandas as pd
import requests
import yfinance as yf

SYMBOLS = ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY BANK', 'NIFTY FIN SERVICE', 'NIFTY MID SELECT']

CSV_FILES = ["data/df_nifty50.csv",
             "data/df_nifty_next_50.csv",
             "data/df_niftybank.csv",
             "data/df_nifty_fin_service.csv",
             "data/df_nifty_mid_select.csv"
             ]
CSV_HISTORICAL = ["data/NIFTY 50_Historical.csv",
                  "data/NIFTY NEXT_50_Historical.csv",
                  "data/NIFTY BANK_Historical.csv",
                  "data/NIFTY FIN SERVICE_Historical.csv",
                  "data/NIFTY MID Select_Historical.csv"
                  ]
PERIODS = [20, 40, 60, 120, 250, 500, 750, 1000, 2000, 3000, 4000, 5000]

# Yahoo Finance tickers for price data. NIFTY MID SELECT has no confirmed
# Yahoo ticker — if it fails for you, share the correct one and I'll wire it in.
YF_TICKERS = {
    'NIFTY 50': '^NSEI',
    'NIFTY NEXT 50': '^NSMIDCP',
    'NIFTY BANK': '^NSEBANK',
    'NIFTY FIN SERVICE': 'NIFTY_FIN_SERVICE.NS',
    'NIFTY MID SELECT': None,
}

NIFTYINDICES_BASE = "https://niftyindices.com"
PEPB_URL = f"{NIFTYINDICES_BASE}/Backpage.aspx/getpepbHistoricaldataDBtoString"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{NIFTYINDICES_BASE}/reports/historical-pepb",
    "Origin": NIFTYINDICES_BASE,
}


# ---------------------------------------------------------------------------
# PE / PB fetch (direct NSE source — same data nsepython used, hardened)
# ---------------------------------------------------------------------------

def _new_session():
    """Warm up a session the way a browser would, to pick up required cookies."""
    session = requests.Session()
    session.get(NIFTYINDICES_BASE, headers=HEADERS, timeout=15)
    return session


def _normalize_pepb_columns(df):
    """Map whatever NSE's raw field names are to old-style lowercase columns."""
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "").replace("/", "").replace("_", "")
        if key in ("date",):
            rename_map[col] = "DATE"
        elif key in ("pe", "indexpe"):
            rename_map[col] = "pe"
        elif key in ("pb", "indexpb"):
            rename_map[col] = "pb"
        elif "div" in key:
            rename_map[col] = "div"
    return df.rename(columns=rename_map)


def fetch_pe_pb_div(symbol, start_date, end_date, retries=3, backoff=5):
    """
    Direct replacement for nsepython.index_pe_pb_div(symbol, start_date, end_date).
    start_date/end_date format: "DD-Mon-YYYY" (e.g. "01-Jan-2000").
    Returns a DataFrame with columns DATE, pe, pb (and div if available).
    """
    cinfo = ("{'name':'" + symbol + "','startDate':'" + start_date +
              "','endDate':'" + end_date + "','indexName':'" + symbol + "'}")
    body = {"cinfo": cinfo}

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            session = _new_session()
            resp = session.post(PEPB_URL, headers=HEADERS, data=json.dumps(body), timeout=20)
            resp.raise_for_status()
            payload = resp.json()

            if "d" not in payload:
                raise ValueError(f"Unexpected response shape: {payload}")

            records = json.loads(payload["d"])
            if not records:
                raise ValueError("NSE returned an empty record set")

            df = pd.DataFrame.from_records(records)
            df = _normalize_pepb_columns(df)

            if "DATE" not in df.columns or "pe" not in df.columns or "pb" not in df.columns:
                raise ValueError(f"Could not find DATE/pe/pb in response columns: {list(df.columns)}")

            return df

        except Exception as e:
            last_err = e
            print(f"[{symbol}] PE/PB fetch attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)  # simple linear backoff

    print(f"[{symbol}] All PE/PB fetch attempts failed: {last_err}")
    return pd.DataFrame(columns=["DATE", "pe", "pb"])


# ---------------------------------------------------------------------------
# Price fetch (yfinance — this part genuinely is a safe swap)
# ---------------------------------------------------------------------------

def fetch_latest_close(symbol, start_date, end_date):
    """
    yfinance replacement for nsepython.index_history()'s CLOSE column.
    start_date/end_date here are datetime.date / datetime.datetime objects.
    Returns the latest available close price, or "N/A".
    """
    ticker = YF_TICKERS.get(symbol)
    if not ticker:
        print(f"[{symbol}] No Yahoo Finance ticker configured — skipping price fetch.")
        return "N/A"
    try:
        hist = yf.Ticker(ticker).history(start=start_date, end=end_date)
        if hist.empty:
            return "N/A"
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        print(f"[{symbol}] yfinance price fetch failed: {e}")
        return "N/A"


# ---------------------------------------------------------------------------
# Update / analyze / recommend (logic unchanged from your original script)
# ---------------------------------------------------------------------------

def update_nifty_data(symbol, csv_file, csv_historical):
    try:
        start_date = (datetime.datetime.now() - timedelta(days=12000)).strftime("%d-%b-%Y")
        end_date = datetime.datetime.now().strftime("%d-%b-%Y")
        df = fetch_pe_pb_div(symbol, start_date, end_date)
        if df.empty:
            return False

        df = df.iloc[::-1]
        df["pe"] = pd.to_numeric(df["pe"], errors="coerce")
        df["pb"] = pd.to_numeric(df["pb"], errors="coerce")
        df["pe*pb"] = df["pe"] * df["pb"]

        df_historical = pd.read_csv(csv_historical)
        cols = [c for c in df_historical.columns if c in df.columns]
        df_to_concat = df[cols].dropna(how='all')
        df_combined = pd.concat([df_historical, df_to_concat], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['DATE'])
        df_combined["DATE"] = pd.to_datetime(df_combined["DATE"])
        df_combined = df_combined.sort_values("DATE")
        df_combined.to_csv(csv_file, index=False)
        return True
    except Exception as e:
        print(f"Error updating {symbol}: {e}")
        return False


def analyze_data(csv_file):
    df = pd.read_csv(csv_file)
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.dropna(subset=["pe*pb"])
    df = df.sort_values(by="DATE", ascending=True)
    df.set_index("DATE", inplace=True)

    last_date = df.index[-1]
    extended_date = (last_date + timedelta(days=3)).strftime("%Y-%m-%d")
    last_date = last_date.strftime("%Y-%m-%d")
    current = round(float(df["pe*pb"].tail(1).values[0]), 2)
    averages = {p: round(df["pe*pb"].tail(p).mean(), 2) for p in PERIODS}
    averages["all_time"] = round(df['pe*pb'].mean(), 2)
    return last_date, current, averages, extended_date


def pct(current, avg):
    if avg is None or avg == 0:
        return "N/A"
    return f"{((current - avg) / avg) * 100:.2f}%"


def buying_recommendation(csv_file):
    df = pd.read_csv(csv_file)
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.dropna(subset=["pe*pb"])
    df = df.sort_values(by="DATE", ascending=True)
    df.set_index("DATE", inplace=True)

    current = float(df["pe*pb"].tail(1).values[0])
    averages = {p: df["pe*pb"].tail(p).mean() for p in PERIODS}

    deviations = {}
    for p, avg in averages.items():
        if avg is None or pd.isna(avg) or avg == 0:
            deviations[p] = None
        else:
            deviations[p] = round(((current - avg) / avg) * 100, 2)

    averages["all_time"] = df["pe*pb"].mean()
    if averages["all_time"] and not pd.isna(averages["all_time"]):
        deviations["all_time"] = round(
            ((current - averages["all_time"]) / averages["all_time"]) * 100, 2
        )
    else:
        deviations["all_time"] = None

    check_periods = [20, 40, 60, 120, 250, 500, 750, 1000, 'all_time']
    available_check_values = [deviations[p] for p in check_periods if deviations.get(p) is not None]

    if not available_check_values:
        signal = "🟡 Hold / Neutral — insufficient historical data to decide."
    else:
        if all(v < 0 for v in available_check_values):
            signal = "🟢 Strong Buy" if all(v < -5 for v in available_check_values) else "🟩 Buy"
        elif all(v > 0 for v in available_check_values):
            signal = "🔴 Overvalued"
        else:
            signal = "🟡 Hold / Neutral"

    return {
        "recommendation": signal,
        "current": round(current, 2),
        "averages": {p: (round(averages[p], 2) if (averages[p] is not None and not pd.isna(averages[p])) else None) for p in PERIODS},
        "deviations": deviations
    }


def get_report_message():
    message_parts = []

    for symbol, csv_file in zip(SYMBOLS, CSV_FILES):
        last_date, current, averages, extended_date = analyze_data(csv_file)
        formatted_date = datetime.datetime.strptime(last_date, "%Y-%m-%d").strftime("%d %B %Y").lstrip("0")

        start_dt = datetime.datetime.strptime(last_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(extended_date, "%Y-%m-%d")
        current_price = fetch_latest_close(symbol, start_dt, end_dt)

        rec = buying_recommendation(csv_file)
        rec_text = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)

        symbol_message = f"""📊 {symbol} Analysis Report
📅 Date: {formatted_date}

Today's PE*PB: {current}  |  Last Closing Value : {current_price} — {rec_text}

Moving Averages:
20 Days: {averages[20]}  ({pct(current, averages[20])})
40 Days: {averages[40]}  ({pct(current, averages[40])})
60 Days: {averages[60]}  ({pct(current, averages[60])})
120 Days: {averages[120]}
250 Days: {averages[250]}
500 Days: {averages[500]}
750 Days: {averages[750]}
1000 Days: {averages[1000]}
2000 Days: {averages[2000]}
3000 Days: {averages[3000]}
4000 Days: {averages[4000]}
5000 Days: {averages[5000]}
All time Average: {averages['all_time']}"""
        message_parts.append(symbol_message)

    return "\n\n".join(message_parts)


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)

    for symbol, csv_file, csv_hist in zip(SYMBOLS, CSV_FILES, CSV_HISTORICAL):
        update_nifty_data(symbol, csv_file, csv_hist)

    print(get_report_message())
