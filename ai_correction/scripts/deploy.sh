#!/bin/bash

# 班级作业批改系统部署脚本
# 支持开发环境和生产环境部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 默认配置
ENVIRONMENT="development"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="3.8"
VENV_DIR="venv"
CONFIG_FILE=".env"
BACKUP_DIR="backups"
LOG_DIR="logs"

# 显示帮助信息
show_help() {
    cat << EOF
班级作业批改系统部署脚本

用法: $0 [选项]

选项:
    -e, --environment ENV    部署环境 (development|production) [默认: development]
    -p, --python-version VER Python版本 [默认: 3.8]
    -d, --project-dir DIR    项目目录 [默认: 当前目录的上级]
    -v, --venv-dir DIR       虚拟环境目录 [默认: venv]
    -c, --config FILE        配置文件 [默认: .env]
    -b, --backup             部署前备份现有系统
    --skip-deps              跳过依赖安装
    --skip-db                跳过数据库初始化
    --skip-test              跳过测试
    -h, --help               显示此帮助信息

示例:
    $0                                    # 开发环境部署
    $0 -e production -b                   # 生产环境部署并备份
    $0 --skip-deps --skip-test           # 快速部署（跳过依赖和测试）
EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--python-version)
                PYTHON_VERSION="$2"
                shift 2
                ;;
            -d|--project-dir)
                PROJECT_DIR="$2"
                shift 2
                ;;
            -v|--venv-dir)
                VENV_DIR="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -b|--backup)
                BACKUP_BEFORE_DEPLOY=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --skip-test)
                SKIP_TEST=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查Python版本
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "未找到Python，请先安装Python ${PYTHON_VERSION}+"
        exit 1
    fi
    
    CURRENT_PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_info "当前Python版本: $CURRENT_PYTHON_VERSION"
    
    # 检查pip
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        log_error "未找到pip，请先安装pip"
        exit 1
    fi
    
    # 检查git（可选）
    if command -v git &> /dev/null; then
        log_info "Git版本: $(git --version)"
    else
        log_warn "未找到Git，某些功能可能不可用"
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -BG "$PROJECT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 5 ]; then
        log_warn "磁盘空间不足5GB，建议清理磁盘空间"
    fi
    
    log_info "系统要求检查完成"
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    cd "$PROJECT_DIR"
    
    # 创建必要的目录
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "uploads/assignments"
    mkdir -p "uploads/submissions"
    mkdir -p "uploads/grading_results"
    mkdir -p "uploads/temp"
    mkdir -p "config"
    mkdir -p "data/templates"
    
    # 设置目录权限
    chmod 755 uploads/
    chmod 755 "$LOG_DIR"
    chmod 755 "$BACKUP_DIR"
    
    log_info "目录结构创建完成"
}

# 备份现有系统
backup_system() {
    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        log_info "备份现有系统..."
        
        BACKUP_NAME="system_backup_$(date +%Y%m%d_%H%M%S)"
        BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
        
        mkdir -p "$BACKUP_PATH"
        
        # 备份数据库
        if [ -f "class_system.db" ]; then
            cp "class_system.db" "$BACKUP_PATH/"
            log_info "数据库已备份"
        fi
        
        # 备份配置文件
        if [ -f "$CONFIG_FILE" ]; then
            cp "$CONFIG_FILE" "$BACKUP_PATH/"
            log_info "配置文件已备份"
        fi
        
        # 备份上传文件
        if [ -d "uploads" ]; then
            cp -r "uploads" "$BACKUP_PATH/"
            log_info "上传文件已备份"
        fi
        
        # 备份日志
        if [ -d "$LOG_DIR" ]; then
            cp -r "$LOG_DIR" "$BACKUP_PATH/"
            log_info "日志文件已备份"
        fi
        
        log_info "系统备份完成: $BACKUP_PATH"
    fi
}

# 设置Python虚拟环境
setup_virtualenv() {
    log_info "设置Python虚拟环境..."
    
    cd "$PROJECT_DIR"
    
    # 创建虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        log_info "创建虚拟环境: $VENV_DIR"
        $PYTHON_CMD -m venv "$VENV_DIR"
    else
        log_info "虚拟环境已存在: $VENV_DIR"
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    # 升级pip
    pip install --upgrade pip
    
    log_info "虚拟环境设置完成"
}

