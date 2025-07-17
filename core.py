import pandas as pd
import datetime
from datetime import timedelta
from nsepython import *

# Constants
SYMBOLS = ["NIFTY 50", "NIFTY MIDCAP 150", "NIFTY BANK"]
CSV_FILES = [
    "data/df_nifty50.csv",
    "data/df_niftymidcap.csv",
    "data/df_niftybank.csv"
]
CSV_HISTORICAL = [
    "data/NIFTY 50_Historical.csv",
    "data/NIFTY MIDCAP 150_Historical.csv",
    "data/NIFTY BANK_Historical.csv"
]

# Periods per symbol (excluding 12000, we'll use .mean() instead for all-time)
PERIODS_MAP = {
    "NIFTY 50": [20, 40, 60, 120, 250, 500, 750, 1000, 2000, 3000, 4000, 5000],
    "NIFTY BANK": [20, 40, 60, 120, 250, 500, 750, 1000, 2000, 3000, 4000, 5000],
    "NIFTY MIDCAP 150": [20, 40, 60, 120, 250, 500, 1000, 2000],
}

# Period labels
PERIOD_LABELS = {
    20: "1 Month",
    40: "2 Month",
    60: "3 Month",
    120: "6 Month",
    250: "1 Year",
    500: "2 Year",
    750: "3 Year",
    1000: "4 Year",
    2000: "8 Year",
    3000: "12 Year",
    4000: "16 Year",
    5000: "20 Year",
}


def update_nifty_data(symbol, csv_file, csv_historical):
    try:
        start_date = (datetime.datetime.now() - timedelta(days=12000)).strftime("%d-%b-%Y")
        end_date = datetime.datetime.now().strftime("%d-%b-%Y")
        df = index_pe_pb_div(symbol, start_date, end_date)
        df = df.iloc[::-1]
        df["pe"] = pd.to_numeric(df["pe"], errors="coerce")
        df["pb"] = pd.to_numeric(df["pb"], errors="coerce")
        df["pe*pb"] = df["pe"] * df["pb"]

        df_historical = pd.read_csv(csv_historical)
        df_combined = pd.concat([df_historical, df[df_historical.columns]], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['DATE'])
        df_combined["DATE"] = pd.to_datetime(df_combined["DATE"])
        df_combined = df_combined.sort_values("DATE")
        df_combined.to_csv(csv_file, index=False)
        return True
    except Exception as e:
        print(f"Error updating data for {symbol}: {e}")
        return False


def analyze_data(csv_file, symbol):
    df = pd.read_csv(csv_file)
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.dropna(subset=["pe*pb"])
    df = df.sort_values(by="DATE", ascending=True)
    df.set_index("DATE", inplace=True)

    last_date = df.index[-1].strftime("%Y-%m-%d")
    current = round(float(df["pe*pb"].tail(1).values[0]), 2)

    periods = PERIODS_MAP[symbol]
    averages = {}

    for p in periods:
        if len(df) >= p:
            averages[p] = round(df["pe*pb"].tail(p).mean(), 2)

    # All time average
    averages["all_time"] = round(df["pe*pb"].mean(), 2)

    return last_date, current, averages


def get_report_message():
    message_parts = []

    for symbol, csv_file in zip(SYMBOLS, CSV_FILES):
        last_date, current, averages = analyze_data(csv_file, symbol)
        date_obj = datetime.datetime.strptime(last_date, "%Y-%m-%d")
        formatted_date = f"{date_obj.day} {date_obj.strftime('%B %Y')}"

        symbol_message = f"""📊 {symbol} Analysis Report
📅 Date: {formatted_date}

Today's PE*PB: {current}

Moving Averages:"""

        for p in PERIODS_MAP[symbol]:
            if p in averages:
                label = PERIOD_LABELS.get(p, f"{p} days")
                symbol_message += f"\n{label}: {averages[p]}"

        symbol_message += f"\nAll time Average: {averages['all_time']}"
        message_parts.append(symbol_message)

    return "\n\n".join(message_parts)
