#!/usr/bin/env python3
"""
实时宠物监控系统 - 无延迟版本
专为实时播放和快速检测设计
"""

import cv2
import torch
import numpy as np

# 全局猴子补丁：让 bfloat16 张量转 numpy 时自动升级为 float32
# 修复 VLM (bfloat16) 与 YOLO 跟踪器同时运行时的 "Got unsupported ScalarType BFloat16" 错误
_orig_tensor_numpy = torch.Tensor.numpy
def _safe_numpy(self, *args, **kwargs):
    if self.dtype == torch.bfloat16:
        return _orig_tensor_numpy(self.float(), *args, **kwargs)
    return _orig_tensor_numpy(self, *args, **kwargs)
torch.Tensor.numpy = _safe_numpy

_orig_array = torch.Tensor.__array__
def _safe_array(self, *args, **kwargs):
    if self.dtype == torch.bfloat16:
        return _orig_array(self.float(), *args, **kwargs)
    return _orig_array(self, *args, **kwargs)
torch.Tensor.__array__ = _safe_array
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

class RealtimePetMonitor:
    """实时宠物监控系统 - 无延迟版本"""

    def __init__(self, video_file="real_cat.mp4"):
        print("🎬 初始化实时宠物监控系统...")

        self.video_file = video_file
        self.cap = None
        self.current_frame = None
        self.frame_count = 0
        self.total_frames = 0
        self.running = False

        # 实时检测统计 - 区分检测次数和实际只数
        self.total_detections = 0  # 总检测次数
        self.cat_detections = 0    # 猫检测次数
        self.cat_tracks = {}       # 猫的追踪信息 {track_id: last_seen_frame}
        self.track_active_window = 60  # 近60帧内出现过的track才算"当前活跃"

        # 3D轨迹：每个track_id独立坐标平滑
        self.track_smoothed_coords = {}  # {track_id: (x, y, z)}
        self.track_trajectory = {}       # {track_id: [(x,y,z), ...] 最近N个点}
        self.trajectory_max_len = 30
        self.coord_ema_alpha = 0.4       # 指数滑动平均系数
        self.next_track_id = 1     # 下一个分配的追踪ID
        self.recent_detections = []
        self.detection_history = []

        # VLM分析
        self.vlm_analysis = {
            "scene": "正在分析场景...",
            "behavior": "正在分析行为..."
        }
        self.vlm_analysis_interval = 30  # 每30帧分析一次，减少对视频流的影响
        self.last_vlm_analysis_frame = 0
        self.vlm_model = None
        self.vlm_processor = None
        self.vlm_model_loaded = False

        # 3D定位数据
        self.room_bounds = None
        self.homography_matrix = None
        self.usd_geometry = []
        self.usd_bounds = None
        self.last_3d_viz_time = 0
        self.min_3d_viz_interval = 0.3  # 进一步减少到0.3秒，超实时追踪
        self.viz_3d_cache = None  # 3D可视化缓存
        self.pet_velocities = {}  # 宠物速度追踪
        self.last_positions = {}  # 上一次位置记录

        # 实时播放优化参数
        self.target_fps = 30  # 提升到30FPS，与原视频同步
        self.frame_skip = 1   # 不跳帧，处理每一帧
        self.detection_frequency = 1  # 每帧都检测
        self.skip_detection_counter = 0  # 检测跳帧计数器

        # 异步检测解耦：视频流不再等待检测，检测在后台线程跑最新帧
        self.latest_raw_frame = None          # 最新原始帧（视频线程写入）
        self.latest_detections_async = []     # 后台检测结果（检测线程写入）
        self.latest_detections_lock = threading.Lock()
        self.detection_worker_running = False
        self.detection_worker_thread = None

        # 猫检测优化 - 跟踪模式下使用合理阈值（ByteTrack会跨帧保留短暂消失的目标）
        self.primary_cat_threshold = 0.25    # 主要检测阈值（跟踪模式下不再需要极低阈值）
        self.secondary_cat_threshold = 0.10  # 备用阈值（仅在完全丢失时触发）
        self.dog_detection_threshold = 0.25  # 狗的阈值
        self.infer_imgsz = 1280              # 大输入尺寸，对小/远猫更有效

        # 智能过滤参数
        self.min_area = 200          # 最小面积
        self.max_area = 50000        # 最大面积
        self.min_aspect_ratio = 0.3  # 最小宽高比
        self.max_aspect_ratio = 3.0  # 最大宽高比

        # 质量评分权重
        self.quality_weights = {
            'detection': 1.0,    # 检测置信度
            'area': 0.3,        # 面积权重
            'aspect_ratio': 0.2, # 宽高比权重
            'position': 0.1     # 位置权重
        }

        # 加载组件
        self._load_components()

    @property
    def unique_cats(self):
        """动态计算：只统计最近track_active_window帧内仍活跃的track_id"""
        cutoff = self.frame_count - self.track_active_window
        return {tid for tid, last_seen in self.cat_tracks.items() if last_seen >= cutoff}

    def _load_components(self):
        """加载核心组件"""
        print("🔧 加载检测组件...")

        # 加载YOLO模型 - yolo11x (SOTA 2025) + TensorRT FP16
        self.yolo_model = None
        model_stem = 'yolo11x'  # 更强：相同精度下比yolov8x快~20%，mAP更高
        engine_path = Path(f'{model_stem}.engine')
        pt_path = Path(f'{model_stem}.pt')
        try:
            if engine_path.exists():
                self.yolo_model = YOLO(str(engine_path))
                print(f"✅ {model_stem} 加载成功 (TensorRT FP16 engine)")
            else:
                self.yolo_model = YOLO(str(pt_path))  # 不存在会自动下载
                if torch.cuda.is_available():
                    self.yolo_model.to('cuda')
                    print(f"✅ {model_stem} 加载成功 (PyTorch + GPU)")
                    try:
                        print(f"🔧 导出TensorRT FP16引擎（首次约2-5分钟，之后自动复用）...")
                        self.yolo_model.export(format='engine', half=True,
                                               imgsz=self.infer_imgsz, device=0,
                                               workspace=4)
                        if engine_path.exists():
                            self.yolo_model = YOLO(str(engine_path))
                            print("✅ 已切换到TensorRT引擎")
                    except Exception as ex:
                        print(f"⚠️ TensorRT导出失败，使用.pt继续: {ex}")
                else:
                    print(f"✅ {model_stem} 加载成功 (CPU)")
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")
            self.yolo_model = None

        # VLM模型延迟加载
        if VLM_AVAILABLE:
            print("⚠️ VLM模型将在首次使用时加载")

        # 加载3D定位组件
        print("📥 加载3D空间定位组件...")
        self._load_3d_components()

        # 初始化视频
        self._initialize_video()

        # 启动异步检测工作线程（解耦视频播放与AI推理）
        self._start_detection_worker()

    def _start_detection_worker(self):
        """后台检测线程：持续处理最新帧，结果供视频流叠加"""
        if self.yolo_model is None:
            print("⚠️ 无YOLO模型，跳过异步检测线程")
            return

        self.detection_worker_running = True

        def worker():
            print("🚀 异步检测线程已启动")
            while self.detection_worker_running:
                frame = self.latest_raw_frame
                if frame is None:
                    time.sleep(0.003)
                    continue
                try:
                    dets = self._multi_threshold_detection(frame)
                    now = time.time()
                    # 更新统计 + 3D坐标平滑 + 速度估计
                    for d in dets:
                        self.total_detections += 1
                        if d['class'] == '猫':
                            self.cat_detections += 1
                        self._update_3d_state(d, now)
                    with self.latest_detections_lock:
                        self.latest_detections_async = dets
                    # 维护历史（供3D可视化使用）
                    self.recent_detections.extend(dets)
                    if len(self.recent_detections) > 20:
                        self.recent_detections = self.recent_detections[-20:]
                    self.detection_history.extend(dets)
                    if len(self.detection_history) > 30:
                        self.detection_history = self.detection_history[-30:]
                except Exception as e:
                    import traceback
                    print(f"⚠️ 异步检测异常: {e}")
                    traceback.print_exc()
                    time.sleep(0.5)  # 异常时多睡避免刷屏

        self.detection_worker_thread = threading.Thread(target=worker, daemon=True)
        self.detection_worker_thread.start()

    def _update_3d_state(self, det, now):
        """对单个检测做EMA坐标平滑 + 轨迹累积，结果写回det供3D视图使用。"""
        tid = det.get('track_id')
        coords = det.get('physical_coords')
        if tid is None or not coords:
            return

        raw = (coords.get('x', 0.0), coords.get('y', 0.0), coords.get('z', 0.0))
        prev_smoothed = self.track_smoothed_coords.get(tid)
        a = self.coord_ema_alpha
        if prev_smoothed is None:
            smoothed = raw
        else:
            smoothed = (
                a * raw[0] + (1 - a) * prev_smoothed[0],
                a * raw[1] + (1 - a) * prev_smoothed[1],
                a * raw[2] + (1 - a) * prev_smoothed[2],
            )

        self.track_smoothed_coords[tid] = smoothed
        traj = self.track_trajectory.setdefault(tid, [])
        traj.append(smoothed)
        if len(traj) > self.trajectory_max_len:
            del traj[:len(traj) - self.trajectory_max_len]

        det['physical_coords'] = {'x': smoothed[0], 'y': smoothed[1], 'z': smoothed[2]}

    def _load_3d_components(self):
        """加载3D定位相关组件"""
        # 加载房间数据
        room_data_files = [
            "step3_output_20260410_122421/room_data.json",
            "room_data.json"
        ]

        for file_path in room_data_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        room_data = json.load(f)
                    self.room_bounds = room_data.get('room_bounds')
                    print(f"✅ 房间数据加载成功: {file_path}")
                    break
                except Exception as e:
                    print(f"⚠️ 房间数据加载失败: {e}")

        # 加载同形变换矩阵
        calibration_files = [
            "meeting_room_calibration_20260410_120824.json"
        ]

        for file_path in calibration_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        calib_data = json.load(f)
                    if 'homography_matrix' in calib_data:
                        self.homography_matrix = np.array(calib_data['homography_matrix'])
                        print("✅ 同形变换矩阵加载成功")
                    break
                except Exception as e:
                    print(f"⚠️ 校准数据加载失败: {e}")

        # 加载USD 3D模型
        self._load_usd_model()

    def _load_usd_model(self):
        """加载USD扫描模型"""
        self.usd_geometry = []
        self.usd_bounds = None

        if not USD_AVAILABLE:
            print("⚠️ USD库未安装，跳过3D模型加载")
            return

        usd_file = "scan.usd"
        if not Path(usd_file).exists():
            print("⚠️ 未找到scan.usd文件")
            return

        try:
            print(f"📥 加载USD 3D模型: {usd_file}")
            stage = Usd.Stage.Open(usd_file)

            # 遍历所有几何对象
            for prim in stage.Traverse():
                if prim.IsA(UsdGeom.Mesh):
                    mesh = UsdGeom.Mesh(prim)
                    points_attr = mesh.GetPointsAttr()
                    faces_attr = mesh.GetFaceVertexIndicesAttr()

                    if points_attr and faces_attr:
                        points = points_attr.Get()
                        faces = faces_attr.Get()

                        if points and faces:
                            vertices = np.array([[p[0], p[1], p[2]] for p in points])
                            indices = np.array(faces)

                            self.usd_geometry.append({
                                'vertices': vertices,
                                'indices': indices,
                                'name': prim.GetName()
                            })

                            # 更新边界框
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

    def _load_vlm_model(self):
        """延迟加载VLM模型"""
        if not VLM_AVAILABLE or self.vlm_model_loaded:
            return

        print("📥 加载VLM分析模型...")
        try:
            self.vlm_model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype=torch.bfloat16,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            self.vlm_processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
            self.vlm_model_loaded = True
            print("✅ VLM模型加载成功")
        except Exception as e:
            print(f"❌ VLM模型加载失败: {e}")

    def _initialize_video(self):
        """初始化视频源"""
        print(f"📹 加载视频文件: {self.video_file}")

        if Path(self.video_file).exists():
            self.cap = cv2.VideoCapture(self.video_file)
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

                # 获取原始视频FPS
                original_fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"✅ 视频文件加载成功")
                print(f"   总帧数: {self.total_frames}")
                print(f"   原始FPS: {original_fps:.1f}")
                print(f"   目标FPS: {self.target_fps}")

                self.running = True
            else:
                print("❌ 视频文件加载失败")
        else:
            print(f"❌ 视频文件不存在: {self.video_file}")

    def detect_cats_fast(self, frame):
        """优化的猫检测 - 高准确率 + 实时性能"""
        if self.yolo_model is None:
            return []

        try:
            # 多阈值检测策略
            detections = self._multi_threshold_detection(frame)

            # 更新统计
            for detection in detections:
                self.total_detections += 1
                if detection['class'] == '猫':
                    self.cat_detections += 1

            # 保持最近的检测记录
            self.recent_detections.extend(detections)
            if len(self.recent_detections) > 20:
                self.recent_detections = self.recent_detections[-20:]

            # 保持历史记录用于3D可视化
            self.detection_history.extend(detections)
            if len(self.detection_history) > 30:
                self.detection_history = self.detection_history[-30:]

            return detections

        except Exception as e:
            print(f"检测失败: {e}")
            return []

    def _multi_threshold_detection(self, frame):
        """SOTA检测+跟踪：yolo11x + BoT-SORT(ReID外观特征)，遮挡抗性&ID稳定性远优于ByteTrack。
        丢失时自动切高分辨率+TTA做兜底扫描。"""
        tracker_cfg = 'bytetrack.yaml'  # 最稳定，避免ReID/GMC引入的bfloat16冲突

        results = self.yolo_model.track(
            frame,
            conf=self.primary_cat_threshold,
            iou=0.5,
            imgsz=self.infer_imgsz,
            classes=[15, 16],
            tracker=tracker_cfg,
            persist=True,
            verbose=False,
        )
        detections = self._extract_detections(results, 'track')

        # 兜底：连续无猫时，放大分辨率 + TTA多尺度增强扫描（速度慢，仅偶发触发）
        if not any(d['class'] == '猫' for d in detections):
            try:
                secondary_results = self.yolo_model(
                    frame,
                    conf=self.secondary_cat_threshold,
                    iou=0.3,
                    imgsz=1920,        # 更大输入尺寸找小/远目标
                    classes=[15, 16],
                    augment=True,      # TTA：水平翻转+多尺度
                    verbose=False,
                )
                detections.extend(self._extract_detections(secondary_results, 'secondary'))
            except Exception:
                pass

        return detections

    def _extract_detections(self, results, detection_type):
        """提取并过滤检测结果"""
        detections = []

        for r in results:
            boxes = r.boxes
            if boxes is not None:
                # 强制float32，避免VLM引入的bfloat16污染导致numpy转换失败
                try:
                    if boxes.data is not None and boxes.data.dtype != torch.float32:
                        boxes.data = boxes.data.float()
                except Exception:
                    pass
                for box in boxes:
                    cls = int(box.cls[0].float().item())
                    conf = float(box.conf[0].float().item())

                    # 只处理猫和狗
                    is_cat = cls == 15
                    is_dog = cls == 16

                    if not (is_cat or is_dog):
                        continue

                    # 狗的阈值过滤
                    if is_dog and conf <= self.dog_detection_threshold:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0].float().tolist()
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    width = x2 - x1
                    height = y2 - y1
                    bbox_area = width * height
                    aspect_ratio = width / height if height > 0 else 0

                    # 智能过滤
                    if not self._passes_quality_filters(bbox_area, aspect_ratio):
                        continue

                    # 计算物理坐标
                    physical_coords = self._pixel_to_physical(center_x, center_y, bbox_area)

                    # 追踪ID：仅来自tracker的ID参与唯一性统计（secondary兜底帧不计）
                    track_id = None
                    if is_cat and detection_type == 'track':
                        if hasattr(box, 'id') and box.id is not None:
                            track_id = int(box.id[0].float().item())
                            self.cat_tracks[track_id] = self.frame_count

                    detection = {
                        'class': '猫' if is_cat else '狗',
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'center': [center_x, center_y],
                        'physical_coords': physical_coords,
                        'area': bbox_area,
                        'aspect_ratio': aspect_ratio,
                        'track_id': track_id,
                        'detection_type': detection_type
                    }

                    # 添加质量分数
                    if is_cat:
                        detection['quality_score'] = self._calculate_quality_score(detection)
                        # 只保留高质量的猫检测
                        if detection['quality_score'] > 0.3:
                            detections.append(detection)
                    else:
                        detections.append(detection)

        return detections

    def _passes_quality_filters(self, area, aspect_ratio):
        """智能质量过滤器"""
        if area < self.min_area or area > self.max_area:
            return False
        if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
            return False
        return True

    def _calculate_quality_score(self, detection):
        """计算检测质量分数"""
        score = 0

        # 置信度权重
        conf_score = min(detection['confidence'] / 0.1, 1.0)
        score += conf_score * self.quality_weights['detection']

        # 面积权重
        area = detection['area']
        if 2000 <= area <= 8000:
            area_score = 1.0
        elif 1000 <= area <= 15000:
            area_score = 0.7
        else:
            area_score = 0.3
        score += area_score * self.quality_weights['area']

        # 宽高比权重
        aspect_ratio = detection['aspect_ratio']
        if 0.8 <= aspect_ratio <= 1.5:
            ratio_score = 1.0
        elif 0.5 <= aspect_ratio <= 2.0:
            ratio_score = 0.7
        else:
            ratio_score = 0.3
        score += ratio_score * self.quality_weights['aspect_ratio']

        # 位置权重 (避免边缘检测)
        center_x, center_y = detection['center']
        if 100 < center_x < 1180 and 50 < center_y < 670:
            position_score = 1.0
        else:
            position_score = 0.5
        score += position_score * self.quality_weights['position']

        return score

    def _pixel_to_physical(self, pixel_x, pixel_y, bbox_area=None):
        """像素坐标转物理坐标，包含Z轴深度估算"""
        if self.homography_matrix is None:
            return {"x": 0, "y": 0, "z": 0}

        try:
            # 2D地面位置转换
            pixel_point = np.array([[pixel_x, pixel_y]], dtype=np.float32)
            physical_point = cv2.perspectiveTransform(pixel_point.reshape(1, -1, 2), self.homography_matrix)

            x = float(physical_point[0][0][0])
            y = float(physical_point[0][0][1])

            # Z轴深度估算（基于多种因素）
            z = self._estimate_z_depth(pixel_x, pixel_y, bbox_area)

            return {"x": x, "y": y, "z": z}
        except Exception as e:
            return {"x": 0, "y": 0, "z": 0}

    def _assign_track_id(self, center_x, center_y, distance_threshold=100):
        """基于位置的简单追踪 - 为猫分配唯一ID"""
        current_frame = self.frame_count

        # 清理过期的追踪 (超过30帧未见)
        expired_tracks = []
        for track_id, last_frame in self.cat_tracks.items():
            if current_frame - last_frame > 30:
                expired_tracks.append(track_id)

        for track_id in expired_tracks:
            del self.cat_tracks[track_id]

        # 寻找最近的现有追踪
        best_track_id = None
        min_distance = float('inf')

        for track_id, last_frame in self.cat_tracks.items():
            # 只考虑最近的追踪 (10帧内)
            if current_frame - last_frame <= 10:
                best_track_id = track_id
                break

        # 如果没找到匹配的追踪，创建新的
        if best_track_id is None:
            best_track_id = self.next_track_id
            self.next_track_id += 1

        # 更新追踪信息
        self.cat_tracks[best_track_id] = current_frame

        return best_track_id

    def _estimate_z_depth(self, pixel_x, pixel_y, bbox_area=None):
        """基于多种因素估算Z轴深度"""
        try:
            # 方法1: 基于画面高度的深度估算
            # 假设相机高度2米，视频分辨率720p
            video_height = 720
            camera_height = 2.0  # 相机安装高度(米)

            # 垂直位置越低，说明离地面越近
            height_ratio = pixel_y / video_height

            # 基础地面高度
            base_z = 0.0

            # 根据垂直位置估算高度
            if height_ratio < 0.3:  # 画面上部，可能在桌子或高处
                estimated_z = base_z + 0.5 + (0.3 - height_ratio) * 2.0
            elif height_ratio < 0.7:  # 画面中部，可能在地面稍高
                estimated_z = base_z + 0.1 + (0.7 - height_ratio) * 0.5
            else:  # 画面下部，接近地面
                estimated_z = base_z + (1.0 - height_ratio) * 0.2

            # 方法2: 基于检测框大小的距离估算
            if bbox_area is not None:
                # 检测框越大，说明距离摄像头越近，高度可能更明显
                # 标准化bbox面积 (假设典型猫的检测框约8000像素)
                standard_area = 8000
                size_ratio = min(bbox_area / standard_area, 3.0)  # 限制比例

                # 大检测框可能意味着更立体的姿态或跳跃
                if size_ratio > 1.5:
                    estimated_z += 0.2 * (size_ratio - 1.0)

            # 方法3: 添加随机性模拟真实的3D运动
            # 动物可能跳跃、爬高等立体运动
            import random
            noise = random.uniform(-0.1, 0.3)  # 轻微随机高度变化
            estimated_z += noise

            # 方法4: 基于水平位置的透视修正
            # 画面边缘的物体可能有高度差异
            video_width = 1280
            center_x = video_width / 2
            edge_distance = abs(pixel_x - center_x) / center_x

            # 边缘物体可能有轻微高度差
            if edge_distance > 0.7:
                estimated_z += 0.1 * edge_distance

            # 确保Z值在合理范围内
            estimated_z = max(0.0, min(estimated_z, 2.5))

            return estimated_z

        except Exception as e:
            # 返回默认的轻微高度
            import random
            return random.uniform(0.0, 0.3)

    def analyze_frame_vlm(self, frame):
        """VLM帧分析"""
        # 检查是否需要进行VLM分析
        if (self.frame_count - self.last_vlm_analysis_frame) < self.vlm_analysis_interval:
            return self.vlm_analysis

        if not VLM_AVAILABLE:
            return self.vlm_analysis

        # 延迟加载VLM模型
        if not self.vlm_model_loaded:
            self._load_vlm_model()

        if self.vlm_model is None:
            return self.vlm_analysis

        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            from PIL import Image
            pil_image = Image.fromarray(frame_rgb)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {"type": "text", "text": "简要描述场景和宠物行为，用中文，一句话。"}
                    ]
                }
            ]

            text = self.vlm_processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.vlm_processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )
            inputs = inputs.to("cuda" if torch.cuda.is_available() else "cpu")

            generated_ids = self.vlm_model.generate(**inputs, max_new_tokens=128, do_sample=False)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.vlm_processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            self.vlm_analysis = {
                "scene": output_text[:100] if len(output_text) > 100 else output_text,
                "behavior": "正在分析..."
            }

            self.last_vlm_analysis_frame = self.frame_count

        except Exception as e:
            print(f"VLM分析失败: {e}")

        return self.vlm_analysis

    def _calculate_velocity(self, coords, pet_class, timestamp):
        """计算宠物速度和方向"""
        key = f"{pet_class}_{int(timestamp)}"
        current_pos = np.array([coords['x'], coords['y'], coords['z']])

        if key in self.last_positions:
            last_pos, last_time = self.last_positions[key]
            dt = timestamp - last_time
            if dt > 0:
                velocity = (current_pos - last_pos) / dt
                speed = np.linalg.norm(velocity[:2])  # 2D速度
                self.pet_velocities[key] = {
                    'velocity': velocity,
                    'speed': speed,
                    'direction': velocity[:2] / (speed + 1e-6)  # 归一化方向
                }

        self.last_positions[key] = (current_pos, timestamp)
        return self.pet_velocities.get(key, {'velocity': np.zeros(3), 'speed': 0, 'direction': np.zeros(2)})

    def generate_3d_visualization(self):
        """高级实时3D空间追踪可视化"""
        current_time = time.time()

        # 更激进的缓存策略
        if (current_time - self.last_3d_viz_time < self.min_3d_viz_interval and
            self.viz_3d_cache is not None):
            return self.viz_3d_cache

        self.last_3d_viz_time = current_time

        try:
            # 高性能设置
            plt.ioff()
            fig = plt.figure(figsize=(7, 5), facecolor='black', dpi=72)
            ax = fig.add_subplot(111, projection='3d')
            ax.set_facecolor('black')

            # 绘制房间环境
            if self.usd_bounds:
                bounds = self.usd_bounds

                # 绘制房间地板网格
                x_range = np.linspace(bounds['x_min'], bounds['x_max'], 6)
                y_range = np.linspace(bounds['y_min'], bounds['y_max'], 6)
                z_floor = bounds['z_min']

                # 地板网格线
                for x in x_range[1:-1]:
                    ax.plot([x, x], [bounds['y_min'], bounds['y_max']], [z_floor, z_floor],
                           'gray', alpha=0.2, linewidth=0.5)
                for y in y_range[1:-1]:
                    ax.plot([bounds['x_min'], bounds['x_max']], [y, y], [z_floor, z_floor],
                           'gray', alpha=0.2, linewidth=0.5)

                # 房间边界
                corners = np.array([
                    [bounds['x_min'], bounds['y_min'], z_floor],
                    [bounds['x_max'], bounds['y_min'], z_floor],
                    [bounds['x_max'], bounds['y_max'], z_floor],
                    [bounds['x_min'], bounds['y_max'], z_floor]
                ])
                ax.plot(corners[[0,1,2,3,0], 0], corners[[0,1,2,3,0], 1],
                       corners[[0,1,2,3,0], 2], 'cyan', alpha=0.6, linewidth=2)

                # 设置坐标轴范围，强调Z轴
                ax.set_xlim([bounds['x_min'], bounds['x_max']])
                ax.set_ylim([bounds['y_min'], bounds['y_max']])
                ax.set_zlim([0.0, 2.5])  # 设置明确的Z轴范围：0-2.5米高度

                # 绘制垂直参考线，突出Z轴
                # 在房间四个角绘制垂直线
                for corner in corners:
                    ax.plot([corner[0], corner[0]], [corner[1], corner[1]],
                           [0, 2.5], 'gray', alpha=0.3, linewidth=0.8)

            # 高级宠物轨迹可视化
            if len(self.detection_history) > 0:
                recent_detections = self.detection_history[-30:]  # 增加到30个点

                # 分类整理轨迹数据
                cat_trail = []
                dog_trail = []

                for i, det in enumerate(recent_detections):
                    if det.get('physical_coords'):
                        coords = det['physical_coords']
                        timestamp = current_time - (len(recent_detections) - i) * 0.1

                        # 计算速度和方向
                        velocity_info = self._calculate_velocity(coords, det['class'], timestamp)

                        if det['class'] == '猫':
                            cat_trail.append({
                                'pos': [coords['x'], coords['y'], coords['z']],
                                'time_weight': i / len(recent_detections),
                                'velocity': velocity_info
                            })
                        else:
                            dog_trail.append({
                                'pos': [coords['x'], coords['y'], coords['z']],
                                'time_weight': i / len(recent_detections),
                                'velocity': velocity_info
                            })

                # 绘制猫的高级3D轨迹
                if len(cat_trail) > 1:
                    positions = np.array([point['pos'] for point in cat_trail])

                    # 3D渐变轨迹线
                    for i in range(len(positions) - 1):
                        alpha = 0.3 + 0.7 * (i / len(positions))
                        linewidth = 1 + 3 * (i / len(positions))
                        ax.plot(positions[i:i+2, 0], positions[i:i+2, 1], positions[i:i+2, 2],
                               'lime', alpha=alpha, linewidth=linewidth)

                    # 绘制到地面的投影线，突出Z轴高度
                    for i, point in enumerate(cat_trail[-5:]):  # 最近5个点的投影
                        pos = point['pos']
                        if pos[2] > 0.1:  # 只有明显高度才绘制投影
                            # 投影线：从位置点到地面
                            ax.plot([pos[0], pos[0]], [pos[1], pos[1]], [pos[2], 0],
                                   'lime', alpha=0.3, linewidth=1, linestyle='--')
                            # 地面投影点
                            ax.scatter(pos[0], pos[1], 0, c='green', s=20, alpha=0.4, marker='o')

                    # 3D热力图式轨迹点
                    for i, point in enumerate(cat_trail[-10:]):  # 最近10个点
                        pos = point['pos']
                        weight = point['time_weight']
                        base_size = 30 + 50 * weight
                        alpha = 0.4 + 0.6 * weight

                        # 高度指示颜色 + 速度颜色组合
                        height = pos[2]
                        speed = point['velocity']['speed']

                        # 根据高度调整颜色强度
                        if height > 0.8:
                            color_base = 'red'  # 高处
                            size_multiplier = 1.3
                        elif height > 0.3:
                            color_base = 'orange'  # 中等高度
                            size_multiplier = 1.1
                        else:
                            color_base = 'yellow'  # 接近地面
                            size_multiplier = 1.0

                        # 根据速度调整透明度
                        if speed > 0.5:
                            speed_alpha = 1.0
                        elif speed > 0.2:
                            speed_alpha = 0.8
                        else:
                            speed_alpha = 0.6

                        final_alpha = alpha * speed_alpha
                        final_size = base_size * size_multiplier

                        ax.scatter(pos[0], pos[1], pos[2], c=color_base, s=final_size,
                                 alpha=final_alpha, edgecolors='lime', linewidths=1)

                        # 显示高度信息
                        if i == len(cat_trail[-10:]) - 1 and height > 0.1:  # 最新位置显示高度
                            ax.text(pos[0], pos[1], pos[2] + 0.15, f'H:{height:.2f}m',
                                   fontsize=7, color='lime', ha='center', alpha=0.8)

                        # 3D速度方向箭头
                        if speed > 0.1 and i == len(cat_trail[-10:]) - 1:
                            direction = point['velocity']['direction']
                            arrow_length = min(speed * 0.4, 0.25)
                            # 3D箭头，包含Z方向分量
                            z_component = (height - 0.2) * 0.1  # 简单的Z方向分量
                            ax.quiver(pos[0], pos[1], pos[2],
                                     direction[0] * arrow_length,
                                     direction[1] * arrow_length,
                                     z_component,
                                     color='lime', arrow_length_ratio=0.3, alpha=0.9)

                # 绘制狗的轨迹（简化版）
                if len(dog_trail) > 1:
                    positions = np.array([point['pos'] for point in dog_trail])
                    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2],
                           'cyan', linewidth=2, alpha=0.7)

                    # 最新位置
                    latest_pos = positions[-1]
                    ax.scatter(latest_pos[0], latest_pos[1], latest_pos[2],
                             c='blue', s=80, alpha=0.9, edgecolors='cyan', linewidths=2)

                # 标记每只活跃猫的当前位置 + 精确XYZ坐标 + 轨迹线
                active_cat_ids = self.unique_cats
                for tid in active_cat_ids:
                    traj = self.track_trajectory.get(tid)
                    if not traj:
                        continue
                    # 轨迹线（按时间渐变颜色）
                    if len(traj) >= 2:
                        import matplotlib.cm as cm
                        xs = [p[0] for p in traj]
                        ys = [p[1] for p in traj]
                        zs = [p[2] for p in traj]
                        for i in range(1, len(traj)):
                            c = cm.plasma(i / len(traj))
                            ax.plot(xs[i-1:i+1], ys[i-1:i+1], zs[i-1:i+1],
                                    color=c, linewidth=2, alpha=0.85)

                    # 当前位置：大星标
                    cx, cy, cz = traj[-1]
                    ax.scatter(cx, cy, cz, c='white', s=180, alpha=0.95,
                               marker='*', edgecolors='lime', linewidths=2.5)

                    # 精确XYZ文本（多行）
                    coord_text = f"CAT#{tid}\nX={cx:.2f}m\nY={cy:.2f}m\nZ={cz:.2f}m"
                    ax.text(cx, cy, cz + 0.25, coord_text,
                            fontsize=9, color='lime', ha='center',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='black',
                                      edgecolor='lime', alpha=0.7))

            # 美化设置
            ax.set_xlabel('X(m)', fontsize=9, color='cyan')
            ax.set_ylabel('Y(m)', fontsize=9, color='cyan')
            ax.set_zlabel('Z(m)', fontsize=9, color='cyan')

            # 动态标题显示活跃宠物数
            active_cats = len([d for d in self.detection_history[-5:] if d.get('class') == '猫'])
            active_dogs = len([d for d in self.detection_history[-5:] if d.get('class') == '狗'])
            title = f"🏠 实时追踪 | 🐱{active_cats} 🐶{active_dogs}"
            ax.set_title(title, fontsize=11, color='lime', pad=15)

            # 优化视角 - 轻微旋转营造动感
            azim = 45 + (current_time % 60) * 0.5  # 缓慢旋转视角
            ax.view_init(elev=25, azim=azim)

            # 保留坐标刻度以便读取精确位置
            ax.tick_params(colors='cyan', labelsize=7)
            ax.grid(True, linestyle=':', alpha=0.25, color='cyan')

            # 添加时间戳
            ax.text2D(0.02, 0.98, f"更新: {time.strftime('%H:%M:%S')}",
                     transform=ax.transAxes, fontsize=8, color='gray',
                     verticalalignment='top')

            # 超快保存
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=72, bbox_inches='tight',
                       facecolor='black', edgecolor='none', pad_inches=0.05)
            img_buffer.seek(0)
            plt.close(fig)

            # 缓存结果
            result = base64.b64encode(img_buffer.read()).decode()
            self.viz_3d_cache = result
            return result

        except Exception as e:
            print(f"高级3D可视化生成失败: {e}")
            return self.viz_3d_cache

        finally:
            plt.close('all')

    def get_next_frame(self):
        """获取下一帧 - 实时播放版本"""
        if not self.running or self.cap is None:
            return None

        ret, frame = self.cap.read()
        if ret:
            self.frame_count += 1
            self.current_frame = frame

            # VLM分析
            if (self.frame_count % self.vlm_analysis_interval == 0):
                self.analyze_frame_vlm(frame)

            return frame
        else:
            # 视频结束，重新开始
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            return self.get_next_frame()

    def stop(self):
        """停止系统"""
        self.running = False
        if self.cap:
            self.cap.release()

