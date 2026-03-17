"""
技术指标图表展示模块

功能：提供多种图表类型展示技术指标，支持实时更新、交互操作、主题切换等功能
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue

import pandas as pd
import numpy as np
from loguru import logger


class ChartType(Enum):
    """图表类型枚举"""
    LINE = "line"           # 折线图
    BAR = "bar"             # 柱状图
    CANDLESTICK = "candlestick"  # K线图
    AREA = "area"           # 面积图
    SCATTER = "scatter"     # 散点图
    PIE = "pie"             # 饼图
    GAUGE = "gauge"         # 仪表盘
    HEATMAP = "heatmap"     # 热力图
    RADAR = "radar"         # 雷达图
    MULTI_AXES = "multi_axes"  # 多轴图


class Theme(Enum):
    """主题模式枚举"""
    LIGHT = "light"
    DARK = "dark"


@dataclass
class ChartConfig:
    """图表配置类"""
    width: int = 1200
    height: int = 600
    theme: Theme = Theme.LIGHT
    title: str = ""
    subtitle: str = ""
    x_axis_label: str = ""
    y_axis_label: str = ""
    show_legend: bool = True
    show_grid: bool = True
    show_tooltip: bool = True
    enable_zoom: bool = True
    enable_brush: bool = True
    animation_duration: int = 300
    colors: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result['theme'] = self.theme.value
        return result


@dataclass
class IndicatorData:
    """指标数据类"""
    name: str                    # 指标名称
    value: Union[float, List[float]]  # 指标数值
    unit: str = ""              # 单位
    timestamp: Optional[datetime] = None  # 时间戳
    category: str = ""          # 分类
    metadata: Optional[Dict] = None  # 元数据
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'category': self.category,
            'metadata': self.metadata
        }
        return result


class ChartTheme:
    """图表主题管理类"""
    
    # 预定义配色方案
    COLOR_SCHEMES = {
        'default': ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', 
                   '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'],
        'technical': {
            'up': '#ef5350',      # 上涨红色
            'down': '#26a69a',    # 下跌绿色
            'neutral': '#757575', # 中性灰色
            'ma5': '#ff9800',     # 5日均线
            'ma10': '#2196f3',    # 10日均线
            'ma20': '#9c27b0',    # 20日均线
            'ma60': '#795548',    # 60日均线
            'volume': '#607d8b',  # 成交量
            'boll_upper': '#ff5722',
            'boll_middle': '#2196f3',
            'boll_lower': '#ff5722',
            'macd_positive': '#ef5350',
            'macd_negative': '#26a69a',
        },
        'light': {
            'background': '#ffffff',
            'text': '#333333',
            'grid': '#e0e0e0',
            'axis': '#666666',
            'tooltip_bg': 'rgba(255, 255, 255, 0.9)',
            'tooltip_border': '#ccc',
            'tooltip_text': '#333',
        },
        'dark': {
            'background': '#1a1a1a',
            'text': '#e0e0e0',
            'grid': '#333333',
            'axis': '#888888',
            'tooltip_bg': 'rgba(50, 50, 50, 0.9)',
            'tooltip_border': '#555',
            'tooltip_text': '#e0e0e0',
        }
    }
    
    def __init__(self, theme: Theme = Theme.LIGHT):
        self.theme = theme
        self.colors = self.COLOR_SCHEMES['default']
        self.technical_colors = self.COLOR_SCHEMES['technical']
        self.theme_colors = self.COLOR_SCHEMES[theme.value]
    
    def get_color(self, index: int) -> str:
        """获取指定索引的颜色"""
        return self.colors[index % len(self.colors)]
    
    def get_technical_color(self, name: str) -> str:
        """获取技术指标专用颜色"""
        return self.technical_colors.get(name, self.colors[0])
    
    def get_theme_color(self, element: str) -> str:
        """获取主题元素颜色"""
        return self.theme_colors.get(element, '#000000')


class DataProcessor:
    """数据处理器类"""
    
    @staticmethod
    def resample_data(data: pd.DataFrame, rule: str = 'D') -> pd.DataFrame:
        """
        重采样数据
        
        Args:
            data: 原始数据
            rule: 重采样规则，'D'日，'W'周，'M'月
            
        Returns:
            重采样后的数据
        """
        data = data.copy()
        
        if '日期' in data.columns:
            data = data.set_index('日期')
        elif 'date' in data.columns:
            data = data.set_index('date')
        else:
            raise ValueError("数据中必须包含'日期'或'date'列")
        
        # 确保索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data.index = pd.to_datetime(data.index)
            except Exception as e:
                raise ValueError(f"无法将索引转换为DatetimeIndex: {e}")
        
        # 确定列名映射
        agg_dict = {}
        if '开盘' in data.columns:
            agg_dict['开盘'] = 'first'
        if 'open' in data.columns:
            agg_dict['open'] = 'first'
        if '最高' in data.columns:
            agg_dict['最高'] = 'max'
        if 'high' in data.columns:
            agg_dict['high'] = 'max'
        if '最低' in data.columns:
            agg_dict['最低'] = 'min'
        if 'low' in data.columns:
            agg_dict['low'] = 'min'
        if '收盘' in data.columns:
            agg_dict['收盘'] = 'last'
        if 'close' in data.columns:
            agg_dict['close'] = 'last'
        if '成交量' in data.columns:
            agg_dict['成交量'] = 'sum'
        if 'volume' in data.columns:
            agg_dict['volume'] = 'sum'
        
        # OHLCV重采样
        resampled = data.resample(rule).agg(agg_dict)
        
        return resampled.reset_index()
    
    @staticmethod
    def filter_by_date_range(data: pd.DataFrame, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        按日期范围过滤数据
        
        Args:
            data: 原始数据
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            过滤后的数据
        """
        date_col = '日期' if '日期' in data.columns else 'date'
        
        if start_date:
            data = data[data[date_col] >= start_date]
        if end_date:
            data = data[data[date_col] <= end_date]
        
        return data
    
    @staticmethod
    def normalize_data(data: pd.Series, method: str = 'minmax') -> pd.Series:
        """
        数据归一化
        
        Args:
            data: 原始数据
            method: 归一化方法，'minmax'或'zscore'
            
        Returns:
            归一化后的数据
        """
        if method == 'minmax':
            return (data - data.min()) / (data.max() - data.min())
        elif method == 'zscore':
            return (data - data.mean()) / data.std()
        else:
            raise ValueError(f"不支持的归一化方法: {method}")


