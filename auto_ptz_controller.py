#!/usr/bin/env python3
"""
自动获取SessionId的PTZ控制器
SessionId: 99FD7138E582CA2EE02C0537F55B8D1
"""

import subprocess, json, time, os
from datetime import datetime

os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

class AutoPTZController:
    def __init__(self):
        self.session_id = "99FD7138E582CA2EE02C0537F55B8D1"
        self.camera_ip = "192.168.31.146"

    def send_command(self, method, params=None):
        if params is None: params = {"channelid": 0}
        data = {"method": method, "param": params}

        cmd = ["curl", "-s", "--insecure", "--connect-timeout", "5",
               "-H", "Content-Type: application/json",
               "-H", f"SessionId: {self.session_id}",
               "-H", "Accept: application/json",
               "--data-raw", json.dumps(data),
               f"https://{self.camera_ip}/ipc/grpc_cmd"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            success = result.returncode == 0
            if success:
                try:
                    response = json.loads(result.stdout)
                    if 'error' in response and 'Invailed' in str(response.get('error', {})):
                        print("⚠️ SessionId可能已过期，请重新运行自动获取工具")
                        return False
                except: pass
            return success
        except: return False

    def move(self, direction, duration=0.3):
        movements = {
            'up': {"tiltUp": 120},
            'down': {"tiltUp": -120},
            'left': {"panLeft": 120},
            'right': {"panRight": 120}
        }

        if direction in movements:
            if self.send_command("ptz_move_start", {"channelid": 0, **movements[direction]}):
                time.sleep(duration)
                return self.send_command("ptz_move_stop")
        return False

    def stop(self):
        return self.send_command("ptz_move_stop")

def main():
    controller = AutoPTZController()

    print(f"🎮 自动PTZ控制器")
    print(f"SessionId: 99FD7138E582CA2E...")
    print(f"获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nw/s:上下, a/d:左右, x:停止, t:测试, q:退出")

    while True:
        try:
            cmd = input("\n命令: ").strip().lower()
            if cmd in ['q', 'quit', 'exit']: break
            elif cmd == 'w': controller.move('up')
            elif cmd == 's': controller.move('down')
            elif cmd == 'a': controller.move('left')
            elif cmd == 'd': controller.move('right')
            elif cmd == 'x': controller.stop()
            elif cmd == 't':
                print("🧪 测试连接...")
                if controller.stop(): print("✅ 连接正常")
                else: print("❌ 连接失败，SessionId可能已过期")
            else: print("❌ 未知命令")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    main()
