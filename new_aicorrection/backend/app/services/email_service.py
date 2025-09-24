"""Email service for sending notifications and communications."""

import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, Template

from app.core.config import get_settings
from app.models.notification import NotificationType

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails with templates and tracking."""
    
    def __init__(self):
        self.settings = get_settings()
        self.smtp_host = self.settings.SMTP_HOST
        self.smtp_port = self.settings.SMTP_PORT
        self.smtp_username = self.settings.SMTP_USERNAME
        self.smtp_password = self.settings.SMTP_PASSWORD
        self.smtp_use_tls = getattr(self.settings, 'SMTP_USE_TLS', True)
        self.from_email = getattr(self.settings, 'FROM_EMAIL', self.smtp_username)
        self.from_name = getattr(self.settings, 'FROM_NAME', 'AI智能批改系统')
        
        # Initialize Jinja2 environment for templates
        self.template_env = Environment(
            loader=FileSystemLoader('app/templates/email'),
            autoescape=True
        )
        
        # Email templates
        self.templates = {
            NotificationType.ASSIGNMENT_PUBLISHED: 'assignment_published.html',
            NotificationType.ASSIGNMENT_DUE_SOON: 'assignment_due_soon.html',
            NotificationType.ASSIGNMENT_OVERDUE: 'assignment_overdue.html',
            NotificationType.SUBMISSION_GRADED: 'submission_graded.html',
            NotificationType.SUBMISSION_RETURNED: 'submission_returned.html',
            'default': 'notification_default.html',
            'welcome': 'welcome.html',
            'password_reset': 'password_reset.html',
            'email_verification': 'email_verification.html'
        }
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """Send an email with HTML and optional text content."""
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{from_name or self.from_name} <{from_email or self.from_email}>"
            message['To'] = to_email
            
            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(html_part)
            
            # Send email
            if self.smtp_host and self.smtp_username and self.smtp_password:
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_username,
                    password=self.smtp_password,
                    use_tls=self.smtp_use_tls
                )
                
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.warning(f"SMTP not configured, email to {to_email} not sent")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_notification_email(
        self,
        to_email: str,
        user_name: str,
        title: str,
        content: str,
        notification_type: NotificationType,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a notification email using appropriate template."""
        try:
            # Get template for notification type
            template_name = self.templates.get(notification_type, self.templates['default'])
            
            # Prepare template context
            context = {
                'user_name': user_name,
                'title': title,
                'content': content,
                'notification_type': notification_type,
                'data': data or {},
                'system_name': self.from_name,
                'current_year': datetime.now().year
            }
            
            # Add specific context based on notification type
            if notification_type == NotificationType.ASSIGNMENT_PUBLISHED:
                context.update({
                    'assignment_title': data.get('assignment_title', ''),
                    'due_date': data.get('due_date'),
                    'total_points': data.get('total_points'),
                    'class_id': data.get('class_id')
                })
            elif notification_type == NotificationType.ASSIGNMENT_DUE_SOON:
                context.update({
                    'assignment_title': data.get('assignment_title', ''),
                    'due_date': data.get('due_date'),
                    'hours_before': data.get('hours_before', 24)
                })
            elif notification_type == NotificationType.SUBMISSION_GRADED:
                context.update({
                    'assignment_title': data.get('assignment_title', ''),
                    'score': data.get('score'),
                    'max_score': data.get('max_score'),
                    'grade_percentage': data.get('grade_percentage'),
                    'feedback': data.get('feedback', '')
                })
            
            # Render template
            html_content = await self._render_template(template_name, context)
            
            # Generate subject
            subject = self._generate_subject(notification_type, title, data)
            
            # Send email
            return await self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification email to {to_email}: {e}")
            return False
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        user_role: str,
        verification_token: Optional[str] = None
    ) -> bool:
        """Send welcome email to new users."""
        try:
            context = {
                'user_name': user_name,
                'user_role': user_role,
                'system_name': self.from_name,
                'verification_token': verification_token,
                'current_year': datetime.now().year
            }
            
            html_content = await self._render_template('welcome.html', context)
            subject = f"欢迎加入{self.from_name}！"
            
            return await self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {to_email}: {e}")
            return False
    
    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
        reset_url: str
    ) -> bool:
        """Send password reset email."""
        try:
            context = {
                'user_name': user_name,
                'reset_token': reset_token,
                'reset_url': reset_url,
                'system_name': self.from_name,
                'current_year': datetime.now().year
            }
            
            html_content = await self._render_template('password_reset.html', context)
            subject = f"{self.from_name} - 密码重置请求"
            
            return await self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            return False
    
    async def send_email_verification(
        self,
        to_email: str,
        user_name: str,
        verification_token: str,
        verification_url: str
    ) -> bool:
        """Send email verification email."""
        try:
            context = {
                'user_name': user_name,
                'verification_token': verification_token,
                'verification_url': verification_url,
                'system_name': self.from_name,
                'current_year': datetime.now().year
            }
            
            html_content = await self._render_template('email_verification.html', context)
            subject = f"{self.from_name} - 邮箱验证"
            
            return await self.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send email verification to {to_email}: {e}")
            return False
    
    async def send_bulk_emails(
        self,
        email_data: List[Dict[str, Any]],
        batch_size: int = 10,
        delay_between_batches: float = 1.0
    ) -> Dict[str, Any]:
        """Send multiple emails in batches."""
        total_emails = len(email_data)
        successful_emails = 0
        failed_emails = 0
        results = []
        
        # Process emails in batches
        for i in range(0, total_emails, batch_size):
            batch = email_data[i:i + batch_size]
            batch_results = []
            
            # Send batch concurrently
            tasks = []
            for email_info in batch:
                task = self.send_email(
                    to_email=email_info['to_email'],
                    subject=email_info['subject'],
                    html_content=email_info['html_content'],
                    text_content=email_info.get('text_content'),
                    from_email=email_info.get('from_email'),
                    from_name=email_info.get('from_name')
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                email_info = batch[j]
                if isinstance(result, Exception):
                    failed_emails += 1
                    results.append({
                        'to_email': email_info['to_email'],
                        'success': False,
                        'error': str(result)
                    })
                else:
                    if result:
                        successful_emails += 1
                    else:
                        failed_emails += 1
                    results.append({
                        'to_email': email_info['to_email'],
                        'success': result,
                        'error': None if result else 'Unknown error'
                    })
            
            # Delay between batches to avoid overwhelming SMTP server
            if i + batch_size < total_emails:
                await asyncio.sleep(delay_between_batches)
        
        return {
            'total_emails': total_emails,
            'successful_emails': successful_emails,
            'failed_emails': failed_emails,
            'results': results,
            'sent_at': datetime.utcnow().isoformat()
        }
    
    async def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        try:
            template = self.template_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            # Fallback to simple template
            return await self._render_fallback_template(context)
    
    async def _render_fallback_template(self, context: Dict[str, Any]) -> str:
        """Render a simple fallback template when main template fails."""
        fallback_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #f8f9fa; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ system_name }}</h1>
                </div>
                <div class="content">
                    <h2>{{ title }}</h2>
                    <p>{{ content }}</p>
                </div>
                <div class="footer">
                    <p>&copy; {{ current_year }} {{ system_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(fallback_template)
        return template.render(**context)
    
    def _generate_subject(
        self,
        notification_type: NotificationType,
        title: str,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate email subject based on notification type."""
        subject_templates = {
            NotificationType.ASSIGNMENT_PUBLISHED: f"[{self.from_name}] 新作业发布",
            NotificationType.ASSIGNMENT_DUE_SOON: f"[{self.from_name}] 作业即将截止",
            NotificationType.ASSIGNMENT_OVERDUE: f"[{self.from_name}] 作业已逾期",
            NotificationType.SUBMISSION_GRADED: f"[{self.from_name}] 作业已批改",
            NotificationType.SUBMISSION_RETURNED: f"[{self.from_name}] 作业已返还",
            NotificationType.SUBMISSION_RECEIVED: f"[{self.from_name}] 收到作业提交",
            NotificationType.CLASS_ANNOUNCEMENT: f"[{self.from_name}] 班级通知",
            NotificationType.SYSTEM_UPDATE: f"[{self.from_name}] 系统更新",
            NotificationType.AI_FEEDBACK: f"[{self.from_name}] AI学习建议",
            NotificationType.PARENT_UPDATE: f"[{self.from_name}] 学习进展更新"
        }
        
        base_subject = subject_templates.get(notification_type, f"[{self.from_name}] 通知")
        
        # Add specific details if available
        if data and notification_type in [
            NotificationType.ASSIGNMENT_PUBLISHED,
            NotificationType.ASSIGNMENT_DUE_SOON,
            NotificationType.ASSIGNMENT_OVERDUE,
            NotificationType.SUBMISSION_GRADED,
            NotificationType.SUBMISSION_RETURNED
        ]:
            assignment_title = data.get('assignment_title')
            if assignment_title:
                base_subject += f" - {assignment_title}"
        
        return base_subject
    
    async def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            if not all([self.smtp_host, self.smtp_username, self.smtp_password]):
                logger.warning("SMTP configuration incomplete")
                return False
            
            # Test connection
            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls
            )
            
            await smtp.connect()
            await smtp.login(self.smtp_username, self.smtp_password)
            await smtp.quit()
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False


# Email template creation helper
def create_email_templates():
    """Create default email templates if they don't exist."""
    import os
    
    template_dir = "app/templates/email"
    os.makedirs(template_dir, exist_ok=True)
    
    templates = {
        'notification_default.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px 20px; }
        .content h2 { color: #333; margin-top: 0; }
        .notification-box { background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }
        .button { display: inline-block; padding: 12px 24px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ system_name }}</h1>
        </div>
        <div class="content">
            <h2>{{ title }}</h2>
            <div class="notification-box">
                <p>{{ content }}</p>
            </div>
            {% if data.action_url %}
            <a href="{{ data.action_url }}" class="button">{{ data.action_text or '查看详情' }}</a>
            {% endif %}
        </div>
        <div class="footer">
            <p>&copy; {{ current_year }} {{ system_name }}. All rights reserved.</p>
            <p>如果您不希望接收此类邮件，请联系系统管理员。</p>
        </div>
    </div>
</body>
</html>
        """,
        
        'assignment_published.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>新作业发布 - {{ assignment_title }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
        .header { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 30px 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px 20px; }
        .assignment-info { background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .info-row { display: flex; justify-content: space-between; margin: 10px 0; }
        .info-label { font-weight: bold; color: #555; }
        .due-date { color: #e74c3c; font-weight: bold; }
        .button { display: inline-block; padding: 12px 24px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 新作业发布</h1>
        </div>
        <div class="content">
            <p>亲爱的 {{ user_name }}，</p>
            <p>您有一个新的作业需要完成：</p>
            
            <div class="assignment-info">
                <h3>{{ assignment_title }}</h3>
                {% if due_date %}
                <div class="info-row">
                    <span class="info-label">截止时间：</span>
                    <span class="due-date">{{ due_date }}</span>
                </div>
                {% endif %}
                {% if total_points %}
                <div class="info-row">
                    <span class="info-label">总分：</span>
                    <span>{{ total_points }} 分</span>
                </div>
                {% endif %}
            </div>
            
            <p>请及时完成并提交作业。如有疑问，请联系您的教师。</p>
            
            <a href="{{ data.action_url or '#' }}" class="button">查看作业详情</a>
        </div>
        <div class="footer">
            <p>&copy; {{ current_year }} {{ system_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """,
        
        'assignment_due_soon.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>作业即将截止 - {{ assignment_title }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
        .header { background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 30px 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px 20px; }
        .warning-box { background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .due-time { font-size: 18px; font-weight: bold; color: #e74c3c; text-align: center; margin: 15px 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #ff9800; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ 作业即将截止</h1>
        </div>
        <div class="content">
            <p>亲爱的 {{ user_name }}，</p>
            
            <div class="warning-box">
                <h3>{{ assignment_title }}</h3>
                <div class="due-time">
                    将在 {{ hours_before }} 小时后截止！
                </div>
                {% if due_date %}
                <p><strong>截止时间：</strong>{{ due_date }}</p>
                {% endif %}
            </div>
            
            <p>请抓紧时间完成并提交您的作业。逾期提交可能会影响您的成绩。</p>
            
            <a href="{{ data.action_url or '#' }}" class="button">立即提交作业</a>
        </div>
        <div class="footer">
            <p>&copy; {{ current_year }} {{ system_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """,
        
        'submission_graded.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>作业已批改 - {{ assignment_title }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
        .header { background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); color: white; padding: 30px 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px 20px; }
        .grade-box { background-color: #e3f2fd; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }
        .grade-score { font-size: 36px; font-weight: bold; color: #1976D2; margin: 10px 0; }
        .grade-percentage { font-size: 18px; color: #666; }
        .feedback-box { background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ 作业已批改</h1>
        </div>
        <div class="content">
            <p>亲爱的 {{ user_name }}，</p>
            <p>您的作业 <strong>{{ assignment_title }}</strong> 已经批改完成！</p>
            
            <div class="grade-box">
                <div class="grade-score">{{ score }}/{{ max_score }}</div>
                {% if grade_percentage %}
                <div class="grade-percentage">{{ grade_percentage }}%</div>
                {% endif %}
            </div>
            
            {% if feedback %}
            <div class="feedback-box">
                <h4>教师反馈：</h4>
                <p>{{ feedback }}</p>
            </div>
            {% endif %}
            
            <a href="{{ data.action_url or '#' }}" class="button">查看详细结果</a>
        </div>
        <div class="footer">
            <p>&copy; {{ current_year }} {{ system_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """
    }
    
    for filename, content in templates.items():
        filepath = os.path.join(template_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            print(f"Created email template: {filepath}")