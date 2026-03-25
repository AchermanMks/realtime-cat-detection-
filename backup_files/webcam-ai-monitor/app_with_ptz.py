#!/usr/bin/env python3
"""
Web版实时摄像头流 + VLM分析 + 云台控制
通过浏览器查看实时画面、AI分析结果并控制摄像头云台
"""

import cv2
import torch
import time
import threading
import queue
import base64
import json
import requests
import socket
from urllib.parse import urlparse
from flask import Flask, render_template, Response, jsonify, request
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import signal
import sys

app = Flask(__name__)

class PTZController:
    """云台控制器类 - 支持多种控制协议"""

    def __init__(self, camera_ip, username="admin", password="admin"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.ptz_supported = False
        self.ptz_type = None  # 'onvif', 'hikvision', 'dahua', 'generic_http'

        # PTZ状态
        self.current_preset = 0
        self.zoom_level = 0
        self.pan_position = 0
        self.tilt_position = 0

        # 控制参数
        self.pan_speed = 50   # 水平转动速度 (1-100)
        self.tilt_speed = 50  # 垂直转动速度 (1-100)
        self.zoom_speed = 50  # 变焦速度 (1-100)

        # 预设位置
        self.presets = {
            1: "正门入口",
            2: "大厅中央",
            3: "侧门出口",
            4: "停车场",
            5: "后门区域"
        }

        self._detect_ptz_type()

    def _detect_ptz_type(self):
        """自动检测云台控制类型"""
        try:
            # 尝试检测ONVIF
            if self._test_onvif():
                self.ptz_type = 'onvif'
                self.ptz_supported = True
                print(f"✅ 检测到ONVIF云台控制: {self.camera_ip}")
                return

            # 尝试检测海康威视
            if self._test_hikvision():
                self.ptz_type = 'hikvision'
                self.ptz_supported = True
                print(f"✅ 检测到海康威视云台控制: {self.camera_ip}")
                return

            # 尝试检测大华
            if self._test_dahua():
                self.ptz_type = 'dahua'
                self.ptz_supported = True
                print(f"✅ 检测到大华云台控制: {self.camera_ip}")
                return

            # 通用HTTP控制
            if self._test_generic_http():
                self.ptz_type = 'generic_http'
                self.ptz_supported = True
                print(f"✅ 检测到通用HTTP云台控制: {self.camera_ip}")
                return

            print(f"⚠️ 未检测到云台控制支持: {self.camera_ip}")

        except Exception as e:
            print(f"❌ 云台检测失败: {e}")

    def _test_onvif(self):
        """测试ONVIF协议支持"""
        try:
            # 简单的ONVIF设备发现
            onvif_discovery_msg = """<?xml version="1.0" encoding="UTF-8"?>
            <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
                <soap:Body>
                    <wsdd:Probe xmlns:wsdd="http://schemas.xmlsoap.org/ws/2005/04/discovery"/>
                </soap:Body>
            </soap:Envelope>"""

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.sendto(onvif_discovery_msg.encode(), (self.camera_ip, 3702))
            response, addr = sock.recvfrom(1024)
            sock.close()
            return True
        except:
            return False

    def _test_hikvision(self):
        """测试海康威视API"""
        try:
            url = f"http://{self.camera_ip}/ISAPI/PTZ/channels/1/status"
            response = requests.get(url, auth=(self.username, self.password), timeout=2)
            return response.status_code in [200, 401]  # 401也表示设备存在
        except:
            return False

    def _test_dahua(self):
        """测试大华API"""
        try:
            url = f"http://{self.camera_ip}/cgi-bin/ptz.cgi?action=getCurrentProtocolCaps"
            response = requests.get(url, auth=(self.username, self.password), timeout=2)
            return response.status_code in [200, 401]
        except:
            return False

    def _test_generic_http(self):
        """测试通用HTTP控制"""
        try:
            # 尝试访问常见的PTZ端点
            endpoints = [
                f"http://{self.camera_ip}/cgi-bin/ptz.cgi",
                f"http://{self.camera_ip}/axis-cgi/com/ptz.cgi",
                f"http://{self.camera_ip}/web/cgi-bin/hi3510/ptzctrl.cgi"
            ]

            for endpoint in endpoints:
                try:
                    response = requests.head(endpoint, timeout=1)
                    if response.status_code < 500:
                        return True
                except:
                    continue
            return False
        except:
            return False

    def pan_left(self, speed=None):
        """向左转动"""
        speed = speed or self.pan_speed
        return self._send_ptz_command('pan', 'left', speed)

    def pan_right(self, speed=None):
        """向右转动"""
        speed = speed or self.pan_speed
        return self._send_ptz_command('pan', 'right', speed)

    def tilt_up(self, speed=None):
        """向上转动"""
        speed = speed or self.tilt_speed
        return self._send_ptz_command('tilt', 'up', speed)

    def tilt_down(self, speed=None):
        """向下转动"""
        speed = speed or self.tilt_speed
        return self._send_ptz_command('tilt', 'down', speed)

    def zoom_in(self, speed=None):
        """放大"""
        speed = speed or self.zoom_speed
        return self._send_ptz_command('zoom', 'in', speed)

    def zoom_out(self, speed=None):
        """缩小"""
        speed = speed or self.zoom_speed
        return self._send_ptz_command('zoom', 'out', speed)

    def stop_movement(self):
        """停止所有移动"""
        return self._send_ptz_command('stop', 'all', 0)

    def goto_preset(self, preset_number):
        """转到预设位置"""
        if preset_number in self.presets:
            result = self._send_ptz_command('preset', 'goto', preset_number)
            if result:
                self.current_preset = preset_number
            return result
        return False

    def set_preset(self, preset_number, name=None):
        """设置预设位置"""
        if name:
            self.presets[preset_number] = name
        return self._send_ptz_command('preset', 'set', preset_number)

    def _send_ptz_command(self, command_type, direction, speed):
        """发送PTZ控制命令"""
        if not self.ptz_supported:
            print("❌ 云台控制不支持")
            return False

        try:
            if self.ptz_type == 'hikvision':
                return self._send_hikvision_command(command_type, direction, speed)
            elif self.ptz_type == 'dahua':
                return self._send_dahua_command(command_type, direction, speed)
            elif self.ptz_type == 'onvif':
                return self._send_onvif_command(command_type, direction, speed)
            elif self.ptz_type == 'generic_http':
                return self._send_generic_command(command_type, direction, speed)

        except Exception as e:
            print(f"❌ PTZ命令发送失败: {e}")
            return False

        return False

    def _send_hikvision_command(self, command_type, direction, speed):
        """发送海康威视PTZ命令"""
        base_url = f"http://{self.camera_ip}/ISAPI/PTZ/channels/1"

        if command_type == 'pan':
            if direction == 'left':
                url = f"{base_url}/momentary?arg1=LEFT&arg2={speed}&arg3=1"
            else:  # right
                url = f"{base_url}/momentary?arg1=RIGHT&arg2={speed}&arg3=1"
        elif command_type == 'tilt':
            if direction == 'up':
                url = f"{base_url}/momentary?arg1=UP&arg2={speed}&arg3=1"
            else:  # down
                url = f"{base_url}/momentary?arg1=DOWN&arg2={speed}&arg3=1"
        elif command_type == 'zoom':
            if direction == 'in':
                url = f"{base_url}/momentary?arg1=ZOOMIN&arg2={speed}&arg3=1"
            else:  # out
                url = f"{base_url}/momentary?arg1=ZOOMOUT&arg2={speed}&arg3=1"
        elif command_type == 'stop':
            url = f"{base_url}/momentary?arg1=STOP&arg2=0&arg3=0"
        elif command_type == 'preset':
            if direction == 'goto':
                url = f"{base_url}/presets/{speed}/goto"
            else:  # set
                url = f"{base_url}/presets/{speed}"
        else:
            return False

        try:
            response = requests.put(url, auth=(self.username, self.password), timeout=3)
            return response.status_code == 200
        except:
            return False

    def _send_dahua_command(self, command_type, direction, speed):
        """发送大华PTZ命令"""
        base_url = f"http://{self.camera_ip}/cgi-bin/ptz.cgi"

        # 大华命令映射
        command_map = {
            ('pan', 'left'): f"?action=start&channel=0&code=Left&arg1={speed}&arg2={speed}",
            ('pan', 'right'): f"?action=start&channel=0&code=Right&arg1={speed}&arg2={speed}",
            ('tilt', 'up'): f"?action=start&channel=0&code=Up&arg1={speed}&arg2={speed}",
            ('tilt', 'down'): f"?action=start&channel=0&code=Down&arg1={speed}&arg2={speed}",
            ('zoom', 'in'): f"?action=start&channel=0&code=ZoomTele&arg1={speed}&arg2={speed}",
            ('zoom', 'out'): f"?action=start&channel=0&code=ZoomWide&arg1={speed}&arg2={speed}",
            ('stop', 'all'): "?action=stop&channel=0",
        }

        if command_type == 'preset':
            if direction == 'goto':
                query = f"?action=start&channel=0&code=GotoPreset&arg1=0&arg2={speed}"
            else:  # set
                query = f"?action=start&channel=0&code=SetPreset&arg1=0&arg2={speed}"
        else:
            query = command_map.get((command_type, direction))

        if not query:
            return False

        try:
            url = base_url + query
            response = requests.get(url, auth=(self.username, self.password), timeout=3)
            return "OK" in response.text
        except:
            return False

    def _send_onvif_command(self, command_type, direction, speed):
        """发送ONVIF PTZ命令"""
        # 这里需要完整的ONVIF实现，比较复杂
        # 暂时返回模拟结果
        print(f"🔄 ONVIF命令: {command_type} {direction} {speed}")
        time.sleep(0.1)  # 模拟网络延迟
        return True

    def _send_generic_command(self, command_type, direction, speed):
        """发送通用HTTP PTZ命令"""
        # 通用PTZ控制，适用于多种摄像头
        command_map = {
            ('pan', 'left'): f"/cgi-bin/ptz.cgi?move=left&speed={speed}",
            ('pan', 'right'): f"/cgi-bin/ptz.cgi?move=right&speed={speed}",
            ('tilt', 'up'): f"/cgi-bin/ptz.cgi?move=up&speed={speed}",
            ('tilt', 'down'): f"/cgi-bin/ptz.cgi?move=down&speed={speed}",
            ('zoom', 'in'): f"/cgi-bin/ptz.cgi?zoom=in&speed={speed}",
            ('zoom', 'out'): f"/cgi-bin/ptz.cgi?zoom=out&speed={speed}",
            ('stop', 'all'): "/cgi-bin/ptz.cgi?move=stop",
        }

        path = command_map.get((command_type, direction))
        if not path:
            return False

        try:
            url = f"http://{self.camera_ip}{path}"
            response = requests.get(url, auth=(self.username, self.password), timeout=3)
            return response.status_code == 200
        except:
            return False

    def get_status(self):
        """获取云台状态"""
        return {
            'supported': self.ptz_supported,
            'type': self.ptz_type,
            'current_preset': self.current_preset,
            'presets': self.presets,
            'zoom_level': self.zoom_level,
            'pan_position': self.pan_position,
            'tilt_position': self.tilt_position,
            'speeds': {
                'pan': self.pan_speed,
                'tilt': self.tilt_speed,
                'zoom': self.zoom_speed
            }
        }


class WebCameraVLM:
    def __init__(self):
        self.camera_url = "rtsp://192.168.31.146:8554/unicast"
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

        # 云台控制器
        self.ptz_controller = None
        self._init_ptz_controller()

    def _init_ptz_controller(self):
        """初始化云台控制器"""
        try:
            # 从RTSP URL提取IP地址
            if self.camera_url.startswith('rtsp://'):
                parsed = urlparse(self.camera_url)
                camera_ip = parsed.hostname

                if camera_ip:
                    print(f"🔧 初始化云台控制器: {camera_ip}")
                    self.ptz_controller = PTZController(camera_ip)
                else:
                    print("⚠️ 无法从RTSP URL提取IP地址")
            else:
                print("⚠️ 仅支持RTSP摄像头的云台控制")

        except Exception as e:
            print(f"❌ 云台控制器初始化失败: {e}")

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
        try:
            print(f"📡 连接摄像头: {self.camera_url}")
            self.cap = cv2.VideoCapture(self.camera_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 测试连接
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"✅ 摄像头连接成功: {w}x{h} @{fps}fps")
                self.stats['camera_connected'] = True
                return True
            else:
                print("❌ 无法获取测试帧")
                return False

        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            return False

    def capture_frames(self):
        """视频帧捕获线程"""
        while self.running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None:
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

                else:
                    print("⚠️ 读取帧失败")
                    time.sleep(0.1)

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

# 全局实例
camera_system = WebCameraVLM()

# Web路由
@app.route('/')
def index():
    """主页"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>🎥 实时摄像头监控 + AI分析 + 云台控制</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0; padding: 20px;
            background: #1a1a1a; color: #fff;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .main-content {
            display: grid;
            grid-template-columns: 2fr 1fr 300px;
            gap: 20px;
            align-items: start;
        }
        .video-panel {
            background: #2a2a2a; border-radius: 10px; padding: 15px;
        }
        .analysis-panel {
            background: #2a2a2a; border-radius: 10px; padding: 15px;
        }
        .control-panel {
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
            display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px; margin: 15px 0;
        }
        .stat-item {
            background: #444; padding: 10px; border-radius: 6px; text-align: center;
        }
        .stat-value { font-size: 18px; font-weight: bold; color: #00ff88; }
        .stat-label { font-size: 11px; color: #ccc; }

        /* PTZ控制样式 */
        .ptz-controls {
            text-align: center;
        }
        .direction-pad {
            display: grid;
            grid-template-areas:
                ". up ."
                "left stop right"
                ". down .";
            gap: 5px;
            margin: 20px 0;
            max-width: 150px;
            margin-left: auto;
            margin-right: auto;
        }
        .ptz-btn {
            background: #555; color: white; border: none;
            padding: 15px; border-radius: 8px; cursor: pointer;
            font-size: 16px; transition: all 0.2s;
        }
        .ptz-btn:hover { background: #00ff88; color: #000; }
        .ptz-btn:active { transform: scale(0.95); }
        .btn-up { grid-area: up; }
        .btn-down { grid-area: down; }
        .btn-left { grid-area: left; }
        .btn-right { grid-area: right; }
        .btn-stop { grid-area: stop; background: #ff4444; }

        .zoom-controls {
            display: flex; gap: 10px; margin: 15px 0; justify-content: center;
        }
        .zoom-btn {
            background: #666; color: white; border: none;
            padding: 12px 20px; border-radius: 6px; cursor: pointer;
            flex: 1; transition: all 0.2s;
        }
        .zoom-btn:hover { background: #00ff88; color: #000; }

        .preset-controls {
            margin: 15px 0;
        }
        .preset-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
            margin: 10px 0;
        }
        .preset-btn {
            background: #666; color: white; border: none;
            padding: 10px; border-radius: 6px; cursor: pointer;
            font-size: 12px; transition: all 0.2s;
        }
        .preset-btn:hover { background: #00ff88; color: #000; }
        .preset-btn.active { background: #00ff88; color: #000; }

        .speed-control {
            margin: 15px 0;
        }
        .speed-slider {
            width: 100%; margin: 8px 0;
            background: #555; height: 6px; border-radius: 3px;
        }

        .ptz-status {
            background: #333; padding: 10px; border-radius: 6px;
            margin: 15px 0; font-size: 12px;
        }

        h1, h2, h3 { color: #00ff88; margin-top: 0; }
        .timestamp { color: #888; font-size: 12px; }
        .loading { text-align: center; padding: 50px; color: #888; }

        @media (max-width: 1200px) {
            .main-content {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto auto;
            }
            .control-panel { order: 2; }
            .analysis-panel { order: 3; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 实时摄像头监控 + AI分析 + 云台控制</h1>
            <p>基于VLM的智能视觉分析 | 实时流处理 | PTZ云台控制</p>
        </div>

        <div class="main-content">
            <!-- 视频显示面板 -->
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

            <!-- AI分析面板 -->
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

            <!-- 云台控制面板 -->
            <div class="control-panel">
                <h3>🎮 云台控制</h3>

                <div class="ptz-status" id="ptz-status">
                    <div>状态: <span id="ptz-supported">检测中...</span></div>
                    <div>类型: <span id="ptz-type">--</span></div>
                    <div>当前预设: <span id="current-preset">--</span></div>
                </div>

                <div class="ptz-controls">
                    <h4>方向控制</h4>
                    <div class="direction-pad">
                        <button class="ptz-btn btn-up" onclick="ptzCommand('tilt', 'up')">⬆</button>
                        <button class="ptz-btn btn-left" onclick="ptzCommand('pan', 'left')">⬅</button>
                        <button class="ptz-btn btn-stop" onclick="ptzCommand('stop', 'all')">⏹</button>
                        <button class="ptz-btn btn-right" onclick="ptzCommand('pan', 'right')">➡</button>
                        <button class="ptz-btn btn-down" onclick="ptzCommand('tilt', 'down')">⬇</button>
                    </div>

                    <h4>变焦控制</h4>
                    <div class="zoom-controls">
                        <button class="zoom-btn" onclick="ptzCommand('zoom', 'in')">🔍+ 放大</button>
                        <button class="zoom-btn" onclick="ptzCommand('zoom', 'out')">🔍- 缩小</button>
                    </div>

                    <h4>预设位置</h4>
                    <div class="preset-grid" id="preset-grid">
                        <button class="preset-btn" onclick="gotoPreset(1)">1: 正门</button>
                        <button class="preset-btn" onclick="gotoPreset(2)">2: 大厅</button>
                        <button class="preset-btn" onclick="gotoPreset(3)">3: 侧门</button>
                        <button class="preset-btn" onclick="gotoPreset(4)">4: 停车场</button>
                    </div>

                    <h4>速度控制</h4>
                    <div class="speed-control">
                        <label>移动速度: <span id="speed-value">50</span></label>
                        <input type="range" id="speed-slider" class="speed-slider"
                               min="1" max="100" value="50"
                               oninput="updateSpeed(this.value)">
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentSpeed = 50;

        // 定期更新数据
        function updateData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 更新系统统计
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('frames').textContent = data.total_frames.toLocaleString();
                    document.getElementById('analyses').textContent = data.total_analyses;

                    // 运行时间
                    const uptimeSeconds = Math.floor(data.uptime);
                    const hours = Math.floor(uptimeSeconds / 3600);
                    const minutes = Math.floor((uptimeSeconds % 3600) / 60);
                    const seconds = uptimeSeconds % 60;
                    document.getElementById('uptime').textContent =
                        hours + 'h ' + minutes + 'm ' + seconds + 's';

                    // 更新AI分析结果
                    if (data.analysis && data.analysis.text) {
                        document.getElementById('analysis').innerHTML =
                            '<strong>AI分析结果:</strong><br>' + data.analysis.text;

                        const updateTime = new Date(data.analysis.timestamp * 1000);
                        document.getElementById('last-update').textContent =
                            updateTime.toLocaleTimeString();
                        document.getElementById('analysis-time').textContent =
                            data.analysis.analysis_time.toFixed(2);
                    }

                    // 更新PTZ状态
                    if (data.ptz_status) {
                        document.getElementById('ptz-supported').textContent =
                            data.ptz_status.supported ? '✅ 支持' : '❌ 不支持';
                        document.getElementById('ptz-type').textContent =
                            data.ptz_status.type || '--';
                        document.getElementById('current-preset').textContent =
                            data.ptz_status.current_preset || '--';

                        // 更新预设按钮状态
                        updatePresetButtons(data.ptz_status.current_preset);
                    }
                })
                .catch(error => {
                    console.error('Error updating data:', error);
                });
        }

        // PTZ控制命令
        function ptzCommand(type, direction) {
            const data = {
                command: type,
                direction: direction,
                speed: currentSpeed
            };

            fetch('/api/ptz/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (!result.success) {
                    alert('PTZ控制失败: ' + result.error);
                }
            })
            .catch(error => {
                console.error('PTZ控制错误:', error);
                alert('PTZ控制失败');
            });
        }

        // 转到预设位置
        function gotoPreset(presetNumber) {
            fetch('/api/ptz/preset/' + presetNumber, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    updatePresetButtons(presetNumber);
                } else {
                    alert('预设位置控制失败: ' + result.error);
                }
            })
            .catch(error => {
                console.error('预设位置控制错误:', error);
            });
        }

        // 更新预设按钮状态
        function updatePresetButtons(activePreset) {
            const buttons = document.querySelectorAll('.preset-btn');
            buttons.forEach((btn, index) => {
                btn.classList.toggle('active', (index + 1) === activePreset);
            });
        }

        // 更新速度
        function updateSpeed(value) {
            currentSpeed = parseInt(value);
            document.getElementById('speed-value').textContent = value;
        }

        // 键盘控制
        document.addEventListener('keydown', function(event) {
            switch(event.key) {
                case 'ArrowUp':
                    event.preventDefault();
                    ptzCommand('tilt', 'up');
                    break;
                case 'ArrowDown':
                    event.preventDefault();
                    ptzCommand('tilt', 'down');
                    break;
                case 'ArrowLeft':
                    event.preventDefault();
                    ptzCommand('pan', 'left');
                    break;
                case 'ArrowRight':
                    event.preventDefault();
                    ptzCommand('pan', 'right');
                    break;
                case ' ':
                    event.preventDefault();
                    ptzCommand('stop', 'all');
                    break;
                case '+':
                case '=':
                    event.preventDefault();
                    ptzCommand('zoom', 'in');
                    break;
                case '-':
                    event.preventDefault();
                    ptzCommand('zoom', 'out');
                    break;
            }
        });

        // 停止移动当按键释放时
        document.addEventListener('keyup', function(event) {
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
                setTimeout(() => ptzCommand('stop', 'all'), 100);
            }
        });

        // 每2秒更新一次数据
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

    # 获取PTZ状态
    ptz_status = None
    if camera_system.ptz_controller:
        ptz_status = camera_system.ptz_controller.get_status()

    return jsonify({
        'fps': camera_system.display_fps,
        'total_frames': camera_system.stats['total_frames'],
        'total_analyses': camera_system.stats['total_analyses'],
        'uptime': uptime,
        'camera_connected': camera_system.stats['camera_connected'],
        'analysis': camera_system.latest_analysis,
        'ptz_status': ptz_status
    })

@app.route('/api/ptz/control', methods=['POST'])
def ptz_control():
    """PTZ控制API"""
    if not camera_system.ptz_controller:
        return jsonify({'success': False, 'error': 'PTZ控制器未初始化'})

    if not camera_system.ptz_controller.ptz_supported:
        return jsonify({'success': False, 'error': 'PTZ功能不支持'})

    try:
        data = request.get_json()
        command = data.get('command')
        direction = data.get('direction')
        speed = data.get('speed', 50)

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
def ptz_goto_preset(preset_number):
    """转到预设位置API"""
    if not camera_system.ptz_controller:
        return jsonify({'success': False, 'error': 'PTZ控制器未初始化'})

    if not camera_system.ptz_controller.ptz_supported:
        return jsonify({'success': False, 'error': 'PTZ功能不支持'})

    try:
        success = camera_system.ptz_controller.goto_preset(preset_number)
        return jsonify({'success': success})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ptz/preset/<int:preset_number>/set', methods=['POST'])
def ptz_set_preset(preset_number):
    """设置预设位置API"""
    if not camera_system.ptz_controller:
        return jsonify({'success': False, 'error': 'PTZ控制器未初始化'})

    if not camera_system.ptz_controller.ptz_supported:
        return jsonify({'success': False, 'error': 'PTZ功能不支持'})

    try:
        data = request.get_json() or {}
        name = data.get('name')
        success = camera_system.ptz_controller.set_preset(preset_number, name)
        return jsonify({'success': success})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ptz/status')
def ptz_status():
    """PTZ状态API"""
    if not camera_system.ptz_controller:
        return jsonify({'supported': False, 'error': 'PTZ控制器未初始化'})

    return jsonify(camera_system.ptz_controller.get_status())

def signal_handler(signum, frame):
    """信号处理"""
    camera_system.stop_system()
    sys.exit(0)

def main():
    """主函数"""
    print("🌐 Web版摄像头系统 + 云台控制启动中...")

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动摄像头系统
    if not camera_system.start_system():
        print("❌ 系统启动失败")
        return

    # 启动Web服务器
    print("🌐 启动Web服务器...")
    print("📱 打开浏览器访问: http://localhost:5000")
    print("🎮 支持键盘控制:")
    print("   ↑↓←→ 方向键控制云台")
    print("   + - 控制变焦")
    print("   空格键停止移动")
    print("🛑 按 Ctrl+C 停止服务")

    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 接收到中断信号")
    finally:
        camera_system.stop_system()

if __name__ == "__main__":
    main()