import quarter_filter
from ak_fund import AkFund
from data_reader import DataReader
from technical_indicators import TechnicalIndicators as TI

if __name__ == '__main__':
    ak_fund = AkFund()
    rd = DataReader(base_path='data')
    # 获取基金持仓
    fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code='005538')
    # 获取最新季度的股票代码
    quarter_summary = quarter_filter.filter_latest_quarter_data(fund_info)
    # 获取股票代码
    stock_code_series = quarter_summary['股票代码']
    # 获取已有的股票文件
    stock_files = rd.list_stock_files(data_dir='stock_data')
    # print(stock_files)
    for stock in stock_code_series:
        if stock in stock_files:
            continue
        else:
            stock_kline = ak_fund.get_stock_kline(symbol=stock, period='d',
                                                  start_date='2021-01-01')
            ak_fund.save_data(stock_kline,
                              file_name=f'stock_data/{stock}_kline',
                              file_type='csv')

    # print(stock_files)

    for stock in stock_code_series:
        # 读取股票K线数据
        stock_kline = rd.read_stock_kline(symbol=stock, data_dir='stock_data')
        # print(stock_kline)
        ti = TI(stock_kline)
        # 计算技术指标
        ti.period_kdj = [9, 3, 3]
        ti.period_ma = [3, 5, 10, 14, 20, 30, 45]
        result = ti.calculate_all(
            indicators=['ma', 'rsi', 'kdj', 'boll', 'macd', 'cci'])
        # 打印技术指标结果
        print(result)
