#!/bin/bash
# =============================================
#  拼多多 AI 客服 —— 服务器一键部署脚本
# =============================================
# 在你的 Linux 服务器上运行:
#   chmod +x setup_server.sh
#   sudo bash setup_server.sh
#
# 这个脚本会:
#   1. 检查并安装 Python3 / pip3
#   2. 安装 Flask、requests 等依赖
#   3. 引导你输入 DeepSeek API Key
#   4. 创建 systemd 服务,让服务器开机自启、崩溃自动重启
#   5. 开放防火墙 5000 端口
# =============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}   拼多多 AI 客服 —— 服务器部署${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---- 1. 检查 Python3 ----
echo -e "${YELLOW}[1/6] 检查 Python3 环境...${NC}"

if ! command -v python3 &>/dev/null; then
    echo "Python3 未安装,正在安装..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq python3 python3-pip
    elif command -v yum &>/dev/null; then
        yum install -y python3 python3-pip
    elif command -v dnf &>/dev/null; then
        dnf install -y python3 python3-pip
    else
        echo -e "${RED}无法识别包管理器,请手动安装 python3 和 pip3${NC}"
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version)
echo -e "  ${GREEN}✓${NC} $PYTHON_VERSION"

# ---- 2. 创建工作目录 ----
echo -e "${YELLOW}[2/6] 创建工作目录...${NC}"
WORKDIR="/opt/pdd-kefu"
mkdir -p "$WORKDIR"
echo -e "  ${GREEN}✓${NC} 工作目录: $WORKDIR"

# ---- 3. 安装 Python 依赖 ----
echo -e "${YELLOW}[3/6] 安装 Python 依赖...${NC}"
pip3 install --quiet flask flask-cors requests gunicorn
echo -e "  ${GREEN}✓${NC} 依赖安装完成"

# ---- 4. 复制 server.py ----
echo -e "${YELLOW}[4/6] 部署 server.py...${NC}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/server.py" ]; then
    cp "$SCRIPT_DIR/server.py" "$WORKDIR/server.py"
    echo -e "  ${GREEN}✓${NC} server.py 已复制到 $WORKDIR/"
else
    echo -e "  ${RED}✗${NC} 找不到 server.py! 请确保该文件与本脚本在同一目录"
    exit 1
fi

# ---- 5. 配置 API Key ----
echo -e "${YELLOW}[5/6] 配置 DeepSeek API Key...${NC}"
echo ""
echo "  请输入你的 DeepSeek API Key (以 sk- 开头):"
echo "  (输入时字符不会显示,直接粘贴后回车)"
read -s -p "  API Key: " API_KEY
echo ""

if [ -z "$API_KEY" ]; then
    echo -e "  ${YELLOW}⚠ 未输入 API Key,你可以在服务器启动后通过插件设置${NC}"
else
    echo "DEEPSEEK_API_KEY=\"$API_KEY\"" > "$WORKDIR/env.sh"
    chmod 600 "$WORKDIR/env.sh"
    echo -e "  ${GREEN}✓${NC} API Key 已保存"
fi

# ---- 6. 创建 systemd 服务 ----
echo -e "${YELLOW}[6/6] 创建系统服务...${NC}"

# 如果 env.sh 存在就加载,否则忽略
ENV_FILE_LINE=""
if [ -f "$WORKDIR/env.sh" ]; then
    ENV_FILE_LINE="EnvironmentFile=$WORKDIR/env.sh"
fi

cat > /etc/systemd/system/pdd-kefu.service << SYSTEMD_EOF
[Unit]
Description=拼多多 AI 客服服务器
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$WORKDIR
$ENV_FILE_LINE
ExecStart=/usr/bin/python3 -m gunicorn -w 2 -b 0.0.0.0:5000 server:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

systemctl daemon-reload
systemctl enable pdd-kefu
systemctl restart pdd-kefu

echo -e "  ${GREEN}✓${NC} 系统服务已创建并启动"

# ---- 防火墙 ----
if command -v ufw &>/dev/null; then
    ufw allow 5000/tcp 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 防火墙已开放 5000 端口"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-port=5000/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} firewalld 已开放 5000 端口"
fi

# ---- 验证 ----
sleep 2
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}  部署完成!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# 检查服务状态
if systemctl is-active --quiet pdd-kefu; then
    echo -e "  ${GREEN}✓${NC} 服务运行中"
    echo ""
    echo "  测试命令:"
    echo "    curl http://localhost:5000/api/health"
    echo "    curl http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '你的服务器IP'):5000/api/health"
else
    echo -e "  ${RED}✗${NC} 服务未正常运行,查看日志:"
    echo "    journalctl -u pdd-kefu -n 30 --no-pager"
fi

echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │  常用管理命令:                           │"
echo "  │  查看日志: journalctl -u pdd-kefu -f     │"
echo "  │  重启服务: systemctl restart pdd-kefu    │"
echo "  │  停止服务: systemctl stop pdd-kefu       │"
echo "  │  查看状态: systemctl status pdd-kefu     │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  重要提醒: 如果用的是云服务器(阿里云/腾讯云等),"
echo "  还需要在云控制台的"安全组"中放行 TCP 5000 端口!"
echo ""
