#!/usr/bin/env python3
"""
优化版PTZ系统启动器 - 解决CUDA内存问题
"""

import os
import sys
import subprocess
import signal

def optimize_gpu_memory():
    """优化GPU内存设置"""
    print("🔧 配置GPU内存优化...")

    # 设置PyTorch内存管理
    os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:True'

    # 设置CUDA内存管理
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

    # 启用PyTorch内存池优化
    os.environ['PYTORCH_CUDA_MEMORY_MANAGEMENT'] = '1'

    print("✅ GPU内存优化已配置")

def start_system():
    """启动优化的PTZ系统"""
    print("🚀 启动优化版PTZ监控系统...")

    # 应用内存优化
    optimize_gpu_memory()

    # 启动命令
    cmd = [
        sys.executable,
        'final_ptz_system.py',
        '--rtsp', 'rtsp://admin:admin123@192.168.31.146:8554/stream1',
        '--port', '5005'
    ]

    print(f"📡 RTSP摄像头: rtsp://admin:admin123@192.168.31.146:8554/stream1")
    print(f"🌐 Web界面: http://localhost:5005")
    print(f"🧠 AI分析: Qwen2-VL (GPU优化)")
    print("=" * 60)

    try:
        # 启动系统
        process = subprocess.Popen(cmd)

        print("✅ 系统启动成功")
        print("🛑 按 Ctrl+C 停止")

        # 等待信号
        process.wait()

    except KeyboardInterrupt:
        print("\n🛑 接收到停止信号...")
        process.terminate()
        print("✅ 系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    start_system()