#!/usr/bin/env python3
"""
智能PTZ摄像头监控系统启动脚本
集成自动SessionId管理的完整解决方案
"""

import subprocess
import sys
import time

def main():
    print("🚀 智能PTZ摄像头监控系统")
    print("=" * 60)
    print()
    print("🔧 此系统解决了以下问题:")
    print("   ✅ SessionId自动刷新 - 无需手动更新")
    print("   ✅ 连接失败自动重试")
    print("   ✅ 智能错误检测和恢复")
    print("   ✅ 完整的PTZ控制功能")
    print()

    # 获取摄像头配置
    camera_ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not camera_ip:
        camera_ip = "192.168.31.146"

    camera_user = input("请输入用户名 (默认: admin): ").strip()
    if not camera_user:
        camera_user = "admin"

    camera_pass = input("请输入密码 (默认: admin123): ").strip()
    if not camera_pass:
        camera_pass = "admin123"

    # 选择视频源
    print("\n📹 选择视频源:")
    print("1. RTSP摄像头流")
    print("2. 本地摄像头")

    choice = input("请选择 (1/2, 默认: 1): ").strip()

    if choice == "2":
        camera_url = 0  # 本地摄像头
        rtsp_url = None
    else:
        # 构建RTSP URL
        rtsp_url = f"rtsp://{camera_user}:{camera_pass}@{camera_ip}/stream1"
        camera_url = None

    # 构建启动命令
    cmd = [
        sys.executable,
        "integrated_camera_system.py",
        "--camera-ip", camera_ip,
        "--camera-user", camera_user,
        "--camera-pass", camera_pass,
    ]

    if rtsp_url:
        cmd.extend(["--rtsp", rtsp_url])
    else:
        cmd.extend(["--camera", "0"])

    print(f"\n🎯 启动配置:")
    print(f"   摄像头IP: {camera_ip}")
    print(f"   用户名: {camera_user}")
    print(f"   视频源: {'RTSP流' if rtsp_url else '本地摄像头'}")
    print(f"   Web端口: 5000")
    print()

    print("🚀 启动智能PTZ监控系统...")
    print("💡 系统将自动处理SessionId刷新，无需手动干预")
    print("🌐 浏览器访问: http://localhost:5000")
    print("🛑 按 Ctrl+C 停止系统")
    print("-" * 60)

    try:
        # 启动系统
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 用户停止了系统")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 系统启动失败: {e}")
        print("\n🔧 故障排除建议:")
        print("   1. 检查摄像头IP地址和网络连接")
        print("   2. 确认用户名和密码正确")
        print("   3. 确保摄像头支持RTSP流")
        print("   4. 检查防火墙设置")
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")

def test_smart_controller():
    """测试智能PTZ控制器"""
    print("🧪 智能PTZ控制器独立测试")
    print("=" * 50)

    camera_ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not camera_ip:
        camera_ip = "192.168.31.146"

    cmd = [sys.executable, "smart_ptz_controller.py"]

    print(f"🔍 测试摄像头: {camera_ip}")
    print("🎮 这将测试PTZ控制和SessionId自动管理")
    print("-" * 40)

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    print("🎛️ 智能PTZ系统工具")
    print("=" * 40)
    print("1. 启动完整监控系统")
    print("2. 测试PTZ控制器")
    print("3. 退出")

    choice = input("\n请选择 (1/2/3): ").strip()

    if choice == "1":
        main()
    elif choice == "2":
        test_smart_controller()
    else:
        print("👋 退出")