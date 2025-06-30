"""
AI批改系统API模块
提供简化的两种批改模式：
1. 有批改标准模式
2. 无批改标准模式（自动生成）
"""

from .calling_api import (
    # 核心批改函数
    batch_correction_with_standard,
    batch_correction_without_standard,
    
    # 智能批改函数（自动选择模式）
    intelligent_correction_with_files,
    
    # 简化版批改函数
    simplified_batch_correction,
    
    # Web接口
    web_correction_with_scheme,
    web_correction_without_scheme,
    web_batch_correction,
    
    # API配置相关
    get_api_status,
    update_api_config,
    api_config,
    
    # 工具函数
    GradingResult,
    
    # 向后兼容（保留旧版函数名）
    correction_with_marking_scheme,
    correction_without_marking_scheme,
    generate_marking_scheme,
    efficient_correction_single,
    batch_efficient_correction,
    correction_single_group,
    
    # 核心API调用函数
    call_tongyiqianwen_api,
    img_to_base64,
)

__all__ = [
    # 新版简化函数
    'batch_correction_with_standard',
    'batch_correction_without_standard',
    'intelligent_correction_with_files',
    'simplified_batch_correction',
    
    # Web接口
    'web_correction_with_scheme',
    'web_correction_without_scheme', 
    'web_batch_correction',
    
    # API配置
    'get_api_status',
    'update_api_config',
    'api_config',
    
    # 工具类
    'GradingResult',
    
    # 向后兼容
    'correction_with_marking_scheme',
    'correction_without_marking_scheme',
    'generate_marking_scheme',
    'efficient_correction_single',
    'batch_efficient_correction',
    'correction_single_group',
    
    # 核心API调用函数
    'call_tongyiqianwen_api',
    'img_to_base64',
] 