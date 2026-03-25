#!/usr/bin/env python3
"""
JOVISION摄像头Web管理界面密码获取工具
"""

import requests
import time
from urllib.parse import quote
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def test_default_passwords():
    """测试JOVISION常见的默认密码"""
    camera_ip = "192.168.31.146"

    print("🔐 测试JOVISION常见默认密码")
    print("=" * 50)

    # JOVISION常见默认凭据组合
    credentials = [
        ("admin", "admin"),
        ("admin", ""),
        ("admin", "123456"),
        ("admin", "888888"),
        ("admin", "password"),
        ("admin", "admin123"),
        ("admin", "jovision"),
        ("admin", "12345"),
        ("root", "root"),
        ("root", "admin"),
        ("user", "user"),
        ("guest", "guest"),
        ("admin", "000000"),
        ("admin", "666666"),
        ("jovision", "jovision"),
        ("jovision", "admin"),
    ]

    # 测试HTTP和HTTPS
    protocols = ["http", "https"]

    for protocol in protocols:
        print(f"\n🌐 测试 {protocol.upper()} 协议...")

        for username, password in credentials:
            try:
                url = f"{protocol}://{camera_ip}"

                print(f"🔑 测试: {username} / {'(空)' if not password else password}")

                response = requests.get(
                    url,
                    auth=(username, password),
                    timeout=5,
                    verify=False
                )

                print(f"   状态码: {response.status_code}")

                if response.status_code == 200:
                    print(f"   ✅ 成功! 用户名: {username}, 密码: {password}")
                    print(f"   🌐 Web界面: {url}")

                    # 检查是否真的成功登录（不是重定向到登录页）
                    if "login" not in response.text.lower() or "password" not in response.text.lower():
                        print(f"   🎉 确认成功登录Web管理界面!")
                        return username, password, url
                    else:
                        print(f"   ⚠️ 被重定向到登录页，尝试下一个...")

                elif response.status_code == 401:
                    print(f"   ❌ 认证失败")
                elif response.status_code == 404:
                    print(f"   ❌ 页面不存在")
                else:
                    print(f"   ⚠️ 状态码: {response.status_code}")

            except requests.exceptions.ConnectTimeout:
                print(f"   ❌ 连接超时")
            except requests.exceptions.SSLError:
                print(f"   ❌ SSL证书错误 (跳过)")
            except requests.exceptions.ConnectionError as e:
                if "refused" in str(e):
                    print(f"   ❌ 连接被拒绝")
                else:
                    print(f"   ❌ 连接错误: {str(e)[:50]}...")
            except Exception as e:
                print(f"   ❌ 异常: {str(e)[:50]}...")

    return None, None, None

def try_password_recovery():
    """尝试密码恢复方法"""
    camera_ip = "192.168.31.146"

    print("\n🔧 尝试密码恢复方法")
    print("=" * 50)

    # 常见的密码重置端点
    reset_endpoints = [
        "/reset.cgi",
        "/factory_reset.cgi",
        "/admin/reset.cgi",
        "/cgi-bin/reset.cgi",
        "/web/reset.cgi",
        "/recovery.html",
        "/forgot_password.html",
    ]

    for protocol in ["http", "https"]:
        for endpoint in reset_endpoints:
            try:
                url = f"{protocol}://{camera_ip}{endpoint}"
                print(f"🔍 测试重置端点: {url}")

                response = requests.get(url, timeout=3, verify=False)

                if response.status_code == 200:
                    print(f"   ✅ 发现重置页面: {url}")
                    print(f"   📝 页面内容预览: {response.text[:200]}...")

                    if any(keyword in response.text.lower() for keyword in ['reset', 'recovery', 'forgot']):
                        print(f"   🎯 可能的密码重置页面!")

            except Exception as e:
                continue

    print("\n💡 JOVISION摄像头密码重置方法:")
    print("1. 📹 物理重置按钮:")
    print("   - 找到摄像头的RESET按钮")
    print("   - 通电状态下按住RESET键10-30秒")
    print("   - 等待摄像头重启，密码将恢复默认")

    print("\n2. 🔧 WEB重置方法:")
    print("   - 尝试访问: http://192.168.31.146/reset.html")
    print("   - 或 https://192.168.31.146/factory_reset.cgi")

    print("\n3. 📞 厂商支持:")
    print("   - JOVISION官方技术支持")
    print("   - 提供摄像头序列号获取重置码")

