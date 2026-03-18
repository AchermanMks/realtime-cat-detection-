#!/usr/bin/env python3
"""
摄像头发现和配置工具
帮助用户找到RTSP URL和云台控制地址
"""

import socket
import requests
import subprocess
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

class CameraDiscovery:
    """摄像头发现工具"""

    def __init__(self):
        self.discovered_cameras = []
        self.common_ports = [80, 554, 8080, 8000, 88, 8081, 37777, 34567]
        self.common_usernames = ['admin', 'root', 'user', 'viewer']
        self.common_passwords = ['admin', '123456', 'password', '888888', '12345', 'admin123']

    def scan_network(self, network="192.168.1", timeout=1):
        """扫描网络中的摄像头设备"""
        print(f"🔍 扫描网络 {network}.1-254...")

        active_ips = []

        def ping_host(ip):
            try:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return ip
            except:
                pass
            return None

        # 并行ping扫描
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for i in range(1, 255):
                ip = f"{network}.{i}"
                futures.append(executor.submit(ping_host, ip))

            for future in futures:
                result = future.result()
                if result:
                    active_ips.append(result)
                    print(f"✅ 发现活跃IP: {result}")

        print(f"📊 发现 {len(active_ips)} 个活跃设备")
        return active_ips

    def check_camera_ports(self, ip, timeout=2):
        """检查摄像头常用端口"""
        open_ports = []

        for port in self.common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports.append(port)
                    print(f"  ✅ {ip}:{port} 开放")
                sock.close()
            except:
                pass

        return open_ports

    def probe_web_interface(self, ip, port=80):
        """探测Web管理界面"""
        urls_to_try = [
            f"http://{ip}:{port}/",
            f"http://{ip}:{port}/index.html",
            f"http://{ip}:{port}/admin",
            f"http://{ip}:{port}/login.html",
            f"http://{ip}:{port}/web/",
        ]

        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=3, allow_redirects=True)
                if response.status_code == 200:
                    content = response.text.lower()

                    # 检测摄像头品牌
                    brands = {
                        'hikvision': ['hikvision', 'hik', 'dahua'],
                        'dahua': ['dahua', 'dh'],
                        'axis': ['axis'],
                        'foscam': ['foscam'],
                        'tp-link': ['tp-link', 'tplink'],
                        'xiaomi': ['xiaomi', 'mi'],
                        'uniview': ['uniview'],
                    }

                    detected_brand = None
                    for brand, keywords in brands.items():
                        if any(keyword in content for keyword in keywords):
                            detected_brand = brand
                            break

                    return {
                        'url': url,
                        'brand': detected_brand,
                        'title': self._extract_title(content),
                        'requires_auth': 'login' in content or 'password' in content
                    }
            except:
                continue

        return None

    def _extract_title(self, html):
        """提取网页标题"""
        try:
            start = html.find('<title>') + 7
            end = html.find('</title>')
            if start > 6 and end > start:
                return html[start:end].strip()
        except:
            pass
        return "Unknown"

    def test_rtsp_url(self, ip, port=554, username='admin', password='admin'):
        """测试RTSP URL"""

        # 常见RTSP路径模式
        rtsp_patterns = [
            # 海康威视
            "/Streaming/Channels/101",
            "/Streaming/Channels/1/Preview_01_sub",
            "/h264/ch1/main/av_stream",
            "/cam/realmonitor?channel=1&subtype=0",

            # 大华
            "/cam/realmonitor?channel=1&subtype=0",
            "/cam/realmonitor?channel=1&subtype=1",

            # 通用
            "/stream1",
            "/stream",
            "/video",
            "/live",
            "/h264",
            "/mjpeg",
            "/mpeg4",
            "/axis-media/media.amp",

            # TP-Link
            "/h264_stream",
            "/mjpg/video.mjpg",

            # 小米
            "/stream/0",
            "/video/PSIA/streaming/channels/1",
        ]

        working_urls = []

        for pattern in rtsp_patterns:
            rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{pattern}"

            print(f"  🔍 测试: rtsp://{username}:***@{ip}:{port}{pattern}")

            if self._test_rtsp_connection(rtsp_url):
                working_urls.append(rtsp_url)
                print(f"  ✅ 成功: {pattern}")

        return working_urls

    def _test_rtsp_connection(self, rtsp_url, timeout=5):
        """测试RTSP连接"""
        try:
            import cv2
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

            ret, frame = cap.read()
            cap.release()

            return ret and frame is not None
        except:
            return False

    def find_ptz_endpoints(self, ip, port=80, username='admin', password='admin'):
        """查找云台控制接口"""

        ptz_endpoints = [
            # 海康威视
            "/PSIA/PTZ/channels/1/continuous",
            "/cgi-bin/ptz.cgi",
            "/web/cgi-bin/hi3510/ptzctrl.cgi",

            # 大华
            "/cgi-bin/ptz.cgi",
            "/cgi-bin/camctrl.cgi",

            # 通用
            "/ptz",
            "/control/ptz",
            "/cgi/ptdc.cgi",
            "/cgi/mjpg/ptz.cgi",
            "/control",
            "/api/ptz",
        ]

        working_endpoints = []

        for endpoint in ptz_endpoints:
            url = f"http://{ip}:{port}{endpoint}"

            try:
                # 测试GET请求
                response = requests.get(url, auth=(username, password), timeout=3)
                if response.status_code in [200, 401, 403]:
                    working_endpoints.append({
                        'endpoint': endpoint,
                        'method': 'GET',
                        'status': response.status_code,
                        'auth_required': response.status_code == 401
                    })
                    print(f"  ✅ 发现PTZ接口: {endpoint} (GET)")

                # 测试POST请求
                response = requests.post(url, auth=(username, password), timeout=3)
                if response.status_code in [200, 401, 403]:
                    working_endpoints.append({
                        'endpoint': endpoint,
                        'method': 'POST',
                        'status': response.status_code,
                        'auth_required': response.status_code == 401
                    })
                    print(f"  ✅ 发现PTZ接口: {endpoint} (POST)")

            except:
                continue

        return working_endpoints

    def generate_config(self, camera_info):
        """生成配置代码"""
        config_code = f"""
# 摄像头配置 - 自动生成
# 设备IP: {camera_info['ip']}
# 品牌: {camera_info.get('brand', 'Unknown')}

# RTSP配置
RTSP_URL = "{camera_info.get('rtsp_url', 'rtsp://admin:password@' + camera_info['ip'] + ':554/stream1')}"

# 云台控制配置
PTZ_BASE_URL = "http://{camera_info['ip']}"
PTZ_USERNAME = "{camera_info.get('username', 'admin')}"
PTZ_PASSWORD = "{camera_info.get('password', 'admin')}"

# 检测到的PTZ接口:
"""

        if camera_info.get('ptz_endpoints'):
            config_code += "# PTZ接口:\n"
            for ep in camera_info['ptz_endpoints']:
                config_code += f"# - {ep['endpoint']} ({ep['method']})\n"

        return config_code

    def discover_cameras(self, network="192.168.1"):
        """完整的摄像头发现流程"""
        print("🎥 开始摄像头发现流程...")
        print("=" * 50)

        # 1. 网络扫描
        active_ips = self.scan_network(network)

        if not active_ips:
            print("❌ 未发现任何活跃设备")
            return

        # 2. 端口扫描和设备识别
        camera_candidates = []

        for ip in active_ips:
            print(f"\n🔍 检查设备: {ip}")

            # 检查端口
            open_ports = self.check_camera_ports(ip)

            if not open_ports:
                continue

            # 检查Web界面
            web_info = None
            if 80 in open_ports or 8080 in open_ports:
                web_port = 80 if 80 in open_ports else 8080
                web_info = self.probe_web_interface(ip, web_port)

            # 如果有554端口或检测到摄像头特征，添加为候选
            if 554 in open_ports or (web_info and web_info['brand']):
                camera_candidates.append({
                    'ip': ip,
                    'open_ports': open_ports,
                    'web_info': web_info
                })

                print(f"  🎯 疑似摄像头设备")
                if web_info:
                    print(f"    品牌: {web_info.get('brand', 'Unknown')}")
                    print(f"    标题: {web_info.get('title', 'Unknown')}")

        # 3. 详细测试摄像头
        for camera in camera_candidates:
            print(f"\n🎥 详细测试摄像头: {camera['ip']}")

            # 测试RTSP
            if 554 in camera['open_ports']:
                print("  🔍 测试RTSP连接...")
                rtsp_urls = self.test_rtsp_url(camera['ip'])
                camera['rtsp_urls'] = rtsp_urls

                if rtsp_urls:
                    print(f"  ✅ 找到 {len(rtsp_urls)} 个可用RTSP流")
                else:
                    print("  ❌ 未找到可用RTSP流")

            # 测试PTZ控制
            if 80 in camera['open_ports']:
                print("  🔍 测试PTZ控制...")
                ptz_endpoints = self.find_ptz_endpoints(camera['ip'])
                camera['ptz_endpoints'] = ptz_endpoints

                if ptz_endpoints:
                    print(f"  ✅ 找到 {len(ptz_endpoints)} 个PTZ接口")
                else:
                    print("  ❌ 未找到PTZ接口")

        # 4. 生成结果
        self.discovered_cameras = camera_candidates
        self.print_summary()

        return camera_candidates

    def print_summary(self):
        """打印发现结果摘要"""
        print("\n" + "=" * 50)
        print("📋 摄像头发现结果摘要")
        print("=" * 50)

        if not self.discovered_cameras:
            print("❌ 未发现摄像头设备")
            return

        for i, camera in enumerate(self.discovered_cameras, 1):
            print(f"\n📷 设备 {i}: {camera['ip']}")
            print("-" * 30)

            web_info = camera.get('web_info')
            if web_info:
                print(f"品牌: {web_info.get('brand', 'Unknown')}")
                print(f"标题: {web_info.get('title', 'Unknown')}")
                print(f"Web界面: {web_info['url']}")

            rtsp_urls = camera.get('rtsp_urls', [])
            if rtsp_urls:
                print("RTSP地址:")
                for url in rtsp_urls:
                    # 隐藏密码显示
                    display_url = url.replace(':admin@', ':***@')
                    print(f"  - {display_url}")

            ptz_endpoints = camera.get('ptz_endpoints', [])
            if ptz_endpoints:
                print("PTZ接口:")
                for ep in ptz_endpoints:
                    print(f"  - {ep['endpoint']} ({ep['method']})")

            # 生成配置
            config = self.generate_config(camera)
            print("\n配置代码:")
            print(config)

