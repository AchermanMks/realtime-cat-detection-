#!/usr/bin/env python3
"""
快速测试你的摄像头连接
使用方法: python3 test_my_camera.py
"""

import cv2

def test_camera_urls():
    """测试常见的摄像头URL格式"""

    # 请修改为你的摄像头IP
    CAMERA_IP = "192.168.1.100"  # 修改为你的摄像头IP
    USERNAME = "admin"           # 修改为你的用户名
    PASSWORD = "admin"           # 修改为你的密码

    # 常见URL格式
    test_urls = [
        # 海康威视
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/Streaming/Channels/101",
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/h264/ch1/main/av_stream",

        # 大华
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/cam/realmonitor?channel=1&subtype=0",

        # TP-Link
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/stream1",
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/stream2",

        # 小米
        f"rtsp://{CAMERA_IP}:8554/unicast",
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:8554/unicast",

        # 通用
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/video",
        f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/live",
    ]

    print(f"🎥 测试摄像头: {CAMERA_IP}")
    print("=" * 50)

    working_urls = []

    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. 测试: {url.replace(PASSWORD, '***')}")

        try:
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"   ✅ 连接成功! 分辨率: {w}x{h}")
                working_urls.append(url)
            else:
                print(f"   ❌ 连接失败: 无法获取视频帧")

        except Exception as e:
            print(f"   ❌ 连接失败: {str(e)}")

    # 结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)

    if working_urls:
        print(f"🎉 找到 {len(working_urls)} 个可用URL:")
        for i, url in enumerate(working_urls, 1):
            print(f"\n{i}. {url}")

        # 生成配置
        print("\n📋 配置代码 (复制到 robot_vision_config.py):")
        print("-" * 40)
        print(f'''
# 摄像头配置
RTSP_URL = "{working_urls[0]}"

# 云台控制配置
PTZ_BASE_URL = "http://{CAMERA_IP}"
PTZ_USERNAME = "{USERNAME}"
PTZ_PASSWORD = "{PASSWORD}"
''')

    else:
        print("❌ 未找到可用的RTSP地址")
        print("\n💡 解决建议:")
        print("1. 确认摄像头IP地址正确")
        print("2. 检查用户名密码是否正确")
        print("3. 确认摄像头支持RTSP协议")
        print("4. 检查网络连接")
        print("5. 查看摄像头说明书获取正确的RTSP路径")

        print(f"\n🔧 手动配置步骤:")
        print(f"1. 浏览器打开: http://{CAMERA_IP}")
        print(f"2. 登录摄像头Web界面")
        print(f"3. 查找'网络设置'→'RTSP设置'")
        print(f"4. 记录RTSP端口和路径")

def check_network_connectivity():
    """检查网络连通性"""
    import subprocess

    CAMERA_IP = "192.168.1.100"  # 修改为你的IP

    print(f"\n🌐 检查网络连通性: {CAMERA_IP}")
    print("-" * 30)

    try:
        result = subprocess.run(['ping', '-c', '3', CAMERA_IP],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            print("✅ 网络连通正常")
            return True
        else:
            print("❌ 网络不通，请检查:")
            print("  1. IP地址是否正确")
            print("  2. 摄像头是否开机")
            print("  3. 是否在同一网络")
            return False

    except Exception as e:
        print(f"❌ 网络测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🎥 摄像头连接测试工具")
    print("=" * 50)
    print("📝 使用前请修改脚本中的IP地址和账号信息")
    print("=" * 50)

    # 检查网络
    if check_network_connectivity():
        # 测试RTSP
        test_camera_urls()

    print("\n✅ 测试完成!")