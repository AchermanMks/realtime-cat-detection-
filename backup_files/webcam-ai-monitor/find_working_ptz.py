#!/usr/bin/env python3
"""
寻找真正工作的PTZ协议
"""

import socket
import struct
import time
import requests
import json
from xml.etree import ElementTree as ET

def test_udp_ptz_protocols():
    """测试各种UDP PTZ协议"""
    camera_ip = "192.168.31.146"

    print("🔍 测试UDP PTZ协议...")

    # 常见UDP PTZ端口
    udp_ports = [554, 8000, 8080, 9000, 9999, 37777, 34567, 6036]

    for port in udp_ports:
        print(f"\n🔍 测试UDP端口 {port}...")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)

            # 不同的UDP命令格式
            commands = [
                # 简单文本命令
                b"PTZ_LEFT_START",
                b"ptz left 30",
                b"move left 30",

                # JSON格式
                json.dumps({"cmd": "ptz", "action": "left", "speed": 30}).encode(),

                # 可能的二进制协议
                struct.pack("!BBB", 0x81, 0x01, 0x04),  # VISCA协议左移
                struct.pack("!BBBBBBBB", 0xFF, 0x01, 0x00, 0x08, 0x81, 0x01, 0x06, 0x01),

                # JOVISION可能的格式
                b"\x00\x01\x02\x03LEFT\x00",
                b"JOVISION:PTZ:LEFT:30",
            ]

            for i, cmd in enumerate(commands):
                try:
                    sock.sendto(cmd, (camera_ip, port))

                    # 尝试接收响应
                    try:
                        response, addr = sock.recvfrom(1024)
                        print(f"  ✅ 命令 {i+1} 有响应: {response[:50]}")
                        return True  # 找到工作的协议
                    except socket.timeout:
                        print(f"  ⏳ 命令 {i+1} 无响应")
                except Exception as e:
                    print(f"  ❌ 命令 {i+1} 发送失败: {e}")

            sock.close()

        except Exception as e:
            print(f"  ❌ 端口 {port} 连接失败: {e}")

    return False

def test_onvif_profiles():
    """测试ONVIF不同的Profile"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("\n🔍 测试ONVIF Profiles...")

    # 获取可用的Profiles
    media_url = f"http://{camera_ip}/onvif/media_service"

    profiles_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
        <soap:Header/>
        <soap:Body>
            <trt:GetProfiles/>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
    }

    try:
        response = requests.post(media_url, data=profiles_request, headers=headers,
                               auth=(username, password), timeout=5)

        if response.status_code == 200:
            print("✅ 获取到Profiles")

            # 解析Profiles
            root = ET.fromstring(response.text)
            profiles = []

            for elem in root.iter():
                if 'token' in elem.attrib:
                    token = elem.attrib['token']
                    if token not in profiles:
                        profiles.append(token)
                        print(f"  发现Profile: {token}")

            # 测试每个Profile的PTZ
            for profile in profiles:
                if test_ptz_with_profile(profile, username, password, camera_ip):
                    return True

    except Exception as e:
        print(f"❌ 获取Profiles失败: {e}")

    return False

def test_ptz_with_profile(profile_token, username, password, camera_ip):
    """使用特定Profile测试PTZ"""

    print(f"\n🎮 测试Profile: {profile_token}")

    ptz_url = f"http://{camera_ip}/onvif/ptz_service"

    # PTZ相对移动命令
    move_request = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
        <soap:Header/>
        <soap:Body>
            <tptz:RelativeMove>
                <tptz:ProfileToken>{profile_token}</tptz:ProfileToken>
                <tptz:Translation>
                    <tt:PanTilt x="-0.1" y="0.0" xmlns:tt="http://www.onvif.org/ver10/schema"/>
                </tptz:Translation>
                <tptz:Speed>
                    <tt:PanTilt x="0.5" y="0.5" xmlns:tt="http://www.onvif.org/ver10/schema"/>
                </tptz:Speed>
            </tptz:RelativeMove>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
    }

    try:
        print("  发送相对移动命令...")
        response = requests.post(ptz_url, data=move_request, headers=headers,
                               auth=(username, password), timeout=5)

        print(f"  响应状态: {response.status_code}")
        print(f"  响应内容: {response.text[:200]}...")

        if response.status_code == 200:
            # 检查是否有SOAP错误
            if 'soap:fault' not in response.text.lower() and 'faultstring' not in response.text.lower():
                print("  ✅ 相对移动命令成功!")

                # 等待一下，然后发送停止命令
                time.sleep(2)

                stop_request = f"""<?xml version="1.0" encoding="UTF-8"?>
                <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                               xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
                    <soap:Header/>
                    <soap:Body>
                        <tptz:Stop>
                            <tptz:ProfileToken>{profile_token}</tptz:ProfileToken>
                            <tptz:PanTilt>true</tptz:PanTilt>
                        </tptz:Stop>
                    </soap:Body>
                </soap:Envelope>"""

                print("  发送停止命令...")
                requests.post(ptz_url, data=stop_request, headers=headers,
                            auth=(username, password), timeout=3)

                return True
            else:
                print("  ❌ 响应包含SOAP错误")

    except Exception as e:
        print(f"  ❌ PTZ测试异常: {e}")

    return False

def test_alternate_ports():
    """测试其他端口上的PTZ控制"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("\n🔍 测试其他端口的PTZ控制...")

    # 尝试不同端口
    test_ports = [8000, 8080, 9000]

    for port in test_ports:
        print(f"\n测试端口 {port}...")

        # 尝试HTTP PTZ命令
        test_urls = [
            f"http://{camera_ip}:{port}/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=5&arg2=5",
            f"http://{camera_ip}:{port}/api/ptz?move=left&speed=30",
            f"http://{camera_ip}:{port}/ptz?cmd=left&speed=30",
        ]

        for url in test_urls:
            try:
                response = requests.get(url, auth=(username, password), timeout=3)
                print(f"  端口{port} 响应: {response.status_code} - {response.text[:50]}...")

                if response.status_code == 200 and response.text.strip():
                    print(f"  ✅ 可能的工作端点: {url}")
                    return True

            except Exception as e:
                print(f"  ❌ {url} 失败: {str(e)[:50]}...")

    return False

def main():
    print("🎯 寻找真正工作的PTZ协议")
    print("=" * 50)
    print("📍 已确认: 摄像头可以物理转动")
    print("🎯 目标: 找到手机客户端使用的协议")
    print("=" * 50)

    # 1. 测试UDP协议
    if test_udp_ptz_protocols():
        print("\n🎉 找到UDP PTZ协议!")
        return

    # 2. 测试ONVIF不同Profiles
    if test_onvif_profiles():
        print("\n🎉 找到ONVIF PTZ协议!")
        return

    # 3. 测试其他端口
    if test_alternate_ports():
        print("\n🎉 找到其他端口的PTZ协议!")
        return

    print("\n❌ 暂未找到工作的PTZ协议")
    print("💡 建议:")
    print("1. 查看手机客户端的设置，了解使用的协议")
    print("2. 检查摄像头说明书")
    print("3. 尝试抓包分析手机客户端的通信")

if __name__ == "__main__":
    main()