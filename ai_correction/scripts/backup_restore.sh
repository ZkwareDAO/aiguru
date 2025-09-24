#!/bin/bash

# 班级作业批改系统备份和恢复脚本

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
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="system_backup_$TIMESTAMP"

# 显示帮助信息
show_help() {
    cat << EOF
班级作业批改系统备份和恢复脚本

用法: $0 [命令] [选项]

命令:
    backup              创建系统备份
    restore             恢复系统备份
    list                列出所有备份
    cleanup             清理旧备份
    verify              验证备份完整性

选项:
    -d, --dir DIR       备份目录 [默认: ./backups]
    -n, --name NAME     备份名称 [默认: system_backup_TIMESTAMP]
    -f, --file FILE     恢复时指定备份文件
    -k, --keep DAYS     清理时保留天数 [默认: 30]
    -c, --compress      压缩备份文件
    -v, --verbose       详细输出
    -h, --help          显示此帮助信息

示例:
    $0 backup                           # 创建备份
    $0 backup -c                        # 创建压缩备份
    $0 restore -f backup_20250101.tar.gz  # 恢复指定备份
    $0 list                             # 列出所有备份
    $0 cleanup -k 7                     # 清理7天前的备份
EOF
}

# 解析命令行参数
parse_args() {
    COMMAND=""
    COMPRESS=false
    VERBOSE=false
    KEEP_DAYS=30
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            backup|restore|list|cleanup|verify)
                COMMAND="$1"
                shift
                ;;
            -d|--dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -n|--name)
                BACKUP_NAME="$2"
                shift 2
                ;;
            -f|--file)
                RESTORE_FILE="$2"
                shift 2
                ;;
            -k|--keep)
                KEEP_DAYS="$2"
                shift 2
                ;;
            -c|--compress)
                COMPRESS=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
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
    
    if [ -z "$COMMAND" ]; then
        log_error "请指定命令"
        show_help
        exit 1
    fi
}

# 创建备份目录
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    if [ $VERBOSE = true ]; then
        log_info "备份目录: $BACKUP_DIR"
    fi
}

# 检查系统状态
check_system_status() {
    cd "$PROJECT_DIR"
    
    # 检查关键文件
    CRITICAL_FILES=("class_system.db" "streamlit_simple.py" ".env")
    for file in "${CRITICAL_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            log_warn "关键文件不存在: $file"
        fi
    done
    
    # 检查应用是否运行
    if pgrep -f "streamlit" > /dev/null; then
        log_warn "检测到Streamlit正在运行，建议停止后再备份"
        read -p "是否继续备份？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "备份已取消"
            exit 0
        fi
    fi
}

