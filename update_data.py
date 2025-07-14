from core import update_nifty_data, SYMBOLS, CSV_FILES, CSV_HISTORICAL

for symbol, csv_file, hist_file in zip(SYMBOLS, CSV_FILES, CSV_HISTORICAL):
    update_nifty_data(symbol, csv_file, hist_file)