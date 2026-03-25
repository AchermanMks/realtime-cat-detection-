#!/usr/bin/env python3
"""
Web版实时摄像头流 + VLM分析
通过浏览器查看实时画面和AI分析结果
"""

import cv2
import torch
import time
import threading
import queue
import base64
import json
from flask import Flask, render_template, Response, jsonify
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import signal
import sys

app = Flask(__name__)

class WebCameraVLM:
    def __init__(self, camera_url=None):
        # 支持RTSP URL或本地摄像头索引
        # 示例RTSP: "rtsp://username:password@ip:port/path"
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
        self.analysis_interval = 10.0  # VLM分析间隔(秒)

        # 统计信息
        self.stats = {
            'total_frames': 0,
            'total_analyses': 0,
            'start_time': time.time(),
            'camera_connected': False
        }

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
        """连接摄像头 - 支持本地摄像头和RTSP流"""
        if self.is_rtsp:
            return self.connect_rtsp_camera()
        else:
            return self.connect_local_camera()

    def connect_rtsp_camera(self):
        """连接RTSP摄像头"""
        print(f"📡 正在连接RTSP摄像头: {self.camera_url}")

        # RTSP连接选项
        rtsp_options = [
            # FFMPEG后端通常对RTSP支持最好
            cv2.CAP_FFMPEG,
            cv2.CAP_GSTREAMER,
            cv2.CAP_ANY
        ]

        for backend in rtsp_options:
            try:
                print(f"📡 尝试后端: {backend}")
                cap = cv2.VideoCapture(self.camera_url, backend)

                # 设置缓冲区大小以减少延迟
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                # 设置超时
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 10秒连接超时
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)   # 5秒读取超时

                if cap.isOpened():
                    # 测试读取帧
                    print("🔍 测试RTSP流...")
                    ret, test_frame = cap.read()

                    if ret and test_frame is not None:
                        h, w = test_frame.shape[:2]
                        fps = cap.get(cv2.CAP_PROP_FPS) or 25

                        print(f"✅ RTSP连接成功: {w}x{h} @{fps}fps")
                        print(f"📺 摄像头信息:")
                        print(f"   - 分辨率: {w}x{h}")
                        print(f"   - 帧率: {fps}")
                        print(f"   - 编码格式: {cap.get(cv2.CAP_PROP_FOURCC)}")

                        self.cap = cap
                        self.stats['camera_connected'] = True
                        return True
                    else:
                        print("⚠️ 无法从RTSP流读取帧")
                        cap.release()
                else:
                    print("⚠️ 无法打开RTSP流")
                    cap.release()

            except Exception as e:
                print(f"⚠️ RTSP连接失败: {e}")
                if 'cap' in locals():
                    cap.release()

        print("❌ 所有RTSP连接尝试都失败了")
        print("💡 请检查:")
        print("   1. RTSP URL是否正确")
        print("   2. 网络连接是否正常")
        print("   3. 摄像头是否支持RTSP协议")
        print("   4. 用户名密码是否正确")

        # 失败后使用模拟视频源
        print("🔄 切换到模拟视频源")
        self.cap = None
        self.stats['camera_connected'] = True
        return True

    def connect_local_camera(self):
        """连接本地摄像头"""
        print("🔍 正在搜索可用摄像头...")

        # 如果指定了具体索引，优先尝试
        if isinstance(self.camera_url, int):
            indices_to_try = [self.camera_url] + [i for i in range(0, 10) if i != self.camera_url]
        else:
            indices_to_try = range(0, 10)

        # 尝试多个摄像头索引
        for camera_index in indices_to_try:
            try:
                print(f"📡 尝试摄像头索引: {camera_index}")
                cap = cv2.VideoCapture(camera_index)

                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # 测试读取帧
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        h, w = test_frame.shape[:2]
                        fps = cap.get(cv2.CAP_PROP_FPS) or 30
                        print(f"✅ 找到摄像头{camera_index}: {w}x{h} @{fps}fps")

                        # 保存成功的摄像头
                        self.cap = cap
                        self.camera_url = camera_index
                        self.stats['camera_connected'] = True
                        return True
                    else:
                        cap.release()
                else:
                    cap.release()

            except Exception as e:
                print(f"⚠️ 摄像头{camera_index}测试失败: {e}")

        # 尝试不同的后端
        backends = [cv2.CAP_V4L2, cv2.CAP_GSTREAMER, cv2.CAP_FFMPEG]
        backend_names = ["V4L2", "GStreamer", "FFMPEG"]

        for backend, name in zip(backends, backend_names):
            try:
                print(f"📡 尝试{name}后端...")
                cap = cv2.VideoCapture(0, backend)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        h, w = test_frame.shape[:2]
                        fps = cap.get(cv2.CAP_PROP_FPS) or 30
                        print(f"✅ {name}后端连接成功: {w}x{h} @{fps}fps")
                        self.cap = cap
                        self.camera_url = f"{name}:0"
                        self.stats['camera_connected'] = True
                        return True
                cap.release()
            except Exception as e:
                print(f"⚠️ {name}后端失败: {e}")

        print("❌ 未找到可用摄像头，使用模拟视频源")
        self.cap = None
        self.stats['camera_connected'] = True  # 模拟连接
        return True

    def generate_demo_frame(self):
        """生成演示帧"""
        import numpy as np

        # 创建640x480的演示图像
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 添加渐变背景
        for y in range(480):
            for x in range(640):
                frame[y, x] = [int(x * 255 / 640), int(y * 255 / 480), 128]

        # 添加当前时间文本
        current_time = time.time()
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))

        # 添加一些图形元素
        cv2.rectangle(frame, (50, 50), (590, 430), (255, 255, 255), 2)
        cv2.putText(frame, "VLM Demo Camera", (200, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, time_str, (200, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # 添加移动的圆圈
        center_x = int(320 + 200 * np.sin(current_time * 2))
        center_y = int(240 + 100 * np.cos(current_time * 2))
        cv2.circle(frame, (center_x, center_y), 30, (0, 255, 0), -1)

        cv2.putText(frame, f"Frame: {self.stats['total_frames']}", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"FPS: {self.display_fps:.1f}", (200, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return frame

    def capture_frames(self):
        """视频帧捕获线程"""
        while self.running:
            try:
                # 如果有真实摄像头，使用真实摄像头
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        frame = self.generate_demo_frame()
                else:
                    # 使用模拟帧
                    frame = self.generate_demo_frame()

                # 更新统计
                self.stats['total_frames'] += 1
                self.fps_counter += 1
                current_time = time.time()

                # 计算FPS
                if current_time - self.last_fps_time >= 1.0:
                    self.display_fps = self.fps_counter / (current_time - self.last_fps_time)
                    self.fps_counter = 0
                    self.last_fps_time = current_time

                # 存储当前帧
                with self.frame_lock:
                    self.current_frame = frame.copy()

                # 提交VLM分析
                if current_time - self.last_analysis_time > self.analysis_interval:
                    if not self.analysis_queue.full():
                        self.analysis_queue.put(frame.copy())
                        self.last_analysis_time = current_time
                        print("📋 提交帧进行VLM分析")

                # 控制帧率
                time.sleep(0.033)  # 约30fps

            except Exception as e:
                print(f"⚠️ 帧捕获异常: {e}")
                time.sleep(1)

    def analysis_worker(self):
        """VLM分析工作线程"""
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
            # 保存临时图片
            temp_path = "/tmp/web_frame.jpg"
            cv2.imwrite(temp_path, frame)

            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": "描述图像中的场景和主要内容，回复要简洁清晰，重点突出重要信息。"},
                    ],
                }
            ]

            # VLM处理
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
                # 缩放帧以提高传输效率
                h, w = self.current_frame.shape[:2]
                scale = 0.7
                new_w, new_h = int(w * scale), int(h * scale)
                resized_frame = cv2.resize(self.current_frame, (new_w, new_h))

                # 编码为JPEG
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
                time.sleep(0.1)

    def start_system(self):
        """启动系统"""
        print("🚀 启动Web版摄像头系统...")

        # 加载模型
        if not self.load_vlm_model():
            return False

        # 连接摄像头
        if not self.connect_camera():
            return False

        self.running = True

        # 启动工作线程
        capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)

        capture_thread.start()
        analysis_thread.start()

        print("✅ 系统启动成功")
        return True

    def stop_system(self):
        """停止系统"""
        print("🛑 正在停止系统...")
        self.running = False

        if self.cap:
            self.cap.release()

        print("✅ 系统已停止")

# 全局实例 - 在main函数中创建
camera_system = None

# Web路由
@app.route('/')
def index():
    """主页"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>🎥 实时摄像头监控 + AI分析</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0; padding: 20px;
            background: #1a1a1a; color: #fff;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .video-container {
            display: flex; flex-wrap: wrap; gap: 20px;
            justify-content: center; align-items: flex-start;
        }
        .video-panel {
            flex: 1; min-width: 400px; max-width: 800px;
            background: #2a2a2a; border-radius: 10px; padding: 15px;
        }
        .analysis-panel {
            flex: 1; min-width: 300px; max-width: 400px;
            background: #2a2a2a; border-radius: 10px; padding: 15px;
        }
        .video-stream {
            width: 100%; height: auto;
            border-radius: 8px; background: #000;
        }
        .info-box {
            background: #333; padding: 15px; border-radius: 8px;
            margin: 10px 0; border-left: 4px solid #00ff88;
        }
        .analysis-text {
            background: #444; padding: 15px; border-radius: 8px;
            margin: 10px 0; font-size: 14px; line-height: 1.4;
        }
        .stats {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px; margin: 15px 0;
        }
        .stat-item {
            background: #444; padding: 10px; border-radius: 6px; text-align: center;
        }
        .stat-value { font-size: 20px; font-weight: bold; color: #00ff88; }
        .stat-label { font-size: 12px; color: #ccc; }
        h1, h2, h3 { color: #00ff88; margin-top: 0; }
        .timestamp { color: #888; font-size: 12px; }
        .loading { text-align: center; padding: 50px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 实时摄像头监控 + AI分析系统</h1>
            <p>基于VLM的智能视觉分析 | 实时流处理</p>
        </div>

        <div class="video-container">
            <div class="video-panel">
                <h3>📺 实时视频流</h3>
                <img src="/video_feed" class="video-stream" alt="实时摄像头画面">

                <div class="info-box">
                    <h4>📊 系统状态</h4>
                    <div class="stats" id="stats">
                        <div class="stat-item">
                            <div class="stat-value" id="fps">--</div>
                            <div class="stat-label">FPS</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="frames">--</div>
                            <div class="stat-label">总帧数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="analyses">--</div>
                            <div class="stat-label">AI分析次数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="uptime">--</div>
                            <div class="stat-label">运行时间</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="analysis-panel">
                <h3>🤖 AI视觉分析</h3>
                <div class="analysis-text" id="analysis">
                    <div class="loading">正在等待AI分析结果...</div>
                </div>

                <div class="info-box">
                    <h4>ℹ️ 分析信息</h4>
                    <p><strong>分析间隔:</strong> 10秒</p>
                    <p><strong>模型:</strong> Qwen2-VL-7B-Instruct</p>
                    <p><strong>最后更新:</strong> <span id="last-update">--</span></p>
                    <p><strong>分析耗时:</strong> <span id="analysis-time">--</span> 秒</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 定期更新分析结果和统计信息
        function updateData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 更新统计信息
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('frames').textContent = data.total_frames.toLocaleString();
                    document.getElementById('analyses').textContent = data.total_analyses;

                    // 计算运行时间
                    const uptimeSeconds = Math.floor(data.uptime);
                    const hours = Math.floor(uptimeSeconds / 3600);
                    const minutes = Math.floor((uptimeSeconds % 3600) / 60);
                    const seconds = uptimeSeconds % 60;
                    document.getElementById('uptime').textContent =
                        hours + 'h ' + minutes + 'm ' + seconds + 's';

                    // 更新分析结果
                    if (data.analysis && data.analysis.text) {
                        document.getElementById('analysis').innerHTML =
                            '<strong>AI分析结果:</strong><br>' + data.analysis.text;

                        const updateTime = new Date(data.analysis.timestamp * 1000);
                        document.getElementById('last-update').textContent =
                            updateTime.toLocaleTimeString();
                        document.getElementById('analysis-time').textContent =
                            data.analysis.analysis_time.toFixed(2);
                    }
                })
                .catch(error => {
                    console.error('Error updating data:', error);
                });
        }

        // 每2秒更新一次
        setInterval(updateData, 2000);
        updateData(); // 立即更新一次
    </script>
</body>
</html>
    '''

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
        'analysis': camera_system.latest_analysis
    })

def signal_handler(signum, frame):
    """信号处理"""
    camera_system.stop_system()
    sys.exit(0)

def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Web版摄像头监控系统 - 支持本地摄像头和RTSP流')
    parser.add_argument('--rtsp', '-r', type=str,
                      help='RTSP摄像头URL (例如: rtsp://username:password@192.168.1.100:554/stream)')
    parser.add_argument('--camera', '-c', type=int, default=0,
                      help='本地摄像头索引 (默认: 0)')
    parser.add_argument('--port', '-p', type=int, default=5000,
                      help='Web服务器端口 (默认: 5000)')

    args = parser.parse_args()

    print("🌐 Web版摄像头系统启动中...")

    # 显示使用的摄像头源
    if args.rtsp:
        print(f"📡 使用RTSP摄像头: {args.rtsp}")
        camera_url = args.rtsp
    else:
        print(f"📹 使用本地摄像头: 索引{args.camera}")
        camera_url = args.camera

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建摄像头系统实例
    global camera_system
    camera_system = WebCameraVLM(camera_url=camera_url)

    # 启动摄像头系统
    if not camera_system.start_system():
        print("❌ 系统启动失败")
        return

    # 启动Web服务器
    print("🌐 启动Web服务器...")
    print(f"📱 打开浏览器访问: http://localhost:{args.port}")
    print("🛑 按 Ctrl+C 停止服务")
    print("")
    print("💡 使用说明:")
    print("   本地摄像头: python3 web_camera_stream.py --camera 0")
    print("   RTSP摄像头: python3 web_camera_stream.py --rtsp rtsp://user:pass@ip:port/stream")


    try:
        app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 接收到中断信号")
    finally:
        camera_system.stop_system()

if __name__ == "__main__":
    main()