# 安装依赖
install_dependencies() {
    if [ "$SKIP_DEPS" = true ]; then
        log_info "跳过依赖安装"
        return
    fi
    
    log_info "安装Python依赖..."
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # 安装基础依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_info "基础依赖安装完成"
    else
        log_error "未找到requirements.txt文件"
        exit 1
    fi
    
    # 根据环境安装额外依赖
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ -f "requirements-prod.txt" ]; then
            pip install -r requirements-prod.txt
            log_info "生产环境依赖安装完成"
        fi
    else
        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt
            log_info "开发环境依赖安装完成"
        fi
    fi
    
    # 验证关键依赖
    python -c "import streamlit; print(f'Streamlit版本: {streamlit.__version__}')"
    python -c "import sqlite3; print('SQLite3可用')"
    
    log_info "依赖安装完成"
}

# 配置系统
configure_system() {
    log_info "配置系统..."
    
    cd "$PROJECT_DIR"
    
    # 创建配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        if [ -f "config_template.env" ]; then
            cp "config_template.env" "$CONFIG_FILE"
            log_info "从模板创建配置文件: $CONFIG_FILE"
        else
            log_warn "未找到配置模板，创建基本配置文件"
            cat > "$CONFIG_FILE" << EOF
# 数据库配置
DATABASE_URL=sqlite:///class_system.db

# 文件存储配置
UPLOAD_PATH=./uploads/
MAX_FILE_SIZE=52428800

# AI批改配置
AI_ENGINE_URL=http://localhost:8000
AI_TIMEOUT=300

# 安全配置
SECRET_KEY=$(openssl rand -hex 32)
JWT_EXPIRATION=3600

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/system.log

# 环境配置
ENVIRONMENT=$ENVIRONMENT
EOF
        fi
    else
        log_info "配置文件已存在: $CONFIG_FILE"
    fi
    
    # 根据环境调整配置
    if [ "$ENVIRONMENT" = "production" ]; then
        # 生产环境配置调整
        sed -i 's/LOG_LEVEL=DEBUG/LOG_LEVEL=INFO/' "$CONFIG_FILE"
        sed -i 's/DEBUG=true/DEBUG=false/' "$CONFIG_FILE"
        log_info "应用生产环境配置"
    fi
    
    log_info "系统配置完成"
}

# 初始化数据库
initialize_database() {
    if [ "$SKIP_DB" = true ]; then
        log_info "跳过数据库初始化"
        return
    fi
    
    log_info "初始化数据库..."
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # 运行数据库迁移
    if [ -f "scripts/database_migration.py" ]; then
        python scripts/database_migration.py --db class_system.db
        log_info "数据库迁移完成"
    else
        log_warn "未找到数据库迁移脚本，跳过迁移"
    fi
    
    # 创建默认管理员账号（仅开发环境）
    if [ "$ENVIRONMENT" = "development" ]; then
        if [ -f "scripts/create_admin.py" ]; then
            python scripts/create_admin.py --username admin --password admin123 --email admin@example.com
            log_info "默认管理员账号已创建 (admin/admin123)"
        fi
    fi
    
    log_info "数据库初始化完成"
}

# 运行测试
run_tests() {
    if [ "$SKIP_TEST" = true ]; then
        log_info "跳过测试"
        return
    fi
    
    log_info "运行测试..."
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # 运行单元测试
    if [ -d "test" ]; then
        python -m pytest test/ -v --tb=short
        if [ $? -eq 0 ]; then
            log_info "所有测试通过"
        else
            log_error "测试失败"
            exit 1
        fi
    else
        log_warn "未找到测试目录，跳过测试"
    fi
}

# 设置系统服务（生产环境）
setup_service() {
    if [ "$ENVIRONMENT" != "production" ]; then
        return
    fi
    
    log_info "设置系统服务..."
    
    # 创建systemd服务文件
    SERVICE_FILE="/etc/systemd/system/classroom-grading.service"
    
    if [ ! -f "$SERVICE_FILE" ]; then
        # 复制预配置的服务文件
        if [ -f "scripts/classroom-grading.service" ]; then
            sudo cp "scripts/classroom-grading.service" "$SERVICE_FILE"
            # 替换路径变量
            sudo sed -i "s|/opt/classroom-grading-system|$PROJECT_DIR|g" "$SERVICE_FILE"
            sudo sed -i "s|www-data|$USER|g" "$SERVICE_FILE"
        else
            # 创建基本服务文件
            sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Classroom Assignment Grading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/$VENV_DIR/bin
ExecStart=$PROJECT_DIR/$VENV_DIR/bin/streamlit run streamlit_simple.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        fi
        
        sudo systemctl daemon-reload
        sudo systemctl enable classroom-grading
        log_info "系统服务已创建并启用"
    else
        log_info "系统服务已存在"
    fi
    
    # 设置监控服务
    setup_monitoring_service
}

