#!/usr/bin/env python3
"""
一键启动完整PTZ监控系统
自动处理SessionId，直接启动监控系统
"""

import subprocess
import json
import os
import sys

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
    print("✅ SSL兼容性配置完成")

def auto_get_session():
    """自动获取SessionId"""
    print("🤖 自动获取SessionId...")
    try:
        # 运行自动获取脚本
        result = subprocess.run([sys.executable, 'smart_auto_session.py'],
                              input="n\n", text=True, capture_output=True, timeout=30)

        if result.returncode == 0:
            print("✅ SessionId自动获取成功")

            # 读取生成的SessionId
            try:
                with open('auto_session_config.json', 'r') as f:
                    config = json.load(f)
                return config.get('session_id')
            except:
                return None
        else:
            print(f"❌ SessionId获取失败")
            return None
    except Exception as e:
        print(f"❌ 自动获取异常: {e}")
        return None

def update_integrated_system(session_id):
    """更新集成系统的PTZ控制器"""
    print("🔧 更新系统PTZ控制器...")

    # 创建一个替换的PTZ控制器类
    ptz_controller_code = f'''
# 自动SessionId PTZ控制器替换
class AutoSessionPTZController:
    def __init__(self):
        self.session_id = "{session_id}"
        import os
        os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'
        self.last_command_time = 0
        self.command_cooldown = 0.1

    def send_command(self, action):
        import subprocess
        import json
        import time

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
            print(f"PTZ命令 {{action}}: {{'成功' if success else '失败'}}")
            return success
        except:
            return False

# 用自动SessionId控制器替换原有的PTZControllerAdapter
PTZControllerAdapter = AutoSessionPTZController
'''

    # 将这个代码写入临时文件
    with open('auto_ptz_patch.py', 'w') as f:
        f.write(ptz_controller_code)

    print("✅ PTZ控制器已更新")

def start_monitoring():
    """启动监控系统"""
    print("🚀 启动完整监控系统...")
    print("📺 系统包含:")
    print("   • AI视频分析 (Qwen2-VL)")
    print("   • 实时视频流")
    print("   • PTZ摄像头控制")
    print("   • Web界面控制")
    print("   • 系统状态监控")
    print()
    print("🌐 Web界面将在 http://localhost:5000 启动")
    print("🎮 PTZ控制: 点击界面按钮或使用键盘 WASD")
    print("🛑 停止: 按 Ctrl+C")
    print("-" * 60)

    try:
        # 导入补丁
        exec(open('auto_ptz_patch.py').read(), globals())

        # 启动集成系统
        cmd = [
            sys.executable, 'integrated_camera_system.py',
            '--camera-ip', '192.168.31.146',
            '--camera-user', 'admin',
            '--camera-pass', 'admin123',
            '--rtsp', 'rtsp://admin:admin123@192.168.31.146/stream1'
        ]

        subprocess.run(cmd)

    except KeyboardInterrupt:
        print("\n👋 监控系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

def main():
    print("🎯 一键启动完整PTZ监控系统")
    print("=" * 60)

    # 1. 设置环境
    setup_ssl()

    # 2. 自动获取SessionId
    session_id = auto_get_session()

    if not session_id:
        print("❌ 无法获取SessionId，系统启动失败")
        return

    print(f"✅ 获取到SessionId: {session_id[:16]}...")

    # 3. 更新系统
    update_integrated_system(session_id)

    # 4. 启动监控
    start_monitoring()

if __name__ == "__main__":
    main()