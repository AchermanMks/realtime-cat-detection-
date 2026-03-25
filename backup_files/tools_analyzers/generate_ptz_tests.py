#!/usr/bin/env python3
"""
PTZ测试命令生成器
生成各种可能的PTZ控制命令进行测试
"""

def generate_ptz_test_commands(camera_ip="192.168.31.146", username="admin", password="admin123"):
    """生成PTZ测试命令"""

    base_url_http = f"http://{camera_ip}"
    base_url_https = f"https://{camera_ip}"
    auth = f"{username}:{password}"

    commands = []

    # 1. 海康威视风格的PTZ命令
    hik_endpoints = [
        "/cgi-bin/ptz.cgi",
        "/web/cgi-bin/hi3510/ptzctrl.cgi",
        "/PSIA/PTZ/channels/1/continuous",
        "/PSIA/PTZ/channels/1/momentary"
    ]

    hik_params = [
        "action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0",
        "action=start&channel=0&code=Right&arg1=0&arg2=5&arg3=0",
        "action=start&channel=0&code=Up&arg1=0&arg2=5&arg3=0",
        "action=start&channel=0&code=Down&arg1=0&arg2=5&arg3=0",
        "action=stop&channel=0&code=Left&arg1=0&arg2=5&arg3=0",
    ]

    for protocol in ["http", "https"]:
        base_url = base_url_http if protocol == "http" else base_url_https
        ssl_flag = "" if protocol == "http" else "-k"

        for endpoint in hik_endpoints:
            for params in hik_params:
                cmd = f'curl {ssl_flag} -u {auth} "{base_url}{endpoint}?{params}"'
                commands.append(("海康威视风格", cmd))

    # 2. 大华风格的PTZ命令
    dahua_endpoints = [
        "/cgi-bin/ptz.cgi",
        "/cgi-bin/camctrl.cgi"
    ]

    dahua_params = [
        "action=start&channel=0&code=LeftUp&arg1=0&arg2=5&arg3=0",
        "action=start&channel=0&code=RightUp&arg1=0&arg2=5&arg3=0",
        "action=start&channel=0&code=LeftDown&arg1=0&arg2=5&arg3=0",
        "action=start&channel=0&code=RightDown&arg1=0&arg2=5&arg3=0",
    ]

    for protocol in ["http", "https"]:
        base_url = base_url_http if protocol == "http" else base_url_https
        ssl_flag = "" if protocol == "http" else "-k"

        for endpoint in dahua_endpoints:
            for params in dahua_params:
                cmd = f'curl {ssl_flag} -u {auth} "{base_url}{endpoint}?{params}"'
                commands.append(("大华风格", cmd))

    # 3. 现代API风格
    api_endpoints = [
        "/api/ptz",
        "/api/v1/ptz",
        "/api/camera/ptz",
        "/control/ptz",
        "/device/ptz"
    ]

    api_params = [
        "action=move&direction=left&speed=5",
        "action=move&direction=right&speed=5",
        "action=move&direction=up&speed=5",
        "action=move&direction=down&speed=5",
        "cmd=left&speed=3",
        "cmd=right&speed=3",
        "cmd=up&speed=3",
        "cmd=down&speed=3",
    ]

    for protocol in ["http", "https"]:
        base_url = base_url_http if protocol == "http" else base_url_https
        ssl_flag = "" if protocol == "http" else "-k"

        for endpoint in api_endpoints:
            for params in api_params:
                cmd = f'curl {ssl_flag} -u {auth} "{base_url}{endpoint}?{params}"'
                commands.append(("现代API风格", cmd))

    # 4. POST JSON格式
    json_payloads = [
        '{"action": "move", "direction": "left", "speed": 5}',
        '{"action": "move", "direction": "right", "speed": 5}',
        '{"action": "move", "direction": "up", "speed": 5}',
        '{"action": "move", "direction": "down", "speed": 5}',
        '{"command": "ptz", "move": "left", "speed": 3}',
        '{"command": "ptz", "move": "right", "speed": 3}',
        '{"cmd": "moveLeft", "speed": 50}',
        '{"cmd": "moveRight", "speed": 50}',
    ]

    for protocol in ["http", "https"]:
        base_url = base_url_http if protocol == "http" else base_url_https
        ssl_flag = "" if protocol == "http" else "-k"

        for endpoint in api_endpoints:
            for payload in json_payloads:
                cmd = f'curl {ssl_flag} -u {auth} -X POST -H "Content-Type: application/json" -d \'{payload}\' "{base_url}{endpoint}"'
                commands.append(("JSON POST", cmd))

    # 5. 小米/其他厂商可能的格式
    xiaomi_endpoints = [
        "/cgi-bin/action.cgi",
        "/cgi-bin/hi3510/param.cgi",
        "/web/cgi-bin/hi3510/param.cgi",
        "/mcu?action=ptz",
        "/motor",
        "/control"
    ]

    xiaomi_params = [
        "cmd=preset&-act=goto&-number=1",
        "cmd=ptzctrl&-step=0&-act=left&-speed=5",
        "cmd=ptzctrl&-step=0&-act=right&-speed=5",
        "cmd=ptzctrl&-step=0&-act=up&-speed=5",
        "cmd=ptzctrl&-step=0&-act=down&-speed=5",
        "action=ptz&move=left&speed=3",
        "action=ptz&move=right&speed=3"
    ]

    for protocol in ["http", "https"]:
        base_url = base_url_http if protocol == "http" else base_url_https
        ssl_flag = "" if protocol == "http" else "-k"

        for endpoint in xiaomi_endpoints:
            for params in xiaomi_params:
                cmd = f'curl {ssl_flag} -u {auth} "{base_url}{endpoint}?{params}"'
                commands.append(("小米/其他风格", cmd))

    return commands

