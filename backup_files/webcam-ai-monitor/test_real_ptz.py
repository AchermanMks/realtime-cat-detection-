#!/usr/bin/env python3
"""
测试真实PTZ控制
"""

import requests
import time

def test_real_camera_movement():
    """测试真实摄像头PTZ控制"""

    camera_ip = "192.168.31.146"
    username = input("请输入摄像头用户名 (默认: admin): ").strip() or "admin"
    password = input("请输入摄像头密码 (默认: admin): ").strip() or "admin"

    print(f"\n🔍 测试PTZ控制: {camera_ip}")

    # 海康威视测试
    hikvision_urls = [
        f"http://{camera_ip}/ISAPI/PTZ/channels/1/momentary?arg1=LEFT&arg2=50&arg3=1",
        f"http://{camera_ip}/ISAPI/PTZ/channels/1/momentary?arg1=STOP&arg2=0&arg3=0",
    ]

    print("测试海康威视协议...")
    for i, url in enumerate(hikvision_urls):
        try:
            response = requests.put(url, auth=(username, password), timeout=3)
            if response.status_code == 200:
                print(f"  ✅ 海康威视命令 {i+1} 成功")
                if i == 0:  # 向左转动
                    print("    📹 摄像头应该向左转动2秒...")
                    time.sleep(2)
                elif i == 1:  # 停止
                    print("    ⏹️ 摄像头应该停止移动")
            else:
                print(f"  ❌ 海康威视命令 {i+1} 失败: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 海康威视测试失败: {str(e)[:50]}...")

    # 大华测试
    print("\n测试大华协议...")
    dahua_urls = [
        f"http://{camera_ip}/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=50&arg2=50",
        f"http://{camera_ip}/cgi-bin/ptz.cgi?action=stop&channel=0",
    ]

    for i, url in enumerate(dahua_urls):
        try:
            response = requests.get(url, auth=(username, password), timeout=3)
            if "OK" in response.text:
                print(f"  ✅ 大华命令 {i+1} 成功")
                if i == 0:  # 向右转动
                    print("    📹 摄像头应该向右转动2秒...")
                    time.sleep(2)
                elif i == 1:  # 停止
                    print("    ⏹️ 摄像头应该停止移动")
            else:
                print(f"  ❌ 大华命令 {i+1} 失败")
        except Exception as e:
            print(f"  ❌ 大华测试失败: {str(e)[:50]}...")

if __name__ == "__main__":
    print("🎮 真实PTZ控制测试")
    print("注意: 只有在摄像头真实支持PTZ时才会看到画面移动")
    print("=" * 50)

    confirm = input("确认要测试真实PTZ控制吗？(y/N): ").strip().lower()
    if confirm == 'y':
        test_real_camera_movement()
    else:
        print("❌ 已取消测试")