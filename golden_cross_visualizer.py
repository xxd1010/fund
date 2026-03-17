"""
金叉/死叉可视化模块
提供专业的技术信号可视化展示功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime
from loguru import logger
import json


class GoldenCrossVisualizer:
    """
    金叉/死叉可视化器
    
    提供基于ECharts的金叉/死叉信号可视化功能
    """
    
    def __init__(self, data: pd.DataFrame, signals: Dict[str, pd.DataFrame]):
        """
        初始化可视化器
        
        Args:
            data: 原始OHLCV数据
            signals: 信号字典，包含golden_cross和death_cross的DataFrame
        """
        self.data = data.copy()
        self.signals = signals
        self._validate_data()
    
    def _validate_data(self) -> None:
        """验证输入数据"""
        if self.data.empty:
            raise ValueError("输入数据不能为空")
        
        # 检查必要的列
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in self.data.columns for col in required_cols):
            # 检查中文列名
            required_cols_cn = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
            if not all(col in self.data.columns for col in required_cols_cn):
                raise ValueError("数据必须包含OHLCV列")
    
    def _get_column(self, col_name: str) -> pd.Series:
        """获取指定列的数据（支持中英文列名）"""
        col_mapping = {
            'date': '日期',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量'
        }
        
        if col_name in self.data.columns:
            return self.data[col_name]
        elif col_name in col_mapping and col_mapping[col_name] in self.data.columns:
            return self.data[col_mapping[col_name]]
        else:
            raise ValueError(f"找不到列 '{col_name}'")
    
    def _convert_to_serializable(self, obj):
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
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return [self._convert_to_serializable(item) for item in obj]
        else:
            return obj
    
    def generate_kline_with_signals(self, short_period: int = 5, 
                                    long_period: int = 20,
                                    show_ma: bool = True) -> Dict:
        """
        生成带信号的K线图配置
        
        Args:
            short_period: 短期均线周期
            long_period: 长期均线周期
            show_ma: 是否显示均线
            
        Returns:
            ECharts配置字典
        """
        # 准备数据
        dates = self._get_column('date').astype(str).tolist()
        kline_data = [
            [self._get_column('open').iloc[i],
             self._get_column('close').iloc[i],
             self._get_column('low').iloc[i],
             self._get_column('high').iloc[i]]
            for i in range(len(self.data))
        ]
        
        # 计算均线
        close = self._get_column('close')
        short_ma = close.rolling(window=short_period).mean().tolist()
        long_ma = close.rolling(window=long_period).mean().tolist()
        
        # 准备信号标记点
        mark_points = []
        
        # 添加金叉标记
        if 'golden_cross' in self.signals and not self.signals['golden_cross'].empty:
            golden_crosses = self.signals['golden_cross']
            for idx, row in golden_crosses.iterrows():
                signal_date = str(row['date'])
                if signal_date in dates:
                    date_idx = dates.index(signal_date)
                    mark_points.append({
                        'name': '金叉',
                        'coord': [date_idx, row['price']],
                        'value': '金叉',
                        'itemStyle': {
                            'color': '#ff4d4d'
                        },
                        'symbol': 'triangle',
                        'symbolSize': 15,
                        'label': {
                            'show': True,
                            'position': 'top',
                            'formatter': '金叉'
                        }
                    })
        
        # 添加死叉标记
        if 'death_cross' in self.signals and not self.signals['death_cross'].empty:
            death_crosses = self.signals['death_cross']
            for idx, row in death_crosses.iterrows():
                signal_date = str(row['date'])
                if signal_date in dates:
                    date_idx = dates.index(signal_date)
                    mark_points.append({
                        'name': '死叉',
                        'coord': [date_idx, row['price']],
                        'value': '死叉',
                        'itemStyle': {
                            'color': '#4b92ff'
                        },
                        'symbol': 'triangle',
                        'symbolSize': 15,
                        'label': {
                            'show': True,
                            'position': 'bottom',
                            'formatter': '死叉'
                        }
                    })
        
        # 构建ECharts配置
        config = {
            'title': {
                'text': '金叉/死叉K线图',
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'cross'
                }
            },
            'legend': {
                'data': ['K线', '短期均线', '长期均线'],
                'bottom': 10
            },
            'grid': [
                {
                    'left': '10%',
                    'right': '10%',
                    'top': '15%',
                    'height': '60%'
                },
                {
                    'left': '10%',
                    'right': '10%',
                    'top': '80%',
                    'height': '15%'
                }
            ],
            'xAxis': [
                {
                    'type': 'category',
                    'data': dates,
                    'scale': True,
                    'boundaryGap': False,
                    'axisLine': {'onZero': False},
                    'splitLine': {'show': False},
                    'min': 'dataMin',
                    'max': 'dataMax'
                },
                {
                    'type': 'category',
                    'gridIndex': 1,
                    'data': dates,
                    'axisLabel': {'show': False}
                }
            ],
            'yAxis': [
                {
                    'scale': True,
                    'splitArea': {
                        'show': True
                    }
                },
                {
                    'scale': True,
                    'gridIndex': 1,
                    'splitNumber': 2,
                    'axisLabel': {'show': False},
                    'axisLine': {'show': False},
                    'splitLine': {'show': False}
                }
            ],
            'dataZoom': [
                {
                    'type': 'inside',
                    'xAxisIndex': [0, 1],
                    'start': 0,
                    'end': 100
                },
                {
                    'show': True,
                    'xAxisIndex': [0, 1],
                    'type': 'slider',
                    'top': '90%',
                    'start': 0,
                    'end': 100
                }
            ],
            'series': [
                {
                    'name': 'K线',
                    'type': 'candlestick',
                    'data': kline_data,
                    'markPoint': {
                        'data': mark_points
                    },
                    'itemStyle': {
                        'color': '#ef4136',
                        'color0': '#4b92ff',
                        'borderColor': '#ef4136',
                        'borderColor0': '#4b92ff'
                    }
                }
            ]
        }
        
        # 添加均线
        if show_ma:
            config['series'].append({
                'name': '短期均线',
                'type': 'line',
                'data': short_ma,
                'smooth': True,
                'lineStyle': {
                    'opacity': 0.8
                }
            })
            config['series'].append({
                'name': '长期均线',
                'type': 'line',
                'data': long_ma,
                'smooth': True,
                'lineStyle': {
                    'opacity': 0.8
                }
            })
        
        # 添加成交量
        volume_data = self._get_column('volume').tolist()
        config['series'].append({
            'name': '成交量',
            'type': 'bar',
            'xAxisIndex': 1,
            'yAxisIndex': 1,
            'data': volume_data,
            'itemStyle': {
                'color': '#7fbe87'
            }
        })
        
        return self._convert_to_serializable(config)
    
    def generate_signal_strength_chart(self) -> Dict:
        """
        生成信号强度图表
        
        Returns:
            ECharts配置字典
        """
        # 准备数据
        all_signals = []
        
        if 'golden_cross' in self.signals and not self.signals['golden_cross'].empty:
            golden_crosses = self.signals['golden_cross'].copy()
            golden_crosses['signal_type'] = '金叉'
            all_signals.append(golden_crosses)
        
        if 'death_cross' in self.signals and not self.signals['death_cross'].empty:
            death_crosses = self.signals['death_cross'].copy()
            death_crosses['signal_type'] = '死叉'
            all_signals.append(death_crosses)
        
        if not all_signals:
            return {'title': {'text': '暂无信号数据'}}
        
        # 合并所有信号
        signals_df = pd.concat(all_signals).sort_values('date')
        
        # 准备图表数据
        dates = signals_df['date'].astype(str).tolist()
        strengths = signals_df['strength'].tolist()
        signal_types = signals_df['signal_type'].tolist()
        
        # 构建ECharts配置
        config = {
            'title': {
                'text': '信号强度分析',
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'axis',
                'formatter': function_formatter
            },
            'legend': {
                'data': ['金叉强度', '死叉强度'],
                'bottom': 10
            },
            'xAxis': {
                'type': 'category',
                'data': dates,
                'axisLabel': {
                    'rotate': 45
                }
            },
            'yAxis': {
                'type': 'value',
                'name': '强度',
                'max': 1.0,
                'min': 0.0
            },
            'series': [
                {
                    'name': '金叉强度',
                    'type': 'bar',
                    'data': [
                        {
                            'value': strength,
                            'itemStyle': {
                                'color': '#ff4d4d' if signal_type == '金叉' else '#4b92ff'
                            }
                        }
                        for strength, signal_type in zip(strengths, signal_types)
                    ]
                }
            ]
        }
        
        return self._convert_to_serializable(config)
    
    def generate_performance_chart(self, backtest_results: Dict) -> Dict:
        """
        生成回测性能图表
        
        Args:
            backtest_results: 回测结果字典
            
        Returns:
            ECharts配置字典
        """
        if 'detailed_results' not in backtest_results or backtest_results['detailed_results'].empty:
            return {'title': {'text': '暂无回测数据'}}
        
        detailed_results = backtest_results['detailed_results']
        
        # 准备数据
        dates = detailed_results['date'].astype(str).tolist()
        profits = detailed_results['profit'].tolist()
        
        # 计算累计收益
        cumulative_profits = np.cumsum(profits).tolist()
        
        # 构建ECharts配置
        config = {
            'title': {
                'text': '回测性能分析',
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'axis',
                'formatter': function_formatter
            },
            'legend': {
                'data': ['单笔收益', '累计收益'],
                'bottom': 10
            },
            'xAxis': {
                'type': 'category',
                'data': dates,
                'axisLabel': {
                    'rotate': 45
                }
            },
            'yAxis': {
                'type': 'value',
                'name': '收益 (%)'
            },
            'series': [
                {
                    'name': '单笔收益',
                    'type': 'bar',
                    'data': [
                        {
                            'value': profit,
                            'itemStyle': {
                                'color': '#ef4136' if profit < 0 else '#4b92ff'
                            }
                        }
                        for profit in profits
                    ]
                },
                {
                    'name': '累计收益',
                    'type': 'line',
                    'data': cumulative_profits,
                    'smooth': True,
                    'lineStyle': {
                        'width': 3
                    },
                    'itemStyle': {
                        'color': '#7fbe87'
                    }
                }
            ]
        }
        
        return self._convert_to_serializable(config)
    
    def generate_multi_timeframe_chart(self, multi_timeframe_data: Dict) -> Dict:
        """
        生成多时间周期对比图表
        
        Args:
            multi_timeframe_data: 多时间周期数据字典
            
        Returns:
            ECharts配置字典
        """
        # 准备数据
        timeframes = []
        golden_counts = []
        death_counts = []
        
        for timeframe, data in multi_timeframe_data.items():
            timeframes.append(timeframe)
            golden_count = len(data.get('golden_cross', pd.DataFrame()))
            death_count = len(data.get('death_cross', pd.DataFrame()))
            golden_counts.append(golden_count)
            death_counts.append(death_count)
        
        # 构建ECharts配置
        config = {
            'title': {
                'text': '多时间周期信号对比',
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'shadow'
                }
            },
            'legend': {
                'data': ['金叉数量', '死叉数量'],
                'bottom': 10
            },
            'xAxis': {
                'type': 'category',
                'data': timeframes
            },
            'yAxis': {
                'type': 'value',
                'name': '信号数量'
            },
            'series': [
                {
                    'name': '金叉数量',
                    'type': 'bar',
                    'data': golden_counts,
                    'itemStyle': {
                        'color': '#ff4d4d'
                    }
                },
                {
                    'name': '死叉数量',
                    'type': 'bar',
                    'data': death_counts,
                    'itemStyle': {
                        'color': '#4b92ff'
                    }
                }
            ]
        }
        
        return self._convert_to_serializable(config)
    
    def generate_dashboard(self, short_period: int = 5, 
                        long_period: int = 20,
                        backtest_results: Optional[Dict] = None,
                        multi_timeframe_data: Optional[Dict] = None) -> Dict:
        """
        生成完整仪表盘配置
        
        Args:
            short_period: 短期均线周期
            long_period: 长期均线周期
            backtest_results: 回测结果
            multi_timeframe_data: 多时间周期数据
            
        Returns:
            仪表盘配置字典
        """
        dashboard = {
            'title': '金叉/死叉分析仪表盘',
            'charts': []
        }
        
        # K线图
        kline_config = self.generate_kline_with_signals(short_period, long_period)
        dashboard['charts'].append({
            'id': 'kline_chart',
            'title': 'K线图',
            'config': kline_config
        })
        
        # 信号强度图
        strength_config = self.generate_signal_strength_chart()
        dashboard['charts'].append({
            'id': 'strength_chart',
            'title': '信号强度',
            'config': strength_config
        })
        
        # 回测性能图
        if backtest_results:
            performance_config = self.generate_performance_chart(backtest_results)
            dashboard['charts'].append({
                'id': 'performance_chart',
                'title': '回测性能',
                'config': performance_config
            })
        
        # 多时间周期图
        if multi_timeframe_data:
            multi_config = self.generate_multi_timeframe_chart(multi_timeframe_data)
            dashboard['charts'].append({
                'id': 'multi_timeframe_chart',
                'title': '多时间周期对比',
                'config': multi_config
            })
        
        return self._convert_to_serializable(dashboard)
    
    def export_html(self, output_file: str = 'golden_cross_dashboard.html',
                   short_period: int = 5, 
                   long_period: int = 20,
                   backtest_results: Optional[Dict] = None,
                   multi_timeframe_data: Optional[Dict] = None) -> str:
        """
        导出HTML文件
        
        Args:
            output_file: 输出文件名
            short_period: 短期均线周期
            long_period: 长期均线周期
            backtest_results: 回测结果
            multi_timeframe_data: 多时间周期数据
            
        Returns:
            HTML字符串
        """
        # 生成仪表盘配置
        dashboard = self.generate_dashboard(
            short_period, long_period, backtest_results, multi_timeframe_data
        )
        
        # 生成HTML
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>金叉/死叉分析仪表盘</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .dashboard-title {{
            text-align: center;
            color: #1a1a2e;
            margin-bottom: 30px;
            font-size: 28px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        .chart {{
            width: 100%;
            height: 500px;
        }}
        .chart-title {{
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
            border-bottom: 2px solid #4b92ff;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <h1 class="dashboard-title">{{dashboard['title']}}</h1>
        
        <div class="chart-container">
            <h2 class="chart-title">K线图</h2>
            <div id="kline_chart" class="chart"></div>
        </div>
        
        <div class="chart-container">
            <h2 class="chart-title">信号强度</h2>
            <div id="strength_chart" class="chart"></div>
        </div>
        
        <div class="chart-container">
            <h2 class="chart-title">回测性能</h2>
            <div id="performance_chart" class="chart"></div>
        </div>
        
        <div class="chart-container">
            <h2 class="chart-title">多时间周期对比</h2>
            <div id="multi_timeframe_chart" class="chart"></div>
        </div>
    </div>
    
    <script>
        // 初始化图表
        const charts = {{}};
        
        // K线图
        const klineChart = echarts.init(document.getElementById('kline_chart'));
        klineChart.setOption({json.dumps(dashboard['charts'][0]['config'], ensure_ascii=False, indent=2)});
        charts['kline_chart'] = klineChart;
        
        // 信号强度图
        const strengthChart = echarts.init(document.getElementById('strength_chart'));
        strengthChart.setOption({json.dumps(dashboard['charts'][1]['config'], ensure_ascii=False, indent=2)});
        charts['strength_chart'] = strengthChart;
        
        // 回测性能图
        const performanceChart = echarts.init(document.getElementById('performance_chart'));
        performanceChart.setOption({json.dumps(dashboard['charts'][2]['config'], ensure_ascii=False, indent=2)});
        charts['performance_chart'] = performanceChart;
        
        // 多时间周期图
        const multiChart = echarts.init(document.getElementById('multi_timeframe_chart'));
        multiChart.setOption({json.dumps(dashboard['charts'][3]['config'], ensure_ascii=False, indent=2)});
        charts['multi_timeframe_chart'] = multiChart;
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            Object.values(charts).forEach(chart => chart.resize());
        }});
    </script>
</body>
</html>
"""
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        logger.info(f"仪表盘已导出到 {output_file}")
        return html_template


def function_formatter(params):
    """ECharts格式化函数"""
    if isinstance(params, list) and len(params) > 0:
        param = params[0]
        if param.seriesName == '金叉强度' or param.seriesName == '死叉强度':
            return f"日期: {{param.name}}<br/>信号类型: {{param.seriesName}}<br/>强度: {{param.value:.2f}}"
        elif param.seriesName == '单笔收益' or param.seriesName == '累计收益':
            return f"日期: {{param.name}}<br/>{{param.seriesName}}: {{param.value:.2f}}%"
    return str(params)
