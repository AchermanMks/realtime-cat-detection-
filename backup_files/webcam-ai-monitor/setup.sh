#!/bin/bash

# Web版智能摄像头监控系统 - 安装脚本
# 支持Ubuntu/Debian和CentOS/RHEL系统

echo "🚀 Web版智能摄像头监控系统安装脚本"
echo "=========================================="

# 检查操作系统
if command -v apt-get &> /dev/null; then
    OS="ubuntu"
    echo "✅ 检测到Ubuntu/Debian系统"
elif command -v yum &> /dev/null; then
    OS="centos"
    echo "✅ 检测到CentOS/RHEL系统"
else
    echo "❌ 不支持的操作系统"
    exit 1
fi

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+' | head -1)
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ 需要Python 3.8+，当前版本: $python_version"
    exit 1
else
    echo "✅ Python版本检查通过: $python_version"
fi

# 安装系统依赖
echo "📦 安装系统依赖..."
if [ "$OS" = "ubuntu" ]; then
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv libgl1-mesa-glx libglib2.0-0 \
                            libsm6 libxext6 libxrender-dev libgomp1
elif [ "$OS" = "centos" ]; then
    sudo yum update -y
    sudo yum install -y python3-pip mesa-libGL glib2
fi

# 创建虚拟环境
echo "🐍 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate
echo "✅ 虚拟环境已激活"

# 升级pip
echo "📦 升级pip..."
pip install --upgrade pip

# 安装Python依赖
echo "📦 安装Python依赖包..."
pip install -r requirements.txt

# 安装Qwen VL工具包
echo "🤖 安装Qwen VL工具包..."
pip install qwen-vl-utils

# 检查CUDA是否可用
echo "🔍 检查CUDA支持..."
python3 -c "
import torch
print('✅ PyTorch版本:', torch.__version__)
if torch.cuda.is_available():
    print('✅ CUDA可用，GPU数量:', torch.cuda.device_count())
    print('✅ GPU型号:', torch.cuda.get_device_name(0))
else:
    print('⚠️ CUDA不可用，将使用CPU模式')
"

# 创建必要目录
echo "📁 创建项目目录..."
mkdir -p logs captures temp

# 运行配置验证
echo "🔧 验证系统配置..."
python3 config.py

# 完成安装
echo ""
echo "🎉 安装完成！"
echo "=========================================="
echo "使用方法:"
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 修改config.py中的摄像头配置"
echo "3. 启动系统: python3 app.py"
echo "4. 访问: http://localhost:5000"
echo ""
echo "注意事项:"
echo "- 首次运行会下载AI模型 (~15GB)"
echo "- 确保摄像头URL配置正确"
echo "- 推荐使用GPU加速以获得更好性能"
echo ""
echo "故障排除:"
echo "- 如果摄像头连接失败，请检查config.py中的URL"
echo "- 如果模型加载失败，请检查网络连接"
echo "- 如果内存不足，请尝试使用较小的模型"