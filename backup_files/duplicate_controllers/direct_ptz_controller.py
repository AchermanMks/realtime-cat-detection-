#!/usr/bin/env python3
"""
直接HTTP API PTZ控制器
基于摄像头的Web管理API，更稳定可靠
"""

import requests
import json
import time
import urllib3
import ssl

# 禁用SSL警告（因为使用--insecure）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 允许不安全的SSL重新协商（针对旧设备）
import urllib3.util.ssl_
urllib3.util.ssl_.DEFAULT_CIPHERS += ':!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA'

class DirectPTZController:
    """直接通过HTTP API控制PTZ"""

    def __init__(self, camera_ip="192.168.31.146", session_id="1DD2682BD160DCAC9712EA6FC1452D6"):
        self.camera_ip = camera_ip
        self.session_id = session_id
        self.base_url = f"https://{camera_ip}/ipc/grpc_cmd"
        self.last_command_time = 0
        self.command_cooldown = 0.1  # 100ms冷却时间

        # 创建requests会话，配置SSL
        self.session = requests.Session()

        # 配置SSL适配器以支持旧设备
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context

        class LegacySSLAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)

        self.session.mount('https://', LegacySSLAdapter())

        # 公共请求头
        self.headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json; charset=UTF-8',
            'Origin': f'https://{camera_ip}',
            'Referer': f'https://{camera_ip}/ptzManager/ptzControl.html',
            'SessionId': session_id,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

    def send_ptz_command(self, method, params=None):
        """发送PTZ命令"""
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            return False

        if params is None:
            params = {"channelid": 0}

        data = {
            "method": method,
            "param": params
        }

        try:
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json=data,
                verify=False,  # 等同于--insecure
                timeout=3
            )

            self.last_command_time = current_time

            if response.status_code == 200:
                result = response.json()
                print(f"PTZ命令 {method}: 成功 - {result}")
                return True
            else:
                print(f"PTZ命令 {method}: HTTP错误 {response.status_code}")
                return False

        except Exception as e:
            print(f"PTZ命令 {method} 失败: {e}")
            return False

    def stop(self):
        """停止移动"""
        return self.send_ptz_command("ptz_move_stop")

    def up(self):
        """向上移动"""
        return self.send_ptz_command("ptz_move_up")

    def down(self):
        """向下移动"""
        return self.send_ptz_command("ptz_move_down")

    def left(self):
        """向左移动"""
        return self.send_ptz_command("ptz_move_left")

    def right(self):
        """向右移动"""
        return self.send_ptz_command("ptz_move_right")

    def zoom_in(self):
        """放大"""
        return self.send_ptz_command("ptz_zoom_in")

    def zoom_out(self):
        """缩小"""
        return self.send_ptz_command("ptz_zoom_out")

    def preset_goto(self, preset_id):
        """前往预设点"""
        params = {"channelid": 0, "preset": preset_id}
        return self.send_ptz_command("ptz_preset_goto", params)

    def preset_set(self, preset_id):
        """设置预设点"""
        params = {"channelid": 0, "preset": preset_id}
        return self.send_ptz_command("ptz_preset_set", params)

    def send_command(self, action):
        """兼容原有接口"""
        action_map = {
            'up': self.up,
            'down': self.down,
            'left': self.left,
            'right': self.right,
            'stop': self.stop,
            'zoom_in': self.zoom_in,
            'zoom_out': self.zoom_out,
        }

        if action in action_map:
            return action_map[action]()
        else:
            print(f"未知PTZ动作: {action}")
            return False

def test_ptz_controller():
    """测试PTZ控制器"""
    print("🎮 测试直接PTZ控制器")
    print("=" * 50)

    # 创建控制器实例
    ptz = DirectPTZController()

    # 测试各种命令
    commands = [
        ("停止", ptz.stop),
        ("上", ptz.up),
        ("停止", ptz.stop),
        ("下", ptz.down),
        ("停止", ptz.stop),
        ("左", ptz.left),
        ("停止", ptz.stop),
        ("右", ptz.right),
        ("停止", ptz.stop),
        ("放大", ptz.zoom_in),
        ("停止", ptz.stop),
        ("缩小", ptz.zoom_out),
        ("停止", ptz.stop),
    ]

    for name, cmd in commands:
        print(f"\n📡 执行命令: {name}")
        result = cmd()
        print(f"结果: {'✅ 成功' if result else '❌ 失败'}")
        time.sleep(1)  # 等待1秒

    print(f"\n🎉 测试完成")

if __name__ == "__main__":
    test_ptz_controller()