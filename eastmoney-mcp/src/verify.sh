#!/bin/bash
# 验证安装脚本

echo "🔍 验证东方财富 MCP Server 安装..."
echo ""

# 检查命令
echo "1. 检查 CLI 命令..."
if command -v eastmoney-cli &> /dev/null; then
    echo "   ✅ eastmoney-cli 已安装"
    eastmoney-cli --help | head -3
else
    echo "   ❌ eastmoney-cli 未找到"
fi

if command -v eastmoney-mcp &> /dev/null; then
    echo "   ✅ eastmoney-mcp 已安装"
else
    echo "   ❌ eastmoney-mcp 未找到"
fi

echo ""
echo "2. 检查 Python 包..."
python3 -c "from eastmoney_mcp.api import EastMoneyAPI; print('   ✅ Python 包导入成功')" 2>/dev/null || echo "   ❌ Python 包导入失败"

echo ""
echo "3. 检查环境变量..."
if [ -f .env ]; then
    echo "   ✅ .env 文件存在"
    if grep -q "EASTMONEY_APPKEY" .env; then
        echo "   ✅ EASTMONEY_APPKEY 已配置"
    else
        echo "   ⚠️  EASTMONEY_APPKEY 未配置"
    fi
    if grep -q "EASTMONEY_COOKIE" .env; then
        echo "   ✅ EASTMONEY_COOKIE 已配置"
    else
        echo "   ⚠️  EASTMONEY_COOKIE 未配置"
    fi
else
    echo "   ❌ .env 文件不存在"
fi

echo ""
echo "4. 检查 Hermes 配置..."
HCP_CONFIG="$HOME/.hermes/config.yaml"
if [ -f "$HCP_CONFIG" ]; then
    if grep -q "eastmoney:" "$HCP_CONFIG"; then
        echo "   ✅ Hermes MCP 配置已添加"
    else
        echo "   ❌ Hermes MCP 配置未添加"
    fi
else
    echo "   ❌ Hermes 配置文件不存在"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 快速测试命令："
echo "   eastmoney-cli groups      # 查看分组"
echo "   eastmoney-cli list        # 列出自选股"
echo "   eastmoney-cli quotes      # 查看行情"
echo ""
echo "⚠️  注意：首次使用前请确保 .env 中的 Cookie 有效"
echo ""
