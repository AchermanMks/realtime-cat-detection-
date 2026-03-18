#!/usr/bin/env python3
"""
视频流测试 - 诊断视频显示问题
"""

import cv2
import time
from flask import Flask, Response

app = Flask(__name__)

# 全局变量
cap = None
current_frame = None

def init_camera():
    global cap
    rtsp_url = "rtsp://admin:admin123@192.168.31.146:8554/unicast"
    print(f"连接RTSP: {rtsp_url}")

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ 连接成功: {frame.shape}")
            return True
    return False

def generate_frames():
    global cap, current_frame

    while True:
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # 缩放帧
                height, width = frame.shape[:2]
                scale = 0.5
                new_width, new_height = int(width * scale), int(height * scale)
                resized_frame = cv2.resize(frame, (new_width, new_height))

                # 添加文字标识
                cv2.putText(resized_frame, f"Time: {time.strftime('%H:%M:%S')}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # 编码为JPEG
                ret, buffer = cv2.imencode('.jpg', resized_frame,
                                         [cv2.IMWRITE_JPEG_QUALITY, 80])

                if ret:
                    frame_data = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                    print(f"发送帧: {len(frame_data)} 字节")
                else:
                    print("❌ JPEG编码失败")
            else:
                print("❌ 读取帧失败")
                time.sleep(0.1)
        else:
            print("❌ 摄像头未连接")
            time.sleep(1)

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>视频流测试</title>
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #fff; text-align: center; padding: 50px; }
        img { max-width: 90%; border: 2px solid #fff; }
        .info { margin: 20px 0; font-size: 18px; }
    </style>
</head>
<body>
    <h1>视频流测试页面</h1>
    <div class="info">如果下方显示视频，说明流正常</div>
    <img src="/video_feed" alt="视频流">
    <div class="info">
        <button onclick="location.reload()">刷新页面</button>
        <button onclick="testVideoFeed()">测试视频流</button>
    </div>
    <div id="status"></div>

    <script>
        function testVideoFeed() {
            fetch('/video_feed')
                .then(response => {
                    document.getElementById('status').innerHTML =
                        '视频流状态: ' + response.status + ' ' + response.statusText +
                        '<br>Content-Type: ' + response.headers.get('content-type');
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = '错误: ' + error;
                });
        }

        // 自动测试
        setTimeout(testVideoFeed, 2000);
    </script>
</body>
</html>'''

@app.route('/video_feed')
def video_feed():
    print("📺 视频流被请求")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 启动视频流测试...")
    if init_camera():
        print("✅ 摄像头初始化成功")
        print("📱 访问: http://localhost:5001")
        app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        print("❌ 摄像头初始化失败")