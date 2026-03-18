#!/usr/bin/env python3
"""
快速扫描网络中的摄像头设备
"""

import subprocess
import socket
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
import time

def ping_host(ip):
    """快速ping测试主机是否在线"""
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return ip if result.returncode == 0 else None
    except:
        return None

def check_camera_ports(ip):
    """检查摄像头常用端口"""
    camera_ports = [80, 554, 8080, 8000, 8554, 37777]
    open_ports = []

    for port in camera_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            if result == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass

    return open_ports

def check_web_interface(ip):
    """检查是否有Web界面"""
    try:
        response = requests.get(f"http://{ip}", timeout=2)
        content = response.text.lower()

        # 检测摄像头关键词
        camera_keywords = ['camera', 'webcam', 'ipcam', 'nvr', 'dvr', 'hikvision', 'dahua',
                          'axis', 'foscam', 'tp-link', 'xiaomi', 'uniview']

        is_camera = any(keyword in content for keyword in camera_keywords)

        return {
            'has_web': True,
            'is_camera': is_camera,
            'title': extract_title(content),
            'status_code': response.status_code
        }
    except:
        return {'has_web': False, 'is_camera': False}

def extract_title(html):
    """提取网页标题"""
    try:
        start = html.find('<title>') + 7
        end = html.find('</title>')
        if start > 6 and end > start:
            return html[start:end].strip()[:50]
    except:
        pass
    return ""

def scan_network(network="192.168.31"):
    """扫描网络"""
    print(f"🔍 扫描网络: {network}.1-254")
    print("=" * 50)

    # 第一步：ping扫描
    print("📡 第一步: Ping扫描活跃设备...")
    active_ips = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for i in range(1, 255):
            ip = f"{network}.{i}"
            futures.append(executor.submit(ping_host, ip))

        for future in futures:
            result = future.result()
            if result:
                active_ips.append(result)
                print(f"  ✅ {result} 在线")

    print(f"\n📊 发现 {len(active_ips)} 个活跃设备")

    if not active_ips:
        print("❌ 未发现任何活跃设备")
        return []

    # 第二步：端口和服务检测
    print("\n🔍 第二步: 检测摄像头设备...")
    camera_candidates = []

    for ip in active_ips:
        print(f"\n🎯 检测: {ip}")

        # 检查端口
        open_ports = check_camera_ports(ip)
        if open_ports:
            print(f"  📡 开放端口: {open_ports}")

            # 检查Web界面
            web_info = check_web_interface(ip)

            # 判断是否为摄像头
            is_camera_candidate = (
                554 in open_ports or  # RTSP端口
                8554 in open_ports or  # 小米RTSP端口
                web_info.get('is_camera', False)  # Web界面包含摄像头关键词
            )

            if is_camera_candidate:
                device_info = {
                    'ip': ip,
                    'open_ports': open_ports,
                    'web_info': web_info
                }
                camera_candidates.append(device_info)

                print(f"  🎥 疑似摄像头设备!")
                if web_info.get('title'):
                    print(f"     标题: {web_info['title']}")
                if 554 in open_ports:
                    print(f"     支持RTSP (端口554)")
                if 8554 in open_ports:
                    print(f"     支持RTSP (端口8554)")
            else:
                print(f"  ⚪ 普通网络设备")

    return camera_candidates

def main():
    """主函数"""
    print("🎥 摄像头快速扫描工具")
    print("=" * 50)

    # 扫描网络
    cameras = scan_network()

    # 显示结果
    print("\n" + "=" * 50)
    print("📋 扫描结果汇总")
    print("=" * 50)

    if cameras:
        print(f"🎉 发现 {len(cameras)} 个疑似摄像头设备:")

        for i, camera in enumerate(cameras, 1):
            print(f"\n📷 设备 {i}: {camera['ip']}")
            print(f"   开放端口: {camera['open_ports']}")

            if camera['web_info'].get('has_web'):
                print(f"   Web界面: http://{camera['ip']}")
                if camera['web_info'].get('title'):
                    print(f"   页面标题: {camera['web_info']['title']}")

            # 生成测试配置
            print(f"   测试配置:")
            if 554 in camera['open_ports']:
                print(f"     RTSP_URL = \"rtsp://admin:admin@{camera['ip']}:554/stream1\"")
            elif 8554 in camera['open_ports']:
                print(f"     RTSP_URL = \"rtsp://{camera['ip']}:8554/unicast\"")
            print(f"     PTZ_BASE_URL = \"http://{camera['ip']}\"")
    else:
        print("❌ 未发现摄像头设备")
        print("\n💡 可能的原因:")
        print("1. 摄像头未连接到网络")
        print("2. 摄像头在其他网段")
        print("3. 防火墙阻止了扫描")
        print("\n🔧 手动检查建议:")
        print("1. 检查摄像头网络指示灯")
        print("2. 查看路由器管理界面的设备列表")
        print("3. 使用摄像头厂商提供的配置工具")

if __name__ == "__main__":
    main()