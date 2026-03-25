#!/usr/bin/env python3
"""
RTSP摄像头监控快速启动脚本
使用现有的web_camera_stream.py但针对RTSP优化
"""

import os
import sys
import subprocess
import time
import argparse
import signal

def get_xiaomi_rtsp_url(ip, username="admin", password="admin123", stream=1):
    """构建小米摄像头RTSP URL"""
    # 小米摄像头常见RTSP路径
    rtsp_paths = [
        f"rtsp://{username}:{password}@{ip}:554/unicast/c{stream}/s{stream}/live",
        f"rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel={stream}&subtype=0",
        f"rtsp://{username}:{password}@{ip}:554/stream{stream}",
        f"rtsp://{username}:{password}@{ip}:554/live{stream}",
        f"rtsp://{username}:{password}@{ip}/cam{stream}",
    ]

    print("📡 小米摄像头可能的RTSP URL:")
    for i, url in enumerate(rtsp_paths, 1):
        print(f"  {i}. {url}")

    return rtsp_paths[0]  # 返回最常用的格式

def test_rtsp_connection(rtsp_url):
    """测试RTSP连接"""
    import cv2

    print(f"🔍 测试RTSP连接: {rtsp_url}")

    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                print(f"✅ RTSP连接成功: {w}x{h} @{fps}fps")
                cap.release()
                return True
            else:
                print("❌ 无法读取RTSP帧")
        else:
            print("❌ 无法打开RTSP流")

        cap.release()

    except Exception as e:
        print(f"❌ RTSP连接测试失败: {e}")

    return False

def start_web_monitor(rtsp_url, port=5000, with_ai=True):
    """启动Web监控界面"""
    web_camera_script = os.path.join(os.path.dirname(__file__), "web_camera_stream.py")

    if not os.path.exists(web_camera_script):
        print(f"❌ 找不到web_camera_stream.py文件: {web_camera_script}")
        return False

    print(f"🌐 启动Web监控界面...")
    print(f"📱 访问地址: http://localhost:{port}")

    # 构建命令
    cmd = [
        sys.executable,
        web_camera_script,
        "--rtsp", rtsp_url,
        "--port", str(port)
    ]

    print(f"🚀 执行命令: {' '.join(cmd)}")

    try:
        # 启动Web服务
        process = subprocess.Popen(cmd)

        print("🛑 按 Ctrl+C 停止监控")

        # 等待用户中断
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 正在停止监控...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        return True

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def start_simple_viewer(rtsp_url):
    """启动简单RTSP查看器"""
    rtsp_viewer_script = os.path.join(os.path.dirname(__file__), "rtsp_viewer.py")

    if not os.path.exists(rtsp_viewer_script):
        print(f"❌ 找不到rtsp_viewer.py文件: {rtsp_viewer_script}")
        return False

    cmd = [sys.executable, rtsp_viewer_script, rtsp_url]

    print(f"🚀 启动简单RTSP查看器...")

    try:
        subprocess.run(cmd)
        return True
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def interactive_setup():
    """交互式设置"""
    print("🎥 RTSP摄像头监控快速设置")
    print("=" * 50)

    # 获取摄像头IP
    camera_ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not camera_ip:
        camera_ip = "192.168.31.146"

    # 获取认证信息
    username = input("请输入用户名 (默认: admin): ").strip()
    if not username:
        username = "admin"

    password = input("请输入密码 (默认: admin123): ").strip()
    if not password:
        password = "admin123"

    # 选择监控模式
    print("\n📺 选择监控模式:")
    print("  1. 完整Web界面 + AI分析 (推荐)")
    print("  2. 简单RTSP显示")
    print("  3. 自定义RTSP URL")

    choice = input("请选择 (1-3): ").strip()

    if choice == "3":
        rtsp_url = input("请输入完整RTSP URL: ").strip()
    else:
        rtsp_url = get_xiaomi_rtsp_url(camera_ip, username, password)
        print(f"\n📡 使用RTSP URL: {rtsp_url}")

    # 测试连接
    print(f"\n🔍 测试RTSP连接...")
    if not test_rtsp_connection(rtsp_url):
        print("\n⚠️ RTSP连接测试失败，但仍可以尝试启动监控")
        if input("是否继续? (y/N): ").strip().lower() != 'y':
            return

    # 启动监控
    if choice == "2":
        start_simple_viewer(rtsp_url)
    else:
        port = input("\nWeb服务端口 (默认: 5000): ").strip()
        if not port.isdigit():
            port = 5000
        else:
            port = int(port)

        start_web_monitor(rtsp_url, port)

def show_examples():
    """显示使用示例"""
    print("📺 RTSP摄像头监控使用示例")
    print("=" * 60)

    examples = [
        ("小米摄像头 (自动检测)",
         "python start_rtsp_monitor.py --ip 192.168.31.146"),

        ("小米摄像头 (指定认证)",
         "python start_rtsp_monitor.py --ip 192.168.31.146 --username admin --password admin123"),

        ("自定义RTSP URL",
         "python start_rtsp_monitor.py --rtsp rtsp://user:pass@192.168.1.100:554/stream"),

        ("简单显示模式",
         "python start_rtsp_monitor.py --ip 192.168.31.146 --simple"),

        ("指定Web端口",
         "python start_rtsp_monitor.py --ip 192.168.31.146 --port 8080"),
    ]

    for title, cmd in examples:
        print(f"\n🔸 {title}:")
        print(f"   {cmd}")

    print(f"\n💡 常见RTSP URL格式:")
    print(f"   rtsp://用户名:密码@IP:端口/路径")
    print(f"   rtsp://admin:admin123@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RTSP摄像头监控快速启动')
    parser.add_argument('--ip', '-i', help='摄像头IP地址')
    parser.add_argument('--username', '-u', default='admin', help='用户名 (默认: admin)')
    parser.add_argument('--password', '-p', default='admin123', help='密码 (默认: admin123)')
    parser.add_argument('--rtsp', '-r', help='完整RTSP URL')
    parser.add_argument('--port', type=int, default=5000, help='Web服务端口 (默认: 5000)')
    parser.add_argument('--simple', '-s', action='store_true', help='使用简单RTSP查看器')
    parser.add_argument('--test', '-t', action='store_true', help='仅测试RTSP连接')
    parser.add_argument('--examples', '-e', action='store_true', help='显示使用示例')

    args = parser.parse_args()

    if args.examples:
        show_examples()
        return

    # 确定RTSP URL
    if args.rtsp:
        rtsp_url = args.rtsp
    elif args.ip:
        rtsp_url = get_xiaomi_rtsp_url(args.ip, args.username, args.password)
    else:
        # 交互式模式
        interactive_setup()
        return

    print(f"📡 RTSP URL: {rtsp_url}")

    # 仅测试连接
    if args.test:
        success = test_rtsp_connection(rtsp_url)
        sys.exit(0 if success else 1)

    # 启动监控
    if args.simple:
        start_simple_viewer(rtsp_url)
    else:
        start_web_monitor(rtsp_url, args.port)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 无参数时显示帮助和交互模式选项
        print("📺 RTSP摄像头监控快速启动")
        print("=" * 50)
        print("选择启动方式:")
        print("  1. 交互式设置")
        print("  2. 查看使用示例")
        print("  3. 退出")

        choice = input("\n请选择 (1-3): ").strip()

        if choice == "1":
            interactive_setup()
        elif choice == "2":
            show_examples()
        else:
            print("👋 再见!")
    else:
        main()