class ChartRenderer:
    """图表渲染引擎基类"""
    
    def __init__(self, config: ChartConfig):
        self.config = config
        self.theme = ChartTheme(config.theme)
        self.data_processor = DataProcessor()
    
    def render(self, data: Any, chart_type: ChartType) -> Dict:
        """
        渲染图表
        
        Args:
            data: 图表数据
            chart_type: 图表类型
            
        Returns:
            图表配置字典
        """
        raise NotImplementedError("子类必须实现render方法")
    
    def _create_base_config(self) -> Dict:
        """创建基础配置"""
        return {
            'width': self.config.width,
            'height': self.config.height,
            'backgroundColor': self.theme.get_theme_color('background'),
            'title': {
                'text': self.config.title,
                'subtext': self.config.subtitle,
                'textStyle': {'color': self.theme.get_theme_color('text')},
                'left': 'center'
            },
            'tooltip': {
                'show': self.config.show_tooltip,
                'trigger': 'axis',
                'backgroundColor': self.theme.get_theme_color('tooltip_bg'),
                'borderColor': self.theme.get_theme_color('tooltip_border'),
                'textStyle': {'color': self.theme.get_theme_color('tooltip_text')},
                'axisPointer': {
                    'type': 'cross',
                    'label': {'backgroundColor': self.theme.get_theme_color('grid')}
                }
            },
            'legend': {
                'show': self.config.show_legend,
                'data': [],
                'textStyle': {'color': self.theme.get_theme_color('text')},
                'top': 30
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'bottom': '3%',
                'containLabel': True,
                'show': self.config.show_grid,
                'borderColor': self.theme.get_theme_color('grid')
            },
            'toolbox': {
                'feature': {
                    'dataZoom': {'yAxisIndex': 'none'},
                    'restore': {},
                    'saveAsImage': {}
                }
            },
            'dataZoom': [
                {'type': 'inside', 'start': 0, 'end': 100},
                {'start': 0, 'end': 100}
            ] if self.config.enable_zoom else [],
            'color': self.theme.colors,
            'series': []
        }