# 设置监控服务
setup_monitoring_service() {
    log_info "设置监控服务..."
    
    MONITORING_SERVICE_FILE="/etc/systemd/system/classroom-monitoring.service"
    
    if [ ! -f "$MONITORING_SERVICE_FILE" ]; then
        sudo tee "$MONITORING_SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Classroom System Monitoring
After=network.target classroom-grading.service
Requires=classroom-grading.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/$VENV_DIR/bin
ExecStart=$PROJECT_DIR/$VENV_DIR/bin/python scripts/system_monitor.py --config config/monitoring.json
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable classroom-monitoring
        log_info "监控服务已创建并启用"
    else
        log_info "监控服务已存在"
    fi
}

# 启动应用
start_application() {
    log_info "启动应用..."
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # 生产环境使用systemd服务
        sudo systemctl start classroom-grading
        sudo systemctl status classroom-grading --no-pager
        log_info "应用已通过systemd启动"
        log_info "访问地址: http://localhost:8501"
    else
        # 开发环境直接启动
        log_info "启动开发服务器..."
        log_info "访问地址: http://localhost:8501"
        log_info "按Ctrl+C停止服务器"
        
        # 后台启动（可选）
        if [ "$1" = "--daemon" ]; then
            nohup streamlit run streamlit_simple.py --server.port 8501 > "$LOG_DIR/streamlit.log" 2>&1 &
            echo $! > "$LOG_DIR/streamlit.pid"
            log_info "应用已在后台启动，PID: $(cat $LOG_DIR/streamlit.pid)"
        else
            streamlit run streamlit_simple.py --server.port 8501
        fi
    fi
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查文件存在
    REQUIRED_FILES=("streamlit_simple.py" "$CONFIG_FILE" "class_system.db")
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "缺少必要文件: $file"
            exit 1
        fi
    done
    
    # 检查目录存在
    REQUIRED_DIRS=("uploads" "$LOG_DIR" "$VENV_DIR")
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            log_error "缺少必要目录: $dir"
            exit 1
        fi
    done
    
    # 检查Python环境
    source "$VENV_DIR/bin/activate"
    python -c "import streamlit, sqlite3; print('Python环境验证通过')"
    
    # 检查数据库
    python -c "
import sqlite3
conn = sqlite3.connect('class_system.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
tables = cursor.fetchall()
print(f'数据库表数量: {len(tables)}')
conn.close()
"
    
    log_info "部署验证通过"
}

# 显示部署信息
show_deployment_info() {
    log_info "部署完成！"
    echo
    echo "=========================================="
    echo "  班级作业批改系统部署信息"
    echo "=========================================="
    echo "环境: $ENVIRONMENT"
    echo "项目目录: $PROJECT_DIR"
    echo "虚拟环境: $VENV_DIR"
    echo "配置文件: $CONFIG_FILE"
    echo "数据库: class_system.db"
    echo "日志目录: $LOG_DIR"
    echo "备份目录: $BACKUP_DIR"
    echo
    echo "访问地址: http://localhost:8501"
    echo
    if [ "$ENVIRONMENT" = "development" ]; then
        echo "默认管理员账号: admin / admin123"
        echo
        echo "启动命令:"
        echo "  cd $PROJECT_DIR"
        echo "  source $VENV_DIR/bin/activate"
        echo "  streamlit run streamlit_simple.py"
        echo
        echo "后台启动:"
        echo "  $0 --start-daemon"
    else
        echo "系统服务管理:"
        echo "  sudo systemctl start classroom-grading"
        echo "  sudo systemctl stop classroom-grading"
        echo "  sudo systemctl status classroom-grading"
    fi
    echo "=========================================="
}

# 主函数
main() {
    echo "班级作业批改系统部署脚本"
    echo "========================================"
    
    # 解析参数
    parse_args "$@"
    
    # 特殊命令处理
    if [ "$1" = "--start-daemon" ]; then
        cd "$PROJECT_DIR"
        source "$VENV_DIR/bin/activate"
        start_application --daemon
        exit 0
    fi
    
    # 执行部署步骤
    check_requirements
    create_directories
    backup_system
    setup_virtualenv
    install_dependencies
    configure_system
    initialize_database
    run_tests
    setup_service
    verify_deployment
    
    # 显示部署信息
    show_deployment_info
    
    # 询问是否立即启动
    if [ "$ENVIRONMENT" = "development" ]; then
        echo
        read -p "是否立即启动应用？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            start_application
        fi
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi