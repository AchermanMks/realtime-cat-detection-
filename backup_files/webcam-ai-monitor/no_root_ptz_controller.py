#!/usr/bin/env python3
"""
无需root权限的PTZ控制器
提供Web界面和命令行控制，不依赖keyboard库
"""

import subprocess
import json
import time
import threading
import webbrowser
import os
import requests
import ssl
from urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver

# 禁用SSL警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class LegacyHTTPSAdapter(HTTPAdapter):
    """支持传统SSL的适配器"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

class PTZController:
    """PTZ控制器 - 无需root权限"""

    def __init__(self, camera_ip="192.168.31.146", session_id="8E7EB2F6FE2304F134901333A05631A"):
        self.camera_ip = camera_ip
        self.session_id = session_id
        self.base_url = f"https://{camera_ip}"
        self.api_endpoint = "/ipc/grpc_cmd"

        # API endpoint configuration
        # Commands will be built dynamically to match working shell script format

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def send_command(self, method, params):
        """发送PTZ命令 - 通过Node.js代理"""

        # 映射方法到代理命令
        action_map = {
            ('ptz_move_start', 'panLeft', 120): 'left',
            ('ptz_move_start', 'panLeft', -120): 'right',
            ('ptz_move_start', 'tiltUp', 120): 'up',
            ('ptz_move_start', 'tiltUp', -120): 'down',
            ('ptz_move_stop', '', 0): 'stop',
            ('ptz_zoom_start', 'zoomIn', 120): 'zoom_in',
            ('ptz_zoom_start', 'zoomOut', 120): 'zoom_out',
        }

        # 确定动作类型
        action = 'stop'  # 默认动作

        if method == 'ptz_move_start':
            if 'panLeft' in params:
                action = 'left' if params['panLeft'] > 0 else 'right'
            elif 'tiltUp' in params:
                action = 'up' if params['tiltUp'] > 0 else 'down'
        elif method == 'ptz_move_stop':
            action = 'stop'
        elif method == 'ptz_zoom_start':
            if 'zoomIn' in params:
                action = 'zoom_in'
            elif 'zoomOut' in params:
                action = 'zoom_out'

        self.log(f"📤 {method}: {params} -> {action}")

        try:
            import urllib.request
            proxy_url = f"http://localhost:8899/ptz/{action}"

            req = urllib.request.Request(proxy_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                result = response.read().decode() == 'success'

            if result:
                self.log("✅ 命令成功")
                return True
            else:
                self.log("❌ 命令失败")
                return False

        except Exception as e:
            self.log(f"❌ 代理连接错误: {e}")
            return False

    # PTZ控制方法
    def move_left(self, speed=120):
        """向左移动"""
        return self.send_command("ptz_move_start", {"panLeft": speed})

    def move_right(self, speed=120):
        """向右移动"""
        return self.send_command("ptz_move_start", {"panLeft": -speed})

    def move_up(self, speed=120):
        """向上移动"""
        return self.send_command("ptz_move_start", {"tiltUp": speed})

    def move_down(self, speed=120):
        """向下移动"""
        return self.send_command("ptz_move_start", {"tiltUp": -speed})

    def stop_move(self):
        """停止移动"""
        return self.send_command("ptz_move_stop", {})

    def zoom_in(self, speed=120):
        """放大"""
        return self.send_command("ptz_zoom_start", {"zoomIn": speed})

    def zoom_out(self, speed=120):
        """缩小"""
        return self.send_command("ptz_zoom_start", {"zoomOut": speed})

    def stop_zoom(self):
        """停止缩放"""
        return self.send_command("ptz_zoom_stop", {})

class PTZWebHandler(BaseHTTPRequestHandler):
    """Web界面处理器"""

    def do_GET(self):
        """处理GET请求"""
        if self.path == '/':
            self.serve_control_page()
        elif self.path.startswith('/ptz/'):
            self.handle_ptz_command()
        else:
            self.send_error(404)

    def serve_control_page(self):
        """提供控制页面"""
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>PTZ实时控制 - 无需Root权限</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #fff;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        .ptz-panel {
            background: #2a2a2a;
            border-radius: 15px;
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .direction-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            grid-template-rows: 1fr 1fr 1fr;
            gap: 10px;
            max-width: 200px;
            margin: 20px auto;
        }
        .btn {
            background: #444;
            border: none;
            color: #fff;
            padding: 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
        }
        .btn:hover {
            background: #555;
            transform: scale(1.05);
        }
        .btn:active {
            background: #666;
            transform: scale(0.95);
        }
        .btn-up { grid-column: 2; grid-row: 1; }
        .btn-left { grid-column: 1; grid-row: 2; }
        .btn-stop { grid-column: 2; grid-row: 2; background: #666; }
        .btn-right { grid-column: 3; grid-row: 2; }
        .btn-down { grid-column: 2; grid-row: 3; }
        .zoom-controls {
            margin: 20px 0;
        }
        .zoom-btn {
            background: #0066cc;
            margin: 0 10px;
            padding: 10px 20px;
        }
        .status {
            background: #333;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            font-family: monospace;
        }
        .monitor-link {
            background: #006600;
            color: white;
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
            margin: 20px 0;
        }
        h1 { color: #00ff88; }
        h3 { color: #66ccff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 PTZ实时控制</h1>
        <p>无需Root权限，直接Web控制</p>

        <div class="ptz-panel">
            <h3>方向控制</h3>
            <div class="direction-grid">
                <button class="btn btn-up" onclick="ptzCommand('up')">▲</button>
                <button class="btn btn-left" onclick="ptzCommand('left')">◄</button>
                <button class="btn btn-stop" onclick="ptzCommand('stop')">⏹</button>
                <button class="btn btn-right" onclick="ptzCommand('right')">►</button>
                <button class="btn btn-down" onclick="ptzCommand('down')">▼</button>
            </div>

            <div class="zoom-controls">
                <h3>缩放控制</h3>
                <button class="btn zoom-btn" onclick="ptzCommand('zoom_in')">🔍+</button>
                <button class="btn zoom-btn" onclick="ptzCommand('zoom_out')">🔍-</button>
            </div>

            <div>
                <h3>快捷测试</h3>
                <button class="btn" onclick="autoTest()" style="background: #ff6600;">🎯 自动演示</button>
            </div>
        </div>

        <a href="http://localhost:8888" target="_blank" class="monitor-link">
            📺 打开视频监控界面
        </a>

        <div class="status" id="status">
            准备就绪 - 点击按钮控制摄像头
        </div>
    </div>

    <script>
        function ptzCommand(action) {
            updateStatus('发送命令: ' + action);

            fetch('/ptz/' + action)
                .then(response => response.text())
                .then(data => {
                    updateStatus('命令执行: ' + action + ' - ' + data);
                })
                .catch(error => {
                    updateStatus('错误: ' + error);
                });
        }

        function updateStatus(message) {
            const timestamp = new Date().toLocaleTimeString();
            document.getElementById('status').innerHTML = '[' + timestamp + '] ' + message;
        }

        function autoTest() {
            updateStatus('开始自动演示...');

            // 左右移动演示
            ptzCommand('left');
            setTimeout(() => ptzCommand('stop'), 2000);
            setTimeout(() => ptzCommand('right'), 3000);
            setTimeout(() => ptzCommand('stop'), 5000);
            setTimeout(() => updateStatus('自动演示完成'), 6000);
        }

        // 键盘控制 (可选)
        document.addEventListener('keydown', function(e) {
            switch(e.key.toLowerCase()) {
                case 'w':
                case 'arrowup':
                    ptzCommand('up');
                    break;
                case 's':
                case 'arrowdown':
                    ptzCommand('down');
                    break;
                case 'a':
                case 'arrowleft':
                    ptzCommand('left');
                    break;
                case 'd':
                case 'arrowright':
                    ptzCommand('right');
                    break;
                case ' ':
                    e.preventDefault();
                    ptzCommand('stop');
                    break;
            }
        });

        updateStatus('Web控制界面已加载，支持鼠标点击和键盘控制');
    </script>
</body>
</html>'''

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def handle_ptz_command(self):
        """处理PTZ命令 - 通过Node.js代理"""
        command = self.path.split('/')[-1]

        try:
            # 通过Node.js代理发送命令
            import urllib.request
            proxy_url = f"http://localhost:8899/ptz/{command}"

            req = urllib.request.Request(proxy_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                result = response.read().decode() == 'success'

        except Exception as e:
            print(f"代理请求失败: {e}")
            result = False

        response = 'success' if result else 'failed'

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        """禁用HTTP服务器日志"""
        pass

def start_web_server(port=9999):
    """启动Web服务器"""
    try:
        with socketserver.TCPServer(("", port), PTZWebHandler) as httpd:
            print(f"🌐 Web控制界面已启动: http://localhost:{port}")
            print("📺 视频监控界面: http://localhost:8888")
            print("🎮 在浏览器中打开控制界面，或按Ctrl+C停止")
            print()

            try:
                webbrowser.open(f'http://localhost:{port}')
            except:
                pass

            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 端口 {port} 已被占用，尝试其他端口...")
            start_web_server(port + 1)
        else:
            print(f"❌ 启动Web服务器失败: {e}")

def command_line_control():
    """命令行控制"""
    controller = PTZController()

    print("🎮 PTZ命令行控制")
    print("=" * 40)

    while True:
        print("\n📋 控制选项:")
        print("1) 向左移动    2) 向右移动")
        print("3) 向上移动    4) 向下移动")
        print("5) 停止移动    6) 放大")
        print("7) 缩小        8) 自动测试")
        print("9) 启动Web控制 0) 退出")

        try:
            choice = input("\n请选择 (0-9): ").strip()

            if choice == '1':
                controller.move_left()
            elif choice == '2':
                controller.move_right()
            elif choice == '3':
                controller.move_up()
            elif choice == '4':
                controller.move_down()
            elif choice == '5':
                controller.stop_move()
            elif choice == '6':
                controller.zoom_in()
            elif choice == '7':
                controller.zoom_out()
            elif choice == '8':
                print("🎯 自动测试...")
                controller.move_left()
                time.sleep(2)
                controller.stop_move()
                time.sleep(1)
                controller.move_right()
                time.sleep(2)
                controller.stop_move()
                print("✅ 自动测试完成")
            elif choice == '9':
                print("🌐 启动Web控制界面...")
                start_web_server()
                break
            elif choice == '0':
                print("👋 退出控制程序")
                break
            else:
                print("❌ 无效选择")

        except KeyboardInterrupt:
            print("\n👋 退出控制程序")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")

def main():
    """主函数"""
    print("🎮 PTZ控制器 - 无需Root权限版本")
    print("=" * 50)
    print()
    print("📋 选择控制模式:")
    print("1) Web界面控制 (推荐)")
    print("2) 命令行交互控制")
    print("3) 快速测试")

    try:
        choice = input("\n请选择 (1-3): ").strip()

        if choice == '1':
            start_web_server()
        elif choice == '2':
            command_line_control()
        elif choice == '3':
            print("🎯 执行快速测试...")
            controller = PTZController()
            controller.move_left()
            time.sleep(2)
            controller.stop_move()
            time.sleep(1)
            controller.move_right()
            time.sleep(2)
            controller.stop_move()
            print("✅ 快速测试完成")
        else:
            print("❌ 无效选择")

    except KeyboardInterrupt:
        print("\n👋 程序中断")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()