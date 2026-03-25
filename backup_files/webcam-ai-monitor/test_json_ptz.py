#!/usr/bin/env python3
"""
测试JSON格式的PTZ命令
"""

import socket
import json
import time

def test_json_ptz_commands():
    """测试不同的JSON PTZ命令格式"""
    camera_ip = "192.168.31.146"
    port = 34567  # 发现的工作端口

    print("🎯 测试JSON PTZ命令")
    print(f"📡 目标: {camera_ip}:{port}")
    print("=" * 50)

    # 各种可能的JSON命令格式
    ptz_commands = [
        # 基础PTZ命令
        {"Name": "PTZ", "PTZ": {"Direction": "Left", "Speed": 30}},
        {"Name": "PTZCtrl", "Action": "Start", "Direction": "Left", "Speed": 30},
        {"cmd": "ptz", "action": "move", "direction": "left", "speed": 30},

        # JOVISION可能的格式
        {"Name": "ControlPTZ", "ControlPTZ": {"Action": "Left", "Parameter": 30}},
        {"Name": "PTZControl", "PTZControl": {"Command": "Left", "Speed": 30}},
        {"Name": "DeviceControl", "DeviceControl": {"Type": "PTZ", "Action": "Left", "Speed": 30}},

        # 更详细的格式
        {"Name": "PTZ", "PTZ": {"Action": "DirectionMove", "Direction": "Left", "Speed": 30, "Step": 1}},
        {"Name": "PTZOperate", "PTZOperate": {"Channel": 0, "Command": "Left", "Parameter1": 30, "Parameter2": 0}},

        # 可能的停止命令
        {"Name": "PTZ", "PTZ": {"Direction": "Stop"}},
        {"Name": "PTZCtrl", "Action": "Stop"},

        # 其他方向测试
        {"Name": "PTZ", "PTZ": {"Direction": "Right", "Speed": 30}},
        {"Name": "PTZ", "PTZ": {"Direction": "Up", "Speed": 30}},
        {"Name": "PTZ", "PTZ": {"Direction": "Down", "Speed": 30}},

        # 缩放命令
        {"Name": "PTZ", "PTZ": {"Direction": "ZoomIn", "Speed": 30}},
        {"Name": "PTZ", "PTZ": {"Direction": "ZoomOut", "Speed": 30}},
    ]

    working_commands = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for i, command in enumerate(ptz_commands):
            print(f"\n🔍 测试命令 {i+1}: {command}")

            try:
                # 发送JSON命令
                json_data = json.dumps(command).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                # 等待响应
                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"  ✅ 响应: {response_text}")

                    # 分析响应
                    if "Invalid" not in response_text and "Error" not in response_text:
                        print("  🎉 可能的成功命令!")
                        working_commands.append({
                            "command": command,
                            "response": response_text
                        })

                        # 如果是移动命令，等待2秒后发送停止命令
                        if any(direction in json.dumps(command).lower() for direction in ["left", "right", "up", "down", "zoom"]):
                            print("  ⏸️ 发送停止命令...")
                            time.sleep(2)

                            stop_command = {"Name": "PTZ", "PTZ": {"Direction": "Stop"}}
                            stop_json = json.dumps(stop_command).encode('utf-8')
                            sock.sendto(stop_json, (camera_ip, port))

                            try:
                                stop_response, _ = sock.recvfrom(1024)
                                print(f"  🛑 停止响应: {stop_response.decode('utf-8', errors='ignore')}")
                            except socket.timeout:
                                print("  ⏳ 停止命令无响应")

                    else:
                        print(f"  ❌ 错误响应: {response_text}")

                except socket.timeout:
                    print("  ⏳ 无响应")

            except Exception as e:
                print(f"  ❌ 发送失败: {e}")

        sock.close()

    except Exception as e:
        print(f"❌ Socket创建失败: {e}")

    # 输出结果
    print("\n" + "=" * 50)
    print("🎯 测试结果:")

    if working_commands:
        print(f"✅ 找到 {len(working_commands)} 个可能工作的命令:")
        for i, result in enumerate(working_commands):
            print(f"\n{i+1}. 命令: {result['command']}")
            print(f"   响应: {result['response']}")

        return working_commands
    else:
        print("❌ 没有找到成功的PTZ命令")
        print("💡 可能需要:")
        print("   1. 不同的JSON字段名")
        print("   2. 认证信息")
        print("   3. 特殊的会话管理")
        return None

def test_authenticated_commands():
    """测试带认证的命令"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin"

    print("\n🔐 测试带认证的PTZ命令")
    print("=" * 50)

    # 带认证信息的命令
    auth_commands = [
        {
            "Name": "PTZ",
            "SessionID": "test",
            "Username": username,
            "Password": password,
            "PTZ": {"Direction": "Left", "Speed": 30}
        },
        {
            "Name": "PTZControl",
            "User": username,
            "Pass": password,
            "Command": "Left",
            "Speed": 30
        },
        {
            "cmd": "login_ptz",
            "username": username,
            "password": password,
            "ptz_action": "left",
            "speed": 30
        }
    ]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for i, command in enumerate(auth_commands):
            print(f"\n🔍 测试认证命令 {i+1}: {command}")

            try:
                json_data = json.dumps(command).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"  ✅ 响应: {response_text}")

                    if "success" in response_text.lower() or "ok" in response_text.lower():
                        print("  🎉 认证命令可能成功!")
                        return command

                except socket.timeout:
                    print("  ⏳ 无响应")

            except Exception as e:
                print(f"  ❌ 发送失败: {e}")

        sock.close()

    except Exception as e:
        print(f"❌ Socket创建失败: {e}")

    return None

if __name__ == "__main__":
    # 测试基础命令
    working = test_json_ptz_commands()

    # 如果基础命令不工作，尝试认证命令
    if not working:
        test_authenticated_commands()