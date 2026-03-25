#!/usr/bin/env python3
"""
修复SSL问题的PTZ控制器
适配现代Python环境的SSL配置
"""

import requests
import json
import time
import urllib3
import ssl
import os

# 允许不安全的SSL重新协商
os.environ['OPENSSL_CONF'] = '/dev/null'

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FixedPTZController:
    """修复SSL问题的PTZ控制器"""

    def __init__(self, camera_ip="192.168.31.146", session_id="1DD2682BD160DCAC9712EA6FC1452D6"):
        self.camera_ip = camera_ip
        self.session_id = session_id
        self.base_url = f"https://{camera_ip}/ipc/grpc_cmd"
        self.last_command_time = 0
        self.command_cooldown = 0.1

        # 创建自定义SSL上下文
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        # 允许不安全的SSL重新协商
        self.ssl_context.options |= ssl.OP_LEGACY_SERVER_CONNECT

        # 设置更宽松的密码套件
        try:
            self.ssl_context.set_ciphers('ALL:@SECLEVEL=0')
        except:
            try:
                self.ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
            except:
                pass  # 如果都失败，使用默认设置

        # 创建requests会话
        self.session = self._create_session()

    def _create_session(self):
        """创建配置好的requests会话"""
        from requests.adapters import HTTPAdapter
        from urllib3.poolmanager import PoolManager

        class SSLAdapter(HTTPAdapter):
            def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
                pool_kwargs['ssl_context'] = self.ssl_context
                pool_kwargs['cert_reqs'] = 'CERT_NONE'
                pool_kwargs['check_hostname'] = False
                return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

        session = requests.Session()
        session.verify = False

        # 使用自定义SSL适配器
        ssl_adapter = SSLAdapter()
        ssl_adapter.ssl_context = self.ssl_context
        session.mount('https://', ssl_adapter)

        # 设置请求头
        session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json; charset=UTF-8',
            'Origin': f'https://{self.camera_ip}',
            'Referer': f'https://{self.camera_ip}/ptzManager/ptzControl.html',
            'SessionId': self.session_id,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        })

        return session

    def log(self, message):
        """记录日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def send_ptz_command(self, method, params=None):
        """发送PTZ命令"""
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            self.log(f"PTZ命令 {method}: 冷却中，跳过")
            return False

        if params is None:
            params = {"channelid": 0}

        data = {
            "method": method,
            "param": params
        }

        try:
            self.log(f"📤 发送PTZ命令: {method}")

            response = self.session.post(
                self.base_url,
                json=data,
                timeout=5
            )

            self.last_command_time = current_time

            if response.status_code == 200:
                try:
                    result = response.json()
                    self.log(f"✅ PTZ命令成功: {result}")
                    return True
                except:
                    self.log(f"✅ PTZ命令成功: {response.text[:100]}")
                    return True
            else:
                self.log(f"❌ PTZ命令失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            self.log(f"❌ PTZ命令异常: {e}")
            return False

    # PTZ控制方法
    def stop(self):
        """停止移动"""
        return self.send_ptz_command("ptz_move_stop")

    def up(self, duration=0.5):
        """向上移动"""
        if self.send_ptz_command("ptz_move_start", {"channelid": 0, "tiltUp": 120}):
            time.sleep(duration)
            return self.stop()
        return False

    def down(self, duration=0.5):
        """向下移动"""
        if self.send_ptz_command("ptz_move_start", {"channelid": 0, "tiltUp": -120}):
            time.sleep(duration)
            return self.stop()
        return False

    def left(self, duration=0.5):
        """向左移动"""
        if self.send_ptz_command("ptz_move_start", {"channelid": 0, "panLeft": 120}):
            time.sleep(duration)
            return self.stop()
        return False

    def right(self, duration=0.5):
        """向右移动"""
        if self.send_ptz_command("ptz_move_start", {"channelid": 0, "panRight": 120}):
            time.sleep(duration)
            return self.stop()
        return False

    def zoom_in(self, duration=0.5):
        """放大"""
        if self.send_ptz_command("ptz_move_start", {"channelid": 0, "zoomIn": 120}):
            time.sleep(duration)
            return self.send_ptz_command("ptz_move_stop")
        return False

    def zoom_out(self, duration=0.5):
        """缩小"""
        if self.send_ptz_command("ptz_move_start", {"channelid": 0, "zoomOut": 120}):
            time.sleep(duration)
            return self.send_ptz_command("ptz_move_stop")
        return False

    def test_all_directions(self):
        """测试所有方向"""
        self.log("🧪 开始测试所有PTZ方向...")

        directions = [
            ("上", self.up),
            ("下", self.down),
            ("左", self.left),
            ("右", self.right),
            ("放大", self.zoom_in),
            ("缩小", self.zoom_out)
        ]

        for name, func in directions:
            self.log(f"🎯 测试{name}移动...")
            result = func(0.5)
            self.log(f"   结果: {'✅ 成功' if result else '❌ 失败'}")
            time.sleep(0.5)

        self.log("✅ 所有方向测试完成")

def test_controller():
    """测试控制器"""
    print("🧪 修复版PTZ控制器测试")
    print("=" * 50)

    # 获取摄像头信息
    ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not ip:
        ip = "192.168.31.146"

    session_id = input("请输入SessionId (默认: 1DD2682BD160DCAC9712EA6FC1452D6): ").strip()
    if not session_id:
        session_id = "1DD2682BD160DCAC9712EA6FC1452D6"

    controller = FixedPTZController(ip, session_id)

    print(f"\n🎯 开始测试摄像头: {ip}")
    print(f"🔑 使用SessionId: {session_id[:16]}...")

    try:
        controller.test_all_directions()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

def interactive_control():
    """交互式控制"""
    print("🎮 修复版PTZ交互式控制器")
    print("=" * 60)

    # 获取摄像头信息
    ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not ip:
        ip = "192.168.31.146"

    session_id = input("请输入SessionId: ").strip()
    if not session_id:
        print("❌ 必须提供SessionId")
        return

    controller = FixedPTZController(ip, session_id)

    print(f"\n✅ 控制器初始化完成")
    print("\n🎯 PTZ控制命令:")
    print("  w/s: 上/下移动")
    print("  a/d: 左/右移动")
    print("  q/e: 放大/缩小")
    print("  x: 停止移动")
    print("  t: 测试所有方向")
    print("  quit: 退出")

    while True:
        try:
            cmd = input("\n请输入命令: ").strip().lower()

            if cmd in ['quit', 'exit', 'q']:
                break
            elif cmd == 'w':
                controller.up(0.3)
            elif cmd == 's':
                controller.down(0.3)
            elif cmd == 'a':
                controller.left(0.3)
            elif cmd == 'd':
                controller.right(0.3)
            elif cmd == 'q':
                controller.zoom_in(0.3)
            elif cmd == 'e':
                controller.zoom_out(0.3)
            elif cmd == 'x':
                controller.stop()
            elif cmd == 't':
                controller.test_all_directions()
            else:
                print("❌ 未知命令")

        except KeyboardInterrupt:
            print("\n👋 退出程序")
            break
        except Exception as e:
            print(f"❌ 执行错误: {e}")

def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_controller()
        elif sys.argv[1] == "interactive":
            interactive_control()
        else:
            print("使用方法:")
            print("  python fixed_ptz_controller.py          # 交互式控制")
            print("  python fixed_ptz_controller.py test     # 测试模式")
            print("  python fixed_ptz_controller.py interactive # 交互式模式")
    else:
        interactive_control()

if __name__ == "__main__":
    main()