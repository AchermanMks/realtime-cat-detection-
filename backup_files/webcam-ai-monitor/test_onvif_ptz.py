#!/usr/bin/env python3
"""
ONVIF PTZ控制测试
"""

import requests
import time
from xml.etree import ElementTree as ET
import base64

def test_onvif_ptz():
    """测试ONVIF PTZ控制"""

    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print(f"🎯 ONVIF PTZ球机控制测试")
    print(f"📡 摄像头IP: {camera_ip}")
    print("=" * 50)

    # ONVIF设备信息查询
    device_service_url = f"http://{camera_ip}/onvif/device_service"

    # 创建SOAP请求获取设备信息
    soap_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
        <soap:Header/>
        <soap:Body>
            <tds:GetDeviceInformation/>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'Content-Length': str(len(soap_request))
    }

    print("🔍 查询设备信息...")
    try:
        response = requests.post(
            device_service_url,
            data=soap_request,
            headers=headers,
            auth=(username, password),
            timeout=5
        )

        print(f"响应状态: {response.status_code}")

        if response.status_code == 200:
            print("✅ ONVIF设备信息获取成功!")

            # 解析设备信息
            try:
                root = ET.fromstring(response.text)
                # 查找制造商和型号
                for elem in root.iter():
                    if 'Manufacturer' in elem.tag:
                        print(f"📱 制造商: {elem.text}")
                    elif 'Model' in elem.tag:
                        print(f"🏷️ 型号: {elem.text}")
                    elif 'FirmwareVersion' in elem.tag:
                        print(f"🔧 固件版本: {elem.text}")
            except:
                print("📋 设备信息解析中...")

        elif response.status_code == 401:
            print("❌ 认证失败 - 需要正确的用户名/密码")
            return False
        else:
            print(f"❌ 设备查询失败: {response.status_code}")

    except Exception as e:
        print(f"❌ ONVIF查询异常: {e}")

    # 获取PTZ服务端点
    print("\n🔍 查询PTZ服务...")

    capabilities_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
        <soap:Header/>
        <soap:Body>
            <tds:GetCapabilities>
                <tds:Category>PTZ</tds:Category>
            </tds:GetCapabilities>
        </soap:Body>
    </soap:Envelope>"""

    try:
        response = requests.post(
            device_service_url,
            data=capabilities_request,
            headers=headers,
            auth=(username, password),
            timeout=5
        )

        if response.status_code == 200:
            print("✅ PTZ服务查询成功!")

            # 查找PTZ服务URL
            ptz_service_url = None
            try:
                root = ET.fromstring(response.text)
                for elem in root.iter():
                    if 'XAddr' in elem.tag and 'ptz' in elem.text.lower():
                        ptz_service_url = elem.text
                        print(f"🎮 PTZ服务地址: {ptz_service_url}")
                        break
            except:
                # 尝试常见的PTZ服务地址
                ptz_service_url = f"http://{camera_ip}/onvif/ptz_service"
                print(f"🎮 使用默认PTZ服务地址: {ptz_service_url}")

            if ptz_service_url:
                return test_ptz_movement(ptz_service_url, username, password)

    except Exception as e:
        print(f"❌ PTZ服务查询异常: {e}")

    return False

def test_ptz_movement(ptz_url, username, password):
    """测试PTZ移动"""

    print(f"\n🎮 开始PTZ移动测试...")

    # PTZ连续移动命令
    move_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
        <soap:Header/>
        <soap:Body>
            <tptz:ContinuousMove>
                <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                <tptz:Velocity>
                    <tt:PanTilt x="-0.5" y="0.0" xmlns:tt="http://www.onvif.org/ver10/schema"/>
                </tptz:Velocity>
                <tptz:Timeout>PT3S</tptz:Timeout>
            </tptz:ContinuousMove>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'Content-Length': str(len(move_request))
    }

    try:
        print("📹 发送PTZ向左移动命令...")
        response = requests.post(
            ptz_url,
            data=move_request,
            headers=headers,
            auth=(username, password),
            timeout=10
        )

        print(f"响应状态: {response.status_code}")

        if response.status_code == 200:
            print("✅ PTZ移动命令发送成功!")
            print("📹 摄像头应该向左转动3秒...")
            print("🎉 如果看到画面移动，说明PTZ控制成功!")

            # 等待3秒
            time.sleep(3)

            # 发送停止命令
            stop_request = """<?xml version="1.0" encoding="UTF-8"?>
            <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                           xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
                <soap:Header/>
                <soap:Body>
                    <tptz:Stop>
                        <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                        <tptz:PanTilt>true</tptz:PanTilt>
                    </tptz:Stop>
                </soap:Body>
            </soap:Envelope>"""

            print("⏹️ 发送停止命令...")
            requests.post(ptz_url, data=stop_request, headers=headers, auth=(username, password), timeout=5)
            print("✅ PTZ测试完成!")

            return True

        elif response.status_code == 401:
            print("❌ 认证失败")
        else:
            print(f"❌ PTZ命令失败: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")

    except Exception as e:
        print(f"❌ PTZ移动测试异常: {e}")

    return False

if __name__ == "__main__":
    success = test_onvif_ptz()

    print("\n" + "=" * 50)
    if success:
        print("🎉 ONVIF PTZ测试成功!")
        print("💡 如果看到画面移动，PTZ控制完全正常")
        print("💡 现在可以启动真实PTZ控制版本了")
    else:
        print("❌ ONVIF PTZ测试失败")
        print("💡 可能需要正确的用户名/密码")
        print("💡 或者PTZ功能被禁用")