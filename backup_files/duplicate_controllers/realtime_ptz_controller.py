#!/usr/bin/env python3
"""
实时PTZ控制器
基于正确解析的协议，支持实时云台控制
"""

import subprocess
import json
import time
import threading
from datetime import datetime
import keyboard  # 需要安装: pip install keyboard

class RealtimePTZController:
    """实时PTZ控制器"""

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
            "-H", "Content-Type: application/json; charset=UTF-8",
            "-H", f"Origin: {self.base_url}",
            "-H", f"Referer: {self.base_url}/ptzManager/ptzControl.html",
            "-H", f"SessionId: {self.session_id}",
            "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "-H", "X-Requested-With: XMLHttpRequest"
        ]

        self.is_moving = False
        self.current_movement = None

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def send_command(self, method, params, silent=False):
        """发送PTZ命令"""
        payload = {
            "method": method,
            "param": {
                "channelid": 0,
                **params
            }
        }

        payload_json = json.dumps(payload)
        cmd = self.curl_base + ["--data-raw", payload_json]

        if not silent:
            self.log(f"📤 {method}: {params}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and not silent:
                response = result.stdout.strip()
                if response:
                    self.log(f"📥 {response}")
            return result.returncode == 0
        except Exception as e:
            if not silent:
                self.log(f"❌ 命令失败: {e}")
            return False

    # 基础移动控制 - 基于正确的协议
    def move_horizontal(self, speed):
        """水平移动 (正值向左，负值向右)"""
        return self.send_command("ptz_move_start", {"panLeft": speed})

    def move_vertical(self, speed):
        """垂直移动 (正值向上，负值向下)"""
        return self.send_command("ptz_move_start", {"tiltUp": speed})

    def move_diagonal(self, pan_speed, tilt_speed):
        """对角线移动"""
        return self.send_command("ptz_move_start", {"panLeft": pan_speed, "tiltUp": tilt_speed})

    def stop_move(self):
        """停止移动"""
        return self.send_command("ptz_move_stop", {})

    def zoom(self, speed):
        """缩放 (正值放大，负值缩小)"""
        if speed > 0:
            return self.send_command("ptz_zoom_start", {"zoomIn": speed})
        else:
            return self.send_command("ptz_zoom_start", {"zoomOut": -speed})

    def stop_zoom(self):
        """停止缩放"""
        return self.send_command("ptz_zoom_stop", {})

    # 便捷控制方法
    def move_left(self, speed=120):
        """向左移动"""
        return self.move_horizontal(speed)

    def move_right(self, speed=120):
        """向右移动"""
        return self.move_horizontal(-speed)

    def move_up(self, speed=120):
        """向上移动"""
        return self.move_vertical(speed)

    def move_down(self, speed=120):
        """向下移动"""
        return self.move_vertical(-speed)

    def zoom_in(self, speed=120):
        """放大"""
        return self.zoom(speed)

    def zoom_out(self, speed=120):
        """缩小"""
        return self.zoom(-speed)

    # 键盘控制
    def start_keyboard_control(self):
        """启动键盘控制"""
        print("🎮 键盘控制已启动!")
        print("=" * 40)
        print("📋 控制说明:")
        print("  ↑ W/Arrow Up    - 向上")
        print("  ↓ S/Arrow Down  - 向下")
        print("  ← A/Arrow Left  - 向左")
        print("  → D/Arrow Right - 向右")
        print("  + Plus          - 放大")
        print("  - Minus         - 缩小")
        print("  Space           - 停止移动")
        print("  Q               - 退出")
        print("=" * 40)
        print("按任意方向键开始控制...")

        try:
            while True:
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    self._handle_key_press(event.name)
                elif event.event_type == keyboard.KEY_UP:
                    self._handle_key_release(event.name)

        except KeyboardInterrupt:
            print("\n⏹️ 键盘控制已停止")
            self.stop_move()

    def _handle_key_press(self, key):
        """处理按键按下"""
        speed = 120

        if key in ['w', 'up']:
            self.move_up(speed)
            self.is_moving = True
            self.current_movement = 'up'

        elif key in ['s', 'down']:
            self.move_down(speed)
            self.is_moving = True
            self.current_movement = 'down'

        elif key in ['a', 'left']:
            self.move_left(speed)
            self.is_moving = True
            self.current_movement = 'left'

        elif key in ['d', 'right']:
            self.move_right(speed)
            self.is_moving = True
            self.current_movement = 'right'

        elif key == 'plus' or key == '=':
            self.zoom_in(speed)
            self.is_moving = True
            self.current_movement = 'zoom_in'

        elif key == 'minus':
            self.zoom_out(speed)
            self.is_moving = True
            self.current_movement = 'zoom_out'

        elif key == 'space':
            self.stop_move()
            self.stop_zoom()
            self.is_moving = False
            self.current_movement = None

        elif key == 'q':
            self.stop_move()
            exit(0)

    def _handle_key_release(self, key):
        """处理按键释放"""
        if key in ['w', 's', 'a', 'd', 'up', 'down', 'left', 'right', 'plus', 'minus', '=']:
            if self.is_moving:
                self.stop_move()
                self.stop_zoom()
                self.is_moving = False
                self.current_movement = None

    # 预设位控制
    def goto_preset(self, preset_id):
        """转到预设位"""
        return self.send_command("ptz_preset_goto", {"presetId": preset_id})

    def save_preset(self, preset_id):
        """保存预设位"""
        return self.send_command("ptz_preset_save", {"presetId": preset_id})

    def test_all_directions(self, speed=120, duration=2):
        """测试所有方向"""
        tests = [
            ("向左移动", lambda: self.move_left(speed)),
            ("向右移动", lambda: self.move_right(speed)),
            ("向上移动", lambda: self.move_up(speed)),
            ("向下移动", lambda: self.move_down(speed)),
            ("放大", lambda: self.zoom_in(speed)),
            ("缩小", lambda: self.zoom_out(speed)),
        ]

        self.log("🧪 开始测试所有方向...")

        for name, action in tests:
            self.log(f"🎯 测试: {name}")
            action()
            time.sleep(duration)
            self.stop_move()
            self.stop_zoom()
            time.sleep(0.5)

        self.log("✅ 所有方向测试完成")

def generate_web_interface():
    """生成Web控制界面"""

    html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>PTZ实时控制</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; text-align: center; }
        .ptz-control { background: #2a2a2a; border-radius: 10px; padding: 30px; margin: 20px 0; }
        .direction-pad { display: inline-block; position: relative; }
        .btn { background: #444; border: none; color: #fff; padding: 15px 20px; margin: 5px;
               border-radius: 8px; cursor: pointer; font-size: 18px; user-select: none; }
        .btn:hover { background: #555; }
        .btn:active { background: #666; transform: scale(0.95); }
        .btn-up { position: absolute; top: -50px; left: 50%; transform: translateX(-50%); }
        .btn-down { position: absolute; bottom: -50px; left: 50%; transform: translateX(-50%); }
        .btn-left { position: absolute; left: -70px; top: 50%; transform: translateY(-50%); }
        .btn-right { position: absolute; right: -70px; top: 50%; transform: translateY(-50%); }
        .btn-center { width: 60px; height: 60px; border-radius: 50%; background: #666; }
        .zoom-controls { margin: 20px 0; }
        .zoom-btn { background: #0066cc; margin: 0 10px; }
        .status { background: #333; border-radius: 8px; padding: 15px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 PTZ实时控制</h1>

        <div class="ptz-control">
            <h3>方向控制</h3>
            <div class="direction-pad">
                <button class="btn btn-up" onmousedown="startMove('up')" onmouseup="stopMove()">▲</button>
                <button class="btn btn-down" onmousedown="startMove('down')" onmouseup="stopMove()">▼</button>
                <button class="btn btn-left" onmousedown="startMove('left')" onmouseup="stopMove()">◄</button>
                <button class="btn btn-right" onmousedown="startMove('right')" onmouseup="stopMove()">►</button>
                <button class="btn btn-center" onclick="stopMove()">⏹</button>
            </div>

            <div class="zoom-controls">
                <h3>缩放控制</h3>
                <button class="btn zoom-btn" onmousedown="startZoom('in')" onmouseup="stopZoom()">🔍+</button>
                <button class="btn zoom-btn" onmousedown="startZoom('out')" onmouseup="stopZoom()">🔍-</button>
            </div>
        </div>

        <div class="status">
            <div id="status">准备就绪</div>
        </div>
    </div>

    <script>
        const API_BASE = 'https://192.168.31.146/ipc/grpc_cmd';
        const SESSION_ID = 'D1D66678A96617EF9555E42E67349E2';

        function sendCommand(method, params) {
            const payload = {
                method: method,
                param: { channelid: 0, ...params }
            };

            fetch(API_BASE, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'SessionId': SESSION_ID
                },
                body: JSON.stringify(payload)
            }).then(response => {
                document.getElementById('status').textContent = `${method}: ${JSON.stringify(params)}`;
            }).catch(error => {
                document.getElementById('status').textContent = `错误: ${error}`;
            });
        }

        function startMove(direction) {
            const speed = 120;
            switch(direction) {
                case 'up': sendCommand('ptz_move_start', {tiltUp: speed}); break;
                case 'down': sendCommand('ptz_move_start', {tiltUp: -speed}); break;
                case 'left': sendCommand('ptz_move_start', {panLeft: speed}); break;
                case 'right': sendCommand('ptz_move_start', {panLeft: -speed}); break;
            }
        }

        function stopMove() {
            sendCommand('ptz_move_stop', {});
        }

        function startZoom(direction) {
            const speed = 120;
            if (direction === 'in') {
                sendCommand('ptz_zoom_start', {zoomIn: speed});
            } else {
                sendCommand('ptz_zoom_start', {zoomOut: speed});
            }
        }

        function stopZoom() {
            sendCommand('ptz_zoom_stop', {});
        }

        // 键盘控制
        document.addEventListener('keydown', function(e) {
            switch(e.key) {
                case 'ArrowUp': case 'w': case 'W': startMove('up'); break;
                case 'ArrowDown': case 's': case 'S': startMove('down'); break;
                case 'ArrowLeft': case 'a': case 'A': startMove('left'); break;
                case 'ArrowRight': case 'd': case 'D': startMove('right'); break;
                case '+': case '=': startZoom('in'); break;
                case '-': startZoom('out'); break;
            }
        });

        document.addEventListener('keyup', function(e) {
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'W', 's', 'S', 'a', 'A', 'd', 'D'].includes(e.key)) {
                stopMove();
            }
            if (['+', '=', '-'].includes(e.key)) {
                stopZoom();
            }
        });
    </script>
</body>
</html>'''

    with open('ptz_web_control.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("🌐 Web控制界面已生成: ptz_web_control.html")
    print("   在浏览器中打开即可使用Web控制")

def main():
    """主函数"""
    print("🎮 实时PTZ控制器")
    print("=" * 50)

    controller = RealtimePTZController()

    print("📋 选择控制模式:")
    print("1. 键盘实时控制")
    print("2. 测试所有方向")
    print("3. 生成Web控制界面")
    print("4. 快速测试")

    try:
        choice = input("请选择 (1-4): ").strip()

        if choice == "1":
            print("准备启动键盘控制...")
            print("注意: 需要安装keyboard库: pip install keyboard")
            input("按Enter开始...")
            controller.start_keyboard_control()

        elif choice == "2":
            controller.test_all_directions()

        elif choice == "3":
            generate_web_interface()

        elif choice == "4":
            print("🎯 快速测试左右移动...")
            controller.move_left(120)
            time.sleep(2)
            controller.stop_move()
            time.sleep(1)
            controller.move_right(120)
            time.sleep(2)
            controller.stop_move()
            print("✅ 快速测试完成")

        else:
            print("无效选择")

    except KeyboardInterrupt:
        print("\n⏹️ 程序中断")
        controller.stop_move()
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()