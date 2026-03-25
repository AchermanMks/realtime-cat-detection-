#!/usr/bin/env python3
"""
摄像头协议分析工具
"""

import socket
import requests
import json
from xml.etree import ElementTree as ET

def scan_camera_ports():
    """扫描摄像头开放的端口"""
    camera_ip = "192.168.31.146"

    print("🔍 扫描摄像头开放端口...")

    # 常见的摄像头端口
    common_ports = [
        21,    # FTP
        23,    # Telnet
        80,    # HTTP
        443,   # HTTPS
        554,   # RTSP
        8000,  # 管理端口
        8080,  # 备用HTTP
        8554,  # 备用RTSP
        9000,  # 某些摄像头管理端口
        9999,  # 某些摄像头控制端口
        37777, # 大华常用端口
        34567, # 海康威视端口
        6036,  # JOVISION可能的端口
    ]

    open_ports = []

    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((camera_ip, port))
            if result == 0:
                print(f"✅ 端口 {port} 开放")
                open_ports.append(port)
            sock.close()
        except:
            pass

    print(f"发现开放端口: {open_ports}")
    return open_ports

def test_onvif_ptz_direct():
    """直接测试ONVIF PTZ命令"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("\n🔍 测试ONVIF PTZ直接命令...")

    # 先获取PTZ服务地址
    device_url = f"http://{camera_ip}/onvif/device_service"

    # 获取Capabilities
    soap_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
        <soap:Header/>
        <soap:Body>
            <tds:GetCapabilities>
                <tds:Category>PTZ</tds:Category>
            </tds:GetCapabilities>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'Content-Length': str(len(soap_request))
    }

    try:
        response = requests.post(device_url, data=soap_request, headers=headers,
                               auth=(username, password), timeout=5)

        if response.status_code == 200:
            print("✅ ONVIF设备响应正常")

            # 查找PTZ服务URL
            root = ET.fromstring(response.text)
            ptz_url = None
            for elem in root.iter():
                if 'XAddr' in elem.tag and elem.text and 'ptz' in elem.text.lower():
                    ptz_url = elem.text
                    break

            if not ptz_url:
                # 尝试默认PTZ地址
                ptz_url = f"http://{camera_ip}/onvif/ptz_service"

            print(f"PTZ服务地址: {ptz_url}")

            # 测试PTZ移动命令
            return test_ptz_movement(ptz_url, username, password)
    except Exception as e:
        print(f"❌ ONVIF测试失败: {e}")
        return False

def test_ptz_movement(ptz_url, username, password):
    """测试PTZ移动命令"""

    print(f"🎮 测试PTZ移动: {ptz_url}")

    # PTZ移动命令
    move_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
        <soap:Header/>
        <soap:Body>
            <tptz:ContinuousMove>
                <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                <tptz:Velocity>
                    <tt:PanTilt x="-0.3" y="0.0" xmlns:tt="http://www.onvif.org/ver10/schema"/>
                </tptz:Velocity>
                <tptz:Timeout>PT2S</tptz:Timeout>
            </tptz:ContinuousMove>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
    }

    try:
        response = requests.post(ptz_url, data=move_request, headers=headers,
                               auth=(username, password), timeout=5)

        print(f"PTZ命令状态: {response.status_code}")
        print(f"响应内容: {response.text[:200]}...")

        if response.status_code == 200:
            print("✅ PTZ命令发送成功！")

            # 检查是否有错误信息
            if 'fault' in response.text.lower() or 'error' in response.text.lower():
                print("⚠️ 响应中包含错误信息")
                return False
            else:
                print("🎉 PTZ命令可能成功执行！")
                return True
        else:
            print("❌ PTZ命令失败")
            return False

    except Exception as e:
        print(f"❌ PTZ移动测试异常: {e}")
        return False

def check_camera_type():
    """检查摄像头类型和能力"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("\n🔍 检查摄像头类型和能力...")

    # 获取设备信息
    device_url = f"http://{camera_ip}/onvif/device_service"

    info_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
        <soap:Header/>
        <soap:Body>
            <tds:GetDeviceInformation/>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
    }

    try:
        response = requests.post(device_url, data=info_request, headers=headers,
                               auth=(username, password), timeout=5)

        if response.status_code == 200:
            root = ET.fromstring(response.text)

            device_info = {}
            for elem in root.iter():
                if elem.text and elem.tag.split('}')[-1] in ['Manufacturer', 'Model', 'FirmwareVersion', 'SerialNumber']:
                    key = elem.tag.split('}')[-1]
                    device_info[key] = elem.text

            print("📱 设备信息:")
            for key, value in device_info.items():
                print(f"   {key}: {value}")

            # 检查是否为PTZ设备
            model = device_info.get('Model', '').lower()
            if 'ptz' in model or 'dome' in model or 'speed' in model:
                print("✅ 设备型号显示支持PTZ功能")
                return True
            else:
                print("⚠️ 设备型号未明确显示PTZ支持")
                print("💡 可能是固定式摄像头或PTZ功能被禁用")
                return False

    except Exception as e:
        print(f"❌ 设备信息查询失败: {e}")
        return False

if __name__ == "__main__":
    print("🔍 摄像头协议深度分析")
    print("=" * 50)

    # 1. 扫描端口
    ports = scan_camera_ports()

    # 2. 检查设备类型
    supports_ptz = check_camera_type()

    # 3. 测试ONVIF PTZ
    if supports_ptz:
        onvif_success = test_onvif_ptz_direct()

        if onvif_success:
            print("\n🎉 找到工作的PTZ控制方法！")
        else:
            print("\n❌ ONVIF PTZ控制失败")
            print("💡 可能需要:")
            print("   1. 启用PTZ功能")
            print("   2. 配置PTZ协议")
            print("   3. 检查用户权限")
    else:
        print("\n⚠️ 摄像头可能不支持PTZ功能")
        print("💡 如果手机可以控制，可能使用私有协议")