class TechnicalChartRenderer(ChartRenderer):
    """技术指标图表渲染器"""
    
    def render_candlestick(self, data: pd.DataFrame, indicators: Optional[Dict] = None) -> Dict:
        """
        渲染K线图
        
        Args:
            data: OHLCV数据
            indicators: 技术指标数据字典
            
        Returns:
            图表配置
        """
        config = self._create_base_config()
        config['title']['text'] = self.config.title or 'K线图'
        
        # 日期列
        date_col = '日期' if '日期' in data.columns else 'date'
        dates = data[date_col].tolist()
        
        # K线数据 [开盘, 收盘, 最低, 最高]
        candlestick_data = []
        for _, row in data.iterrows():
            open_price = row.get('开盘', row.get('open', 0))
            close_price = row.get('收盘', row.get('close', 0))
            low_price = row.get('最低', row.get('low', 0))
            high_price = row.get('最高', row.get('high', 0))
            candlestick_data.append([open_price, close_price, low_price, high_price])
        
        # X轴
        config['xAxis'] = {
            'type': 'category',
            'data': dates,
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')}
        }
        
        # Y轴 - 价格
        config['yAxis'] = [
            {
                'type': 'value',
                'name': '价格',
                'position': 'left',
                'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
                'axisLabel': {'color': self.theme.get_theme_color('text')},
                'splitLine': {'lineStyle': {'color': self.theme.get_theme_color('grid')}}
            }
        ]
        
        # 系列数据
        config['series'] = [
            {
                'name': 'K线',
                'type': 'candlestick',
                'data': candlestick_data,
                'itemStyle': {
                    'color': self.theme.get_technical_color('up'),
                    'color0': self.theme.get_technical_color('down'),
                    'borderColor': self.theme.get_technical_color('up'),
                    'borderColor0': self.theme.get_technical_color('down')
                }
            }
        ]
        
        # 添加技术指标
        if indicators:
            for name, values in indicators.items():
                if name.startswith('MA'):
                    config['series'].append({
                        'name': name,
                        'type': 'line',
                        'data': values.tolist() if isinstance(values, pd.Series) else values,
                        'smooth': True,
                        'lineStyle': {'width': 1},
                        'symbol': 'none'
                    })
                elif name in ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']:
                    config['series'].append({
                        'name': name,
                        'type': 'line',
                        'data': values.tolist() if isinstance(values, pd.Series) else values,
                        'smooth': True,
                        'lineStyle': {'width': 1, 'type': 'dashed'},
                        'symbol': 'none'
                    })
        
        config['legend']['data'] = [s['name'] for s in config['series']]
        
        return config
    
    def render_volume(self, data: pd.DataFrame) -> Dict:
        """
        渲染成交量图
        
        Args:
            data: OHLCV数据
            
        Returns:
            图表配置
        """
        config = self._create_base_config()
        config['title']['text'] = self.config.title or '成交量'
        
        date_col = '日期' if '日期' in data.columns else 'date'
        dates = data[date_col].tolist()
        
        # 成交量数据
        volume_col = '成交量' if '成交量' in data.columns else 'volume'
        close_col = '收盘' if '收盘' in data.columns else 'close'
        
        volumes = data[volume_col].tolist()
        closes = data[close_col].tolist()
        
        # 根据涨跌设置颜色
        colors = []
        for i in range(len(volumes)):
            if i == 0:
                colors.append(self.theme.get_technical_color('neutral'))
            else:
                if closes[i] >= closes[i-1]:
                    colors.append(self.theme.get_technical_color('up'))
                else:
                    colors.append(self.theme.get_technical_color('down'))
        
        config['xAxis'] = {
            'type': 'category',
            'data': dates,
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')}
        }
        
        config['yAxis'] = {
            'type': 'value',
            'name': '成交量',
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')},
            'splitLine': {'lineStyle': {'color': self.theme.get_theme_color('grid')}}
        }
        
        config['series'] = [{
            'name': '成交量',
            'type': 'bar',
            'data': [{'value': v, 'itemStyle': {'color': c}} for v, c in zip(volumes, colors)],
            'barWidth': '60%'
        }]
        
        return config
    
    def render_macd(self, dif: pd.Series, dea: pd.Series, macd: pd.Series, 
                   dates: pd.Series) -> Dict:
        """
        渲染MACD图
        
        Args:
            dif: DIF线
            dea: DEA线
            macd: MACD柱状图
            dates: 日期序列
            
        Returns:
            图表配置
        """
        config = self._create_base_config()
        config['title']['text'] = self.config.title or 'MACD'
        
        config['xAxis'] = {
            'type': 'category',
            'data': dates.tolist(),
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')}
        }
        
        config['yAxis'] = {
            'type': 'value',
            'name': 'MACD',
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')},
            'splitLine': {'lineStyle': {'color': self.theme.get_theme_color('grid')}}
        }
        
        # MACD柱状图颜色
        macd_colors = []
        for val in macd:
            if val >= 0:
                macd_colors.append(self.theme.get_technical_color('macd_positive'))
            else:
                macd_colors.append(self.theme.get_technical_color('macd_negative'))
        
        config['series'] = [
            {
                'name': 'DIF',
                'type': 'line',
                'data': dif.tolist(),
                'smooth': True,
                'lineStyle': {'width': 1},
                'symbol': 'none'
            },
            {
                'name': 'DEA',
                'type': 'line',
                'data': dea.tolist(),
                'smooth': True,
                'lineStyle': {'width': 1},
                'symbol': 'none'
            },
            {
                'name': 'MACD',
                'type': 'bar',
                'data': [{'value': v, 'itemStyle': {'color': c}} 
                        for v, c in zip(macd.tolist(), macd_colors)],
                'barWidth': '50%'
            }
        ]
        
        config['legend']['data'] = ['DIF', 'DEA', 'MACD']
        
        return config
    
    def render_rsi(self, rsi_data: Dict[str, pd.Series], dates: pd.Series) -> Dict:
        """
        渲染RSI图
        
        Args:
            rsi_data: RSI数据字典，如 {'RSI6': series, 'RSI12': series}
            dates: 日期序列
            
        Returns:
            图表配置
        """
        config = self._create_base_config()
        config['title']['text'] = self.config.title or 'RSI'
        
        config['xAxis'] = {
            'type': 'category',
            'data': dates.tolist(),
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')}
        }
        
        config['yAxis'] = {
            'type': 'value',
            'name': 'RSI',
            'min': 0,
            'max': 100,
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')},
            'splitLine': {'lineStyle': {'color': self.theme.get_theme_color('grid')}},
            'markLine': {
                'silent': True,
                'data': [
                    {'yAxis': 30, 'lineStyle': {'color': '#26a69a', 'type': 'dashed'}},
                    {'yAxis': 70, 'lineStyle': {'color': '#ef5350', 'type': 'dashed'}}
                ]
            }
        }
        
        config['series'] = []
        for name, values in rsi_data.items():
            config['series'].append({
                'name': name,
                'type': 'line',
                'data': values.tolist(),
                'smooth': True,
                'lineStyle': {'width': 1},
                'symbol': 'none'
            })
        
        config['legend']['data'] = list(rsi_data.keys())
        
        return config
    
    def render_kdj(self, k: pd.Series, d: pd.Series, j: pd.Series, 
                  dates: pd.Series) -> Dict:
        """
        渲染KDJ图
        
        Args:
            k: K值
            d: D值
            j: J值
            dates: 日期序列
            
        Returns:
            图表配置
        """
        config = self._create_base_config()
        config['title']['text'] = self.config.title or 'KDJ'
        
        config['xAxis'] = {
            'type': 'category',
            'data': dates.tolist(),
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')}
        }
        
        config['yAxis'] = {
            'type': 'value',
            'name': 'KDJ',
            'min': 0,
            'max': 100,
            'axisLine': {'lineStyle': {'color': self.theme.get_theme_color('axis')}},
            'axisLabel': {'color': self.theme.get_theme_color('text')},
            'splitLine': {'lineStyle': {'color': self.theme.get_theme_color('grid')}},
            'markLine': {
                'silent': True,
                'data': [
                    {'yAxis': 20, 'lineStyle': {'color': '#26a69a', 'type': 'dashed'}},
                    {'yAxis': 80, 'lineStyle': {'color': '#ef5350', 'type': 'dashed'}}
                ]
            }
        }
        
        config['series'] = [
            {
                'name': 'K',
                'type': 'line',
                'data': k.tolist(),
                'smooth': True,
                'lineStyle': {'width': 1},
                'symbol': 'none'
            },
            {
                'name': 'D',
                'type': 'line',
                'data': d.tolist(),
                'smooth': True,
                'lineStyle': {'width': 1},
                'symbol': 'none'
            },
            {
                'name': 'J',
                'type': 'line',
                'data': j.tolist(),
                'smooth': True,
                'lineStyle': {'width': 1},
                'symbol': 'none'
            }
        ]
        
        config['legend']['data'] = ['K', 'D', 'J']
        
        return config


