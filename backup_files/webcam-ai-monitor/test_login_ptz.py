#!/usr/bin/env python3
"""
测试带登录的PTZ命令
"""

import socket
import json
import time
import hashlib

def test_login_methods():
    """测试各种登录方法"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin"

    print("🔐 测试登录认证方法")
    print("=" * 50)

    # 各种登录方法
    login_methods = [
        # 方法1: 直接登录
        {
            "Name": "Login",
            "Login": {
                "UserName": username,
                "Password": password
            }
        },

        # 方法2: 简单认证
        {
            "Name": "AuthLogin",
            "UserName": username,
            "Password": password
        },

        # 方法3: MD5密码
        {
            "Name": "Login",
            "UserName": username,
            "Password": hashlib.md5(password.encode()).hexdigest()
        },

        # 方法4: 详细登录
        {
            "Name": "Login",
            "Login": {
                "UserName": username,
                "Password": password,
                "Channel": 0
            }
        }
    ]

    session_id = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for i, login_cmd in enumerate(login_methods):
            print(f"\n🔍 测试登录方法 {i+1}: {login_cmd}")

            try:
                json_data = json.dumps(login_cmd).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"  ✅ 登录响应: {response_text}")

                    # 检查登录是否成功
                    if any(keyword in response_text.lower() for keyword in ['success', 'ok', 'sessionid', 'token']):
                        print("  🎉 登录可能成功!")

                        # 尝试提取session信息
                        try:
                            response_json = json.loads(response_text)
                            for key in ['SessionID', 'Token', 'session', 'token']:
                                if key in response_json:
                                    session_id = response_json[key]
                                    print(f"  🔑 获取到Session: {session_id}")
                                    break
                        except:
                            pass

                        return True, session_id

                except socket.timeout:
                    print("  ⏳ 登录无响应")

            except Exception as e:
                print(f"  ❌ 登录失败: {e}")

        sock.close()

    except Exception as e:
        print(f"❌ Socket创建失败: {e}")

    return False, None

def test_ptz_with_auth(session_id=None):
    """使用认证信息测试PTZ"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin"

    print(f"\n🎮 使用认证测试PTZ (Session: {session_id})")
    print("=" * 50)

    # 带认证的PTZ命令
    auth_ptz_commands = []

    if session_id:
        # 使用Session ID的命令
        auth_ptz_commands.extend([
            {
                "Name": "PTZ",
                "SessionID": session_id,
                "PTZ": {"Direction": "Left", "Speed": 30}
            },
            {
                "Name": "PTZControl",
                "SessionID": session_id,
                "Command": "Left",
                "Speed": 30
            }
        ])

    # 直接包含用户名密码的命令
    auth_ptz_commands.extend([
        {
            "Name": "PTZ",
            "UserName": username,
            "Password": password,
            "PTZ": {"Direction": "Left", "Speed": 30}
        },
        {
            "Name": "PTZControl",
            "Login": {
                "UserName": username,
                "Password": password
            },
            "PTZ": {"Direction": "Left", "Speed": 30}
        },
        {
            "Name": "ControlPTZ",
            "User": username,
            "Pass": password,
            "Direction": "Left",
            "Speed": 30
        },
        {
            "name": "ptz_control",
            "username": username,
            "password": password,
            "cmd": "move",
            "direction": "left",
            "speed": 30
        }
    ])

    working_commands = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for i, command in enumerate(auth_ptz_commands):
            print(f"\n🔍 测试认证PTZ命令 {i+1}:")
            print(f"  {command}")

            try:
                json_data = json.dumps(command).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"  ✅ 响应: {response_text}")

                    # 检查是否成功
                    if "No Login Info" not in response_text and "Invalid" not in response_text:
                        if any(keyword in response_text.lower() for keyword in ['success', 'ok', '"ret": 200', '"result": 0']):
                            print("  🎉 PTZ命令成功!")
                            working_commands.append({
                                "command": command,
                                "response": response_text
                            })

                            # 等待2秒测试摄像头是否移动
                            print("  📹 等待摄像头移动...")
                            time.sleep(3)

                            # 发送停止命令
                            stop_command = command.copy()
                            if "PTZ" in stop_command:
                                stop_command["PTZ"]["Direction"] = "Stop"
                            elif "Direction" in stop_command:
                                stop_command["Direction"] = "Stop"

                            print("  🛑 发送停止命令...")
                            stop_json = json.dumps(stop_command).encode('utf-8')
                            sock.sendto(stop_json, (camera_ip, port))

                        else:
                            print(f"  ⚠️ 响应状态不明: {response_text}")
                    else:
                        print(f"  ❌ 仍需认证或格式错误")

                except socket.timeout:
                    print("  ⏳ 无响应")

            except Exception as e:
                print(f"  ❌ 命令发送失败: {e}")

        sock.close()

    except Exception as e:
        print(f"❌ Socket创建失败: {e}")

    return working_commands

if __name__ == "__main__":
    print("🎯 JOVISION PTZ认证测试")
    print("🚀 目标：找到工作的认证PTZ协议")
    print("=" * 60)

    # 1. 尝试登录
    login_success, session_id = test_login_methods()

    # 2. 使用认证信息测试PTZ
    working_commands = test_ptz_with_auth(session_id)

    # 3. 总结结果
    print("\n" + "=" * 60)
    print("🎯 最终结果:")

    if working_commands:
        print(f"🎉 找到 {len(working_commands)} 个工作的PTZ命令!")
        for i, result in enumerate(working_commands):
            print(f"\n✅ 工作命令 {i+1}:")
            print(f"   命令: {result['command']}")
            print(f"   响应: {result['response']}")

        print(f"\n💡 现在可以集成到Web应用中!")
    else:
        print("❌ 暂未找到完全工作的PTZ命令")
        print("💡 建议继续尝试其他认证方法或查看厂商文档")