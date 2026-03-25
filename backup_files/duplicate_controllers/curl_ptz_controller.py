#!/usr/bin/env python3
"""
基于curl命令的小米摄像头PTZ控制器
直接复制curl命令的功能和参数
"""

import subprocess
import json
import time
import sys

class CurlPTZController:
    """直接使用curl命令控制PTZ"""

    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.session_id = None
        self.base_headers = [
            '-H', 'Accept: application/json, text/javascript, */*; q=0.01',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Connection: keep-alive',
            '-H', 'Content-Type: application/json; charset=UTF-8',
            '-H', f'Origin: https://{camera_ip}',
            '-H', f'Referer: https://{camera_ip}/ptzManager/ptzControl.html',
            '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            '-H', 'X-Requested-With: XMLHttpRequest',
            '--insecure'
        ]

    def log(self, message):
        """打印日志"""
        print(f"[PTZ] {message}")

    def run_curl(self, url, data=None, method='GET'):
        """执行curl命令"""
        cmd = ['curl', '-s']

        # 添加基本headers
        cmd.extend(self.base_headers)

        # 添加SessionId (如果有)
        if self.session_id:
            cmd.extend(['-H', f'SessionId: {self.session_id}'])

        # 添加数据
        if data:
            cmd.extend(['-H', 'Content-Type: application/json; charset=UTF-8'])
            cmd.extend(['--data-raw', json.dumps(data)])

        # 添加URL
        cmd.append(url)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"status": "success", "text": result.stdout}
            else:
                self.log(f"curl命令失败: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            self.log("curl命令超时")
            return None
        except Exception as e:
            self.log(f"执行curl命令出错: {e}")
            return None

    def login(self):
        """登录获取SessionId"""
        self.log(f"正在登录摄像头: {self.camera_ip}")

        login_url = f"https://{self.camera_ip}/ipc/login"
        login_data = {
            "username": self.username,
            "password": self.password
        }

        result = self.run_curl(login_url, login_data)

        if result and result.get('result') == 0:
            param = result.get('param', {})
            self.session_id = param.get('sessionid')
            if self.session_id:
                self.log(f"✅ 登录成功，SessionID: {self.session_id}")
                return True

        self.log("❌ 登录失败")
        return False

    def send_grpc_cmd(self, method, params):
        """发送gRPC命令"""
        if not self.session_id and not self.login():
            return None

        grpc_url = f"https://{self.camera_ip}/ipc/grpc_cmd"
        cmd_data = {
            "method": method,
            "param": {
                "channelid": 0,
                **params
            }
        }

        self.log(f"发送命令: {method} - {params}")
        result = self.run_curl(grpc_url, cmd_data)

        if result:
            if result.get('result') == 0:
                self.log("✅ 命令执行成功")
                return True
            else:
                self.log(f"❌ 命令执行失败: {result}")

        return False

    # PTZ控制命令 (基于实际curl命令)
    def move_up(self, speed=120):
        """向上移动"""
        return self.send_grpc_cmd("ptz_move_start", {"tiltUp": speed})

    def move_down(self, speed=120):
        """向下移动 (使用负的tiltUp值)"""
        return self.send_grpc_cmd("ptz_move_start", {"tiltUp": -speed})

    def move_left(self, speed=120):
        """向左移动"""
        return self.send_grpc_cmd("ptz_move_start", {"panLeft": speed})

    def move_right(self, speed=120):
        """向右移动"""
        return self.send_grpc_cmd("ptz_move_start", {"panRight": speed})

    def stop_move(self):
        """停止移动"""
        return self.send_grpc_cmd("ptz_move_stop", {})

    def zoom_in(self, speed=120):
        """放大"""
        return self.send_grpc_cmd("ptz_move_start", {"zoomIn": speed})

    def zoom_out(self, speed=120):
        """缩小"""
        return self.send_grpc_cmd("ptz_move_start", {"zoomOut": speed})

    def goto_preset(self, preset_id):
        """转到预设位"""
        return self.send_grpc_cmd("ptz_preset_goto", {"presetId": preset_id})

    def save_preset(self, preset_id):
        """保存预设位"""
        return self.send_grpc_cmd("ptz_preset_set", {"presetId": preset_id})

    def get_ptz_ability(self):
        """获取PTZ能力"""
        return self.send_grpc_cmd("ptz_ability_get", {})

    def get_ptz_presets(self):
        """获取预设位列表"""
        return self.send_grpc_cmd("ptz_presets_get", {})

    def get_move_status(self):
        """获取移动状态"""
        return self.send_grpc_cmd("ptz_move_stat_get", {})

    # 便捷控制方法
    def move_for_duration(self, direction, speed=120, duration=1.0):
        """移动指定时间后停止"""
        move_map = {
            'up': self.move_up,
            'down': self.move_down,
            'left': self.move_left,
            'right': self.move_right
        }

        if direction not in move_map:
            self.log(f"❌ 不支持的方向: {direction}")
            return False

        # 开始移动
        if move_map[direction](speed):
            self.log(f"🔄 向{direction}移动 {duration} 秒...")
            time.sleep(duration)
            return self.stop_move()

        return False

def print_curl_command_example():
    """打印curl命令示例"""
    print("\n📝 等效的curl命令示例:")
    print("=" * 60)

    examples = [
        ("登录", '''curl 'https://192.168.31.146/ipc/login' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  --data-raw '{"username":"admin","password":"admin123"}' \\
  --insecure'''),

        ("向上移动", '''curl 'https://192.168.31.146/ipc/grpc_cmd' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  -H 'SessionId: YOUR_SESSION_ID' \\
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}' \\
  --insecure'''),

        ("停止移动", '''curl 'https://192.168.31.146/ipc/grpc_cmd' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  -H 'SessionId: YOUR_SESSION_ID' \\
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}' \\
  --insecure''')
    ]

    for title, cmd in examples:
        print(f"\n🔸 {title}:")
        print(cmd)

def interactive_curl_control():
    """交互式curl控制"""
    print("🎮 基于curl的小米摄像头PTZ控制器")
    print("=" * 60)

    # 获取摄像头信息
    ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not ip:
        ip = "192.168.31.146"

    username = input("请输入用户名 (默认: admin): ").strip()
    if not username:
        username = "admin"

    password = input("请输入密码 (默认: admin123): ").strip()
    if not password:
        password = "admin123"

    # 创建控制器
    controller = CurlPTZController(ip, username, password)

    # 登录
    if not controller.login():
        print("❌ 登录失败，退出程序")
        return

    print("\n✅ 登录成功！")
    print("\n🎯 PTZ控制命令:")
    print("  w/s: 上/下移动")
    print("  a/d: 左/右移动")
    print("  q/e: 放大/缩小")
    print("  space: 停止移动")
    print("  1-8: 转到预设位")
    print("  p: 获取PTZ信息")
    print("  c: 显示curl命令示例")
    print("  h: 显示帮助")
    print("  quit: 退出")

    while True:
        try:
            cmd = input("\n请输入命令: ").strip().lower()

            if cmd in ['quit', 'exit']:
                print("👋 退出PTZ控制器")
                break
            elif cmd == 'h':
                print("\n🎯 控制命令:")
                print("  方向: w(上) s(下) a(左) d(右)")
                print("  缩放: q(放大) e(缩小)")
                print("  停止: space")
                print("  预设: 1-8")
                print("  信息: p")
                print("  示例: c")
            elif cmd == 'w':
                controller.move_for_duration('up', 120, 0.5)
            elif cmd == 's':
                controller.move_for_duration('down', 120, 0.5)
            elif cmd == 'a':
                controller.move_for_duration('left', 120, 0.5)
            elif cmd == 'd':
                controller.move_for_duration('right', 120, 0.5)
            elif cmd == 'q':
                controller.zoom_in(120)
                time.sleep(0.5)
                controller.stop_move()
            elif cmd == 'e':
                controller.zoom_out(120)
                time.sleep(0.5)
                controller.stop_move()
            elif cmd == ' ' or cmd == 'space':
                controller.stop_move()
            elif cmd.isdigit() and 1 <= int(cmd) <= 8:
                preset_id = int(cmd)
                controller.goto_preset(preset_id)
            elif cmd == 'p':
                print("\n📊 获取PTZ信息...")
                controller.get_ptz_ability()
                controller.get_ptz_presets()
                controller.get_move_status()
            elif cmd == 'c':
                print_curl_command_example()
            else:
                print("❌ 未知命令，输入 'h' 查看帮助")

        except KeyboardInterrupt:
            print("\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"❌ 执行错误: {e}")

def test_curl_commands():
    """测试curl命令"""
    print("🧪 测试curl PTZ命令")
    print("=" * 50)

    controller = CurlPTZController()

    if not controller.login():
        print("❌ 登录失败")
        return

    print("\n🎯 测试基本移动命令...")

    # 测试移动命令
    movements = [
        ("上", lambda: controller.move_for_duration('up', 60, 1)),
        ("下", lambda: controller.move_for_duration('down', 60, 1)),
        ("左", lambda: controller.move_for_duration('left', 60, 1)),
        ("右", lambda: controller.move_for_duration('right', 60, 1))
    ]

    for direction, move_func in movements:
        print(f"\n📍 测试{direction}移动...")
        result = move_func()
        print(f"   结果: {'✅ 成功' if result else '❌ 失败'}")

    print("\n✅ curl命令测试完成")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_curl_commands()
        elif sys.argv[1] == "curl":
            print_curl_command_example()
        elif sys.argv[1] == "interactive":
            interactive_curl_control()
        else:
            print("使用方法:")
            print("  python curl_ptz_controller.py                # 交互式控制")
            print("  python curl_ptz_controller.py test          # 测试模式")
            print("  python curl_ptz_controller.py curl          # 显示curl示例")
            print("  python curl_ptz_controller.py interactive   # 交互式模式")
    else:
        interactive_curl_control()

if __name__ == "__main__":
    main()