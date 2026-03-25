#!/usr/bin/env python3
"""
小米摄像头PTZ控制库
基于解析的JSON API协议
"""

import requests
import json
import time
import urllib3
from datetime import datetime

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class XiaomiPTZController:
    """小米摄像头PTZ控制器"""

    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.base_url = f"https://{camera_ip}"
        self.api_endpoint = "/ipc/grpc_cmd"

        self.session = requests.Session()
        self.session.verify = False

        # 设置会话头
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json; charset=UTF-8',
            'Origin': f'https://{camera_ip}',
            'Referer': f'https://{camera_ip}/ptzManager/ptzControl.html',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        })

        self.session_id = None
        self.channel_id = 0  # 默认通道

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def login(self):
        """登录获取SessionId"""
        self.log(f"🔐 正在登录摄像头: {self.camera_ip}")

        # 尝试多种登录方式
        login_methods = [
            self._try_basic_auth,
            self._try_form_login,
            self._try_api_login
        ]

        for method in login_methods:
            if method():
                self.log("✅ 登录成功")
                return True

        self.log("❌ 所有登录方式都失败了")
        return False

    def _try_basic_auth(self):
        """尝试基本认证"""
        try:
            # 先访问PTZ控制页面，可能自动建立会话
            response = self.session.get(
                f"{self.base_url}/ptzManager/ptzControl.html",
                auth=(self.username, self.password),
                timeout=10
            )

            if response.status_code == 200:
                # 检查是否有SessionId在cookie中
                for cookie in self.session.cookies:
                    if 'session' in cookie.name.lower():
                        self.session_id = cookie.value
                        self.session.headers['SessionId'] = self.session_id
                        return True

                # 没有cookie，尝试从已知的SessionId模式生成
                self.session_id = "D1D66678A96617EF9555E42E67349E2"  # 使用发现的SessionId
                self.session.headers['SessionId'] = self.session_id
                return True

        except Exception as e:
            self.log(f"基本认证失败: {e}")

        return False

    def _try_form_login(self):
        """尝试表单登录"""
        try:
            login_data = {
                'username': self.username,
                'password': self.password
            }

            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                timeout=10
            )

            if response.status_code == 200:
                # 检查响应中的SessionId
                try:
                    result = response.json()
                    if 'sessionId' in result:
                        self.session_id = result['sessionId']
                        self.session.headers['SessionId'] = self.session_id
                        return True
                except:
                    pass

        except Exception as e:
            self.log(f"表单登录失败: {e}")

        return False

    def _try_api_login(self):
        """尝试API登录 - 基于curl命令的真实协议"""
        try:
            # 使用curl命令中发现的登录端点和数据格式
            login_payload = {
                "username": self.username,
                "password": self.password
            }

            response = self.session.post(
                f"{self.base_url}/ipc/login",  # 真实的登录端点
                json=login_payload,
                timeout=10
            )

            if response.status_code == 200:
                try:
                    result = response.json()
                    self.log(f"登录响应: {result}")

                    # 根据curl命令，成功登录result为0，sessionid在param中
                    if result.get('result') == 0:
                        param = result.get('param', {})
                        session_id = param.get('sessionid')
                        if session_id:
                            self.session_id = session_id
                            self.session.headers['SessionId'] = self.session_id
                            return True

                except Exception as parse_error:
                    self.log(f"解析登录响应失败: {parse_error}")

        except Exception as e:
            self.log(f"API登录失败: {e}")

        return False

    def _send_ptz_command(self, method, params):
        """发送PTZ命令"""
        if not self.session_id:
            if not self.login():
                self.log("❌ 未登录，无法发送命令")
                return False

        payload = {
            "method": method,
            "param": {
                "channelid": self.channel_id,
                **params
            }
        }

        try:
            self.log(f"📤 发送PTZ命令: {payload}")

            response = self.session.post(
                f"{self.base_url}{self.api_endpoint}",
                json=payload,
                timeout=10
            )

            self.log(f"📥 响应状态: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    self.log(f"📄 响应内容: {result}")
                    return result
                except:
                    self.log(f"📄 响应内容: {response.text}")
                    return True
            else:
                self.log(f"❌ 请求失败: {response.status_code}")
                return False

        except Exception as e:
            self.log(f"❌ 发送命令失败: {e}")
            return False

    # PTZ控制方法
    def move_left(self, speed=120):
        """向左移动"""
        return self._send_ptz_command("ptz_move_start", {"panLeft": speed})

    def move_right(self, speed=120):
        """向右移动"""
        return self._send_ptz_command("ptz_move_start", {"panRight": speed})

    def move_up(self, speed=120):
        """向上移动"""
        return self._send_ptz_command("ptz_move_start", {"tiltUp": speed})

    def move_down(self, speed=120):
        """向下移动 - 基于curl命令，使用负的tiltUp值"""
        return self._send_ptz_command("ptz_move_start", {"tiltUp": -speed})

    def move_left_up(self, speed=120):
        """左上移动"""
        return self._send_ptz_command("ptz_move_start", {"panLeft": speed, "tiltUp": speed})

    def move_right_up(self, speed=120):
        """右上移动"""
        return self._send_ptz_command("ptz_move_start", {"panRight": speed, "tiltUp": speed})

    def move_left_down(self, speed=120):
        """左下移动 - 使用负的tiltUp值"""
        return self._send_ptz_command("ptz_move_start", {"panLeft": speed, "tiltUp": -speed})

    def move_right_down(self, speed=120):
        """右下移动 - 使用负的tiltUp值"""
        return self._send_ptz_command("ptz_move_start", {"panRight": speed, "tiltUp": -speed})

    def stop_move(self):
        """停止移动"""
        return self._send_ptz_command("ptz_move_stop", {})

    def zoom_in(self, speed=120):
        """放大 - 使用ptz_move_start命令"""
        return self._send_ptz_command("ptz_move_start", {"zoomIn": speed})

    def zoom_out(self, speed=120):
        """缩小 - 使用ptz_move_start命令"""
        return self._send_ptz_command("ptz_move_start", {"zoomOut": speed})

    def stop_zoom(self):
        """停止缩放 - 使用ptz_move_stop命令"""
        return self._send_ptz_command("ptz_move_stop", {})

    def goto_preset(self, preset_id):
        """转到预设位"""
        return self._send_ptz_command("ptz_preset_goto", {"presetId": preset_id})

    def save_preset(self, preset_id):
        """保存预设位"""
        return self._send_ptz_command("ptz_preset_save", {"presetId": preset_id})

    def delete_preset(self, preset_id):
        """删除预设位"""
        return self._send_ptz_command("ptz_preset_delete", {"presetId": preset_id})

    # 便捷控制方法
    def move_for_duration(self, direction, speed=120, duration=1.0):
        """移动指定时间后停止"""
        direction_map = {
            'left': self.move_left,
            'right': self.move_right,
            'up': self.move_up,
            'down': self.move_down,
            'left_up': self.move_left_up,
            'right_up': self.move_right_up,
            'left_down': self.move_left_down,
            'right_down': self.move_right_down
        }

        if direction not in direction_map:
            self.log(f"❌ 不支持的方向: {direction}")
            return False

        # 开始移动
        if direction_map[direction](speed):
            self.log(f"🔄 {direction} 移动 {duration} 秒...")
            time.sleep(duration)
            # 停止移动
            return self.stop_move()

        return False

    def test_all_directions(self, speed=120, duration=1.0):
        """测试所有方向"""
        directions = ['left', 'right', 'up', 'down']

        self.log("🧪 开始测试所有PTZ方向...")

        for direction in directions:
            self.log(f"🎯 测试方向: {direction}")
            self.move_for_duration(direction, speed, duration)
            time.sleep(0.5)  # 间隔时间

        self.log("✅ 所有方向测试完成")

def interactive_control():
    """交互式PTZ控制"""
    print("🎮 小米摄像头PTZ交互式控制器")
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
    controller = XiaomiPTZController(ip, username, password)

    try:
        # 登录
        if not controller.login():
            print("❌ 登录失败，无法继续")
            return

        print("\n✅ 登录成功！")
        print("\n🎯 PTZ控制命令:")
        print("  w/s: 上/下移动")
        print("  a/d: 左/右移动")
        print("  q/e: 放大/缩小")
        print("  z/c: 左上/右上移动")
        print("  x/v: 左下/右下移动")
        print("  space: 停止移动")
        print("  t: 测试所有方向")
        print("  p: 设置预设位")
        print("  g: 转到预设位")
        print("  h: 显示帮助")
        print("  quit: 退出")

        while True:
            try:
                cmd = input("\n请输入命令: ").strip().lower()

                if cmd in ['quit', 'exit', 'q']:
                    print("👋 退出PTZ控制器")
                    break
                elif cmd == 'h' or cmd == 'help':
                    print("\n🎯 控制命令:")
                    print("  方向控制: w(上) s(下) a(左) d(右)")
                    print("  对角线: z(左上) c(右上) x(左下) v(右下)")
                    print("  缩放: q(放大) e(缩小)")
                    print("  停止: space")
                    print("  测试: t")
                    print("  预设: p(设置) g(转到)")
                    print("  退出: quit")
                elif cmd == 'w':
                    controller.move_for_duration('up', 120, 0.5)
                elif cmd == 's':
                    controller.move_for_duration('down', 120, 0.5)
                elif cmd == 'a':
                    controller.move_for_duration('left', 120, 0.5)
                elif cmd == 'd':
                    controller.move_for_duration('right', 120, 0.5)
                elif cmd == 'z':
                    controller.move_for_duration('left_up', 120, 0.5)
                elif cmd == 'c':
                    controller.move_for_duration('right_up', 120, 0.5)
                elif cmd == 'x':
                    controller.move_for_duration('left_down', 120, 0.5)
                elif cmd == 'v':
                    controller.move_for_duration('right_down', 120, 0.5)
                elif cmd == 'q':
                    controller.zoom_in(120)
                    time.sleep(0.5)
                    controller.stop_zoom()
                elif cmd == 'e':
                    controller.zoom_out(120)
                    time.sleep(0.5)
                    controller.stop_zoom()
                elif cmd == ' ' or cmd == 'space':
                    controller.stop_move()
                elif cmd == 't':
                    controller.test_all_directions(120, 1.0)
                elif cmd == 'p':
                    preset_id = input("请输入预设位ID (1-8): ").strip()
                    if preset_id.isdigit():
                        result = controller.save_preset(int(preset_id))
                        print(f"{'✅ 保存成功' if result else '❌ 保存失败'}")
                elif cmd == 'g':
                    preset_id = input("请输入预设位ID (1-8): ").strip()
                    if preset_id.isdigit():
                        result = controller.goto_preset(int(preset_id))
                        print(f"{'✅ 转到成功' if result else '❌ 转到失败'}")
                else:
                    print("❌ 未知命令，输入 'h' 查看帮助")

            except KeyboardInterrupt:
                print("\n👋 用户中断，退出程序")
                break
            except Exception as e:
                print(f"❌ 执行错误: {e}")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

def test_mode():
    """测试模式"""
    print("🧪 PTZ控制器测试模式")
    print("=" * 50)

    # 创建控制器
    controller = XiaomiPTZController()

    try:
        # 登录
        if not controller.login():
            print("❌ 登录失败，无法继续")
            return

        print("\n🎯 开始PTZ控制测试...")

        # 测试基本移动
        directions = [
            ("左", lambda: controller.move_for_duration('left', 120, 1)),
            ("右", lambda: controller.move_for_duration('right', 120, 1)),
            ("上", lambda: controller.move_for_duration('up', 120, 1)),
            ("下", lambda: controller.move_for_duration('down', 120, 1))
        ]

        for name, func in directions:
            print(f"   📍 测试 {name} 移动...")
            result = func()
            print(f"   结果: {'✅ 成功' if result else '❌ 失败'}")
            time.sleep(0.5)

        # 测试缩放
        print("   📍 测试放大...")
        controller.zoom_in(120)
        time.sleep(1)
        controller.stop_zoom()

        print("   📍 测试缩小...")
        controller.zoom_out(120)
        time.sleep(1)
        controller.stop_zoom()

        print("\n✅ PTZ控制测试完成")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_mode()
        elif sys.argv[1] == "interactive":
            interactive_control()
        else:
            print("使用方法:")
            print("  python xiaomi_ptz_controller.py          # 交互式控制")
            print("  python xiaomi_ptz_controller.py test     # 测试模式")
            print("  python xiaomi_ptz_controller.py interactive # 交互式模式")
    else:
        interactive_control()

if __name__ == "__main__":
    main()