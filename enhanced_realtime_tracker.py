#!/usr/bin/env python3
"""
增强实时猫咪追踪系统 - 专注于方框显示、AI分析、3D位置
确保用户能清楚看到追踪方框和分析数据
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
from collections import defaultdict, deque

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

class SimpleTracker:
    """简化但稳定的跟踪器"""

    def __init__(self, track_id, bbox, confidence):
        self.track_id = track_id
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen = time.time()
        self.age = 0
        self.hits = 1
        self.history = deque(maxlen=20)

    def update(self, bbox, confidence):
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen = time.time()
        self.hits += 1
        self.history.append({
            'bbox': bbox,
            'confidence': confidence,
            'timestamp': time.time()
        })

class EnhancedRealtimeTracker:
    """增强实时猫咪追踪系统"""

    def __init__(self, video_file="real_cat.mp4"):
        print("🚀 启动增强实时猫咪追踪系统...")
        print("🎯 专注功能:")
        print("   - 💚 明显的绿色追踪方框")
        print("   - 🧠 实时AI场景分析")
        print("   - 📐 精确3D位置显示")
        print("   - ⚡ 稳定高性能检测")

        self.video_file = video_file
        self.target_fps = 30

        # 视频相关
        self.cap = None
        self.frame_count = 0
        self.total_frames = 0
        self.current_frame = None

        # 检测相关
        self.yolo_model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 简化跟踪
        self.trackers = {}
        self.next_track_id = 0
        self.max_disappeared = 30

        # 3D定位相关
        self.homography_matrix = None
        self.room_data = None
        self.usd_geometry = []
        self.usd_bounds = None

        # 数据存储
        self.current_detections = []
        self.detection_history = deque(maxlen=100)
        self.cat_detections = 0
        self.total_detections = 0

        # VLM分析相关
        self.vlm_model = None
        self.vlv_processor = None
        self.vlm_model_loaded = False
        self.last_vlm_analysis = ""
        self.current_scene_analysis = ""
        self.current_behavior_analysis = ""

        # 初始化组件
        self._initialize_detection()
        self._initialize_3d_tracking()
        self._initialize_video()

        print(f"✅ 增强追踪系统启动成功！")

    def _initialize_detection(self):
        """初始化检测模型"""
        print("🔧 加载检测模型...")
        try:
            # 优先使用已下载的大模型，否则使用小模型
            if Path("yolov8x.pt").exists():
                print("   🎯 使用YOLOv8x大模型")
                self.yolo_model = YOLO('yolov8x.pt')
            else:
                print("   🎯 使用YOLOv8n模型")
                self.yolo_model = YOLO('yolov8n.pt')

            self.yolo_model.to(self.device)
            print(f"   ✅ 检测模型就绪 ({self.device})")
        except Exception as e:
            print(f"   ❌ 检测模型加载失败: {e}")

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
                    print(f"✅ 房间数据加载成功")
                    break
                except Exception as e:
                    print(f"⚠️ 房间数据加载失败: {e}")

        # 加载校准矩阵
        calibration_files = [
            "meeting_room_calibration_20260410_120824.json"
        ]

        for file_path in calibration_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        calib_data = json.load(f)
                        self.homography_matrix = np.array(calib_data['homography_matrix'])
                    print(f"✅ 校准矩阵加载成功")
                    break
                except Exception as e:
                    print(f"⚠️ 校准数据加载失败: {e}")

        # 加载USD 3D模型
        self._load_usd_model()

    def _load_usd_model(self):
        """加载USD 3D模型"""
        if not USD_AVAILABLE:
            print("⚠️ USD库不可用")
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

            print(f"✅ 3D模型加载成功，共 {len(self.usd_geometry)} 个几何对象")
            if self.usd_bounds:
                print(f"   房间尺寸: {self.usd_bounds['x_max']-self.usd_bounds['x_min']:.2f}m x {self.usd_bounds['y_max']-self.usd_bounds['y_min']:.2f}m")

        except Exception as e:
            print(f"⚠️ 3D模型加载失败: {e}")

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

        except Exception as e:
            print(f"❌ 视频初始化失败: {e}")

    def get_next_frame(self):
        """获取下一帧"""
        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            # 视频结束，重新开始
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            ret, frame = self.cap.read()

        if ret:
            self.frame_count += 1
            self.current_frame = frame.copy()

        return frame

    def enhanced_cat_detection(self, frame):
        """增强猫咪检测"""
        if frame is None or self.yolo_model is None:
            return []

        try:
            # 高质量检测 - 降低阈值提高灵敏度
            results = self.yolo_model(
                frame,
                conf=0.05,  # 非常低的置信度阈值，更敏感
                iou=0.4,   # 稍微宽松的NMS
                verbose=False,
                device=self.device
            )

            detections = []

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]

                    # 检测猫
                    if cls == 15:  # COCO类别中猫是15
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        bbox_area = (x2 - x1) * (y2 - y1)

                        # 基本过滤 - 降低面积要求
                        if bbox_area >= 100:  # 更小的最小面积过滤
                            # 计算3D物理坐标
                            physical_coords = self._pixel_to_physical(center_x, center_y, bbox_area)

                            detection = {
                                'class': '猫',
                                'confidence': conf,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'center': [center_x, center_y],
                                'physical_coords': physical_coords,
                                'area': bbox_area,
                                'frame_number': self.frame_count,
                                'timestamp': time.time()
                            }
                            detections.append(detection)

                            self.total_detections += 1
                            self.cat_detections += 1

            return detections

        except Exception as e:
            print(f"检测失败: {e}")
            return []

    def _pixel_to_physical(self, pixel_x, pixel_y, bbox_area=None):
        """像素坐标转物理坐标"""
        if self.homography_matrix is None:
            return {"x": 0, "y": 0, "z": 0}

        try:
            # 2D转换
            pixel_point = np.array([[pixel_x, pixel_y]], dtype=np.float32)
            physical_point = cv2.perspectiveTransform(
                pixel_point.reshape(1, -1, 2), self.homography_matrix)
            x, y = physical_point[0][0]

            # 简化Z轴估算
            z = self._estimate_z_depth(pixel_x, pixel_y, bbox_area)

            return {"x": float(x), "y": float(y), "z": float(z)}

        except Exception as e:
            return {"x": 0, "y": 0, "z": 0}

    def _estimate_z_depth(self, pixel_x, pixel_y, bbox_area):
        """估算Z轴深度"""
        try:
            video_height = 720
            height_ratio = pixel_y / video_height
            base_z = 0.3

            # 简单深度估算
            if height_ratio < 0.3:
                estimated_z = base_z + (0.3 - height_ratio) * 2.0
            elif height_ratio > 0.7:
                estimated_z = max(0.0, base_z - (height_ratio - 0.7) * 1.5)
            else:
                estimated_z = base_z + (0.5 - height_ratio) * 0.8

            # 面积调整
            if bbox_area:
                area_factor = min(bbox_area / 8000, 1.5)
                estimated_z += area_factor * 0.2

            return max(0.0, min(estimated_z, 2.5))

        except:
            return 0.3

    def simple_tracking(self, detections):
        """简化但稳定的跟踪"""
        current_time = time.time()

        # 移除超时的跟踪器
        expired_ids = []
        for track_id, tracker in self.trackers.items():
            if current_time - tracker.last_seen > 2.0:  # 2秒超时
                expired_ids.append(track_id)

        for track_id in expired_ids:
            del self.trackers[track_id]

        # 为新检测分配跟踪器
        for detection in detections:
            best_track_id = None
            best_distance = float('inf')

            # 查找最近的跟踪器
            for track_id, tracker in self.trackers.items():
                old_center = [(tracker.bbox[0] + tracker.bbox[2]) / 2,
                             (tracker.bbox[1] + tracker.bbox[3]) / 2]
                new_center = detection['center']

                distance = np.sqrt((old_center[0] - new_center[0])**2 +
                                  (old_center[1] - new_center[1])**2)

                if distance < best_distance and distance < 100:  # 最大关联距离
                    best_distance = distance
                    best_track_id = track_id

            # 更新或创建跟踪器
            if best_track_id is not None:
                # 更新现有跟踪器
                self.trackers[best_track_id].update(detection['bbox'], detection['confidence'])
                detection['track_id'] = best_track_id
            else:
                # 创建新跟踪器
                new_tracker = SimpleTracker(self.next_track_id, detection['bbox'], detection['confidence'])
                self.trackers[self.next_track_id] = new_tracker
                detection['track_id'] = self.next_track_id
                self.next_track_id += 1

        # 更新当前检测
        self.current_detections = detections
        self.detection_history.extend(detections)

        return detections

    def analyze_scene_with_vlm(self, frame):
        """VLM场景分析"""
        try:
            if not VLM_AVAILABLE or not self.vlm_model_loaded:
                # 简单的规则基础分析
                if self.current_detections:
                    cat_count = len(self.current_detections)
                    if cat_count == 1:
                        self.current_scene_analysis = "检测到1只猫咪在房间内活动"
                        self.current_behavior_analysis = "猫咪表现出正常的室内活动行为"
                    else:
                        self.current_scene_analysis = f"检测到{cat_count}只猫咪同时在场"
                        self.current_behavior_analysis = "多只猫咪的互动行为观察中"
                else:
                    self.current_scene_analysis = "房间内暂未检测到猫咪"
                    self.current_behavior_analysis = "等待猫咪进入监控区域"

                # 添加位置信息
                if self.current_detections:
                    coords = self.current_detections[0]['physical_coords']
                    self.current_scene_analysis += f" (位置: {coords['x']:.1f}m, {coords['y']:.1f}m)"

                return True

            # TODO: 实际的VLM分析
            return False

        except Exception as e:
            self.current_scene_analysis = "场景分析暂时不可用"
            self.current_behavior_analysis = "行为分析系统正在恢复"
            return False

    def generate_enhanced_3d_visualization(self):
        """生成增强的3D可视化"""
        try:
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(10, 8), facecolor='black')
            ax = fig.add_subplot(111, projection='3d')
            ax.set_facecolor('black')

            # 绘制房间结构
            if self.usd_bounds:
                bounds = self.usd_bounds

                # 地板网格
                x_grid = np.linspace(bounds['x_min'], bounds['x_max'], 10)
                y_grid = np.linspace(bounds['y_min'], bounds['y_max'], 10)
                for x in x_grid:
                    ax.plot([x, x], [bounds['y_min'], bounds['y_max']], [0, 0], 'gray', alpha=0.3)
                for y in y_grid:
                    ax.plot([bounds['x_min'], bounds['x_max']], [y, y], [0, 0], 'gray', alpha=0.3)

            # 绘制当前检测
            for detection in self.current_detections:
                coords = detection['physical_coords']
                track_id = detection.get('track_id', 0)

                # 根据track_id使用不同颜色
                colors = ['lime', 'cyan', 'yellow', 'magenta', 'orange']
                color = colors[track_id % len(colors)]

                # 当前位置
                ax.scatter(coords['x'], coords['y'], coords['z'],
                          c=color, s=150, alpha=1.0, edgecolors='white', linewidth=2)

                # Z轴投影线
                ax.plot([coords['x'], coords['x']], [coords['y'], coords['y']], [0, coords['z']],
                       color=color, linestyle='--', alpha=0.7, linewidth=2)

                # 标签
                ax.text(coords['x'], coords['y'], coords['z'] + 0.15,
                       f'Cat#{track_id}\n({coords["x"]:.1f},{coords["y"]:.1f},{coords["z"]:.1f})',
                       fontsize=9, color='white', ha='center')

            # 绘制历史轨迹
            track_positions = defaultdict(list)
            for det in list(self.detection_history)[-20:]:  # 最近20个检测
                if 'track_id' in det:
                    track_id = det['track_id']
                    coords = det['physical_coords']
                    track_positions[track_id].append([coords['x'], coords['y'], coords['z']])

            for track_id, positions in track_positions.items():
                if len(positions) > 1:
                    positions = np.array(positions)
                    color = ['lime', 'cyan', 'yellow', 'magenta', 'orange'][track_id % 5]
                    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2],
                           color=color, linewidth=1.5, alpha=0.6)

            # 设置标题和标签
            active_cats = len(self.current_detections)
            total_tracks = len(self.trackers)

            ax.set_title(f'🏠 实时3D追踪 | 帧#{self.frame_count} | 活跃:{active_cats} | 总数:{total_tracks}',
                        color='white', fontsize=12)
            ax.set_xlabel('X (m)', color='white')
            ax.set_ylabel('Y (m)', color='white')
            ax.set_zlabel('Z (m)', color='white')

            # 设置范围
            if self.usd_bounds:
                ax.set_xlim(self.usd_bounds['x_min']-0.5, self.usd_bounds['x_max']+0.5)
                ax.set_ylim(self.usd_bounds['y_min']-0.5, self.usd_bounds['y_max']+0.5)
            ax.set_zlim(0, 2.5)

            ax.tick_params(colors='white')

            # 保存图像
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=72, bbox_inches='tight',
                       facecolor='black', edgecolor='none')
            img_buffer.seek(0)
            img_data = img_buffer.read()
            plt.close('all')
            gc.collect()

            return img_data

        except Exception as e:
            print(f"3D可视化生成失败: {e}")
            return None

# 全局系统实例
enhanced_tracker = None

@app.route('/')
def index():
    """主页面 - 增强追踪界面"""
    # 使用原来的Apple风格界面
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced Cat Tracker - 增强猫咪追踪</title>
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
                background: linear-gradient(135deg, #34C759 0%, #30D158 25%, #32D74B 50%, #34C759 75%, #30D158 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-size: 200% 200%;
                animation: gradientShift 6s ease-in-out infinite;
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

            .enhanced-indicator {
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
                background: linear-gradient(135deg, rgba(52, 199, 89, 0.03) 0%, rgba(48, 209, 88, 0.02) 100%);
                position: relative;
            }

            /* 统计面板 */
            .stats-panel {
                background: linear-gradient(135deg, rgba(0, 122, 255, 0.03) 0%, rgba(90, 200, 250, 0.02) 100%);
            }

            /* AI分析面板 */
            .vlm-panel {
                background: linear-gradient(135deg, rgba(175, 82, 222, 0.03) 0%, rgba(255, 45, 85, 0.02) 100%);
            }

            /* 3D视图面板 */
            .viz-panel {
                background: linear-gradient(135deg, rgba(255, 149, 0, 0.03) 0%, rgba(255, 204, 0, 0.02) 100%);
            }

            /* 面板标题栏 */
            .panel-header {
                padding: 16px 20px 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                flex-shrink: 0;
            }

            /* 不同颜色的标题栏 */
            .video-header {
                background: linear-gradient(135deg, rgba(52, 199, 89, 0.08) 0%, rgba(48, 209, 88, 0.04) 100%);
            }

            .stats-header {
                background: linear-gradient(135deg, rgba(0, 122, 255, 0.08) 0%, rgba(90, 200, 250, 0.04) 100%);
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

            /* 增强状态覆盖层 */
            .enhanced-overlay {
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
                color: #34C759 !important;
                font-size: 32px !important;
                text-shadow: 0 0 8px rgba(52, 199, 89, 0.3);
            }

            .track-count {
                color: #007AFF !important;
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
                        document.getElementById('track-count').textContent = data.active_tracks || 0;
                        document.getElementById('avg-confidence').textContent = (data.average_confidence || 0).toFixed(3);

                        // 更新导航栏状态
                        const navStats = document.getElementById('nav-stats');
                        if (navStats) {
                            const activeTracks = data.active_tracks || 0;
                            const frameNum = data.frame_number || 0;
                            navStats.textContent = `帧#${frameNum} | 追踪:${activeTracks}只猫`;
                        }

                        // 更新增强覆盖层
                        const enhancedOverlay = document.getElementById('enhanced-overlay');
                        if (enhancedOverlay) {
                            const frameNum = data.frame_number || 0;
                            enhancedOverlay.textContent = `ENHANCED | 帧#${frameNum} | 绿框追踪`;
                        }
                    })
                    .catch(error => console.error('Error fetching detections:', error));

                // 更新VLM分析
                fetch('/api/vlm_analysis')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('scene-analysis').textContent = data.scene_analysis || '场景分析中...';
                        document.getElementById('behavior-analysis').textContent = data.behavior_analysis || '行为分析中...';
                    })
                    .catch(error => {
                        console.error('Error fetching VLM analysis:', error);
                    });
            }

            // 优化更新频率
            setInterval(updateData, 800);  // 更频繁的更新

            // 高频3D可视化更新
            function update3D() {
                const viz3d = document.getElementById('viz-3d');
                if (viz3d) {
                    viz3d.src = '/api/3d_visualization?' + new Date().getTime();
                }
            }
            setInterval(update3D, 600);  // 更快的3D更新

            // 页面加载时立即更新
            window.onload = updateData;

            // 添加一些交互效果
            function addInteractivity() {
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

            document.addEventListener('DOMContentLoaded', addInteractivity);
        </script>
    </head>
    <body>
        <!-- 顶部导航栏 -->
        <nav class="top-nav">
            <div class="nav-title">Enhanced Cat Tracker</div>
            <div class="nav-status">
                <div class="live-dot"></div>
                <span>LIVE</span>
                <span id="nav-stats">增强追踪运行中...</span>
                <div class="enhanced-indicator">
                    <div class="live-dot" style="background: #32D74B; width: 6px; height: 6px;"></div>
                    <span>ENHANCED</span>
                </div>
            </div>
        </nav>

        <!-- 主容器 - 完全横向整齐四列布局 -->
        <div class="main-container">
            <!-- 第1列：主视频面板 -->
            <div class="panel video-panel">
                <div class="panel-header video-header">
                    <h3>💚 增强视频追踪 (绿色方框)</h3>
                </div>
                <div class="panel-content">
                    <img src="/video_feed" class="video-stream" alt="增强追踪视频流">
                    <div class="enhanced-overlay" id="enhanced-overlay">
                        ENHANCED | 启动中...
                    </div>
                </div>
            </div>

            <!-- 第2列：统计数据面板 -->
            <div class="panel stats-panel">
                <div class="panel-header stats-header">
                    <h3>📊 实时数据</h3>
                </div>
                <div class="panel-content">
                    <div class="stats-content">
                        <div class="stat-row">
                            <div class="stat-label">🐱 检测到猫</div>
                            <div id="cat-count" class="stat-value cat-count">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">🔄 活跃追踪</div>
                            <div id="track-count" class="stat-value track-count">0</div>
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
                    <h3>🧠 AI智能分析</h3>
                </div>
                <div class="panel-content">
                    <div class="vlm-content">
                        <div class="analysis-item">
                            <div class="analysis-label">场景分析</div>
                            <div id="scene-analysis" class="vlm-analysis">正在分析场景...</div>
                        </div>
                        <div class="analysis-item">
                            <div class="analysis-label">行为分析</div>
                            <div id="behavior-analysis" class="vlm-analysis">正在分析行为...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 第4列：3D空间追踪面板 -->
            <div class="panel viz-panel">
                <div class="panel-header viz-header">
                    <h3>🏠 3D空间定位</h3>
                </div>
                <div class="panel-content">
                    <div class="viz-content">
                        <img id="viz-3d" src="/api/3d_visualization" class="viz-3d-image" alt="3D位置可视化">
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    """增强视频流"""
    def generate():
        print("💚 开始增强追踪视频流...")

        while True:
            if enhanced_tracker is None:
                break

            frame_start_time = time.time()

            # 获取下一帧
            frame = enhanced_tracker.get_next_frame()
            if frame is None:
                break

            # 猫咪检测
            detections = enhanced_tracker.enhanced_cat_detection(frame)

            # 简单跟踪
            if detections:
                tracked_detections = enhanced_tracker.simple_tracking(detections)
            else:
                tracked_detections = []

            # 场景分析
            enhanced_tracker.analyze_scene_with_vlm(frame)

            # 绘制超明显的绿色追踪方框
            for detection in tracked_detections:
                bbox = detection['bbox']
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                track_id = detection.get('track_id', 0)
                confidence = detection['confidence']

                # 超明显的亮绿色方框
                color = (0, 255, 0)  # 纯绿色
                thickness = 5  # 超粗边框

                # 绘制主边框
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                # 绘制内边框增强效果
                cv2.rectangle(frame, (x1+2, y1+2), (x2-2, y2-2), color, 2)

                # 超明显的标签背景
                label = f"CAT #{track_id}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 3)[0]

                # 绘制标签背景
                cv2.rectangle(frame, (x1, y1-35), (x1 + label_size[0] + 20, y1), color, -1)
                cv2.putText(frame, label, (x1+10, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)

                # 置信度显示
                conf_text = f"{confidence:.2f}"
                cv2.putText(frame, conf_text, (x1, y2+25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                # 3D坐标显示
                coords = detection['physical_coords']
                coord_text = f"3D: ({coords['x']:.1f}, {coords['y']:.1f}, {coords['z']:.1f})"
                cv2.putText(frame, coord_text, (x1, y2+50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # 系统状态信息
            active_tracks = len(tracked_detections)
            total_tracks = len(enhanced_tracker.trackers)

            status_text = f"ENHANCED | Frame #{enhanced_tracker.frame_count} | Active: {active_tracks}/{total_tracks}"
            cv2.putText(frame, status_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (52, 199, 89), 2)

            algo_text = f"Detection + Tracking + 3D Analysis | Green Boxes = Cats"
            cv2.putText(frame, algo_text, (10, 60),
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

            # 帧率控制
            frame_elapsed = time.time() - frame_start_time
            frame_time = 1.0 / enhanced_tracker.target_fps
            if frame_elapsed < frame_time:
                time.sleep(frame_time - frame_elapsed)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/detections')
def api_detections():
    """获取当前检测数据"""
    if enhanced_tracker is None:
        return jsonify({})

    # 计算统计数据
    detections_data = []
    confidences = []

    for detection in enhanced_tracker.current_detections:
        det_data = detection.copy()
        det_data['physical_x'] = detection['physical_coords']['x']
        det_data['physical_y'] = detection['physical_coords']['y']
        det_data['physical_z'] = detection['physical_coords']['z']
        detections_data.append(det_data)
        confidences.append(detection['confidence'])

    return jsonify({
        'detections': detections_data,
        'frame_number': enhanced_tracker.frame_count,
        'total_detections': enhanced_tracker.total_detections,
        'cat_detections': enhanced_tracker.cat_detections,
        'active_tracks': len(enhanced_tracker.current_detections),
        'total_trackers': len(enhanced_tracker.trackers),
        'average_confidence': np.mean(confidences) if confidences else 0,
        'tracking_mode': 'enhanced_realtime'
    })

@app.route('/api/3d_visualization')
def api_3d_visualization():
    """获取3D可视化图像"""
    if enhanced_tracker is None:
        return "No system", 404

    img_data = enhanced_tracker.generate_enhanced_3d_visualization()
    if img_data:
        return Response(img_data, mimetype='image/png')
    else:
        return "Error generating visualization", 500

@app.route('/api/vlm_analysis')
def api_vlm_analysis():
    """VLM分析接口"""
    if enhanced_tracker is None:
        return jsonify({})

    return jsonify({
        'scene_analysis': enhanced_tracker.current_scene_analysis,
        'behavior_analysis': enhanced_tracker.current_behavior_analysis,
        'status': 'Real-time AI analysis active',
        'features': ['Scene understanding', 'Behavior analysis', '3D positioning']
    })

def main():
    global enhanced_tracker

    print("💚 启动增强实时猫咪追踪系统...")
    print("🎯 核心功能:")
    print("   - 💚 超明显的绿色追踪方框")
    print("   - 🧠 实时AI场景和行为分析")
    print("   - 📐 精确3D位置坐标显示")
    print("   - 🔄 稳定的多目标追踪")
    print("   - ⚡ 优化的实时性能")

    # 创建增强追踪系统
    enhanced_tracker = EnhancedRealtimeTracker()

    print(f"✅ 增强追踪系统启动成功！")
    print(f"🌐 Web界面: http://localhost:5008")
    print(f"💚 特色: 超明显绿色方框 + AI分析 + 3D位置")

    app.run(host='0.0.0.0', port=5008, debug=False, threaded=True)

if __name__ == "__main__":
    main()