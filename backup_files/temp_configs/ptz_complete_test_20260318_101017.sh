#!/bin/bash
# 完整PTZ控制测试脚本
# 生成时间: 2026-03-18 10:10:17.761663

CAMERA_IP="192.168.31.146"
SESSION_ID="D1D66678A96617EF9555E42E67349E2"
BASE_URL="https://$CAMERA_IP/ipc/grpc_cmd"

echo '🎮 小米摄像头PTZ控制测试'
echo '============================'
echo ''

echo '🎯 向左移动'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'
echo ''
sleep 2

echo '🎯 向右移动'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panRight":120}}'
echo ''
sleep 2

echo '🎯 向上移动'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}'
echo ''
sleep 2

echo '🎯 向下移动'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltDown":120}}'
echo ''
sleep 2

echo '🎯 停止移动'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
echo ''
sleep 2

echo '🎯 放大'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomIn":120}}'
echo ''
sleep 2

echo '🎯 缩小'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomOut":120}}'
echo ''
sleep 2

echo '🎯 停止缩放'
curl --insecure -s \
  '$BASE_URL' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'Origin: https://$CAMERA_IP' \
  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \
  -H 'SessionId: $SESSION_ID' \
  --data-raw '{"method":"ptz_zoom_stop","param":{"channelid":0}}'
echo ''
sleep 2

