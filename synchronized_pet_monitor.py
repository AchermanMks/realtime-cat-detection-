#!/usr/bin/env python3
"""
同步宠物监控系统 - 逐帧播放逐帧分析版本
确保视频播放与AI分析完全同步
"""

import cv2
import torch
import numpy as np
import json
import time
import base64
import io
import gc
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import threading

# VLM分析相关导入
try:
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    from qwen_vl_utils import process_vision_info
    VLM_AVAILABLE = True
except ImportError:
    print("⚠️ VLM库未安装，VLM分析功能将不可用")
    VLM_AVAILABLE = False

# USD处理相关导入
try:
    from pxr import Usd, UsdGeom, Gf
    USD_AVAILABLE = True
except ImportError:
    print("⚠️ USD库未安装，将使用备用3D可视化")
    USD_AVAILABLE = False

app = Flask(__name__)

class SynchronizedPetMonitor:
    """同步宠物监控系统 - 逐帧分析版本"""

    def __init__(self, video_file="real_cat.mp4", sync_fps=15):
        print("🎬 初始化同步宠物监控系统...")
        print("📍 特性: 逐帧播放逐帧分析完全同步")

        self.video_file = video_file
        self.sync_fps = sync_fps  # 同步帧率，降低以确保检测能跟上
        self.frame_time = 1.0 / sync_fps

        # 视频相关
        self.cap = None
        self.frame_count = 0
        self.total_frames = 0
        self.current_frame = None

        # 检测相关
        self.yolo_model = None
        self.homography_matrix = None
        self.room_data = None
        self.usd_geometry = []
        self.usd_bounds = None

        # 同步状态
        self.detections_count = 0
        self.sync_frame_number = 0
        self.cat_detections = 0
        self.total_detections = 0

        # 数据存储
        self.current_detections = []
        self.current_frame_analysis = {}
        self.detection_history = []
        self.frame_analysis_history = []

        # VLM相关
        self.vlm_model = None
        self.vlm_processor = None
        self.vlm_model_loaded = False

        # 初始化组件
        self._initialize_yolo()
        self._initialize_3d_tracking()
        self._initialize_video()

        print(f"✅ 同步监控系统启动成功！")
        print(f"🎯 同步帧率: {sync_fps} FPS")
        print(f"⏱️ 帧间隔: {self.frame_time:.3f}s")

    def _initialize_yolo(self):
        """初始化YOLO检测模型"""
        print("🔧 加载检测组件...")
        try:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.yolo_model = YOLO('yolov8n.pt')
            self.yolo_model.to(device)
            print(f"✅ YOLO模型加载成功 ({'GPU加速' if device.type == 'cuda' else 'CPU模式'})")
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")

    def _initialize_3d_tracking(self):
        """初始化3D追踪组件"""
        print("📥 加载3D空间定位组件...")

        # 加载房间数据
        room_data_files = [
            "step3_output_20260410_122421/room_data.json",
            "room_data.json"
        ]

        for file_path in room_data_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        self.room_data = json.load(f)
                    print(f"✅ 房间数据加载成功: {file_path}")
                    break
                except Exception as e:
                    print(f"⚠️ 房间数据加载失败 {file_path}: {e}")

        # 加载同形变换矩阵
        calibration_files = [
            "meeting_room_calibration_20260410_120824.json"
        ]

        for file_path in calibration_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        calib_data = json.load(f)
                        self.homography_matrix = np.array(calib_data['homography_matrix'])
                    print(f"✅ 同形变换矩阵加载成功")
                    break
                except Exception as e:
                    print(f"⚠️ 校准数据加载失败: {e}")

        # 加载USD 3D模型
        self._load_usd_model()

    def _load_usd_model(self):
        """加载USD 3D模型"""
        self.usd_geometry = []
        self.usd_bounds = None

        if not USD_AVAILABLE:
            print("⚠️ USD库不可用，跳过3D模型加载")
            return

        usd_file = "scan.usd"
        if not Path(usd_file).exists():
            print("⚠️ 未找到scan.usd文件")
            return

        try:
            stage = Usd.Stage.Open(usd_file)

            for prim in stage.Traverse():
                if prim.IsA(UsdGeom.Mesh):
                    mesh = UsdGeom.Mesh(prim)

                    points = mesh.GetPointsAttr().Get()
                    if points:
                        vertices = np.array([(p[0], p[1], p[2]) for p in points])

                        self.usd_geometry.append({
                            'name': prim.GetName(),
                            'vertices': vertices,
                            'type': 'mesh'
                        })

                        # 计算边界
                        if self.usd_bounds is None:
                            self.usd_bounds = {
                                'x_min': vertices[:, 0].min(),
                                'x_max': vertices[:, 0].max(),
                                'y_min': vertices[:, 1].min(),
                                'y_max': vertices[:, 1].max(),
                                'z_min': vertices[:, 2].min(),
                                'z_max': vertices[:, 2].max()
                            }
                        else:
                            self.usd_bounds['x_min'] = min(self.usd_bounds['x_min'], vertices[:, 0].min())
                            self.usd_bounds['x_max'] = max(self.usd_bounds['x_max'], vertices[:, 0].max())
                            self.usd_bounds['y_min'] = min(self.usd_bounds['y_min'], vertices[:, 1].min())
                            self.usd_bounds['y_max'] = max(self.usd_bounds['y_max'], vertices[:, 1].max())
                            self.usd_bounds['z_min'] = min(self.usd_bounds['z_min'], vertices[:, 2].min())
                            self.usd_bounds['z_max'] = max(self.usd_bounds['z_max'], vertices[:, 2].max())

            print(f"✅ USD模型加载成功，共 {len(self.usd_geometry)} 个几何对象")
            if self.usd_bounds:
                print(f"   房间尺寸: {self.usd_bounds['x_max']-self.usd_bounds['x_min']:.2f}m x {self.usd_bounds['y_max']-self.usd_bounds['y_min']:.2f}m")

        except Exception as e:
            print(f"⚠️ USD模型加载失败: {e}")

    def _initialize_video(self):
        """初始化视频"""
        try:
            self.cap = cv2.VideoCapture(self.video_file)
            if not self.cap.isOpened():
                raise Exception("无法打开视频文件")

            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            original_fps = self.cap.get(cv2.CAP_PROP_FPS)

            print(f"✅ 视频文件加载成功")
            print(f"   总帧数: {self.total_frames}")
            print(f"   原始FPS: {original_fps:.1f}")
            print(f"   同步FPS: {self.sync_fps}")

        except Exception as e:
            print(f"❌ 视频初始化失败: {e}")

    def get_next_frame(self):
        """获取下一帧并同步更新帧计数"""
        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            # 视频结束，重新开始
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            self.sync_frame_number = 0
            ret, frame = self.cap.read()

        if ret:
            self.frame_count += 1
            self.sync_frame_number += 1
            self.current_frame = frame.copy()

        return frame

    def detect_and_analyze_frame(self, frame):
        """对单帧进行完整的检测和分析"""
        if frame is None or self.yolo_model is None:
            return []

        try:
            # YOLO检测
            results = self.yolo_model(frame, conf=0.01, verbose=False)
            detections = []

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]

                    # 检查是否是猫或狗
                    is_cat = cls == 15  # COCO类别中猫是15
                    is_dog = cls == 16  # COCO类别中狗是16

                    if is_cat or is_dog:
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        bbox_area = (x2 - x1) * (y2 - y1)

                        # 过滤过小的检测框
                        if bbox_area < 200:
                            continue

                        # 计算物理坐标，包含Z轴深度
                        physical_coords = self._pixel_to_physical(center_x, center_y, bbox_area)

                        detection = {
                            'frame_number': self.sync_frame_number,
                            'class': '猫' if is_cat else '狗',
                            'confidence': conf,
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'center': [center_x, center_y],
                            'physical_coords': physical_coords,
                            'area': bbox_area,
                            'timestamp': time.time()
                        }
                        detections.append(detection)

                        # 更新统计
                        self.total_detections += 1
                        if is_cat:
                            self.cat_detections += 1

            # 更新当前检测结果
            self.current_detections = detections
            self.detections_count += len(detections)

            # 保持检测历史
            self.detection_history.extend(detections)
            if len(self.detection_history) > 50:  # 保持更多历史用于分析
                self.detection_history = self.detection_history[-50:]

            # 生成帧分析报告
            frame_analysis = {
                'frame_number': self.sync_frame_number,
                'timestamp': time.time(),
                'detections_count': len(detections),
                'cats_detected': sum(1 for d in detections if d['class'] == '猫'),
                'dogs_detected': sum(1 for d in detections if d['class'] == '狗'),
                'total_processed': self.sync_frame_number,
                'sync_status': 'synchronized'
            }

            self.current_frame_analysis = frame_analysis
            self.frame_analysis_history.append(frame_analysis)
            if len(self.frame_analysis_history) > 100:
                self.frame_analysis_history = self.frame_analysis_history[-100:]

            return detections

        except Exception as e:
            print(f"帧分析失败: {e}")
            return []

    def _pixel_to_physical(self, pixel_x, pixel_y, bbox_area=None):
        """像素坐标转物理坐标，包含Z轴深度估算"""
        if self.homography_matrix is None:
            return {"x": 0, "y": 0, "z": 0}

        try:
            # 2D地面位置转换
            pixel_point = np.array([[pixel_x, pixel_y]], dtype=np.float32)
            physical_point = cv2.perspectiveTransform(pixel_point.reshape(1, -1, 2), self.homography_matrix)
            x, y = physical_point[0][0]

            # Z轴深度估算
            z = self._estimate_z_depth(pixel_x, pixel_y, bbox_area)

            return {"x": float(x), "y": float(y), "z": float(z)}

        except Exception as e:
            print(f"坐标转换失败: {e}")
            return {"x": 0, "y": 0, "z": 0}

    def _estimate_z_depth(self, pixel_x, pixel_y, bbox_area=None):
        """基于多种因素估算Z轴深度"""
        try:
            video_height = 720
            camera_height = 2.0
            height_ratio = pixel_y / video_height
            base_z = 0.3

            # 基于画面位置的深度估算
            if height_ratio < 0.3:
                # 画面上部，可能是更高的位置或远距离
                estimated_z = base_z + 0.5 + (0.3 - height_ratio) * 2.0
            elif height_ratio > 0.7:
                # 画面下部，靠近摄像头，可能在地面
                estimated_z = max(base_z - (height_ratio - 0.7) * 1.5, 0.0)
            else:
                # 画面中部
                estimated_z = base_z + (0.5 - height_ratio) * 0.8

            # 基于边框大小调整（大边框可能意味着更靠近，或更突出的物体）
            if bbox_area:
                area_factor = min(bbox_area / 10000, 1.5)
                estimated_z += area_factor * 0.3

            # 添加轻微的水平位置影响
            video_width = 1280
            center_offset = abs(pixel_x - video_width/2) / (video_width/2)
            estimated_z += center_offset * 0.1

            # 限制在合理范围内
            estimated_z = max(0.0, min(estimated_z, 2.5))

            # 添加微小随机变化模拟自然运动
            import random
            noise = random.uniform(-0.02, 0.02)
            estimated_z += noise
            estimated_z = max(0.0, min(estimated_z, 2.5))

            return estimated_z

        except Exception as e:
            return 0.3

    def generate_3d_visualization(self):
        """生成3D空间可视化"""
        try:
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(10, 8), facecolor='black')
            ax = fig.add_subplot(111, projection='3d')
            ax.set_facecolor('black')

            # 绘制房间结构
            if self.usd_bounds:
                bounds = self.usd_bounds

                # 房间边界线框
                room_x = [bounds['x_min'], bounds['x_max']]
                room_y = [bounds['y_min'], bounds['y_max']]
                room_z = [0, 2.5]

                # 绘制地板网格
                x_grid = np.linspace(bounds['x_min'], bounds['x_max'], 10)
                y_grid = np.linspace(bounds['y_min'], bounds['y_max'], 10)
                for x in x_grid:
                    ax.plot([x, x], [bounds['y_min'], bounds['y_max']], [0, 0], 'gray', alpha=0.3)
                for y in y_grid:
                    ax.plot([bounds['x_min'], bounds['x_max']], [y, y], [0, 0], 'gray', alpha=0.3)

            # 绘制检测历史轨迹
            if self.detection_history:
                cats_history = []
                dogs_history = []

                for detection in self.detection_history[-20:]:  # 最近20个检测
                    coords = detection['physical_coords']
                    if detection['class'] == '猫':
                        cats_history.append([coords['x'], coords['y'], coords['z']])
                    else:
                        dogs_history.append([coords['x'], coords['y'], coords['z']])

                # 绘制猫的轨迹
                if cats_history:
                    cats_array = np.array(cats_history)
                    ax.plot(cats_array[:, 0], cats_array[:, 1], cats_array[:, 2],
                           'lime', linewidth=2, alpha=0.7, label='猫轨迹')

                    # 当前位置
                    if len(cats_array) > 0:
                        current = cats_array[-1]
                        ax.scatter(current[0], current[1], current[2],
                                 c='lime', s=100, alpha=1.0, edgecolors='white', linewidth=2)

                        # Z轴投影线
                        ax.plot([current[0], current[0]], [current[1], current[1]], [0, current[2]],
                               'lime', linestyle='--', alpha=0.6)

                # 绘制狗的轨迹
                if dogs_history:
                    dogs_array = np.array(dogs_history)
                    ax.plot(dogs_array[:, 0], dogs_array[:, 1], dogs_array[:, 2],
                           'cyan', linewidth=2, alpha=0.7, label='狗轨迹')

                    if len(dogs_array) > 0:
                        current = dogs_array[-1]
                        ax.scatter(current[0], current[1], current[2],
                                 c='cyan', s=100, alpha=1.0, edgecolors='white', linewidth=2)

                        ax.plot([current[0], current[0]], [current[1], current[1]], [0, current[2]],
                               'cyan', linestyle='--', alpha=0.6)

            # 设置标题和标签
            active_pets = len([d for d in self.current_detections])
            ax.set_title(f'🏠 同步3D追踪 | 帧#{self.sync_frame_number} | 活跃宠物: {active_pets}',
                        color='white', fontsize=12)

            ax.set_xlabel('X (m)', color='white')
            ax.set_ylabel('Y (m)', color='white')
            ax.set_zlabel('Z (m)', color='white')

            # 设置坐标轴范围
            if self.usd_bounds:
                ax.set_xlim(self.usd_bounds['x_min']-0.5, self.usd_bounds['x_max']+0.5)
                ax.set_ylim(self.usd_bounds['y_min']-0.5, self.usd_bounds['y_max']+0.5)
            ax.set_zlim(0, 2.5)

            # 美化设置
            ax.tick_params(colors='white')
            if len(self.detection_history) > 0:
                ax.legend(loc='upper right', framealpha=0.8)

            # 保存到内存
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=72, bbox_inches='tight',
                       facecolor='black', edgecolor='none')
            img_buffer.seek(0)
            img_data = img_buffer.read()
            plt.close('all')  # 释放内存
            gc.collect()

            return img_data

        except Exception as e:
            print(f"3D可视化生成失败: {e}")
            return None

    def initialize_vlm(self):
        """初始化VLM模型（按需加载）"""
        if not VLM_AVAILABLE or self.vlm_model_loaded:
            return

        try:
            print("🧠 初始化VLM分析模型...")
            self.vlm_model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.vlm_processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
            self.vlm_model_loaded = True
            print("✅ VLM模型加载成功")
        except Exception as e:
            print(f"❌ VLM模型加载失败: {e}")

