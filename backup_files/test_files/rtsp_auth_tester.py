#!/usr/bin/env python3
"""RTSP认证测试工具"""
import cv2
import time

# 常见的摄像头认证组合
CREDENTIALS = [
    "",  # 无认证
    "admin:admin",
    "admin:admin123",
    "admin:",
    "admin:password",
    "admin:123456",
    "admin:12345678",
    "root:root",
    "root:admin",
    "user:user",
    "guest:guest",
    "admin:888888",
    "admin:000000",
]

# RTSP URL模板
CAMERA_CONFIGS = [
    "192.168.31.146:8554/unicast",
    "192.168.31.146:8554/stream1",
    "192.168.31.146:8554/",
    "192.168.31.208:554/stream1",
    "192.168.31.208:554/",
]

def test_rtsp_connection(camera_ip_port, credentials=""):
    """测试RTSP连接"""
    if credentials:
        url = f"rtsp://{credentials}@{camera_ip_port}"
    else:
        url = f"rtsp://{camera_ip_port}"

    print(f"🔍 测试: {url}")

    # 尝试连接
    cap = cv2.VideoCapture(url)

    if cap.isOpened():
        # 尝试读取一帧
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            print(f"✅ 成功连接! URL: {url}")
            return url
        else:
            print(f"⚠️ 连接成功但无法读取帧")
    else:
        print(f"❌ 连接失败")

    return None

def main():
    print("🎥 RTSP摄像头认证测试工具")
    print("=" * 50)

    successful_urls = []

    for camera in CAMERA_CONFIGS:
        print(f"\n📡 测试摄像头: {camera}")
        print("-" * 30)

        for cred in CREDENTIALS:
            working_url = test_rtsp_connection(camera, cred)
            if working_url:
                successful_urls.append(working_url)
                print(f"🎉 发现工作的URL: {working_url}")
                break  # 找到工作的认证就停止测试这个摄像头

            time.sleep(0.5)  # 避免过快请求

    print("\n" + "=" * 50)
    print("📋 测试结果汇总")
    print("=" * 50)

    if successful_urls:
        print("🎉 发现以下可用的RTSP URL:")
        for i, url in enumerate(successful_urls, 1):
            print(f"  {i}. {url}")

        print(f"\n💡 使用建议:")
        print(f"python integrated_camera_system.py --rtsp \"{successful_urls[0]}\" --port 5000")
    else:
        print("❌ 未发现任何可用的RTSP连接")
        print("💡 建议:")
        print("1. 检查摄像头是否正确设置了RTSP功能")
        print("2. 确认摄像头的用户名和密码")
        print("3. 尝试通过摄像头的Web界面设置RTSP认证")

if __name__ == "__main__":
    main()