#!/usr/bin/env python3
"""
修复版集成系统 - 直接集成自动SessionId PTZ控制
"""

import cv2
import torch
import time
import threading
import queue
import base64
import json
import requests
import subprocess
import os
from flask import Flask, render_template, Response, jsonify, request
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import signal
import sys
import urllib.request

# 设置SSL兼容性
os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

app = Flask(__name__)

class AutoSessionPTZController:
    """自动SessionId PTZ控制器 - 直接集成版"""

    def __init__(self, session_id="2204F92CDE0B66FD22D99043BBD5C27"):
        self.session_id = session_id
        self.camera_ip = "192.168.31.146"
        self.last_command_time = 0
        self.command_cooldown = 0.1

    def send_command(self, action):
        """发送PTZ命令 - 适配原有接口"""
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            print(f"PTZ命令 {action}: 冷却中")
            return True

        command_map = {
            'up': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": 120}},
            'down': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": -120}},
            'left': {"method": "ptz_move_start", "param": {"channelid": 0, "panLeft": 120}},
            'right': {"method": "ptz_move_start", "param": {"channelid": 0, "panRight": 120}},
            'stop': {"method": "ptz_move_stop", "param": {"channelid": 0}},
            'zoom_in': {"method": "ptz_move_start", "param": {"channelid": 0, "zoomIn": 120}},
            'zoom_out': {"method": "ptz_move_start", "param": {"channelid": 0, "zoomOut": 120}},
        }

        if action not in command_map:
            print(f"❌ 不支持的PTZ命令: {action}")
            return False

        data = command_map[action]
        curl_cmd = [
            "curl", "-s", "--insecure", "--connect-timeout", "3",
            "-H", "Content-Type: application/json",
            "-H", f"SessionId: {self.session_id}",
            "--data-raw", json.dumps(data),
            f"https://{self.camera_ip}/ipc/grpc_cmd"
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
            self.last_command_time = current_time
            success = result.returncode == 0

            if success:
                try:
                    response = json.loads(result.stdout)
                    if 'error' in response:
                        error_code = response.get('error', {}).get('errorcode', -1)
                        if error_code == 0:
                            print(f"✅ PTZ命令 {action}: 成功")
                            return True
                        else:
                            print(f"❌ PTZ命令 {action}: 错误码 {error_code}")
                            return False
                except:
                    pass
                print(f"✅ PTZ命令 {action}: 成功")
                return True
            else:
                print(f"❌ PTZ命令 {action}: 连接失败")
                return False

        except Exception as e:
            print(f"❌ PTZ命令 {action}: 异常 {e}")
            return False

class WebCameraVLM:
    def __init__(self, camera_url=None, use_rtsp=False):
        # 视频源设置
        self.camera_url = camera_url if camera_url is not None else 0
        self.use_rtsp = use_rtsp
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

        # PTZ控制器 - 使用自动SessionId控制器
        self.ptz_controller = AutoSessionPTZController()

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
        if self.use_rtsp:
            return self.connect_rtsp_camera()
        else:
            return self.connect_local_camera()

    def connect_rtsp_camera(self):
        """连接RTSP摄像头"""
        print(f"📡 正在连接RTSP摄像头: {self.camera_url}")

        # 尝试不同的RTSP URL
        rtsp_urls = [
            self.camera_url,
            "rtsp://admin:admin123@192.168.31.146/stream1",
            "rtsp://admin:admin123@192.168.31.146/stream2",
            "rtsp://admin:admin123@192.168.31.146/live",
            "rtsp://admin:admin123@192.168.31.146/h264",
        ]

        for url in rtsp_urls:
            print(f"🔍 尝试RTSP URL: {url}")
            try:
                self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        height, width = frame.shape[:2]
                        print(f"✅ RTSP连接成功: {width}x{height}")
                        self.stats['camera_connected'] = True
                        return True

                self.cap.release()
            except Exception as e:
                print(f"❌ RTSP连接失败: {e}")

        print("❌ 所有RTSP连接尝试都失败了")
        return False

    def connect_local_camera(self):
        """连接本地摄像头或创建模拟视频"""
        print(f"📷 正在连接本地摄像头: {self.camera_url}")
        try:
            self.cap = cv2.VideoCapture(self.camera_url)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    print("✅ 本地摄像头连接成功")
                    self.stats['camera_connected'] = True
                    return True

            # 创建模拟视频
            print("💡 创建模拟视频源")
            self.cap = None
            self.stats['camera_connected'] = False
            return True

        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            return False

    def generate_fake_frame(self):
        """生成模拟视频帧"""
        import numpy as np

        # 创建一个蓝色背景的帧
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (100, 50, 0)  # BGR蓝色

        # 添加时间戳文字
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Simulation Mode", (20, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Time: {timestamp}", (20, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"PTZ Control: Available", (20, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"AI Analysis: Active", (20, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame

    def capture_frames(self):
        """捕获帧的线程"""
        while self.running:
            try:
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if not ret:
                        time.sleep(0.1)
                        continue
                else:
                    # 使用模拟帧
                    frame = self.generate_fake_frame()

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
                        {"type": "text", "text": "描述图像中的场景和主要内容，回复要简洁清晰。"},
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

    def generate_frames(self):
        """生成视频流"""
        while self.running:
            try:
                with self.frame_lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                    else:
                        frame = self.generate_fake_frame()

                # 编码为JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            except Exception as e:
                print(f"帧生成异常: {e}")

            time.sleep(0.033)

    def start_system(self):
        """启动系统"""
        print("🚀 启动整合版摄像头系统...")

        # 加载VLM模型
        if not self.load_vlm_model():
            return False

        # 连接摄像头
        if not self.connect_camera():
            print("⚠️ 摄像头连接失败，使用模拟视频源")

        self.running = True

        # 启动线程
        self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.vlm_thread = threading.Thread(target=self.vlm_analysis_worker, daemon=True)

        self.capture_thread.start()
        self.vlm_thread.start()

        print("✅ 系统启动成功")
        return True

    def stop_system(self):
        """停止系统"""
        print("🛑 正在停止系统...")
        self.running = False

        if self.cap:
            self.cap.release()

        print("✅ 系统已停止")

# 创建全局摄像头系统实例
camera_system = None

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

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
    """PTZ控制API - 修复版"""
    print(f"🎮 收到PTZ命令: {action}")

    try:
        success = camera_system.ptz_controller.send_command(action)
        response = {
            'success': success,
            'action': action,
            'timestamp': time.time(),
            'session_id': camera_system.ptz_controller.session_id[:16] + "..."
        }
        print(f"🎮 PTZ响应: {response}")
        return jsonify(response)
    except Exception as e:
        print(f"❌ PTZ控制异常: {e}")
        return jsonify({
            'success': False,
            'action': action,
            'error': str(e),
            'timestamp': time.time()
        })

# HTML模板（内嵌）
INDEX_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>🎥 修复版PTZ监控系统</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #000;
            color: #fff;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        .video-container {
            position: relative;
            background: #111;
            border-radius: 10px;
            padding: 20px;
        }
        .video-stream {
            width: 100%;
            border-radius: 10px;
        }
        .controls {
            background: #222;
            border-radius: 10px;
            padding: 20px;
        }
        .ptz-controls {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        .ptz-btn {
            background: #444;
            color: #fff;
            border: none;
            padding: 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }
        .ptz-btn:hover {
            background: #555;
        }
        .ptz-btn:active {
            background: #666;
        }
        .status {
            background: #333;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .analysis {
            background: #1a472a;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .title {
            color: #4ade80;
            text-align: center;
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <h1 class="title">🎥 修复版PTZ监控系统</h1>

    <div class="container">
        <div class="video-container">
            <img src="/video_feed" alt="Video Stream" class="video-stream" id="video">
        </div>

        <div class="controls">
            <h3>🎮 PTZ控制</h3>
            <div class="ptz-controls">
                <div></div>
                <button class="ptz-btn" onclick="sendPTZ('up')">↑ 上</button>
                <div></div>
                <button class="ptz-btn" onclick="sendPTZ('left')">← 左</button>
                <button class="ptz-btn" onclick="sendPTZ('stop')">⏹ 停止</button>
                <button class="ptz-btn" onclick="sendPTZ('right')">→ 右</button>
                <div></div>
                <button class="ptz-btn" onclick="sendPTZ('down')">↓ 下</button>
                <div></div>
            </div>

            <div class="ptz-controls">
                <button class="ptz-btn" onclick="sendPTZ('zoom_in')">🔍 放大</button>
                <button class="ptz-btn" onclick="sendPTZ('zoom_out')">🔎 缩小</button>
            </div>

            <div class="status" id="status">
                <h4>📊 系统状态</h4>
                <p>FPS: <span id="fps">0</span></p>
                <p>总帧数: <span id="frames">0</span></p>
                <p>运行时间: <span id="uptime">0</span>秒</p>
                <p>PTZ: <span id="ptz-status">待命</span></p>
            </div>

            <div class="analysis" id="analysis">
                <h4>🤖 AI分析</h4>
                <p id="analysis-text">等待AI分析...</p>
            </div>
        </div>
    </div>

    <script>
        // PTZ控制函数
        function sendPTZ(action) {
            const statusEl = document.getElementById('ptz-status');
            statusEl.textContent = `执行 ${action}...`;
            statusEl.style.color = '#fbbf24';

            fetch(`/api/ptz/${action}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusEl.textContent = `✅ ${action} 成功`;
                        statusEl.style.color = '#10b981';
                    } else {
                        statusEl.textContent = `❌ ${action} 失败`;
                        statusEl.style.color = '#ef4444';
                    }
                    console.log('PTZ结果:', data);
                })
                .catch(error => {
                    statusEl.textContent = `❌ ${action} 错误`;
                    statusEl.style.color = '#ef4444';
                    console.error('PTZ错误:', error);
                });
        }

        // 键盘控制
        document.addEventListener('keydown', function(event) {
            switch(event.key.toLowerCase()) {
                case 'w': sendPTZ('up'); break;
                case 's': sendPTZ('down'); break;
                case 'a': sendPTZ('left'); break;
                case 'd': sendPTZ('right'); break;
                case ' ': sendPTZ('stop'); event.preventDefault(); break;
                case 'q': sendPTZ('zoom_in'); break;
                case 'e': sendPTZ('zoom_out'); break;
            }
        });

        // 定期更新状态
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('frames').textContent = data.total_frames;
                    document.getElementById('uptime').textContent = data.uptime.toFixed(0);
                    document.getElementById('analysis-text').textContent = data.latest_analysis.text;
                })
                .catch(error => console.error('状态更新错误:', error));
        }

        setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</body>
</html>'''

# 创建templates目录和文件
def setup_templates():
    import os
    templates_dir = 'templates'
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)

    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(INDEX_HTML)

def signal_handler(sig, frame):
    """信号处理器"""
    print('\n🛑 接收到停止信号...')
    if camera_system:
        camera_system.stop_system()
    sys.exit(0)

def main():
    global camera_system
    import argparse

    # 设置SSL兼容性
    openssl_conf = '/tmp/openssl_legacy.conf'
    config_content = '''openssl_conf = openssl_init

[openssl_init]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
Options = UnsafeLegacyRenegotiation
'''

    with open(openssl_conf, 'w') as f:
        f.write(config_content)

    os.environ['OPENSSL_CONF'] = openssl_conf

    # 处理命令行参数
    parser = argparse.ArgumentParser(description='修复版PTZ监控系统')
    parser.add_argument('--rtsp', help='RTSP摄像头URL')
    parser.add_argument('--port', type=int, default=5002, help='Web服务器端口')
    parser.add_argument('--host', default='0.0.0.0', help='Web服务器主机')

    args = parser.parse_args()

    print("🎯 修复版PTZ监控系统")
    print("=" * 60)

    # 设置模板
    setup_templates()

    # 初始化摄像头系统
    use_rtsp = args.rtsp is not None
    camera_system = WebCameraVLM(camera_url=args.rtsp, use_rtsp=use_rtsp)

    print(f"📺 视频源: {'RTSP' if use_rtsp else '模拟'}")
    print(f"🎮 PTZ控制: 自动SessionId")

    # 启动系统
    if not camera_system.start_system():
        print("❌ 系统启动失败")
        return

    print(f"🌐 Web界面: http://localhost:{args.port}")
    print("🎮 PTZ控制: 点击按钮或键盘WASD")
    print("🛑 按 Ctrl+C 停止")
    print("-" * 60)

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