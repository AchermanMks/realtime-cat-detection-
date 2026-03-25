#!/usr/bin/env python3
"""
JOVISION摄像头监控系统 - 混合PTZ控制版本
支持物理PTZ + 数字PTZ的智能切换
"""

import cv2
import numpy as np
import time
import threading
import queue
import json
import socket
from flask import Flask, render_template, Response, jsonify, request
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import warnings
warnings.filterwarnings("ignore")

# 混合PTZ控制器
class HybridPTZController:
    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.udp_port = 34567

        # 物理PTZ状态
        self.physical_ptz_enabled = True
        self.last_physical_test = 0

        # 数字PTZ状态
        self.digital_zoom = 1.0
        self.digital_pan = 0.0
        self.digital_tilt = 0.0
        self.max_zoom = 4.0

        # 预设位置
        self.presets = {
            1: {"zoom": 1.0, "pan": 0.0, "tilt": 0.0, "name": "默认位置"},
            2: {"zoom": 2.0, "pan": -0.3, "tilt": 0.2, "name": "左上角"},
            3: {"zoom": 2.0, "pan": 0.3, "tilt": 0.2, "name": "右上角"},
            4: {"zoom": 1.5, "pan": 0.0, "tilt": -0.3, "name": "中心下方"}
        }

        self.lock = threading.Lock()
        print("🎮 混合PTZ控制器已初始化 (物理+数字)")

    def pan_left(self, speed=30):
        if self.physical_ptz_enabled and self._try_physical_ptz("pan", "left", speed):
            return True
        return self._digital_pan_left(speed)

    def pan_right(self, speed=30):
        if self.physical_ptz_enabled and self._try_physical_ptz("pan", "right", speed):
            return True
        return self._digital_pan_right(speed)

    def tilt_up(self, speed=30):
        if self.physical_ptz_enabled and self._try_physical_ptz("tilt", "up", speed):
            return True
        return self._digital_tilt_up(speed)

    def tilt_down(self, speed=30):
        if self.physical_ptz_enabled and self._try_physical_ptz("tilt", "down", speed):
            return True
        return self._digital_tilt_down(speed)

    def zoom_in(self, speed=30):
        if self.physical_ptz_enabled and self._try_physical_ptz("zoom", "in", speed):
            return True
        return self._digital_zoom_in(speed)

    def zoom_out(self, speed=30):
        if self.physical_ptz_enabled and self._try_physical_ptz("zoom", "out", speed):
            return True
        return self._digital_zoom_out(speed)

    def stop_movement(self):
        if self.physical_ptz_enabled:
            self._try_physical_ptz("stop", "all", 0)
        return True

    def goto_preset(self, preset_number):
        if preset_number in self.presets:
            preset = self.presets[preset_number]
            if self.physical_ptz_enabled and self._try_physical_preset(preset_number):
                return True
            return self._goto_digital_preset(preset)
        return False

    def _try_physical_ptz(self, command_type, direction, speed):
        try:
            command = {
                "Name": "PTZControl",
                "Login": {"UserName": self.username, "Password": self.password},
                "PTZ": {"Direction": direction.capitalize(), "Speed": speed}
            }

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            json_data = json.dumps(command).encode('utf-8')
            sock.sendto(json_data, (self.camera_ip, self.udp_port))

            response, addr = sock.recvfrom(1024)
            response_text = response.decode('utf-8', errors='ignore')
            sock.close()

            if '"Ret": "OK"' in response_text:
                return True
        except:
            pass
        return False

    def _try_physical_preset(self, preset_number):
        try:
            command = {
                "Name": "PTZControl",
                "Login": {"UserName": self.username, "Password": self.password},
                "PTZ": {"Preset": preset_number, "Action": "Goto"}
            }

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            json_data = json.dumps(command).encode('utf-8')
            sock.sendto(json_data, (self.camera_ip, self.udp_port))

            response, addr = sock.recvfrom(1024)
            response_text = response.decode('utf-8', errors='ignore')
            sock.close()

            return '"Ret": "OK"' in response_text
        except:
            return False

    def _digital_pan_left(self, speed):
        with self.lock:
            step = speed / 1000.0
            self.digital_pan = max(-1.0, self.digital_pan - step)
            return True

    def _digital_pan_right(self, speed):
        with self.lock:
            step = speed / 1000.0
            self.digital_pan = min(1.0, self.digital_pan + step)
            return True

    def _digital_tilt_up(self, speed):
        with self.lock:
            step = speed / 1000.0
            self.digital_tilt = min(1.0, self.digital_tilt + step)
            return True

    def _digital_tilt_down(self, speed):
        with self.lock:
            step = speed / 1000.0
            self.digital_tilt = max(-1.0, self.digital_tilt - step)
            return True

    def _digital_zoom_in(self, speed):
        with self.lock:
            step = speed / 1000.0
            self.digital_zoom = min(self.max_zoom, self.digital_zoom + step)
            return True

    def _digital_zoom_out(self, speed):
        with self.lock:
            step = speed / 1000.0
            self.digital_zoom = max(1.0, self.digital_zoom - step)
            return True

    def _goto_digital_preset(self, preset):
        with self.lock:
            self.digital_zoom = preset["zoom"]
            self.digital_pan = preset["pan"]
            self.digital_tilt = preset["tilt"]
            return True

    def apply_digital_ptz(self, frame):
        """对帧应用数字PTZ变换"""
        if frame is None:
            return frame

        with self.lock:
            h, w = frame.shape[:2]

            # 计算缩放和平移
            zoom_factor = self.digital_zoom
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)

            pan_offset_x = int(self.digital_pan * (w - new_w) / 2)
            tilt_offset_y = int(-self.digital_tilt * (h - new_h) / 2)

            center_x = w // 2 + pan_offset_x
            center_y = h // 2 + tilt_offset_y

            x1 = max(0, center_x - new_w // 2)
            y1 = max(0, center_y - new_h // 2)
            x2 = min(w, x1 + new_w)
            y2 = min(h, y1 + new_h)

            if x2 <= x1 or y2 <= y1:
                return frame

            cropped = frame[y1:y2, x1:x2]
            if cropped.size > 0:
                resized = cv2.resize(cropped, (w, h))
                return resized

            return frame

    def get_status(self):
        return {
            "physical_ptz_enabled": self.physical_ptz_enabled,
            "digital_zoom": round(self.digital_zoom, 2),
            "digital_pan": round(self.digital_pan, 2),
            "digital_tilt": round(self.digital_tilt, 2),
            "presets": self.presets
        }

    def set_mode(self, physical_mode):
        self.physical_ptz_enabled = physical_mode

    def reset_position(self):
        with self.lock:
            self.digital_zoom = 1.0
            self.digital_pan = 0.0
            self.digital_tilt = 0.0

# VLM分析器
class VLMAnalyzer:
    def __init__(self):
        print("🤖 初始化VLM模型...")
        self.model_name = "Qwen/Qwen2-VL-7B-Instruct"
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_name, torch_dtype=torch.float16, device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        print("✅ VLM模型加载完成")

    def analyze_frame(self, frame):
        try:
            temp_path = "/tmp/web_frame.jpg"
            cv2.imwrite(temp_path, frame)

            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": temp_path},
                    {"type": "text", "text": "描述图像中的场景和主要内容，回复要简洁清晰。"},
                ],
            }]

            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text], images=image_inputs, videos=video_inputs,
                padding=True, return_tensors="pt",
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
            return f"VLM分析异常: {e}"

