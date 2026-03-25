#!/usr/bin/env python3
"""
一键自动PTZ系统
完全自动化的SessionId获取和PTZ控制解决方案
"""

import subprocess
import json
import os
from datetime import datetime

def run_auto_session_getter():
    """运行自动SessionId获取器"""
    print("🤖 启动自动SessionId获取...")
    try:
        result = subprocess.run(['python', 'smart_auto_session.py'],
                              input="n\n", text=True, capture_output=True, timeout=30)

        if result.returncode == 0:
            print("✅ SessionId自动获取成功")
            return True
        else:
            print(f"❌ SessionId获取失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 自动获取异常: {e}")
        return False

def check_session_config():
    """检查SessionId配置"""
    try:
        with open('auto_session_config.json', 'r') as f:
            config = json.load(f)

        session_id = config.get('session_id')
        timestamp = config.get('timestamp')

        if session_id:
            print(f"📋 找到已保存的SessionId:")
            print(f"   SessionId: {session_id[:16]}...")
            print(f"   获取时间: {timestamp}")
            return session_id
    except:
        pass

    return None

def test_existing_session(session_id):
    """测试现有SessionId是否仍有效"""
    print(f"🔍 测试SessionId有效性...")

    curl_cmd = [
        "curl", "-s", "--insecure", "--connect-timeout", "5",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}',
        "https://192.168.31.146/ipc/grpc_cmd"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10, env=env)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if 'error' in response and 'Invailed' in str(response.get('error', {})):
                    print("❌ SessionId已过期")
                    return False
                else:
                    print("✅ SessionId仍有效")
                    return True
            except:
                print("✅ SessionId有效")
                return True
        else:
            print("❌ 连接测试失败")
            return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def create_integrated_system(session_id):
    """创建集成的监控系统"""
    print("🔧 正在集成SessionId到主监控系统...")

    # 更新integrated_camera_system.py中的PTZ控制器
    try:
        # 创建一个简化的PTZ适配器
        adapter_content = f'''#!/usr/bin/env python3
"""
自动SessionId PTZ适配器
"""

import subprocess
import json
import os

class AutoSessionPTZAdapter:
    def __init__(self):
        self.session_id = "{session_id}"
        os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

    def send_command(self, action):
        """适配原有接口"""
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
            return result.returncode == 0
        except:
            return False
'''

        with open('auto_session_ptz_adapter.py', 'w') as f:
            f.write(adapter_content)

        print("✅ PTZ适配器已创建")
        return True

    except Exception as e:
        print(f"❌ 创建适配器失败: {e}")
        return False

def start_monitoring_system():
    """启动完整监控系统"""
    print("🚀 启动完整监控系统...")

    start_cmd = [
        'python', 'integrated_camera_system.py',
        '--camera-ip', '192.168.31.146',
        '--camera-user', 'admin',
        '--camera-pass', 'admin123',
        '--rtsp', 'rtsp://admin:admin123@192.168.31.146/stream1'
    ]

    try:
        subprocess.run(start_cmd)
    except KeyboardInterrupt:
        print("\\n👋 用户停止了监控系统")
    except Exception as e:
        print(f"❌ 监控系统启动失败: {e}")

def show_menu():
    """显示主菜单"""
    print("\\n🎛️ 自动PTZ系统控制面板")
    print("=" * 50)
    print("1. 🤖 自动获取SessionId")
    print("2. 🎮 启动PTZ控制器")
    print("3. 📺 启动完整监控系统")
    print("4. 🔍 检查SessionId状态")
    print("5. ❌ 退出")

    choice = input("\\n请选择 (1-5): ").strip()
    return choice

def main():
    print("🎯 一键自动PTZ系统")
    print("=" * 60)
    print("完全自动化的SessionId管理和PTZ控制解决方案")
    print()

    while True:
        choice = show_menu()

        if choice == "1":
            print("\\n🤖 执行自动SessionId获取...")
            if run_auto_session_getter():
                print("✅ 自动获取完成！")
            else:
                print("❌ 自动获取失败")

        elif choice == "2":
            print("\\n🎮 启动PTZ控制器...")
            # 检查是否有有效的SessionId
            session_id = check_session_config()
            if session_id and test_existing_session(session_id):
                try:
                    subprocess.run(['python', 'auto_ptz_controller.py'])
                except KeyboardInterrupt:
                    print("\\n👋 PTZ控制器已停止")
            else:
                print("❌ 需要先获取有效的SessionId")
                print("💡 请选择选项1自动获取")

        elif choice == "3":
            print("\\n📺 启动完整监控系统...")
            session_id = check_session_config()
            if session_id and test_existing_session(session_id):
                if create_integrated_system(session_id):
                    start_monitoring_system()
            else:
                print("❌ 需要先获取有效的SessionId")
                print("💡 请选择选项1自动获取")

        elif choice == "4":
            print("\\n🔍 检查SessionId状态...")
            session_id = check_session_config()
            if session_id:
                if test_existing_session(session_id):
                    print("✅ SessionId有效，可以使用PTZ控制")
                else:
                    print("❌ SessionId已过期，需要重新获取")
            else:
                print("❌ 未找到SessionId配置")

        elif choice == "5":
            print("\\n👋 退出系统")
            break

        else:
            print("❌ 无效选择，请重新输入")

        input("\\n按回车继续...")

if __name__ == "__main__":
    main()