def main():
    """主函数"""
    print("🔍 摄像头发现工具")
    print("=" * 50)

    discovery = CameraDiscovery()

    # 获取用户网络段
    try:
        import netifaces
        gateways = netifaces.gateways()
        default_gateway = gateways['default'][netifaces.AF_INET][0]
        network = '.'.join(default_gateway.split('.')[:-1])
        print(f"💡 检测到网络段: {network}.x")
    except:
        network = "192.168.1"
        print(f"💡 使用默认网络段: {network}.x")

    # 用户输入
    user_network = input(f"输入网络段 (默认 {network}): ").strip()
    if user_network:
        network = user_network

    # 开始发现
    cameras = discovery.discover_cameras(network)

    # 提供下一步建议
    if cameras:
        print(f"\n🎉 发现了 {len(cameras)} 个摄像头设备！")
        print("\n📝 下一步操作:")
        print("1. 复制上面的配置代码到 robot_vision_config.py")
        print("2. 根据需要修改用户名密码")
        print("3. 运行 python3 robot_vision_main.py 测试系统")
    else:
        print("\n💡 未发现摄像头，可能的原因:")
        print("1. 摄像头不在当前网络段")
        print("2. 摄像头使用了非标准端口")
        print("3. 网络防火墙阻止了扫描")
        print("4. 摄像头需要特殊配置")

        print("\n🔧 手动配置建议:")
        print("1. 查看摄像头说明书获取默认IP")
        print("2. 使用厂商提供的配置工具")
        print("3. 检查路由器管理界面的设备列表")

if __name__ == "__main__":
    main()