#!/usr/bin/env python3
"""
手动获取SessionId指导工具
提供详细步骤和自动验证
"""

import webbrowser
import subprocess
import json
import os

def setup_ssl_compatibility():
    """设置SSL兼容性"""
    openssl_conf = '/tmp/openssl_legacy.conf'
    config_content = '''openssl_conf = openssl_init

[openssl_init]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
Options = UnsafeLegacyRenegotiation
'''

    with open(openssl_conf, 'w') as f:
        f.write(config_content)

    os.environ['OPENSSL_CONF'] = openssl_conf
    print("✅ SSL兼容性配置完成")

def open_camera_interface():
    """打开摄像头Web界面"""
    camera_url = "https://192.168.31.146"

    print("🌐 正在打开摄像头Web界面...")
    try:
        webbrowser.open(camera_url)
        print(f"✅ 浏览器已打开: {camera_url}")
    except:
        print(f"⚠️ 请手动打开浏览器访问: {camera_url}")

def show_detailed_instructions():
    """显示详细获取步骤"""
    print("\n📋 获取SessionId详细步骤:")
    print("=" * 60)

    steps = [
        "1. 在打开的浏览器中登录摄像头",
        "   - 用户名通常是: admin",
        "   - 密码通常是: admin123 或 123456",
        "",
        "2. 登录成功后，进入PTZ控制页面",
        "   - 寻找 '云台控制' 或 'PTZ Control' 菜单",
        "",
        "3. 按 F12 打开开发者工具",
        "   - 或右键 → 检查元素",
        "",
        "4. 点击 'Network'(网络) 标签",
        "   - 确保开发者工具中的网络监控是开启的",
        "",
        "5. 在PTZ控制界面点击任意方向按钮",
        "   - 比如点击 ↑ 上方向按钮",
        "",
        "6. 在Network标签中找到最新的请求",
        "   - 请求URL包含: /ipc/grpc_cmd",
        "   - 点击这个请求",
        "",
        "7. 查看请求详情:",
        "   - 点击 'Headers'(请求头) 标签",
        "   - 在 'Request Headers' 中找到 'SessionId'",
        "   - 复制 SessionId 的值",
        "",
        "💡 备用方法 - 浏览器控制台:",
        "   - 按F12 → Console标签",
        "   - 输入: document.cookie",
        "   - 查找包含session的cookie值"
    ]

    for step in steps:
        print(f"   {step}")

    print("\n" + "=" * 60)

def test_session_id(session_id):
    """测试SessionId是否有效"""
    if not session_id or len(session_id) < 10:
        print("❌ SessionId格式不正确")
        return False

    print(f"\n🔍 测试SessionId: {session_id[:16]}...")

    curl_cmd = [
        "curl", "-s",
        "--insecure",
        "--connect-timeout", "5",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "-H", "Accept: application/json",
        "-H", "Origin: https://192.168.31.146",
        "-H", "Referer: https://192.168.31.146/ptzManager/ptzControl.html",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}',
        "https://192.168.31.146/ipc/grpc_cmd"
    ]

    try:
        # 使用SSL兼容配置
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10, env=env)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)

                # 检查是否有错误信息
                if 'error' in response:
                    error_msg = response.get('error', {}).get('message', '')
                    if 'Invailed' in error_msg or 'Expired' in error_msg:
                        print("❌ SessionId已过期或无效")
                        print(f"   错误信息: {error_msg}")
                        return False

                print("✅ SessionId有效！")
                print(f"   响应: {response}")
                return True

            except json.JSONDecodeError:
                # 如果不是JSON，但状态码是200，也可能是成功
                print("✅ SessionId可能有效")
                print(f"   响应: {result.stdout[:100]}")
                return True
        else:
            print("❌ 连接失败")
            print(f"   错误: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def save_working_session(session_id):
    """保存有效的SessionId到配置文件"""
    config_file = "/home/fusha/Desktop/vlm_test.py/ptz_config.json"

    config = {
        "session_id": session_id,
        "camera_ip": "192.168.31.146",
        "timestamp": str(datetime.now()),
        "notes": "手动获取的有效SessionId，有效期约1小时"
    }

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"💾 SessionId已保存到: {config_file}")

