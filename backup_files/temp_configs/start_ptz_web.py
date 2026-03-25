#!/usr/bin/env python3
"""
自动启动PTZ Web控制界面 - 无需用户输入
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入PTZ控制器模块
from no_root_ptz_controller import start_web_server

if __name__ == "__main__":
    print("🎮 自动启动PTZ Web控制界面")
    print("🚀 Node.js代理应已在后台运行 (端口8899)")
    print()

    # 直接启动Web服务器，无需用户选择
    start_web_server(port=9999)