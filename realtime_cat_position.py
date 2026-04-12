#!/usr/bin/env python3
"""
实时猫咪位置识别和显示系统
专门用于实时检测、追踪和显示猫咪位置坐标
"""

import cv2
import numpy as np
import time
import json
from ultralytics import YOLO
from flask import Flask, render_template_string, Response, jsonify
import threading
import queue

app = Flask(__name__)

class RealtimeCatTracker:
    """实时猫咪位置追踪器"""

    def __init__(self):
        self.model = None
        self.cap = None
        self.current_frame = None
        self.cat_positions = []
        self.detection_active = True
        self.detection_threshold = 0.05  # 极低阈值确保检测到猫咪

        # 位置历史记录
        self.position_history = []
        self.max_history = 50

        # 统计信息
        self.stats = {
            'total_detections': 0,
            'current_cats': 0,
            'last_detection_time': 0,
            'detection_confidence': 0,
            'cat_positions': []
        }

        self.load_model()

    def load_model(self):
        """加载YOLOv8模型"""
        try:
            print("🐱 加载猫咪位置识别模型...")
            self.model = YOLO('yolov8n.pt')
            print("✅ 模型加载成功")
            return True
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False

    def start_video(self, video_path):
        """启动视频捕获"""
        try:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                print(f"❌ 无法打开视频: {video_path}")
                return False

            fps = self.cap.get(cv2.CAP_PROP_FPS)
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            print(f"📹 视频已连接: {width}x{height}@{fps}fps")
            return True

        except Exception as e:
            print(f"❌ 视频连接失败: {e}")
            return False

    def detect_cat_positions(self, frame):
        """检测猫咪位置"""
        if not self.model:
            return []

        try:
            # YOLOv8检测
            results = self.model(frame, verbose=False)
            cat_detections = []

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])

                        # 只检测猫咪 (类别15) 且置信度大于阈值
                        if class_id == 15 and confidence > self.detection_threshold:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                            # 计算中心点位置
                            center_x = int((x1 + x2) / 2)
                            center_y = int((y1 + y2) / 2)
                            width = int(x2 - x1)
                            height = int(y2 - y1)

                            cat_info = {
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'center': (center_x, center_y),
                                'size': (width, height),
                                'confidence': confidence,
                                'timestamp': time.time()
                            }

                            cat_detections.append(cat_info)

                            # 更新统计
                            self.stats['total_detections'] += 1
                            self.stats['last_detection_time'] = time.time()
                            self.stats['detection_confidence'] = confidence

            # 更新当前猫咪数量和位置
            self.stats['current_cats'] = len(cat_detections)
            self.stats['cat_positions'] = [cat['center'] for cat in cat_detections]

            # 记录位置历史
            if cat_detections:
                self.position_history.extend([cat['center'] for cat in cat_detections])
                if len(self.position_history) > self.max_history:
                    self.position_history = self.position_history[-self.max_history:]

            return cat_detections

        except Exception as e:
            print(f"⚠️ 检测失败: {e}")
            return []

    def draw_cat_positions(self, frame, cat_detections):
        """在帧上绘制猫咪位置信息"""
        # 绘制检测框和位置信息
        for i, cat in enumerate(cat_detections):
            x1, y1, x2, y2 = cat['bbox']
            center_x, center_y = cat['center']
            width, height = cat['size']
            confidence = cat['confidence']

            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # 绘制中心点
            cv2.circle(frame, (center_x, center_y), 8, (0, 255, 0), -1)

            # 绘制十字线标记精确位置
            cv2.line(frame, (center_x-15, center_y), (center_x+15, center_y), (0, 255, 0), 2)
            cv2.line(frame, (center_x, center_y-15), (center_x, center_y+15), (0, 255, 0), 2)

            # 显示位置坐标和置信度
            position_text = f"Cat #{i+1}: ({center_x}, {center_y})"
            confidence_text = f"Confidence: {confidence:.3f}"
            size_text = f"Size: {width}x{height}"

            # 背景框
            cv2.rectangle(frame, (x1, y1-80), (x1+300, y1-5), (0, 0, 0), -1)

            # 文本信息
            cv2.putText(frame, position_text, (x1+5, y1-60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, confidence_text, (x1+5, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, size_text, (x1+5, y1-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 绘制历史轨迹
        if len(self.position_history) > 1:
            points = np.array(self.position_history, dtype=np.int32)
            cv2.polylines(frame, [points], False, (255, 255, 0), 2)

            # 标记轨迹点
            for point in self.position_history[-10:]:  # 只显示最近10个点
                cv2.circle(frame, point, 3, (255, 255, 0), -1)

        # 显示实时统计
        stats_text = [
            f"Real-time Cat Position Tracking",
            f"Current Cats: {self.stats['current_cats']}",
            f"Total Detections: {self.stats['total_detections']}",
            f"Threshold: {self.detection_threshold}",
            f"History Points: {len(self.position_history)}"
        ]

        # 统计信息背景
        cv2.rectangle(frame, (10, 10), (400, 150), (0, 0, 0), -1)

        for i, text in enumerate(stats_text):
            cv2.putText(frame, text, (20, 30 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        return frame

    def get_current_frame(self):
        """获取当前处理的帧"""
        if self.cap is None:
            return None

        ret, frame = self.cap.read()
        if not ret:
            # 视频结束，重新开始
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret and self.detection_active:
            # 检测猫咪位置
            cat_detections = self.detect_cat_positions(frame)

            # 绘制位置信息
            frame = self.draw_cat_positions(frame, cat_detections)

            self.current_frame = frame

        return frame

# 全局追踪器实例
tracker = RealtimeCatTracker()

def generate_frames():
    """生成视频流"""
    while True:
        frame = tracker.get_current_frame()
        if frame is not None:
            # 编码为JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.033)  # ~30fps

@app.route('/')
def index():
    """主页面"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>🐱 实时猫咪位置识别</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
            margin: 0;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .video-section {
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }
        .video-container {
            flex: 1;
            background: #2a2a2a;
            border-radius: 10px;
            padding: 20px;
        }
        .info-panel {
            width: 350px;
            background: #2a2a2a;
            border-radius: 10px;
            padding: 20px;
        }
        video, img {
            width: 100%;
            border-radius: 8px;
            border: 2px solid #ff6b9d;
        }
        .stats {
            background: #333;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .position-list {
            background: #333;
            border-radius: 8px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
        }
        .cat-item {
            background: #444;
            margin: 8px 0;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #ff6b9d;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            justify-content: center;
        }
        button {
            background: #ff6b9d;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover { background: #ff4d7a; }
        .threshold { margin: 10px 0; }
        input[type="range"] { width: 100%; }
        .status {
            text-align: center;
            font-size: 18px;
            margin: 10px 0;
        }
        .live-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff00;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐱 实时猫咪位置识别系统</h1>
            <div class="status">
                <span class="live-dot"></span>
                实时检测中 - cat.mp4
            </div>
        </div>

        <div class="video-section">
            <div class="video-container">
                <h3>📹 实时视频流 + 位置标记</h3>
                <img src="/video_feed" alt="实时猫咪检测">
            </div>

            <div class="info-panel">
                <div class="stats" id="stats">
                    <h3>📊 检测统计</h3>
                    <div>当前猫咪数: <span id="current_cats">0</span></div>
                    <div>总检测次数: <span id="total_detections">0</span></div>
                    <div>检测阈值: <span id="threshold">0.05</span></div>
                    <div>历史轨迹点: <span id="history_points">0</span></div>
                    <div>最后检测: <span id="last_detection">无</span></div>
                </div>

                <div class="threshold">
                    <h4>🎛️ 检测阈值调节</h4>
                    <input type="range" id="threshold_slider" min="0.01" max="0.9" step="0.01" value="0.05">
                    <div>当前值: <span id="threshold_value">0.05</span></div>
                </div>

                <div class="controls">
                    <button onclick="clearHistory()">清除轨迹</button>
                    <button onclick="resetStats()">重置统计</button>
                </div>

                <div class="position-list">
                    <h3>📍 猫咪位置列表</h3>
                    <div id="cat_positions">
                        <div style="text-align: center; color: #888;">等待检测猫咪...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 实时更新统计信息
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('current_cats').textContent = data.current_cats;
                    document.getElementById('total_detections').textContent = data.total_detections;
                    document.getElementById('history_points').textContent = data.position_history_length;

                    if (data.last_detection_time > 0) {
                        const timeDiff = Date.now()/1000 - data.last_detection_time;
                        document.getElementById('last_detection').textContent = timeDiff < 60 ?
                            Math.round(timeDiff) + '秒前' : '超过1分钟';
                    }

                    // 更新猫咪位置列表
                    const positionsDiv = document.getElementById('cat_positions');
                    if (data.cat_positions && data.cat_positions.length > 0) {
                        positionsDiv.innerHTML = '';
                        data.cat_positions.forEach((pos, index) => {
                            const catDiv = document.createElement('div');
                            catDiv.className = 'cat-item';
                            catDiv.innerHTML = `
                                <strong>猫咪 #${index + 1}</strong><br>
                                位置: (${pos[0]}, ${pos[1]})<br>
                                置信度: ${data.detection_confidence.toFixed(3)}
                            `;
                            positionsDiv.appendChild(catDiv);
                        });
                    } else {
                        positionsDiv.innerHTML = '<div style="text-align: center; color: #888;">未检测到猫咪</div>';
                    }
                });
        }

        // 阈值调节
        document.getElementById('threshold_slider').addEventListener('input', function() {
            const value = parseFloat(this.value);
            document.getElementById('threshold_value').textContent = value;
            document.getElementById('threshold').textContent = value;

            // 发送到服务器
            fetch('/api/set_threshold', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({threshold: value})
            });
        });

        function clearHistory() {
            fetch('/api/clear_history', {method: 'POST'});
        }

        function resetStats() {
            fetch('/api/reset_stats', {method: 'POST'});
        }

        // 每秒更新统计
        setInterval(updateStats, 1000);
        updateStats();
    </script>
</body>
</html>
    ''')

@app.route('/video_feed')
def video_feed():
    """视频流端点"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def api_stats():
    """获取统计信息"""
    stats = tracker.stats.copy()
    stats['position_history_length'] = len(tracker.position_history)
    return jsonify(stats)

@app.route('/api/set_threshold', methods=['POST'])
def set_threshold():
    """设置检测阈值"""
    data = request.get_json()
    threshold = data.get('threshold', 0.05)
    tracker.detection_threshold = max(0.01, min(0.9, threshold))
    return jsonify({'success': True, 'threshold': tracker.detection_threshold})

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    """清除位置历史"""
    tracker.position_history = []
    return jsonify({'success': True})

@app.route('/api/reset_stats', methods=['POST'])
def reset_stats():
    """重置统计信息"""
    tracker.stats = {
        'total_detections': 0,
        'current_cats': 0,
        'last_detection_time': 0,
        'detection_confidence': 0,
        'cat_positions': []
    }
    return jsonify({'success': True})

def main():
    print("🐱 启动实时猫咪位置识别系统")

    # 连接视频
    if not tracker.start_video('cat.mp4'):
        print("❌ 视频连接失败")
        return

    print("🌐 Web界面: http://localhost:5002")
    print("🎯 功能: 实时检测猫咪位置坐标")
    print("📍 显示: 边界框 + 中心点 + 轨迹 + 坐标")

    # 启动Web服务器
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)

if __name__ == "__main__":
    main()