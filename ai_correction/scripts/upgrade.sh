#!/bin/bash

# 班级作业批改系统升级脚本
# 支持从旧版本平滑升级到新版本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 默认配置
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"
UPGRADE_LOG="$PROJECT_DIR/logs/upgrade.log"
CURRENT_VERSION=""
TARGET_VERSION=""

# 显示帮助信息
show_help() {
    cat << EOF
班级作业批改系统升级脚本

用法: $0 [选项]

选项:
    -f, --from VERSION      当前版本号
    -t, --to VERSION        目标版本号
    -b, --backup            升级前创建备份
    -r, --rollback          回滚到备份版本
    --dry-run               模拟升级过程，不实际执行
    --force                 强制升级，跳过兼容性检查
    -h, --help              显示此帮助信息

示例:
    $0 -f 1.0.0 -t 1.1.0 -b     # 从1.0.0升级到1.1.0并备份
    $0 --rollback                # 回滚到最近的备份
    $0 --dry-run -t 1.2.0        # 模拟升级到1.2.0
EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--from)
                CURRENT_VERSION="$2"
                shift 2
                ;;
            -t|--to)
                TARGET_VERSION="$2"
                shift 2
                ;;
            -b|--backup)
                CREATE_BACKUP=true
                shift
                ;;
            -r|--rollback)
                ROLLBACK=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE_UPGRADE=true
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

# 检测当前版本
detect_current_version() {
    log_info "检测当前系统版本..."
    
    # 从数据库检测版本
    if [ -f "class_system.db" ]; then
        VERSION=$(sqlite3 class_system.db "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1" 2>/dev/null || echo "")
        if [ -n "$VERSION" ]; then
            CURRENT_VERSION="db_v$VERSION"
            log_info "从数据库检测到版本: $CURRENT_VERSION"
            return
        fi
    fi
    
    # 从版本文件检测
    if [ -f "VERSION" ]; then
        CURRENT_VERSION=$(cat VERSION)
        log_info "从VERSION文件检测到版本: $CURRENT_VERSION"
        return
    fi
    
    # 从Git标签检测
    if command -v git &> /dev/null && [ -d ".git" ]; then
        VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        if [ -n "$VERSION" ]; then
            CURRENT_VERSION="$VERSION"
            log_info "从Git标签检测到版本: $CURRENT_VERSION"
            return
        fi
    fi
    
    log_warn "无法自动检测当前版本，请使用 -f 参数指定"
    CURRENT_VERSION="unknown"
}

# 检查升级兼容性
check_compatibility() {
    log_info "检查升级兼容性..."
    
    if [ "$FORCE_UPGRADE" = true ]; then
        log_warn "强制升级模式，跳过兼容性检查"
        return
    fi
    
    # 检查Python版本兼容性
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    REQUIRED_PYTHON="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
        log_error "Python版本不兼容: 需要 $REQUIRED_PYTHON+, 当前 $PYTHON_VERSION"
        exit 1
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -BG "$PROJECT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 2 ]; then
        log_error "磁盘空间不足，需要至少2GB可用空间"
        exit 1
    fi
    
    # 检查数据库兼容性
    if [ -f "class_system.db" ]; then
        # 检查数据库是否可以正常访问
        sqlite3 class_system.db "SELECT COUNT(*) FROM sqlite_master" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            log_error "数据库文件损坏或无法访问"
            exit 1
        fi
    fi
    
    log_info "兼容性检查通过"
}

# 停止服务
stop_services() {
    log_info "停止系统服务..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将停止以下服务:"
        log_info "[DRY RUN] - classroom-grading"
        log_info "[DRY RUN] - classroom-monitoring"
        return
    fi
    
    # 停止Streamlit进程
    if pgrep -f "streamlit" > /dev/null; then
        log_info "停止Streamlit进程..."
        pkill -f "streamlit" || true
        sleep 3
    fi
    
    # 停止systemd服务
    if systemctl is-active --quiet classroom-grading 2>/dev/null; then
        log_info "停止classroom-grading服务..."
        sudo systemctl stop classroom-grading || true
    fi
    
    if systemctl is-active --quiet classroom-monitoring 2>/dev/null; then
        log_info "停止classroom-monitoring服务..."
        sudo systemctl stop classroom-monitoring || true
    fi
    
    log_info "服务已停止"
}

