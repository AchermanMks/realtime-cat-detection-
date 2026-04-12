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
import numpy as np
import pygame
from ultralytics import YOLO
from flask import Flask, render_template, Response, jsonify, request
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import signal
import sys
import urllib.request
from smart_ptz_controller import SmartPTZController

app = Flask(__name__)

class AlertManager:
    """告警管理器 - 处理声光告警和通知推送"""

    def __init__(self):
        self.alert_active = False
        self.alert_count = 0
        self.last_alert_time = 0
        self.alert_cooldown = 2.0  # 告警冷却时间(秒)

        # 初始化pygame音频
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.audio_enabled = True
            print("✅ 音频告警系统已初始化")
        except Exception as e:
            print(f"⚠️ 音频告警初始化失败: {e}")
            self.audio_enabled = False

    def trigger_alert(self, alert_type, message="检测到目标"):
        """触发告警"""
        current_time = time.time()

        # 检查冷却时间
        if current_time - self.last_alert_time < self.alert_cooldown:
            return False

        self.alert_active = True
        self.alert_count += 1
        self.last_alert_time = current_time

        print(f"🚨 告警触发: {alert_type} - {message}")

        # 声音告警
        if self.audio_enabled:
            self.play_alert_sound()

        # 记录告警日志
        self.log_alert(alert_type, message)

        return True

    def play_alert_sound(self):
        """播放告警声音"""
        try:
            # 生成简单的蜂鸣声
            duration = 0.2  # 秒
            sample_rate = 22050
            frames = int(duration * sample_rate)
            frequency = 800  # Hz

            # 生成正弦波
            wave_array = np.sin(2 * np.pi * frequency * np.linspace(0, duration, frames))
            wave_array = (wave_array * 32767).astype(np.int16)
            stereo_wave = np.array([wave_array, wave_array]).T

            sound = pygame.sndarray.make_sound(stereo_wave)
            sound.play()
        except Exception as e:
            print(f"⚠️ 声音告警失败: {e}")

    def log_alert(self, alert_type, message):
        """记录告警日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] 告警类型: {alert_type}, 消息: {message}"
        print(f"📝 {log_entry}")

        # 可以扩展为文件日志或数据库存储

    def get_alert_status(self):
        """获取告警状态"""
        return {
            'alert_active': self.alert_active,
            'alert_count': self.alert_count,
            'last_alert_time': self.last_alert_time
        }

    def reset_alert_status(self):
        """重置告警状态"""
        self.alert_active = False

    def send_notification(self, webhook_url, message):
        """发送通知到企业微信/飞书 (预留接口)"""
        try:
            payload = {
                "msgtype": "text",
                "text": {"content": f"🚨监控告警: {message}"}
            }
            response = requests.post(webhook_url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ 通知推送失败: {e}")
            return False

class YOLODetector:
    """YOLOv8人体检测器"""

    def __init__(self):
        self.model = None
        self.detection_enabled = True
        self.detection_threshold = 0.5
        self.detection_stats = {
            'total_detections': 0,
            'person_count': 0,
            'last_detection_time': 0
        }

        # ROI区域设置 (多边形)
        self.roi_points = []  # [(x,y), ...] 多边形顶点
        self.roi_enabled = False

        # 人员离开检测
        self.person_tracking = {
            'last_seen_time': time.time(),
            'absence_threshold': 10.0,  # 10秒无人触发告警
            'person_present': False
        }

        self.load_model()

    def load_model(self):
        """加载YOLOv8模型"""
        try:
            print("🤖 正在加载YOLOv8模型...")
            start_time = time.time()

            # 使用轻量化版本YOLOv8n
            self.model = YOLO('yolov8n.pt')

            load_time = time.time() - start_time
            print(f"✅ YOLOv8模型加载完成，耗时: {load_time:.2f}秒")
            return True

        except Exception as e:
            print(f"❌ YOLOv8模型加载失败: {e}")
            self.detection_enabled = False
            return False

    def detect_persons(self, frame):
        """检测人体目标"""
        if not self.model or not self.detection_enabled:
            return []

        try:
            # YOLOv8检测
            results = self.model(frame, verbose=False)
            persons = []

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 只检测人(class_id=0)
                        if int(box.cls[0]) == 0 and float(box.conf[0]) > self.detection_threshold:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = float(box.conf[0])

                            persons.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': confidence,
                                'class': 'person'
                            })

            # 更新检测统计
            self.detection_stats['total_detections'] += len(persons)
            self.detection_stats['person_count'] = len(persons)
            if persons:
                self.detection_stats['last_detection_time'] = time.time()
                self.person_tracking['last_seen_time'] = time.time()
                self.person_tracking['person_present'] = True
            else:
                self.person_tracking['person_present'] = False

            return persons

        except Exception as e:
            print(f"⚠️ 人体检测失败: {e}")
            return []

    def check_roi_intrusion(self, persons):
        """检查ROI区域入侵"""
        if not self.roi_enabled or not self.roi_points:
            return []

        intruders = []
        for person in persons:
            x1, y1, x2, y2 = person['bbox']

            # 检查检测框中心点是否在ROI内
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            if self.point_in_polygon(center_x, center_y, self.roi_points):
                intruders.append(person)

        return intruders

    def check_person_absence(self):
        """检查人员离开"""
        current_time = time.time()
        time_since_last_seen = current_time - self.person_tracking['last_seen_time']

        if (not self.person_tracking['person_present'] and
            time_since_last_seen > self.person_tracking['absence_threshold']):
            return True

        return False

    def point_in_polygon(self, x, y, poly_points):
        """判断点是否在多边形内 (射线法)"""
        if len(poly_points) < 3:
            return False

        n = len(poly_points)
        inside = False

        p1x, p1y = poly_points[0]
        for i in range(1, n + 1):
            p2x, p2y = poly_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def set_roi(self, points):
        """设置ROI区域"""
        self.roi_points = points
        self.roi_enabled = len(points) >= 3
        print(f"🔧 ROI区域已设置: {len(points)} 个点")

    def draw_detections(self, frame, persons, alert_active=False):
        """在帧上绘制检测结果"""
        # 绘制ROI区域
        if self.roi_enabled and self.roi_points:
            roi_array = np.array(self.roi_points, np.int32)
            cv2.polylines(frame, [roi_array], True, (255, 255, 0), 2)  # 黄色ROI
            cv2.fillPoly(frame.copy(), [roi_array], (255, 255, 0))  # 半透明填充

        # 绘制人体检测框
        for person in persons:
            x1, y1, x2, y2 = person['bbox']
            confidence = person['confidence']

            # 检测框颜色
            color = (0, 255, 0)  # 绿色

            # 检查是否在ROI内
            if self.roi_enabled:
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                if self.point_in_polygon(center_x, center_y, self.roi_points):
                    color = (0, 0, 255)  # 红色 - ROI入侵

            # 绘制检测框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 绘制置信度标签
            label = f"Person {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # 告警状态指示
        if alert_active:
            cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 10)
            cv2.putText(frame, "ALERT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                       3, (0, 0, 255), 5)

        # 绘制统计信息
        info_text = [
            f"Person Count: {len(persons)}",
            f"ROI: {'ON' if self.roi_enabled else 'OFF'}",
            f"Total Detections: {self.detection_stats['total_detections']}"
        ]

        for i, text in enumerate(info_text):
            cv2.putText(frame, text, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX,
                       0.7, (255, 255, 255), 2)

        return frame

    def get_detection_stats(self):
        """获取检测统计"""
        return {
            **self.detection_stats,
            'roi_enabled': self.roi_enabled,
            'roi_points_count': len(self.roi_points),
            'person_present': self.person_tracking['person_present'],
            'time_since_last_seen': time.time() - self.person_tracking['last_seen_time']
        }

class PTZControllerAdapter:
    """PTZ控制器适配器 - 适配SmartPTZController到原有接口"""

    def __init__(self, smart_controller):
        self.smart_controller = smart_controller
        self.last_command_time = 0
        self.command_cooldown = 0.1  # 100ms冷却时间

    def send_command(self, action):
        """发送PTZ命令 - 适配原有接口"""
        if not self.smart_controller:
            print("⚠️ PTZ控制器未初始化")
            return False

        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            print(f"PTZ命令 {action}: 冷却中，跳过")
            return True

        # 映射命令到SmartPTZController的方法
        command_map = {
            'up': lambda: self.smart_controller.move_for_duration('up', 120, 0.3),
            'down': lambda: self.smart_controller.move_for_duration('down', 120, 0.3),
            'left': lambda: self.smart_controller.move_for_duration('left', 120, 0.3),
            'right': lambda: self.smart_controller.move_for_duration('right', 120, 0.3),
            'stop': lambda: self.smart_controller.stop_move(),
        }

        if action in command_map:
            try:
                result = command_map[action]()
                self.last_command_time = current_time
                print(f"PTZ命令 {action}: {'成功' if result else '失败'}")
                return bool(result)
            except Exception as e:
                print(f"PTZ命令失败: {e}")
                return False
        else:
            print(f"❌ 不支持的PTZ命令: {action}")
            return False

class WebCameraVLM:
    def __init__(self, camera_url=None, camera_ip=None, camera_username="admin", camera_password="admin123"):
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

        # YOLOv8检测器
        self.yolo_detector = YOLODetector()
        self.detection_enabled = True
        self.detection_interval = 0.1  # 检测间隔(秒) - 10fps检测

        # 告警管理器
        self.alert_manager = AlertManager()

        # 检测相关
        self.last_detection_time = 0
        self.current_detections = []
        self.detection_lock = threading.Lock()

        # 统计信息
        self.stats = {
            'total_frames': 0,
            'total_analyses': 0,
            'total_detections': 0,
            'start_time': time.time(),
            'camera_connected': False
        }

        # PTZ控制器 - 使用智能直接控制
        if camera_ip:
            smart_controller = SmartPTZController(camera_ip, camera_username, camera_password)
            self.ptz_controller = PTZControllerAdapter(smart_controller)
        else:
            print("⚠️ 未提供摄像头IP，PTZ控制功能将不可用")
            self.ptz_controller = PTZControllerAdapter(None)

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

                # YOLOv8人体检测
                current_time = time.time()
                if (self.detection_enabled and
                    current_time - self.last_detection_time >= self.detection_interval):

                    # 人体检测
                    persons = self.yolo_detector.detect_persons(frame)

                    # 检查ROI入侵
                    intruders = self.yolo_detector.check_roi_intrusion(persons)

                    # 检查人员离开
                    person_absent = self.yolo_detector.check_person_absence()

                    # 触发告警
                    if intruders:
                        self.alert_manager.trigger_alert(
                            "ROI入侵",
                            f"检测到{len(intruders)}人进入监控区域"
                        )

                    if person_absent:
                        self.alert_manager.trigger_alert(
                            "人员离开",
                            "监控区域无人员超过设定时间"
                        )

                    # 更新检测结果
                    with self.detection_lock:
                        self.current_detections = persons
                        self.stats['total_detections'] += len(persons)

                    self.last_detection_time = current_time

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
        """获取JPEG格式的当前帧 - 包含检测结果绘制"""
        with self.frame_lock:
            if self.current_frame is not None:
                display_frame = self.current_frame.copy()

                # 绘制检测结果
                with self.detection_lock:
                    if self.detection_enabled and self.current_detections:
                        alert_status = self.alert_manager.get_alert_status()
                        display_frame = self.yolo_detector.draw_detections(
                            display_frame,
                            self.current_detections,
                            alert_status['alert_active']
                        )

                        # 重置告警状态（视觉指示）
                        if alert_status['alert_active']:
                            self.alert_manager.reset_alert_status()

                ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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

        /* 告警动画 */
        @keyframes alertBlink {
            0% { border-color: #e53e3e; }
            50% { border-color: transparent; }
            100% { border-color: #e53e3e; }
        }

        /* ROI设置提示 */
        .roi-hint {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: #fff;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            display: none;
        }

        /* 检测状态指示 */
        .detection-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }

        .detection-indicator.active {
            background: #68d391;
            animation: pulse 2s infinite;
        }

        .detection-indicator.inactive {
            background: #f56565;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
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


                <div style="text-align: center; margin-top: 15px; font-size: 12px; color: #a0aec0;">
                    键盘快捷键: WASD移动, 空格停止
                </div>
            </div>

            <!-- 人体检测控制 -->
            <div class="ptz-panel">
                <h2>🚶 人体检测控制</h2>

                <div class="status-grid">
                    <div class="status-item">
                        <div>检测状态</div>
                        <div id="detection-status" class="status-value">关闭</div>
                    </div>
                    <div class="status-item">
                        <div>人员计数</div>
                        <div id="person-count" class="status-value">0</div>
                    </div>
                    <div class="status-item">
                        <div>ROI区域</div>
                        <div id="roi-status" class="status-value">未设置</div>
                    </div>
                    <div class="status-item">
                        <div>告警次数</div>
                        <div id="alert-count" class="status-value">0</div>
                    </div>
                </div>

                <div style="margin: 15px 0;">
                    <button class="btn" onclick="toggleDetection()" id="detection-toggle">
                        启用检测
                    </button>
                    <button class="btn" onclick="testAlert()" style="margin-left: 10px;">
                        测试告警
                    </button>
                </div>

                <div style="margin: 15px 0;">
                    <button class="btn" onclick="clearROI()" style="background: #e53e3e;">
                        清除ROI区域
                    </button>
                </div>

                <div style="text-align: center; margin-top: 10px; font-size: 12px; color: #a0aec0;">
                    双击视频画面设置ROI监控区域
                </div>
            </div>

            <!-- 检测设置 -->
            <div class="ptz-panel">
                <h2>⚙️ 检测设置</h2>

                <div style="margin: 10px 0;">
                    <label style="font-size: 14px; color: #a0aec0;">检测阈值: <span id="threshold-value">0.5</span></label>
                    <input type="range" id="detection-threshold" min="0.1" max="0.9" step="0.1" value="0.5"
                           style="width: 100%; margin-top: 5px;" onchange="updateThreshold(this.value)">
                </div>

                <div style="margin: 10px 0;">
                    <label style="font-size: 14px; color: #a0aec0;">离开超时(秒): <span id="absence-value">10</span></label>
                    <input type="range" id="absence-threshold" min="5" max="60" step="5" value="10"
                           style="width: 100%; margin-top: 5px;" onchange="updateAbsenceThreshold(this.value)">
                </div>

                <div style="text-align: center; margin-top: 10px; font-size: 12px; color: #a0aec0;">
                    实时调整检测参数
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
                        <div>检测总数</div>
                        <div id="detections-value" class="status-value">0</div>
                    </div>
                    <div class="status-item">
                        <div>运行时间</div>
                        <div id="uptime-value" class="status-value">0s</div>
                    </div>
                    <div class="status-item">
                        <div>最后检测</div>
                        <div id="last-detection-value" class="status-value">无</div>
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

        // 检测控制函数
        function toggleDetection() {
            fetch('/api/detection/toggle', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const button = document.getElementById('detection-toggle');
                        const status = document.getElementById('detection-status');

                        if (data.detection_enabled) {
                            button.textContent = '停止检测';
                            button.style.background = '#e53e3e';
                            status.textContent = '运行中';
                            status.style.color = '#68d391';
                        } else {
                            button.textContent = '启用检测';
                            button.style.background = '#68d391';
                            status.textContent = '已停止';
                            status.style.color = '#f56565';
                        }

                        console.log('检测状态切换:', data.detection_enabled ? '启用' : '停止');
                    }
                })
                .catch(error => {
                    console.error('检测切换错误:', error);
                });
        }

        function testAlert() {
            fetch('/api/alert/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    type: '手动测试',
                    message: '这是一个手动触发的测试告警'
                })
            })
                .then(response => response.json())
                .then(data => {
                    console.log('告警测试:', data.success ? '成功' : '失败');
                    if (data.success) {
                        // 临时显示告警状态
                        document.body.style.border = '5px solid red';
                        setTimeout(() => {
                            document.body.style.border = 'none';
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('告警测试错误:', error);
                });
        }

        function clearROI() {
            fetch('/api/detection/roi/clear', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('roi-status').textContent = '已清除';
                        console.log('ROI区域已清除');
                    }
                })
                .catch(error => {
                    console.error('ROI清除错误:', error);
                });
        }

        function updateThreshold(value) {
            document.getElementById('threshold-value').textContent = value;

            fetch('/api/detection/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({detection_threshold: parseFloat(value)})
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('检测阈值已更新:', value);
                    }
                })
                .catch(error => {
                    console.error('阈值更新错误:', error);
                });
        }

        function updateAbsenceThreshold(value) {
            document.getElementById('absence-value').textContent = value;

            fetch('/api/detection/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({absence_threshold: parseFloat(value)})
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('离开超时已更新:', value + '秒');
                    }
                })
                .catch(error => {
                    console.error('超时更新错误:', error);
                });
        }

        // ROI设置功能
        let roiPoints = [];
        let isSettingROI = false;

        function startROISelection() {
            roiPoints = [];
            isSettingROI = true;
            console.log('开始设置ROI区域，请在视频上点击设置多边形顶点，双击完成');
        }

        // 视频点击事件处理
        document.getElementById('video').addEventListener('dblclick', function(e) {
            if (roiPoints.length < 3) {
                startROISelection();
                return;
            }

            if (isSettingROI && roiPoints.length >= 3) {
                // 完成ROI设置
                fetch('/api/detection/roi', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({points: roiPoints})
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('roi-status').textContent = `${roiPoints.length}个点`;
                            console.log('ROI区域设置完成:', roiPoints.length + '个点');
                            isSettingROI = false;
                        }
                    })
                    .catch(error => {
                        console.error('ROI设置错误:', error);
                    });
            } else {
                startROISelection();
            }
        });

        document.getElementById('video').addEventListener('click', function(e) {
            if (isSettingROI) {
                const rect = this.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                // 转换为视频坐标
                const videoX = Math.floor(x * this.naturalWidth / rect.width);
                const videoY = Math.floor(y * this.naturalHeight / rect.height);

                roiPoints.push({x: videoX, y: videoY});
                console.log(`添加ROI点 ${roiPoints.length}: (${videoX}, ${videoY})`);

                if (roiPoints.length >= 8) {
                    // 最多8个点
                    console.log('已达到最大点数，双击完成设置');
                }
            }
        });


        // 键盘控制
        document.addEventListener('keydown', function(e) {
            switch(e.key.toLowerCase()) {
                case 'w': case 'arrowup': sendPTZ('up'); break;
                case 's': case 'arrowdown': sendPTZ('down'); break;
                case 'a': case 'arrowleft': sendPTZ('left'); break;
                case 'd': case 'arrowright': sendPTZ('right'); break;
                case ' ': e.preventDefault(); sendPTZ('stop'); break;
            }
        });

        // 更新系统状态和AI分析
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 基础状态
                    document.getElementById('fps-value').textContent = data.fps.toFixed(1);
                    document.getElementById('frames-value').textContent = data.total_frames.toLocaleString();
                    document.getElementById('analysis-value').textContent = data.total_analyses;
                    document.getElementById('detections-value').textContent = data.total_detections || 0;

                    const uptime = Math.floor(data.uptime);
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    const seconds = uptime % 60;
                    document.getElementById('uptime-value').textContent =
                        `${hours}h${minutes}m${seconds}s`;

                    // 检测状态更新
                    if (data.detection_stats) {
                        const personCount = data.detection_stats.person_count || 0;
                        document.getElementById('person-count').textContent = personCount;

                        const timeSinceLastSeen = data.detection_stats.time_since_last_seen || 0;
                        if (timeSinceLastSeen < 2) {
                            document.getElementById('last-detection-value').textContent = '刚刚';
                            document.getElementById('last-detection-value').style.color = '#68d391';
                        } else if (timeSinceLastSeen < 10) {
                            document.getElementById('last-detection-value').textContent = Math.floor(timeSinceLastSeen) + 's前';
                            document.getElementById('last-detection-value').style.color = '#fbb040';
                        } else {
                            document.getElementById('last-detection-value').textContent = '超过10s';
                            document.getElementById('last-detection-value').style.color = '#f56565';
                        }

                        // ROI状态
                        if (data.detection_stats.roi_enabled) {
                            const pointCount = data.detection_stats.roi_points_count || 0;
                            document.getElementById('roi-status').textContent = `${pointCount}个点`;
                            document.getElementById('roi-status').style.color = '#68d391';
                        }

                        // 检测状态指示器
                        if (data.detection_enabled) {
                            if (!document.getElementById('detection-toggle').textContent.includes('停止')) {
                                document.getElementById('detection-toggle').textContent = '停止检测';
                                document.getElementById('detection-toggle').style.background = '#e53e3e';
                            }
                            document.getElementById('detection-status').textContent = '运行中';
                            document.getElementById('detection-status').style.color = '#68d391';
                        }
                    }

                    // 告警状态更新
                    if (data.alert_stats) {
                        document.getElementById('alert-count').textContent = data.alert_stats.alert_count || 0;

                        // 显示活跃告警
                        if (data.alert_stats.alert_active) {
                            document.body.style.border = '3px solid #e53e3e';
                            document.body.style.animation = 'alertBlink 1s infinite';
                        } else {
                            document.body.style.border = 'none';
                            document.body.style.animation = 'none';
                        }
                    }

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

    # 获取检测统计
    detection_stats = camera_system.yolo_detector.get_detection_stats()
    alert_stats = camera_system.alert_manager.get_alert_status()

    return jsonify({
        'fps': camera_system.display_fps,
        'total_frames': camera_system.stats['total_frames'],
        'total_analyses': camera_system.stats['total_analyses'],
        'total_detections': camera_system.stats['total_detections'],
        'uptime': uptime,
        'camera_connected': camera_system.stats['camera_connected'],
        'latest_analysis': camera_system.latest_analysis,
        'detection_stats': detection_stats,
        'alert_stats': alert_stats,
        'detection_enabled': camera_system.detection_enabled
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

@app.route('/api/detection/toggle', methods=['POST'])
def toggle_detection():
    """切换检测功能开关"""
    camera_system.detection_enabled = not camera_system.detection_enabled
    return jsonify({
        'success': True,
        'detection_enabled': camera_system.detection_enabled,
        'timestamp': time.time()
    })

@app.route('/api/detection/roi', methods=['POST'])
def set_roi():
    """设置ROI区域"""
    try:
        data = request.get_json()
        points = data.get('points', [])

        # 验证点数据格式
        if not isinstance(points, list) or len(points) < 3:
            return jsonify({
                'success': False,
                'error': 'ROI区域至少需要3个点',
                'timestamp': time.time()
            })

        # 转换为整数坐标
        roi_points = []
        for point in points:
            if isinstance(point, dict) and 'x' in point and 'y' in point:
                roi_points.append((int(point['x']), int(point['y'])))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                roi_points.append((int(point[0]), int(point[1])))
            else:
                return jsonify({
                    'success': False,
                    'error': '点坐标格式错误',
                    'timestamp': time.time()
                })

        camera_system.yolo_detector.set_roi(roi_points)

        return jsonify({
            'success': True,
            'roi_points': roi_points,
            'roi_enabled': camera_system.yolo_detector.roi_enabled,
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        })

@app.route('/api/detection/roi/clear', methods=['POST'])
def clear_roi():
    """清除ROI区域"""
    camera_system.yolo_detector.roi_points = []
    camera_system.yolo_detector.roi_enabled = False
    return jsonify({
        'success': True,
        'message': 'ROI区域已清除',
        'timestamp': time.time()
    })

@app.route('/api/detection/settings', methods=['GET', 'POST'])
def detection_settings():
    """检测设置API"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            if 'detection_threshold' in data:
                threshold = float(data['detection_threshold'])
                if 0.1 <= threshold <= 0.9:
                    camera_system.yolo_detector.detection_threshold = threshold

            if 'absence_threshold' in data:
                absence_threshold = float(data['absence_threshold'])
                if absence_threshold >= 1.0:
                    camera_system.yolo_detector.person_tracking['absence_threshold'] = absence_threshold

            if 'detection_interval' in data:
                interval = float(data['detection_interval'])
                if 0.05 <= interval <= 1.0:
                    camera_system.detection_interval = interval

            return jsonify({
                'success': True,
                'message': '检测设置已更新',
                'timestamp': time.time()
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            })

    # GET请求 - 返回当前设置
    return jsonify({
        'detection_threshold': camera_system.yolo_detector.detection_threshold,
        'absence_threshold': camera_system.yolo_detector.person_tracking['absence_threshold'],
        'detection_interval': camera_system.detection_interval,
        'detection_enabled': camera_system.detection_enabled,
        'roi_enabled': camera_system.yolo_detector.roi_enabled,
        'timestamp': time.time()
    })

