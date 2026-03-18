#!/usr/bin/env python3
"""
高级监控分析仪表板
集成实时监控、AI分析、数据可视化、报警系统
"""

import cv2
import torch
import time
import threading
import queue
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import sqlite3
import io
import base64

class MonitoringDashboard:
    """高级监控分析仪表板"""

    def __init__(self):
        # 摄像头配置
        self.camera_url = "rtsp://192.168.31.146:8554/unicast"
        self.backup_camera = 0  # 备用摄像头

        # VLM模型
        self.model = None
        self.processor = None
        self.model_loaded = False

        # 视频流
        self.cap = None
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 分析相关
        self.analysis_queue = queue.Queue(maxsize=5)
        self.analysis_history = deque(maxlen=100)  # 保存最近100次分析
        self.latest_analysis = None
        self.analysis_interval = 8.0  # 分析间隔
        self.last_analysis_time = 0

        # 统计数据
        self.stats = {
            'start_time': time.time(),
            'total_frames': 0,
            'total_analyses': 0,
            'fps': 0,
            'analysis_fps': 0,
            'alerts_triggered': 0
        }

        # 数据存储
        self.db_path = "monitoring_data.db"
        self.init_database()

        # 报警配置
        self.alert_keywords = ['人', '车辆', '异常', '动作']
        self.alert_cooldown = 30  # 报警冷却时间(秒)
        self.last_alert_time = 0

        # GUI相关
        self.root = None
        self.setup_gui()

        print("🚀 高级监控分析仪表板初始化完成")

    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建分析历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    analysis_text TEXT,
                    objects TEXT,
                    persons TEXT,
                    vehicles TEXT,
                    scene TEXT,
                    analysis_time REAL,
                    frame_data BLOB
                )
            ''')

            # 创建报警记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    alert_type TEXT,
                    description TEXT,
                    frame_data BLOB
                )
            ''')

            conn.commit()
            conn.close()
            print("✅ 数据库初始化完成")

        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")

    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("🎥 高级监控分析仪表板")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2b2b2b')

        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧面板 - 视频显示
        left_frame = ttk.LabelFrame(main_frame, text="📺 实时监控", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 视频显示区域
        self.video_label = ttk.Label(left_frame, text="等待连接摄像头...", background="black")
        self.video_label.pack(pady=5)

        # 视频控制按钮
        video_controls = ttk.Frame(left_frame)
        video_controls.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(video_controls, text="▶ 开始监控", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=2)

        self.stop_btn = ttk.Button(video_controls, text="⏹ 停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        self.screenshot_btn = ttk.Button(video_controls, text="📸 截图", command=self.take_screenshot, state=tk.DISABLED)
        self.screenshot_btn.pack(side=tk.LEFT, padx=2)

        self.record_btn = ttk.Button(video_controls, text="🔴 录制", command=self.toggle_recording, state=tk.DISABLED)
        self.record_btn.pack(side=tk.LEFT, padx=2)

        # 右侧面板
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        # 分析结果面板
        analysis_frame = ttk.LabelFrame(right_frame, text="🤖 AI分析结果", padding="5")
        analysis_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 分析文本显示
        self.analysis_text = tk.Text(analysis_frame, height=8, width=40, wrap=tk.WORD, bg='#3c3c3c', fg='white')
        self.analysis_text.pack(fill=tk.BOTH, expand=True)

        # 统计信息面板
        stats_frame = ttk.LabelFrame(right_frame, text="📊 系统统计", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 5))

        self.stats_labels = {}
        stats_info = [
            ("运行时间", "uptime"),
            ("FPS", "fps"),
            ("总帧数", "total_frames"),
            ("AI分析次数", "total_analyses"),
            ("报警次数", "alerts_triggered")
        ]

        for i, (label, key) in enumerate(stats_info):
            ttk.Label(stats_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W)
            self.stats_labels[key] = ttk.Label(stats_frame, text="--")
            self.stats_labels[key].grid(row=i, column=1, sticky=tk.W, padx=(10, 0))

        # 报警面板
        alert_frame = ttk.LabelFrame(right_frame, text="⚠️ 实时报警", padding="5")
        alert_frame.pack(fill=tk.X, pady=(0, 5))

        self.alert_text = tk.Text(alert_frame, height=4, width=40, wrap=tk.WORD, bg='#4c1f1f', fg='#ff6b6b')
        self.alert_text.pack(fill=tk.BOTH, expand=True)

        # 控制面板
        control_frame = ttk.LabelFrame(right_frame, text="🎛️ 控制设置", padding="5")
        control_frame.pack(fill=tk.X)

        # 分析间隔设置
        ttk.Label(control_frame, text="分析间隔(秒):").grid(row=0, column=0, sticky=tk.W)
        self.interval_var = tk.DoubleVar(value=8.0)
        interval_scale = ttk.Scale(control_frame, from_=2.0, to=30.0, variable=self.interval_var, orient=tk.HORIZONTAL)
        interval_scale.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

        # 报警开关
        self.alert_enabled = tk.BooleanVar(value=True)
        alert_check = ttk.Checkbutton(control_frame, text="启用报警", variable=self.alert_enabled)
        alert_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 数据导出按钮
        export_btn = ttk.Button(control_frame, text="📤 导出数据", command=self.export_data)
        export_btn.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=5)

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_vlm_model(self):
        """加载VLM模型"""
        try:
            print("🤖 正在加载VLM模型...")
            self.update_analysis_text("正在加载AI模型，请稍候...")

            start_time = time.time()

            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype="auto",
                device_map="auto",
            )
            self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

            load_time = time.time() - start_time
            self.model_loaded = True

            message = f"✅ VLM模型加载完成\n耗时: {load_time:.2f}秒\n设备: {'CUDA' if torch.cuda.is_available() else 'CPU'}"
            print(message)
            self.update_analysis_text(message)

            return True

        except Exception as e:
            error_msg = f"❌ VLM模型加载失败: {str(e)}"
            print(error_msg)
            self.update_analysis_text(error_msg)
            messagebox.showerror("错误", error_msg)
            return False

    def connect_camera(self):
        """连接摄像头"""
        try:
            print(f"📡 尝试连接摄像头: {self.camera_url}")
            self.cap = cv2.VideoCapture(self.camera_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 测试连接
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"✅ 主摄像头连接成功: {w}x{h} @{fps:.1f}fps")
                return True
            else:
                print("⚠️ 主摄像头连接失败，尝试备用摄像头")
                self.cap.release()
                self.cap = cv2.VideoCapture(self.backup_camera)
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    print("✅ 备用摄像头连接成功")
                    return True
                else:
                    return False

        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            return False

    def start_monitoring(self):
        """开始监控"""
        if not self.model_loaded:
            if not self.load_vlm_model():
                return

        if not self.connect_camera():
            messagebox.showerror("错误", "无法连接摄像头")
            return

        self.running = True
        self.stats['start_time'] = time.time()

        # 启动线程
        self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)
        self.display_thread = threading.Thread(target=self.display_frames, daemon=True)
        self.stats_thread = threading.Thread(target=self.update_stats_display, daemon=True)

        self.capture_thread.start()
        self.analysis_thread.start()
        self.display_thread.start()
        self.stats_thread.start()

        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.screenshot_btn.config(state=tk.NORMAL)
        self.record_btn.config(state=tk.NORMAL)

        print("🚀 监控系统启动完成")

    def stop_monitoring(self):
        """停止监控"""
        print("🛑 正在停止监控...")
        self.running = False

        if self.cap:
            self.cap.release()

        # 更新按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.screenshot_btn.config(state=tk.DISABLED)
        self.record_btn.config(state=tk.DISABLED)

        print("✅ 监控系统已停止")

    def capture_frames(self):
        """帧捕获线程"""
        fps_counter = 0
        last_fps_time = time.time()

        while self.running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None:
                    # 更新统计
                    self.stats['total_frames'] += 1
                    fps_counter += 1
                    current_time = time.time()

                    # 计算FPS
                    if current_time - last_fps_time >= 1.0:
                        self.stats['fps'] = fps_counter / (current_time - last_fps_time)
                        fps_counter = 0
                        last_fps_time = current_time

                    # 存储当前帧
                    with self.frame_lock:
                        self.current_frame = frame.copy()

                    # 提交分析
                    self.analysis_interval = self.interval_var.get()
                    if current_time - self.last_analysis_time > self.analysis_interval:
                        if not self.analysis_queue.full():
                            self.analysis_queue.put((frame.copy(), current_time))
                            self.last_analysis_time = current_time

                else:
                    time.sleep(0.1)

            except Exception as e:
                print(f"帧捕获异常: {e}")
                time.sleep(1)

    def analysis_worker(self):
        """AI分析工作线程"""
        while self.running:
            try:
                frame, timestamp = self.analysis_queue.get(timeout=1)

                print("🔍 开始AI分析...")
                start_time = time.time()

                result = self.analyze_frame(frame)
                analysis_time = time.time() - start_time

                if result:
                    result['timestamp'] = timestamp
                    result['analysis_time'] = analysis_time

                    # 更新最新分析结果
                    self.latest_analysis = result
                    self.analysis_history.append(result)
                    self.stats['total_analyses'] += 1

                    # 保存到数据库
                    self.save_analysis_to_db(result, frame)

                    # 更新显示
                    self.update_analysis_display(result)

                    # 检查报警
                    self.check_alerts(result, frame)

                    print(f"✅ AI分析完成 ({analysis_time:.2f}秒)")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"分析异常: {e}")

    def analyze_frame(self, frame):
        """分析单帧"""
        try:
            # 保存临时图片
            temp_path = "/tmp/dashboard_frame.jpg"
            cv2.imwrite(temp_path, frame)

            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": """请详细分析这个监控画面：
