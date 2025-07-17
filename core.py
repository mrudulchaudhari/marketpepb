import pandas as pd
import datetime
from datetime import timedelta
from nsepython import *

SYMBOLS = ["NIFTY 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY BANK"]
CSV_FILES = ["data/df_nifty50.csv", "data/df_niftymidcap.csv", "data/df_niftysmallcap.csv", "data/df_niftybank.csv"]
CSV_HISTORICAL = ["data/NIFTY 50_Historical.csv", "data/NIFTY MIDCAP 150_Historical.csv",
                  "data/NIFTY SMALLCAP250_Historical.csv", "data/NIFTY BANK_Historical.csv"]
PERIODS = [20, 40, 60, 120, 250, 500, 750, 1000, 2000, 3000, 4000, 5000, 12000]


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
        print(f"Error: {e}")
        return False

def analyze_data(csv_file):
    df = pd.read_csv(csv_file)
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.dropna(subset=["pe*pb"])
    df = df.sort_values(by="DATE", ascending=True)
    df.set_index("DATE", inplace=True)

    last_date = df.index[-1].strftime("%Y-%m-%d")
    current = round(float(df["pe*pb"].tail(1).values[0]), 2)
    averages = {p: round(df["pe*pb"].tail(p).mean(), 2) for p in PERIODS}
    return last_date, current, averages


def get_report_message():
    message_parts = []

    for symbol, csv_file in zip(SYMBOLS, CSV_FILES):
        last_date, current, averages = analyze_data(csv_file)
        date_obj = datetime.datetime.strptime(last_date, "%Y-%m-%d")
        formatted_date = f"{date_obj.day} {date_obj.strftime('%B %Y')}"

        symbol_message = f"""📊 {symbol} Analysis Report
📅 Date: {formatted_date}

Today's PE*PB: {current}

Moving Averages:
1 Month: {averages[20]}
2 Month: {averages[40]}
3 Month: {averages[60]}
6 Month: {averages[120]}
1 Year : {averages[250]}
2 Year : {averages[500]}
3 Year : {averages[750]}
4 Year : {averages[1000]}
8 Year : {averages[2000]}
12 Year: {averages[3000]}
16 Year: {averages[4000]}
20 Year: {averages[5000]}
All time Average: {averages[12000]}
"""
        message_parts.append(symbol_message)

    return "\n\n".join(message_parts)
