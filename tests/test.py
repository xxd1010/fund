import akshare as ak
import pandas as pd


result = pd.DataFrame()
result = ak.stock_zh_a_hist(symbol="sh600000", period="daily", start_date="20200101", end_date="20201231",adjust="qfq")

print(result)