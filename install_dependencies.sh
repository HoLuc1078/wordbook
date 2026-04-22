#!/bin/bash
# 安装OpenResty和依赖的脚本

echo "安装OpenResty依赖..."

# 对于Windows用户，建议使用WSL或Chocolatey
# 对于Linux/Mac用户，使用系统包管理器

if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y build-essential libsqlite3-dev sqlite3
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y gcc make sqlite-devel sqlite
elif command -v brew &> /dev/null; then
    # macOS
    brew install sqlite
elif command -v choco &> /dev/null; then
    # Windows (Chocolatey)
    choco install sqlite
else
    echo "无法自动安装依赖，请手动安装OpenResty和SQLite3"
fi

echo "请从 https://openresty.org/ 下载并安装OpenResty"

# 创建必要的目录结构
mkdir -p lualib
mkdir -p logs

# 测试SQLite是否可用
if command -v sqlite3 &> /dev/null; then
    echo "SQLite3 已安装，测试数据库创建..."
    sqlite3 database/words.db "SELECT 1;" 2>/dev/null || echo "数据库目录创建成功"
else
    echo "警告：sqlite3 命令行工具未找到"
fi

echo "依赖安装脚本执行完成"