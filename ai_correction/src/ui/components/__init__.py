#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI组件包
包含所有用户界面组件
"""

from .assignment_center import AssignmentCenter
from .submission_interface import SubmissionInterface
from .grading_dashboard import GradingDashboard

__all__ = [
    'AssignmentCenter',
    'SubmissionInterface', 
    'GradingDashboard'
]