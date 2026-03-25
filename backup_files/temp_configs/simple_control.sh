#!/bin/bash
# 最简单的PTZ控制命令

echo "🎮 简单PTZ控制"
echo "=============="

# 快捷变量
URL="https://192.168.31.146/ipc/grpc_cmd"
SESSION="8E7EB2F6FE2304F134901333A05631A"  # ✅ 已更新 - 从浏览器开发者工具获取
HEADERS=(-H 'Content-Type: application/json' -H "SessionId: $SESSION")

echo "选择控制动作:"
echo "1) 向左移动"
echo "2) 向右移动"
echo "3) 向上移动"
echo "4) 向下移动"
echo "5) 停止移动"
echo "6) 自动测试"
echo ""

read -p "请选择 (1-6): " choice

case $choice in
    1)
        echo "⬅️ 向左移动..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'
        echo "执行完成! 记得发送停止命令 (选项5)"
        ;;
    2)
        echo "➡️ 向右移动..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":-120}}'
        echo "执行完成! 记得发送停止命令 (选项5)"
        ;;
    3)
        echo "⬆️ 向上移动..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}'
        echo "执行完成! 记得发送停止命令 (选项5)"
        ;;
    4)
        echo "⬇️ 向下移动..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":-120}}'
        echo "执行完成! 记得发送停止命令 (选项5)"
        ;;
    5)
        echo "⏹️ 停止移动..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
        echo "✅ 已停止"
        ;;
    6)
        echo "🎯 自动测试 - 左右移动演示"
        echo "向左移动 3秒..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'
        sleep 3

        echo "停止..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
        sleep 1

        echo "向右移动 3秒..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":-120}}'
        sleep 3

        echo "停止..."
        curl --insecure -s "$URL" "${HEADERS[@]}" \
            --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
        echo "✅ 自动测试完成!"
        ;;
    *)
        echo "无效选择"
        ;;
esac