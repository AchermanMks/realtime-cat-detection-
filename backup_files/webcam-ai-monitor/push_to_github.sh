#!/bin/bash

# 推送到GitHub脚本
# 在GitHub上创建仓库后运行此脚本

echo "🚀 推送Web版智能摄像头监控系统到GitHub..."
echo "============================================"

# 检查远程仓库配置
echo "📡 远程仓库配置:"
git remote -v

# 检查当前分支和提交
echo ""
echo "📋 当前提交状态:"
git log --oneline -5

# 开始推送
echo ""
echo "🌐 开始推送到GitHub..."
echo "目标仓库: https://github.com/jial92286/webcam-ai-monitor"
echo ""

# 推送代码
if git push -u origin main; then
    echo ""
    echo "🎉 成功推送到GitHub!"
    echo "============================================"
    echo "📱 访问你的项目:"
    echo "   https://github.com/jial92286/webcam-ai-monitor"
    echo ""
    echo "📚 项目包含:"
    echo "   ✅ 完整的Web应用代码 (app.py)"
    echo "   ✅ 详细的README文档"
    echo "   ✅ 自动安装脚本 (setup.sh)"
    echo "   ✅ 快速启动脚本 (start.sh)"
    echo "   ✅ 配置文件和依赖列表"
    echo "   ✅ GitHub部署指南"
    echo ""
    echo "🔗 克隆命令:"
    echo "   git clone https://github.com/jial92286/webcam-ai-monitor.git"
    echo ""
    echo "🚀 使用命令:"
    echo "   cd webcam-ai-monitor"
    echo "   ./setup.sh      # 安装依赖"
    echo "   ./start.sh      # 启动系统"
else
    echo ""
    echo "❌ 推送失败!"
    echo "============================================"
    echo "可能的原因:"
    echo "1. GitHub仓库尚未创建"
    echo "2. 网络连接问题"
    echo "3. 认证问题"
    echo ""
    echo "解决方案:"
    echo "1. 确保在GitHub上创建了仓库: webcam-ai-monitor"
    echo "2. 检查网络连接"
    echo "3. 如果需要认证，请使用个人访问令牌"
    echo ""
    echo "手动推送命令:"
    echo "   git push -u origin main"
fi