#!/usr/bin/env python3
"""
最终PTZ监控系统
功能完全保持，界面回归原版风格
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

class FixedPTZController:
    """PTZ控制器 - 保持修复的参数，隐藏实现细节"""

    def __init__(self, session_id="99FD7138E582CA2EE02C0537F55B8D1"):
        self.session_id = session_id
        self.camera_ip = "192.168.31.146"
        self.last_command_time = 0
        self.command_cooldown = 0.1

    def send_command(self, action):
        """发送PTZ命令 - 使用修复的参数但不显示"""
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            return True

        # 保持修复的参数映射
        command_map = {
            'up': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": 120}},
            'down': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": -120}},
            'left': {"method": "ptz_move_start", "param": {"channelid": 0, "panLeft": 120}},
            'right': {"method": "ptz_move_start", "param": {"channelid": 0, "panLeft": -120}},  # 保持修复
            'stop': {"method": "ptz_move_stop", "param": {"channelid": 0}},
        }

        if action not in command_map:
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
                        return error_code == 0
                except:
                    pass
                return True
            return False

        except:
            return False


class WebCameraVLM:
    def __init__(self, camera_url=None, use_rtsp=False):
        self.camera_url = camera_url if camera_url is not None else 0
        self.use_rtsp = use_rtsp
        self.model = None
        self.processor = None
        self.running = False

        self.cap = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.display_fps = 0

        self.analysis_queue = queue.Queue(maxsize=3)
        self.latest_analysis = {
            'text': '等待AI分析...',
            'timestamp': time.time(),
            'analysis_time': 0
        }
        self.analysis_counter = 0
        self.last_analysis_time = 0
        self.analysis_interval = 15.0

        self.stats = {
            'total_frames': 0,
            'total_analyses': 0,
            'start_time': time.time(),
            'camera_connected': False
        }

        # PTZ控制器 - 保持修复的功能
        self.ptz_controller = FixedPTZController()

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
        if self.use_rtsp:
            return self.connect_rtsp_camera()
        else:
            return self.connect_local_camera()

    def connect_rtsp_camera(self):
        print(f"📡 正在连接RTSP摄像头: {self.camera_url}")

        try:
            self.cap = cv2.VideoCapture(self.camera_url, cv2.CAP_FFMPEG)
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

        return False

    def connect_local_camera(self):
        print(f"📷 正在连接本地摄像头: {self.camera_url}")
        try:
            self.cap = cv2.VideoCapture(self.camera_url)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    print("✅ 本地摄像头连接成功")
                    self.stats['camera_connected'] = True
                    return True

            print("💡 创建模拟视频源")
            self.cap = None
            self.stats['camera_connected'] = False
            return True

        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            return False

    def generate_fake_frame(self):
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (100, 50, 0)

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Simulation Mode", (20, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Time: {timestamp}", (20, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"PTZ Control: Available", (20, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame

    def capture_frames(self):
        while self.running:
            try:
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if not ret:
                        time.sleep(0.1)
                        continue
                else:
                    frame = self.generate_fake_frame()

                with self.frame_lock:
                    self.current_frame = frame.copy()
                    self.stats['total_frames'] += 1

                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    self.display_fps = self.fps_counter / (current_time - self.last_fps_time)
                    self.fps_counter = 0
                    self.last_fps_time = current_time

                if (current_time - self.last_analysis_time >= self.analysis_interval and
                    self.analysis_queue.qsize() < 2):
                    try:
                        self.analysis_queue.put_nowait(frame.copy())
                        self.last_analysis_time = current_time
                    except queue.Full:
                        pass

                time.sleep(0.033)

            except Exception as e:
                print(f"帧捕获异常: {e}")
                time.sleep(1)

    def vlm_analysis_worker(self):
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
        while self.running:
            try:
                with self.frame_lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                    else:
                        frame = self.generate_fake_frame()

                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            except Exception as e:
                print(f"帧生成异常: {e}")

            time.sleep(0.033)

    def start_system(self):
        print("🚀 启动整合版摄像头系统...")

        if not self.load_vlm_model():
            return False

        if not self.connect_camera():
            print("⚠️ 摄像头连接失败，使用模拟视频源")

        self.running = True

        self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.vlm_thread = threading.Thread(target=self.vlm_analysis_worker, daemon=True)

        self.capture_thread.start()
        self.vlm_thread.start()

        print("✅ 系统启动成功")
        return True

    def stop_system(self):
        print("🛑 正在停止系统...")
        self.running = False

        if self.cap:
            self.cap.release()

        print("✅ 系统已停止")

# 创建全局摄像头系统实例
camera_system = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(camera_system.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
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
    """PTZ控制API - 保持原始风格的响应"""
    try:
        success = camera_system.ptz_controller.send_command(action)
        return jsonify({
            'success': success,
            'action': action,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'action': action,
            'error': str(e),
            'timestamp': time.time()
        })

# 原版HTML模板
INDEX_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Camera Control System</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --apple-blue: #007AFF;
            --apple-green: #34C759;
            --apple-red: #FF3B30;
            --apple-orange: #FF9500;
            --apple-purple: #5856D6;
            --apple-pink: #FF2D92;
            --apple-teal: #5AC8FA;
            --apple-gray: #8E8E93;
            --apple-light-gray: #F2F2F7;
            --apple-separator: rgba(60, 60, 67, 0.36);
            --apple-background: rgba(255, 255, 255, 0.95);
            --spring-timing: cubic-bezier(0.175, 0.885, 0.32, 1.275);
            --smooth-timing: cubic-bezier(0.25, 0.46, 0.45, 0.94);
            --apple-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            --apple-shadow-hover: 0 12px 40px rgba(0, 0, 0, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'SF Pro Display', 'SF Pro Icons', 'AOS Icons', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background:
                radial-gradient(circle at 20% 80%, rgba(0, 122, 255, 0.03) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(88, 86, 214, 0.03) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(52, 199, 89, 0.02) 0%, transparent 50%),
                linear-gradient(135deg, #000000 0%, #0a0a0a 50%, #000000 100%);
            color: #ffffff;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.47059;
            font-weight: 400;
            overflow-x: hidden;
            position: relative;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background:
                repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 98px,
                    rgba(255, 255, 255, 0.005) 100px
                ),
                repeating-linear-gradient(
                    0deg,
                    transparent,
                    transparent 98px,
                    rgba(255, 255, 255, 0.005) 100px
                );
            pointer-events: none;
            z-index: -1;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px 0;
            animation: headerFadeIn 1.5s var(--smooth-timing);
        }

        @keyframes headerFadeIn {
            0% { opacity: 0; transform: translateY(-30px) scale(0.9); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }

        .header h1 {
            font-size: 48px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--apple-blue), var(--apple-purple), var(--apple-pink));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 12px;
            letter-spacing: -0.022em;
            animation: titleFloat 3s ease-in-out infinite;
            position: relative;
            display: inline-block;
        }

        @keyframes titleFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
        }

        .header h1::before {
            content: '';
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 4px;
            background: linear-gradient(135deg, var(--apple-blue), var(--apple-purple));
            border-radius: 2px;
            animation: barGlow 2s ease-in-out infinite;
        }

        @keyframes barGlow {
            0%, 100% { opacity: 0.6; transform: translateX(-50%) scaleX(1); }
            50% { opacity: 1; transform: translateX(-50%) scaleX(1.2); }
        }

        .header p {
            color: rgba(255, 255, 255, 0.8);
            font-size: 19px;
            font-weight: 500;
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            border-radius: 25px;
            display: inline-block;
            animation: subtitleSlide 1.8s var(--smooth-timing) 0.3s both;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        @keyframes subtitleSlide {
            0% { opacity: 0; transform: translateX(-50px); }
            100% { opacity: 1; transform: translateX(0); }
        }

        .container {
            max-width: 1440px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 2.2fr 1fr;
            gap: 30px;
            align-items: start;
            animation: containerSlideUp 1.2s var(--smooth-timing) 0.5s both;
        }

        @keyframes containerSlideUp {
            0% { opacity: 0; transform: translateY(60px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        .video-card {
            background: rgba(20, 20, 20, 0.8);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            position: relative;
            overflow: hidden;
            transition: all 0.6s var(--smooth-timing);
            animation: cardFloatIn 1.5s var(--spring-timing) 0.7s both;
        }

        @keyframes cardFloatIn {
            0% { opacity: 0; transform: translateY(80px) scale(0.9); }
            60% { transform: translateY(-10px) scale(1.02); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }

        .video-card:hover {
            transform: translateY(-5px) scale(1.01);
            box-shadow: var(--apple-shadow-hover);
            border-color: rgba(255, 255, 255, 0.5);
        }

        .video-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--apple-blue), #5856D6, var(--apple-green));
        }

        .video-stream {
            width: 100%;
            border-radius: 16px;
            display: block;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            background: #000;
        }

        .control-panel {
            background: rgba(20, 20, 20, 0.8);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            display: flex;
            flex-direction: column;
            gap: 30px;
            animation: cardFloatIn 1.5s var(--spring-timing) 0.9s both;
        }

        .section-title {
            font-size: 22px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }

        .ptz-control {
            background: rgba(40, 40, 40, 0.6);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .ptz-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
            max-width: 220px;
            margin-left: auto;
            margin-right: auto;
        }

        .ptz-btn {
            background: linear-gradient(135deg, rgba(60, 60, 60, 0.8), rgba(40, 40, 40, 0.9));
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 18px 14px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.4s var(--spring-timing);
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255, 255, 255, 0.9);
            min-height: 56px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05);
        }

        .ptz-btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: radial-gradient(circle, rgba(0, 122, 255, 0.3) 0%, transparent 70%);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: all 0.6s var(--smooth-timing);
            z-index: 0;
        }

        .ptz-btn:hover::before {
            width: 100px;
            height: 100px;
        }

        .ptz-btn:hover {
            background: linear-gradient(135deg, rgba(0, 122, 255, 0.1), rgba(88, 86, 214, 0.05));
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0, 122, 255, 0.25);
            border-color: var(--apple-blue);
            color: var(--apple-blue);
        }

        .ptz-btn:active {
            transform: scale(0.94);
            background: linear-gradient(135deg, var(--apple-blue), var(--apple-purple));
            color: white;
            box-shadow: 0 2px 8px rgba(0, 122, 255, 0.4);
            border-color: var(--apple-blue);
            animation: ripple 0.6s linear;
        }

        @keyframes ripple {
            0% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0.7); }
            70% { box-shadow: 0 0 0 20px rgba(0, 122, 255, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 122, 255, 0); }
        }

        .ptz-btn.stop-btn {
            background: linear-gradient(135deg, var(--apple-red), #dc2626);
            color: white;
            border-color: var(--apple-red);
            box-shadow: 0 4px 15px rgba(255, 59, 48, 0.3);
            animation: stopBtnPulse 2s ease-in-out infinite;
        }

        @keyframes stopBtnPulse {
            0%, 100% { box-shadow: 0 4px 15px rgba(255, 59, 48, 0.3); }
            50% { box-shadow: 0 6px 20px rgba(255, 59, 48, 0.5); }
        }

        .ptz-btn.stop-btn::before {
            background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
        }

        .ptz-btn.stop-btn:hover {
            background: linear-gradient(135deg, #d90429, #b91c1c);
            transform: translateY(-3px) scale(1.05);
            box-shadow: 0 8px 25px rgba(255, 59, 48, 0.4);
            animation: none;
        }

        .ptz-btn.stop-btn:active {
            background: linear-gradient(135deg, #b91c1c, #991b1b);
            animation: stopRipple 0.6s linear;
        }

        @keyframes stopRipple {
            0% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.7); }
            70% { box-shadow: 0 0 0 20px rgba(255, 59, 48, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0); }
        }

        .keyboard-hint {
            background: rgba(40, 40, 40, 0.6);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 12px;
            padding: 16px;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        }

        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .status-card {
            background: linear-gradient(135deg, rgba(40, 40, 40, 0.8), rgba(30, 30, 30, 0.9));
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            text-align: center;
            transition: all 0.4s var(--spring-timing);
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05);
        }

        .status-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 122, 255, 0.1), transparent);
            transition: left 0.6s;
        }

        .status-card:hover {
            transform: translateY(-5px) scale(1.03);
            box-shadow: 0 10px 30px rgba(0, 122, 255, 0.2);
            border-color: var(--apple-blue);
        }

        .status-card:hover::before {
            left: 100%;
        }

        .status-value {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--apple-blue), var(--apple-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 6px;
            display: block;
            transition: all 0.4s var(--smooth-timing);
        }

        .status-card:hover .status-value {
            transform: scale(1.1);
        }

        .status-label {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.6);
            font-weight: 500;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        }

        .analysis-card {
            background: linear-gradient(135deg, rgba(0, 40, 80, 0.4), rgba(0, 30, 60, 0.6));
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(0, 122, 255, 0.3);
            position: relative;
            box-shadow: 0 4px 20px rgba(0, 122, 255, 0.1), 0 0 0 1px rgba(0, 122, 255, 0.05);
        }

        .analysis-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--apple-blue), var(--apple-green));
            border-radius: 16px 16px 0 0;
        }

        .analysis-text {
            font-size: 15px;
            line-height: 1.6;
            color: rgba(255, 255, 255, 0.9);
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 18px;
            border-radius: 12px;
            margin-top: 10px;
            min-height: 60px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }

        .ptz-status {
            background: rgba(40, 40, 40, 0.7);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 12px;
            padding: 14px 18px;
            font-size: 14px;
            font-weight: 500;
            text-align: center;
            margin-top: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.8);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
            transition: all 0.3s var(--smooth-timing);
        }

        .status-success { color: var(--apple-green); }
        .status-error { color: var(--apple-red); }
        .status-warning { color: var(--apple-orange); }

        /* 响应式设计 */
        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
                gap: 20px;
            }

            .header h1 {
                font-size: 32px;
            }

            .ptz-grid {
                max-width: 200px;
            }
        }

        /* 动画效果 */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        .loading {
            animation: pulse 2s infinite;
        }

        /* iOS风格滚动条 */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--apple-separator);
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--apple-gray);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Camera Control</h1>
        <p>Intelligent monitoring with AI analysis and PTZ control</p>
    </div>

    <div class="container">
        <div class="video-card">
            <img src="/video_feed" alt="Live Video Stream" class="video-stream" id="video">

            <div class="analysis-card">
                <div class="section-title">
                    🤖 AI Analysis
                </div>
                <div class="analysis-text" id="analysis-text">Waiting for AI analysis...</div>
            </div>
        </div>

        <div class="control-panel">
            <div class="ptz-control">
                <div class="section-title">
                    🎮 PTZ Control
                </div>

                <div class="ptz-grid">
                    <div></div>
                    <button class="ptz-btn" onclick="sendPTZ('up')" title="Move Up">
                        ⬆️
                    </button>
                    <div></div>

                    <button class="ptz-btn" onclick="sendPTZ('left')" title="Move Left">
                        ⬅️
                    </button>
                    <button class="ptz-btn stop-btn" onclick="sendPTZ('stop')" title="Stop">
                        ⏹️
                    </button>
                    <button class="ptz-btn" onclick="sendPTZ('right')" title="Move Right">
                        ➡️
                    </button>

                    <div></div>
                    <button class="ptz-btn" onclick="sendPTZ('down')" title="Move Down">
                        ⬇️
                    </button>
                    <div></div>
                </div>

                <div class="keyboard-hint">
                    ⌨️ Keyboard: WASD to move • Space to stop
                </div>

                <div class="ptz-status" id="ptz-status">Ready</div>
            </div>

            <div class="status-grid">
                <div class="status-card">
                    <span class="status-value" id="fps">0</span>
                    <span class="status-label">FPS</span>
                </div>
                <div class="status-card">
                    <span class="status-value" id="frames">0</span>
                    <span class="status-label">Frames</span>
                </div>
                <div class="status-card">
                    <span class="status-value" id="analyses">0</span>
                    <span class="status-label">AI Analyses</span>
                </div>
                <div class="status-card">
                    <span class="status-value" id="uptime">0s</span>
                    <span class="status-label">Uptime</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 苹果风格动画函数
        function createRipple(element, event) {
            const circle = document.createElement('span');
            const diameter = Math.max(element.clientWidth, element.clientHeight);
            const radius = diameter / 2;
            const rect = element.getBoundingClientRect();

            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${event.clientX - rect.left - radius}px`;
            circle.style.top = `${event.clientY - rect.top - radius}px`;
            circle.classList.add('ripple');
            circle.style.cssText += `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                transform: scale(0);
                animation: ripple-animation 0.6s linear;
                pointer-events: none;
            `;

            const style = document.createElement('style');
            style.innerHTML = `
                @keyframes ripple-animation {
                    to { transform: scale(4); opacity: 0; }
                }
            `;
            document.head.appendChild(style);

            const ripple = element.querySelector('.ripple');
            if (ripple) ripple.remove();

            element.appendChild(circle);
            setTimeout(() => circle.remove(), 600);
        }

        // 数值动画函数
        function animateValue(element, start, end, duration = 800) {
            const startTimestamp = performance.now();
            const step = (timestamp) => {
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                const easeOutCubic = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(start + (end - start) * easeOutCubic);

                element.textContent = current.toLocaleString();

                if (progress < 1) {
                    requestAnimationFrame(step);
                }
            };
            requestAnimationFrame(step);
        }

        // 增强的PTZ控制函数
        function sendPTZ(action) {
            const statusEl = document.getElementById('ptz-status');
            const actionNames = {
                'up': 'Moving Up',
                'down': 'Moving Down',
                'left': 'Moving Left',
                'right': 'Moving Right',
                'stop': 'Stopping'
            };

            // 按钮动画效果
            const button = event.target;
            createRipple(button, event);

            // 状态动画
            statusEl.style.transform = 'scale(0.9)';
            statusEl.style.opacity = '0.7';
            setTimeout(() => {
                statusEl.textContent = actionNames[action] || `Executing ${action}`;
                statusEl.className = 'ptz-status status-warning loading';
                statusEl.style.transform = 'scale(1)';
                statusEl.style.opacity = '1';
            }, 150);

            // 发送请求
            fetch(`/api/ptz/${action}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    statusEl.classList.remove('loading');

                    // 成功动画
                    if (data.success) {
                        statusEl.textContent = `✓ ${actionNames[action]} completed`;
                        statusEl.className = 'ptz-status status-success';

                        // 成功特效
                        statusEl.style.animation = 'successBounce 0.5s ease-out';

                        setTimeout(() => {
                            statusEl.style.animation = '';
                            statusEl.textContent = 'Ready';
                            statusEl.className = 'ptz-status';
                        }, 2000);
                    } else {
                        statusEl.textContent = `✗ ${actionNames[action]} failed`;
                        statusEl.className = 'ptz-status status-error';
                        statusEl.style.animation = 'shake 0.5s ease-out';
                        setTimeout(() => statusEl.style.animation = '', 500);
                    }
                })
                .catch(error => {
                    statusEl.classList.remove('loading');
                    statusEl.textContent = `✗ Connection error`;
                    statusEl.className = 'ptz-status status-error';
                    statusEl.style.animation = 'shake 0.5s ease-out';
                    setTimeout(() => statusEl.style.animation = '', 500);
                });
        }

        // 添加CSS动画
        const animationStyles = `
            @keyframes successBounce {
                0%, 20%, 60%, 100% { transform: translateY(0); }
                40% { transform: translateY(-10px); }
                80% { transform: translateY(-5px); }
            }

            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
        `;
        const styleSheet = document.createElement('style');
        styleSheet.innerHTML = animationStyles;
        document.head.appendChild(styleSheet);

        // 键盘控制
        document.addEventListener('keydown', function(event) {
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            switch(event.key.toLowerCase()) {
                case 'w':
                case 'arrowup':
                    sendPTZ('up');
                    break;
                case 's':
                case 'arrowdown':
                    sendPTZ('down');
                    break;
                case 'a':
                case 'arrowleft':
                    sendPTZ('left');
                    break;
                case 'd':
                case 'arrowright':
                    sendPTZ('right');
                    break;
                case ' ':
                    event.preventDefault();
                    sendPTZ('stop');
                    break;
            }
        });

        // 增强状态更新函数
        let previousData = { fps: 0, total_frames: 0, total_analyses: 0, uptime: 0 };

        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 动画更新FPS
                    const fpsEl = document.getElementById('fps');
                    if (Math.abs(data.fps - previousData.fps) > 0.1) {
                        fpsEl.style.transform = 'scale(1.1)';
                        fpsEl.style.color = 'var(--apple-green)';
                        setTimeout(() => {
                            fpsEl.style.transform = 'scale(1)';
                            fpsEl.style.color = '';
                        }, 300);
                    }
                    fpsEl.textContent = data.fps.toFixed(1);

                    // 动画更新帧数
                    const framesEl = document.getElementById('frames');
                    if (data.total_frames !== previousData.total_frames) {
                        animateValue(framesEl, previousData.total_frames, data.total_frames);
                    }

                    // 动画更新分析次数
                    const analysesEl = document.getElementById('analyses');
                    if (data.total_analyses !== previousData.total_analyses) {
                        analysesEl.style.animation = 'successBounce 0.5s ease-out';
                        setTimeout(() => analysesEl.style.animation = '', 500);
                        analysesEl.textContent = data.total_analyses;
                    }

                    // 平滑更新运行时间
                    const uptime = Math.floor(data.uptime);
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    const seconds = uptime % 60;

                    const uptimeText = hours > 0 ? `${hours}h${minutes}m` :
                                     minutes > 0 ? `${minutes}m${seconds}s` : `${seconds}s`;
                    document.getElementById('uptime').textContent = uptimeText;

                    // 动画更新AI分析
                    const analysisEl = document.getElementById('analysis-text');
                    if (data.latest_analysis && data.latest_analysis.text &&
                        data.latest_analysis.text !== analysisEl.textContent) {

                        analysisEl.style.opacity = '0.5';
                        analysisEl.style.transform = 'translateY(10px)';

                        setTimeout(() => {
                            analysisEl.textContent = data.latest_analysis.text;
                            analysisEl.style.opacity = '1';
                            analysisEl.style.transform = 'translateY(0)';
                        }, 200);
                    }

                    previousData = {
                        fps: data.fps,
                        total_frames: data.total_frames,
                        total_analyses: data.total_analyses,
                        uptime: data.uptime
                    };
                })
                .catch(error => {
                    console.error('📊 Status update error:', error);
                    // 错误状态动画
                    document.querySelectorAll('.status-value').forEach(el => {
                        el.style.color = 'var(--apple-red)';
                        setTimeout(() => el.style.color = '', 2000);
                    });
                });
        }

        // 添加按钮事件监听器
        document.addEventListener('DOMContentLoaded', function() {
            // 为所有按钮添加触觉反馈
            const buttons = document.querySelectorAll('.ptz-btn');
            buttons.forEach(button => {
                button.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px) scale(1.02)';
                });

                button.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0) scale(1)';
                });

                button.addEventListener('mousedown', function(e) {
                    createRipple(this, e);
                });
            });

            // 添加状态卡片悬浮效果
            const statusCards = document.querySelectorAll('.status-card');
            statusCards.forEach((card, index) => {
                card.style.animationDelay = `${0.8 + index * 0.1}s`;
                card.style.animation = 'cardFloatIn 1.5s var(--spring-timing) both';

                card.addEventListener('mouseenter', function() {
                    this.style.zIndex = '10';
                });

                card.addEventListener('mouseleave', function() {
                    this.style.zIndex = '1';
                });
            });

            // 视频流加载动画
            const video = document.getElementById('video');
            video.addEventListener('load', function() {
                this.style.opacity = '0';
                this.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    this.style.transition = 'all 0.8s var(--smooth-timing)';
                    this.style.opacity = '1';
                    this.style.transform = 'scale(1)';
                }, 100);
            });
        });

        // 键盘控制增强
        document.addEventListener('keydown', function(event) {
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            const keyActions = {
                'w': 'up', 'arrowup': 'up',
                's': 'down', 'arrowdown': 'down',
                'a': 'left', 'arrowleft': 'left',
                'd': 'right', 'arrowright': 'right',
                ' ': 'stop'
            };

            const action = keyActions[event.key.toLowerCase()];
            if (action) {
                event.preventDefault();

                // 突出显示对应的按钮
                const button = document.querySelector(`[onclick="sendPTZ('${action}')"]`);
                if (button) {
                    button.style.transform = 'scale(0.95)';
                    button.style.background = 'var(--apple-blue)';
                    button.style.color = 'white';

                    setTimeout(() => {
                        button.style.transform = '';
                        button.style.background = '';
                        button.style.color = '';
                    }, 200);
                }

                sendPTZ(action);
            }
        });

        // 高级状态更新
        let updateInterval;
        function startStatusUpdates() {
            updateStatus();
            updateInterval = setInterval(updateStatus, 2000);
        }

        function stopStatusUpdates() {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        }

        // 页面可见性API
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopStatusUpdates();
            } else {
                startStatusUpdates();
            }
        });

        // 启动状态更新
        startStatusUpdates();

        // 页面加载完成动画
        window.addEventListener('load', function() {
            console.log('🖤 Tech-style Camera Control System loaded');

            // 添加科技感脉冲效果
            setTimeout(() => {
                const pulseOverlay = document.createElement('div');
                pulseOverlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: radial-gradient(circle at center, rgba(0, 122, 255, 0.05) 0%, transparent 70%);
                    pointer-events: none;
                    z-index: -1;
                    animation: techPulse 3s ease-in-out infinite;
                `;
                document.body.appendChild(pulseOverlay);

                const style = document.createElement('style');
                style.innerHTML = `
                    @keyframes techPulse {
                        0%, 100% { opacity: 0.3; transform: scale(1); }
                        50% { opacity: 0.8; transform: scale(1.05); }
                    }
                `;
                document.head.appendChild(style);
            }, 1000);

            // 添加科技感粒子效果
            createTechParticles();
        });

        // 科技感粒子效果
        function createTechParticles() {
            const particleCount = 15;
            for (let i = 0; i < particleCount; i++) {
                setTimeout(() => {
                    const particle = document.createElement('div');
                    const isBlue = Math.random() > 0.5;
                    particle.style.cssText = `
                        position: fixed;
                        width: ${2 + Math.random() * 3}px;
                        height: ${2 + Math.random() * 3}px;
                        background: ${isBlue ? 'rgba(0, 122, 255, 0.6)' : 'rgba(255, 255, 255, 0.4)'};
                        border-radius: 50%;
                        pointer-events: none;
                        z-index: -1;
                        left: ${Math.random() * window.innerWidth}px;
                        top: ${Math.random() * window.innerHeight}px;
                        animation: techFloat ${8 + Math.random() * 4}s ease-in-out infinite;
                        opacity: ${0.4 + Math.random() * 0.4};
                        box-shadow: 0 0 ${4 + Math.random() * 6}px ${isBlue ? 'rgba(0, 122, 255, 0.5)' : 'rgba(255, 255, 255, 0.3)'};
                    `;

                    document.body.appendChild(particle);

                    setTimeout(() => particle.remove(), 12000);
                }, i * 300);
            }
        }

        // 添加科技感动画CSS
        const techAnimation = `
            @keyframes techFloat {
                0%, 100% {
                    transform: translateY(0px) translateX(0px) scale(1);
                    opacity: 0.4;
                }
                25% {
                    transform: translateY(-30px) translateX(20px) scale(1.2);
                    opacity: 0.8;
                }
                50% {
                    transform: translateY(-10px) translateX(-15px) scale(0.8);
                    opacity: 0.6;
                }
                75% {
                    transform: translateY(-25px) translateX(10px) scale(1.1);
                    opacity: 0.7;
                }
            }
        `;
        const techStyle = document.createElement('style');
        techStyle.innerHTML = techAnimation;
        document.head.appendChild(techStyle);
    </script>
</body>
</html>'''

def setup_templates():
    import os
    templates_dir = 'templates'
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)

    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(INDEX_HTML)

def signal_handler(sig, frame):
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

    parser = argparse.ArgumentParser(description='智能摄像头监控系统')
    parser.add_argument('--rtsp', help='RTSP摄像头URL')
    parser.add_argument('--port', type=int, default=5000, help='Web服务器端口')
    parser.add_argument('--host', default='0.0.0.0', help='Web服务器主机')

    args = parser.parse_args()

    print("🌐 整合版摄像头系统启动中...")
    print(f"📡 使用摄像头: {args.rtsp if args.rtsp else '本地摄像头'}")

    setup_templates()

    use_rtsp = args.rtsp is not None
    camera_system = WebCameraVLM(camera_url=args.rtsp, use_rtsp=use_rtsp)

    if not camera_system.start_system():
        print("❌ 系统启动失败")
        return

    print(f"🌐 启动Web服务器...")
    print(f"📱 打开浏览器访问: http://localhost:{args.port}")
    print("🛑 按 Ctrl+C 停止服务")
    print()
    print("💡 功能说明:")
    print("   - 实时视频流显示")
    print("   - AI场景分析 (自动)")
    print("   - PTZ摄像头控制 (点击按钮或键盘)")
    print("   - 系统状态监控")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ Web服务器启动失败: {e}")
    finally:
        if camera_system:
            camera_system.stop_system()

if __name__ == "__main__":
    main()