def main():
    print("🔧 PTZ协议测试命令生成器")
    print("=" * 60)

    # 生成命令
    commands = generate_ptz_test_commands()

    # 按类型分组
    by_type = {}
    for cmd_type, cmd in commands:
        if cmd_type not in by_type:
            by_type[cmd_type] = []
        by_type[cmd_type].append(cmd)

    # 生成测试脚本
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    script_file = f"ptz_test_all_{timestamp}.sh"

    with open(script_file, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# PTZ协议全面测试脚本\n")
        f.write("# 自动生成于: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")

        f.write("echo '🔧 PTZ协议测试开始...'\n")
        f.write("echo '按Ctrl+C随时停止测试'\n")
        f.write("echo ''\n\n")

        for cmd_type, cmds in by_type.items():
            f.write(f"echo '📋 测试类型: {cmd_type}'\n")
            f.write("echo '=" + "=" * 50 + "'\n")

            for i, cmd in enumerate(cmds[:5], 1):  # 只取前5个避免太多
                f.write(f"echo '测试 {i}: {cmd}'\n")
                f.write(f"{cmd}\n")
                f.write("sleep 1\n")

            f.write("echo ''\n")

        f.write("echo '✅ 测试完成'\n")

    # 生成分类脚本
    quick_script = f"ptz_quick_test_{timestamp}.sh"
    with open(quick_script, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# PTZ快速测试 - 常见命令\n\n")

        quick_tests = [
            'curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5"',
            'curl -k -u admin:admin123 "https://192.168.31.146/api/ptz?cmd=left&speed=3"',
            'curl -k -u admin:admin123 -X POST -H "Content-Type: application/json" -d \'{"action":"move","direction":"left","speed":5}\' "https://192.168.31.146/api/ptz"',
            'curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=left&-speed=5"',
        ]

        for i, cmd in enumerate(quick_tests, 1):
            f.write(f"echo '快速测试 {i}:'\n")
            f.write(f"echo '{cmd}'\n")
            f.write(f"{cmd}\n")
            f.write("echo ''\n")

    print(f"📄 完整测试脚本: {script_file}")
    print(f"📄 快速测试脚本: {quick_script}")

    # 显示使用说明
    print("\n📋 使用说明:")
    print("1. 使脚本可执行:")
    print(f"   chmod +x {script_file}")
    print(f"   chmod +x {quick_script}")
    print("\n2. 运行测试:")
    print(f"   ./{quick_script}  # 快速测试")
    print(f"   ./{script_file}   # 完整测试")
    print("\n3. 观察输出，寻找返回200状态码或有效响应的命令")

    # 显示手动测试建议
    print("\n🔍 手动测试建议:")
    print("1. 在浏览器中访问: https://192.168.31.146/setting.html")
    print("2. 打开开发者工具(F12) -> Network标签")
    print("3. 操作PTZ控制，观察网络请求")
    print("4. 记录成功的请求URL和参数")

if __name__ == "__main__":
    import time
    main()