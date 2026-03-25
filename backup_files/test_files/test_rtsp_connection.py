#!/usr/bin/env python3
"""
RTSP连接测试工具
测试不同的RTSP URL和端口组合
"""

import cv2
import time

def test_rtsp_url(url, timeout=10):
    """测试RTSP URL是否可连接"""
    print(f"🔍 测试 RTSP: {url}")

    try:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # 设置超时
        start_time = time.time()

        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                print(f"✅ 连接成功: {width}x{height}")

                # 测试读取几帧
                for i in range(3):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    print(f"   帧 {i+1}: {frame.shape}")

                cap.release()
                return True
            else:
                print("❌ 无法读取帧")
        else:
            print("❌ 无法打开流")

        cap.release()
        return False

    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    """测试主函数"""
    print("🎥 RTSP连接测试工具")
    print("=" * 50)

    # 常见的RTSP URL模式
    rtsp_urls = [
        # 端口8554 (发现开放的端口)
        "rtsp://admin:admin123@192.168.31.146:8554/stream1",
        "rtsp://admin:admin123@192.168.31.146:8554/stream2",
        "rtsp://admin:admin123@192.168.31.146:8554/live",
        "rtsp://admin:admin123@192.168.31.146:8554/h264",
        "rtsp://admin:admin123@192.168.31.146:8554/",

        # 无端口（默认554）
        "rtsp://admin:admin123@192.168.31.146/stream1",
        "rtsp://admin:admin123@192.168.31.146/live",
        "rtsp://admin:admin123@192.168.31.146/h264",

        # 其他可能的端口
        "rtsp://192.168.31.146:8554/stream1",
        "rtsp://192.168.31.146:8554/live",
    ]

    working_urls = []

    for url in rtsp_urls:
        if test_rtsp_url(url):
            working_urls.append(url)
            break  # 找到一个工作的就够了
        print()

    if working_urls:
        print("🎉 找到可用的RTSP URL:")
        for url in working_urls:
            print(f"  ✅ {url}")

        # 保存配置
        config = {
            "working_rtsp_url": working_urls[0],
            "camera_ip": "192.168.31.146",
            "rtsp_port": 8554,
            "tested_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        import json
        with open('rtsp_config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f"💾 配置已保存到: rtsp_config.json")
        return working_urls[0]
    else:
        print("❌ 没有找到可用的RTSP URL")
        print("\n🔧 排查建议:")
        print("  1. 检查摄像头RTSP设置是否启用")
        print("  2. 确认用户名/密码正确")
        print("  3. 检查摄像头型号和RTSP支持")
        print("  4. 尝试其他RTSP客户端测试")
        return None

if __name__ == "__main__":
    main()