#!/usr/bin/env python3
"""
使用新凭据admin/admin123测试PTZ控制
"""

import socket
import json
import time

def test_ptz_with_new_credentials():
    """使用新凭据测试PTZ"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin123"  # 新凭据

    print("🎯 使用新凭据测试PTZ控制")
    print(f"📡 摄像头: {camera_ip}:{port}")
    print(f"👤 用户名: {username}")
    print(f"🔑 密码: {password}")
    print("=" * 50)

    # 各种PTZ命令格式
    ptz_commands = [
        # 基础格式
        {
            "Name": "PTZ",
            "UserName": username,
            "Password": password,
            "PTZ": {"Direction": "Left", "Speed": 30}
        },

        # 登录格式
        {
            "Name": "PTZControl",
            "Login": {
                "UserName": username,
                "Password": password
            },
            "PTZ": {"Direction": "Left", "Speed": 30}
        },

        # 直接字段格式
        {
            "Name": "ControlPTZ",
            "User": username,
            "Pass": password,
            "Direction": "Left",
            "Speed": 30
        },

        # 可能的session格式
        {
            "Name": "PTZ",
            "SessionID": username + ":" + password,
            "PTZ": {"Direction": "Left", "Speed": 30}
        },

        # 简化格式
        {
            "name": "ptz_control",
            "username": username,
            "password": password,
            "cmd": "move",
            "direction": "left",
            "speed": 30
        }
    ]

    working_commands = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for i, command in enumerate(ptz_commands):
            print(f"\n🔍 测试命令 {i+1}:")
            print(f"  {json.dumps(command, indent=2)}")

            try:
                json_data = json.dumps(command).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"  ✅ 响应: {response_text}")

                    # 检查是否成功
                    response_lower = response_text.lower()
                    if "no login info" not in response_lower and "invalid username" not in response_lower:
                        if any(success_keyword in response_lower for success_keyword in ['success', 'ok', '"ret": 200', '"result": 0']):
                            print("  🎉 PTZ命令可能成功!")
                            working_commands.append({
                                "command": command,
                                "response": response_text
                            })

                            print("  📹 等待摄像头移动 (5秒)...")
                            time.sleep(5)

                            # 发送停止命令
                            stop_command = command.copy()
                            if "PTZ" in stop_command:
                                stop_command["PTZ"]["Direction"] = "Stop"
                            elif "Direction" in stop_command:
                                stop_command["Direction"] = "Stop"
                            elif "cmd" in stop_command:
                                stop_command["cmd"] = "stop"

                            print("  🛑 发送停止命令...")
                            stop_json = json.dumps(stop_command).encode('utf-8')
                            sock.sendto(stop_json, (camera_ip, port))

                        else:
                            print(f"  ⚠️ 响应未确认成功: {response_text}")
                    else:
                        print(f"  ❌ 认证或格式问题: {response_text}")

                except socket.timeout:
                    print("  ⏳ 无响应")

            except Exception as e:
                print(f"  ❌ 命令发送失败: {e}")

        sock.close()

    except Exception as e:
        print(f"❌ Socket创建失败: {e}")

    return working_commands

def test_simple_login_first():
    """先尝试简单登录"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin123"

    print("\n🔐 先尝试登录...")

    login_commands = [
        {
            "Name": "Login",
            "UserName": username,
            "Password": password
        },
        {
            "Name": "Login",
            "Login": {
                "UserName": username,
                "Password": password
            }
        }
    ]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for login_cmd in login_commands:
            print(f"🔑 尝试登录: {login_cmd}")

            json_data = json.dumps(login_cmd).encode('utf-8')
            sock.sendto(json_data, (camera_ip, port))

            try:
                response, addr = sock.recvfrom(1024)
                response_text = response.decode('utf-8', errors='ignore')
                print(f"   登录响应: {response_text}")

                if "invalid username" not in response_text.lower():
                    print("   ✅ 登录可能成功!")
                    return True

            except socket.timeout:
                print("   ⏳ 登录无响应")

        sock.close()

    except Exception as e:
        print(f"❌ 登录测试失败: {e}")

    return False

if __name__ == "__main__":
    print("🎯 JOVISION PTZ新凭据测试")
    print("🔑 凭据: admin / admin123")
    print("=" * 60)

    # 1. 先测试登录
    login_success = test_simple_login_first()

    # 2. 测试PTZ控制
    working_commands = test_ptz_with_new_credentials()

    # 3. 总结结果
    print("\n" + "=" * 60)
    print("🎯 测试结果:")

    if working_commands:
        print(f"🎉 找到 {len(working_commands)} 个可能工作的PTZ命令!")

        for i, result in enumerate(working_commands):
            print(f"\n✅ 工作命令 {i+1}:")
            print(f"   响应: {result['response']}")

        print("\n💡 如果摄像头实际移动了，我们就找到了正确的协议!")
        print("🔧 现在可以集成到Web应用中实现真正的PTZ控制!")
    else:
        print("❌ 仍未找到工作的PTZ命令")

        if login_success:
            print("✅ 但登录凭据可能正确")

        print("💡 下一步建议:")
        print("   1. 检查Web界面是否有PTZ启用选项")
        print("   2. 确认PTZ功能已激活")
        print("   3. 查看是否需要特殊的PTZ用户权限")