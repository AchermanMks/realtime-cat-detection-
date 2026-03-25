#!/bin/bash
# 测试PTZ控制的简化脚本
# 使用之前请更新SessionId

CAMERA_IP="192.168.31.146"
SESSION_ID="请在这里填入您的SessionId"

echo "🎮 测试PTZ控制"
echo "使用SessionId: $SESSION_ID"

# 测试停止命令
curl "https://$CAMERA_IP/ipc/grpc_cmd" \
  -H "Content-Type: application/json" \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}' \
  --insecure -s | jq .

echo "如果返回成功的JSON响应，说明SessionId有效"
