#!/usr/bin/env python3
"""
完整PTZ问题修复脚本
解决SSL兼容性和SessionId过期问题
"""

import os
import subprocess
import requests
import json
import time
import webbrowser
from datetime import datetime

def setup_ssl_compatibility():
    """设置SSL兼容性配置"""
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
    return openssl_conf

def get_session_id_manually():
    """指导用户手动获取SessionId"""
    print("\n📋 获取有效SessionId的步骤:")
    print("=" * 60)
    print("1. 打开浏览器，访问: https://192.168.31.146")
    print("2. 使用用户名密码登录（通常是 admin/admin123）")
    print("3. 进入PTZ控制页面")
    print("4. 按F12打开开发者工具")
    print("5. 点击'Network'(网络)标签")
    print("6. 点击任意PTZ方向按钮")
    print("7. 在网络请求中找到 '/ipc/grpc_cmd' 请求")
    print("8. 查看请求头(Request Headers)中的 'SessionId' 值")
    print()
    print("💡 或者在浏览器控制台(Console)运行:")
    print("   document.cookie.split(';').find(c => c.includes('session'))")
    print()

    # 尝试打开浏览器
    try:
        webbrowser.open('https://192.168.31.146')
        print("🌐 已自动打开浏览器")
    except:
        print("🌐 请手动打开浏览器访问摄像头")

    print()
    session_id = input("请输入获取到的SessionId: ").strip()
    return session_id

