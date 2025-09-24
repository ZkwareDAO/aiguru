# 班级作业批改系统部署指南

## 概述

本指南详细介绍了班级作业批改系统的部署、配置、监控和维护流程。系统支持开发环境和生产环境的部署，提供了完整的自动化脚本和监控工具。

## 目录

1. [系统要求](#系统要求)
2. [快速部署](#快速部署)
3. [详细部署步骤](#详细部署步骤)
4. [Docker部署](#docker部署)
5. [生产环境配置](#生产环境配置)
6. [监控和维护](#监控和维护)
7. [备份和恢复](#备份和恢复)
8. [升级指南](#升级指南)
9. [故障排除](#故障排除)

## 系统要求

### 最低要求
- **操作系统**: Windows 10+, Ubuntu 18.04+, CentOS 7+, macOS 10.15+
- **Python**: 3.8 或更高版本
- **内存**: 4GB RAM
- **磁盘空间**: 10GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **操作系统**: Ubuntu 20.04 LTS 或 Windows Server 2019
- **Python**: 3.9+
- **内存**: 8GB RAM 或更多
- **磁盘空间**: 50GB 可用空间（SSD推荐）
- **CPU**: 4核心或更多

### 软件依赖
- Python 3.8+
- pip (Python包管理器)
- Git (可选，用于代码更新)
- SQLite 3.x
- 现代Web浏览器

## 快速部署

### 1. 获取代码
```bash
# 从Git仓库克隆
git clone <repository-url>
cd classroom-grading-system

# 或解压发布包
unzip classroom-grading-system-v1.0.zip
cd classroom-grading-system
```

### 2. 运行部署脚本
```bash
# Linux/macOS
bash scripts/deploy.sh

# Windows (使用Git Bash或WSL)
bash scripts/deploy.sh

# 或使用PowerShell
python scripts/deploy.py
```

### 3. 访问系统
部署完成后，在浏览器中访问: http://localhost:8501

默认管理员账号:
- 用户名: admin
- 密码: admin123

## 详细部署步骤

### 1. 环境准备

#### Linux/macOS
```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# 或
sudo yum update -y  # CentOS/RHEL

# 安装Python和依赖
sudo apt install python3 python3-pip python3-venv sqlite3 git -y

# 验证安装
python3 --version
pip3 --version
```

#### Windows
1. 从 [python.org](https://python.org) 下载并安装Python 3.8+
2. 确保在安装时勾选"Add Python to PATH"
3. 安装Git (可选): https://git-scm.com/download/win
4. 打开命令提示符或PowerShell验证安装

### 2. 创建项目目录
```bash
# 创建项目目录
mkdir -p /opt/classroom-grading-system
cd /opt/classroom-grading-system

# 或在Windows中
mkdir C:\classroom-grading-system
cd C:\classroom-grading-system
```

### 3. 设置虚拟环境
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. 安装依赖
```bash
# 升级pip
pip install --upgrade pip

# 安装基础依赖
pip install -r requirements.txt

# 生产环境额外依赖
pip install -r requirements-prod.txt
```

### 5. 配置系统
```bash
# 复制配置模板
cp config_template.env .env

# 编辑配置文件
nano .env  # Linux/macOS
# 或使用记事本编辑 .env 文件 (Windows)
```

### 6. 初始化数据库
```bash
# 运行数据库迁移
python scripts/database_migration.py

# 创建管理员账号
python scripts/create_admin.py --username admin --password admin123
```

### 7. 启动应用
```bash
# 开发环境
streamlit run streamlit_simple.py --server.port 8501

# 生产环境 (后台运行)
nohup streamlit run streamlit_simple.py --server.port 8501 > logs/app.log 2>&1 &
```

## Docker部署

### 1. 使用Docker Compose (推荐)
```bash
# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f classroom-grading
```

### 2. 使用Docker
```bash
# 构建镜像
docker build -t classroom-grading:latest .

# 运行容器
docker run -d \
  --name classroom-grading \
  -p 8501:8501 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/class_system.db:/app/class_system.db \
  classroom-grading:latest
```

### 3. Docker环境配置
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  classroom-grading:
    environment:
      - DATABASE_URL=sqlite:///class_system.db
      - LOG_LEVEL=INFO
      - MAX_FILE_SIZE=52428800
    volumes:
      - ./custom-config:/app/config
```

## 生产环境配置

### 1. 系统服务配置
```bash
# 复制服务文件
sudo cp scripts/classroom-grading.service /etc/systemd/system/

# 编辑服务文件中的路径
sudo nano /etc/systemd/system/classroom-grading.service

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable classroom-grading
sudo systemctl start classroom-grading

# 检查服务状态
sudo systemctl status classroom-grading
```

### 2. 反向代理配置 (Nginx)
```nginx
# /etc/nginx/sites-available/classroom-grading
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL证书配置
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 4. 防火墙配置
```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 监控和维护

### 1. 系统监控
```bash
# 启动监控服务
python scripts/system_monitor.py

# 后台运行监控
nohup python scripts/system_monitor.py > logs/monitoring.log 2>&1 &

# 查看监控报告
python scripts/system_monitor.py --report
```

### 2. 健康检查
```bash
# 运行健康检查
python scripts/health_check.py

# 输出JSON格式结果
python scripts/health_check.py --json

# 保存结果到文件
python scripts/health_check.py --output health_report.txt
```

### 3. 日志管理
```bash
# 查看应用日志
tail -f logs/system.log

# 查看Streamlit日志
tail -f logs/streamlit.log

# 日志轮转配置
sudo nano /etc/logrotate.d/classroom-grading
```

### 4. 性能监控
```bash
# 查看系统资源使用
htop
# 或
top

# 查看磁盘使用
df -h

# 查看数据库大小
ls -lh *.db
```

## 备份和恢复

### 1. 创建备份
```bash
# 创建完整备份
bash scripts/backup_restore.sh backup

# 创建压缩备份
bash scripts/backup_restore.sh backup -c

# 自动备份 (添加到crontab)
0 2 * * * /path/to/scripts/backup_restore.sh backup -c
```

### 2. 恢复备份
```bash
# 列出所有备份
bash scripts/backup_restore.sh list

# 恢复指定备份
bash scripts/backup_restore.sh restore -f backup_20250101_120000.tar.gz

# 验证备份完整性
bash scripts/backup_restore.sh verify -f backup_20250101_120000.tar.gz
```

### 3. 清理旧备份
```bash
# 清理30天前的备份
bash scripts/backup_restore.sh cleanup -k 30

# 清理7天前的备份
bash scripts/backup_restore.sh cleanup -k 7
```

## 升级指南

### 1. 准备升级
```bash
# 检查当前版本
cat VERSION

# 创建升级前备份
bash scripts/upgrade.sh -b

# 模拟升级过程
bash scripts/upgrade.sh --dry-run -t 1.1.0
```

### 2. 执行升级
```bash
# 从1.0.0升级到1.1.0
bash scripts/upgrade.sh -f 1.0.0 -t 1.1.0 -b

# 强制升级 (跳过兼容性检查)
bash scripts/upgrade.sh -t 1.1.0 --force
```

### 3. 升级后验证
```bash
# 运行健康检查
python scripts/health_check.py

# 检查服务状态
sudo systemctl status classroom-grading

# 访问Web界面验证功能
curl -I http://localhost:8501
```

### 4. 回滚升级
```bash
# 回滚到最近的备份
bash scripts/upgrade.sh --rollback
```

## 故障排除

### 1. 常见问题

#### 应用无法启动
```bash
# 检查Python环境
python3 --version
which python3

# 检查依赖安装
pip list | grep streamlit

# 查看错误日志
tail -f logs/system.log
```

#### 数据库连接失败
```bash
# 检查数据库文件
ls -la *.db

# 测试数据库连接
sqlite3 class_system.db "SELECT COUNT(*) FROM sqlite_master;"

# 运行数据库修复
python scripts/database_migration.py --verify
```

#### 端口被占用
```bash
# 查看端口使用情况
netstat -tlnp | grep 8501
# 或
lsof -i :8501

# 杀死占用进程
sudo kill -9 <PID>
```

#### 磁盘空间不足
```bash
# 检查磁盘使用
df -h

# 清理日志文件
find logs/ -name "*.log" -mtime +30 -delete

# 清理临时文件
rm -rf uploads/temp/*

# 清理旧备份
bash scripts/backup_restore.sh cleanup -k 7
```

### 2. 性能问题

#### 响应速度慢
```bash
# 检查系统资源
htop

# 检查数据库性能
python scripts/health_check.py

# 优化数据库
sqlite3 class_system.db "VACUUM;"
sqlite3 class_system.db "ANALYZE;"
```

#### 内存使用过高
```bash
# 重启应用服务
sudo systemctl restart classroom-grading

# 检查内存泄漏
python scripts/system_monitor.py --once
```

### 3. 网络问题

#### 无法访问Web界面
```bash
# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all

# 检查Nginx配置
sudo nginx -t
sudo systemctl status nginx

# 检查SSL证书
sudo certbot certificates
```

### 4. 获取帮助

#### 日志收集
```bash
# 收集系统信息
python scripts/health_check.py --json > system_info.json

# 收集日志文件
tar -czf logs_$(date +%Y%m%d).tar.gz logs/

# 生成诊断报告
python scripts/system_monitor.py --report > diagnostic_report.txt
```

#### 联系支持
如果遇到无法解决的问题，请提供以下信息：
- 系统信息 (system_info.json)
- 错误日志 (logs/)
- 诊断报告 (diagnostic_report.txt)
- 问题描述和重现步骤

## 安全建议

### 1. 系统安全
- 定期更新系统和依赖包
- 使用强密码和双因素认证
- 配置防火墙限制访问
- 启用SSL/TLS加密

### 2. 数据安全
- 定期备份重要数据
- 加密敏感信息存储
- 限制文件上传类型和大小
- 实施访问控制和审计

### 3. 网络安全
- 使用反向代理隐藏应用端口
- 配置速率限制防止滥用
- 监控异常访问和攻击
- 定期安全扫描和评估

## 附录

### A. 配置文件说明
- `.env`: 主配置文件
- `config/monitoring.json`: 监控配置
- `config/ai_optimization.yaml`: AI批改配置
- `requirements.txt`: Python依赖列表

### B. 脚本说明
- `deploy.sh`: 自动化部署脚本
- `backup_restore.sh`: 备份恢复脚本
- `upgrade.sh`: 系统升级脚本
- `system_monitor.py`: 系统监控脚本
- `health_check.py`: 健康检查脚本

### C. 目录结构
```
classroom-grading-system/
├── src/                    # 源代码
├── scripts/               # 部署和运维脚本
├── config/                # 配置文件
├── logs/                  # 日志文件
├── uploads/               # 上传文件
├── backups/               # 备份文件
├── data/                  # 数据文件
├── test/                  # 测试文件
├── docs/                  # 文档
├── requirements.txt       # Python依赖
├── .env                   # 环境配置
├── Dockerfile            # Docker配置
└── docker-compose.yml    # Docker Compose配置
```

---

**版本**: v1.0  
**更新日期**: 2025年1月  
**维护者**: 系统管理团队