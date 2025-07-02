#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF处理工具模块
专门处理PDF相关操作，抑制MuPDF错误输出
"""

import os
import sys
import warnings
import contextlib
import logging
from io import StringIO
import tempfile

# 抑制所有警告
warnings.filterwarnings("ignore")

class SuppressOutput:
    """上下文管理器：抑制stdout和stderr输出"""
    
    def __init__(self, suppress_stdout=True, suppress_stderr=True):
        self.suppress_stdout = suppress_stdout
        self.suppress_stderr = suppress_stderr
        
    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        if self.suppress_stdout:
            sys.stdout = open(os.devnull, 'w')
        if self.suppress_stderr:
            sys.stderr = open(os.devnull, 'w')
            
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.suppress_stdout:
            sys.stdout.close()
            sys.stdout = self.original_stdout
        if self.suppress_stderr:
            sys.stderr.close()
            sys.stderr = self.original_stderr

def safe_pdf_processing(func):
    """装饰器：为PDF处理函数添加错误抑制"""
    def wrapper(*args, **kwargs):
        with SuppressOutput():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 只记录关键错误，忽略MuPDF的格式错误
                if "xref" not in str(e).lower() and "format error" not in str(e).lower():
                    logging.warning(f"PDF处理警告: {str(e)}")
                return None
    return wrapper

@safe_pdf_processing
def safe_pdf_open(pdf_path):
    """安全地打开PDF文件"""
    try:
        import fitz
        return fitz.open(pdf_path)
    except Exception:
        return None

@safe_pdf_processing
def safe_page_to_image(page, matrix):
    """安全地将PDF页面转换为图像"""
    try:
        return page.get_pixmap(matrix=matrix, alpha=False)
    except Exception:
        # 尝试更简单的转换
        try:
            return page.get_pixmap(alpha=False)
        except Exception:
            return None

def suppress_mupdf_errors():
    """全局抑制MuPDF错误输出"""
    # 重定向stderr到null
    if hasattr(os, 'devnull'):
        devnull = open(os.devnull, 'w')
        sys.stderr = devnull
    
    # 设置环境变量抑制MuPDF输出
    os.environ['MUPDF_QUIET'] = '1'
    
    # 抑制Python警告
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

# 在模块加载时就抑制错误
suppress_mupdf_errors() 