# 创建备份
create_backup() {
    log_info "开始创建系统备份..."
    
    create_backup_dir
    check_system_status
    
    cd "$PROJECT_DIR"
    
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p "$BACKUP_PATH"
    
    # 备份数据库
    if [ -f "class_system.db" ]; then
        cp "class_system.db" "$BACKUP_PATH/"
        log_info "✓ 数据库已备份"
    fi
    
    # 备份任务数据库
    if [ -f "tasks.db" ]; then
        cp "tasks.db" "$BACKUP_PATH/"
        log_info "✓ 任务数据库已备份"
    fi
    
    # 备份审计数据库
    if [ -f "audit.db" ]; then
        cp "audit.db" "$BACKUP_PATH/"
        log_info "✓ 审计数据库已备份"
    fi
    
    # 备份配置文件
    CONFIG_FILES=(".env" "config_template.env")
    for file in "${CONFIG_FILES[@]}"; do
        if [ -f "$file" ]; then
            cp "$file" "$BACKUP_PATH/"
            if [ $VERBOSE = true ]; then
                log_info "✓ 配置文件已备份: $file"
            fi
        fi
    done
    
    # 备份配置目录
    if [ -d "config" ]; then
        cp -r "config" "$BACKUP_PATH/"
        log_info "✓ 配置目录已备份"
    fi
    
    # 备份数据目录
    if [ -d "data" ]; then
        cp -r "data" "$BACKUP_PATH/"
        log_info "✓ 数据目录已备份"
    fi
    
    # 备份上传文件
    if [ -d "uploads" ]; then
        # 计算上传文件大小
        UPLOAD_SIZE=$(du -sh uploads 2>/dev/null | cut -f1)
        log_info "备份上传文件 (大小: $UPLOAD_SIZE)..."
        cp -r "uploads" "$BACKUP_PATH/"
        log_info "✓ 上传文件已备份"
    fi
    
    # 备份日志（最近7天）
    if [ -d "logs" ]; then
        mkdir -p "$BACKUP_PATH/logs"
        find logs -name "*.log" -mtime -7 -exec cp {} "$BACKUP_PATH/logs/" \;
        log_info "✓ 日志文件已备份（最近7天）"
    fi
    
    # 备份重要脚本
    SCRIPTS=("streamlit_simple.py" "start.bat" "start_simple.py")
    for script in "${SCRIPTS[@]}"; do
        if [ -f "$script" ]; then
            cp "$script" "$BACKUP_PATH/"
            if [ $VERBOSE = true ]; then
                log_info "✓ 脚本已备份: $script"
            fi
        fi
    done
    
    # 创建备份信息文件
    cat > "$BACKUP_PATH/backup_info.txt" << EOF
备份信息
========================================
备份时间: $(date)
备份名称: $BACKUP_NAME
系统版本: $(python --version 2>&1 || echo "未知")
备份大小: $(du -sh "$BACKUP_PATH" | cut -f1)
备份内容:
$(ls -la "$BACKUP_PATH")

环境信息:
========================================
操作系统: $(uname -a)
磁盘使用: $(df -h "$PROJECT_DIR" | tail -1)
内存使用: $(free -h | head -2 | tail -1)

数据库信息:
========================================
EOF
    
    # 添加数据库统计信息
    if [ -f "class_system.db" ]; then
        sqlite3 "class_system.db" "
        .mode column
        .headers on
        SELECT 'assignments' as table_name, COUNT(*) as count FROM assignments
        UNION ALL
        SELECT 'submissions', COUNT(*) FROM submissions
        UNION ALL
        SELECT 'classes', COUNT(*) FROM classes WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='classes')
        UNION ALL
        SELECT 'users', COUNT(*) FROM users WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='users');
        " >> "$BACKUP_PATH/backup_info.txt" 2>/dev/null || echo "无法获取数据库统计信息" >> "$BACKUP_PATH/backup_info.txt"
    fi
    
    # 压缩备份（如果指定）
    if [ $COMPRESS = true ]; then
        log_info "压缩备份文件..."
        cd "$BACKUP_DIR"
        tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
        rm -rf "$BACKUP_NAME"
        BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
        log_info "✓ 备份已压缩: ${BACKUP_NAME}.tar.gz"
    fi
    
    # 计算备份大小
    BACKUP_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
    
    log_info "备份创建完成！"
    log_info "备份位置: $BACKUP_PATH"
    log_info "备份大小: $BACKUP_SIZE"
}

