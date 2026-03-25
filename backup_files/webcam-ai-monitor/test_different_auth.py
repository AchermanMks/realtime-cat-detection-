#!/usr/bin/env python3
"""
测试不同的认证组合
"""

import socket
import json
import requests
from xml.etree import ElementTree as ET

def test_different_credentials():
    """测试不同的用户名密码组合"""
    camera_ip = "192.168.31.146"
    port = 34567

    print("🔐 测试不同的认证凭据")
    print("=" * 50)

    # JOVISION常见的用户名/密码组合
    credentials = [
        ("admin", "admin"),
        ("admin", ""),
        ("admin", "123456"),
        ("admin", "888888"),
        ("admin", "password"),
        ("root", "root"),
        ("user", "user"),
        ("admin", "admin123"),
        ("", ""),  # 空用户名和密码
    ]

    for username, password in credentials:
        print(f"\n🔑 测试凭据: '{username}' / '{password}'")

        # 测试登录命令
        login_cmd = {
            "Name": "Login",
            "Login": {
                "UserName": username,
                "Password": password
            }
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)

            json_data = json.dumps(login_cmd).encode('utf-8')
            sock.sendto(json_data, (camera_ip, port))

            try:
                response, addr = sock.recvfrom(1024)
                response_text = response.decode('utf-8', errors='ignore')
                print(f"  响应: {response_text}")

                if "Invalid UserName or PassWord" not in response_text:
                    print(f"  ✅ 可能的有效凭据: {username}/{password}")

                    # 立即测试PTZ命令
                    ptz_cmd = {
                        "Name": "PTZ",
                        "UserName": username,
                        "Password": password,
                        "PTZ": {"Direction": "Left", "Speed": 30}
                    }

                    ptz_json = json.dumps(ptz_cmd).encode('utf-8')
                    sock.sendto(ptz_json, (camera_ip, port))

                    try:
                        ptz_response, _ = sock.recvfrom(1024)
                        ptz_text = ptz_response.decode('utf-8', errors='ignore')
                        print(f"  PTZ响应: {ptz_text}")

                        if "No Login Info" not in ptz_text and "Invalid" not in ptz_text:
                            print(f"  🎉 PTZ可能成功! 凭据: {username}/{password}")
                            return username, password

                    except socket.timeout:
                        print("  ⏳ PTZ命令无响应")

            except socket.timeout:
                print("  ⏳ 登录命令无响应")

            sock.close()

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")

    return None, None

def verify_onvif_ptz_support():
    """验证ONVIF PTZ支持"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("\n🔍 验证ONVIF PTZ支持")
    print("=" * 50)

    # 获取PTZ配置
    ptz_url = f"http://{camera_ip}/onvif/ptz_service"

    # 获取PTZ配置信息
    config_request = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
        <soap:Header/>
        <soap:Body>
            <tptz:GetConfigurations/>
        </soap:Body>
    </soap:Envelope>"""

    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
    }

    try:
        response = requests.post(ptz_url, data=config_request, headers=headers,
                               auth=(username, password), timeout=5)

        print(f"PTZ配置查询状态: {response.status_code}")

        if response.status_code == 200:
            print("✅ ONVIF PTZ服务响应正常")

            # 检查是否有PTZ配置
            if 'PTZConfiguration' in response.text:
                print("✅ 发现PTZ配置!")
                print(f"配置详情: {response.text[:300]}...")
                return True
            else:
                print("❌ 没有找到PTZ配置")
                print(f"响应内容: {response.text[:200]}...")
                return False
        else:
            print(f"❌ PTZ服务查询失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ ONVIF PTZ验证异常: {e}")
        return False

def test_no_auth_commands():
    """测试不需要认证的命令"""
    camera_ip = "192.168.31.146"
    port = 34567

    print("\n🔍 测试无认证命令")
    print("=" * 50)

    # 可能不需要认证的命令
    no_auth_commands = [
        {"Name": "PTZ", "PTZ": {"Direction": "Left", "Speed": 30}},
        {"cmd": "ptz", "direction": "left", "speed": 30},
        {"Name": "GetPTZStatus"},
        {"Name": "PTZInfo"},
        {"Name": "GetDeviceInfo"},
    ]

    for i, command in enumerate(no_auth_commands):
        print(f"\n🔍 测试命令 {i+1}: {command}")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)

            json_data = json.dumps(command).encode('utf-8')
            sock.sendto(json_data, (camera_ip, port))

            try:
                response, addr = sock.recvfrom(1024)
                response_text = response.decode('utf-8', errors='ignore')
                print(f"  响应: {response_text}")

                if "Login" not in response_text and "Invalid" not in response_text:
                    print("  ✅ 命令被接受!")

            except socket.timeout:
                print("  ⏳ 无响应")

            sock.close()

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")

def check_web_interface():
    """检查Web界面是否有PTZ控制"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("\n🌐 检查Web界面PTZ功能")
    print("=" * 50)

    try:
        # 尝试访问可能的PTZ控制页面
        test_urls = [
            f"https://{camera_ip}/web/ptz.html",
            f"https://{camera_ip}/ptz.html",
            f"https://{camera_ip}/control.html",
            f"https://{camera_ip}/admin/ptz.html",
        ]

        for url in test_urls:
            try:
                response = requests.get(url, auth=(username, password), timeout=3, verify=False)
                print(f"测试URL: {url}")
                print(f"状态: {response.status_code}")

                if response.status_code == 200:
                    if 'ptz' in response.text.lower() or 'control' in response.text.lower():
                        print("✅ 可能找到PTZ控制界面!")
                        print(f"内容预览: {response.text[:200]}...")

            except Exception as e:
                print(f"URL {url} 测试失败: {str(e)[:50]}...")

    except Exception as e:
        print(f"Web界面检查失败: {e}")

if __name__ == "__main__":
    print("🎯 JOVISION PTZ深度认证分析")
    print("🔍 多方向验证PTZ功能和认证")
    print("=" * 60)

    # 1. 测试不同凭据
    working_user, working_pass = test_different_credentials()

    if working_user:
        print(f"\n🎉 找到工作凭据: {working_user}/{working_pass}")
    else:
        print("\n❌ 没有找到工作的认证凭据")

    # 2. 验证ONVIF PTZ支持
    onvif_ptz = verify_onvif_ptz_support()

    # 3. 测试无认证命令
    test_no_auth_commands()

    # 4. 检查Web界面
    check_web_interface()

    # 5. 最终结论
    print("\n" + "=" * 60)
    print("🎯 分析结论:")

    if onvif_ptz:
        print("✅ ONVIF报告支持PTZ")
    else:
        print("❌ ONVIF未发现PTZ配置")

    if working_user:
        print(f"✅ UDP认证成功: {working_user}/{working_pass}")
    else:
        print("❌ UDP认证失败")

    print("\n💡 建议:")
    if not onvif_ptz and not working_user:
        print("1. 摄像头可能需要特殊激活PTZ功能")
        print("2. 可能使用完全不同的协议")
        print("3. 检查摄像头物理连接（RS485/RS232）")
        print("4. 查看厂商特定的控制软件")