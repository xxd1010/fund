"""
工作流模块
包含技术指标计算和基金加权分析的工作流
"""

from .base import BaseWorkflow
from .technical import TechnicalIndicatorWorkflow
from .analysis import FundAnalysisWorkflow

__all__ = [
    'BaseWorkflow',
    'TechnicalIndicatorWorkflow',
    'FundAnalysisWorkflow',
]