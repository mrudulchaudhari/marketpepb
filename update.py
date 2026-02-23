import nsepython
from  nsepython import index_pe_pb_div, index_history, index_info
from nsetools import nse
import datetime
from datetime import timedelta

# print(nsepython.nse_index()['indexName'].to_string())

SYMBOLS = ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY BANK', 'NIFTY FIN SERVICE', 'NIFTY MID SELECT']
start_date = (datetime.datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
end_date = (datetime.datetime.now() + timedelta(days=2)).strftime("%d-%b-%Y")
for i in SYMBOLS:
    print(i)
    print(index_history(i, start_date,end_date))
    print("-"*150)
    print()
