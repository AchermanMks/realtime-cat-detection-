#!/usr/bin/env python3
"""
RTSP摄像头实时显示器
支持多种显示模式和PTZ控制集成
"""

import cv2
import time
import threading
import argparse
import sys
import numpy as np
from flask import Flask, render_template_string, Response
import requests
import urllib3

# 禁用SSL警告 (用于PTZ控制)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RTSPViewer:
    def __init__(self, rtsp_url, ptz_ip=None):
        self.rtsp_url = rtsp_url
        self.ptz_ip = ptz_ip
        self.cap = None
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 统计信息
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.display_fps = 0
        self.total_frames = 0
        self.start_time = time.time()

        # PTZ控制相关
        self.ptz_session = None
        self.ptz_session_id = None

    def connect_rtsp(self):
        """连接RTSP摄像头"""
        print(f"📡 正在连接RTSP摄像头: {self.rtsp_url}")

        # 尝试不同的后端
        backends = [
            (cv2.CAP_FFMPEG, "FFMPEG"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_ANY, "默认")
        ]

        for backend, name in backends:
            try:
                print(f"🔧 尝试{name}后端...")
                cap = cv2.VideoCapture(self.rtsp_url, backend)

                # 设置参数
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少延迟
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 连接超时
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)   # 读取超时

                if cap.isOpened():
                    # 测试读取
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        h, w = test_frame.shape[:2]
                        fps = cap.get(cv2.CAP_PROP_FPS) or 25

                        print(f"✅ RTSP连接成功!")
                        print(f"   - 后端: {name}")
                        print(f"   - 分辨率: {w}x{h}")
                        print(f"   - 帧率: {fps}")

                        self.cap = cap
                        return True
                    else:
                        cap.release()
                else:
                    cap.release()

            except Exception as e:
                print(f"❌ {name}后端连接失败: {e}")

        print("❌ 所有RTSP连接尝试都失败了")
        return False

    def init_ptz_control(self):
        """初始化PTZ控制"""
        if not self.ptz_ip:
            return False

        try:
            self.ptz_session = requests.Session()
            self.ptz_session.verify = False

            # 登录获取SessionId
            login_url = f"https://{self.ptz_ip}/ipc/login"
            login_data = {"username": "admin", "password": "admin123"}

            response = self.ptz_session.post(login_url, json=login_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('result') == 0:
                    self.ptz_session_id = result.get('param', {}).get('sessionid')
                    if self.ptz_session_id:
                        self.ptz_session.headers.update({
                            'SessionId': self.ptz_session_id,
                            'Content-Type': 'application/json'
                        })
                        print(f"✅ PTZ控制初始化成功: {self.ptz_ip}")
                        return True

            print(f"❌ PTZ控制初始化失败")
            return False

        except Exception as e:
            print(f"❌ PTZ控制初始化错误: {e}")
            return False

    def send_ptz_command(self, method, params):
        """发送PTZ命令"""
        if not self.ptz_session_id:
            return False

        try:
            cmd_url = f"https://{self.ptz_ip}/ipc/grpc_cmd"
            cmd_data = {
                "method": method,
                "param": {"channelid": 0, **params}
            }

            response = self.ptz_session.post(cmd_url, json=cmd_data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                return result.get("result") == 0
        except Exception as e:
            print(f"PTZ命令发送失败: {e}")

        return False

    def capture_frames(self):
        """视频帧捕获线程"""
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # 更新统计
                    self.total_frames += 1
                    self.fps_counter += 1
                    current_time = time.time()

                    # 计算FPS
                    if current_time - self.last_fps_time >= 1.0:
                        self.display_fps = self.fps_counter / (current_time - self.last_fps_time)
                        self.fps_counter = 0
                        self.last_fps_time = current_time

                    # 在画面上显示信息
                    self.draw_overlay(frame)

                    # 存储当前帧
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                else:
                    print("⚠️ 无法读取RTSP帧")
                    time.sleep(1)
            else:
                time.sleep(1)

    def draw_overlay(self, frame):
        """在画面上绘制信息覆盖层"""
        h, w = frame.shape[:2]

        # 半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # 文字信息
        font = cv2.FONT_HERSHEY_SIMPLEX
        color = (0, 255, 0)

        # RTSP信息
        cv2.putText(frame, f"RTSP: {self.rtsp_url}", (20, 30), font, 0.5, color, 1)
        cv2.putText(frame, f"FPS: {self.display_fps:.1f}", (20, 50), font, 0.5, color, 1)
        cv2.putText(frame, f"Frames: {self.total_frames}", (20, 70), font, 0.5, color, 1)

        # 运行时间
        uptime = time.time() - self.start_time
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
        cv2.putText(frame, f"Uptime: {uptime_str}", (20, 90), font, 0.5, color, 1)

        # PTZ状态
        if self.ptz_ip:
            ptz_status = "Connected" if self.ptz_session_id else "Disconnected"
            cv2.putText(frame, f"PTZ: {ptz_status}", (20, 110), font, 0.5, color, 1)

        # 时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (w-200, h-20), font, 0.5, (255, 255, 255), 1)

    def get_frame_jpeg(self):
        """获取JPEG编码的帧"""
        with self.frame_lock:
            if self.current_frame is not None:
                ret, buffer = cv2.imencode('.jpg', self.current_frame,
                                         [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    return buffer.tobytes()
        return None

    def start_capture(self):
        """开始捕获"""
        if not self.connect_rtsp():
            return False

        # 初始化PTZ控制
        if self.ptz_ip:
            self.init_ptz_control()

        self.running = True
        self.start_time = time.time()

        # 启动捕获线程
        capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        capture_thread.start()

        return True

    def stop_capture(self):
        """停止捕获"""
        self.running = False
        if self.cap:
            self.cap.release()

# Flask Web界面
app = Flask(__name__)
viewer = None

# Web界面HTML
WEB_INTERFACE = """
<!DOCTYPE html>
<html>
<head>
    <title>RTSP摄像头实时显示</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        .video-container {
            text-align: center;
            margin-bottom: 20px;
        }
        .video-stream {
            max-width: 100%;
            border: 2px solid #333;
            border-radius: 8px;
        }
        .controls {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .control-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            max-width: 300px;
            margin: 0 auto;
        }
        .control-btn {
            background: #444;
            border: none;
            color: white;
            padding: 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .control-btn:hover {
            background: #555;
        }
        .control-btn:active {
            background: #666;
        }
        .empty {
            visibility: hidden;
        }
        .info {
            background: #333;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        h1 { color: #00ff88; }
        h3 { color: #00ff88; margin-top: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📺 RTSP摄像头实时显示</h1>
        </div>

        <div class="video-container">
            <img src="/video_feed" class="video-stream" alt="RTSP摄像头画面">
        </div>

        {% if ptz_enabled %}
        <div class="controls">
            <h3>🎮 PTZ控制</h3>
            <div class="control-grid">
                <div class="empty"></div>
                <button class="control-btn" onmousedown="ptzMove('up')" onmouseup="ptzStop()">⬆️</button>
                <div class="empty"></div>

                <button class="control-btn" onmousedown="ptzMove('left')" onmouseup="ptzStop()">⬅️</button>
                <button class="control-btn" onclick="ptzStop()">⏹️</button>
                <button class="control-btn" onmousedown="ptzMove('right')" onmouseup="ptzStop()">➡️</button>

                <div class="empty"></div>
                <button class="control-btn" onmousedown="ptzMove('down')" onmouseup="ptzStop()">⬇️</button>
                <div class="empty"></div>
            </div>
            <br>
            <div style="text-align: center;">
                <button class="control-btn" onmousedown="ptzZoom('in')" onmouseup="ptzStop()">🔍 放大</button>
                <button class="control-btn" onmousedown="ptzZoom('out')" onmouseup="ptzStop()">🔍 缩小</button>
            </div>
        </div>
        {% endif %}

        <div class="info">
            <h3>ℹ️ 使用说明</h3>
            <p><strong>RTSP URL:</strong> {{ rtsp_url }}</p>
            {% if ptz_enabled %}
            <p><strong>PTZ控制:</strong> 启用 ({{ ptz_ip }})</p>
            <p><strong>控制方式:</strong> 按住方向按钮进行移动，松开自动停止</p>
            {% else %}
            <p><strong>PTZ控制:</strong> 未启用</p>
            {% endif %}
            <p><strong>快捷键:</strong> W(上) S(下) A(左) D(右) Q(放大) E(缩小) 空格(停止)</p>
        </div>
    </div>

    <script>
        {% if ptz_enabled %}
        function ptzMove(direction) {
            fetch('/ptz/move', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({direction: direction})
            });
        }

        function ptzZoom(type) {
            fetch('/ptz/zoom', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type: type})
            });
        }

        function ptzStop() {
            fetch('/ptz/stop', {method: 'POST'});
        }

        // 键盘控制
        document.addEventListener('keydown', function(e) {
            switch(e.key.toLowerCase()) {
                case 'w': ptzMove('up'); break;
                case 's': ptzMove('down'); break;
                case 'a': ptzMove('left'); break;
                case 'd': ptzMove('right'); break;
                case 'q': ptzZoom('in'); break;
                case 'e': ptzZoom('out'); break;
                case ' ': e.preventDefault(); ptzStop(); break;
            }
        });

        document.addEventListener('keyup', function(e) {
            if (['w','s','a','d','q','e'].includes(e.key.toLowerCase())) {
                ptzStop();
            }
        });
        {% endif %}
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    return render_template_string(WEB_INTERFACE,
                                rtsp_url=viewer.rtsp_url,
                                ptz_enabled=viewer.ptz_ip is not None,
                                ptz_ip=viewer.ptz_ip)

@app.route('/video_feed')
def video_feed():
    """视频流"""
    def generate():
        while viewer.running:
            frame_data = viewer.get_frame_jpeg()
            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            else:
                time.sleep(0.1)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/ptz/move', methods=['POST'])
def ptz_move():
    """PTZ移动控制"""
    from flask import request, jsonify

    if not viewer.ptz_session_id:
        return jsonify({"success": False, "message": "PTZ未连接"})

    data = request.get_json()
    direction = data.get('direction')

    params = {}
    if direction == 'up':
        params['tiltUp'] = 120
    elif direction == 'down':
        params['tiltUp'] = -120
    elif direction == 'left':
        params['panLeft'] = 120
    elif direction == 'right':
        params['panRight'] = 120

    success = viewer.send_ptz_command('ptz_move_start', params)
    return jsonify({"success": success})

@app.route('/ptz/zoom', methods=['POST'])
def ptz_zoom():
    """PTZ缩放控制"""
    from flask import request, jsonify

    if not viewer.ptz_session_id:
        return jsonify({"success": False, "message": "PTZ未连接"})

    data = request.get_json()
    zoom_type = data.get('type')

    params = {}
    if zoom_type == 'in':
        params['zoomIn'] = 120
    elif zoom_type == 'out':
        params['zoomOut'] = 120

    success = viewer.send_ptz_command('ptz_move_start', params)
    return jsonify({"success": success})

@app.route('/ptz/stop', methods=['POST'])
def ptz_stop():
    """停止PTZ移动"""
    from flask import jsonify

    if not viewer.ptz_session_id:
        return jsonify({"success": False, "message": "PTZ未连接"})

    success = viewer.send_ptz_command('ptz_move_stop', {})
    return jsonify({"success": success})

def opencv_display(rtsp_url, ptz_ip=None):
    """OpenCV显示模式"""
    print("🖼️ 启动OpenCV显示模式")

    viewer = RTSPViewer(rtsp_url, ptz_ip)
    if not viewer.start_capture():
        return

    print("📺 视频窗口已打开，按'q'退出")
    print("🎮 PTZ控制: W(上) S(下) A(左) D(右) Q(放大) E(缩小) 空格(停止)")

    # 显示窗口
    cv2.namedWindow('RTSP Stream', cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            with viewer.frame_lock:
                if viewer.current_frame is not None:
                    cv2.imshow('RTSP Stream', viewer.current_frame)

            key = cv2.waitKey(1) & 0xFF

            # 处理按键
            if key == ord('q'):
                break
            elif key == ord('w') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_start', {'tiltUp': 120})
            elif key == ord('s') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_start', {'tiltUp': -120})
            elif key == ord('a') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_start', {'panLeft': 120})
            elif key == ord('d') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_start', {'panRight': 120})
            elif key == ord('q') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_start', {'zoomIn': 120})
            elif key == ord('e') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_start', {'zoomOut': 120})
            elif key == ord(' ') and viewer.ptz_session_id:
                viewer.send_ptz_command('ptz_move_stop', {})

    finally:
        viewer.stop_capture()
        cv2.destroyAllWindows()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RTSP摄像头实时显示器')
    parser.add_argument('rtsp_url', help='RTSP摄像头URL')
    parser.add_argument('--mode', '-m', choices=['web', 'opencv'], default='web',
                       help='显示模式: web(Web界面) 或 opencv(OpenCV窗口)')
    parser.add_argument('--port', '-p', type=int, default=5000,
                       help='Web服务器端口 (默认: 5000)')
    parser.add_argument('--ptz-ip', type=str,
                       help='PTZ控制摄像头IP地址 (可选)')

    args = parser.parse_args()

    print("📺 RTSP摄像头实时显示器")
    print("=" * 50)
    print(f"RTSP URL: {args.rtsp_url}")
    if args.ptz_ip:
        print(f"PTZ控制: {args.ptz_ip}")
    print(f"显示模式: {args.mode}")
    print("=" * 50)

    if args.mode == 'opencv':
        opencv_display(args.rtsp_url, args.ptz_ip)
    else:
        # Web模式
        global viewer
        viewer = RTSPViewer(args.rtsp_url, args.ptz_ip)

        if not viewer.start_capture():
            print("❌ RTSP连接失败")
            return

        print(f"🌐 Web服务器启动: http://localhost:{args.port}")
        print("🛑 按 Ctrl+C 停止服务")

        try:
            app.run(host='0.0.0.0', port=args.port, debug=False)
        except KeyboardInterrupt:
            print("\n🛑 服务已停止")
        finally:
            viewer.stop_capture()

if __name__ == "__main__":
    # 示例用法
    if len(sys.argv) == 1:
        print("📺 RTSP摄像头实时显示器")
        print("=" * 50)
        print("使用方法:")
        print("  python rtsp_viewer.py <RTSP_URL> [选项]")
        print("")
        print("示例:")
        print("  # Web界面模式")
        print("  python rtsp_viewer.py rtsp://admin:admin123@192.168.31.146:554/stream")
        print("  ")
        print("  # Web界面 + PTZ控制")
        print("  python rtsp_viewer.py rtsp://admin:admin123@192.168.31.146:554/stream --ptz-ip 192.168.31.146")
        print("  ")
        print("  # OpenCV窗口模式")
        print("  python rtsp_viewer.py rtsp://admin:admin123@192.168.31.146:554/stream --mode opencv")
        print("")
        print("常见RTSP URL格式:")
        print("  - rtsp://用户名:密码@IP地址:端口/路径")
        print("  - rtsp://admin:admin123@192.168.1.100:554/stream")
        print("  - rtsp://192.168.1.100:554/cam/realmonitor?channel=1&subtype=0")
        sys.exit(1)

    main()