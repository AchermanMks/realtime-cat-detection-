#!/usr/bin/env python3
"""
完整3D监控系统整合
结合实时监控 + 3D建模 + VLM分析 + 空间定位
"""

import cv2
import torch
import numpy as np
import json
import time
import threading
import queue
import base64
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, Response, jsonify, request
from ultralytics import YOLO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 导入之前的模块
try:
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    from qwen_vl_utils import process_vision_info
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False

app = Flask(__name__)

class Integrated3DMonitoringSystem:
    """完整3D监控系统整合器"""

    def __init__(self, camera_url=None, use_3d_model=True, use_vlm_analysis=True):
        """
        初始化整合系统

        Args:
            camera_url: 摄像头URL或索引
            use_3d_model: 是否启用3D建模
            use_vlm_analysis: 是否启用VLM分析
        """
        print("🚀 初始化完整3D监控系统...")

        # 基础配置
        self.camera_url = camera_url if camera_url is not None else 0
        self.use_3d_model = use_3d_model
        self.use_vlm_analysis = use_vlm_analysis
        self.running = False

        # 视频采集
        self.cap = None
        self.current_frame = None
        self.frame_queue = queue.Queue(maxsize=5)

        # 检测组件
        self.yolo_model = None
        self.vlm_model = None
        self.vlm_processor = None

        # 3D空间定位组件
        self.homography_matrix = None
        self.room_bounds = None
        self.coordinate_transformer = None

        # 3D房间模型
        self.room_model_data = None
        self.room_objects = []

        # 检测结果
        self.current_detections = []
        self.detection_history = []
        self.vlm_analysis_queue = queue.Queue(maxsize=3)
        self.latest_vlm_analysis = {"text": "等待分析...", "timestamp": time.time()}

        # 统计信息
        self.stats = {
            "total_detections": 0,
            "3d_localizations": 0,
            "vlm_analyses": 0,
            "system_uptime": time.time()
        }

        self._initialize_components()

    def _initialize_components(self):
        """初始化各个组件"""
        print("🔧 初始化系统组件...")

        # 1. 加载YOLO检测模型
        self._load_yolo_model()

        # 2. 加载VLM模型（如果启用）
        if self.use_vlm_analysis and VLM_AVAILABLE:
            self._load_vlm_model()

        # 3. 加载3D空间定位数据（如果启用）
        if self.use_3d_model:
            self._load_3d_components()

        # 4. 连接摄像头
        self._connect_camera()

    def _load_yolo_model(self):
        """加载YOLO检测模型"""
        try:
            print("📥 加载YOLO检测模型...")
            self.yolo_model = YOLO("yolov8n.pt")
            print("✅ YOLO模型加载成功")
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")
            self.yolo_model = None

    def _load_vlm_model(self):
        """加载VLM模型"""
        try:
            print("📥 加载VLM模型...")
            self.vlm_model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype="auto",
                device_map="auto",
            )
            self.vlm_processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
            print("✅ VLM模型加载成功")
        except Exception as e:
            print(f"❌ VLM模型加载失败: {e}")
            self.vlm_model = None
            self.vlm_processor = None

    def _load_3d_components(self):
        """加载3D空间定位组件"""
        try:
            print("📥 加载3D空间定位组件...")

            # 加载Homography标定数据
            calibration_files = list(Path(".").glob("meeting_room_calibration_*.json"))
            if calibration_files:
                latest_calibration = max(calibration_files, key=lambda p: p.stat().st_mtime)
                with open(latest_calibration, 'r', encoding='utf-8') as f:
                    calibration_data = json.load(f)

                self.homography_matrix = np.array(calibration_data['homography_matrix'], dtype=np.float32)
                print(f"✅ 坐标变换矩阵加载成功: {latest_calibration.name}")

            # 加载房间模型数据
            room_files = list(Path(".").glob("step3_output_*/room_data.json"))
            if room_files:
                latest_room = max(room_files, key=lambda p: p.stat().st_mtime)
                with open(latest_room, 'r', encoding='utf-8') as f:
                    self.room_model_data = json.load(f)
                    self.room_bounds = self.room_model_data['room_bounds']

                print(f"✅ 房间模型数据加载成功: {latest_room}")

            # 设置坐标系转换器
            if self.homography_matrix is not None:
                self.coordinate_transformer = CoordinateTransformer(self.homography_matrix)

        except Exception as e:
            print(f"❌ 3D组件加载失败: {e}")

    def _connect_camera(self):
        """连接摄像头"""
        try:
            print(f"📹 连接摄像头: {self.camera_url}")
            self.cap = cv2.VideoCapture(self.camera_url)
            if not self.cap.isOpened():
                raise ValueError("无法打开摄像头")

            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            print("✅ 摄像头连接成功")
        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            self.cap = None

    def start_system(self):
        """启动整个系统"""
        if self.cap is None:
            print("❌ 摄像头未连接，无法启动系统")
            return False

        print("🚀 启动完整3D监控系统...")
        self.running = True

        # 启动各个工作线程
        threading.Thread(target=self._frame_capture_worker, daemon=True).start()
        threading.Thread(target=self._detection_worker, daemon=True).start()

        if self.use_vlm_analysis and self.vlm_model is not None:
            threading.Thread(target=self._vlm_analysis_worker, daemon=True).start()

        print("✅ 系统启动成功")
        return True

    def _frame_capture_worker(self):
        """帧采集工作线程"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy()

                    # 添加到检测队列
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame.copy())

                time.sleep(1/30)  # 30 FPS
            except Exception as e:
                print(f"⚠️ 帧采集异常: {e}")
                time.sleep(1)

    def _detection_worker(self):
        """检测工作线程"""
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    detections = self._detect_pets_in_frame(frame)

                    if detections:
                        # 添加3D定位信息
                        detections_3d = self._add_3d_localization(detections)

                        self.current_detections = detections_3d
                        self.detection_history.extend(detections_3d)
                        self.stats["total_detections"] += len(detections_3d)

                        # 添加到VLM分析队列
                        if (self.use_vlm_analysis and
                            self.vlm_model is not None and
                            not self.vlm_analysis_queue.full()):
                            self.vlm_analysis_queue.put(frame.copy())

                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ 检测异常: {e}")
                time.sleep(1)

    def _detect_pets_in_frame(self, frame):
        """在帧中检测宠物"""
        if self.yolo_model is None:
            return []

        try:
            results = self.yolo_model(frame, verbose=False)
            detections = []

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        confidence = float(box.conf[0])

                        # 只保留宠物类别
                        if cls_id in [15, 16] and confidence > 0.3:  # 15=cat, 16=dog
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            center_x = int((x1 + x2) / 2)
                            center_y = int((y1 + y2) / 2)

                            detection = {
                                'class_id': cls_id,
                                'class_name': 'cat' if cls_id == 15 else 'dog',
                                'confidence': confidence,
                                'bbox': {'x1': int(x1), 'y1': int(y1), 'x2': int(x2), 'y2': int(y2)},
                                'center': {'x': center_x, 'y': center_y},
                                'timestamp': time.time(),
                                'frame_id': int(time.time() * 30)  # 假设30fps
                            }
                            detections.append(detection)

            return detections

        except Exception as e:
            print(f"⚠️ 宠物检测失败: {e}")
            return []

    def _add_3d_localization(self, detections):
        """为检测结果添加3D定位信息"""
        if not self.use_3d_model or self.coordinate_transformer is None:
            return detections

        enhanced_detections = []

        for detection in detections:
            enhanced_detection = detection.copy()

            # 转换像素坐标为物理坐标
            pixel_x = detection['center']['x']
            pixel_y = detection['center']['y']

            real_coords = self.coordinate_transformer.pixel_to_real(pixel_x, pixel_y)

            if real_coords[0] is not None:
                enhanced_detection['3d_position'] = {
                    'calibrated_coords': {
                        'x': real_coords[0],
                        'y': real_coords[1],
                        'z': 0.0
                    },
                    'room_position': self._get_room_position_description(real_coords[0], real_coords[1])
                }
                enhanced_detection['3d_valid'] = True
                self.stats["3d_localizations"] += 1
            else:
                enhanced_detection['3d_position'] = None
                enhanced_detection['3d_valid'] = False

            enhanced_detections.append(enhanced_detection)

        return enhanced_detections

    def _vlm_analysis_worker(self):
        """VLM分析工作线程"""
        while self.running:
            try:
                if not self.vlm_analysis_queue.empty():
                    frame = self.vlm_analysis_queue.get()
                    analysis_result = self._analyze_frame_with_vlm(frame)

                    if analysis_result:
                        self.latest_vlm_analysis = {
                            "text": analysis_result,
                            "timestamp": time.time()
                        }
                        self.stats["vlm_analyses"] += 1

                time.sleep(5)  # VLM分析间隔
            except Exception as e:
                print(f"⚠️ VLM分析异常: {e}")
                time.sleep(10)

    def _analyze_frame_with_vlm(self, frame):
        """使用VLM分析帧"""
        if self.vlm_model is None or self.vlm_processor is None:
            return None

        try:
            # 转换帧为PIL图像
            from PIL import Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # VLM分析提示词
            prompt = "请详细描述这个画面中的宠物活动。包括宠物类型、位置、行为状态和周围环境。如果有多只宠物，请分别描述。"

            # 构建消息
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": prompt}
                ]
            }]

            # 处理和生成
            text = self.vlm_processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.vlm_processor(
                text=[text], images=image_inputs, videos=video_inputs,
                padding=True, return_tensors="pt"
            )

            inputs = inputs.to(self.vlm_model.device)
            generated_ids = self.vlm_model.generate(**inputs, max_new_tokens=256)

            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]

            output_text = self.vlm_processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )

            return output_text[0] if output_text else None

        except Exception as e:
            print(f"⚠️ VLM分析失败: {e}")
            return None

    def _get_room_position_description(self, x: float, y: float) -> str:
        """获取房间位置描述"""
        # 基于标定坐标系的位置描述
        if x < 1.5:
            x_desc = "左侧"
        elif x > 2.5:
            x_desc = "右侧"
        else:
            x_desc = "中央"

        if y < 1.0:
            y_desc = "下方"
        elif y > 2.0:
            y_desc = "上方"
        else:
            y_desc = "中央"

        return f"{x_desc}{y_desc}"

    def generate_3d_visualization(self):
        """生成3D可视化"""
        if not self.current_detections:
            return None

        try:
            fig = plt.figure(figsize=(12, 8))
            ax = fig.add_subplot(111, projection='3d')

            # 绘制房间边界（如果有3D模型数据）
            if self.room_bounds:
                self._plot_room_3d(ax)

            # 绘制当前检测的宠物位置
            for detection in self.current_detections:
                if detection.get('3d_valid', False):
                    pos = detection['3d_position']['calibrated_coords']
                    color = 'green' if detection['class_name'] == 'cat' else 'blue'

                    ax.scatter([pos['x']], [pos['y']], [pos['z'] + 0.3],
                              s=100, c=color, alpha=0.8)

                    # 添加标签
                    ax.text(pos['x'], pos['y'], pos['z'] + 0.5,
                           f"{detection['class_name']}\n{detection['room_position']}",
                           fontsize=8)

            ax.set_xlabel('X (meters)')
            ax.set_ylabel('Y (meters)')
            ax.set_zlabel('Z (meters)')
            ax.set_title('Real-time 3D Pet Localization')

            # 保存为base64图像
            import io
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            return img_base64

        except Exception as e:
            print(f"⚠️ 3D可视化生成失败: {e}")
            return None

    def _plot_room_3d(self, ax):
        """绘制3D房间"""
        if self.room_bounds:
            # 绘制地板
            x = [0, 4, 4, 0, 0]
            y = [0, 0, 3, 3, 0]
            z = [0, 0, 0, 0, 0]
            ax.plot(x, y, z, 'k-', alpha=0.5)

    def get_system_status(self):
        """获取系统状态"""
        return {
            'running': self.running,
            'current_detections': len(self.current_detections),
            'total_detections': self.stats['total_detections'],
            '3d_localizations': self.stats['3d_localizations'],
            'vlm_analyses': self.stats['vlm_analyses'],
            'uptime_seconds': time.time() - self.stats['system_uptime'],
            'components': {
                'yolo_loaded': self.yolo_model is not None,
                'vlm_loaded': self.vlm_model is not None,
                '3d_model_loaded': self.coordinate_transformer is not None,
                'camera_connected': self.cap is not None
            }
        }

    def stop_system(self):
        """停止系统"""
        print("🛑 停止3D监控系统...")
        self.running = False
        if self.cap:
            self.cap.release()


class CoordinateTransformer:
    """坐标转换器（简化版）"""

    def __init__(self, homography_matrix):
        self.homography_matrix = homography_matrix

    def pixel_to_real(self, pixel_x, pixel_y):
        """像素坐标转换为物理坐标"""
        try:
            pixel_point = np.array([[pixel_x, pixel_y]], dtype=np.float32)
            pixel_point = pixel_point.reshape(-1, 1, 2)
            real_point = cv2.perspectiveTransform(pixel_point, self.homography_matrix)

            real_x = float(real_point[0][0][0])
            real_y = float(real_point[0][0][1])
            return real_x, real_y
        except Exception:
            return None, None


# Flask Web接口
monitoring_system = None

@app.route('/')
def index():
    """主页面"""
    return render_template('integrated_3d_monitoring.html')

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    if monitoring_system:
        return jsonify(monitoring_system.get_system_status())
    return jsonify({'error': 'System not initialized'})

@app.route('/api/detections')
def get_current_detections():
    """获取当前检测结果"""
    if monitoring_system:
        return jsonify({
            'current_detections': monitoring_system.current_detections,
            'latest_vlm_analysis': monitoring_system.latest_vlm_analysis
        })
    return jsonify({'error': 'System not initialized'})

@app.route('/api/3d_visualization')
def get_3d_visualization():
    """获取3D可视化"""
    if monitoring_system:
        img_base64 = monitoring_system.generate_3d_visualization()
        if img_base64:
            return jsonify({'image': img_base64})
        return jsonify({'error': 'No detections available'})
    return jsonify({'error': 'System not initialized'})

@app.route('/video_feed')
def video_feed():
    """视频流"""
    def generate():
        while monitoring_system and monitoring_system.running:
            if monitoring_system.current_frame is not None:
                frame = monitoring_system.current_frame.copy()

                # 绘制检测结果
                for detection in monitoring_system.current_detections:
                    bbox = detection['bbox']
                    center = detection['center']
                    color = (0, 255, 0) if detection['class_name'] == 'cat' else (255, 0, 0)

                    cv2.rectangle(frame, (bbox['x1'], bbox['y1']), (bbox['x2'], bbox['y2']), color, 2)
                    cv2.circle(frame, (center['x'], center['y']), 5, color, -1)

                    # 添加3D位置信息
                    if detection.get('3d_valid', False):
                        pos = detection['3d_position']['calibrated_coords']
                        text = f"{detection['class_name']}: ({pos['x']:.1f}, {pos['y']:.1f})"
                        cv2.putText(frame, text, (bbox['x1'], bbox['y1'] - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            time.sleep(1/30)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


def main():
    """主函数"""
    print("🚀 完整3D监控系统整合")
    print("=" * 50)

    try:
        global monitoring_system

        # 创建整合系统
        monitoring_system = Integrated3DMonitoringSystem(
            camera_url=0,  # 使用默认摄像头，可以改为RTSP URL
            use_3d_model=True,
            use_vlm_analysis=True
        )

        # 启动系统
        if monitoring_system.start_system():
            print("\n✅ 系统启动成功！")
            print("🌐 Web界面: http://localhost:5000")
            print("📊 功能特性:")
            print("   - 实时宠物检测 (YOLO)")
            print("   - 3D空间定位 (Homography)")
            print("   - VLM智能分析 (Qwen)")
            print("   - 实时可视化界面")

            # 启动Flask应用
            app.run(host='0.0.0.0', port=5000, debug=False)
        else:
            print("❌ 系统启动失败")

    except KeyboardInterrupt:
        print("\n🛑 收到停止信号")
        if monitoring_system:
            monitoring_system.stop_system()
    except Exception as e:
        print(f"❌ 系统运行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if monitoring_system:
            monitoring_system.stop_system()

if __name__ == "__main__":
    main()