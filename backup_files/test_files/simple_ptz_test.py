#!/usr/bin/env python3
"""
简单的PTZ控制测试 - 使用curl命令绕过SSL问题
"""

import subprocess
import json
import time
import sys

class SimplePTZController:
    """使用curl命令的简单PTZ控制器"""

    def __init__(self, camera_ip="192.168.31.146", session_id="1DD2682BD160DCAC9712EA6FC1452D6"):
        self.camera_ip = camera_ip
        self.session_id = session_id
        self.base_url = f"https://{camera_ip}/ipc/grpc_cmd"

    def log(self, message):
        """记录日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def send_curl_command(self, method, params=None):
        """使用curl发送PTZ命令"""
        if params is None:
            params = {"channelid": 0}

        data = {
            "method": method,
            "param": params
        }

        curl_cmd = [
            "curl", "-s",
            "--insecure",
            "--connect-timeout", "5",
            "-H", "Content-Type: application/json",
            "-H", f"SessionId: {self.session_id}",
            "-H", "Accept: application/json",
            "-H", f"Origin: https://{self.camera_ip}",
            "-H", f"Referer: https://{self.camera_ip}/ptzManager/ptzControl.html",
            "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "--data-raw", json.dumps(data),
            self.base_url
        ]

        try:
            self.log(f"📤 发送PTZ命令: {method}")
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    self.log(f"✅ 命令成功: {response}")
                    return True
                except:
                    if result.stdout.strip():
                        self.log(f"✅ 命令成功: {result.stdout.strip()}")
                        return True
                    else:
                        self.log("✅ 命令发送成功")
                        return True
            else:
                self.log(f"❌ curl命令失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.log("❌ 命令超时")
            return False
        except Exception as e:
            self.log(f"❌ 命令异常: {e}")
            return False

    def stop(self):
        """停止移动"""
        return self.send_curl_command("ptz_move_stop")

    def up(self, duration=0.5):
        """向上移动"""
        if self.send_curl_command("ptz_move_start", {"channelid": 0, "tiltUp": 120}):
            time.sleep(duration)
            return self.stop()
        return False

    def down(self, duration=0.5):
        """向下移动"""
        if self.send_curl_command("ptz_move_start", {"channelid": 0, "tiltUp": -120}):
            time.sleep(duration)
            return self.stop()
        return False

    def left(self, duration=0.5):
        """向左移动"""
        if self.send_curl_command("ptz_move_start", {"channelid": 0, "panLeft": 120}):
            time.sleep(duration)
            return self.stop()
        return False

    def right(self, duration=0.5):
        """向右移动"""
        if self.send_curl_command("ptz_move_start", {"channelid": 0, "panRight": 120}):
            time.sleep(duration)
            return self.stop()
        return False

    def test_connection(self):
        """测试连接"""
        self.log("🔍 测试连接...")
        return self.stop()  # 发送停止命令测试连接

def test_basic():
    """基础测试"""
    print("🧪 简单PTZ控制器测试")
    print("=" * 50)

    controller = SimplePTZController()

    print("🔍 测试连接...")
    if controller.test_connection():
        print("✅ 连接成功！")

        print("\n🎯 测试PTZ控制...")
        directions = [
            ("停止", controller.stop),
            ("上", lambda: controller.up(0.3)),
            ("下", lambda: controller.down(0.3)),
            ("左", lambda: controller.left(0.3)),
            ("右", lambda: controller.right(0.3))
        ]

        for name, func in directions:
            print(f"   📍 测试{name}...")
            result = func()
            print(f"   结果: {'✅ 成功' if result else '❌ 失败'}")
            time.sleep(0.5)

        print("\n✅ 基础测试完成")
    else:
        print("❌ 连接失败")
        print("\n🔧 故障排除:")
        print("   1. 检查摄像头IP是否正确")
        print("   2. 检查SessionId是否有效")
        print("   3. 确认网络连接正常")

def interactive_control():
    """交互式控制"""
    print("🎮 简单PTZ交互式控制器")
    print("=" * 60)

    # 获取摄像头信息
    ip = input("请输入摄像头IP地址 (默认: 192.168.31.146): ").strip()
    if not ip:
        ip = "192.168.31.146"

    print("\n💡 获取SessionId方法:")
    print("   1. 打开浏览器访问: https://{0}".format(ip))
    print("   2. 登录并进入PTZ控制页面")
    print("   3. 按F12->网络，执行PTZ操作，查看请求头的SessionId")
    print("   4. 或者用已知的SessionId: 1DD2682BD160DCAC9712EA6FC1452D6")

    session_id = input("\n请输入SessionId: ").strip()
    if not session_id:
        session_id = "1DD2682BD160DCAC9712EA6FC1452D6"
        print(f"使用默认SessionId: {session_id}")

    controller = SimplePTZController(ip, session_id)

    # 测试连接
    print("\n🔍 测试连接...")
    if not controller.test_connection():
        print("❌ 连接失败，请检查配置")
        return

    print("✅ 连接成功！")
    print("\n🎯 PTZ控制命令:")
    print("  w: 上移")
    print("  s: 下移")
    print("  a: 左移")
    print("  d: 右移")
    print("  x: 停止")
    print("  t: 连接测试")
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
            elif cmd == 'x':
                controller.stop()
            elif cmd == 't':
                controller.test_connection()
            else:
                print("❌ 未知命令，请重新输入")

        except KeyboardInterrupt:
            print("\n👋 退出程序")
            break
        except Exception as e:
            print(f"❌ 执行错误: {e}")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_basic()
        elif sys.argv[1] == "interactive":
            interactive_control()
        else:
            print("使用方法:")
            print("  python simple_ptz_test.py          # 交互式控制")
            print("  python simple_ptz_test.py test     # 基础测试")
            print("  python simple_ptz_test.py interactive # 交互式模式")
    else:
        interactive_control()

if __name__ == "__main__":
    main()