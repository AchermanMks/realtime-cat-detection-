#!/usr/bin/env python3
"""
测试发现的摄像头设备
"""

import cv2
import requests
import time

def test_web_interface(ip):
    """测试摄像头Web界面"""
    print(f"🌐 测试Web界面: http://{ip}")

    try:
        response = requests.get(f"http://{ip}", timeout=5)
        print(f"   ✅ Web界面响应正常 (状态码: {response.status_code})")

        # 尝试获取页面标题
        content = response.text
        if '<title>' in content:
            start = content.find('<title>') + 7
            end = content.find('</title>')
            title = content[start:end] if start > 6 and end > start else "未知"
            print(f"   📄 页面标题: {title[:50]}")

        # 检测摄像头品牌
        content_lower = content.lower()
        brands = {
            '小米': ['xiaomi', 'mi', 'mijia'],
            '海康威视': ['hikvision', 'hik'],
            '大华': ['dahua', 'dh'],
            'TP-Link': ['tp-link', 'tplink'],
            '萤石': ['ezviz'],
        }

        for brand, keywords in brands.items():
            if any(keyword in content_lower for keyword in keywords):
                print(f"   🏷️  检测到品牌: {brand}")
                break

        return True
    except Exception as e:
        print(f"   ❌ Web界面无法访问: {e}")
        return False

def test_rtsp_urls(ip, port, urls_to_test):
    """测试RTSP地址"""
    print(f"📡 测试RTSP连接: {ip}:{port}")

    working_urls = []

    for i, url in enumerate(urls_to_test, 1):
        print(f"\n   {i}. 测试: {url.replace('admin:', '***:')}")

        try:
            cap = cv2.VideoCapture(url)

            # 设置超时和缓冲
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # 尝试读取帧
            start_time = time.time()
            ret, frame = cap.read()
            read_time = time.time() - start_time

            if ret and frame is not None:
                h, w, c = frame.shape
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f"      ✅ 连接成功!")
                print(f"      📊 分辨率: {w}x{h}")
                print(f"      🎬 帧率: {fps:.1f} fps")
                print(f"      ⏱️  响应时间: {read_time:.2f}秒")

                working_urls.append(url)

                # 保存测试帧
                test_frame_path = f"test_frame_{ip.replace('.', '_')}.jpg"
                cv2.imwrite(test_frame_path, frame)
                print(f"      💾 测试帧已保存: {test_frame_path}")

            else:
                print(f"      ❌ 无法获取视频帧")

            cap.release()

        except Exception as e:
            print(f"      ❌ 连接失败: {e}")

    return working_urls

def test_ptz_control(ip, username="admin", password="admin"):
    """测试云台控制"""
    print(f"🎮 测试云台控制: {ip}")

    # 常见PTZ接口
    ptz_endpoints = [
        "/cgi-bin/ptz.cgi",
        "/PSIA/PTZ/channels/1/continuous",
        "/api/ptz/move",
        "/control/ptz",
    ]

    working_endpoints = []

    for endpoint in ptz_endpoints:
        url = f"http://{ip}{endpoint}"
        print(f"   测试: {endpoint}")

        try:
            # 测试GET请求
            response = requests.get(url, auth=(username, password), timeout=3)
            if response.status_code in [200, 401, 403]:
                print(f"      ✅ 接口响应 (状态: {response.status_code})")
                working_endpoints.append(endpoint)
            else:
                print(f"      ❌ 无响应")

        except Exception as e:
            print(f"      ❌ 请求失败: {str(e)[:50]}")

    return working_endpoints

def main():
    """主函数"""
    print("🧪 测试发现的摄像头设备")
    print("=" * 50)

    # 定义发现的摄像头
    cameras = [
        {
            'ip': '192.168.31.146',
            'ports': [80, 8554],
            'type': '疑似小米摄像头',
            'rtsp_urls': [
                'rtsp://192.168.31.146:8554/unicast',
                'rtsp://admin:admin@192.168.31.146:8554/unicast',
                'rtsp://192.168.31.146:8554/stream/0',
                'rtsp://admin:@192.168.31.146:8554/unicast',
            ]
        },
        {
            'ip': '192.168.31.208',
            'ports': [554],
            'type': '标准RTSP摄像头',
            'rtsp_urls': [
                'rtsp://admin:admin@192.168.31.208:554/stream1',
                'rtsp://admin:12345@192.168.31.208:554/stream1',
                'rtsp://admin:password@192.168.31.208:554/stream1',
                'rtsp://admin:admin@192.168.31.208:554/Streaming/Channels/101',
                'rtsp://admin:admin@192.168.31.208:554/cam/realmonitor?channel=1&subtype=0',
                'rtsp://admin:admin@192.168.31.208:554/h264/ch1/main/av_stream',
            ]
        }
    ]

    results = []

    for i, camera in enumerate(cameras, 1):
        print(f"\n📷 测试设备 {i}: {camera['ip']} ({camera['type']})")
        print("=" * 60)

        camera_result = {
            'ip': camera['ip'],
            'type': camera['type'],
            'web_working': False,
            'rtsp_urls': [],
            'ptz_endpoints': []
        }

        # 测试Web界面
        if 80 in camera['ports']:
            camera_result['web_working'] = test_web_interface(camera['ip'])

        # 测试RTSP
        rtsp_port = 8554 if 8554 in camera['ports'] else 554
        working_urls = test_rtsp_urls(camera['ip'], rtsp_port, camera['rtsp_urls'])
        camera_result['rtsp_urls'] = working_urls

        # 测试PTZ控制
        if camera_result['web_working']:
            working_ptz = test_ptz_control(camera['ip'])
            camera_result['ptz_endpoints'] = working_ptz

        results.append(camera_result)

    # 生成总结报告
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    working_cameras = [r for r in results if r['rtsp_urls']]

    if working_cameras:
        print(f"🎉 找到 {len(working_cameras)} 个可用摄像头!")

        for i, camera in enumerate(working_cameras, 1):
            print(f"\n📷 摄像头 {i}: {camera['ip']} ({camera['type']})")
            print(f"   Web界面: {'✅ 可用' if camera['web_working'] else '❌ 不可用'}")
            print(f"   RTSP地址: {len(camera['rtsp_urls'])} 个可用")
            for url in camera['rtsp_urls']:
                print(f"     - {url}")
            print(f"   PTZ控制: {len(camera['ptz_endpoints'])} 个接口")

        # 生成配置代码
        best_camera = working_cameras[0]
        print(f"\n📋 推荐配置 (摄像头: {best_camera['ip']}):")
        print("-" * 40)
        config = f'''
# 复制以下配置到 robot_vision_config.py

# RTSP配置
RTSP_URL = "{best_camera['rtsp_urls'][0]}"

# 云台控制配置
PTZ_BASE_URL = "http://{best_camera['ip']}"
PTZ_USERNAME = "admin"
PTZ_PASSWORD = "admin"

# 如果需要，可以尝试其他RTSP地址:'''

        for url in best_camera['rtsp_urls'][1:]:
            config += f'\n# "{url}"'

        print(config)

        print(f"\n🚀 下一步操作:")
        print("1. 复制上面的配置到 robot_vision_config.py")
        print("2. 运行: python3 robot_vision_main.py")

    else:
        print("❌ 未找到可用的摄像头RTSP连接")
        print("\n🔧 故障排除建议:")
        print("1. 确认摄像头已开启RTSP功能")
        print("2. 检查用户名密码是否正确")
        print("3. 查看摄像头说明书确认RTSP路径")
        print("4. 尝试通过Web界面手动配置")

if __name__ == "__main__":
    main()