#!/bin/bash
# PTZ HTTP测试 - 避免SSL问题

echo "🔧 PTZ HTTP协议测试"
echo "===================="

# 设置基本信息
CAMERA_IP="192.168.31.146"
USERNAME="admin"
PASSWORD="admin123"

echo "📡 目标摄像头: $CAMERA_IP"
echo "🔑 认证信息: $USERNAME/***"
echo ""

# 测试1: 海康威视风格 HTTP
echo "测试 1: 海康威视风格 (HTTP)"
curl -u $USERNAME:$PASSWORD "http://$CAMERA_IP/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0" 2>/dev/null
echo ""

# 测试2: 现代API风格 HTTP
echo "测试 2: 现代API风格 (HTTP)"
curl -u $USERNAME:$PASSWORD "http://$CAMERA_IP/api/ptz?cmd=left&speed=3" 2>/dev/null
echo ""

# 测试3: 小米风格 HTTP
echo "测试 3: 小米风格 (HTTP)"
curl -u $USERNAME:$PASSWORD "http://$CAMERA_IP/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=left&-speed=5" 2>/dev/null
echo ""

# 测试4: POST JSON HTTP
echo "测试 4: POST JSON (HTTP)"
curl -u $USERNAME:$PASSWORD -X POST -H "Content-Type: application/json" -d '{"action":"move","direction":"left","speed":5}' "http://$CAMERA_IP/api/ptz" 2>/dev/null
echo ""

# 测试5: 尝试发现端点
echo "测试 5: 发现可能的端点"
endpoints=(
    "/cgi-bin/ptz.cgi"
    "/api/ptz"
    "/control/ptz"
    "/cgi-bin/hi3510/ptzctrl.cgi"
    "/web/cgi-bin/hi3510/ptzctrl.cgi"
    "/motor"
    "/mcu"
)

for endpoint in "${endpoints[@]}"; do
    echo "  测试端点: $endpoint"
    response=$(curl -s -o /dev/null -w "%{http_code}" -u $USERNAME:$PASSWORD "http://$CAMERA_IP$endpoint" 2>/dev/null)
    echo "    状态码: $response"
done

echo ""
echo "✅ HTTP测试完成"

# 如果需要HTTPS，配置SSL选项
echo ""
echo "📋 如果需要HTTPS，请安装支持旧SSL的curl:"
echo "export CURL_CA_BUNDLE=''"
echo "或使用以下命令:"
echo "curl --ssl-allow-beast --ciphers 'DEFAULT:!DH' -k -u $USERNAME:$PASSWORD 'https://$CAMERA_IP/cgi-bin/ptz.cgi?action=start&code=Left'"