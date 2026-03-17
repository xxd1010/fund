from ak_fund import AkFund
from technical_indicators import TechnicalIndicators
import quarter_filter

if __name__ == '__main__':
    ak_fund = AkFund()
    fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code='005538')
    quarter_summary = quarter_filter.filter_latest_quarter_data(fund_info)
    stock_code_series = quarter_summary['股票代码']
    for stock in stock_code_series:
        stock_kline = ak_fund.get_stock_kline(symbol=stock, period='d', start_date='2022-01-01')
        ak_fund.save_data(stock_kline, f'{stock}_kline')
