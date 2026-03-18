#!/bin/bash
# 完美PTZ控制测试 - 基于正确破解的协议

echo "🎮 完美PTZ控制测试"
echo "=================="
echo "基于正确破解的协议格式"
echo ""

CAMERA_IP="192.168.31.146"
SESSION_ID="D1D66678A96617EF9555E42E67349E2"
URL="https://$CAMERA_IP/ipc/grpc_cmd"

# 公共请求头
HEADERS=(
    -H "Accept: application/json, text/javascript, */*; q=0.01"
    -H "Content-Type: application/json; charset=UTF-8"
    -H "Origin: https://$CAMERA_IP"
    -H "Referer: https://$CAMERA_IP/ptzManager/ptzControl.html"
    -H "SessionId: $SESSION_ID"
    -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    -H "X-Requested-With: XMLHttpRequest"
)

echo "🎯 测试1: 向左移动 (panLeft: 120)"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'
echo ""
sleep 3

echo "⏹️ 停止移动"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
echo ""
sleep 1

echo "🎯 测试2: 向右移动 (panLeft: -120)"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":-120}}'
echo ""
sleep 3

echo "⏹️ 停止移动"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
echo ""
sleep 1

echo "🎯 测试3: 向上移动 (tiltUp: 120)"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}'
echo ""
sleep 2

echo "⏹️ 停止移动"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
echo ""
sleep 1

echo "🎯 测试4: 向下移动 (tiltUp: -120)"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":-120}}'
echo ""
sleep 2

echo "⏹️ 停止移动"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
echo ""
sleep 1

echo "🎯 测试5: 对角线移动 (左上)"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120,"tiltUp":120}}'
echo ""
sleep 2

echo "⏹️ 停止移动"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
echo ""
sleep 1

echo "🔍 测试6: 放大"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomIn":120}}'
echo ""
sleep 2

echo "⏹️ 停止缩放"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_zoom_stop","param":{"channelid":0}}'
echo ""
sleep 1

echo "🔍 测试7: 缩小"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomOut":120}}'
echo ""
sleep 2

echo "⏹️ 停止缩放"
curl --insecure -s "$URL" "${HEADERS[@]}" \
    --data-raw '{"method":"ptz_zoom_stop","param":{"channelid":0}}'
echo ""

echo "✅ 完美PTZ控制测试完成！"
echo ""
echo "📋 协议总结:"
echo "- panLeft: 正值向左，负值向右"
echo "- tiltUp: 正值向上，负值向下"
echo "- 可以同时控制pan和tilt实现对角线移动"
echo "- zoomIn/zoomOut: 正值表示速度"
echo "- 所有移动都需要手动发送stop命令"
echo ""
echo "🎉 协议已完全破解！可以进行任意PTZ控制！"