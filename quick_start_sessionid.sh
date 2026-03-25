#!/bin/bash
# SessionId 快速获取脚本

echo "🚀 PTZ SessionId 快速获取"
echo "========================="

echo "选择获取方式:"
echo "1) 手动获取 (推荐) - 100%成功"
echo "2) 自动获取 (实验性) - 可能失败"
echo "3) 查看详细对比"

read -p "请选择 (1/2/3): " choice

case $choice in
    1)
        echo "🥇 启动手动获取工具..."
        python get_session_manual.py
        ;;
    2)
        echo "🤖 启动自动获取工具..."
        python get_session_auto.py
        ;;
    3)
        echo "📊 显示详细对比..."
        python sessionid_guide.py
        ;;
    *)
        echo "❌ 无效选择"
        ;;
esac