# 主相机系统
class CameraSystem:
    def __init__(self):
        self.camera = None
        self.frame_queue = queue.Queue(maxsize=5)
        self.analysis_queue = queue.Queue(maxsize=3)
        self.latest_frame = None
        self.latest_analysis = {"text": "等待分析...", "timestamp": time.time()}
        self.running = True

        # 统计信息
        self.stats = {
            'total_frames': 0,
            'total_analyses': 0,
            'camera_connected': False,
            'start_time': time.time()
        }

        # 初始化组件
        self.ptz_controller = HybridPTZController()
        self.vlm_analyzer = VLMAnalyzer()

        # 启动线程
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.analysis_thread = threading.Thread(target=self._analysis_loop)

        self.camera_thread.start()
        self.analysis_thread.start()

    def _camera_loop(self):
        """摄像头捕获循环"""
        while self.running:
            try:
                if self.camera is None:
                    self.camera = cv2.VideoCapture("rtsp://admin:admin123@192.168.31.146:8554/unicast")
                    if self.camera.isOpened():
                        print("✅ 摄像头连接成功")
                        self.stats['camera_connected'] = True

                ret, frame = self.camera.read()
                if ret:
                    self.stats['total_frames'] += 1

                    # 应用数字PTZ变换
                    frame = self.ptz_controller.apply_digital_ptz(frame)

                    self.latest_frame = frame.copy()

                    # 提交分析
                    if not self.analysis_queue.full():
                        self.analysis_queue.put(frame.copy())

                    # 更新帧队列
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame.copy())

            except Exception as e:
                print(f"摄像头错误: {e}")
                self.stats['camera_connected'] = False
                time.sleep(1)

    def _analysis_loop(self):
        """VLM分析循环"""
        while self.running:
            try:
                frame = self.analysis_queue.get(timeout=5)
                result = self.vlm_analyzer.analyze_frame(frame)

                self.latest_analysis = {
                    "text": result,
                    "timestamp": time.time()
                }
                self.stats['total_analyses'] += 1

            except queue.Empty:
                continue
            except Exception as e:
                print(f"VLM分析异常: {e}")

    def get_frame(self):
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return self.latest_frame

    def cleanup(self):
        self.running = False
        if self.camera:
            self.camera.release()