class ChartDashboard:
    """图表仪表盘类 - 管理多个图表"""
    
    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or ChartConfig()
        self.renderer = TechnicalChartRenderer(self.config)
        self.data_processor = DataProcessor()
        self.charts: Dict[str, Dict] = {}
        self.update_callbacks: List[Callable] = []
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._data_queue: queue.Queue = queue.Queue()
    
    def add_chart(self, chart_id: str, chart_config: Dict) -> None:
        """
        添加图表
        
        Args:
            chart_id: 图表唯一标识
            chart_config: 图表配置
        """
        self.charts[chart_id] = chart_config
        logger.info(f"添加图表: {chart_id}")
    
    def remove_chart(self, chart_id: str) -> None:
        """
        移除图表
        
        Args:
            chart_id: 图表唯一标识
        """
        if chart_id in self.charts:
            del self.charts[chart_id]
            logger.info(f"移除图表: {chart_id}")
    
    def update_chart(self, chart_id: str, data: Any) -> None:
        """
        更新图表数据
        
        Args:
            chart_id: 图表唯一标识
            data: 新数据
        """
        if chart_id in self.charts:
            self._data_queue.put((chart_id, data))
            logger.debug(f"更新图表数据: {chart_id}")
    
    def create_kline_chart(self, data: pd.DataFrame, indicators: Optional[Dict] = None,
                          title: str = "K线图") -> str:
        """
        创建K线图
        
        Args:
            data: OHLCV数据
            indicators: 技术指标数据
            title: 图表标题
            
        Returns:
            图表ID
        """
        chart_id = f"kline_{int(time.time() * 1000)}_{id(data)}"
        self.config.title = title
        chart_config = self.renderer.render_candlestick(data, indicators)
        self.add_chart(chart_id, chart_config)
        return chart_id
    
    def create_volume_chart(self, data: pd.DataFrame, title: str = "成交量") -> str:
        """
        创建成交量图
        
        Args:
            data: OHLCV数据
            title: 图表标题
            
        Returns:
            图表ID
        """
        chart_id = f"volume_{int(time.time() * 1000)}_{id(data)}"
        self.config.title = title
        chart_config = self.renderer.render_volume(data)
        self.add_chart(chart_id, chart_config)
        return chart_id
    
    def create_macd_chart(self, dif: pd.Series, dea: pd.Series, macd: pd.Series,
                         dates: pd.Series, title: str = "MACD") -> str:
        """
        创建MACD图
        
        Args:
            dif: DIF线
            dea: DEA线
            macd: MACD柱状图
            dates: 日期序列
            title: 图表标题
            
        Returns:
            图表ID
        """
        chart_id = f"macd_{int(time.time() * 1000)}_{id(dif)}"
        self.config.title = title
        chart_config = self.renderer.render_macd(dif, dea, macd, dates)
        self.add_chart(chart_id, chart_config)
        return chart_id
    
    def create_rsi_chart(self, rsi_data: Dict[str, pd.Series], dates: pd.Series,
                        title: str = "RSI") -> str:
        """
        创建RSI图
        
        Args:
            rsi_data: RSI数据字典
            dates: 日期序列
            title: 图表标题
            
        Returns:
            图表ID
        """
        chart_id = f"rsi_{int(time.time() * 1000)}_{id(rsi_data)}"
        self.config.title = title
        chart_config = self.renderer.render_rsi(rsi_data, dates)
        self.add_chart(chart_id, chart_config)
        return chart_id
    
    def create_kdj_chart(self, k: pd.Series, d: pd.Series, j: pd.Series,
                        dates: pd.Series, title: str = "KDJ") -> str:
        """
        创建KDJ图
        
        Args:
            k: K值
            d: D值
            j: J值
            dates: 日期序列
            title: 图表标题
            
        Returns:
            图表ID
        """
        chart_id = f"kdj_{int(time.time() * 1000)}_{id(k)}"
        self.config.title = title
        chart_config = self.renderer.render_kdj(k, d, j, dates)
        self.add_chart(chart_id, chart_config)
        return chart_id
    
    def get_chart_config(self, chart_id: str) -> Optional[Dict]:
        """
        获取图表配置
        
        Args:
            chart_id: 图表唯一标识
            
        Returns:
            图表配置字典
        """
        return self.charts.get(chart_id)
    
    def get_all_charts(self) -> Dict[str, Dict]:
        """
        获取所有图表配置
        
        Returns:
            所有图表配置字典
        """
        return self.charts.copy()
    
    def export_chart(self, chart_id: str, format: str = 'json') -> Union[str, Dict]:
        """
        导出图表配置
        
        Args:
            chart_id: 图表唯一标识
            format: 导出格式，'json'或'dict'
            
        Returns:
            图表配置
        """
        config = self.charts.get(chart_id)
        if config is None:
            raise ValueError(f"图表不存在: {chart_id}")
        
        # 转换config为可JSON序列化的格式
        def convert_to_serializable(obj):
            if isinstance(obj, pd.Timestamp):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'date':
                return obj.strftime('%Y-%m-%d')
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, tuple):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_config = convert_to_serializable(config)
        
        if format == 'json':
            return json.dumps(serializable_config, ensure_ascii=False, indent=2)
        else:
            return serializable_config
    
    def set_theme(self, theme: Theme) -> None:
        """
        设置主题
        
        Args:
            theme: 主题模式
        """
        self.config.theme = theme
        self.renderer.theme = ChartTheme(theme)
        logger.info(f"设置主题: {theme.value}")
    
    def start_auto_update(self, interval: int = 60) -> None:
        """
        启动自动更新
        
        Args:
            interval: 更新间隔（秒）
        """
        if self._update_thread and self._update_thread.is_alive():
            logger.warning("自动更新已在运行")
            return
        
        self._stop_event.clear()
        self._update_thread = threading.Thread(target=self._update_loop, args=(interval,))
        self._update_thread.daemon = True
        self._update_thread.start()
        logger.info(f"启动自动更新，间隔: {interval}秒")
    
    def stop_auto_update(self) -> None:
        """停止自动更新"""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=5)
        logger.info("停止自动更新")
    
    def _update_loop(self, interval: int) -> None:
        """更新循环"""
        while not self._stop_event.is_set():
            try:
                # 处理数据队列
                while not self._data_queue.empty():
                    chart_id, data = self._data_queue.get_nowait()
                    # 触发更新回调
                    for callback in self.update_callbacks:
                        callback(chart_id, data)
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"自动更新出错: {e}")
    
    def register_update_callback(self, callback: Callable) -> None:
        """
        注册更新回调函数
        
        Args:
            callback: 回调函数，参数为(chart_id, data)
        """
        self.update_callbacks.append(callback)
    
    def unregister_update_callback(self, callback: Callable) -> None:
        """
        注销更新回调函数
        
        Args:
            callback: 回调函数
        """
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)