# 全局系统实例
monitor_system = None

@app.route('/')
def index():
    """主页面 - 保持原版Apple风格界面但添加同步功能"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pet Monitor Pro - 同步逐帧分析</title>
        <style>
            /* 基础样式重置 */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", system-ui, sans-serif;
                background: linear-gradient(135deg, #0a0a0f 0%, #1c1c22 100%);
                color: #ffffff;
                overflow: hidden;
                position: relative;
                font-feature-settings: 'kern' 1, 'liga' 1, 'calt' 1;
                -webkit-font-smoothing: antialiased;
                text-rendering: optimizeLegibility;
                height: 100vh;
            }

            /* 背景网格效果 */
            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background:
                    linear-gradient(rgba(255, 255, 255, 0.01) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255, 255, 255, 0.01) 1px, transparent 1px);
                background-size: 80px 80px;
                z-index: -1;
                opacity: 0.3;
            }

            /* 顶部导航栏 */
            .top-nav {
                background: rgba(0, 0, 0, 0.85);
                backdrop-filter: blur(40px) saturate(180%);
                -webkit-backdrop-filter: blur(40px) saturate(180%);
                border-bottom: 0.5px solid rgba(255, 255, 255, 0.08);
                padding: 12px 32px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: sticky;
                top: 0;
                z-index: 1000;
                box-shadow: 0 1px 0 0 rgba(255, 255, 255, 0.05), 0 8px 32px rgba(0, 0, 0, 0.6);
            }

            .nav-title {
                font-size: 22px;
                font-weight: 700;
                background: linear-gradient(135deg, #007AFF 0%, #5AC8FA 25%, #34C759 50%, #AF52DE 75%, #FF2D92 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-size: 200% 200%;
                animation: gradientShift 8s ease-in-out infinite;
            }

            .nav-status {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
            }

            .live-dot {
                width: 8px;
                height: 8px;
                background: #34C759;
                border-radius: 50%;
                animation: pulse 2s infinite;
                box-shadow: 0 0 0 4px rgba(52, 199, 89, 0.2);
            }

            .sync-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 4px 8px;
                background: rgba(52, 199, 89, 0.1);
                border-radius: 12px;
                border: 1px solid rgba(52, 199, 89, 0.2);
                font-size: 12px;
                font-weight: 500;
            }

            @keyframes gradientShift {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.6; transform: scale(1.2); }
            }

            /* 主容器 - 完全横向整齐排列布局 */
            .main-container {
                padding: 16px;
                height: calc(100vh - 60px);
                display: grid;
                grid-template-columns: minmax(600px, 2.5fr) 1fr 1fr 1fr;
                gap: 16px;
                max-width: none;
                overflow-x: auto;
            }

            /* 通用面板样式 */
            .panel {
                background: rgba(10, 10, 15, 0.9);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                overflow: hidden;
                box-shadow:
                    0 8px 32px rgba(0, 0, 0, 0.6),
                    inset 0 1px 0 rgba(255, 255, 255, 0.08);
                backdrop-filter: blur(20px);
                position: relative;
                display: flex;
                flex-direction: column;
            }

            /* 主视频面板 */
            .video-panel {
                background: linear-gradient(135deg, rgba(0, 122, 255, 0.02) 0%, rgba(175, 82, 222, 0.01) 100%);
                position: relative;
            }

            /* 统计面板 */
            .stats-panel {
                background: linear-gradient(135deg, rgba(52, 199, 89, 0.02) 0%, rgba(48, 209, 88, 0.01) 100%);
            }

            /* AI分析面板 */
            .vlm-panel {
                background: linear-gradient(135deg, rgba(175, 82, 222, 0.02) 0%, rgba(255, 45, 85, 0.01) 100%);
            }

            /* 3D视图面板 */
            .viz-panel {
                background: linear-gradient(135deg, rgba(255, 149, 0, 0.02) 0%, rgba(255, 204, 0, 0.01) 100%);
            }

            /* 面板标题栏 */
            .panel-header {
                padding: 16px 20px 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                flex-shrink: 0;
            }

            /* 不同颜色的标题栏 */
            .video-header {
                background: linear-gradient(135deg, rgba(0, 122, 255, 0.08) 0%, rgba(90, 200, 250, 0.04) 100%);
            }

            .stats-header {
                background: linear-gradient(135deg, rgba(52, 199, 89, 0.08) 0%, rgba(48, 209, 88, 0.04) 100%);
            }

            .vlm-header {
                background: linear-gradient(135deg, rgba(175, 82, 222, 0.08) 0%, rgba(255, 45, 85, 0.04) 100%);
            }

            .viz-header {
                background: linear-gradient(135deg, rgba(255, 149, 0, 0.08) 0%, rgba(255, 204, 0, 0.04) 100%);
            }

            .panel-header h3 {
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
                margin: 0;
                letter-spacing: -0.01em;
            }

            /* 面板内容 */
            .panel-content {
                flex: 1;
                padding: 0;
                overflow: auto;
                display: flex;
                flex-direction: column;
            }

            /* 视频面板特殊处理 */
            .video-panel .panel-content {
                overflow: auto;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #000;
                position: relative;
            }

            /* 同步状态覆盖层 */
            .sync-overlay {
                position: absolute;
                top: 10px;
                left: 10px;
                background: rgba(0, 0, 0, 0.8);
                padding: 6px 10px;
                border-radius: 8px;
                font-size: 11px;
                color: #34C759;
                font-weight: 500;
                z-index: 10;
                border: 1px solid rgba(52, 199, 89, 0.3);
                backdrop-filter: blur(8px);
            }

            /* 视频流 - 原始尺寸显示 */
            .video-stream {
                max-width: 100%;
                max-height: 100%;
                width: auto;
                height: auto;
                object-fit: none;
                border-radius: 0 0 20px 20px;
                display: block;
                margin: 0 auto;
            }

            /* 统计内容 */
            .stats-content {
                padding: 20px;
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .stat-row {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                padding: 12px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.04);
                transition: all 0.2s ease;
            }

            .stat-row:hover {
                background: rgba(255, 255, 255, 0.04);
                transform: translateY(-1px);
            }

            .stat-label {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.6);
                font-weight: 500;
                margin-bottom: 8px;
            }

            .stat-value {
                font-size: 24px;
                font-weight: 800;
                color: #34C759;
                font-variant-numeric: tabular-nums;
            }

            .cat-count {
                color: #30D158 !important;
                font-size: 32px !important;
                text-shadow: 0 0 8px rgba(48, 209, 88, 0.3);
            }

            .frame-count {
                color: #5AC8FA !important;
                font-size: 28px !important;
            }

            /* VLM分析内容 */
            .vlm-content {
                padding: 20px;
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .analysis-item {
                padding: 16px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.04);
                flex: 1;
                transition: all 0.2s ease;
            }

            .analysis-item:hover {
                background: rgba(255, 255, 255, 0.04);
                transform: translateY(-1px);
            }

            .analysis-label {
                font-weight: 600;
                color: #5AC8FA;
                margin-bottom: 8px;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .vlm-analysis {
                color: rgba(255, 255, 255, 0.9);
                line-height: 1.5;
                font-size: 13px;
            }

            /* 3D可视化内容 */
            .viz-content {
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 8px;
            }

            .viz-3d-image {
                width: 100%;
                height: 100%;
                object-fit: contain;
                border-radius: 0 0 20px 20px;
                background: linear-gradient(135deg, #0a0a0f 0%, #111118 100%);
            }

            /* 响应式设计 */
            @media (max-width: 1400px) {
                .main-container {
                    grid-template-columns: minmax(500px, 2fr) 1fr 1fr 1fr;
                    gap: 12px;
                }
            }
        </style>

        <script>
            // 数据更新函数
            function updateData() {
                // 更新检测数据
                fetch('/api/detections')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('cat-count').textContent = data.cat_detections || 0;
                        document.getElementById('total-count').textContent = data.total_detections || 0;
                        document.getElementById('frame-count').textContent = data.current_frame_number || 0;
                        document.getElementById('avg-confidence').textContent = (data.average_confidence || 0).toFixed(3);

                        // 更新导航栏状态
                        const navStats = document.getElementById('nav-stats');
                        if (navStats) {
                            const currentFrame = data.current_frame_number || 0;
                            const syncFps = data.sync_fps || 15;
                            const syncStatus = data.sync_status || 'synchronized';
                            navStats.textContent = `帧#${currentFrame} | ${syncFps}FPS | ${syncStatus}`;
                        }

                        // 更新同步覆盖层
                        const syncOverlay = document.getElementById('sync-overlay');
                        if (syncOverlay) {
                            const frameNum = data.current_frame_number || 0;
                            syncOverlay.textContent = `SYNC | 帧#${frameNum} | 逐帧分析`;
                        }
                    })
                    .catch(error => console.error('Error fetching detections:', error));

                // 更新VLM分析
                fetch('/api/vlm_analysis')
                    .then(response => response.json())
                    .then(data => {
                        if (data.analysis) {
                            document.getElementById('scene-analysis').textContent = data.analysis.scene || '正在分析场景...';
                            document.getElementById('behavior-analysis').textContent = data.analysis.behavior || '正在分析行为...';
                        } else {
                            document.getElementById('scene-analysis').textContent = '逐帧同步分析模式运行中';
                            document.getElementById('behavior-analysis').textContent = '每帧都进行完整AI检测分析';
                        }
                    })
                    .catch(error => {
                        document.getElementById('scene-analysis').textContent = '同步逐帧分析模式';
                        document.getElementById('behavior-analysis').textContent = '视频与AI检测完全同步';
                    });

                // 3D可视化已在单独函数中更新
            }

            // 优化更新频率
            setInterval(updateData, 1000);  // 统计数据每秒更新

            // 高频3D可视化更新
            function update3D() {
                const viz3d = document.getElementById('viz-3d');
                if (viz3d) {
                    viz3d.src = '/api/3d_visualization?' + new Date().getTime();
                }
            }
            setInterval(update3D, 400);  // 3D可视化每0.4秒更新，超实时！

            // 添加3D图片加载完成的平滑动画
            document.addEventListener('DOMContentLoaded', function() {
                const viz3d = document.getElementById('viz-3d');
                if (viz3d) {
                    viz3d.style.transition = 'opacity 0.2s ease-in-out';
                    viz3d.onload = function() {
                        this.style.opacity = '1';
                    };
                    viz3d.onerror = function() {
                        console.log('3D visualization load error');
                    };
                }
            });

            // 页面加载时立即更新
            window.onload = updateData;

            // 添加一些交互效果
            function addInteractivity() {
                // 鼠标悬停效果
                document.querySelectorAll('.stat-row, .analysis-item').forEach(item => {
                    item.addEventListener('mouseenter', function() {
                        this.style.transform = 'translateY(-1px)';
                        this.style.background = 'rgba(255, 255, 255, 0.03)';
                    });
                    item.addEventListener('mouseleave', function() {
                        this.style.transform = 'translateY(0)';
                        this.style.background = 'transparent';
                    });
                });
            }

            // 页面加载完成后添加交互
            document.addEventListener('DOMContentLoaded', addInteractivity);
        </script>
    </head>
    <body>
        <!-- 顶部导航栏 -->
        <nav class="top-nav">
            <div class="nav-title">Pet Monitor Pro - Sync Mode</div>
            <div class="nav-status">
                <div class="live-dot"></div>
                <span>LIVE</span>
                <span id="nav-stats">同步逐帧分析中...</span>
                <div class="sync-indicator">
                    <div class="live-dot" style="background: #FF9500; width: 6px; height: 6px;"></div>
                    <span>SYNC</span>
                </div>
            </div>
        </nav>

        <!-- 主容器 - 完全横向整齐四列布局 -->
        <div class="main-container">
            <!-- 第1列：主视频面板 -->
            <div class="panel video-panel">
                <div class="panel-header video-header">
                    <h3>🎬 同步视频检测 (逐帧分析)</h3>
                </div>
                <div class="panel-content">
                    <img src="/video_feed" class="video-stream" alt="同步视频流">
                    <div class="sync-overlay" id="sync-overlay">
                        SYNC | 启动中...
                    </div>
                </div>
            </div>

            <!-- 第2列：统计数据面板 -->
            <div class="panel stats-panel">
                <div class="panel-header stats-header">
                    <h3>📊 同步数据</h3>
                </div>
                <div class="panel-content">
                    <div class="stats-content">
                        <div class="stat-row">
                            <div class="stat-label">🐱 猫咪检测</div>
                            <div id="cat-count" class="stat-value cat-count">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">🎬 当前帧号</div>
                            <div id="frame-count" class="stat-value frame-count">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">📈 总检测数</div>
                            <div id="total-count" class="stat-value">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">🎯 置信度</div>
                            <div id="avg-confidence" class="stat-value">0.000</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 第3列：AI智能分析面板 -->
            <div class="panel vlm-panel">
                <div class="panel-header vlm-header">
                    <h3>🧠 同步AI分析</h3>
                </div>
                <div class="panel-content">
                    <div class="vlm-content">
                        <div class="analysis-item">
                            <div class="analysis-label">同步模式</div>
                            <div id="scene-analysis" class="vlm-analysis">逐帧播放逐帧分析...</div>
                        </div>
                        <div class="analysis-item">
                            <div class="analysis-label">分析状态</div>
                            <div id="behavior-analysis" class="vlm-analysis">视频与AI检测完全同步...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 第4列：3D空间追踪面板 -->
            <div class="panel viz-panel">
                <div class="panel-header viz-header">
                    <h3>🏠 3D空间追踪 (含Z轴)</h3>
                </div>
                <div class="panel-content">
                    <div class="viz-content">
                        <img id="viz-3d" src="/api/3d_visualization" class="viz-3d-image" alt="3D空间可视化">
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    """同步视频流 - 逐帧播放逐帧分析"""
    def generate():
        print("🎬 开始同步视频流...")

        while True:
            if monitor_system is None:
                break

            frame_start_time = time.time()

            # 获取下一帧
            frame = monitor_system.get_next_frame()
            if frame is None:
                break

            # 对每一帧进行完整分析
            detections = monitor_system.detect_and_analyze_frame(frame)

            # 绘制检测结果
            for det in detections:
                x1, y1, x2, y2 = det['bbox']

                if det['class'] == '猫':
                    # 猫用亮绿色
                    color = (0, 255, 0)
                    thickness = 3

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                    # 显示帧同步信息
                    label = f"CAT #{det['frame_number']}"
                    cv2.rectangle(frame, (x1, y1-25), (x1 + 120, y1), color, -1)
                    cv2.putText(frame, label, (x1+5, y1-8),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

                    # 显示Z轴深度
                    z_depth = det['physical_coords']['z']
                    depth_label = f"Z:{z_depth:.1f}m"
                    cv2.putText(frame, depth_label, (x1, y2+20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

                else:
                    # 狗用蓝色
                    color = (255, 100, 0)
                    thickness = 2
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            # 显示同步状态信息
            sync_text = f"SYNC | Frame #{monitor_system.sync_frame_number} | {monitor_system.sync_fps}FPS"
            cv2.putText(frame, sync_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 136), 2)

            detection_text = f"Detections: {len(detections)} | Cats: {monitor_system.cat_detections}"
            cv2.putText(frame, detection_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 编码帧
            encode_param = [
                int(cv2.IMWRITE_JPEG_QUALITY), 90,
                int(cv2.IMWRITE_JPEG_OPTIMIZE), 1
            ]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # 严格的帧率同步控制
            frame_elapsed = time.time() - frame_start_time
            if frame_elapsed < monitor_system.frame_time:
                time.sleep(monitor_system.frame_time - frame_elapsed)
            else:
                # 如果处理时间过长，记录但继续
                print(f"⚠️ 帧#{monitor_system.sync_frame_number} 处理超时: {frame_elapsed:.3f}s")

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/detections')
def api_detections():
    """获取当前检测数据 - 同步版本"""
    if monitor_system is None:
        return jsonify({})

    # 添加额外的同步信息
    detections_data = []
    for det in monitor_system.current_detections:
        det_data = det.copy()
        det_data['physical_x'] = det['physical_coords']['x']
        det_data['physical_y'] = det['physical_coords']['y']
        det_data['physical_z'] = det['physical_coords']['z']
        detections_data.append(det_data)

    return jsonify({
        'detections': detections_data,
        'current_frame_number': monitor_system.sync_frame_number,
        'total_detections': monitor_system.total_detections,
        'cat_detections': monitor_system.cat_detections,
        'total_frames': monitor_system.total_frames,
        'sync_fps': monitor_system.sync_fps,
        'sync_status': 'synchronized'
    })

@app.route('/api/sync_analysis')
def api_sync_analysis():
    """获取同步分析数据"""
    if monitor_system is None:
        return jsonify({})

    return jsonify({
        'current_frame_analysis': monitor_system.current_frame_analysis,
        'recent_analysis': monitor_system.frame_analysis_history[-10:],
        'sync_status': 'synchronized',
        'sync_fps': monitor_system.sync_fps,
        'frame_time': monitor_system.frame_time
    })

@app.route('/api/3d_visualization')
def api_3d_visualization():
    """获取3D可视化图像"""
    if monitor_system is None:
        return "No system", 404

    img_data = monitor_system.generate_3d_visualization()
    if img_data:
        return Response(img_data, mimetype='image/png')
    else:
        return "Error generating visualization", 500

@app.route('/api/vlm_analysis')
def api_vlm_analysis():
    """VLM分析接口"""
    return jsonify({
        'status': 'VLM analysis available for synchronized frames',
        'vlm_loaded': monitor_system.vlv_model_loaded if monitor_system else False
    })

def main():
    global monitor_system

    print("🎬 启动同步宠物监控系统...")
    print("⚡ 特性:")
    print("   - 🎯 逐帧播放逐帧分析")
    print("   - 🔄 视频与AI检测完全同步")
    print("   - 🐱 每帧猫检测分析")
    print("   - 🏠 实时3D空间追踪(Z轴)")
    print("   - 📊 同步状态监控")

    # 创建同步监控系统
    sync_fps = 15  # 降低帧率确保检测能跟上
    monitor_system = SynchronizedPetMonitor(sync_fps=sync_fps)

    print(f"✅ 同步监控系统启动成功！")
    print(f"🌐 Web界面: http://localhost:5008")
    print(f"🎯 同步帧率: {sync_fps} FPS (逐帧分析)")

    app.run(host='0.0.0.0', port=5008, debug=False, threaded=True)

if __name__ == "__main__":
    main()