# 系统管理员指南

## 概述

本指南面向班级作业批改系统的系统管理员，详细介绍系统的安装、配置、监控、维护和故障排除等操作。

## 目录

1. [系统架构](#系统架构)
2. [安装部署](#安装部署)
3. [系统配置](#系统配置)
4. [用户管理](#用户管理)
5. [监控维护](#监控维护)
6. [备份恢复](#备份恢复)
7. [故障排除](#故障排除)
8. [性能优化](#性能优化)
9. [安全管理](#安全管理)

## 系统架构

### 1.1 整体架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   应用服务      │    │   数据存储      │
│   (Streamlit)   │◄──►│   (Python)      │◄──►│   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   AI批改引擎    │
                       │   (集成模块)    │
                       └─────────────────┘
```

### 1.2 核心组件

- **Web应用服务**：基于Streamlit的用户界面
- **业务逻辑层**：Python服务和数据处理
- **数据存储层**：SQLite数据库和文件存储
- **AI批改引擎**：集成的智能批改模块
- **任务队列系统**：异步任务处理
- **文件管理系统**：作业和批改文件存储

### 1.3 系统依赖

#### Python环境
- Python 3.8+
- 虚拟环境管理
- 依赖包管理

#### 数据库
- SQLite 3.x
- 数据库文件存储
- 备份和恢复工具

#### 文件系统
- 本地文件存储
- 目录权限管理
- 磁盘空间监控

## 安装部署

### 2.1 环境准备

#### 系统要求
- **操作系统**：Windows 10+, Linux, macOS
- **内存**：最低4GB，推荐8GB+
- **磁盘空间**：最低10GB，推荐50GB+
- **网络**：稳定的互联网连接

#### 软件依赖
```bash
# Python环境
python --version  # 确保3.8+

# 包管理工具
pip install --upgrade pip
pip install virtualenv

# 数据库工具
sqlite3 --version
```

### 2.2 安装步骤

#### 1. 获取源代码
```bash
# 从代码仓库获取
git clone <repository-url>
cd classroom-grading-system

# 或解压发布包
unzip classroom-grading-system-v1.0.zip
cd classroom-grading-system
```

#### 2. 创建虚拟环境
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

#### 3. 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 验证安装
python -c "import streamlit; print('Streamlit installed successfully')"
```

#### 4. 初始化数据库
```bash
# 运行数据库初始化脚本
python scripts/init_database.py

# 验证数据库
sqlite3 class_system.db ".tables"
```

#### 5. 配置系统
```bash
# 复制配置模板
cp config_template.env .env

# 编辑配置文件
nano .env
```

### 2.3 启动系统

#### 开发环境启动
```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 启动应用
streamlit run streamlit_simple.py --server.port 8501
```

#### 生产环境启动
```bash
# 使用启动脚本
./start.sh

# 或使用批处理文件 (Windows)
start.bat
```

### 2.4 验证安装

1. **访问系统**：浏览器打开 http://localhost:8501
2. **登录测试**：使用默认管理员账号登录
3. **功能测试**：创建测试班级和作业
4. **日志检查**：查看系统日志确认无错误

## 系统配置

### 3.1 环境配置文件

#### .env 配置文件
```bash
# 数据库配置
DATABASE_URL=sqlite:///class_system.db
DATABASE_BACKUP_PATH=./backups/

# 文件存储配置
UPLOAD_PATH=./uploads/
MAX_FILE_SIZE=52428800  # 50MB
ALLOWED_EXTENSIONS=pdf,doc,docx,txt,jpg,png

# AI批改配置
AI_ENGINE_URL=http://localhost:8000
AI_ENGINE_API_KEY=your_api_key_here
AI_TIMEOUT=300

# 邮件配置
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=system@example.com
SMTP_PASSWORD=your_password

# 安全配置
SECRET_KEY=your_secret_key_here
JWT_EXPIRATION=3600
PASSWORD_MIN_LENGTH=8

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/system.log
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

### 3.2 数据库配置

#### 数据库连接设置
```python
# config/database.py
DATABASE_CONFIG = {
    'path': 'class_system.db',
    'timeout': 30,
    'check_same_thread': False,
    'isolation_level': None
}
```

#### 连接池配置
```python
CONNECTION_POOL = {
    'max_connections': 10,
    'min_connections': 2,
    'connection_timeout': 30,
    'idle_timeout': 300
}
```

### 3.3 AI批改引擎配置

#### 批改参数配置
```yaml
# config/ai_optimization.yaml
ai_grading:
  default_model: "gpt-3.5-turbo"
  max_tokens: 2000
  temperature: 0.3
  timeout: 300
  
grading_standards:
  strict_mode: false
  confidence_threshold: 0.8
  require_manual_review: true
  
performance:
  batch_size: 10
  concurrent_requests: 5
  retry_attempts: 3
```

### 3.4 文件存储配置

#### 存储路径配置
```yaml
# config/file_storage.yaml
storage:
  base_path: "./uploads"
  assignments_path: "assignments"
  submissions_path: "submissions"
  grading_results_path: "grading_results"
  
limits:
  max_file_size: 52428800  # 50MB
  max_files_per_submission: 10
  allowed_extensions:
    - pdf
    - doc
    - docx
    - txt
    - jpg
    - png
    
cleanup:
  auto_cleanup: true
  retention_days: 365
  archive_old_files: true
```

## 用户管理

### 4.1 用户账号管理

#### 创建管理员账号
```bash
# 使用命令行工具
python scripts/create_admin.py --username admin --password admin123 --email admin@example.com

# 或使用交互式脚本
python scripts/user_management.py
```

#### 批量创建用户
```bash
# 从CSV文件批量导入
python scripts/import_users.py --file users.csv --type teacher

# CSV格式示例
# username,password,email,role,full_name
# teacher1,temp123,teacher1@school.com,teacher,张老师
# student1,temp123,student1@school.com,student,张三
```

#### 用户权限管理
```python
# 权限级别
PERMISSIONS = {
    'admin': ['all'],
    'teacher': ['create_assignment', 'manage_class', 'view_submissions'],
    'student': ['submit_assignment', 'view_results']
}
```

### 4.2 班级管理

#### 批量创建班级
```python
# scripts/create_classes.py
classes_data = [
    {'name': '高一(1)班数学', 'subject': '数学', 'grade': '高一', 'teacher': 'teacher1'},
    {'name': '高一(2)班数学', 'subject': '数学', 'grade': '高一', 'teacher': 'teacher2'},
]

for class_data in classes_data:
    create_class(**class_data)
```

#### 学生班级分配
```bash
# 批量分配学生到班级
python scripts/assign_students.py --class_id 1 --students student1,student2,student3
```

### 4.3 权限控制

#### 角色权限配置
```python
# src/config/permissions.py
ROLE_PERMISSIONS = {
    'admin': {
        'users': ['create', 'read', 'update', 'delete'],
        'classes': ['create', 'read', 'update', 'delete'],
        'assignments': ['create', 'read', 'update', 'delete'],
        'system': ['configure', 'monitor', 'backup']
    },
    'teacher': {
        'classes': ['read', 'update'],  # 只能管理自己的班级
        'assignments': ['create', 'read', 'update', 'delete'],  # 只能管理自己的作业
        'submissions': ['read', 'update']  # 只能查看和批改自己班级的提交
    },
    'student': {
        'assignments': ['read'],  # 只能查看自己班级的作业
        'submissions': ['create', 'read']  # 只能提交和查看自己的作业
    }
}
```

## 监控维护

### 5.1 系统监控

#### 实时监控脚本
```python
# scripts/system_monitor.py
import psutil
import sqlite3
import time
from datetime import datetime

def monitor_system():
    while True:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # 数据库连接数
        db_connections = get_db_connections()
        
        # 记录监控数据
        log_monitoring_data({
            'timestamp': datetime.now(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'db_connections': db_connections
        })
        
        # 检查告警条件
        check_alerts(cpu_percent, memory_percent, disk_percent)
        
        time.sleep(60)  # 每分钟检查一次
```

#### 应用监控
```python
# src/infrastructure/monitoring.py
class ApplicationMonitor:
    def __init__(self):
        self.metrics = {
            'active_users': 0,
            'grading_tasks_pending': 0,
            'grading_tasks_processing': 0,
            'grading_tasks_completed': 0,
            'file_upload_errors': 0,
            'ai_grading_errors': 0
        }
    
    def update_metrics(self):
        """更新应用指标"""
        self.metrics['active_users'] = self.get_active_users_count()
        self.metrics['grading_tasks_pending'] = self.get_pending_tasks_count()
        # ... 更新其他指标
    
    def check_health(self):
        """健康检查"""
        checks = {
            'database': self.check_database_health(),
            'file_system': self.check_file_system_health(),
            'ai_engine': self.check_ai_engine_health(),
            'task_queue': self.check_task_queue_health()
        }
        return all(checks.values()), checks
```

### 5.2 日志管理

#### 日志配置
```python
# src/infrastructure/logging.py
import logging
import logging.handlers
from datetime import datetime

def setup_logging():
    # 创建日志器
    logger = logging.getLogger('classroom_system')
    logger.setLevel(logging.INFO)
    
    # 文件处理器 - 按大小轮转
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/system.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # 按时间轮转的处理器
    time_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/daily.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    file_handler.setFormatter(formatter)
    time_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(time_handler)
    
    return logger
```

#### 日志分析脚本
```bash
#!/bin/bash
# scripts/analyze_logs.sh

# 统计错误日志
echo "=== 错误统计 ==="
grep "ERROR" logs/system.log | wc -l

# 统计用户活动
echo "=== 用户活动统计 ==="
grep "User login" logs/system.log | awk '{print $6}' | sort | uniq -c

# 统计批改任务
echo "=== 批改任务统计 ==="
grep "Grading task" logs/system.log | grep "completed" | wc -l

# 检查系统性能
echo "=== 性能指标 ==="
grep "Performance" logs/system.log | tail -10
```

### 5.3 告警系统

#### 告警配置
```python
# src/infrastructure/alerts.py
class AlertManager:
    def __init__(self):
        self.alert_rules = {
            'high_cpu': {'threshold': 80, 'duration': 300},
            'high_memory': {'threshold': 85, 'duration': 300},
            'high_disk': {'threshold': 90, 'duration': 60},
            'db_connection_limit': {'threshold': 8, 'duration': 60},
            'grading_queue_backlog': {'threshold': 100, 'duration': 600}
        }
    
    def check_alerts(self, metrics):
        """检查告警条件"""
        alerts = []
        
        if metrics['cpu_percent'] > self.alert_rules['high_cpu']['threshold']:
            alerts.append({
                'type': 'high_cpu',
                'message': f"CPU使用率过高: {metrics['cpu_percent']}%",
                'severity': 'warning'
            })
        
        if metrics['memory_percent'] > self.alert_rules['high_memory']['threshold']:
            alerts.append({
                'type': 'high_memory',
                'message': f"内存使用率过高: {metrics['memory_percent']}%",
                'severity': 'warning'
            })
        
        return alerts
    
    def send_alert(self, alert):
        """发送告警"""
        # 邮件告警
        self.send_email_alert(alert)
        
        # 日志记录
        logging.error(f"ALERT: {alert['message']}")
        
        # 系统通知
        self.send_system_notification(alert)
```

## 备份恢复

### 6.1 数据备份

#### 自动备份脚本
```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backup_${TIMESTAMP}.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
echo "备份数据库..."
sqlite3 class_system.db ".backup ${BACKUP_DIR}/database_${TIMESTAMP}.db"

# 备份上传文件
echo "备份文件..."
tar -czf ${BACKUP_DIR}/files_${TIMESTAMP}.tar.gz uploads/

# 备份配置文件
echo "备份配置..."
tar -czf ${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz config/ .env

# 创建完整备份
echo "创建完整备份..."
tar -czf ${BACKUP_DIR}/${BACKUP_FILE} \
    class_system.db \
    uploads/ \
    config/ \
    .env \
    logs/

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "备份完成: ${BACKUP_DIR}/${BACKUP_FILE}"
```

#### 定时备份设置
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点执行备份
0 2 * * * /path/to/classroom-system/scripts/backup.sh

# 每周日凌晨1点执行完整备份
0 1 * * 0 /path/to/classroom-system/scripts/full_backup.sh
```

### 6.2 数据恢复

#### 恢复脚本
```bash
#!/bin/bash
# scripts/restore.sh

if [ $# -eq 0 ]; then
    echo "用法: $0 <备份文件>"
    exit 1
fi

BACKUP_FILE=$1
RESTORE_DIR="./restore_temp"

# 创建临时恢复目录
mkdir -p $RESTORE_DIR

# 解压备份文件
echo "解压备份文件..."
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# 停止应用服务
echo "停止应用服务..."
pkill -f streamlit

# 备份当前数据
echo "备份当前数据..."
cp class_system.db class_system.db.backup.$(date +%Y%m%d_%H%M%S)

# 恢复数据库
echo "恢复数据库..."
cp $RESTORE_DIR/class_system.db ./

# 恢复文件
echo "恢复文件..."
rm -rf uploads/
cp -r $RESTORE_DIR/uploads ./

# 恢复配置
echo "恢复配置..."
cp -r $RESTORE_DIR/config ./
cp $RESTORE_DIR/.env ./

# 清理临时目录
rm -rf $RESTORE_DIR

# 重启应用服务
echo "重启应用服务..."
./start.sh

echo "恢复完成"
```

### 6.3 灾难恢复

#### 灾难恢复计划
```markdown
## 灾难恢复步骤

### 1. 评估损坏程度
- 检查数据库文件完整性
- 检查文件系统状态
- 评估数据丢失范围

### 2. 选择恢复策略
- **完全恢复**：从最新完整备份恢复
- **增量恢复**：从基础备份+增量备份恢复
- **部分恢复**：仅恢复关键数据

### 3. 执行恢复操作
- 停止所有服务
- 恢复数据库
- 恢复文件系统
- 验证数据完整性

### 4. 服务重启和验证
- 重启应用服务
- 执行功能测试
- 通知用户服务恢复
```

## 故障排除

### 7.1 常见问题诊断

#### 数据库问题
```python
# scripts/diagnose_db.py
import sqlite3
import os

def diagnose_database():
    db_path = 'class_system.db'
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print("错误: 数据库文件不存在")
        return False
    
    try:
        # 检查数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库表: {[table[0] for table in tables]}")
        
        # 检查数据完整性
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()
        print(f"数据完整性: {integrity[0]}")
        
        # 检查数据库大小
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        size = cursor.fetchone()[0]
        print(f"数据库大小: {size} bytes")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"数据库错误: {e}")
        return False
```

#### 文件系统问题
```bash
#!/bin/bash
# scripts/diagnose_files.sh

echo "=== 文件系统诊断 ==="

# 检查上传目录
if [ -d "uploads" ]; then
    echo "上传目录存在"
    echo "目录大小: $(du -sh uploads)"
    echo "文件数量: $(find uploads -type f | wc -l)"
else
    echo "错误: 上传目录不存在"
fi

# 检查磁盘空间
echo "磁盘使用情况:"
df -h .

# 检查文件权限
echo "目录权限:"
ls -la uploads/

# 检查文件完整性
echo "检查损坏文件:"
find uploads -name "*.pdf" -exec file {} \; | grep -v "PDF document"
```

#### 性能问题诊断
```python
# scripts/diagnose_performance.py
import psutil
import time
import sqlite3

def diagnose_performance():
    print("=== 性能诊断 ===")
    
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=5)
    print(f"CPU使用率: {cpu_percent}%")
    
    # 内存使用情况
    memory = psutil.virtual_memory()
    print(f"内存使用率: {memory.percent}%")
    print(f"可用内存: {memory.available / 1024 / 1024:.2f} MB")
    
    # 磁盘I/O
    disk_io = psutil.disk_io_counters()
    print(f"磁盘读取: {disk_io.read_bytes / 1024 / 1024:.2f} MB")
    print(f"磁盘写入: {disk_io.write_bytes / 1024 / 1024:.2f} MB")
    
    # 数据库性能
    start_time = time.time()
    conn = sqlite3.connect('class_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assignments")
    result = cursor.fetchone()
    end_time = time.time()
    conn.close()
    
    print(f"数据库查询时间: {(end_time - start_time) * 1000:.2f} ms")
    print(f"作业总数: {result[0]}")
```

### 7.2 错误处理

#### 应用错误恢复
```python
# src/infrastructure/error_recovery.py
class ErrorRecoveryManager:
    def __init__(self):
        self.recovery_strategies = {
            'database_lock': self.recover_database_lock,
            'file_corruption': self.recover_file_corruption,
            'ai_service_down': self.recover_ai_service,
            'memory_leak': self.recover_memory_leak
        }
    
    def handle_error(self, error_type, context):
        """处理系统错误"""
        if error_type in self.recovery_strategies:
            return self.recovery_strategies[error_type](context)
        else:
            return self.generic_error_recovery(error_type, context)
    
    def recover_database_lock(self, context):
        """恢复数据库锁定"""
        # 等待锁释放
        time.sleep(5)
        # 重试操作
        return self.retry_database_operation(context)
    
    def recover_file_corruption(self, context):
        """恢复文件损坏"""
        # 从备份恢复文件
        return self.restore_file_from_backup(context['file_path'])
    
    def recover_ai_service(self, context):
        """恢复AI服务"""
        # 切换到备用服务或降级处理
        return self.fallback_to_manual_grading(context)
```

## 性能优化

### 8.1 数据库优化

#### 索引优化
```sql
-- 为常用查询创建索引
CREATE INDEX idx_assignments_class_id ON assignments(class_id);
CREATE INDEX idx_submissions_assignment_id ON submissions(assignment_id);
CREATE INDEX idx_submissions_student_username ON submissions(student_username);
CREATE INDEX idx_grading_tasks_status ON grading_tasks(status);
CREATE INDEX idx_grading_tasks_created_at ON grading_tasks(created_at);

-- 复合索引
CREATE INDEX idx_submissions_assignment_student ON submissions(assignment_id, student_username);
CREATE INDEX idx_assignments_class_active ON assignments(class_id, is_active);
```

#### 查询优化
```python
# src/repositories/optimized_queries.py
class OptimizedQueries:
    @staticmethod
    def get_class_assignments_with_stats(class_id):
        """获取班级作业及统计信息的优化查询"""
        query = """
        SELECT 
            a.*,
            COUNT(s.id) as submission_count,
            COUNT(CASE WHEN s.status = 'graded' THEN 1 END) as graded_count,
            AVG(CASE WHEN s.score IS NOT NULL THEN s.score END) as avg_score
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id
        WHERE a.class_id = ? AND a.is_active = 1
        GROUP BY a.id
        ORDER BY a.created_at DESC
        """
        return query
    
    @staticmethod
    def get_student_submissions_with_details(student_username):
        """获取学生提交详情的优化查询"""
        query = """
        SELECT 
            s.*,
            a.title as assignment_title,
            a.deadline,
            c.name as class_name
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN classes c ON a.class_id = c.id
        WHERE s.student_username = ?
        ORDER BY s.submitted_at DESC
        """
        return query
```

### 8.2 文件系统优化

#### 文件存储优化
```python
# src/services/optimized_file_manager.py
class OptimizedFileManager:
    def __init__(self):
        self.cache = {}
        self.compression_enabled = True
    
    def store_file_with_compression(self, file_path, content):
        """压缩存储文件"""
        if self.compression_enabled and self.should_compress(file_path):
            compressed_content = self.compress_content(content)
            return self.store_compressed_file(file_path, compressed_content)
        else:
            return self.store_regular_file(file_path, content)
    
    def implement_file_caching(self, file_path):
        """实现文件缓存"""
        if file_path in self.cache:
            return self.cache[file_path]
        
        content = self.read_file(file_path)
        self.cache[file_path] = content
        return content
    
    def cleanup_old_files(self):
        """清理旧文件"""
        cutoff_date = datetime.now() - timedelta(days=365)
        
        for root, dirs, files in os.walk(self.upload_path):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) < cutoff_date.timestamp():
                    self.archive_file(file_path)
```

### 8.3 应用性能优化

#### 缓存策略
```python
# src/infrastructure/caching.py
import redis
from functools import wraps

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.default_ttl = 3600  # 1小时
    
    def cache_result(self, key_prefix, ttl=None):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
                
                # 尝试从缓存获取
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                self.redis_client.setex(
                    cache_key, 
                    ttl or self.default_ttl, 
                    json.dumps(result)
                )
                return result
            return wrapper
        return decorator
    
    @cache_result("assignment_stats", ttl=1800)
    def get_assignment_statistics(self, assignment_id):
        """缓存作业统计数据"""
        # 实际的统计计算逻辑
        pass
```

## 安全管理

### 9.1 安全配置

#### 访问控制
```python
# src/security/access_control.py
class AccessControlManager:
    def __init__(self):
        self.failed_attempts = {}
        self.blocked_ips = set()
        self.max_attempts = 5
        self.block_duration = 3600  # 1小时
    
    def check_access(self, ip_address, username):
        """检查访问权限"""
        # 检查IP是否被阻止
        if ip_address in self.blocked_ips:
            return False, "IP地址已被阻止"
        
        # 检查失败尝试次数
        key = f"{ip_address}:{username}"
        if key in self.failed_attempts:
            attempts, last_attempt = self.failed_attempts[key]
            if attempts >= self.max_attempts:
                if time.time() - last_attempt < self.block_duration:
                    return False, "账号暂时锁定"
                else:
                    # 重置计数器
                    del self.failed_attempts[key]
        
        return True, "访问允许"
    
    def record_failed_attempt(self, ip_address, username):
        """记录失败尝试"""
        key = f"{ip_address}:{username}"
        if key in self.failed_attempts:
            attempts, _ = self.failed_attempts[key]
            self.failed_attempts[key] = (attempts + 1, time.time())
        else:
            self.failed_attempts[key] = (1, time.time())
        
        # 记录安全日志
        logging.warning(f"Failed login attempt: {username} from {ip_address}")
```

#### 数据加密
```python
# src/security/encryption.py
from cryptography.fernet import Fernet
import base64
import os

class EncryptionManager:
    def __init__(self):
        self.key = self.load_or_generate_key()
        self.cipher = Fernet(self.key)
    
    def load_or_generate_key(self):
        """加载或生成加密密钥"""
        key_file = '.encryption_key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_sensitive_data(self, data):
        """加密敏感数据"""
        if isinstance(data, str):
            data = data.encode()
        encrypted_data = self.cipher.encrypt(data)
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data):
        """解密敏感数据"""
        encrypted_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = self.cipher.decrypt(encrypted_data)
        return decrypted_data.decode()
```

### 9.2 安全审计

#### 审计日志
```python
# src/security/audit_logger.py
class AuditLogger:
    def __init__(self):
        self.audit_db = sqlite3.connect('audit.db')
        self.init_audit_tables()
    
    def init_audit_tables(self):
        """初始化审计表"""
        cursor = self.audit_db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                action TEXT,
                resource_type TEXT,
                resource_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT
            )
        """)
        self.audit_db.commit()
    
    def log_action(self, user_id, action, resource_type, resource_id, 
                   ip_address, user_agent, details=None):
        """记录用户操作"""
        cursor = self.audit_db.cursor()
        cursor.execute("""
            INSERT INTO audit_logs 
            (user_id, action, resource_type, resource_id, ip_address, user_agent, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, action, resource_type, resource_id, ip_address, user_agent, details))
        self.audit_db.commit()
    
    def get_user_activity(self, user_id, start_date, end_date):
        """获取用户活动记录"""
        cursor = self.audit_db.cursor()
        cursor.execute("""
            SELECT * FROM audit_logs 
            WHERE user_id = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """, (user_id, start_date, end_date))
        return cursor.fetchall()
```

### 9.3 安全检查清单

#### 定期安全检查
```bash
#!/bin/bash
# scripts/security_check.sh

echo "=== 系统安全检查 ==="

# 检查文件权限
echo "检查关键文件权限..."
ls -la .env config/ class_system.db

# 检查开放端口
echo "检查开放端口..."
netstat -tlnp | grep :8501

# 检查失败登录尝试
echo "检查失败登录..."
grep "Failed login" logs/system.log | tail -10

# 检查异常访问
echo "检查异常访问..."
grep "403\|404\|500" logs/access.log | tail -10

# 检查磁盘空间
echo "检查磁盘空间..."
df -h

# 检查系统更新
echo "检查系统更新..."
# 根据操作系统执行相应命令

echo "安全检查完成"
```

---

**版本信息**：v1.0  
**更新日期**：2025年1月  
**适用系统**：班级作业批改系统 v1.0+  
**联系方式**：admin@example.com