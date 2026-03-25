#!/usr/bin/env python3
"""
PTZ控制演示脚本
展示所有PTZ功能并验证控制效果
"""

import requests
import time
import json

def test_ptz_api():
    """测试PTZ API"""
    print("🎮 PTZ控制演示")
    print("=" * 50)

    base_url = "http://localhost:5000/api/ptz"

    # PTZ命令序列
    commands = [
        ("停止", "stop", 1),
        ("向上", "up", 2),
        ("停止", "stop", 1),
        ("向下", "down", 2),
        ("停止", "stop", 1),
        ("向左", "left", 2),
        ("停止", "stop", 1),
        ("向右", "right", 2),
        ("停止", "stop", 1),
        ("放大", "zoom_in", 1),
        ("停止", "stop", 1),
        ("缩小", "zoom_out", 1),
        ("停止", "stop", 1),
    ]

    print(f"📡 测试API端点: {base_url}")
    print(f"🎯 将执行 {len(commands)} 个PTZ命令")
    print()

    for i, (name, action, duration) in enumerate(commands, 1):
        print(f"[{i:2d}/{len(commands)}] 📡 执行: {name} ({action})")

        try:
            response = requests.post(f"{base_url}/{action}", timeout=5)
            data = response.json()

            status = "✅ 成功" if data.get('success') else "❌ 失败"
            timestamp = time.strftime("%H:%M:%S", time.localtime(data.get('timestamp', time.time())))

            print(f"         结果: {status} | 时间: {timestamp}")

            if not data.get('success'):
                print(f"         详情: {data}")

        except Exception as e:
            print(f"         ❌ 错误: {e}")

        # 等待指定时间
        if duration > 0:
            print(f"         ⏱️  等待 {duration} 秒...")
            time.sleep(duration)

        print()

    print("🎉 PTZ演示完成!")
    print()
    print("💡 如果看到 '成功' 消息，说明PTZ控制正常工作")
    print("📹 请观察RTSP视频流中的画面变化来确认实际效果")

def test_direct_proxy():
    """直接测试PTZ代理"""
    print("🔧 直接测试PTZ代理")
    print("=" * 30)

    proxy_url = "http://localhost:8899/ptz"

    commands = ["stop", "up", "stop", "down", "stop"]

    for cmd in commands:
        try:
            response = requests.get(f"{proxy_url}/{cmd}", timeout=3)
            result = response.text
            print(f"PTZ代理 {cmd}: {result}")
        except Exception as e:
            print(f"PTZ代理 {cmd}: 错误 - {e}")

        time.sleep(0.5)

def show_system_status():
    """显示系统状态"""
    print("📊 系统状态检查")
    print("=" * 30)

    # 检查PTZ代理
    try:
        response = requests.get("http://localhost:8899/ptz/stop", timeout=3)
        proxy_status = "✅ 运行中" if response.text == "success" else "⚠️ 异常"
    except:
        proxy_status = "❌ 离线"

    # 检查主系统
    try:
        response = requests.get("http://localhost:5000/api/status", timeout=3)
        main_status = "✅ 运行中" if response.status_code == 200 else "⚠️ 异常"
    except:
        main_status = "❌ 离线"

    print(f"PTZ代理服务器 (8899): {proxy_status}")
    print(f"主监控系统 (5000): {main_status}")
    print()

if __name__ == "__main__":
    show_system_status()
    test_direct_proxy()
    print()
    test_ptz_api()

    print("🌐 Web访问地址:")
    print("   主监控系统: http://localhost:5000")
    print("   PTZ测试页面: file:///home/fusha/Desktop/vlm_test.py/ptz_test_page.html")