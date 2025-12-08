#!/bin/bash
set -euo pipefail

red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }

echo -e "\n==================== Claude MCP 服务器一致性检查 ====================\n"

blue "【1/6】基础环境信息"
echo "当前系统: $(lsb_release -d 2>/dev/null | awk -F: '{print $2}' | sed 's/^ //' || echo "Ubuntu")"
echo "当前用户: $(whoami) (UID: $(id -u), GID: $(id -g))"
echo "当前目录: $(pwd)"
echo "当前时间: $(date +'%Y-%m-%d %H:%M:%S')"
echo

blue "【2/6】Claude命令核心检查"
CLAUDE_CMD="claude"
if ! command -v $CLAUDE_CMD &>/dev/null; then
    red "❌ 未找到'claude'命令，请确认Claude Code已正确安装！"
    echo "   修复建议：重新安装Claude Code，或确认命令名称（如claude-code）"
else
    CLAUDE_PATH=$(which $CLAUDE_CMD)
    echo "Claude可执行路径: $CLAUDE_PATH"
    
    if $CLAUDE_CMD --version &>/dev/null; then
        CLAUDE_VERSION=$($CLAUDE_CMD --version 2>/dev/null | head -1)
        green "✅ Claude版本: $CLAUDE_VERSION"
        
        VERSION_TMP=$(cd /tmp && $CLAUDE_CMD --version 2>/dev/null | head -1)
        VERSION_HOME=$(cd ~ && $CLAUDE_CMD --version 2>/dev/null | head -1)
        
        if [ "$CLAUDE_VERSION" = "$VERSION_TMP" ] && [ "$CLAUDE_VERSION" = "$VERSION_HOME" ]; then
            green "✅ 多目录下Claude版本一致"
        else
            red "❌ 不同目录下Claude版本不一致！"
            echo "  当前目录: $CLAUDE_VERSION"
            echo "  /tmp目录: $VERSION_TMP"
            echo "  主目录: $VERSION_HOME"
        fi
    else
        yellow "⚠️  无法获取Claude版本（命令--version参数无效）"
    fi
fi
echo

blue "【3/6】MCP核心环境变量检查"
ENV_KEYS=("MCP_CONFIG" "PATH" "PYTHONPATH" "NODE_PATH" "HOME" "USER")
ENV_DIFF=0

for key in "${ENV_KEYS[@]}"; do
    CURRENT_VAL=${!key:-"❌ 未设置"}
    TMP_VAL=$(cd /tmp && echo ${!key:-"❌ 未设置"})
    
    if [ "$CURRENT_VAL" = "$TMP_VAL" ]; then
        echo "✅ $key: $CURRENT_VAL"
    else
        red "❌ $key 环境变量不一致！"
        echo "  当前目录: $CURRENT_VAL"
        echo "  /tmp目录: $TMP_VAL"
        ENV_DIFF=1
    fi
done

if [ $ENV_DIFF -eq 1 ]; then
    echo
    yellow "⚠️  环境变量差异修复建议："
    echo "   1. 编辑全局配置：nano ~/.bashrc"
    echo "   2. 添加固定环境变量（示例）："
    echo "      export MCP_CONFIG=/home/$(whoami)/mcp/config.json"
    echo "      export PATH=\$PATH:/usr/local/bin"
    echo "   3. 生效配置：source ~/.bashrc"
fi
echo

blue "【4/6】目录权限检查"
CHECK_DIRS=("$(pwd)" "/tmp" "$HOME")

for dir in "${CHECK_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        PERM=$(ls -ld $dir | awk '{print $1}')
        OWNER=$(ls -ld $dir | awk '{print $3":"$4}')
        WRITABLE="❌ 不可写"
        if [ -w $dir ]; then
            WRITABLE="✅ 可写"
        fi
        echo "$dir: 权限=$PERM 所属=$OWNER $WRITABLE"
    else
        echo "$dir: ❌ 目录不存在"
    fi
done

if [ "$(whoami)" != "root" ] && [ -w "$(pwd)" = false ]; then
    red "❌ 当前目录无写入权限（非root用户），MCP服务器可能无法生成日志/缓存"
    echo "   修复建议：chmod 755 $(pwd) 或 chown -R $(whoami):$(whoami) $(pwd)"
fi
echo

blue "【5/6】MCP核心依赖检查"
if command -v python3 &>/dev/null; then
    PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python3: $(which python3) (版本: $PYTHON_VER)"
    
    if python3 -m pip list 2>/dev/null | grep -i "mcp" &>/dev/null; then
        MCP_PKG=$(python3 -m pip list 2>/dev/null | grep -i "mcp" | head -1)
        green "✅ 检测到MCP依赖: $MCP_PKG"
    else
        yellow "⚠️  未检测到MCP相关Python包（可能影响MCP服务器运行）"
    fi
else
    red "❌ 未找到Python3（MCP服务器核心依赖）"
    echo "   修复建议：sudo apt update && sudo apt install python3 python3-pip -y"
fi

if command -v node &>/dev/null; then
    echo "✅ Node.js: $(which node) (版本: $(node --version))"
else
    yellow "⚠️  未找到Node.js（部分MCP插件可能依赖）"
fi
echo

blue "【6/6】缓存/临时文件检查"
CACHE_COUNT=$(find ~/.cache -name "*claude*" -o -name "*mcp*" 2>/dev/null | wc -l)
TMP_COUNT=$(ls /tmp/*claude* /tmp/*mcp* 2>/dev/null | wc -l)

echo "Claude/MCP缓存文件数量: $CACHE_COUNT 个"
echo "临时目录相关文件数量: $TMP_COUNT 个"

if [ $CACHE_COUNT -gt 0 ] || [ $TMP_COUNT -gt 0 ]; then
    yellow "⚠️  建议清理缓存（解决多目录状态不一致问题）："
    echo "   执行命令：rm -rf ~/.cache/claude* ~/.cache/mcp* /tmp/claude* /tmp/mcp*"
else
    green "✅ 无缓存/临时文件堆积"
fi
echo

blue "==================== 快速修复命令（按需执行） ===================="
echo "# 1. 统一环境变量（编辑后需重启终端）"
echo "echo 'export MCP_CONFIG=\$HOME/mcp/config.json' >> ~/.bashrc && source ~/.bashrc"
echo
echo "# 2. 清理缓存"
echo "rm -rf ~/.cache/claude* ~/.cache/mcp* /tmp/claude* /tmp/mcp*"
echo
echo "# 3. 修复目录权限"
echo "chown -R $(whoami):$(whoami) $(pwd) && chmod 755 $(pwd)"
echo
echo "# 4. 全局安装MCP依赖"
echo "python3 -m pip install --upgrade pip && python3 -m pip install mcp-server --user"
echo -e "\n✅ 检查完成！请根据红色/黄色提示优先修复对应问题。\n"