def create_test_script(session_id):
    """创建测试脚本"""
    script_content = f'''#!/usr/bin/env python3
"""
使用获取的SessionId测试PTZ控制
"""

import subprocess
import json
import time
import os

# 设置SSL兼容性
os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

SESSION_ID = "{session_id}"
CAMERA_IP = "192.168.31.146"

def send_ptz_command(method, params=None):
    """发送PTZ命令"""
    if params is None:
        params = {{"channelid": 0}}

    data = {{"method": method, "param": params}}

    curl_cmd = [
        "curl", "-s", "--insecure", "--connect-timeout", "5",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {{SESSION_ID}}",
        "-H", "Accept: application/json",
        "--data-raw", json.dumps(data),
        f"https://{{CAMERA_IP}}/ipc/grpc_cmd"
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ {{method}} 成功")
            return True
        else:
            print(f"❌ {{method}} 失败")
            return False
    except Exception as e:
        print(f"❌ {{method}} 异常: {{e}}")
        return False

def test_all_directions():
    """测试所有方向"""
    commands = [
        ("停止", "ptz_move_stop", {{"channelid": 0}}),
        ("向上", "ptz_move_start", {{"channelid": 0, "tiltUp": 120}}),
        ("停止", "ptz_move_stop", {{"channelid": 0}}),
        ("向下", "ptz_move_start", {{"channelid": 0, "tiltUp": -120}}),
        ("停止", "ptz_move_stop", {{"channelid": 0}}),
        ("向左", "ptz_move_start", {{"channelid": 0, "panLeft": 120}}),
        ("停止", "ptz_move_stop", {{"channelid": 0}}),
        ("向右", "ptz_move_start", {{"channelid": 0, "panRight": 120}}),
        ("停止", "ptz_move_stop", {{"channelid": 0}})
    ]

    print("🎯 开始PTZ控制测试...")
    for name, method, params in commands:
        print(f"   📍 {{name}}...")
        send_ptz_command(method, params)
        time.sleep(0.5)

    print("✅ PTZ测试完成")

if __name__ == "__main__":
    print(f"🎮 PTZ控制测试 (SessionId: {{SESSION_ID[:16]}}...)")
    test_all_directions()
'''

    test_file = "/home/fusha/Desktop/vlm_test.py/test_ptz_with_session.py"
    with open(test_file, 'w') as f:
        f.write(script_content)

    os.chmod(test_file, 0o755)
    print(f"📝 测试脚本已创建: {test_file}")
    return test_file

def main():
    from datetime import datetime

    print("📱 手动获取SessionId工具")
    print("=" * 50)

    # 1. 设置环境
    setup_ssl_compatibility()

    # 2. 打开浏览器
    print("\n第1步: 打开摄像头Web界面")
    open_camera_interface()

    # 3. 显示指导
    print("\n第2步: 获取SessionId")
    show_detailed_instructions()

    # 4. 等待用户输入
    print("\n第3步: 输入获取的SessionId")
    while True:
        session_id = input("\n请粘贴SessionId (输入 'help' 查看帮助): ").strip()

        if session_id.lower() == 'help':
            show_detailed_instructions()
            continue
        elif session_id.lower() in ['quit', 'exit', 'q']:
            print("👋 退出")
            return
        elif not session_id:
            print("❌ 请输入SessionId")
            continue

        # 5. 验证SessionId
        if test_session_id(session_id):
            print("\n🎉 SessionId验证成功！")

            # 6. 保存配置和创建测试脚本
            save_working_session(session_id)
            test_script = create_test_script(session_id)

            print(f"\n📋 使用方法:")
            print(f"   1. 立即测试: python {test_script}")
            print(f"   2. 集成使用: 将SessionId用于其他PTZ脚本")
            print(f"   3. 有效期: 约1小时，过期后重新获取")

            # 询问是否立即测试
            test_now = input(f"\n是否立即运行PTZ测试？(Y/n): ").strip().lower()
            if test_now != 'n':
                print("\n🚀 启动PTZ测试...")
                subprocess.run(['python', test_script])

            break
        else:
            print("❌ SessionId无效，请重新获取")
            retry = input("是否重试？(Y/n): ").strip().lower()
            if retry == 'n':
                break

if __name__ == "__main__":
    main()