1. 识别场景中的主要物体和人员
2. 描述人员的行为和动作
3. 检测是否有异常情况
4. 评估安全级别（低/中/高风险）

请以JSON格式回复：
{
    "scene_description": "场景总体描述",
    "objects": ["检测到的物体"],
    "persons": [{"count": 人数, "activities": ["活动描述"]}],
    "vehicles": ["车辆类型"],
    "anomalies": ["异常情况"],
    "risk_level": "风险级别",
    "attention_areas": ["需要关注的区域"]
}"""},
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

            generated_ids = self.model.generate(**inputs, max_new_tokens=300)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            # 解析结果
            result = self.parse_analysis_result(output_text)
            return result

        except Exception as e:
            print(f"分析失败: {e}")
            return None

    def parse_analysis_result(self, output_text):
        """解析分析结果"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                try:
                    parsed_data = json.loads(json_match.group())
                    result = {
                        "raw_text": output_text,
                        "parsed_data": parsed_data,
                        "scene_description": parsed_data.get("scene_description", ""),
                        "objects": parsed_data.get("objects", []),
                        "persons": parsed_data.get("persons", []),
                        "vehicles": parsed_data.get("vehicles", []),
                        "anomalies": parsed_data.get("anomalies", []),
                        "risk_level": parsed_data.get("risk_level", "低"),
                        "attention_areas": parsed_data.get("attention_areas", [])
                    }
                    return result
                except json.JSONDecodeError:
                    pass

            # 如果JSON解析失败，返回原始文本
            return {
                "raw_text": output_text,
                "parsed_data": None,
                "scene_description": output_text[:200] + "..." if len(output_text) > 200 else output_text,
                "objects": [],
                "persons": [],
                "vehicles": [],
                "anomalies": [],
                "risk_level": "低",
                "attention_areas": []
            }

        except Exception as e:
            print(f"解析结果失败: {e}")
            return {"error": str(e)}

    def display_frames(self):
        """显示帧线程"""
        while self.running:
            try:
                with self.frame_lock:
                    if self.current_frame is not None:
                        # 添加信息叠加
                        display_frame = self.add_info_overlay(self.current_frame.copy())

                        # 转换为PIL图像
                        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(rgb_frame)

                        # 调整大小以适应显示区域
                        display_size = (640, 480)
                        pil_image = pil_image.resize(display_size, Image.Resampling.LANCZOS)

                        # 转换为PhotoImage
                        photo = ImageTk.PhotoImage(pil_image)

                        # 更新GUI（需要在主线程中执行）
                        self.root.after(0, self.update_video_display, photo)

                time.sleep(0.033)  # ~30fps显示

            except Exception as e:
                print(f"显示异常: {e}")
                time.sleep(0.1)

    def add_info_overlay(self, frame):
        """添加信息叠加层"""
        h, w = frame.shape[:2]

        # 创建半透明覆盖层
        overlay = frame.copy()

        # 添加时间戳
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(overlay, current_time, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # 添加FPS信息
        fps_text = f"FPS: {self.stats['fps']:.1f}"
        cv2.putText(overlay, fps_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 添加分析信息
        if self.latest_analysis:
            risk_level = self.latest_analysis.get('risk_level', '低')
            color = (0, 255, 0) if risk_level == '低' else (0, 255, 255) if risk_level == '中' else (0, 0, 255)
            cv2.putText(overlay, f"风险级别: {risk_level}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 混合原始帧和覆盖层
        result = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
        return result

    def update_video_display(self, photo):
        """更新视频显示（在主线程中调用）"""
        try:
            self.video_label.configure(image=photo)
            self.video_label.image = photo  # 保持引用
        except Exception as e:
            print(f"更新显示失败: {e}")

    def update_analysis_display(self, result):
        """更新分析显示"""
        def update():
            try:
                self.analysis_text.delete(1.0, tk.END)

                display_text = f"📅 时间: {datetime.fromtimestamp(result['timestamp']).strftime('%H:%M:%S')}\n"
                display_text += f"⏱️ 分析耗时: {result['analysis_time']:.2f}秒\n\n"

                if result.get('parsed_data'):
                    display_text += f"🎬 场景: {result['scene_description']}\n\n"

                    if result['objects']:
                        display_text += f"📦 检测物体: {', '.join(result['objects'])}\n"

                    if result['persons']:
                        display_text += f"👥 人员情况: {result['persons']}\n"

                    if result['vehicles']:
                        display_text += f"🚗 车辆: {', '.join(result['vehicles'])}\n"

                    if result['anomalies']:
                        display_text += f"⚠️ 异常: {', '.join(result['anomalies'])}\n"

                    display_text += f"🚨 风险级别: {result['risk_level']}\n"
                else:
                    display_text += f"📝 原始分析:\n{result['raw_text'][:300]}..."

                self.analysis_text.insert(tk.END, display_text)

            except Exception as e:
                print(f"更新分析显示失败: {e}")

        self.root.after(0, update)

    def update_analysis_text(self, text):
        """更新分析文本"""
        def update():
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(tk.END, text)

        self.root.after(0, update)

    def update_stats_display(self):
        """更新统计显示线程"""
        while self.running:
            try:
                current_time = time.time()
                uptime = current_time - self.stats['start_time']

                # 格式化运行时间
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                # 更新显示
                def update():
                    try:
                        self.stats_labels['uptime'].config(text=uptime_str)
                        self.stats_labels['fps'].config(text=f"{self.stats['fps']:.1f}")
                        self.stats_labels['total_frames'].config(text=f"{self.stats['total_frames']:,}")
                        self.stats_labels['total_analyses'].config(text=f"{self.stats['total_analyses']}")
                        self.stats_labels['alerts_triggered'].config(text=f"{self.stats['alerts_triggered']}")
                    except:
                        pass

                self.root.after(0, update)
                time.sleep(1)

            except Exception as e:
                print(f"统计更新异常: {e}")
                time.sleep(1)

    def check_alerts(self, result, frame):
        """检查报警条件"""
        if not self.alert_enabled.get():
            return

        current_time = time.time()
        if current_time - self.last_alert_time < self.alert_cooldown:
            return

        alert_triggered = False
        alert_messages = []

        # 检查风险级别
        risk_level = result.get('risk_level', '低')
        if risk_level in ['高', '中']:
            alert_triggered = True
            alert_messages.append(f"检测到{risk_level}风险情况")

        # 检查异常
        anomalies = result.get('anomalies', [])
        if anomalies:
            alert_triggered = True
            alert_messages.append(f"检测到异常: {', '.join(anomalies)}")

        if alert_triggered:
            self.last_alert_time = current_time
            self.stats['alerts_triggered'] += 1

            alert_text = f"🚨 {datetime.now().strftime('%H:%M:%S')} - {'; '.join(alert_messages)}\n"

            # 保存报警到数据库
            self.save_alert_to_db(alert_messages, frame)

            # 更新报警显示
            def update():
                self.alert_text.insert(tk.END, alert_text)
                self.alert_text.see(tk.END)

                # 保持最多显示最近10条报警
                lines = self.alert_text.get(1.0, tk.END).split('\n')
                if len(lines) > 10:
                    self.alert_text.delete(1.0, "2.0")

            self.root.after(0, update)

            print(f"🚨 触发报警: {'; '.join(alert_messages)}")

    def save_analysis_to_db(self, result, frame):
        """保存分析结果到数据库"""
        try:
            # 压缩帧数据
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_data = buffer.tobytes()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO analysis_history (
                    timestamp, analysis_text, objects, persons, vehicles,
                    scene, analysis_time, frame_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['timestamp'],
                result['raw_text'],
                json.dumps(result.get('objects', [])),
                json.dumps(result.get('persons', [])),
                json.dumps(result.get('vehicles', [])),
                result.get('scene_description', ''),
                result['analysis_time'],
                frame_data
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"保存分析结果失败: {e}")

    def save_alert_to_db(self, alert_messages, frame):
        """保存报警到数据库"""
        try:
            # 压缩帧数据
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = buffer.tobytes()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, description, frame_data)
                VALUES (?, ?, ?, ?)
            ''', (
                time.time(),
                "风险检测",
                '; '.join(alert_messages),
                frame_data
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"保存报警失败: {e}")

    def take_screenshot(self):
        """截图"""
        try:
            with self.frame_lock:
                if self.current_frame is not None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.jpg"
                    cv2.imwrite(filename, self.current_frame)
                    messagebox.showinfo("截图", f"截图已保存: {filename}")
                    print(f"📸 截图保存: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"截图失败: {e}")

    def toggle_recording(self):
        """切换录制状态"""
        # 这里可以实现视频录制功能
        messagebox.showinfo("录制", "录制功能待实现")

    def export_data(self):
        """导出数据"""
        try:
            # 选择保存路径
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )

            if filename:
                # 导出分析历史
                export_data = {
                    "export_time": datetime.now().isoformat(),
                    "stats": self.stats.copy(),
                    "analysis_history": list(self.analysis_history)
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                messagebox.showinfo("导出", f"数据已导出到: {filename}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def on_closing(self):
        """关闭处理"""
        if self.running:
            self.stop_monitoring()
        self.root.destroy()

    def run(self):
        """运行GUI"""
        print("🖥️ 启动GUI界面...")
        self.root.mainloop()

def main():
    """主函数"""
    print("🎥 高级监控分析仪表板")
    print("=" * 50)

    # 创建并运行仪表板
    dashboard = MonitoringDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()