# HTML模板生成器
class HTMLTemplateGenerator:
    """HTML模板生成器"""
    
    @staticmethod
    def generate_chart_html(chart_config: Dict, container_id: str = "chart") -> str:
        """
        生成图表HTML
        
        Args:
            chart_config: 图表配置
            container_id: 容器ID
            
        Returns:
            HTML字符串
        """
        def convert_to_serializable(obj):
            """转换为可JSON序列化的格式"""
            if isinstance(obj, pd.Timestamp):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'date':
                return obj.strftime('%Y-%m-%d')
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, tuple):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_config = convert_to_serializable(chart_config)
        config_json = json.dumps(serializable_config, ensure_ascii=False)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{chart_config.get('title', {}).get('text', '图表')}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: {chart_config.get('backgroundColor', '#ffffff')};
        }}
        #chart {{
            width: {chart_config.get('width', 1200)}px;
            height: {chart_config.get('height', 600)}px;
        }}
    </style>
</head>
<body>
    <div id="{container_id}"></div>
    <script>
        var chart = echarts.init(document.getElementById('{container_id}'));
        var option = {config_json};
        chart.setOption(option);
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            chart.resize();
        }});
    </script>
</body>
</html>"""
        return html
    
    @staticmethod
    def generate_dashboard_html(charts: Dict[str, Dict], title: str = "技术指标仪表盘") -> str:
        """
        生成仪表盘HTML
        
        Args:
            charts: 图表配置字典
            title: 页面标题
            
        Returns:
            HTML字符串
        """
        chart_divs = []
        chart_scripts = []
        
        def convert_to_serializable(obj):
            """转换为可JSON序列化的格式"""
            if isinstance(obj, pd.Timestamp):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'date':
                return obj.strftime('%Y-%m-%d')
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, tuple):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        for i, (chart_id, config) in enumerate(charts.items()):
            container_id = f"chart_{i}"
            serializable_config = convert_to_serializable(config)
            config_json = json.dumps(serializable_config, ensure_ascii=False)
            
            chart_divs.append(f'<div id="{container_id}" style="width: 100%; height: 400px; margin-bottom: 20px;"></div>')
            chart_scripts.append(f"""
                var chart_{i} = echarts.init(document.getElementById('{container_id}'));
                chart_{i}.setOption({config_json});
                charts.push(chart_{i});
            """)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #333;
            margin: 0;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
    </div>
    {''.join(chart_divs)}
    <script>
        var charts = [];
        {''.join(chart_scripts)}
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            charts.forEach(function(chart) {{
                chart.resize();
            }});
        }});
    </script>
</body>
</html>"""
        return html


