"""
项目共享常量配置

技术指标默认配置，所有模块统一引用此处。
"""

TECHNICAL_INDICATORS_CONFIG = {
    "ma_period": [3, 5, 10, 14, 20, 30, 45],
    "sma_period": [3, 5, 10, 14, 20, 30, 45],
    "ema_period": [12, 26],
    "rsi_period": [6, 12, 24],
    "macd_period": ["12-26-9"],
    "boll_period": ["20-2"],
    "kdj_period": ["9-3-3"],
    "atr_period": [10],
    "cci_period": [20, 26],
    "williams_r_period": [10],
    "bias_period": [5, 10, 20, 30, 60, 120, 250],
    "psy_period": [10],
}
