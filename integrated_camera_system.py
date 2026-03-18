#!/usr/bin/env python3
"""
整合版摄像头监控系统：视频流 + VLM分析 + PTZ控制
一个页面包含所有功能
"""

import cv2
import torch
import time
import threading
import queue
import base64
import json
import requests
from flask import Flask, render_template, Response, jsonify, request
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import signal
import sys
import urllib.request

app = Flask(__name__)

class PTZController:
    """PTZ控制器 - 通过Node.js代理控制"""

    def __init__(self):
        self.proxy_url = "http://localhost:8899"
        self.last_command_time = 0
        self.command_cooldown = 0.1  # 100ms冷却时间

    def send_command(self, action):
        """发送PTZ命令"""
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            return False

        try:
            url = f"{self.proxy_url}/ptz/{action}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as response:
                result = response.read().decode() == 'success'
                self.last_command_time = current_time
                print(f"PTZ命令 {action}: {'成功' if result else '失败'}")
                return result
        except Exception as e:
            print(f"PTZ命令失败: {e}")
            return False

class WebCameraVLM:
    def __init__(self, camera_url=None):
        # 支持RTSP URL或本地摄像头索引
        self.camera_url = camera_url if camera_url is not None else 0
        self.is_rtsp = isinstance(self.camera_url, str) and self.camera_url.startswith('rtsp://')
        self.model = None
        self.processor = None
        self.running = False

        # 视频流相关
        self.cap = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.display_fps = 0

        # VLM分析相关
        self.analysis_queue = queue.Queue(maxsize=3)
        self.latest_analysis = {
            'text': '等待AI分析...',
            'timestamp': time.time(),
            'analysis_time': 0
        }
        self.analysis_counter = 0
        self.last_analysis_time = 0
        self.analysis_interval = 15.0  # VLM分析间隔(秒)

        # 统计信息
        self.stats = {
            'total_frames': 0,
            'total_analyses': 0,
            'start_time': time.time(),
            'camera_connected': False
        }

        # PTZ控制器
        self.ptz_controller = PTZController()

    def load_vlm_model(self):
        """加载VLM模型"""
        print("🤖 正在加载VLM模型...")
        start_time = time.time()

        try:
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype="auto",
                device_map="auto",
            )
            self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

            load_time = time.time() - start_time
            print(f"✅ VLM模型加载完成，耗时: {load_time:.2f}秒")
            return True

        except Exception as e:
            print(f"❌ VLM模型加载失败: {e}")
            return False

    def connect_camera(self):
        """连接摄像头"""
        if self.is_rtsp:
            return self.connect_rtsp_camera()
        else:
            return self.connect_local_camera()

    def connect_rtsp_camera(self):
        """连接RTSP摄像头"""
        print(f"📡 正在连接RTSP摄像头: {self.camera_url}")

        rtsp_options = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]

        for backend in rtsp_options:
            try:
                print(f"📡 尝试后端: {backend}")
                self.cap = cv2.VideoCapture(self.camera_url, backend)

                # 设置缓冲区
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                print("🔍 测试RTSP流...")
                if self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        height, width = frame.shape[:2]
                        fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
                        fourcc = self.cap.get(cv2.CAP_PROP_FOURCC)

                        print(f"✅ RTSP连接成功: {width}x{height} @{fps}fps")
                        print(f"📺 摄像头信息:")
                        print(f"   - 分辨率: {width}x{height}")
                        print(f"   - 帧率: {fps}")
                        print(f"   - 编码格式: {fourcc}")

                        self.stats['camera_connected'] = True
                        return True

                self.cap.release()

            except Exception as e:
                print(f"⚠️ 后端 {backend} 连接失败: {e}")
                continue

        print("❌ 所有RTSP连接尝试都失败了")
        return False

    def connect_local_camera(self):
        """连接本地摄像头"""
        print(f"📷 正在连接本地摄像头: {self.camera_url}")
        try:
            self.cap = cv2.VideoCapture(self.camera_url)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    print("✅ 本地摄像头连接成功")
                    self.stats['camera_connected'] = True
                    return True
            return False
        except Exception as e:
            print(f"❌ 本地摄像头连接失败: {e}")
            return False

    def capture_frames(self):
        """捕获帧的线程"""
        if not self.cap or not self.cap.isOpened():
            return

        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                with self.frame_lock:
                    self.current_frame = frame.copy()
                    self.stats['total_frames'] += 1

                # 计算FPS
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    self.display_fps = self.fps_counter / (current_time - self.last_fps_time)
                    self.fps_counter = 0
                    self.last_fps_time = current_time

                # 添加到VLM分析队列
                current_time = time.time()
                if (current_time - self.last_analysis_time >= self.analysis_interval and
                    self.analysis_queue.qsize() < 2):
                    try:
                        self.analysis_queue.put_nowait(frame.copy())
                        self.last_analysis_time = current_time
                    except queue.Full:
                        pass

                time.sleep(0.033)  # ~30fps

            except Exception as e:
                print(f"帧捕获异常: {e}")
                time.sleep(1)

    def vlm_analysis_worker(self):
        """VLM分析的工作线程"""
        while self.running:
            try:
                frame = self.analysis_queue.get(timeout=1)
                print("🔍 开始VLM分析...")
                start_time = time.time()

                result = self.analyze_frame(frame)
                analysis_time = time.time() - start_time

                if result:
                    self.latest_analysis = {
                        'text': result,
                        'timestamp': time.time(),
                        'analysis_time': analysis_time
                    }
                    self.analysis_counter += 1
                    self.stats['total_analyses'] += 1
                    print(f"✅ VLM分析完成 ({analysis_time:.2f}秒)")
                    print(f"📝 结果: {result[:100]}...")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ VLM分析异常: {e}")

    def analyze_frame(self, frame):
        """分析单帧"""
        try:
            temp_path = "/tmp/web_frame.jpg"
            cv2.imwrite(temp_path, frame)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": "描述图像中的场景和主要内容，回复要简洁清晰，重点突出重要信息。"},
                    ],
                }
            ]

            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda" if torch.cuda.is_available() else "cpu")

            generated_ids = self.model.generate(**inputs, max_new_tokens=150)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            return output_text.strip()

        except Exception as e:
            print(f"VLM分析失败: {e}")
            return f"分析失败: {str(e)}"

    def get_frame_as_jpeg(self):
        """获取JPEG格式的当前帧"""
        with self.frame_lock:
            if self.current_frame is not None:
                h, w = self.current_frame.shape[:2]
                scale = 0.7
                new_w, new_h = int(w * scale), int(h * scale)
                resized_frame = cv2.resize(self.current_frame, (new_w, new_h))

                ret, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    return buffer.tobytes()
        return None

    def generate_frames(self):
        """生成视频帧流"""
        while self.running:
            frame_data = self.get_frame_as_jpeg()
            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            else:
                # 如果没有帧数据，发送一个空白帧保持连接
                import numpy as np
                blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(blank_frame, "No Video Signal", (150, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                ret, buffer = cv2.imencode('.jpg', blank_frame)
                if ret:
                    blank_data = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + blank_data + b'\r\n')
                time.sleep(0.5)

    def start_system(self):
        """启动系统"""
        print("🚀 启动整合版摄像头系统...")

        if not self.load_vlm_model():
            return False

        if not self.connect_camera():
            print("💡 摄像头连接失败，使用模拟视频源")
            # 继续启动系统，使用模拟视频源
            pass

        print("✅ 系统启动成功")

        self.running = True
        threading.Thread(target=self.capture_frames, daemon=True).start()
        threading.Thread(target=self.vlm_analysis_worker, daemon=True).start()

        return True

    def stop_system(self):
        """停止系统"""
        print("🛑 正在停止系统...")
        self.running = False
        if self.cap:
            self.cap.release()
        print("✅ 系统已停止")

# 全局摄像头系统实例
camera_system = None

@app.route('/')
def index():
    """主页 - 整合视频监控和PTZ控制"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>🎥 智能摄像头监控 + PTZ控制</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #000;
            color: #fff;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            height: calc(100vh - 40px);
        }
        .video-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            flex-direction: column;
        }
        .control-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .video-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        #video {
            width: 100%;
            height: 70%;
            object-fit: contain;
            border-radius: 10px;
            background: #000;
        }
        .analysis-box {
            flex: 1;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            overflow-y: auto;
        }
        .ptz-panel {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 15px;
        }
        .direction-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            grid-template-rows: 1fr 1fr 1fr;
            gap: 8px;
            max-width: 200px;
            margin: 15px auto;
        }
        .btn {
            background: linear-gradient(145deg, #4a5568, #2d3748);
            border: none;
            color: #fff;
            padding: 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
            background: linear-gradient(145deg, #5a6578, #3d4758);
        }
        .btn:active {
            transform: translateY(0);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .btn-up { grid-column: 2; grid-row: 1; }
        .btn-left { grid-column: 1; grid-row: 2; }
        .btn-stop {
            grid-column: 2;
            grid-row: 2;
            background: linear-gradient(145deg, #e53e3e, #c53030);
        }
        .btn-right { grid-column: 3; grid-row: 2; }
        .btn-down { grid-column: 2; grid-row: 3; }
        .zoom-controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 15px;
        }
        .zoom-btn {
            background: linear-gradient(145deg, #3182ce, #2c5aa0);
            padding: 8px 16px;
            font-size: 14px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }
        .status-item {
            background: rgba(0, 0, 0, 0.2);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 14px;
        }
        .status-value {
            font-size: 18px;
            font-weight: bold;
            color: #68d391;
        }
        h1 {
            color: #68d391;
            text-align: center;
            margin-bottom: 20px;
            font-size: 24px;
        }
        h2 {
            color: #90cdf4;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .analysis-text {
            line-height: 1.6;
            font-size: 14px;
        }
        .analysis-meta {
            color: #a0aec0;
            font-size: 12px;
            margin-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 10px;
        }
        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 视频监控区域 -->
        <div class="video-section">
            <h1>🎥 智能摄像头监控系统</h1>
            <div class="video-container">
                <img id="video" src="/video_feed" alt="摄像头视频流">
                <div class="analysis-box">
                    <h2>🤖 AI场景分析</h2>
                    <div id="analysis-text" class="analysis-text">等待AI分析...</div>
                    <div id="analysis-meta" class="analysis-meta"></div>
                </div>
            </div>
        </div>

        <!-- PTZ控制区域 -->
        <div class="control-section">
            <div class="ptz-panel">
                <h2>🎮 PTZ摄像头控制</h2>

                <div class="direction-grid">
                    <button class="btn btn-up" onclick="sendPTZ('up')">▲</button>
                    <button class="btn btn-left" onclick="sendPTZ('left')">◄</button>
                    <button class="btn btn-stop" onclick="sendPTZ('stop')">⏹</button>
                    <button class="btn btn-right" onclick="sendPTZ('right')">►</button>
                    <button class="btn btn-down" onclick="sendPTZ('down')">▼</button>
                </div>

                <div class="zoom-controls">
                    <button class="btn zoom-btn" onclick="sendPTZ('zoom_in')">🔍+</button>
                    <button class="btn zoom-btn" onclick="sendPTZ('zoom_out')">🔍-</button>
                </div>

                <div style="text-align: center; margin-top: 15px; font-size: 12px; color: #a0aec0;">
                    键盘快捷键: WASD移动, 空格停止
                </div>
            </div>

            <!-- 系统状态 -->
            <div class="ptz-panel">
                <h2>📊 系统状态</h2>
                <div class="status-grid">
                    <div class="status-item">
                        <div>FPS</div>
                        <div id="fps-value" class="status-value">0</div>
                    </div>
                    <div class="status-item">
                        <div>总帧数</div>
                        <div id="frames-value" class="status-value">0</div>
                    </div>
                    <div class="status-item">
                        <div>AI分析</div>
                        <div id="analysis-value" class="status-value">0</div>
                    </div>
                    <div class="status-item">
                        <div>运行时间</div>
                        <div id="uptime-value" class="status-value">0s</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // PTZ控制函数
        function sendPTZ(action) {
            fetch('/api/ptz/' + action, {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log('PTZ命令:', action, data.success ? '成功' : '失败');
                })
                .catch(error => {
                    console.error('PTZ命令错误:', error);
                });
        }

        // 键盘控制
        document.addEventListener('keydown', function(e) {
            switch(e.key.toLowerCase()) {
                case 'w': case 'arrowup': sendPTZ('up'); break;
                case 's': case 'arrowdown': sendPTZ('down'); break;
                case 'a': case 'arrowleft': sendPTZ('left'); break;
                case 'd': case 'arrowright': sendPTZ('right'); break;
                case ' ': e.preventDefault(); sendPTZ('stop'); break;
                case '=': case '+': sendPTZ('zoom_in'); break;
                case '-': sendPTZ('zoom_out'); break;
            }
        });

        // 更新系统状态和AI分析
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('fps-value').textContent = data.fps.toFixed(1);
                    document.getElementById('frames-value').textContent = data.total_frames.toLocaleString();
                    document.getElementById('analysis-value').textContent = data.total_analyses;

                    const uptime = Math.floor(data.uptime);
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    const seconds = uptime % 60;
                    document.getElementById('uptime-value').textContent =
                        `${hours}h${minutes}m${seconds}s`;

                    // 更新AI分析结果
                    if (data.latest_analysis && data.latest_analysis.text) {
                        document.getElementById('analysis-text').textContent = data.latest_analysis.text;
                        const analysisTime = new Date(data.latest_analysis.timestamp * 1000).toLocaleTimeString();
                        document.getElementById('analysis-meta').textContent =
                            `分析时间: ${data.latest_analysis.analysis_time.toFixed(2)}s | 更新: ${analysisTime}`;
                    }
                })
                .catch(error => console.error('状态更新错误:', error));
        }

        // 定期更新状态
        setInterval(updateStatus, 2000);
        updateStatus(); // 立即更新一次
    </script>
</body>
</html>'''

@app.route('/video_feed')
def video_feed():
    """视频流接口"""
    return Response(camera_system.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    """系统状态API"""
    current_time = time.time()
    uptime = current_time - camera_system.stats['start_time']

    return jsonify({
        'fps': camera_system.display_fps,
        'total_frames': camera_system.stats['total_frames'],
        'total_analyses': camera_system.stats['total_analyses'],
        'uptime': uptime,
        'camera_connected': camera_system.stats['camera_connected'],
        'latest_analysis': camera_system.latest_analysis
    })

@app.route('/api/ptz/<action>', methods=['POST'])
def ptz_control(action):
    """PTZ控制API"""
    success = camera_system.ptz_controller.send_command(action)
    return jsonify({
        'success': success,
        'action': action,
        'timestamp': time.time()
    })

def signal_handler(sig, frame):
    """信号处理器"""
    print('\n🛑 接收到停止信号...')
    if camera_system:
        camera_system.stop_system()
    sys.exit(0)

def main():
    global camera_system

    # 处理命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='整合版智能摄像头监控系统')
    parser.add_argument('--rtsp', help='RTSP摄像头URL')
    parser.add_argument('--camera', type=int, default=0, help='本地摄像头索引')
    parser.add_argument('--port', type=int, default=5000, help='Web服务器端口')
    parser.add_argument('--host', default='0.0.0.0', help='Web服务器主机')

    args = parser.parse_args()

    # 初始化摄像头系统
    camera_url = args.rtsp if args.rtsp else args.camera
    camera_system = WebCameraVLM(camera_url)

    print("🌐 整合版摄像头系统启动中...")
    print(f"📡 使用摄像头: {camera_url}")

    # 启动系统
    if not camera_system.start_system():
        print("❌ 系统启动失败")
        return

    print("🌐 启动Web服务器...")
    print(f"📱 打开浏览器访问: http://localhost:{args.port}")
    print("🛑 按 Ctrl+C 停止服务")
    print()
    print("💡 功能说明:")
    print("   - 实时视频流显示")
    print("   - AI场景分析 (自动)")
    print("   - PTZ摄像头控制 (点击按钮或键盘)")
    print("   - 系统状态监控")

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动Flask应用
    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ Web服务器启动失败: {e}")
    finally:
        if camera_system:
            camera_system.stop_system()

if __name__ == "__main__":
    main()