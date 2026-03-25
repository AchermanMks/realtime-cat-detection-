#!/bin/bash
# 快速PTZ测试 - 立即验证控制功能

echo "🎮 快速PTZ控制测试"
echo "=================="

CAMERA_IP="192.168.31.146"
SESSION_ID="D1D66678A96617EF9555E42E67349E2"
URL="https://$CAMERA_IP/ipc/grpc_cmd"

# 测试1: 向左移动
echo "🎯 测试1: 向左移动 (3秒)"
curl --insecure -s "$URL" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'

sleep 3

# 停止移动
echo "⏹️ 停止移动"
curl --insecure -s "$URL" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'

echo ""
sleep 1

# 测试2: 向右移动
echo "🎯 测试2: 向右移动 (3秒)"
curl --insecure -s "$URL" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panRight":120}}'

sleep 3

# 停止移动
echo "⏹️ 停止移动"
curl --insecure -s "$URL" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'

echo ""
echo "✅ 快速PTZ测试完成！"
echo ""
echo "如果摄像头有移动，说明控制协议工作正常！"
echo "现在可以使用 Python 库或集成到 Web 系统中。"