# 创建升级备份
create_upgrade_backup() {
    if [ "$CREATE_BACKUP" != true ]; then
        return
    fi
    
    log_info "创建升级备份..."
    
    BACKUP_NAME="upgrade_backup_$(date +%Y%m%d_%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将创建备份: $BACKUP_PATH"
        return
    fi
    
    mkdir -p "$BACKUP_PATH"
    
    # 备份关键文件和目录
    BACKUP_ITEMS=(
        "class_system.db"
        "tasks.db"
        "audit.db"
        ".env"
        "config/"
        "data/"
        "uploads/"
        "logs/"
        "streamlit_simple.py"
        "requirements.txt"
    )
    
    for item in "${BACKUP_ITEMS[@]}"; do
        if [ -e "$item" ]; then
            cp -r "$item" "$BACKUP_PATH/"
            log_info "已备份: $item"
        fi
    done
    
    # 记录当前版本信息
    cat > "$BACKUP_PATH/backup_info.txt" << EOF
升级备份信息
============
备份时间: $(date)
当前版本: $CURRENT_VERSION
目标版本: $TARGET_VERSION
Python版本: $(python3 --version)
系统信息: $(uname -a)
EOF
    
    log_info "升级备份完成: $BACKUP_PATH"
    echo "$BACKUP_PATH" > "$PROJECT_DIR/.last_backup"
}

# 更新代码
update_code() {
    log_info "更新应用代码..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将更新应用代码"
        return
    fi
    
    # 如果是Git仓库，拉取最新代码
    if [ -d ".git" ]; then
        log_info "从Git仓库更新代码..."
        git fetch origin
        if [ -n "$TARGET_VERSION" ] && [ "$TARGET_VERSION" != "latest" ]; then
            git checkout "$TARGET_VERSION"
        else
            git pull origin main
        fi
    else
        log_warn "非Git仓库，请手动更新代码文件"
    fi
    
    log_info "代码更新完成"
}

# 更新依赖
update_dependencies() {
    log_info "更新Python依赖..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将更新Python依赖包"
        return
    fi
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        log_error "虚拟环境不存在，请先运行部署脚本"
        exit 1
    fi
    
    # 更新pip
    pip install --upgrade pip
    
    # 安装新依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --upgrade
        log_info "基础依赖更新完成"
    fi
    
    if [ -f "requirements-prod.txt" ]; then
        pip install -r requirements-prod.txt --upgrade
        log_info "生产环境依赖更新完成"
    fi
    
    log_info "依赖更新完成"
}

# 升级数据库
upgrade_database() {
    log_info "升级数据库结构..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将运行数据库迁移"
        return
    fi
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 运行数据库迁移
    if [ -f "scripts/database_migration.py" ]; then
        python scripts/database_migration.py --db class_system.db
        log_info "数据库迁移完成"
    else
        log_warn "未找到数据库迁移脚本"
    fi
    
    log_info "数据库升级完成"
}

# 更新配置文件
update_configuration() {
    log_info "更新配置文件..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将更新配置文件"
        return
    fi
    
    # 备份现有配置
    if [ -f ".env" ]; then
        cp ".env" ".env.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 合并新配置选项
    if [ -f "config_template.env" ]; then
        # 这里可以添加配置合并逻辑
        log_info "配置模板已更新，请检查新的配置选项"
    fi
    
    # 更新监控配置
    if [ -f "config/monitoring.json" ] && [ ! -f "config/monitoring.json.backup" ]; then
        cp "config/monitoring.json" "config/monitoring.json.backup"
        log_info "监控配置已备份"
    fi
    
    log_info "配置文件更新完成"
}

# 运行升级后测试
run_upgrade_tests() {
    log_info "运行升级后测试..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将运行升级测试"
        return
    fi
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 运行健康检查
    if [ -f "scripts/health_check.py" ]; then
        python scripts/health_check.py --exit-code
        if [ $? -eq 0 ]; then
            log_info "健康检查通过"
        else
            log_error "健康检查失败"
            return 1
        fi
    fi
    
    # 运行基本功能测试
    if [ -d "test" ]; then
        python -m pytest test/ -v --tb=short -k "not slow"
        if [ $? -eq 0 ]; then
            log_info "基本功能测试通过"
        else
            log_warn "部分测试失败，请检查"
        fi
    fi
    
    log_info "升级后测试完成"
}

# 启动服务
start_services() {
    log_info "启动系统服务..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将启动系统服务"
        return
    fi
    
    # 重新加载systemd配置
    if command -v systemctl &> /dev/null; then
        sudo systemctl daemon-reload
    fi
    
    # 启动主服务
    if systemctl list-unit-files | grep -q classroom-grading; then
        sudo systemctl start classroom-grading
        log_info "classroom-grading服务已启动"
    else
        log_warn "classroom-grading服务未配置，请手动启动应用"
    fi
    
    # 启动监控服务
    if systemctl list-unit-files | grep -q classroom-monitoring; then
        sudo systemctl start classroom-monitoring
        log_info "classroom-monitoring服务已启动"
    fi
    
    log_info "服务启动完成"
}

