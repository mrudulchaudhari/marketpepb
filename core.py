import pandas as pd
import datetime
from datetime import timedelta
from nsepython import *

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
        # Filter out empty or all-NA entries before concatenation to avoid FutureWarning
        df_to_concat = df[df_historical.columns].dropna(how='all')
        df_combined = pd.concat([df_historical, df_to_concat], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['DATE'])
        df_combined["DATE"] = pd.to_datetime(df_combined["DATE"])
        df_combined = df_combined.sort_values("DATE")
        df_combined.to_csv(csv_file, index=False)
        return True
    except Exception as e:
        print(f"Error: {e}")
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


def get_report_message():
    message_parts = []

    for symbol, csv_file in zip(SYMBOLS, CSV_FILES):
        # analyze_data returns last_date, current, averages
        last_date, current, averages, extended_date = analyze_data(csv_file)

        # Portable date formatting (works on Windows and Unix)
        formatted_date = datetime.datetime.strptime(last_date, "%Y-%m-%d").strftime("%d %B %Y").lstrip("0")

        # Try to fetch current price with error handling for API issues
        try:
            price_df = index_history(symbol, last_date, extended_date)
            current_price = (
                price_df["CLOSE"].iloc[-1]
                if not price_df.empty else "N/A"
            )
        except Exception as e:
            print(f"Warning: Could not fetch price for {symbol}: {e}")
            current_price = "N/A"
        # Get recommendation for this csv_file (expects buying_recommendation to return a dict with 'recommendation')
        # If you used the earlier function it returns a dict; adapt if your function returns a plain string.
        rec = buying_recommendation(csv_file)
        # rec might be a dict (as in the earlier snippet). Make sure we extract the user-facing text:
        if isinstance(rec, dict):
            rec_text = rec.get("recommendation", "")
        else:
            rec_text = str(rec)

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


def buying_recommendation(csv_file):
    df = pd.read_csv(csv_file)
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.dropna(subset=["pe*pb"])
    df = df.sort_values(by="DATE", ascending=True)
    df.set_index("DATE", inplace=True)

    current = float(df["pe*pb"].tail(1).values[0])
    averages = {p: df["pe*pb"].tail(p).mean() for p in PERIODS}

    # Calculate % deviation from each average, safely handling zero/NaN averages
    deviations = {}
    for p, avg in averages.items():
        if avg is None or pd.isna(avg) or avg == 0:
            deviations[p] = None  # mark unavailable
        else:
            deviation = ((current - avg) / avg) * 100
            deviations[p] = round(deviation, 2)


    averages["all_time"] = df["pe*pb"].mean()

    if averages["all_time"] and not pd.isna(averages["all_time"]):
        deviations["all_time"] = round(
            ((current - averages["all_time"]) / averages["all_time"]) * 100, 2
        )
    else:
        deviations["all_time"] = None

    # Periods we want to check for the decision (up to 1000 days + all-time)
    check_periods = [20, 40, 60, 120, 250, 500, 750, 1000, 'all_time']

    # Use only available deviations (skip None)
    available_check_values = [deviations[p] for p in check_periods if deviations.get(p) is not None]

    # If we don't have any valid comparisons, return neutral
    if not available_check_values:
        signal = "🟡 Hold / Neutral — insufficient historical data to decide."
    else:
        # Decision Logic using only available values
        if all(v < 0 for v in available_check_values):
            if all(v < -5 for v in available_check_values):
                signal = "🟢 Strong Buy"
            else:
                signal = "🟩 Buy"
        elif all(v > 0 for v in available_check_values):
            signal = "🔴 Overvalued"
        else:
            signal = "🟡 Hold / Neutral"

    # Return a dict so get_report_message() can do rec.get("recommendation")
    return {
        "recommendation": signal,
        "current": round(current, 2),
        "averages": {p: (round(averages[p], 2) if (averages[p] is not None and not pd.isna(averages[p])) else None) for p in PERIODS},
        "deviations": deviations
    }


if __name__ == "__main__":
    # Ensure data directory exists
    import os
    os.makedirs("data", exist_ok=True)

    # Step 1: Create / update CSVs (RUNS FIRST)
    for symbol, csv_file, csv_hist in zip(SYMBOLS, CSV_FILES, CSV_HISTORICAL):
        update_nifty_data(symbol, csv_file, csv_hist)

    # Step 2: Generate report (READS CSVs)
    print(get_report_message())