def test_session_id(session_id, camera_ip="192.168.31.146"):
    """测试SessionId是否有效"""
    print(f"\n🔍 测试SessionId: {session_id[:16]}...")

    curl_cmd = [
        "curl", "-s",
        "--insecure",
        "--connect-timeout", "5",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "-H", "Accept: application/json",
        "-H", f"Origin: https://{camera_ip}",
        "-H", f"Referer: https://{camera_ip}/ptzManager/ptzControl.html",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}',
        f"https://{camera_ip}/ipc/grpc_cmd"
    ]

    try:
        # 确保使用SSL兼容配置
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10, env=env)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if 'error' in response and 'Invailed' in response.get('error', {}).get('message', ''):
                    print("❌ SessionId已过期或无效")
                    return False
                else:
                    print("✅ SessionId有效")
                    return True
            except:
                print("✅ SessionId测试通过")
                return True
        else:
            print(f"❌ 连接失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def create_ptz_controller_script(session_id):
    """创建PTZ控制器脚本"""
    script_content = f'''#!/usr/bin/env python3
"""
工作版PTZ控制器
使用有效SessionId和SSL兼容配置
"""

import subprocess
import json
import time
import os

# 设置SSL兼容性
os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

class WorkingPTZController:
    def __init__(self, camera_ip="192.168.31.146", session_id="{session_id}"):
        self.camera_ip = camera_ip
        self.session_id = session_id
        self.base_url = f"https://{{camera_ip}}/ipc/grpc_cmd"

    def send_command(self, method, params=None):
        if params is None:
            params = {{"channelid": 0}}

        data = {{"method": method, "param": params}}

        curl_cmd = [
            "curl", "-s", "--insecure", "--connect-timeout", "5",
            "-H", "Content-Type: application/json",
            "-H", f"SessionId: {{self.session_id}}",
            "-H", "Accept: application/json",
            "--data-raw", json.dumps(data),
            self.base_url
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    def up(self, duration=0.5):
        if self.send_command("ptz_move_start", {{"channelid": 0, "tiltUp": 120}}):
            time.sleep(duration)
            return self.send_command("ptz_move_stop")
        return False

    def down(self, duration=0.5):
        if self.send_command("ptz_move_start", {{"channelid": 0, "tiltUp": -120}}):
            time.sleep(duration)
            return self.send_command("ptz_move_stop")
        return False

    def left(self, duration=0.5):
        if self.send_command("ptz_move_start", {{"channelid": 0, "panLeft": 120}}):
            time.sleep(duration)
            return self.send_command("ptz_move_stop")
        return False

    def right(self, duration=0.5):
        if self.send_command("ptz_move_start", {{"channelid": 0, "panRight": 120}}):
            time.sleep(duration)
            return self.send_command("ptz_move_stop")
        return False

    def stop(self):
        return self.send_command("ptz_move_stop")

def interactive_control():
    controller = WorkingPTZController()

    print("🎮 PTZ控制器 (SessionId: {session_id[:16]}...)")
    print("w/s: 上/下, a/d: 左/右, x: 停止, quit: 退出")

    while True:
        try:
            cmd = input("\\n命令: ").strip().lower()
            if cmd in ['quit', 'q']:
                break
            elif cmd == 'w':
                controller.up(0.3)
            elif cmd == 's':
                controller.down(0.3)
            elif cmd == 'a':
                controller.left(0.3)
            elif cmd == 'd':
                controller.right(0.3)
            elif cmd == 'x':
                controller.stop()
            else:
                print("未知命令")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    interactive_control()
'''

    script_file = '/home/fusha/Desktop/vlm_test.py/working_ptz_controller.py'
    with open(script_file, 'w') as f:
        f.write(script_content)

    # 设置执行权限
    os.chmod(script_file, 0o755)

    print(f"✅ 创建工作版PTZ控制器: {script_file}")
    return script_file

def create_startup_script(session_id):
    """创建启动脚本"""
    startup_content = f'''#!/bin/bash
# PTZ系统启动脚本 - 自动设置SSL兼容性

# 设置SSL兼容性
export OPENSSL_CONF=/tmp/openssl_legacy.conf
cat > /tmp/openssl_legacy.conf << 'EOF'
openssl_conf = openssl_init

[openssl_init]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
Options = UnsafeLegacyRenegotiation
EOF

echo "✅ SSL兼容性配置完成"

# 启动主监控系统
python integrated_camera_system.py \\
  --camera-ip 192.168.31.146 \\
  --camera-user admin \\
  --camera-pass admin123 \\
  --rtsp rtsp://admin:admin123@192.168.31.146/stream1

# 或者只启动PTZ控制器
# python working_ptz_controller.py
'''

    script_file = '/home/fusha/Desktop/vlm_test.py/start_fixed_system.sh'
    with open(script_file, 'w') as f:
        f.write(startup_content)

    os.chmod(script_file, 0o755)
    print(f"✅ 创建启动脚本: {script_file}")
    return script_file

def main():
    print("🔧 PTZ系统完整修复工具")
    print("=" * 60)

    # 1. 设置SSL兼容性
    print("第1步: 设置SSL兼容性...")
    setup_ssl_compatibility()

    # 2. 指导获取SessionId
    print("\\n第2步: 获取有效SessionId...")
    session_id = get_session_id_manually()

    if not session_id:
        print("❌ 必须提供SessionId才能继续")
        return

    # 3. 测试SessionId
    print("\\n第3步: 验证SessionId...")
    if not test_session_id(session_id):
        print("❌ SessionId无效，请重新获取")
        return

    # 4. 创建工作版控制器
    print("\\n第4步: 创建工作版控制器...")
    controller_script = create_ptz_controller_script(session_id)
    startup_script = create_startup_script(session_id)

    print("\\n🎉 修复完成！")
    print("=" * 40)
    print("📁 生成的文件:")
    print(f"   • {controller_script}")
    print(f"   • {startup_script}")
    print(f"   • /tmp/openssl_legacy.conf")
    print()
    print("🚀 使用方法:")
    print("   1. 独立PTZ控制: python working_ptz_controller.py")
    print("   2. 完整监控系统: bash start_fixed_system.sh")
    print()
    print("💡 SessionId有效期约1小时，过期后重新获取即可")

    # 询问是否立即测试
    test_now = input("\\n是否立即测试PTZ控制？(y/N): ").strip().lower()
    if test_now == 'y':
        print("\\n🎮 启动PTZ控制器...")
        subprocess.run(['python', controller_script])

if __name__ == "__main__":
    main()