#!/bin/bash
# 东方财富自选股 MCP Server 安装脚本

set -e

echo "🔧 安装东方财富自选股 MCP Server..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3.10+"
    exit 1
fi

# 进入目录
cd "$(dirname "$0")"

# 安装依赖
echo "📦 安装依赖..."
pip install -e . -q

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量模板..."
    cp .env.example .env
    echo "⚠️ 请编辑 .env 文件，填入你的 EASTMONEY_APPKEY 和 EASTMONEY_COOKIE"
fi

# 添加到 Hermes MCP 配置
echo "🔗 添加到 Hermes MCP 配置..."

HCP_CONFIG="$HOME/.hermes/config.yaml"
if [ -f "$HCP_CONFIG" ]; then
    # 备份原配置
    cp "$HCP_CONFIG" "$HCP_CONFIG.bak.$(date +%Y%m%d%H%M%S)"
    
    # 检查是否已存在 eastmoney 配置
    if ! grep -q "eastmoney:" "$HCP_CONFIG" 2>/dev/null; then
        cat >> "$HCP_CONFIG" << 'EOF'

# 东方财富自选股 MCP Server (由揽宝量化添加)
mcp_servers:
  eastmoney:
    command: eastmoney-mcp
    env:
      EASTMONEY_APPKEY: "${EASTMONEY_APPKEY}"
      EASTMONEY_COOKIE: "${EASTMONEY_COOKIE}"
EOF
        echo "✅ 已添加到 Hermes 配置"
    else
        echo "ℹ️ Hermes 配置中已存在 eastmoney 配置，跳过"
    fi
else
    echo "⚠️ 未找到 Hermes 配置文件，请手动添加 MCP Server 配置"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方法："
echo "  1. 编辑 .env 文件，填入东方财富凭证"
echo "  2. CLI: eastmoney-cli --help"
echo "  3. MCP: 在 Hermes 中使用自然语言调用"
echo ""
echo "示例命令："
echo "  eastmoney-cli groups        # 查看分组"
echo "  eastmoney-cli quotes        # 查看行情"
echo "  eastmoney-cli monitor       # 启动监控"