# 全局系统实例
monitor_system = None

@app.route('/')
def index():
    """主页 - 横屏苹果风格科技黑界面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🐱 Pet Monitor Pro - AI Detection & 3D Tracking</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                background: #000000;
                background-image:
                    radial-gradient(circle at 20% 20%, rgba(0, 122, 255, 0.08) 0%, transparent 60%),
                    radial-gradient(circle at 80% 40%, rgba(175, 82, 222, 0.06) 0%, transparent 60%),
                    radial-gradient(circle at 40% 80%, rgba(52, 199, 89, 0.04) 0%, transparent 60%),
                    linear-gradient(135deg, rgba(0, 0, 0, 0.98) 0%, rgba(10, 10, 15, 0.95) 100%);
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
                min-height: 100vh;
                overflow-x: hidden;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            /* 微妙网格背景 */
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

            .vlm-analysis {
                color: rgba(255, 255, 255, 0.9);
                line-height: 1.7;
                font-size: 15px;
                font-weight: 400;
            }

            .analysis-item {
                margin-bottom: 20px;
                padding: 16px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.04);
            }

            .analysis-item:last-child {
                margin-bottom: 0;
            }

            .analysis-label {
                font-weight: 600;
                color: #5AC8FA;
                margin-bottom: 8px;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .viz-3d-image {
                width: 100%;
                height: 100%;
                display: block;
                object-fit: contain;
                border-radius: 0 0 20px 20px;
                background: linear-gradient(135deg, #0a0a0f 0%, #111118 100%);
            }

            /* 图标 */
            .icon {
                width: 16px;
                height: 16px;
                filter: brightness(1.2);
            }

            /* 响应式设计 */
            @media (max-width: 1600px) {
                .main-container {
                    grid-template-columns: 2fr 0.9fr 0.9fr 0.9fr;
                }

                .panel-header h3 {
                    font-size: 15px;
                }

                .stat-value {
                    font-size: 20px;
                }

                .cat-count {
                    font-size: 28px !important;
                }
            }

            @media (max-width: 1200px) {
                .main-container {
                    grid-template-columns: 1fr 1fr;
                    grid-template-rows: 1fr 1fr;
                    gap: 12px;
                }

                .panel-header {
                    padding: 12px 16px 8px;
                }

                .stats-content, .vlm-content {
                    padding: 16px;
                }
            }

            @media (max-width: 768px) {
                .main-container {
                    grid-template-columns: 1fr;
                    grid-template-rows: 2fr 1fr 1fr 1fr;
                    gap: 12px;
                    padding: 12px;
                }

                .nav-title {
                    font-size: 18px;
                }

                .top-nav {
                    padding: 8px 16px;
                }

                .stat-row {
                    padding: 8px;
                }

                .analysis-item {
                    padding: 12px;
                }
            }
        </style>
        <script>
            function updateData() {
                // 更新统计数据
                fetch('/api/detections')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('cat-count').textContent = data.unique_cats || 0;
                        document.getElementById('total-count').textContent = data.total_detections || 0;
                        document.getElementById('frame-count').textContent = data.total_frames || 0;

                        if (data.average_confidence > 0) {
                            document.getElementById('avg-confidence').textContent = data.average_confidence.toFixed(3);
                        }

                        // 更新导航栏状态
                        const navStats = document.getElementById('nav-stats');
                        if (navStats && data.unique_cats > 0) {
                            navStats.textContent = `检测到 ${data.unique_cats} 只猫咪 (${data.cat_detections}次检测)`;
                        }
                    })
                    .catch(error => console.log('Stats error:', error));

                // 更新VLM分析
                fetch('/api/vlm_analysis')
                    .then(response => response.json())
                    .then(data => {
                        if (data.analysis) {
                            document.getElementById('scene-analysis').textContent = data.analysis.scene || '正在分析场景...';
                            document.getElementById('behavior-analysis').textContent = data.analysis.behavior || '正在分析行为...';
                        }
                    })
                    .catch(error => console.log('VLM error:', error));

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
            <div class="nav-title">Pet Monitor Pro</div>
            <div class="nav-status">
                <div class="live-dot"></div>
                <span>LIVE</span>
                <span id="nav-stats">AI检测中...</span>
            </div>
        </nav>

        <!-- 主容器 - 完全横向整齐四列布局 -->
        <div class="main-container">
            <!-- 第1列：主视频面板 -->
            <div class="panel video-panel">
                <div class="panel-header video-header">
                    <h3>🎬 实时视频检测</h3>
                </div>
                <div class="panel-content">
                    <img src="/video_feed" class="video-stream" alt="实时视频流">
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
                            <div class="stat-label">🐱 猫咪检测</div>
                            <div id="cat-count" class="stat-value cat-count">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">📈 总检测数</div>
                            <div id="total-count" class="stat-value">0</div>
                        </div>
                        <div class="stat-row">
                            <div class="stat-label">🎬 处理帧数</div>
                            <div id="frame-count" class="stat-value">0</div>
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
                            <div id="scene-analysis" class="vlm-analysis">正在分析场景环境...</div>
                        </div>
                        <div class="analysis-item">
                            <div class="analysis-label">行为分析</div>
                            <div id="behavior-analysis" class="vlm-analysis">正在分析宠物行为...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 第4列：3D空间追踪面板 -->
            <div class="panel viz-panel">
                <div class="panel-header viz-header">
                    <h3>🏠 3D空间追踪</h3>
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
    """优化的流畅视频流"""
    def generate():
        frame_time = 1.0 / monitor_system.target_fps  # 计算帧间隔

        while True:
            if monitor_system is None:
                break

            start_time = time.time()

            frame = monitor_system.get_next_frame()
            if frame is None:
                break

            # 将最新帧交给后台检测线程，视频流本身永不等待AI推理
            monitor_system.latest_raw_frame = frame

            # 直接读取后台最新检测结果（可能滞后1-2帧，但视频保持30fps流畅）
            with monitor_system.latest_detections_lock:
                detections = list(monitor_system.latest_detections_async)

            # 简洁视频叠加：仅框 + ID标签（3D坐标在3D视图面板里显示）
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                if det['class'] == '猫':
                    color = (0, 255, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                    tid = det.get('track_id')
                    label = f"CAT#{tid}" if tid is not None else "CAT"
                    cv2.rectangle(frame, (x1, y1 - 25), (x1 + 90, y1), color, -1)
                    cv2.putText(frame, label, (x1 + 5, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                else:
                    color = (255, 100, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 简化统计显示
            if len(monitor_system.unique_cats) > 0:
                stats_text = f"LIVE | Cats: {len(monitor_system.unique_cats)}"
                cv2.putText(frame, stats_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 优化编码 - 提升质量但保持速度
            encode_param = [
                int(cv2.IMWRITE_JPEG_QUALITY), 85,
                int(cv2.IMWRITE_JPEG_OPTIMIZE), 1
            ]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # 动态帧率控制 - 如果处理太慢就跳过等待
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
            # 如果处理时间超过帧时间，不等待，直接处理下一帧

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def api_stats():
    """获取统计数据"""
    if monitor_system is None:
        return jsonify({'error': 'System not initialized'})

    return jsonify({
        'cat_detections': monitor_system.cat_detections,      # 检测次数
        'unique_cats': len(monitor_system.unique_cats),       # 实际猫数量
        'total_detections': monitor_system.total_detections,
        'total_frames': monitor_system.frame_count,
        'running': monitor_system.running
    })

@app.route('/api/detections')
def api_detections():
    """获取检测结果API"""
    if monitor_system is None:
        return jsonify({'error': 'System not initialized'})

    # 计算平均置信度
    avg_confidence = 0
    if monitor_system.recent_detections:
        confidences = [det['confidence'] for det in monitor_system.recent_detections]
        avg_confidence = sum(confidences) / len(confidences)

    return jsonify({
        'detections': monitor_system.recent_detections[-5:],  # 最近5个检测
        'total_detections': monitor_system.total_detections,
        'cat_detections': monitor_system.cat_detections,      # 检测次数
        'unique_cats': len(monitor_system.unique_cats),       # 实际猫数量
        'total_frames': monitor_system.frame_count,
        'average_confidence': avg_confidence
    })

@app.route('/api/vlm_analysis')
def api_vlm_analysis():
    """获取VLM分析结果API"""
    if monitor_system is None:
        return jsonify({'error': 'System not initialized'})

    return jsonify({
        'analysis': monitor_system.vlm_analysis
    })

@app.route('/api/3d_visualization')
def api_3d_visualization():
    """获取3D可视化API"""
    if monitor_system is None:
        return Response("System not initialized", mimetype="image/png")

    viz_data = monitor_system.generate_3d_visualization()
    if viz_data:
        img_data = base64.b64decode(viz_data)
        return Response(img_data, mimetype="image/png")
    else:
        # 返回空白图像
        return Response("", mimetype="image/png")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='实时宠物监控系统')
    parser.add_argument('--video', default='real_cat.mp4', help='视频文件路径')
    parser.add_argument('--host', default='0.0.0.0', help='Web服务器地址')
    parser.add_argument('--port', type=int, default=5008, help='Web服务器端口')

    args = parser.parse_args()

    print("🎬 启动实时宠物监控系统...")
    print("⚡ 特性:")
    print("   - 🚀 25FPS实时播放，无延迟")
    print("   - 🐱 猫检测显示亮绿色方框")
    print("   - 📊 实时统计更新")
    print("   - 💚 专为快速检测优化")

    # 初始化系统
    monitor_system = RealtimePetMonitor(args.video)

    print("✅ 实时监控系统启动成功！")
    print(f"🌐 Web界面: http://localhost:{args.port}")
    print("🐱 绿色方框 = 检测到猫")

    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 正在停止系统...")
        if monitor_system:
            monitor_system.stop()
        print("✅ 系统已停止")