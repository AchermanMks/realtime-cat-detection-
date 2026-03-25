#!/usr/bin/env python3
"""
最终PTZ控制测试 - 尝试所有可能的方法
"""

import socket
import json
import time
import struct

def test_alternative_protocols():
    """测试其他可能的PTZ协议"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    print("🎯 最终PTZ控制测试")
    print("🔍 尝试所有可能的协议和参数组合")
    print("=" * 60)

    # 1. 测试预设位置命令（更容易成功）
    print("\n1️⃣ 测试预设位置命令")
    print("-" * 30)

    preset_commands = [
        {
            "Name": "PTZControl",
            "Login": {"UserName": username, "Password": password},
            "PTZ": {"Preset": 1, "Action": "Goto"}
        },
        {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "Preset": 1, "Action": "Call"
        },
        {
            "Name": "PTZControl",
            "Login": {"UserName": username, "Password": password},
            "PTZ": {"Command": "GotoPreset", "PresetID": 1}
        },
        {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "Command": "CallPreset", "PresetNumber": 1
        }
    ]

    if test_commands(camera_ip, 34567, preset_commands, "预设位置"):
        return True

    # 2. 测试相对移动命令
    print("\n2️⃣ 测试相对移动命令")
    print("-" * 30)

    relative_commands = [
        {
            "Name": "PTZControl",
            "Login": {"UserName": username, "Password": password},
            "PTZ": {"RelativeMove": {"Pan": -10, "Tilt": 0}}
        },
        {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "RelativeMove": True, "Pan": -10, "Tilt": 0, "Speed": 5
        },
        {
            "Name": "PTZControl",
            "Login": {"UserName": username, "Password": password},
            "PTZ": {"Move": "Relative", "X": -10, "Y": 0, "Speed": 5}
        }
    ]

    if test_commands(camera_ip, 34567, relative_commands, "相对移动"):
        return True

    # 3. 测试绝对位置命令
    print("\n3️⃣ 测试绝对位置命令")
    print("-" * 30)

    absolute_commands = [
        {
            "Name": "PTZControl",
            "Login": {"UserName": username, "Password": password},
            "PTZ": {"AbsoluteMove": {"Pan": 100, "Tilt": 0, "Zoom": 0}}
        },
        {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "AbsoluteMove": True, "Pan": 100, "Tilt": 0, "Speed": 5
        }
    ]

    if test_commands(camera_ip, 34567, absolute_commands, "绝对位置"):
        return True

    # 4. 测试数字方向代码
    print("\n4️⃣ 测试数字方向代码")
    print("-" * 30)

    numeric_commands = []
    # 尝试0-8的数字代码（经典PTZ协议）
    for code in range(9):
        numeric_commands.append({
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "Code": code, "Speed": 5
        })

    if test_commands(camera_ip, 34567, numeric_commands, "数字代码"):
        return True

    # 5. 测试VISCA协议格式
    print("\n5️⃣ 测试VISCA协议格式")
    print("-" * 30)

    visca_commands = [
        {
            "Name": "PTZControl",
            "Login": {"UserName": username, "Password": password},
            "Protocol": "VISCA",
            "PTZ": {"Command": "Left", "Speed": 0x18}
        },
        {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "Protocol": "VISCA", "Direction": "Left", "Speed": 24
        }
    ]

    if test_commands(camera_ip, 34567, visca_commands, "VISCA协议"):
        return True

    # 6. 测试其他端口
    print("\n6️⃣ 测试其他端口")
    print("-" * 30)

    other_ports = [8000, 9000, 37777]
    basic_command = {
        "Name": "ControlPTZ",
        "User": username, "Pass": password,
        "Direction": "Left", "Speed": 5
    }

    for port in other_ports:
        print(f"🔍 测试端口 {port}")
        if test_commands(camera_ip, port, [basic_command], f"端口{port}"):
            return True

    # 7. 测试启动/停止序列
    print("\n7️⃣ 测试启动/停止序列")
    print("-" * 30)

    if test_start_stop_sequence(camera_ip, 34567, username, password):
        return True

    return False

def test_commands(camera_ip, port, commands, test_name):
    """测试命令列表"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        for i, command in enumerate(commands):
            print(f"🔍 {test_name} 命令 {i+1}: {json.dumps(command)}")

            try:
                json_data = json.dumps(command).encode('utf-8')
                sock.sendto(json_data, (camera_ip, port))

                try:
                    response, addr = sock.recvfrom(1024)
                    response_text = response.decode('utf-8', errors='ignore')
                    print(f"   响应: {response_text}")

                    if '"Ret": "OK"' in response_text:
                        print(f"   📹 等待移动观察 (5秒)...")
                        print(f"   ❓ 您是否看到摄像头移动？如果是，请按Ctrl+C")
                        time.sleep(5)

                except socket.timeout:
                    print(f"   ⏳ 无响应")

            except Exception as e:
                print(f"   ❌ 异常: {str(e)[:30]}...")

        sock.close()

    except Exception as e:
        print(f"❌ {test_name} 测试失败: {e}")

    return False  # 如果到这里，说明没有看到移动

