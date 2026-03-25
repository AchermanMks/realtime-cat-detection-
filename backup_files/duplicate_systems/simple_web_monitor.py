#!/usr/bin/env python3
"""
简化版Web监控 - 快速启动，无需VLM模型
"""

from flask import Flask, render_template_string, jsonify
import time
import random
from datetime import datetime
import threading
import json

app = Flask(__name__)

# 模拟数据
class SimpleMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.frame_count = 0
        self.analysis_count = 0
        self.alerts = []
        self.running = True

        # 模拟场景
        self.scenarios = [
            {"name": "办公室", "risk": "低", "objects": ["桌子", "电脑", "人员"]},
            {"name": "实验室", "risk": "中", "objects": ["设备", "试剂", "人员"]},
            {"name": "车间", "risk": "高", "objects": ["机器", "工具", "人员"]}
        ]
        self.current_scenario = 0

        # 启动模拟线程
        self.thread = threading.Thread(target=self.simulate_data, daemon=True)
        self.thread.start()

    def simulate_data(self):
        """模拟数据生成"""
        while self.running:
            # 模拟帧处理
            self.frame_count += 15  # 15 FPS

            # 模拟分析
            if time.time() % 5 < 1:  # 每5秒一次分析
                self.analysis_count += 1

                # 随机切换场景
                if random.random() < 0.3:
                    self.current_scenario = (self.current_scenario + 1) % len(self.scenarios)

                # 模拟报警
                if random.random() < 0.4:  # 40%概率报警
                    alert = {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "scene": self.scenarios[self.current_scenario]["name"],
                        "message": "检测到异常活动",
                        "risk": self.scenarios[self.current_scenario]["risk"]
                    }
                    self.alerts.append(alert)
                    if len(self.alerts) > 10:
                        self.alerts.pop(0)  # 保持最新10条

            time.sleep(1)

    def get_status(self):
        """获取当前状态"""
        uptime = time.time() - self.start_time
        scenario = self.scenarios[self.current_scenario]

        return {
            "uptime": uptime,
            "fps": 15.0,
            "frame_count": self.frame_count,
            "analysis_count": self.analysis_count,
            "current_scene": scenario["name"],
            "risk_level": scenario["risk"],
            "detected_objects": scenario["objects"],
            "alerts": self.alerts[-5:],  # 最新5条报警
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# 全局监控实例
monitor = SimpleMonitor()

# Web页面模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎥 简化版监控系统</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0; padding: 20px;
            background: #1a1a1a; color: #fff;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #00ff88; margin: 0; }
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .panel {
            background: #2a2a2a;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #00ff88;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: #444;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 12px;
            color: #ccc;
        }
        .video-placeholder {
            width: 100%;
            height: 300px;
            background: #333;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 18px;
            margin: 20px 0;
        }
        .alert-item {
            background: #4a2c2c;
            border-left: 4px solid #ff6b6b;
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
        }
        .risk-low { color: #4caf50; }
        .risk-medium { color: #ff9800; }
        .risk-high { color: #f44336; }
        .objects {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 10px 0;
        }
        .object-tag {
            background: #555;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4caf50;
            margin-right: 8px;
            animation: pulse 2s infinite;
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
        <div class="header">
            <h1>🎥 简化版监控分析系统</h1>
            <p><span class="status-indicator"></span>实时监控中 | 最后更新: <span id="timestamp">--</span></p>
        </div>

        <div class="dashboard">
            <div class="panel">
                <h3>📺 监控画面</h3>
                <div class="video-placeholder">
                    🎬 模拟摄像头画面<br>
                    <small>(实际部署时显示真实视频)</small>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" id="fps">--</div>
                        <div class="stat-label">FPS</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="frames">--</div>
                        <div class="stat-label">处理帧数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="uptime">--</div>
                        <div class="stat-label">运行时间</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="analyses">--</div>
                        <div class="stat-label">AI分析</div>
                    </div>
                </div>
            </div>

            <div class="panel">
                <h3>🤖 AI分析结果</h3>
                <div id="scene-info">
                    <h4>当前场景: <span id="scene">--</span></h4>
                    <p>风险级别: <span id="risk" class="risk-low">--</span></p>
                    <div id="objects" class="objects"></div>
                </div>

                <h4>⚠️ 最新报警</h4>
                <div id="alerts"></div>
            </div>
        </div>
    </div>

    <script>
        function updateData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 更新时间
                    document.getElementById('timestamp').textContent = data.timestamp;

                    // 更新统计
                    document.getElementById('fps').textContent = data.fps;
                    document.getElementById('frames').textContent = data.frame_count.toLocaleString();
                    document.getElementById('analyses').textContent = data.analysis_count;

                    // 更新运行时间
                    const hours = Math.floor(data.uptime / 3600);
                    const minutes = Math.floor((data.uptime % 3600) / 60);
                    const seconds = Math.floor(data.uptime % 60);
                    document.getElementById('uptime').textContent =
                        hours + 'h ' + minutes + 'm ' + seconds + 's';

                    // 更新场景信息
                    document.getElementById('scene').textContent = data.current_scene;

                    const riskElement = document.getElementById('risk');
                    riskElement.textContent = data.risk_level;
                    riskElement.className = 'risk-' + (data.risk_level === '低' ? 'low' :
                                                     data.risk_level === '中' ? 'medium' : 'high');

                    // 更新检测物体
                    const objectsContainer = document.getElementById('objects');
                    objectsContainer.innerHTML = data.detected_objects.map(obj =>
                        `<span class="object-tag">${obj}</span>`
                    ).join('');

                    // 更新报警
                    const alertsContainer = document.getElementById('alerts');
                    alertsContainer.innerHTML = data.alerts.map(alert =>
                        `<div class="alert-item">
                            <strong>${alert.time}</strong> - ${alert.scene}<br>
                            ${alert.message} (${alert.risk}风险)
                        </div>`
                    ).join('') || '<p style="color: #666;">暂无报警</p>';
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('timestamp').textContent = '连接错误';
                });
        }

        // 每2秒更新一次
        setInterval(updateData, 2000);
        updateData(); // 立即更新一次
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    """状态API"""
    return jsonify(monitor.get_status())

def main():
    print("🚀 启动简化版Web监控...")
    print("📱 访问地址: http://localhost:9999")
    print("🛑 按 Ctrl+C 停止服务")

    try:
        app.run(host='0.0.0.0', port=9999, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
        monitor.running = False

if __name__ == "__main__":
    main()