if __name__ == "__main__":
    # 示例用法
    from ak_fund import AkFund
    from technical_indicators import TechnicalIndicators
    
    # 获取股票数据
    ak_fund = AkFund()
    stock_data = ak_fund.get_stock_kline('600519', period='daily', 
                                        start_date='2023-01-01', 
                                        end_date='2023-12-31')
    
    # 计算技术指标
    ti = TechnicalIndicators(stock_data)
    indicators = ti.calculate_all()
    
    # 创建图表仪表盘
    dashboard = ChartDashboard(ChartConfig(
        width=1200,
        height=600,
        theme=Theme.LIGHT,
        title="贵州茅台技术指标分析"
    ))
    
    # 创建K线图
    kline_chart_id = dashboard.create_kline_chart(
        stock_data,
        indicators={
            'MA5': indicators['MA5'],
            'MA10': indicators['MA10'],
            'MA20': indicators['MA20']
        },
        title="K线图与移动平均线"
    )
    
    # 创建成交量图
    volume_chart_id = dashboard.create_volume_chart(stock_data)
    
    # 创建MACD图
    macd_chart_id = dashboard.create_macd_chart(
        indicators['DIF'],
        indicators['DEA'],
        indicators['MACD'],
        stock_data['日期'] if '日期' in stock_data.columns else stock_data['date']
    )
    
    # 创建RSI图
    rsi_chart_id = dashboard.create_rsi_chart(
        {
            'RSI6': indicators['RSI6'],
            'RSI12': indicators['RSI12'],
            'RSI24': indicators['RSI24']
        },
        stock_data['日期'] if '日期' in stock_data.columns else stock_data['date']
    )
    
    # 创建KDJ图
    kdj_chart_id = dashboard.create_kdj_chart(
        indicators['K'],
        indicators['D'],
        indicators['J'],
        stock_data['日期'] if '日期' in stock_data.columns else stock_data['date']
    )
    
    # 导出HTML
    html_generator = HTMLTemplateGenerator()
    
    # 导出单个图表
    kline_config = dashboard.get_chart_config(kline_chart_id)
    kline_html = html_generator.generate_chart_html(kline_config, "kline_chart")
    
    with open('kline_chart.html', 'w', encoding='utf-8') as f:
        f.write(kline_html)
    
    # 导出仪表盘
    all_charts = dashboard.get_all_charts()
    dashboard_html = html_generator.generate_dashboard_html(all_charts)
    
    with open('technical_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print("图表导出完成！")
    print("- kline_chart.html: K线图")
    print("- technical_dashboard.html: 技术指标仪表盘")
