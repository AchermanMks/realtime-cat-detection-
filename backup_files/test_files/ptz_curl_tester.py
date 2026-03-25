#!/usr/bin/env python3
"""
PTZ cURL测试工具
基于解析的协议生成各种PTZ控制命令
"""

import subprocess
import json
import time
from datetime import datetime

class PTZCurlTester:
    """PTZ cURL测试器"""

    def __init__(self, camera_ip="192.168.31.146", session_id="D1D66678A96617EF9555E42E67349E2"):
        self.camera_ip = camera_ip
        self.session_id = session_id
        self.base_url = f"https://{camera_ip}"
        self.api_endpoint = "/ipc/grpc_cmd"

        # 基础curl命令模板
        self.curl_base = [
            "curl", "-s", "--insecure",
            f"{self.base_url}{self.api_endpoint}",
            "-H", "Accept: application/json, text/javascript, */*; q=0.01",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-H", "Connection: keep-alive",
            "-H", "Content-Type: application/json; charset=UTF-8",
            "-H", f"Origin: {self.base_url}",
            "-H", f"Referer: {self.base_url}/ptzManager/ptzControl.html",
            "-H", "Sec-Fetch-Dest: empty",
            "-H", "Sec-Fetch-Mode: cors",
            "-H", "Sec-Fetch-Site: same-origin",
            "-H", f"SessionId: {self.session_id}",
            "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "-H", "X-Requested-With: XMLHttpRequest"
        ]

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def send_ptz_command(self, method, params, channel_id=0):
        """发送PTZ命令"""
        payload = {
            "method": method,
            "param": {
                "channelid": channel_id,
                **params
            }
        }

        payload_json = json.dumps(payload)
        cmd = self.curl_base + ["--data-raw", payload_json]

        self.log(f"📤 发送命令: {method} - {params}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                response = result.stdout.strip()
                if response:
                    self.log(f"📥 响应: {response}")
                    try:
                        parsed = json.loads(response)
                        return parsed
                    except:
                        return {"raw_response": response}
                else:
                    self.log("📥 响应为空")
                    return {"status": "empty_response"}
            else:
                error = result.stderr.strip()
                self.log(f"❌ 命令失败: {error}")
                return {"error": error}

        except subprocess.TimeoutExpired:
            self.log("⏰ 命令超时")
            return {"error": "timeout"}
        except Exception as e:
            self.log(f"❌ 执行错误: {e}")
            return {"error": str(e)}

    def move_left(self, speed=120):
        """向左移动"""
        return self.send_ptz_command("ptz_move_start", {"panLeft": speed})

    def move_right(self, speed=120):
        """向右移动"""
        return self.send_ptz_command("ptz_move_start", {"panRight": speed})

    def move_up(self, speed=120):
        """向上移动"""
        return self.send_ptz_command("ptz_move_start", {"tiltUp": speed})

    def move_down(self, speed=120):
        """向下移动"""
        return self.send_ptz_command("ptz_move_start", {"tiltDown": speed})

    def stop_move(self):
        """停止移动"""
        return self.send_ptz_command("ptz_move_stop", {})

    def zoom_in(self, speed=120):
        """放大"""
        return self.send_ptz_command("ptz_zoom_start", {"zoomIn": speed})

    def zoom_out(self, speed=120):
        """缩小"""
        return self.send_ptz_command("ptz_zoom_start", {"zoomOut": speed})

    def stop_zoom(self):
        """停止缩放"""
        return self.send_ptz_command("ptz_zoom_stop", {})

    def test_basic_movements(self):
        """测试基本移动"""
        self.log("🧪 开始测试基本PTZ移动...")

        movements = [
            ("向左", lambda: self.move_left(120)),
            ("停止", lambda: self.stop_move()),
            ("向右", lambda: self.move_right(120)),
            ("停止", lambda: self.stop_move()),
            ("向上", lambda: self.move_up(120)),
            ("停止", lambda: self.stop_move()),
            ("向下", lambda: self.move_down(120)),
            ("停止", lambda: self.stop_move()),
        ]

        results = []
        for name, action in movements:
            self.log(f"🎯 测试: {name}")
            result = action()
            results.append((name, result))
            time.sleep(1)  # 每个动作间隔1秒

        return results

    def test_zoom_functions(self):
        """测试缩放功能"""
        self.log("🔍 开始测试缩放功能...")

        zoom_tests = [
            ("放大", lambda: self.zoom_in(120)),
            ("停止缩放", lambda: self.stop_zoom()),
            ("缩小", lambda: self.zoom_out(120)),
            ("停止缩放", lambda: self.stop_zoom()),
        ]

        results = []
        for name, action in zoom_tests:
            self.log(f"🎯 测试: {name}")
            result = action()
            results.append((name, result))
            time.sleep(1)

        return results

    def generate_test_commands(self):
        """生成完整的测试命令脚本"""
        commands = []

        # 基本移动命令
        basic_commands = [
            ("向左移动", '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'),
            ("向右移动", '{"method":"ptz_move_start","param":{"channelid":0,"panRight":120}}'),
            ("向上移动", '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}'),
            ("向下移动", '{"method":"ptz_move_start","param":{"channelid":0,"tiltDown":120}}'),
            ("停止移动", '{"method":"ptz_move_stop","param":{"channelid":0}}'),
            ("放大", '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomIn":120}}'),
            ("缩小", '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomOut":120}}'),
            ("停止缩放", '{"method":"ptz_zoom_stop","param":{"channelid":0}}'),
        ]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_file = f"ptz_complete_test_{timestamp}.sh"

        with open(script_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# 完整PTZ控制测试脚本\n")
            f.write(f"# 生成时间: {datetime.now()}\n\n")

            f.write("CAMERA_IP=\"192.168.31.146\"\n")
            f.write(f"SESSION_ID=\"{self.session_id}\"\n")
            f.write("BASE_URL=\"https://$CAMERA_IP/ipc/grpc_cmd\"\n\n")

            f.write("echo '🎮 小米摄像头PTZ控制测试'\n")
            f.write("echo '============================'\n")
            f.write("echo ''\n\n")

            for name, payload in basic_commands:
                f.write(f"echo '🎯 {name}'\n")
                f.write("curl --insecure -s \\\n")
                f.write("  '$BASE_URL' \\\n")
                f.write("  -H 'Accept: application/json, text/javascript, */*; q=0.01' \\\n")
                f.write("  -H 'Content-Type: application/json; charset=UTF-8' \\\n")
                f.write("  -H 'Origin: https://$CAMERA_IP' \\\n")
                f.write("  -H 'Referer: https://$CAMERA_IP/ptzManager/ptzControl.html' \\\n")
                f.write("  -H 'SessionId: $SESSION_ID' \\\n")
                f.write(f"  --data-raw '{payload}'\n")
                f.write("echo ''\n")
                f.write("sleep 2\n\n")

        self.log(f"📋 测试脚本已生成: {script_file}")
        return script_file

def main():
    """主函数"""
    print("🎮 PTZ cURL测试工具")
    print("=" * 50)

    tester = PTZCurlTester()

    try:
        print("📋 选择测试选项:")
        print("1. 测试基本移动")
        print("2. 测试缩放功能")
        print("3. 生成完整测试脚本")
        print("4. 运行单个命令测试")

        choice = input("请选择 (1-4): ").strip()

        if choice == "1":
            results = tester.test_basic_movements()
            print("\n📊 测试结果:")
            for name, result in results:
                status = "✅" if not result.get('error') else "❌"
                print(f"  {status} {name}: {result}")

        elif choice == "2":
            results = tester.test_zoom_functions()
            print("\n📊 缩放测试结果:")
            for name, result in results:
                status = "✅" if not result.get('error') else "❌"
                print(f"  {status} {name}: {result}")

        elif choice == "3":
            script_file = tester.generate_test_commands()
            print(f"\n✅ 测试脚本已生成: {script_file}")
            print("运行方法:")
            print(f"  chmod +x {script_file}")
            print(f"  ./{script_file}")

        elif choice == "4":
            print("🎯 测试向左移动命令...")
            result = tester.move_left(120)
            print(f"结果: {result}")

            time.sleep(2)

            print("🎯 测试停止移动命令...")
            result = tester.stop_move()
            print(f"结果: {result}")

        else:
            print("无效选择")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()