# Flask应用
app = Flask(__name__)
camera_system = CameraSystem()

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>JOVISION混合PTZ控制系统</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .video-container { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .controls { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .status { background: white; border-radius: 8px; padding: 20px; }
        img { max-width: 100%; border-radius: 4px; }
        .btn-group { display: inline-block; margin: 5px; }
        button { padding: 10px 15px; margin: 2px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-ptz { background: #007bff; color: white; }
        .btn-preset { background: #28a745; color: white; }
        .btn-mode { background: #fd7e14; color: white; }
        .btn-ptz:hover { background: #0056b3; }
        .ptz-pad { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; width: 150px; margin: 10px auto; }
        .zoom-controls { text-align: center; margin: 10px; }
        .status-item { margin: 5px 0; }
        .mode-indicator { padding: 5px 10px; border-radius: 4px; display: inline-block; }
        .physical-mode { background: #d4edda; color: #155724; }
        .digital-mode { background: #cce7ff; color: #004085; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 JOVISION混合PTZ控制系统</h1>

        <div class="video-container">
            <h3>📹 实时视频流</h3>
            <img src="/video_feed" id="video-feed">
        </div>

        <div class="controls">
            <h3>🎮 PTZ控制</h3>

            <div class="btn-group">
                <button class="btn-mode" onclick="switchMode(true)">📱 物理PTZ模式</button>
                <button class="btn-mode" onclick="switchMode(false)">💻 数字PTZ模式</button>
                <button class="btn-mode" onclick="resetPosition()">🔄 重置位置</button>
            </div>

            <div class="ptz-pad">
                <div></div>
                <button class="btn-ptz" onclick="ptzControl('tilt', 'up')">⬆️</button>
                <div></div>
                <button class="btn-ptz" onclick="ptzControl('pan', 'left')">⬅️</button>
                <button class="btn-ptz" onclick="ptzControl('stop', '')">🛑</button>
                <button class="btn-ptz" onclick="ptzControl('pan', 'right')">➡️</button>
                <div></div>
                <button class="btn-ptz" onclick="ptzControl('tilt', 'down')">⬇️</button>
                <div></div>
            </div>

            <div class="zoom-controls">
                <button class="btn-ptz" onclick="ptzControl('zoom', 'out')">🔎 缩小</button>
                <button class="btn-ptz" onclick="ptzControl('zoom', 'in')">🔍 放大</button>
            </div>

            <div class="btn-group">
                <h4>📍 预设位置</h4>
                <button class="btn-preset" onclick="gotoPreset(1)">1 默认</button>
                <button class="btn-preset" onclick="gotoPreset(2)">2 左上</button>
                <button class="btn-preset" onclick="gotoPreset(3)">3 右上</button>
                <button class="btn-preset" onclick="gotoPreset(4)">4 下方</button>
            </div>
        </div>

        <div class="status">
            <h3>📊 系统状态</h3>
            <div id="status-info">加载中...</div>
        </div>
    </div>

    <script>
        // PTZ控制
        function ptzControl(command, direction) {
            fetch('/api/ptz/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: command, direction: direction, speed: 30})
            });
        }

        // 预设位置
        function gotoPreset(number) {
            fetch(`/api/ptz/preset/${number}`, {method: 'POST'});
        }

        // 切换模式
        function switchMode(physical) {
            fetch('/api/ptz/mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({physical_mode: physical})
            });
        }

        // 重置位置
        function resetPosition() {
            fetch('/api/ptz/reset', {method: 'POST'});
        }

        // 键盘控制
        document.addEventListener('keydown', function(e) {
            switch(e.key) {
                case 'ArrowUp': ptzControl('tilt', 'up'); break;
                case 'ArrowDown': ptzControl('tilt', 'down'); break;
                case 'ArrowLeft': ptzControl('pan', 'left'); break;
                case 'ArrowRight': ptzControl('pan', 'right'); break;
                case '=': case '+': ptzControl('zoom', 'in'); break;
                case '-': ptzControl('zoom', 'out'); break;
                case ' ': e.preventDefault(); ptzControl('stop', ''); break;
            }
        });

        // 更新状态
        function updateStatus() {
            fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                const ptzStatus = data.ptz_status;
                const mode = ptzStatus.physical_ptz_enabled ?
                    '<span class="mode-indicator physical-mode">📱 物理PTZ模式</span>' :
                    '<span class="mode-indicator digital-mode">💻 数字PTZ模式</span>';

                document.getElementById('status-info').innerHTML = `
                    <div class="status-item"><strong>控制模式:</strong> ${mode}</div>
                    <div class="status-item"><strong>数字缩放:</strong> ${ptzStatus.digital_zoom}x</div>
                    <div class="status-item"><strong>数字平移:</strong> ${ptzStatus.digital_pan}</div>
                    <div class="status-item"><strong>数字倾斜:</strong> ${ptzStatus.digital_tilt}</div>
                    <div class="status-item"><strong>帧数:</strong> ${data.total_frames}</div>
                    <div class="status-item"><strong>分析次数:</strong> ${data.total_analyses}</div>
                    <div class="status-item"><strong>最新分析:</strong> ${data.analysis.text}</div>
                `;
            });
        }

        // 定期更新状态
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>
    '''

@app.route('/video_feed')
def video_feed():
    def generate_frames():
        while True:
            frame = camera_system.get_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.1)

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    uptime = int(time.time() - camera_system.stats['start_time'])
    return jsonify({
        'total_frames': camera_system.stats['total_frames'],
        'total_analyses': camera_system.stats['total_analyses'],
        'uptime': uptime,
        'camera_connected': camera_system.stats['camera_connected'],
        'analysis': camera_system.latest_analysis,
        'ptz_status': camera_system.ptz_controller.get_status()
    })

@app.route('/api/ptz/control', methods=['POST'])
def ptz_control():
    try:
        data = request.get_json()
        command = data.get('command')
        direction = data.get('direction')
        speed = data.get('speed', 30)

        success = False
        if command == 'pan':
            if direction == 'left':
                success = camera_system.ptz_controller.pan_left(speed)
            elif direction == 'right':
                success = camera_system.ptz_controller.pan_right(speed)
        elif command == 'tilt':
            if direction == 'up':
                success = camera_system.ptz_controller.tilt_up(speed)
            elif direction == 'down':
                success = camera_system.ptz_controller.tilt_down(speed)
        elif command == 'zoom':
            if direction == 'in':
                success = camera_system.ptz_controller.zoom_in(speed)
            elif direction == 'out':
                success = camera_system.ptz_controller.zoom_out(speed)
        elif command == 'stop':
            success = camera_system.ptz_controller.stop_movement()

        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ptz/preset/<int:preset_number>', methods=['POST'])
def ptz_preset(preset_number):
    try:
        success = camera_system.ptz_controller.goto_preset(preset_number)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ptz/mode', methods=['POST'])
def ptz_mode():
    try:
        data = request.get_json()
        physical_mode = data.get('physical_mode', True)
        camera_system.ptz_controller.set_mode(physical_mode)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ptz/reset', methods=['POST'])
def ptz_reset():
    try:
        camera_system.ptz_controller.reset_position()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    try:
        print("🚀 启动JOVISION混合PTZ控制系统...")
        print("🌐 访问地址: http://localhost:5001")
        print("🎮 功能特性:")
        print("   • 物理PTZ控制 (继续尝试)")
        print("   • 数字PTZ控制 (立即可用)")
        print("   • 智能模式切换")
        print("   • 预设位置")
        print("   • 键盘控制: ↑↓←→ 方向, +-缩放, 空格停止")
        print("🛑 按Ctrl+C停止服务")

        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 停止服务...")
        camera_system.cleanup()
        print("✅ 服务已停止")