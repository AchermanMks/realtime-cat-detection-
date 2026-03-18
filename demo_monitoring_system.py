#!/usr/bin/env python3
"""
演示版监控系统
使用虚拟摄像头和模拟数据进行功能演示
"""

import cv2
import torch
import time
import threading
import queue
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import random
import math

class DemoMonitoringSystem:
    """演示版监控系统"""

    def __init__(self):
        # 模拟数据
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 虚拟摄像头设置
        self.frame_width = 640
        self.frame_height = 480
        self.fps_target = 15

        # 模拟分析数据
        self.analysis_history = deque(maxlen=50)
        self.latest_analysis = None
        self.analysis_interval = 5.0  # 分析间隔
        self.last_analysis_time = 0

        # 统计数据
        self.stats = {
            'start_time': time.time(),
            'total_frames': 0,
            'total_analyses': 0,
            'fps': 0,
            'alerts_triggered': 0
        }

        # 模拟场景数据
        self.scenarios = [
            {
                "scene": "办公室环境",
                "objects": ["桌子", "椅子", "电脑", "文件"],
                "persons": [{"count": 2, "activities": ["工作", "讨论"]}],
                "vehicles": [],
                "risk_level": "低",
                "anomalies": []
            },
            {
                "scene": "停车场",
                "objects": ["汽车", "路灯", "标识牌"],
                "persons": [{"count": 1, "activities": ["走路"]}],
                "vehicles": ["轿车", "SUV"],
                "risk_level": "低",
                "anomalies": []
            },
            {
                "scene": "实验室",
                "objects": ["实验台", "设备", "化学品"],
                "persons": [{"count": 3, "activities": ["实验", "记录"]}],
                "vehicles": [],
                "risk_level": "中",
                "anomalies": ["未戴防护用品"]
            },
            {
                "scene": "仓库",
                "objects": ["货架", "箱子", "叉车"],
                "persons": [{"count": 1, "activities": ["搬运"]}],
                "vehicles": ["叉车"],
                "risk_level": "高",
                "anomalies": ["违规操作", "安全隐患"]
            }
        ]
        self.current_scenario = 0

        # GUI相关
        self.root = None
        self.setup_gui()

        print("🎬 演示版监控系统初始化完成")

    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("🎬 演示版监控分析系统")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1e1e1e')

        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')

        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧面板 - 视频显示
        left_frame = ttk.LabelFrame(main_frame, text="📺 虚拟摄像头监控", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 视频显示区域
        self.video_label = ttk.Label(left_frame, text="点击开始按钮启动虚拟摄像头", background="black")
        self.video_label.pack(pady=5)

        # 控制按钮
        controls_frame = ttk.Frame(left_frame)
        controls_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(controls_frame, text="▶ 开始演示", command=self.start_demo)
        self.start_btn.pack(side=tk.LEFT, padx=2)

        self.stop_btn = ttk.Button(controls_frame, text="⏹ 停止演示", command=self.stop_demo, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        self.scenario_btn = ttk.Button(controls_frame, text="🔄 切换场景", command=self.switch_scenario, state=tk.DISABLED)
        self.scenario_btn.pack(side=tk.LEFT, padx=2)

        self.screenshot_btn = ttk.Button(controls_frame, text="📸 截图", command=self.take_screenshot, state=tk.DISABLED)
        self.screenshot_btn.pack(side=tk.LEFT, padx=2)

        # 右侧面板
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        # AI分析结果面板
        analysis_frame = ttk.LabelFrame(right_frame, text="🤖 AI分析结果", padding="5")
        analysis_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.analysis_text = scrolledtext.ScrolledText(
            analysis_frame,
            height=12,
            width=45,
            wrap=tk.WORD,
            bg='#2d2d2d',
            fg='white',
            insertbackground='white'
        )
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
            ttk.Label(stats_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, padx=2)
            self.stats_labels[key] = ttk.Label(stats_frame, text="--", foreground="cyan")
            self.stats_labels[key].grid(row=i, column=1, sticky=tk.W, padx=(10, 2))

        # 场景信息面板
        scene_frame = ttk.LabelFrame(right_frame, text="🎬 当前场景", padding="5")
        scene_frame.pack(fill=tk.X, pady=(0, 5))

        self.scene_label = ttk.Label(scene_frame, text="未开始", wraplength=200)
        self.scene_label.pack(fill=tk.X)

        # 报警面板
        alert_frame = ttk.LabelFrame(right_frame, text="⚠️ 实时报警", padding="5")
        alert_frame.pack(fill=tk.X)

        self.alert_text = tk.Text(
            alert_frame,
            height=6,
            width=45,
            wrap=tk.WORD,
            bg='#2d1f1f',
            fg='#ff6b6b',
            insertbackground='#ff6b6b'
        )
        self.alert_text.pack(fill=tk.BOTH, expand=True)

    def generate_virtual_frame(self):
        """生成虚拟摄像头帧"""
        # 创建基础背景
        frame = np.ones((self.frame_height, self.frame_width, 3), dtype=np.uint8) * 40

        # 添加渐变背景
        for y in range(self.frame_height):
            intensity = int(40 + (y / self.frame_height) * 60)
            frame[y, :] = [intensity, intensity-10, intensity-20]

        # 根据当前场景添加不同元素
        scenario = self.scenarios[self.current_scenario]
        current_time = time.time()

        # 添加移动的形状（模拟目标）
        if "人" in str(scenario["persons"]) or scenario["persons"]:
            # 绘制人形轮廓
            person_x = int(200 + 100 * math.sin(current_time * 0.5))
            person_y = int(300 + 50 * math.cos(current_time * 0.3))
            cv2.circle(frame, (person_x, person_y), 15, (100, 150, 200), -1)  # 头部
            cv2.rectangle(frame, (person_x-10, person_y+15), (person_x+10, person_y+50), (100, 150, 200), -1)  # 身体

        if scenario["vehicles"]:
            # 绘制车辆轮廓
            car_x = int(400 + 80 * math.sin(current_time * 0.7))
            car_y = 350
            cv2.rectangle(frame, (car_x-30, car_y-15), (car_x+30, car_y+15), (150, 100, 200), -1)

        if "设备" in scenario["objects"]:
            # 绘制设备
            cv2.rectangle(frame, (50, 100), (150, 200), (200, 200, 100), -1)

        # 添加噪声（模拟真实摄像头）
        noise = np.random.randint(-15, 15, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        return frame

    def start_demo(self):
        """开始演示"""
        self.running = True
        self.stats['start_time'] = time.time()

        # 启动线程
        self.frame_thread = threading.Thread(target=self.frame_generator, daemon=True)
        self.analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)
        self.display_thread = threading.Thread(target=self.display_frames, daemon=True)
        self.stats_thread = threading.Thread(target=self.update_stats_display, daemon=True)

        self.frame_thread.start()
        self.analysis_thread.start()
        self.display_thread.start()
        self.stats_thread.start()

        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.scenario_btn.config(state=tk.NORMAL)
        self.screenshot_btn.config(state=tk.NORMAL)

        # 更新场景信息
        self.update_scene_display()

        print("🎬 演示开始")

    def stop_demo(self):
        """停止演示"""
        self.running = False

        # 更新按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.scenario_btn.config(state=tk.DISABLED)
        self.screenshot_btn.config(state=tk.DISABLED)

        print("🛑 演示停止")

    def frame_generator(self):
        """帧生成线程"""
        fps_counter = 0
        last_fps_time = time.time()

        while self.running:
            start_time = time.time()

            # 生成虚拟帧
            frame = self.generate_virtual_frame()

            # 添加时间戳和信息叠加
            frame = self.add_info_overlay(frame)

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

            # 控制帧率
            frame_time = time.time() - start_time
            target_frame_time = 1.0 / self.fps_target
            if frame_time < target_frame_time:
                time.sleep(target_frame_time - frame_time)

    def analysis_worker(self):
        """模拟AI分析工作线程"""
        while self.running:
            try:
                current_time = time.time()

                if current_time - self.last_analysis_time > self.analysis_interval:
                    print("🔍 开始模拟AI分析...")

                    # 模拟分析延迟
                    analysis_start = time.time()
                    time.sleep(random.uniform(1.0, 3.0))  # 模拟分析时间
                    analysis_time = time.time() - analysis_start

                    # 生成模拟分析结果
                    scenario = self.scenarios[self.current_scenario]
                    result = {
                        'timestamp': current_time,
                        'analysis_time': analysis_time,
                        'scene_description': scenario['scene'],
                        'objects': scenario['objects'],
                        'persons': scenario['persons'],
                        'vehicles': scenario['vehicles'],
                        'risk_level': scenario['risk_level'],
                        'anomalies': scenario['anomalies'],
                        'confidence': random.uniform(0.7, 0.95)
                    }

                    # 更新最新分析结果
                    self.latest_analysis = result
                    self.analysis_history.append(result)
                    self.stats['total_analyses'] += 1
                    self.last_analysis_time = current_time

                    # 更新分析显示
                    self.update_analysis_display(result)

                    # 检查报警
                    if result['risk_level'] in ['中', '高'] or result['anomalies']:
                        self.trigger_alert(result)

                    print(f"✅ 模拟AI分析完成 ({analysis_time:.2f}秒)")

                time.sleep(1)

            except Exception as e:
                print(f"分析异常: {e}")
                time.sleep(1)

    def add_info_overlay(self, frame):
        """添加信息叠加层"""
        overlay = frame.copy()
        h, w = frame.shape[:2]

        # 时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(overlay, timestamp, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # FPS信息
        fps_text = f"FPS: {self.stats['fps']:.1f}"
        cv2.putText(overlay, fps_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # 场景信息
        scenario = self.scenarios[self.current_scenario]
        scene_text = f"Scene: {scenario['scene']}"
        cv2.putText(overlay, scene_text, (10, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # 风险级别
        risk_text = f"Risk: {scenario['risk_level']}"
        color = (0, 255, 0) if scenario['risk_level'] == '低' else (0, 255, 255) if scenario['risk_level'] == '中' else (0, 0, 255)
        cv2.putText(overlay, risk_text, (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return overlay

    def display_frames(self):
        """显示帧线程"""
        while self.running:
            try:
                with self.frame_lock:
                    if self.current_frame is not None:
                        # 转换为PIL图像
                        rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(rgb_frame)

                        # 调整大小
                        display_size = (640, 480)
                        pil_image = pil_image.resize(display_size, Image.Resampling.LANCZOS)

                        # 转换为PhotoImage
                        photo = ImageTk.PhotoImage(pil_image)

                        # 更新GUI
                        self.root.after(0, self.update_video_display, photo)

                time.sleep(1.0 / 30)  # ~30fps显示

            except Exception as e:
                print(f"显示异常: {e}")
                time.sleep(0.1)

    def update_video_display(self, photo):
        """更新视频显示"""
        try:
            self.video_label.configure(image=photo)
            self.video_label.image = photo
        except Exception as e:
            print(f"更新显示失败: {e}")

    def update_analysis_display(self, result):
        """更新分析显示"""
        def update():
            try:
                self.analysis_text.delete(1.0, tk.END)

                display_text = f"📅 分析时间: {datetime.fromtimestamp(result['timestamp']).strftime('%H:%M:%S')}\n"
                display_text += f"⏱️ 耗时: {result['analysis_time']:.2f}秒\n"
                display_text += f"🎯 置信度: {result['confidence']:.1%}\n\n"

                display_text += f"🎬 场景: {result['scene_description']}\n\n"

                if result['objects']:
                    display_text += f"📦 检测物体:\n"
                    for obj in result['objects']:
                        display_text += f"  • {obj}\n"
                    display_text += "\n"

                if result['persons']:
                    display_text += f"👥 人员情况:\n"
                    for person in result['persons']:
                        if isinstance(person, dict):
                            display_text += f"  • 人数: {person.get('count', 0)}\n"
                            activities = person.get('activities', [])
                            if activities:
                                display_text += f"  • 活动: {', '.join(activities)}\n"
                    display_text += "\n"

                if result['vehicles']:
                    display_text += f"🚗 车辆: {', '.join(result['vehicles'])}\n\n"

                if result['anomalies']:
                    display_text += f"⚠️ 异常情况:\n"
                    for anomaly in result['anomalies']:
                        display_text += f"  • {anomaly}\n"
                    display_text += "\n"

                display_text += f"🚨 风险级别: {result['risk_level']}"

                self.analysis_text.insert(tk.END, display_text)

            except Exception as e:
                print(f"更新分析显示失败: {e}")

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

    def switch_scenario(self):
        """切换场景"""
        if self.running:
            self.current_scenario = (self.current_scenario + 1) % len(self.scenarios)
            self.update_scene_display()
            print(f"🔄 切换到场景: {self.scenarios[self.current_scenario]['scene']}")

    def update_scene_display(self):
        """更新场景显示"""
        scenario = self.scenarios[self.current_scenario]
        scene_text = f"🎬 {scenario['scene']}\n"
        scene_text += f"🚨 风险级别: {scenario['risk_level']}\n"

        if scenario['objects']:
            scene_text += f"📦 物体: {', '.join(scenario['objects'][:3])}{'...' if len(scenario['objects']) > 3 else ''}\n"

        if scenario['anomalies']:
            scene_text += f"⚠️ 异常: {len(scenario['anomalies'])}项"

        self.scene_label.config(text=scene_text)

    def trigger_alert(self, result):
        """触发报警"""
        self.stats['alerts_triggered'] += 1

        alert_time = datetime.now().strftime('%H:%M:%S')
        alert_msg = f"🚨 {alert_time} - {result['risk_level']}风险\n"

        if result['anomalies']:
            alert_msg += f"异常: {', '.join(result['anomalies'])}\n"

        alert_msg += f"场景: {result['scene_description']}\n\n"

        def update_alert():
            self.alert_text.insert(tk.END, alert_msg)
            self.alert_text.see(tk.END)

            # 保持最新10条报警
            content = self.alert_text.get(1.0, tk.END)
            lines = content.split('\n')
            if len(lines) > 40:  # 假设每条报警4行
                self.alert_text.delete(1.0, "10.0")

        self.root.after(0, update_alert)

    def take_screenshot(self):
        """截图"""
        try:
            with self.frame_lock:
                if self.current_frame is not None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"demo_screenshot_{timestamp}.jpg"
                    cv2.imwrite(filename, self.current_frame)
                    messagebox.showinfo("截图", f"截图已保存: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"截图失败: {e}")

    def run(self):
        """运行演示系统"""
        print("🎬 启动演示版监控系统...")

        # 添加使用说明
        info_text = """
🎬 演示版监控分析系统使用说明:

1. 点击 "开始演示" 启动虚拟摄像头
2. 点击 "切换场景" 体验不同监控场景
3. 观察AI分析结果和报警系统
4. 可以截图保存当前画面

本系统演示了完整的监控分析功能:
• 实时视频处理
• AI视觉分析
• 风险评估
• 报警系统
• 统计数据

注意: 这是演示版本，使用虚拟数据
实际部署时会连接真实摄像头和AI模型
        """

        self.analysis_text.insert(tk.END, info_text)

        self.root.mainloop()

def main():
    """主函数"""
    print("🎬 演示版监控分析系统")
    print("=" * 50)

    demo = DemoMonitoringSystem()
    demo.run()

if __name__ == "__main__":
    main()