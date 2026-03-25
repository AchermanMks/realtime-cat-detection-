#!/bin/bash

echo "🚀 GitHub仓库设置脚本"
echo "================================"

echo "📋 请按照以下步骤操作:"
echo ""
echo "1. 访问 https://github.com/AchermanMks"
echo "2. 点击 'Repositories' 选项卡"
echo "3. 点击绿色的 'New' 按钮"
echo "4. 仓库名称设置为: rtsp-ai-monitor"
echo "5. 描述: 🎥 基于AI的智能实时摄像头监控系统，支持RTSP流、VLM分析和PTZ控制"
echo "6. 选择 'Public' (公开仓库)"
echo "7. 不要勾选 'Add a README file' (我们已经有了)"
echo "8. 点击 'Create repository'"
echo ""

read -p "✅ 仓库创建完成后，按回车键继续..." -r

echo "📤 正在推送到GitHub..."

# 推送到GitHub
if git push -u origin main; then
    echo ""
    echo "🎉 成功上传到GitHub!"
    echo "🌐 仓库地址: https://github.com/AchermanMks/rtsp-ai-monitor"
    echo ""
    echo "📋 项目包含:"
    echo "  📄 README.md - 详细使用说明"
    echo "  🎥 integrated_camera_system.py - 主程序"
    echo "  🔍 quick_scan.py - 摄像头发现工具"
    echo "  📦 requirements.txt - 依赖列表"
    echo "  🚀 start.sh - 启动脚本"
    echo "  ⚖️ LICENSE - MIT许可证"
else
    echo "❌ 推送失败，请检查:"
    echo "  1. 网络连接是否正常"
    echo "  2. GitHub仓库是否已创建"
    echo "  3. 仓库名称是否正确: rtsp-ai-monitor"
fi