# 列出备份
list_backups() {
    log_info "备份列表:"
    echo "========================================"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "备份目录不存在: $BACKUP_DIR"
        return
    fi
    
    cd "$BACKUP_DIR"
    
    # 列出目录备份
    for backup in system_backup_*; do
        if [ -d "$backup" ]; then
            SIZE=$(du -sh "$backup" 2>/dev/null | cut -f1)
            MTIME=$(stat -c %y "$backup" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
            printf "%-30s %8s %s\n" "$backup" "$SIZE" "$MTIME"
        fi
    done
    
    # 列出压缩备份
    for backup in system_backup_*.tar.gz; do
        if [ -f "$backup" ]; then
            SIZE=$(du -sh "$backup" 2>/dev/null | cut -f1)
            MTIME=$(stat -c %y "$backup" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
            printf "%-30s %8s %s (压缩)\n" "$backup" "$SIZE" "$MTIME"
        fi
    done
    
    echo "========================================"
    
    # 统计信息
    BACKUP_COUNT=$(ls -1 system_backup_* 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh . 2>/dev/null | cut -f1)
    log_info "总计: $BACKUP_COUNT 个备份，占用空间: $TOTAL_SIZE"
}

# 恢复备份
restore_backup() {
    if [ -z "$RESTORE_FILE" ]; then
        log_error "请指定要恢复的备份文件 (-f 选项)"
        exit 1
    fi
    
    log_info "开始恢复系统备份..."
    
    # 检查备份文件
    RESTORE_PATH="$BACKUP_DIR/$RESTORE_FILE"
    if [ ! -f "$RESTORE_PATH" ] && [ ! -d "$RESTORE_PATH" ]; then
        log_error "备份文件不存在: $RESTORE_PATH"
        exit 1
    fi
    
    # 确认恢复操作
    log_warn "恢复操作将覆盖现有数据！"
    read -p "确定要继续吗？(yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "恢复操作已取消"
        exit 0
    fi
    
    cd "$PROJECT_DIR"
    
    # 停止应用服务
    if pgrep -f "streamlit" > /dev/null; then
        log_info "停止Streamlit服务..."
        pkill -f "streamlit" || true
        sleep 2
    fi
    
    # 备份当前系统
    CURRENT_BACKUP="current_system_$(date +%Y%m%d_%H%M%S)"
    log_info "备份当前系统到: $CURRENT_BACKUP"
    mkdir -p "$BACKUP_DIR/$CURRENT_BACKUP"
    
    if [ -f "class_system.db" ]; then
        cp "class_system.db" "$BACKUP_DIR/$CURRENT_BACKUP/"
    fi
    if [ -f ".env" ]; then
        cp ".env" "$BACKUP_DIR/$CURRENT_BACKUP/"
    fi
    
    # 解压备份文件（如果是压缩文件）
    TEMP_RESTORE_DIR=""
    if [[ "$RESTORE_FILE" == *.tar.gz ]]; then
        log_info "解压备份文件..."
        TEMP_RESTORE_DIR="/tmp/restore_$$"
        mkdir -p "$TEMP_RESTORE_DIR"
        tar -xzf "$RESTORE_PATH" -C "$TEMP_RESTORE_DIR"
        RESTORE_SOURCE="$TEMP_RESTORE_DIR/$(basename "$RESTORE_FILE" .tar.gz)"
    else
        RESTORE_SOURCE="$RESTORE_PATH"
    fi
    
    # 恢复数据库
    if [ -f "$RESTORE_SOURCE/class_system.db" ]; then
        cp "$RESTORE_SOURCE/class_system.db" "./"
        log_info "✓ 数据库已恢复"
    fi
    
    if [ -f "$RESTORE_SOURCE/tasks.db" ]; then
        cp "$RESTORE_SOURCE/tasks.db" "./"
        log_info "✓ 任务数据库已恢复"
    fi
    
    if [ -f "$RESTORE_SOURCE/audit.db" ]; then
        cp "$RESTORE_SOURCE/audit.db" "./"
        log_info "✓ 审计数据库已恢复"
    fi
    
    # 恢复配置文件
    if [ -f "$RESTORE_SOURCE/.env" ]; then
        cp "$RESTORE_SOURCE/.env" "./"
        log_info "✓ 配置文件已恢复"
    fi
    
    # 恢复配置目录
    if [ -d "$RESTORE_SOURCE/config" ]; then
        rm -rf "config"
        cp -r "$RESTORE_SOURCE/config" "./"
        log_info "✓ 配置目录已恢复"
    fi
    
    # 恢复数据目录
    if [ -d "$RESTORE_SOURCE/data" ]; then
        rm -rf "data"
        cp -r "$RESTORE_SOURCE/data" "./"
        log_info "✓ 数据目录已恢复"
    fi
    
    # 恢复上传文件
    if [ -d "$RESTORE_SOURCE/uploads" ]; then
        log_info "恢复上传文件..."
        rm -rf "uploads"
        cp -r "$RESTORE_SOURCE/uploads" "./"
        log_info "✓ 上传文件已恢复"
    fi
    
    # 清理临时文件
    if [ -n "$TEMP_RESTORE_DIR" ]; then
        rm -rf "$TEMP_RESTORE_DIR"
    fi
    
    log_info "系统恢复完成！"
    log_info "当前系统已备份到: $BACKUP_DIR/$CURRENT_BACKUP"
    
    # 询问是否重启服务
    read -p "是否重启应用服务？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "重启应用服务..."
        if [ -f "start.bat" ]; then
            ./start.bat &
        elif [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            streamlit run streamlit_simple.py --server.port 8501 &
        else
            streamlit run streamlit_simple.py --server.port 8501 &
        fi
        log_info "应用服务已启动"
    fi
}

# 清理旧备份
cleanup_backups() {
    log_info "清理 $KEEP_DAYS 天前的备份..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "备份目录不存在: $BACKUP_DIR"
        return
    fi
    
    cd "$BACKUP_DIR"
    
    DELETED_COUNT=0
    
    # 清理目录备份
    for backup in system_backup_*; do
        if [ -d "$backup" ]; then
            if [ $(find "$backup" -maxdepth 0 -mtime +$KEEP_DAYS | wc -l) -gt 0 ]; then
                rm -rf "$backup"
                log_info "已删除: $backup"
                ((DELETED_COUNT++))
            fi
        fi
    done
    
    # 清理压缩备份
    for backup in system_backup_*.tar.gz; do
        if [ -f "$backup" ]; then
            if [ $(find "$backup" -maxdepth 0 -mtime +$KEEP_DAYS | wc -l) -gt 0 ]; then
                rm -f "$backup"
                log_info "已删除: $backup"
                ((DELETED_COUNT++))
            fi
        fi
    done
    
    log_info "清理完成，删除了 $DELETED_COUNT 个旧备份"
}

# 验证备份完整性
verify_backup() {
    if [ -z "$RESTORE_FILE" ]; then
        log_error "请指定要验证的备份文件 (-f 选项)"
        exit 1
    fi
    
    log_info "验证备份完整性..."
    
    RESTORE_PATH="$BACKUP_DIR/$RESTORE_FILE"
    if [ ! -f "$RESTORE_PATH" ] && [ ! -d "$RESTORE_PATH" ]; then
        log_error "备份文件不存在: $RESTORE_PATH"
        exit 1
    fi
    
    # 验证压缩文件
    if [[ "$RESTORE_FILE" == *.tar.gz ]]; then
        log_info "验证压缩文件完整性..."
        if tar -tzf "$RESTORE_PATH" > /dev/null 2>&1; then
            log_info "✓ 压缩文件完整"
        else
            log_error "✗ 压缩文件损坏"
            exit 1
        fi
        
        # 解压到临时目录验证内容
        TEMP_DIR="/tmp/verify_$$"
        mkdir -p "$TEMP_DIR"
        tar -xzf "$RESTORE_PATH" -C "$TEMP_DIR"
        VERIFY_SOURCE="$TEMP_DIR/$(basename "$RESTORE_FILE" .tar.gz)"
    else
        VERIFY_SOURCE="$RESTORE_PATH"
    fi
    
    # 验证关键文件
    CRITICAL_FILES=("backup_info.txt")
    for file in "${CRITICAL_FILES[@]}"; do
        if [ -f "$VERIFY_SOURCE/$file" ]; then
            log_info "✓ 找到文件: $file"
        else
            log_warn "✗ 缺少文件: $file"
        fi
    done
    
    # 验证数据库文件
    if [ -f "$VERIFY_SOURCE/class_system.db" ]; then
        log_info "验证数据库文件..."
        if sqlite3 "$VERIFY_SOURCE/class_system.db" "SELECT COUNT(*) FROM sqlite_master;" > /dev/null 2>&1; then
            log_info "✓ 数据库文件完整"
        else
            log_error "✗ 数据库文件损坏"
        fi
    fi
    
    # 显示备份信息
    if [ -f "$VERIFY_SOURCE/backup_info.txt" ]; then
        log_info "备份信息:"
        echo "========================================"
        cat "$VERIFY_SOURCE/backup_info.txt"
        echo "========================================"
    fi
    
    # 清理临时文件
    if [ -n "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    
    log_info "备份验证完成"
}

# 主函数
main() {
    echo "班级作业批改系统备份和恢复工具"
    echo "========================================"
    
    parse_args "$@"
    
    case $COMMAND in
        backup)
            create_backup
            ;;
        restore)
            restore_backup
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_backups
            ;;
        verify)
            verify_backup
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi