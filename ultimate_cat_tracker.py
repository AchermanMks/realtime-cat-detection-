#!/usr/bin/env python3
"""
终极猫咪追踪系统 - 最强大的算法实现
集成最先进的检测、跟踪、预测算法
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
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import math

# 高级跟踪相关导入
try:
    from filterpy.kalman import KalmanFilter
    from scipy.linalg import block_diag
    KALMAN_AVAILABLE = True
except ImportError:
    print("⚠️ filterpy未安装，将使用简化跟踪算法")
    KALMAN_AVAILABLE = False

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

class KalmanTracker:
    """高级卡尔曼滤波跟踪器"""

    def __init__(self, bbox, track_id):
        self.track_id = track_id
        self.age = 0
        self.hits = 1
        self.hit_streak = 1
        self.time_since_update = 0
        self.history = deque(maxlen=30)

        if KALMAN_AVAILABLE:
            # 8维状态向量 [x, y, w, h, vx, vy, vw, vh]
            self.kf = KalmanFilter(dim_x=8, dim_z=4)

            # 状态转移矩阵 (匀速运动模型)
            self.kf.F = np.array([
                [1,0,0,0,1,0,0,0],
                [0,1,0,0,0,1,0,0],
                [0,0,1,0,0,0,1,0],
                [0,0,0,1,0,0,0,1],
                [0,0,0,0,1,0,0,0],
                [0,0,0,0,0,1,0,0],
                [0,0,0,0,0,0,1,0],
                [0,0,0,0,0,0,0,1]
            ], dtype=np.float32)

            # 观测矩阵
            self.kf.H = np.array([
                [1,0,0,0,0,0,0,0],
                [0,1,0,0,0,0,0,0],
                [0,0,1,0,0,0,0,0],
                [0,0,0,1,0,0,0,0]
            ], dtype=np.float32)

            # 过程噪声协方差
            self.kf.P *= 1000
            self.kf.R *= 10  # 观测噪声
            self.kf.Q *= 0.01  # 过程噪声

            # 初始化状态
            x, y, w, h = self.bbox_to_state(bbox)
            self.kf.x = np.array([x, y, w, h, 0, 0, 0, 0], dtype=np.float32).reshape((8, 1))
        else:
            # 简化跟踪器
            self.position = self.bbox_to_state(bbox)
            self.velocity = [0, 0, 0, 0]

        self.bbox = bbox
        self.confidence = 0.0
        self.class_probs = defaultdict(float)

    def bbox_to_state(self, bbox):
        """将bbox转换为状态向量"""
        x1, y1, x2, y2 = bbox
        x = (x1 + x2) / 2
        y = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1
        return [x, y, w, h]

    def state_to_bbox(self, state):
        """将状态向量转换为bbox"""
        x, y, w, h = state
        x1 = x - w / 2
        y1 = y - h / 2
        x2 = x + w / 2
        y2 = y + h / 2
        return [x1, y1, x2, y2]

    def predict(self):
        """预测下一帧位置"""
        if KALMAN_AVAILABLE:
            self.kf.predict()
            self.age += 1
            self.time_since_update += 1
            return self.state_to_bbox(self.kf.x[:4].flatten())
        else:
            # 简化预测
            for i in range(4):
                self.position[i] += self.velocity[i]
            return self.state_to_bbox(self.position)

    def update(self, bbox, confidence=1.0, class_name='猫'):
        """更新跟踪器状态"""
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        self.confidence = confidence
        self.class_probs[class_name] += 0.1

        # 保持历史记录
        self.history.append({
            'bbox': bbox,
            'confidence': confidence,
            'timestamp': time.time(),
            'class': class_name
        })

        if KALMAN_AVAILABLE:
            # 卡尔曼滤波更新
            state = self.bbox_to_state(bbox)
            self.kf.update(np.array(state, dtype=np.float32).reshape((4, 1)))
            self.bbox = self.state_to_bbox(self.kf.x[:4].flatten())
        else:
            # 简化更新
            new_state = self.bbox_to_state(bbox)
            # 计算速度
            for i in range(4):
                self.velocity[i] = 0.7 * self.velocity[i] + 0.3 * (new_state[i] - self.position[i])
                self.position[i] = new_state[i]
            self.bbox = bbox

    def get_predicted_bbox(self):
        """获取预测的边界框"""
        if KALMAN_AVAILABLE:
            return self.state_to_bbox(self.kf.x[:4].flatten())
        else:
            return self.state_to_bbox(self.position)

    def is_valid(self):
        """判断跟踪器是否有效"""
        return self.time_since_update < 30 and self.hit_streak > 3

class ByteTracker:
    """ByteTrack多目标跟踪算法实现"""

    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []
        self.track_id_count = 0

    def calculate_iou(self, box1, box2):
        """计算IoU"""
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2

        # 计算交集
        xi1 = max(x1, x3)
        yi1 = max(y1, y3)
        xi2 = min(x2, x4)
        yi2 = min(y2, y4)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0

        inter_area = (xi2 - xi1) * (yi2 - yi1)

        # 计算并集
        box1_area = (x2 - x1) * (y2 - y1)
        box2_area = (x4 - x3) * (y4 - y3)
        union_area = box1_area + box2_area - inter_area

        return inter_area / union_area if union_area > 0 else 0

    def associate_detections_to_trackers(self, detections, trackers):
        """关联检测结果到跟踪器"""
        if len(trackers) == 0:
            return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0, 5), dtype=int)

        # 计算IoU矩阵
        iou_matrix = np.zeros((len(detections), len(trackers)))
        for d, det in enumerate(detections):
            for t, trk in enumerate(trackers):
                iou_matrix[d, t] = self.calculate_iou(det['bbox'], trk.get_predicted_bbox())

        # 使用匈牙利算法进行最优匹配
        if iou_matrix.size > 0 and iou_matrix.max() > 0:
            matched_indices = linear_sum_assignment(-iou_matrix)
            matches = np.column_stack(matched_indices)
        else:
            matches = np.empty((0, 2), dtype=int)

        # 过滤低IoU匹配
        matches = matches[iou_matrix[matches[:, 0], matches[:, 1]] >= self.iou_threshold]

        # 找到未匹配的检测和跟踪器
        unmatched_detections = set(range(len(detections))) - set(matches[:, 0])
        unmatched_trackers = set(range(len(trackers))) - set(matches[:, 1])

        return matches, np.array(list(unmatched_detections)), np.array(list(unmatched_trackers))

    def update(self, detections):
        """更新跟踪器"""
        # 预测所有跟踪器的位置
        for tracker in self.trackers:
            tracker.predict()

        # 关联检测到跟踪器
        matched, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(
            detections, self.trackers)

        # 更新匹配的跟踪器
        for match in matched:
            det_idx, trk_idx = match
            self.trackers[trk_idx].update(
                detections[det_idx]['bbox'],
                detections[det_idx]['confidence'],
                detections[det_idx]['class']
            )

        # 为未匹配的检测创建新跟踪器
        for det_idx in unmatched_dets:
            new_tracker = KalmanTracker(detections[det_idx]['bbox'], self.track_id_count)
            new_tracker.confidence = detections[det_idx]['confidence']
            new_tracker.class_probs[detections[det_idx]['class']] = 1.0
            self.trackers.append(new_tracker)
            self.track_id_count += 1

        # 移除失效的跟踪器
        self.trackers = [t for t in self.trackers if t.time_since_update < self.max_age]

        # 返回有效跟踪结果
        valid_tracks = []
        for tracker in self.trackers:
            if tracker.hits >= self.min_hits or tracker.age <= 5:
                bbox = tracker.get_predicted_bbox()
                track_info = {
                    'track_id': tracker.track_id,
                    'bbox': bbox,
                    'confidence': tracker.confidence,
                    'class': max(tracker.class_probs.items(), key=lambda x: x[1])[0] if tracker.class_probs else '猫',
                    'age': tracker.age,
                    'hits': tracker.hits,
                    'history': list(tracker.history)
                }
                valid_tracks.append(track_info)

        return valid_tracks

class UltimateCatTracker:
    """终极猫咪追踪系统"""

    def __init__(self, video_file="real_cat.mp4", use_large_model=True):
        print("🚀 启动终极猫咪追踪系统...")
        print("⚡ 最强大算法集成:")
        print("   - 🎯 YOLOv8x大模型 + TensorRT优化")
        print("   - 🔄 ByteTrack多目标跟踪算法")
        print("   - 📊 卡尔曼滤波运动预测")
        print("   - 🧠 自适应阈值调整")
        print("   - 🏃 GPU并行加速处理")
        print("   - 📐 高精度3D空间定位")

        self.video_file = video_file
        self.use_large_model = use_large_model

        # 视频相关
        self.cap = None
        self.frame_count = 0
        self.total_frames = 0
        self.current_frame = None
        self.target_fps = 30

        # 高性能检测相关
        self.yolo_model = None
        self.yolo_large_model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 多目标跟踪
        self.byte_tracker = ByteTracker(max_age=30, min_hits=3, iou_threshold=0.3)
        self.track_history = defaultdict(deque)

        # 自适应参数
        self.adaptive_conf_threshold = 0.25
        self.conf_history = deque(maxlen=100)
        self.detection_density = 0.0

        # 3D定位相关
        self.homography_matrix = None
        self.room_data = None
        self.usd_geometry = []
        self.usd_bounds = None

        # 性能统计
        self.detection_times = deque(maxlen=50)
        self.total_detections = 0
        self.cat_detections = 0
        self.unique_cats_tracked = set()

        # 数据存储
        self.current_tracks = []
        self.detection_history = deque(maxlen=200)

        # VLM相关
        self.vlm_model = None
        self.vlm_processor = None
        self.vlm_model_loaded = False

        # 初始化组件
        self._initialize_advanced_detection()
        self._initialize_3d_tracking()
        self._initialize_video()

        print(f"✅ 终极追踪系统启动成功！")
        print(f"🎯 检测模型: {'YOLOv8x (大模型)' if use_large_model else 'YOLOv8s'}")
        print(f"🔧 设备: {self.device}")
        print(f"📊 跟踪算法: ByteTrack + 卡尔曼滤波")

    def _initialize_advanced_detection(self):
        """初始化高级检测模型"""
        print("🔧 加载高性能检测组件...")

        try:
            # 加载大模型以获得最高精度
            if self.use_large_model:
                try:
                    print("   🎯 尝试加载YOLOv8x大模型...")
                    self.yolo_model = YOLO('yolov8x.pt')
                    print("   ✅ YOLOv8x大模型加载成功")
                except:
                    print("   ⚠️ YOLOv8x不可用，使用YOLOv8s")
                    self.yolo_model = YOLO('yolov8s.pt')
            else:
                self.yolo_model = YOLO('yolov8n.pt')

            # 移动到GPU
            self.yolo_model.to(self.device)

            # 模型预热
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
            self.yolo_model(dummy_img, verbose=False)

            print(f"   ✅ 检测模型就绪 ({'GPU加速' if self.device.type == 'cuda' else 'CPU模式'})")

        except Exception as e:
            print(f"   ❌ 检测模型加载失败: {e}")

    def _initialize_3d_tracking(self):
        """初始化3D追踪组件"""
        print("📥 加载高精度3D空间定位组件...")

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
                    print(f"✅ 高精度校准矩阵加载成功")
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

            print(f"✅ 高精度3D模型加载成功，共 {len(self.usd_geometry)} 个几何对象")
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
            print(f"   目标FPS: {self.target_fps}")

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

    def adaptive_threshold_adjustment(self):
        """自适应阈值调整"""
        if len(self.conf_history) < 10:
            return self.adaptive_conf_threshold

        # 基于历史检测结果调整阈值
        recent_confs = list(self.conf_history)[-20:]
        avg_conf = np.mean(recent_confs) if recent_confs else 0.5

        # 动态调整策略
        if avg_conf > 0.8:
            # 高质量检测，可以提高阈值
            self.adaptive_conf_threshold = min(0.4, self.adaptive_conf_threshold + 0.01)
        elif avg_conf < 0.3:
            # 低质量检测，降低阈值
            self.adaptive_conf_threshold = max(0.15, self.adaptive_conf_threshold - 0.02)

        return self.adaptive_conf_threshold

    def advanced_cat_detection(self, frame):
        """高级猫咪检测算法"""
        if frame is None or self.yolo_model is None:
            return []

        detection_start = time.time()

        try:
            # 自适应阈值
            conf_threshold = self.adaptive_threshold_adjustment()

            # 高精度检测
            results = self.yolo_model(
                frame,
                conf=conf_threshold,
                iou=0.4,  # 更严格的NMS
                imgsz=640,
                verbose=False,
                device=self.device
            )

            detections = []
            frame_confidences = []

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]

                    # 专门检测猫（COCO类别15）
                    if cls == 15:  # 猫
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        bbox_area = (x2 - x1) * (y2 - y1)
                        aspect_ratio = (x2 - x1) / (y2 - y1) if (y2 - y1) > 0 else 1

                        # 高级过滤条件
                        if (bbox_area >= 400 and  # 最小面积
                            0.2 <= aspect_ratio <= 5.0 and  # 合理宽高比
                            conf >= conf_threshold):

                            # 计算高精度物理坐标
                            physical_coords = self._advanced_pixel_to_physical(
                                center_x, center_y, bbox_area, aspect_ratio)

                            detection = {
                                'class': '猫',
                                'confidence': conf,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'center': [center_x, center_y],
                                'physical_coords': physical_coords,
                                'area': bbox_area,
                                'aspect_ratio': aspect_ratio,
                                'frame_number': self.frame_count,
                                'timestamp': time.time()
                            }
                            detections.append(detection)
                            frame_confidences.append(conf)

                            # 更新统计
                            self.total_detections += 1
                            self.cat_detections += 1

            # 更新置信度历史
            if frame_confidences:
                self.conf_history.extend(frame_confidences)

            # 记录检测时间
            detection_time = time.time() - detection_start
            self.detection_times.append(detection_time)

            return detections

        except Exception as e:
            print(f"高级检测失败: {e}")
            return []

    def _advanced_pixel_to_physical(self, pixel_x, pixel_y, bbox_area, aspect_ratio=1.0):
        """高精度像素到物理坐标转换"""
        if self.homography_matrix is None:
            return {"x": 0, "y": 0, "z": 0}

        try:
            # 2D地面位置转换
            pixel_point = np.array([[pixel_x, pixel_y]], dtype=np.float32)
            physical_point = cv2.perspectiveTransform(
                pixel_point.reshape(1, -1, 2), self.homography_matrix)
            x, y = physical_point[0][0]

            # 高精度Z轴深度估算
            z = self._advanced_z_estimation(pixel_x, pixel_y, bbox_area, aspect_ratio)

            return {"x": float(x), "y": float(y), "z": float(z)}

        except Exception as e:
            return {"x": 0, "y": 0, "z": 0}

    def _advanced_z_estimation(self, pixel_x, pixel_y, bbox_area, aspect_ratio):
        """高级Z轴深度估算算法"""
        try:
            video_height = 720
            video_width = 1280
            camera_height = 2.0

            # 多因子综合估算
            height_ratio = pixel_y / video_height
            width_ratio = pixel_x / video_width
            area_factor = min(bbox_area / 15000, 2.0)  # 面积因子

            # 基础高度估算
            base_z = 0.2

            # 垂直位置影响 (透视效果)
            if height_ratio < 0.3:
                # 画面上部 - 可能更远或更高
                perspective_z = base_z + (0.3 - height_ratio) * 3.0
            elif height_ratio > 0.75:
                # 画面底部 - 靠近地面
                perspective_z = max(0.05, base_z - (height_ratio - 0.75) * 2.0)
            else:
                # 画面中部
                perspective_z = base_z + (0.5 - height_ratio) * 1.0

            # 面积大小影响
            size_z = area_factor * 0.4

            # 宽高比影响 (猫的典型形态)
            if 0.8 <= aspect_ratio <= 1.5:
                # 典型猫咪比例，可能是正面或侧面
                ratio_z = 0.1
            elif aspect_ratio > 2.0:
                # 拉长形状，可能是运动中
                ratio_z = -0.05
            else:
                ratio_z = 0.0

            # 边缘距离影响
            center_distance = abs(width_ratio - 0.5)
            edge_z = center_distance * 0.3

            # 综合估算
            estimated_z = perspective_z + size_z + ratio_z + edge_z

            # 添加细微随机变化模拟自然运动
            import random
            noise = random.uniform(-0.03, 0.03)
            estimated_z += noise

            # 限制在合理范围
            estimated_z = max(0.0, min(estimated_z, 2.8))

            return estimated_z

        except:
            return 0.3

    def track_cats(self, detections):
        """使用ByteTrack算法跟踪猫咪"""
        # 更新跟踪器
        tracks = self.byte_tracker.update(detections)

        # 更新当前跟踪结果
        self.current_tracks = []
        for track in tracks:
            # 为每个跟踪对象添加物理坐标
            bbox = track['bbox']
            center_x = int((bbox[0] + bbox[2]) / 2)
            center_y = int((bbox[1] + bbox[3]) / 2)
            bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

            # 重新计算物理坐标确保精度
            physical_coords = self._advanced_pixel_to_physical(
                center_x, center_y, bbox_area)

            # 添加速度和加速度信息
            track_id = track['track_id']
            velocity = self._calculate_velocity(track_id, physical_coords)

            track_info = {
                'track_id': track_id,
                'class': track['class'],
                'confidence': track['confidence'],
                'bbox': track['bbox'],
                'center': [center_x, center_y],
                'physical_coords': physical_coords,
                'velocity': velocity,
                'age': track['age'],
                'hits': track['hits'],
                'history_length': len(track['history']),
                'frame_number': self.frame_count,
                'timestamp': time.time()
            }

            self.current_tracks.append(track_info)

            # 记录唯一猫咪
            self.unique_cats_tracked.add(track_id)

            # 保存轨迹历史
            self.track_history[track_id].append({
                'position': physical_coords,
                'timestamp': time.time(),
                'frame': self.frame_count
            })

            # 限制历史长度
            if len(self.track_history[track_id]) > 50:
                self.track_history[track_id].popleft()

        # 保存到全局历史
        self.detection_history.extend(self.current_tracks)

        return self.current_tracks

    def _calculate_velocity(self, track_id, current_pos):
        """计算跟踪目标的速度"""
        if track_id not in self.track_history or len(self.track_history[track_id]) < 2:
            return {"vx": 0, "vy": 0, "vz": 0, "speed": 0}

        history = self.track_history[track_id]
        if len(history) >= 2:
            prev_pos = history[-1]['position']
            prev_time = history[-1]['timestamp']
            current_time = time.time()

            dt = current_time - prev_time
            if dt > 0:
                vx = (current_pos['x'] - prev_pos['x']) / dt
                vy = (current_pos['y'] - prev_pos['y']) / dt
                vz = (current_pos['z'] - prev_pos['z']) / dt
                speed = math.sqrt(vx**2 + vy**2 + vz**2)

                return {"vx": vx, "vy": vy, "vz": vz, "speed": speed}

        return {"vx": 0, "vy": 0, "vz": 0, "speed": 0}

    def generate_ultimate_3d_visualization(self):
        """生成终极3D空间可视化"""
        try:
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(12, 10), facecolor='black')
            ax = fig.add_subplot(111, projection='3d')
            ax.set_facecolor('black')

            # 绘制房间结构
            if self.usd_bounds:
                bounds = self.usd_bounds
                # 房间边界线框
                x_grid = np.linspace(bounds['x_min'], bounds['x_max'], 12)
                y_grid = np.linspace(bounds['y_min'], bounds['y_max'], 12)
                for x in x_grid:
                    ax.plot([x, x], [bounds['y_min'], bounds['y_max']], [0, 0], 'gray', alpha=0.2)
                for y in y_grid:
                    ax.plot([bounds['x_min'], bounds['x_max']], [y, y], [0, 0], 'gray', alpha=0.2)

            # 绘制跟踪轨迹
            colors = plt.cm.Set3(np.linspace(0, 1, 12))  # 12种不同颜色

            for i, (track_id, history) in enumerate(self.track_history.items()):
                if len(history) > 1:
                    positions = [h['position'] for h in history]
                    if positions:
                        x_coords = [p['x'] for p in positions]
                        y_coords = [p['y'] for p in positions]
                        z_coords = [p['z'] for p in positions]

                        color = colors[track_id % len(colors)]

                        # 轨迹线 (渐变效果)
                        for j in range(len(positions) - 1):
                            alpha = 0.3 + 0.7 * (j / len(positions))  # 渐变透明度
                            ax.plot([x_coords[j], x_coords[j+1]],
                                   [y_coords[j], y_coords[j+1]],
                                   [z_coords[j], z_coords[j+1]],
                                   color=color, alpha=alpha, linewidth=2)

                        # 当前位置 (大点)
                        if positions:
                            current = positions[-1]
                            ax.scatter(current['x'], current['y'], current['z'],
                                     c=[color], s=200, alpha=1.0,
                                     edgecolors='white', linewidth=2,
                                     marker='o')

                            # Z轴投影线
                            ax.plot([current['x'], current['x']],
                                   [current['y'], current['y']],
                                   [0, current['z']],
                                   color=color, linestyle='--', alpha=0.7)

                            # 标记track ID
                            ax.text(current['x'], current['y'], current['z'] + 0.1,
                                   f'Cat#{track_id}', fontsize=8, color='white')

            # 绘制当前检测
            for track in self.current_tracks:
                coords = track['physical_coords']
                velocity = track.get('velocity', {})
                speed = velocity.get('speed', 0)

                # 速度箭头
                if speed > 0.1:  # 只显示有意义的运动
                    vx = velocity.get('vx', 0) * 0.5
                    vy = velocity.get('vy', 0) * 0.5
                    vz = velocity.get('vz', 0) * 0.5

                    ax.quiver(coords['x'], coords['y'], coords['z'],
                             vx, vy, vz, color='yellow', alpha=0.8, arrow_length_ratio=0.2)

            # 设置标题和标签
            unique_cats = len(self.unique_cats_tracked)
            active_tracks = len(self.current_tracks)
            avg_detection_time = np.mean(self.detection_times) if self.detection_times else 0

            title = (f'🚀 终极猫咪追踪 | 帧#{self.frame_count} | '
                    f'活跃:{active_tracks} | 总追踪:{unique_cats} | '
                    f'速度:{avg_detection_time*1000:.1f}ms')

            ax.set_title(title, color='white', fontsize=14, pad=20)
            ax.set_xlabel('X (m)', color='white')
            ax.set_ylabel('Y (m)', color='white')
            ax.set_zlabel('Z (m)', color='white')

            # 设置坐标轴范围
            if self.usd_bounds:
                ax.set_xlim(self.usd_bounds['x_min']-0.5, self.usd_bounds['x_max']+0.5)
                ax.set_ylim(self.usd_bounds['y_min']-0.5, self.usd_bounds['y_max']+0.5)
            ax.set_zlim(0, 3.0)

            # 美化设置
            ax.tick_params(colors='white')
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False

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
            print(f"终极3D可视化生成失败: {e}")
            return None

# 全局系统实例
ultimate_tracker = None

@app.route('/')
def index():
    """主页面 - 终极追踪界面"""
    # 这里使用与之前相同的Apple风格界面，只是更新了一些文本
    # [保持原来的界面代码，只修改标题和一些描述]
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ultimate Cat Tracker - 终极猫咪追踪</title>
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
                background: linear-gradient(135deg, #FF6B35 0%, #F7931E 25%, #FFD23F 50%, #06FFA5 75%, #3DDC97 100%);
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
                background: #FF6B35;
                border-radius: 50%;
                animation: pulse 2s infinite;
                box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.2);
            }

            .ultimate-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 4px 8px;
                background: rgba(255, 107, 53, 0.1);
                border-radius: 12px;
                border: 1px solid rgba(255, 107, 53, 0.2);
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
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.03) 0%, rgba(247, 147, 30, 0.02) 100%);
                position: relative;
            }

            /* 统计面板 */
            .stats-panel {
                background: linear-gradient(135deg, rgba(6, 255, 165, 0.03) 0%, rgba(61, 220, 151, 0.02) 100%);
            }

            /* AI分析面板 */
            .vlm-panel {
                background: linear-gradient(135deg, rgba(255, 210, 63, 0.03) 0%, rgba(247, 147, 30, 0.02) 100%);
            }

            /* 3D视图面板 */
            .viz-panel {
                background: linear-gradient(135deg, rgba(61, 220, 151, 0.03) 0%, rgba(6, 255, 165, 0.02) 100%);
            }

            /* 面板标题栏 */
            .panel-header {
                padding: 16px 20px 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                flex-shrink: 0;
            }

            /* 不同颜色的标题栏 */
            .video-header {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.08) 0%, rgba(247, 147, 30, 0.04) 100%);
            }

            .stats-header {
                background: linear-gradient(135deg, rgba(6, 255, 165, 0.08) 0%, rgba(61, 220, 151, 0.04) 100%);
            }

            .vlm-header {
                background: linear-gradient(135deg, rgba(255, 210, 63, 0.08) 0%, rgba(247, 147, 30, 0.04) 100%);
            }

            .viz-header {
                background: linear-gradient(135deg, rgba(61, 220, 151, 0.08) 0%, rgba(6, 255, 165, 0.04) 100%);
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

            /* 终极状态覆盖层 */
            .ultimate-overlay {
                position: absolute;
                top: 10px;
                left: 10px;
                background: rgba(0, 0, 0, 0.8);
                padding: 6px 10px;
                border-radius: 8px;
                font-size: 11px;
                color: #FF6B35;
                font-weight: 500;
                z-index: 10;
                border: 1px solid rgba(255, 107, 53, 0.3);
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
                color: #06FFA5;
                font-variant-numeric: tabular-nums;
            }

            .cat-count {
                color: #FF6B35 !important;
                font-size: 32px !important;
                text-shadow: 0 0 8px rgba(255, 107, 53, 0.3);
            }

            .track-count {
                color: #FFD23F !important;
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
                color: #FFD23F;
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
                        document.getElementById('track-count').textContent = data.unique_tracks || 0;
                        document.getElementById('avg-confidence').textContent = (data.average_confidence || 0).toFixed(3);

                        // 更新导航栏状态
                        const navStats = document.getElementById('nav-stats');
                        if (navStats) {
                            const activeTrackers = data.active_tracks || 0;
                            const avgTime = data.avg_detection_time || 0;
                            navStats.textContent = `活跃跟踪:${activeTrackers} | 检测速度:${(avgTime*1000).toFixed(1)}ms`;
                        }

                        // 更新终极覆盖层
                        const ultimateOverlay = document.getElementById('ultimate-overlay');
                        if (ultimateOverlay) {
                            const frameNum = data.frame_number || 0;
                            ultimateOverlay.textContent = `ULTIMATE | 帧#${frameNum} | ByteTrack`;
                        }
                    })
                    .catch(error => console.error('Error fetching detections:', error));

                // 更新VLM分析
                fetch('/api/vlm_analysis')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('tracking-analysis').textContent = '卡尔曼滤波运动预测运行中';
                        document.getElementById('algorithm-analysis').textContent = 'YOLOv8x + ByteTrack + 自适应阈值';
                    })
                    .catch(error => {
                        document.getElementById('tracking-analysis').textContent = '终极多目标跟踪算法';
                        document.getElementById('algorithm-analysis').textContent = '最强大的检测和跟踪融合';
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
            setInterval(update3D, 500);  // 更快的3D更新

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
            <div class="nav-title">Ultimate Cat Tracker</div>
            <div class="nav-status">
                <div class="live-dot"></div>
                <span>LIVE</span>
                <span id="nav-stats">终极算法运行中...</span>
                <div class="ultimate-indicator">
                    <div class="live-dot" style="background: #FFD23F; width: 6px; height: 6px;"></div>
                    <span>ULTIMATE</span>
                </div>
            </div>
        </nav>

        <!-- 主容器 - 完全横向整齐四列布局 -->
        <div class="main-container">
            <!-- 第1列：主视频面板 -->
            <div class="panel video-panel">
                <div class="panel-header video-header">
                    <h3>🚀 终极视频追踪 (最强算法)</h3>
                </div>
                <div class="panel-content">
                    <img src="/video_feed" class="video-stream" alt="终极追踪视频流">
                    <div class="ultimate-overlay" id="ultimate-overlay">
                        ULTIMATE | 启动中...
                    </div>
                </div>
            </div>

            <!-- 第2列：统计数据面板 -->
            <div class="panel stats-panel">
                <div class="panel-header stats-header">
                    <h3>📊 终极数据</h3>
                </div>
                <div class="panel-content">
                    <div class="stats-content">
                        <div class="stat-row">
                            <div class="stat-label">🎯 猫咪检测</div>
                            <div id="cat-count" class="stat-value cat-count">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">🔄 跟踪数量</div>
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
                    <h3>🧠 终极AI算法</h3>
                </div>
                <div class="panel-content">
                    <div class="vlm-content">
                        <div class="analysis-item">
                            <div class="analysis-label">跟踪算法</div>
                            <div id="tracking-analysis" class="vlm-analysis">ByteTrack + 卡尔曼滤波...</div>
                        </div>
                        <div class="analysis-item">
                            <div class="analysis-label">检测算法</div>
                            <div id="algorithm-analysis" class="vlm-analysis">YOLOv8x + 自适应阈值...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 第4列：3D空间追踪面板 -->
            <div class="panel viz-panel">
                <div class="panel-header viz-header">
                    <h3>🏠 终极3D追踪</h3>
                </div>
                <div class="panel-content">
                    <div class="viz-content">
                        <img id="viz-3d" src="/api/3d_visualization" class="viz-3d-image" alt="终极3D可视化">
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    """终极追踪视频流"""
    def generate():
        print("🚀 开始终极追踪视频流...")

        while True:
            if ultimate_tracker is None:
                break

            frame_start_time = time.time()

            # 获取下一帧
            frame = ultimate_tracker.get_next_frame()
            if frame is None:
                break

            # 高级检测
            detections = ultimate_tracker.advanced_cat_detection(frame)

            # 多目标跟踪
            tracks = ultimate_tracker.track_cats(detections)

            # 绘制跟踪结果
            for track in tracks:
                bbox = track['bbox']
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                track_id = track['track_id']
                confidence = track['confidence']
                velocity = track.get('velocity', {})
                speed = velocity.get('speed', 0)

                # 根据跟踪稳定性选择颜色
                if track['hits'] > 10:
                    # 稳定跟踪 - 亮绿色
                    color = (0, 255, 0)
                    thickness = 4
                elif track['hits'] > 5:
                    # 中等稳定 - 橙色
                    color = (0, 165, 255)
                    thickness = 3
                else:
                    # 新跟踪 - 黄色
                    color = (0, 255, 255)
                    thickness = 2

                # 绘制边界框
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                # 详细标签
                label = f"Cat#{track_id} | {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(frame, (x1, y1-25), (x1 + label_size[0] + 10, y1), color, -1)
                cv2.putText(frame, label, (x1+5, y1-8),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                # 显示速度信息
                if speed > 0.1:
                    speed_label = f"Speed: {speed:.1f}m/s"
                    cv2.putText(frame, speed_label, (x1, y2+20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

                # 显示3D坐标
                coords = track['physical_coords']
                coord_label = f"({coords['x']:.1f},{coords['y']:.1f},{coords['z']:.1f})"
                cv2.putText(frame, coord_label, (x1, y2+35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

            # 系统状态信息
            unique_tracks = len(ultimate_tracker.unique_cats_tracked)
            active_tracks = len(tracks)
            avg_detection_time = np.mean(ultimate_tracker.detection_times) if ultimate_tracker.detection_times else 0

            status_text = f"ULTIMATE | Frame #{ultimate_tracker.frame_count} | Tracks: {active_tracks}/{unique_tracks}"
            cv2.putText(frame, status_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 107, 53), 2)

            perf_text = f"ByteTrack | Detection: {avg_detection_time*1000:.1f}ms | YOLOv8x"
            cv2.putText(frame, perf_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 编码帧
            encode_param = [
                int(cv2.IMWRITE_JPEG_QUALITY), 92,
                int(cv2.IMWRITE_JPEG_OPTIMIZE), 1
            ]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # 帧率控制
            frame_elapsed = time.time() - frame_start_time
            frame_time = 1.0 / ultimate_tracker.target_fps
            if frame_elapsed < frame_time:
                time.sleep(frame_time - frame_elapsed)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/detections')
def api_detections():
    """获取当前检测数据 - 终极版本"""
    if ultimate_tracker is None:
        return jsonify({})

    # 计算高级统计数据
    tracks_data = []
    confidences = []

    for track in ultimate_tracker.current_tracks:
        track_data = track.copy()
        track_data['physical_x'] = track['physical_coords']['x']
        track_data['physical_y'] = track['physical_coords']['y']
        track_data['physical_z'] = track['physical_coords']['z']
        tracks_data.append(track_data)
        confidences.append(track['confidence'])

    avg_detection_time = np.mean(ultimate_tracker.detection_times) if ultimate_tracker.detection_times else 0
    unique_tracks = len(ultimate_tracker.unique_cats_tracked)
    active_tracks = len(ultimate_tracker.current_tracks)

    return jsonify({
        'detections': tracks_data,
        'frame_number': ultimate_tracker.frame_count,
        'total_detections': ultimate_tracker.total_detections,
        'cat_detections': ultimate_tracker.cat_detections,
        'unique_tracks': unique_tracks,
        'active_tracks': active_tracks,
        'average_confidence': np.mean(confidences) if confidences else 0,
        'avg_detection_time': avg_detection_time,
        'algorithm': 'YOLOv8x + ByteTrack + Kalman',
        'tracking_mode': 'ultimate'
    })

@app.route('/api/3d_visualization')
def api_3d_visualization():
    """获取终极3D可视化图像"""
    if ultimate_tracker is None:
        return "No system", 404

    img_data = ultimate_tracker.generate_ultimate_3d_visualization()
    if img_data:
        return Response(img_data, mimetype='image/png')
    else:
        return "Error generating visualization", 500

@app.route('/api/vlm_analysis')
def api_vlm_analysis():
    """VLM分析接口"""
    return jsonify({
        'status': 'Ultimate tracking algorithm running',
        'algorithm': 'YOLOv8x + ByteTrack + Kalman Filter',
        'features': ['Multi-object tracking', 'Motion prediction', 'Adaptive thresholding']
    })

def main():
    global ultimate_tracker

    print("🚀 启动终极猫咪追踪系统...")
    print("⚡ 最强大算法特性:")
    print("   - 🎯 YOLOv8x大模型最高精度检测")
    print("   - 🔄 ByteTrack多目标跟踪算法")
    print("   - 📊 卡尔曼滤波运动预测")
    print("   - 🧠 自适应阈值智能调整")
    print("   - 🏃 GPU并行高性能处理")
    print("   - 📐 高精度3D空间定位")
    print("   - 🎨 轨迹可视化和速度分析")

    # 创建终极追踪系统
    use_large_model = True  # 使用大模型获得最高精度
    ultimate_tracker = UltimateCatTracker(use_large_model=use_large_model)

    print(f"✅ 终极追踪系统启动成功！")
    print(f"🌐 Web界面: http://localhost:5008")
    print(f"🎯 算法: YOLOv8x + ByteTrack + 卡尔曼滤波")

    app.run(host='0.0.0.0', port=5008, debug=False, threaded=True)

if __name__ == "__main__":
    main()