def get_device_info():
    """获取设备信息以确定确切型号"""
    camera_ip = "192.168.31.146"

    print("\n📱 获取设备详细信息")
    print("=" * 50)

    # ONVIF设备信息（我们知道这个可以访问）
    device_url = f"http://{camera_ip}/onvif/device_service"

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
    }

    try:
        # 尝试无认证访问
        response = requests.post(device_url, data=soap_request, headers=headers, timeout=5)

        if response.status_code == 200:
            print("✅ 获取设备信息成功")

            # 解析设备信息
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)

            device_info = {}
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1]
                if tag_name in ['Manufacturer', 'Model', 'FirmwareVersion', 'SerialNumber', 'HardwareId']:
                    device_info[tag_name] = elem.text

            print("📋 设备详细信息:")
            for key, value in device_info.items():
                print(f"   {key}: {value}")

            # 根据型号提供特定建议
            model = device_info.get('Model', '').upper()
            firmware = device_info.get('FirmwareVersion', '')

            print(f"\n💡 针对 {model} 的密码建议:")

            if 'IPC' in model:
                print("   - 这是IP摄像头型号")
                print("   - 尝试序列号后4位作为密码")
                print("   - 尝试出厂日期相关密码")

                serial = device_info.get('SerialNumber', '')
                if serial:
                    print(f"   - 序列号: {serial}")
                    print(f"   - 尝试密码: {serial[-4:]} (后4位)")
                    print(f"   - 尝试密码: {serial[-6:]} (后6位)")

            return device_info

    except Exception as e:
        print(f"❌ 设备信息获取失败: {e}")

    return None

def check_specific_jovision_urls():
    """检查JOVISION特定的管理URL"""
    camera_ip = "192.168.31.146"

    print("\n🎯 检查JOVISION特定管理页面")
    print("=" * 50)

    # JOVISION常见管理页面
    jovision_urls = [
        "http://192.168.31.146:8080",
        "http://192.168.31.146:80/web/",
        "http://192.168.31.146/webui/",
        "http://192.168.31.146/admin/",
        "http://192.168.31.146/management/",
        "https://192.168.31.146:443/",
        "http://192.168.31.146/index.html",
        "http://192.168.31.146/login.html",
    ]

    for url in jovision_urls:
        try:
            print(f"🔍 检查: {url}")
            response = requests.get(url, timeout=3, verify=False)

            if response.status_code == 200:
                print(f"   ✅ 页面存在!")

                # 检查是否是登录页面
                content_lower = response.text.lower()
                if any(keyword in content_lower for keyword in ['login', 'username', 'password', '用户名', '密码']):
                    print(f"   🎯 发现登录页面: {url}")
                    print(f"   📝 页面内容包含登录表单")

                    # 检查是否有默认密码提示
                    if any(hint in content_lower for keyword in ['admin', 'default', '默认']):
                        print(f"   💡 页面可能包含密码提示")

            elif response.status_code == 401:
                print(f"   🔐 需要认证: {url}")

        except Exception as e:
            continue

def main():
    print("🎯 JOVISION摄像头Web密码获取工具")
    print("📷 摄像头: 192.168.31.146")
    print("🏷️ 型号: JOVISION-IPC V2.2.6501")
    print("=" * 60)

    # 1. 获取设备详细信息
    device_info = get_device_info()

    # 2. 测试默认密码
    username, password, web_url = test_default_passwords()

    if username and password:
        print(f"\n🎉 成功找到Web管理界面密码!")
        print(f"🌐 URL: {web_url}")
        print(f"👤 用户名: {username}")
        print(f"🔑 密码: {password}")
        print(f"\n✨ 现在可以登录Web管理界面配置PTZ设置!")
    else:
        # 3. 检查特定URL
        check_specific_jovision_urls()

        # 4. 提供重置方法
        try_password_recovery()

        print(f"\n❌ 未找到有效的Web管理密码")
        print(f"\n📋 建议步骤:")
        print(f"1. 🔧 尝试硬件重置按钮")
        print(f"2. 📞 联系JOVISION技术支持")
        print(f"3. 🔍 查看摄像头标签上的默认密码")
        print(f"4. 📖 查看产品说明书")

        if device_info and device_info.get('SerialNumber'):
            print(f"5. 🔢 尝试序列号相关密码: {device_info['SerialNumber'][-4:]}")

if __name__ == "__main__":
    main()