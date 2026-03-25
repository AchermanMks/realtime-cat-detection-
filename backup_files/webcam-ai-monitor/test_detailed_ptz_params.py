#!/usr/bin/env python3
"""
详细测试PTZ参数组合
"""

import socket
import json
import time

def test_detailed_ptz_parameters():
    """详细测试各种PTZ参数组合"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin123"

    print("🎯 详细PTZ参数测试")
    print("🔑 已确认认证成功，现在寻找正确的移动参数")
    print("=" * 60)

    # 我们知道这两种格式会返回OK，现在测试不同参数
    working_formats = [
        {
            "name": "PTZControl格式",
            "template": {
                "Name": "PTZControl",
                "Login": {
                    "UserName": username,
                    "Password": password
                },
                "PTZ": {}
            }
        },
        {
            "name": "ControlPTZ格式",
            "template": {
                "Name": "ControlPTZ",
                "User": username,
                "Pass": password
            }
        }
    ]

    # 不同的方向参数
    direction_variants = [
        # 文字方向 - 不同大小写
        {"Direction": "Left"}, {"Direction": "left"}, {"Direction": "LEFT"},
        {"Direction": "Right"}, {"Direction": "right"}, {"Direction": "RIGHT"},
        {"Direction": "Up"}, {"Direction": "up"}, {"Direction": "UP"},
        {"Direction": "Down"}, {"Direction": "down"}, {"Direction": "DOWN"},

        # 数字代码
        {"Direction": 1}, {"Direction": 2}, {"Direction": 3}, {"Direction": 4},  # 可能的方向代码
        {"Direction": "1"}, {"Direction": "2"}, {"Direction": "3"}, {"Direction": "4"},

        # 可能的JOVISION特定参数
        {"Code": "Left"}, {"Code": 1}, {"Code": "1"},
        {"Command": "Left"}, {"Command": 1},
        {"Action": "Left"}, {"Action": "Move", "Direction": "Left"},

        # 带Channel参数
        {"Channel": 0, "Direction": "Left"}, {"Channel": 1, "Direction": "Left"},
        {"Channel": 0, "Code": "Left"}, {"Channel": 1, "Code": "Left"},

        # 带Action参数
        {"Action": "Start", "Direction": "Left"}, {"Action": "start", "Direction": "Left"},
        {"Action": "Move", "Direction": "Left"}, {"Action": "move", "Direction": "Left"},

        # 组合参数
        {"Action": "Start", "Channel": 0, "Code": "Left", "Speed": 30},
        {"Action": "start", "Channel": 0, "Direction": "Left", "Speed": 5},
    ]

    # 不同速度
    speeds = [1, 5, 10, 30, 50, 100]

    test_count = 0
    successful_commands = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        for format_info in working_formats:
            print(f"\n🔍 测试 {format_info['name']}")
            print("-" * 40)

            for direction_params in direction_variants[:15]:  # 限制测试数量
                for speed in [5, 30]:  # 只测试两个速度

                    test_count += 1
                    print(f"\n测试 {test_count}: ", end="")

                    # 构建命令
                    command = format_info['template'].copy()

                    if format_info['name'] == "PTZControl格式":
                        # PTZControl格式
                        command['PTZ'] = direction_params.copy()
                        command['PTZ']['Speed'] = speed
                    else:
                        # ControlPTZ格式
                        command.update(direction_params)
                        command['Speed'] = speed

                    print(f"{command}")

                    try:
                        json_data = json.dumps(command).encode('utf-8')
                        sock.sendto(json_data, (camera_ip, port))

                        try:
                            response, addr = sock.recvfrom(1024)
                            response_text = response.decode('utf-8', errors='ignore')

                            if '"Ret": "OK"' in response_text:
                                print(f"   ✅ OK响应")

                                # 等待观察是否移动
                                print(f"   📹 等待移动观察 (3秒)...")
                                time.sleep(3)

                                # 记录成功命令
                                successful_commands.append({
                                    "command": command,
                                    "response": response_text
                                })

                                # 发送停止命令
                                stop_command = command.copy()
                                if 'PTZ' in stop_command:
                                    stop_command['PTZ'] = {"Action": "Stop"}
                                else:
                                    stop_command['Action'] = "Stop"

                                stop_json = json.dumps(stop_command).encode('utf-8')
                                sock.sendto(stop_json, (camera_ip, port))

                                print(f"   🛑 已发送停止命令")

                                # 询问用户是否看到移动
                                print(f"\n❓ 这次测试中您是否看到摄像头移动？")
                                print(f"   如果看到移动，请立即按Ctrl+C停止测试")

                            else:
                                print(f"   ❌ {response_text}")

                        except socket.timeout:
                            print(f"   ⏳ 无响应")

                    except Exception as e:
                        print(f"   ❌ 异常: {str(e)[:30]}...")

                    # 小延迟避免过快
                    time.sleep(0.5)

        sock.close()

    except KeyboardInterrupt:
        print(f"\n\n🛑 用户停止测试")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")

    # 显示所有成功的命令
    print(f"\n" + "=" * 60)
    print(f"📊 测试总结:")
    print(f"✅ 总共 {len(successful_commands)} 个命令返回OK")

    if successful_commands:
        print(f"\n📋 所有返回OK的命令:")
        for i, result in enumerate(successful_commands):
            print(f"\n{i+1}. {json.dumps(result['command'], indent=2)}")

    else:
        print(f"❌ 没有找到返回OK的命令")

def test_specific_jovision_codes():
    """测试特定的JOVISION代码"""
    camera_ip = "192.168.31.146"
    port = 34567
    username = "admin"
    password = "admin123"

    print(f"\n🎯 测试JOVISION特定代码")
    print("=" * 50)

    # JOVISION可能的控制代码
    jovision_codes = [
        # 基于常见PTZ协议的代码
        {"Name": "PTZControl", "Login": {"UserName": username, "Password": password}, "PTZ": {"Code": 0x01}},  # 上
        {"Name": "PTZControl", "Login": {"UserName": username, "Password": password}, "PTZ": {"Code": 0x02}},  # 下
        {"Name": "PTZControl", "Login": {"UserName": username, "Password": password}, "PTZ": {"Code": 0x03}},  # 左
        {"Name": "PTZControl", "Login": {"UserName": username, "Password": password}, "PTZ": {"Code": 0x04}},  # 右

        # 字符串代码
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "UP", "Speed": 5},
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "DOWN", "Speed": 5},
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "LEFT", "Speed": 5},
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "RIGHT", "Speed": 5},

        # 可能的十六进制代码
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "0x01", "Speed": 5},
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "0x02", "Speed": 5},
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "0x03", "Speed": 5},
        {"Name": "ControlPTZ", "User": username, "Pass": password, "Code": "0x04", "Speed": 5},
    ]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        for i, command in enumerate(jovision_codes):
            print(f"\n🔍 测试代码 {i+1}: {command}")

            try:
                json_data = json.dumps(command).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"   响应: {response_text}")

                    if '"Ret": "OK"' in response_text:
                        print(f"   ✅ 代码被接受，等待移动...")
                        time.sleep(3)

                except socket.timeout:
                    print(f"   ⏳ 无响应")

            except Exception as e:
                print(f"   ❌ 异常: {e}")

        sock.close()

    except Exception as e:
        print(f"❌ 测试异常: {e}")

if __name__ == "__main__":
    print("🎯 JOVISION PTZ详细参数测试")
    print("🔑 认证: admin/admin123 (已确认)")
    print("📹 目标: 找到真正能让摄像头移动的参数")
    print("=" * 70)

    # 提示用户
    print("💡 测试说明:")
    print("   - 每个命令测试后会等待3秒")
    print("   - 如果看到摄像头移动，请立即按 Ctrl+C 停止")
    print("   - 我们会记录那个成功的命令")
    print()

    input("按Enter开始详细测试...")

    # 1. 详细参数测试
    test_detailed_ptz_parameters()

    # 2. 特定代码测试
    test_specific_jovision_codes()

    print(f"\n🎯 如果仍未看到移动，可能需要:")
    print(f"   1. 检查Web界面PTZ设置是否启用")
    print(f"   2. 确认摄像头PTZ权限配置")
    print(f"   3. 查看是否需要特殊的激活步骤")