@app.route('/api/alert/test', methods=['POST'])
def test_alert():
    """测试告警功能"""
    try:
        data = request.get_json() or {}
        alert_type = data.get('type', '测试告警')
        message = data.get('message', '这是一个测试告警')

        success = camera_system.alert_manager.trigger_alert(alert_type, message)

        return jsonify({
            'success': success,
            'message': '告警测试完成',
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        })

@app.route('/api/alert/webhook', methods=['POST'])
def set_webhook():
    """设置Webhook通知地址（预留接口）"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url', '')
        test_message = data.get('test_message', '测试通知')

        if webhook_url:
            # 测试发送通知
            success = camera_system.alert_manager.send_notification(webhook_url, test_message)
            if success:
                # 可以在这里保存webhook_url到配置
                pass

            return jsonify({
                'success': success,
                'message': '通知测试完成' if success else '通知发送失败',
                'timestamp': time.time()
            })

        return jsonify({
            'success': False,
            'error': 'Webhook URL为空',
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
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
    parser.add_argument('--camera-ip', help='摄像头IP地址 (用于PTZ控制)')
    parser.add_argument('--camera-user', default='admin', help='摄像头用户名')
    parser.add_argument('--camera-pass', default='admin123', help='摄像头密码')
    parser.add_argument('--port', type=int, default=5000, help='Web服务器端口')
    parser.add_argument('--host', default='0.0.0.0', help='Web服务器主机')

    args = parser.parse_args()

    # 初始化摄像头系统
    camera_url = args.rtsp if args.rtsp else args.camera
    camera_system = WebCameraVLM(
        camera_url=camera_url,
        camera_ip=args.camera_ip,
        camera_username=args.camera_user,
        camera_password=args.camera_pass
    )

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