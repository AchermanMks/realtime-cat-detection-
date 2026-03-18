#!/bin/bash
# gRPC PTZ控制测试命令
# 基于发现的 /ipc/grpc_cmd 端点

CAMERA_IP="192.168.31.146"
USERNAME="admin"
PASSWORD="admin123"
GRPC_URL="https://$CAMERA_IP/ipc/grpc_cmd"

echo "🔧 gRPC PTZ控制测试"
echo "===================="

# 测试1: JSON Payload
echo "测试 1: JSON格式PTZ命令"
curl -k -u $USERNAME:$PASSWORD \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d '{"command": "ptz", "action": "move", "direction": "left", "speed": 5}' \
    "$GRPC_URL"

echo ""

# 测试2: protobuf格式 (需要从浏览器获取真实payload)
echo "测试 2: ProtoBuf格式PTZ命令"
echo "# 需要从浏览器开发者工具获取真实的Payload"
echo "# curl -k -u $USERNAME:$PASSWORD -X POST -H 'Content-Type: application/grpc-web+proto' --data-binary @payload.bin $GRPC_URL"

echo ""

# 测试3: 模拟浏览器请求
echo "测试 3: 模拟浏览器请求"
curl -k -u $USERNAME:$PASSWORD \
    -X POST \
    -H "Content-Type: application/grpc-web+proto" \
    -H "Accept: application/grpc-web+proto" \
    -H "User-Agent: Mozilla/5.0" \
    -H "Origin: https://$CAMERA_IP" \
    -H "Referer: https://$CAMERA_IP/setting.html" \
    --data-raw "[从浏览器粘贴真实payload]" \
    "$GRPC_URL"