def test_start_stop_sequence(camera_ip, port, username, password):
    """测试启动/停止序列"""
    print("🔄 测试启动/停止序列")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)

        # 1. 发送启动命令
        start_cmd = {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "Action": "Start", "Direction": "Left", "Speed": 5
        }

        print(f"🚀 发送启动命令: {start_cmd}")
        json_data = json.dumps(start_cmd).encode('utf-8')
        sock.sendto(json_data, (camera_ip, port))

        try:
            response, addr = sock.recvfrom(1024)
            print(f"   启动响应: {response.decode('utf-8', errors='ignore')}")
        except socket.timeout:
            print(f"   ⏳ 启动无响应")

        # 2. 等待移动
        print(f"   📹 等待移动 (3秒)...")
        time.sleep(3)

        # 3. 发送停止命令
        stop_cmd = {
            "Name": "ControlPTZ",
            "User": username, "Pass": password,
            "Action": "Stop"
        }

        print(f"🛑 发送停止命令: {stop_cmd}")
        json_data = json.dumps(stop_cmd).encode('utf-8')
        sock.sendto(json_data, (camera_ip, port))

        try:
            response, addr = sock.recvfrom(1024)
            print(f"   停止响应: {response.decode('utf-8', errors='ignore')}")
        except socket.timeout:
            print(f"   ⏳ 停止无响应")

        sock.close()

    except Exception as e:
        print(f"❌ 启动/停止测试失败: {e}")

    return False

def final_diagnosis():
    """最终诊断"""
    print(f"\n" + "=" * 60)
    print(f"🏥 最终诊断")
    print("=" * 60)

    print(f"📊 测试结果总结:")
    print(f"✅ UDP端口34567响应正常")
    print(f"✅ 认证凭据正确 (admin/admin123)")
    print(f"✅ 多个命令返回'OK'状态")
    print(f"❌ 摄像头没有物理移动")

    print(f"\n🔍 可能的原因:")
    print(f"1. 🔧 PTZ功能在固件中被禁用")
    print(f"2. 🎛️ 需要在Web界面中启用PTZ控制")
    print(f"3. 🔌 PTZ硬件连接问题（RS485/RS232）")
    print(f"4. ⚙️ 需要特殊的PTZ协议配置")
    print(f"5. 🎯 摄像头可能不是真正的PTZ设备")

    print(f"\n💡 解决建议:")
    print(f"1. 📱 检查手机客户端的详细设置")
    print(f"   - 查看PTZ协议类型")
    print(f"   - 检查PTZ地址设置")
    print(f"   - 确认速度和其他参数")

    print(f"\n2. 🌐 访问Web管理界面")
    print(f"   - 登录: https://192.168.31.146 (admin/admin123)")
    print(f"   - 查找PTZ/云台设置选项")
    print(f"   - 启用PTZ控制功能")

    print(f"\n3. 🔧 检查硬件连接")
    print(f"   - 确认PTZ电机连接")
    print(f"   - 检查供电是否充足")

    print(f"\n4. 📞 联系技术支持")
    print(f"   - JOVISION官方支持")
    print(f"   - 提供序列号: 92903")
    print(f"   - 固件版本: V2.2.6501")

if __name__ == "__main__":
    try:
        success = test_alternative_protocols()

        if not success:
            print(f"\n❌ 所有PTZ协议测试均未产生物理移动")
            final_diagnosis()
        else:
            print(f"\n🎉 找到工作的PTZ协议!")

    except KeyboardInterrupt:
        print(f"\n\n🎉 用户确认看到摄像头移动!")
        print(f"✅ PTZ控制成功工作!")
        print(f"🔧 现在可以集成到Web应用中!")