# 更新版本信息
update_version_info() {
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] 将更新版本信息到: $TARGET_VERSION"
        return
    fi
    
    if [ -n "$TARGET_VERSION" ]; then
        echo "$TARGET_VERSION" > VERSION
        log_info "版本信息已更新: $TARGET_VERSION"
    fi
}

# 执行升级
perform_upgrade() {
    log_info "开始系统升级..."
    log_info "当前版本: $CURRENT_VERSION"
    log_info "目标版本: $TARGET_VERSION"
    
    # 记录升级日志
    mkdir -p "$(dirname "$UPGRADE_LOG")"
    echo "$(date): 开始升级 $CURRENT_VERSION -> $TARGET_VERSION" >> "$UPGRADE_LOG"
    
    # 执行升级步骤
    check_compatibility
    stop_services
    create_upgrade_backup
    update_code
    update_dependencies
    upgrade_database
    update_configuration
    update_version_info
    
    # 运行测试
    if run_upgrade_tests; then
        start_services
        log_info "升级成功完成！"
        echo "$(date): 升级成功完成 $CURRENT_VERSION -> $TARGET_VERSION" >> "$UPGRADE_LOG"
    else
        log_error "升级测试失败，建议回滚"
        echo "$(date): 升级测试失败 $CURRENT_VERSION -> $TARGET_VERSION" >> "$UPGRADE_LOG"
        return 1
    fi
}

# 回滚到备份
rollback_upgrade() {
    log_info "开始回滚升级..."
    
    # 查找最近的备份
    if [ -f "$PROJECT_DIR/.last_backup" ]; then
        BACKUP_PATH=$(cat "$PROJECT_DIR/.last_backup")
    else
        # 查找最新的升级备份
        BACKUP_PATH=$(find "$BACKUP_DIR" -name "upgrade_backup_*" -type d | sort | tail -1)
    fi
    
    if [ -z "$BACKUP_PATH" ] || [ ! -d "$BACKUP_PATH" ]; then
        log_error "未找到可用的备份"
        exit 1
    fi
    
    log_info "从备份回滚: $BACKUP_PATH"
    
    # 停止服务
    stop_services
    
    # 恢复文件
    if [ -f "$BACKUP_PATH/class_system.db" ]; then
        cp "$BACKUP_PATH/class_system.db" ./
        log_info "数据库已恢复"
    fi
    
    if [ -f "$BACKUP_PATH/.env" ]; then
        cp "$BACKUP_PATH/.env" ./
        log_info "配置文件已恢复"
    fi
    
    if [ -d "$BACKUP_PATH/uploads" ]; then
        rm -rf uploads/
        cp -r "$BACKUP_PATH/uploads" ./
        log_info "上传文件已恢复"
    fi
    
    # 启动服务
    start_services
    
    log_info "回滚完成"
    echo "$(date): 回滚完成，从备份: $BACKUP_PATH" >> "$UPGRADE_LOG"
}

# 显示升级摘要
show_upgrade_summary() {
    echo
    echo "=========================================="
    echo "  升级摘要"
    echo "=========================================="
    echo "当前版本: $CURRENT_VERSION"
    echo "目标版本: $TARGET_VERSION"
    echo "升级时间: $(date)"
    echo "升级日志: $UPGRADE_LOG"
    
    if [ -f "$PROJECT_DIR/.last_backup" ]; then
        echo "备份位置: $(cat $PROJECT_DIR/.last_backup)"
    fi
    
    echo
    echo "访问地址: http://localhost:8501"
    echo "=========================================="
}

# 主函数
main() {
    echo "班级作业批改系统升级工具"
    echo "========================================"
    
    parse_args "$@"
    
    cd "$PROJECT_DIR"
    
    if [ "$ROLLBACK" = true ]; then
        rollback_upgrade
        exit 0
    fi
    
    # 检测当前版本
    if [ -z "$CURRENT_VERSION" ]; then
        detect_current_version
    fi
    
    # 检查目标版本
    if [ -z "$TARGET_VERSION" ]; then
        log_error "请指定目标版本 (-t 选项)"
        exit 1
    fi
    
    # 执行升级
    if perform_upgrade; then
        show_upgrade_summary
    else
        log_error "升级失败，请检查日志: $UPGRADE_LOG"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi