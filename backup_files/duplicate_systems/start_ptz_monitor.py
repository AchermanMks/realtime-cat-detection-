#!/usr/bin/env python3
"""
PTZ监控系统启动器 - 解决端口冲突和连接问题
"""

import subprocess
import json
import os
import sys
import socket

def check_port(port):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
        return True
    except:
        return False

def find_available_port():
    """找到可用端口"""
    for port in range(5001, 5010):
        if check_port(port):
            return port
    return 5001

def setup_ssl():
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

def auto_get_session():
    """自动获取SessionId"""
    print("🤖 自动获取SessionId...")
    try:
        result = subprocess.run([sys.executable, 'smart_auto_session.py'],
                              input="n\n", text=True, capture_output=True, timeout=30)

        if result.returncode == 0:
            try:
                with open('auto_session_config.json', 'r') as f:
                    config = json.load(f)
                return config.get('session_id')
            except:
                return None
        else:
            print(f"自动获取失败，使用手动方式")
            return None
    except Exception as e:
        print(f"获取异常: {e}")
        return None

def test_camera_connection():
    """测试摄像头连接"""
    print("🔍 测试摄像头连接...")

    # 测试ping
    try:
        result = subprocess.run(['ping', '-c', '1', '192.168.31.146'],
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ 摄像头网络可达")
        else:
            print("❌ 摄像头网络不可达")
            return False
    except:
        print("❌ ping测试失败")
        return False

    # 测试RTSP端口
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            result = s.connect_ex(('192.168.31.146', 554))
            if result == 0:
                print("✅ RTSP端口554开放")
                return True
            else:
                print("❌ RTSP端口554关闭")
                return False
    except:
        print("❌ RTSP端口测试失败")
        return False

def start_monitoring_system(session_id, port, use_local_camera=False):
    """启动监控系统"""
    print(f"🚀 启动PTZ监控系统 (端口: {port})")

    # 创建临时的PTZ控制器补丁
    ptz_patch = f'''
import subprocess
import json
import os
import time

class AutoSessionPTZController:
    def __init__(self):
        self.session_id = "{session_id}"
        os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'
        self.last_command_time = 0
        self.command_cooldown = 0.1

    def send_command(self, action):
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            return True

        command_map = {{
            'up': {{"method": "ptz_move_start", "param": {{"channelid": 0, "tiltUp": 120}}}},
            'down': {{"method": "ptz_move_start", "param": {{"channelid": 0, "tiltUp": -120}}}},
            'left': {{"method": "ptz_move_start", "param": {{"channelid": 0, "panLeft": 120}}}},
            'right': {{"method": "ptz_move_start", "param": {{"channelid": 0, "panRight": 120}}}},
            'stop': {{"method": "ptz_move_stop", "param": {{"channelid": 0}}}},
            'zoom_in': {{"method": "ptz_move_start", "param": {{"channelid": 0, "zoomIn": 120}}}},
            'zoom_out': {{"method": "ptz_move_start", "param": {{"channelid": 0, "zoomOut": 120}}}},
        }}

        if action not in command_map:
            print(f"❌ 不支持的PTZ命令: {{action}}")
            return False

        data = command_map[action]
        curl_cmd = [
            "curl", "-s", "--insecure", "--connect-timeout", "3",
            "-H", "Content-Type: application/json",
            "-H", f"SessionId: {{self.session_id}}",
            "--data-raw", json.dumps(data),
            "https://192.168.31.146/ipc/grpc_cmd"
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
            self.last_command_time = current_time
            success = result.returncode == 0
            if success:
                print(f"PTZ命令 {{action}}: 成功")
            else:
                print(f"PTZ命令 {{action}}: 失败")
            return success
        except Exception as e:
            print(f"PTZ命令 {{action}}: 异常 {{e}}")
            return False

# 动态替换PTZ控制器
globals()['PTZControllerAdapter'] = AutoSessionPTZController
'''

    # 保存补丁文件
    with open('ptz_patch_temp.py', 'w') as f:
        f.write(ptz_patch)

    # 构建启动命令
    cmd = [sys.executable, 'integrated_camera_system.py', '--port', str(port)]

    if use_local_camera:
        cmd.extend(['--camera', '0'])
        print("📷 使用本地摄像头")
    else:
        cmd.extend([
            '--camera-ip', '192.168.31.146',
            '--camera-user', 'admin',
            '--camera-pass', 'admin123',
            '--rtsp', 'rtsp://admin:admin123@192.168.31.146/stream1'
        ])
        print("📡 使用RTSP摄像头流")

    print(f"🌐 Web界面: http://localhost:{port}")
    print(f"🎮 PTZ控制: SessionId {session_id[:16]}...")
    print("🛑 按 Ctrl+C 停止")
    print("-" * 60)

    try:
        # 先应用PTZ补丁
        exec(open('ptz_patch_temp.py').read())

        # 启动系统
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\\n👋 系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
    finally:
        # 清理临时文件
        try:
            os.remove('ptz_patch_temp.py')
        except:
            pass

def main():
    print("🎯 PTZ监控系统启动器")
    print("=" * 60)

    # 1. 环境设置
    setup_ssl()

    # 2. 检查端口
    port = find_available_port()
    print(f"📊 使用端口: {port}")

    # 3. 自动获取SessionId
    session_id = auto_get_session()
    if not session_id:
        print("❌ 无法获取SessionId")
        return

    print(f"✅ SessionId: {session_id[:16]}...")

    # 4. 测试摄像头连接
    camera_available = test_camera_connection()

    # 5. 启动系统
    if camera_available:
        print("🎯 使用RTSP摄像头流")
        start_monitoring_system(session_id, port, use_local_camera=False)
    else:
        print("🎯 摄像头不可达，使用本地摄像头")
        start_monitoring_system(session_id, port, use_local_camera=True)

if __name__ == "__main__":
    main()