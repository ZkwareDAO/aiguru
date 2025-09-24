@echo off
REM 在Windows系统上设置脚本权限

echo 设置脚本执行权限...

REM 对于Windows系统，主要是确保Python脚本可以执行
echo Python脚本权限设置完成

REM 显示脚本列表
echo.
echo 可用的部署和运维脚本:
echo ================================
echo deploy.sh              - 系统部署脚本
echo backup_restore.sh      - 备份和恢复脚本  
echo upgrade.sh             - 系统升级脚本
echo database_migration.py  - 数据库迁移脚本
echo system_monitor.py      - 系统监控脚本
echo health_check.py        - 健康检查脚本
echo create_admin.py        - 创建管理员脚本
echo.
echo 使用方法:
echo   bash scripts/deploy.sh --help
echo   python scripts/health_check.py
echo   python scripts/system_monitor.py --once
echo.
pause