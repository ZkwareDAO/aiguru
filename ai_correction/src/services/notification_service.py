#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知服务
扩展现有通知系统支持班级作业批改相关通知
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from database import add_notification, get_user_notifications
from src.models.assignment import Assignment
from src.models.submission import Submission
from src.infrastructure.logging import get_logger


class NotificationType(Enum):
    """通知类型"""
    ASSIGNMENT_PUBLISHED = "assignment_published"
    ASSIGNMENT_DEADLINE_REMINDER = "assignment_deadline_reminder"
    SUBMISSION_RECEIVED = "submission_received"
    GRADING_COMPLETED = "grading_completed"
    GRADING_UPDATED = "grading_updated"
    TEACHER_FEEDBACK_MODIFIED = "teacher_feedback_modified"
    ASSIGNMENT_SHARED = "assignment_shared"
    CLASS_ANNOUNCEMENT = "class_announcement"


@dataclass
class NotificationTemplate:
    """通知模板"""
    type: NotificationType
    title_template: str
    content_template: str
    priority: str = "info"  # info, success, warning, error
    
    def format(self, **kwargs) -> Dict[str, str]:
        """格式化通知内容"""
        return {
            'title': self.title_template.format(**kwargs),
            'content': self.content_template.format(**kwargs),
            'type': self.priority
        }


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.NotificationService")
        self._templates = self._initialize_templates()
        self.logger.info("通知服务已初始化")
    
    def _initialize_templates(self) -> Dict[NotificationType, NotificationTemplate]:
        """初始化通知模板"""
        return {
            NotificationType.ASSIGNMENT_PUBLISHED: NotificationTemplate(
                type=NotificationType.ASSIGNMENT_PUBLISHED,
                title_template="新作业发布：{assignment_title}",
                content_template="教师 {teacher_name} 发布了新作业《{assignment_title}》。\n"
                               "截止时间：{deadline}\n"
                               "请及时查看作业要求并完成提交。",
                priority="info"
            ),
            
            NotificationType.ASSIGNMENT_DEADLINE_REMINDER: NotificationTemplate(
                type=NotificationType.ASSIGNMENT_DEADLINE_REMINDER,
                title_template="作业截止提醒：{assignment_title}",
                content_template="作业《{assignment_title}》将在 {hours_left} 小时后截止。\n"
                               "截止时间：{deadline}\n"
                               "请尽快完成并提交作业。",
                priority="warning"
            ),
            
            NotificationType.SUBMISSION_RECEIVED: NotificationTemplate(
                type=NotificationType.SUBMISSION_RECEIVED,
                title_template="收到学生提交：{assignment_title}",
                content_template="学生 {student_name} 提交了作业《{assignment_title}》。\n"
                               "提交时间：{submission_time}\n"
                               "系统正在进行自动批改，请稍后查看结果。",
                priority="info"
            ),
            
            NotificationType.GRADING_COMPLETED: NotificationTemplate(
                type=NotificationType.GRADING_COMPLETED,
                title_template="作业已批改：{assignment_title}",
                content_template="您的作业《{assignment_title}》已完成批改。\n"
                               "得分：{score}\n"
                               "批改时间：{grading_time}\n"
                               "请查看详细反馈和建议。",
                priority="success"
            ),
            
            NotificationType.GRADING_UPDATED: NotificationTemplate(
                type=NotificationType.GRADING_UPDATED,
                title_template="批改结果已更新：{assignment_title}",
                content_template="教师对您的作业《{assignment_title}》批改结果进行了更新。\n"
                               "更新时间：{update_time}\n"
                               "请查看最新的反馈和评分。",
                priority="info"
            ),
            
            NotificationType.TEACHER_FEEDBACK_MODIFIED: NotificationTemplate(
                type=NotificationType.TEACHER_FEEDBACK_MODIFIED,
                title_template="教师反馈已修改：{assignment_title}",
                content_template="教师对您的作业《{assignment_title}》提供了新的反馈。\n"
                               "修改时间：{modification_time}\n"
                               "请查看教师的详细评语和建议。",
                priority="info"
            ),
            
            NotificationType.ASSIGNMENT_SHARED: NotificationTemplate(
                type=NotificationType.ASSIGNMENT_SHARED,
                title_template="优秀作业分享：{assignment_title}",
                content_template="教师分享了作业《{assignment_title}》的优秀答案。\n"
                               "分享时间：{share_time}\n"
                               "请查看优秀作业，学习借鉴。",
                priority="success"
            ),
            
            NotificationType.CLASS_ANNOUNCEMENT: NotificationTemplate(
                type=NotificationType.CLASS_ANNOUNCEMENT,
                title_template="班级公告：{announcement_title}",
                content_template="{announcement_content}\n"
                               "发布时间：{publish_time}\n"
                               "发布者：{publisher_name}",
                priority="info"
            )
        }
    
    def send_assignment_published_notification(self, assignment: Assignment, 
                                             student_usernames: List[str],
                                             teacher_name: str) -> bool:
        """发送作业发布通知"""
        try:
            template = self._templates[NotificationType.ASSIGNMENT_PUBLISHED]
            
            notification_data = template.format(
                assignment_title=assignment.title,
                teacher_name=teacher_name,
                deadline=assignment.deadline.strftime("%Y-%m-%d %H:%M") if assignment.deadline else "无限制"
            )
            
            success_count = 0
            for username in student_usernames:
                if add_notification(
                    username=username,
                    title=notification_data['title'],
                    content=notification_data['content'],
                    type=notification_data['type']
                ):
                    success_count += 1
            
            self.logger.info(f"作业发布通知已发送: {assignment.title}, 成功: {success_count}/{len(student_usernames)}")
            return success_count == len(student_usernames)
            
        except Exception as e:
            self.logger.error(f"发送作业发布通知失败: {e}")
            return False
    
    def send_deadline_reminder_notification(self, assignment: Assignment,
                                          student_usernames: List[str],
                                          hours_left: int) -> bool:
        """发送作业截止提醒通知"""
        try:
            template = self._templates[NotificationType.ASSIGNMENT_DEADLINE_REMINDER]
            
            notification_data = template.format(
                assignment_title=assignment.title,
                hours_left=hours_left,
                deadline=assignment.deadline.strftime("%Y-%m-%d %H:%M") if assignment.deadline else "无限制"
            )
            
            success_count = 0
            for username in student_usernames:
                if add_notification(
                    username=username,
                    title=notification_data['title'],
                    content=notification_data['content'],
                    type=notification_data['type']
                ):
                    success_count += 1
            
            self.logger.info(f"截止提醒通知已发送: {assignment.title}, 成功: {success_count}/{len(student_usernames)}")
            return success_count == len(student_usernames)
            
        except Exception as e:
            self.logger.error(f"发送截止提醒通知失败: {e}")
            return False
    
    def send_submission_received_notification(self, submission: Submission,
                                            assignment: Assignment,
                                            teacher_username: str,
                                            student_name: str) -> bool:
        """发送学生提交通知给教师"""
        try:
            template = self._templates[NotificationType.SUBMISSION_RECEIVED]
            
            notification_data = template.format(
                assignment_title=assignment.title,
                student_name=student_name,
                submission_time=submission.submitted_at.strftime("%Y-%m-%d %H:%M")
            )
            
            success = add_notification(
                username=teacher_username,
                title=notification_data['title'],
                content=notification_data['content'],
                type=notification_data['type']
            )
            
            if success:
                self.logger.info(f"学生提交通知已发送给教师: {teacher_username}, 作业: {assignment.title}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送学生提交通知失败: {e}")
            return False
    
    def send_grading_completed_notification(self, submission: Submission,
                                          assignment: Assignment,
                                          score: Optional[float] = None) -> bool:
        """发送批改完成通知给学生"""
        try:
            template = self._templates[NotificationType.GRADING_COMPLETED]
            
            score_text = f"{score}分" if score is not None else "待评分"
            
            notification_data = template.format(
                assignment_title=assignment.title,
                score=score_text,
                grading_time=submission.graded_at.strftime("%Y-%m-%d %H:%M") if submission.graded_at else datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            success = add_notification(
                username=submission.student_username,
                title=notification_data['title'],
                content=notification_data['content'],
                type=notification_data['type']
            )
            
            if success:
                self.logger.info(f"批改完成通知已发送给学生: {submission.student_username}, 作业: {assignment.title}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送批改完成通知失败: {e}")
            return False
    
    def send_grading_updated_notification(self, submission: Submission,
                                        assignment: Assignment) -> bool:
        """发送批改结果更新通知给学生"""
        try:
            template = self._templates[NotificationType.GRADING_UPDATED]
            
            notification_data = template.format(
                assignment_title=assignment.title,
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            success = add_notification(
                username=submission.student_username,
                title=notification_data['title'],
                content=notification_data['content'],
                type=notification_data['type']
            )
            
            if success:
                self.logger.info(f"批改更新通知已发送给学生: {submission.student_username}, 作业: {assignment.title}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送批改更新通知失败: {e}")
            return False
    
    def send_teacher_feedback_modified_notification(self, submission: Submission,
                                                   assignment: Assignment) -> bool:
        """发送教师反馈修改通知给学生"""
        try:
            template = self._templates[NotificationType.TEACHER_FEEDBACK_MODIFIED]
            
            notification_data = template.format(
                assignment_title=assignment.title,
                modification_time=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            success = add_notification(
                username=submission.student_username,
                title=notification_data['title'],
                content=notification_data['content'],
                type=notification_data['type']
            )
            
            if success:
                self.logger.info(f"教师反馈修改通知已发送给学生: {submission.student_username}, 作业: {assignment.title}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送教师反馈修改通知失败: {e}")
            return False
    
    def send_assignment_shared_notification(self, assignment: Assignment,
                                          student_usernames: List[str]) -> bool:
        """发送优秀作业分享通知"""
        try:
            template = self._templates[NotificationType.ASSIGNMENT_SHARED]
            
            notification_data = template.format(
                assignment_title=assignment.title,
                share_time=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            success_count = 0
            for username in student_usernames:
                if add_notification(
                    username=username,
                    title=notification_data['title'],
                    content=notification_data['content'],
                    type=notification_data['type']
                ):
                    success_count += 1
            
            self.logger.info(f"优秀作业分享通知已发送: {assignment.title}, 成功: {success_count}/{len(student_usernames)}")
            return success_count == len(student_usernames)
            
        except Exception as e:
            self.logger.error(f"发送优秀作业分享通知失败: {e}")
            return False
    
    def send_class_announcement_notification(self, class_id: int,
                                           student_usernames: List[str],
                                           announcement_title: str,
                                           announcement_content: str,
                                           publisher_name: str) -> bool:
        """发送班级公告通知"""
        try:
            template = self._templates[NotificationType.CLASS_ANNOUNCEMENT]
            
            notification_data = template.format(
                announcement_title=announcement_title,
                announcement_content=announcement_content,
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                publisher_name=publisher_name
            )
            
            success_count = 0
            for username in student_usernames:
                if add_notification(
                    username=username,
                    title=notification_data['title'],
                    content=notification_data['content'],
                    type=notification_data['type']
                ):
                    success_count += 1
            
            self.logger.info(f"班级公告通知已发送: {announcement_title}, 成功: {success_count}/{len(student_usernames)}")
            return success_count == len(student_usernames)
            
        except Exception as e:
            self.logger.error(f"发送班级公告通知失败: {e}")
            return False
    
    def get_user_notifications_enhanced(self, username: str, 
                                      notification_type: Optional[NotificationType] = None,
                                      limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户通知（增强版）"""
        try:
            notifications = get_user_notifications(username, limit)
            
            # 如果指定了通知类型，进行过滤
            if notification_type:
                filtered_notifications = []
                template = self._templates.get(notification_type)
                if template:
                    # 根据标题模板进行简单匹配
                    title_prefix = template.title_template.split('：')[0] if '：' in template.title_template else template.title_template.split(':')[0]
                    for notification in notifications:
                        if notification['title'].startswith(title_prefix):
                            filtered_notifications.append(notification)
                    notifications = filtered_notifications
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"获取用户通知失败: {e}")
            return []
    
    def schedule_deadline_reminders(self, assignment: Assignment,
                                  student_usernames: List[str]) -> bool:
        """安排截止日期提醒"""
        try:
            if not assignment.deadline:
                return True  # 无截止日期，无需提醒
            
            current_time = datetime.now()
            deadline = assignment.deadline
            
            # 计算提醒时间点（24小时前、6小时前、1小时前）
            reminder_times = [
                deadline - timedelta(hours=24),
                deadline - timedelta(hours=6),
                deadline - timedelta(hours=1)
            ]
            
            scheduled_count = 0
            for reminder_time in reminder_times:
                if reminder_time > current_time:
                    hours_left = int((deadline - reminder_time).total_seconds() / 3600)
                    
                    # 这里应该集成到任务调度系统中
                    # 暂时记录日志，实际实现时需要使用任务队列
                    self.logger.info(f"已安排截止提醒: 作业 {assignment.title}, "
                                   f"提醒时间: {reminder_time.strftime('%Y-%m-%d %H:%M')}, "
                                   f"剩余时间: {hours_left}小时")
                    scheduled_count += 1
            
            return scheduled_count > 0
            
        except Exception as e:
            self.logger.error(f"安排截止日期提醒失败: {e}")
            return False
    
    def get_notification_statistics(self, username: str) -> Dict[str, Any]:
        """获取通知统计信息"""
        try:
            notifications = get_user_notifications(username, limit=1000)
            
            total_count = len(notifications)
            unread_count = sum(1 for n in notifications if not n.get('is_read', False))
            
            # 按类型统计
            type_counts = {}
            for notification in notifications:
                # 简单的类型识别，基于标题
                notification_type = "其他"
                for ntype, template in self._templates.items():
                    title_prefix = template.title_template.split('：')[0] if '：' in template.title_template else template.title_template.split(':')[0]
                    if notification['title'].startswith(title_prefix):
                        notification_type = ntype.value
                        break
                
                type_counts[notification_type] = type_counts.get(notification_type, 0) + 1
            
            return {
                'total_count': total_count,
                'unread_count': unread_count,
                'type_counts': type_counts,
                'last_notification_time': notifications[0]['created_at'] if notifications else None
            }
            
        except Exception as e:
            self.logger.error(f"获取通知统计失败: {e}")
            return {
                'total_count': 0,
                'unread_count': 0,
                'type_counts': {},
                'last_notification_time': None
            }


# 全局通知服务实例
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service