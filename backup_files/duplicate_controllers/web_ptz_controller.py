#!/usr/bin/env python3
"""
基于Web的小米摄像头PTZ控制器
提供Web界面控制PTZ功能
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import json
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

class WebPTZController:
    def __init__(self):
        self.camera_ip = "192.168.31.146"
        self.username = "admin"
        self.password = "admin123"
        self.session_id = None
        self.session = requests.Session()
        self.session.verify = False

    def login(self):
        """登录获取SessionId"""
        try:
            login_url = f"https://{self.camera_ip}/ipc/login"
            login_data = {"username": self.username, "password": self.password}

            response = self.session.post(login_url, json=login_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('result') == 0:
                    self.session_id = result.get('param', {}).get('sessionid')
                    if self.session_id:
                        # 设置headers
                        self.session.headers.update({
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                            'Content-Type': 'application/json; charset=UTF-8',
                            'SessionId': self.session_id,
                            'X-Requested-With': 'XMLHttpRequest'
                        })
                        return True
        except Exception as e:
            print(f"登录失败: {e}")
        return False

    def send_command(self, method, params):
        """发送PTZ命令"""
        if not self.session_id and not self.login():
            return {"success": False, "message": "登录失败"}

        try:
            cmd_url = f"https://{self.camera_ip}/ipc/grpc_cmd"
            cmd_data = {"method": method, "param": {"channelid": 0, **params}}

            response = self.session.post(cmd_url, json=cmd_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get("result") == 0, "data": result}
            else:
                return {"success": False, "message": f"请求失败: {response.status_code}"}

        except Exception as e:
            return {"success": False, "message": f"发送命令失败: {e}"}

# 全局控制器实例
ptz_controller = WebPTZController()

# Web界面HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小米摄像头PTZ控制器</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            color: white;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        .status {
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .status.success {
            background: rgba(76, 175, 80, 0.3);
        }
        .status.error {
            background: rgba(244, 67, 54, 0.3);
        }
        .control-section {
            margin-bottom: 30px;
        }
        .control-section h3 {
            margin-bottom: 15px;
            text-align: center;
        }
        .direction-controls {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            max-width: 300px;
            margin: 0 auto 20px;
        }
        .zoom-controls, .preset-controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
        }
        button:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        button:active {
            transform: translateY(0);
        }
        .direction-btn {
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .empty {
            visibility: hidden;
        }
        .stop-btn {
            background: rgba(244, 67, 54, 0.3);
            grid-column: span 3;
        }
        .config-section {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .config-row {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            align-items: center;
        }
        .config-row label {
            min-width: 80px;
        }
        input, select {
            flex: 1;
            padding: 8px 12px;
            border: none;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            backdrop-filter: blur(5px);
        }
        input::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        .preset-row {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 10px;
        }
        .preset-row input {
            width: 60px;
        }
        #log {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 小米摄像头PTZ控制器</h1>

        <div id="status" class="status">准备就绪</div>

        <!-- 配置区域 -->
        <div class="config-section">
            <h3>⚙️ 摄像头配置</h3>
            <div class="config-row">
                <label>IP地址:</label>
                <input type="text" id="cameraIp" value="192.168.31.146" placeholder="摄像头IP地址">
            </div>
            <div class="config-row">
                <label>用户名:</label>
                <input type="text" id="username" value="admin" placeholder="用户名">
            </div>
            <div class="config-row">
                <label>密码:</label>
                <input type="password" id="password" value="admin123" placeholder="密码">
            </div>
            <div class="config-row">
                <label>速度:</label>
                <select id="speed">
                    <option value="60">慢速 (60)</option>
                    <option value="120" selected>中速 (120)</option>
                    <option value="180">快速 (180)</option>
                </select>
            </div>
            <div class="config-row">
                <button onclick="connect()">🔗 连接摄像头</button>
            </div>
        </div>

        <!-- 方向控制 -->
        <div class="control-section">
            <h3>🎮 方向控制</h3>
            <div class="direction-controls">
                <div class="empty"></div>
                <button class="direction-btn" onmousedown="startMove('up')" onmouseup="stopMove()" ontouchstart="startMove('up')" ontouchend="stopMove()">⬆️</button>
                <div class="empty"></div>

                <button class="direction-btn" onmousedown="startMove('left')" onmouseup="stopMove()" ontouchstart="startMove('left')" ontouchend="stopMove()">⬅️</button>
                <div class="empty"></div>
                <button class="direction-btn" onmousedown="startMove('right')" onmouseup="stopMove()" ontouchstart="startMove('right')" ontouchend="stopMove()">➡️</button>

                <div class="empty"></div>
                <button class="direction-btn" onmousedown="startMove('down')" onmouseup="stopMove()" ontouchstart="startMove('down')" ontouchend="stopMove()">⬇️</button>
                <div class="empty"></div>

                <button class="stop-btn" onclick="stopMove()">⏹️ 停止</button>
            </div>
        </div>

        <!-- 缩放控制 -->
        <div class="control-section">
            <h3>🔍 缩放控制</h3>
            <div class="zoom-controls">
                <button onmousedown="startZoom('in')" onmouseup="stopMove()" ontouchstart="startZoom('in')" ontouchend="stopMove()">🔍 放大</button>
                <button onmousedown="startZoom('out')" onmouseup="stopMove()" ontouchstart="startZoom('out')" ontouchend="stopMove()">🔍 缩小</button>
            </div>
        </div>

        <!-- 预设位控制 -->
        <div class="control-section">
            <h3>📍 预设位控制</h3>
            <div class="preset-controls">
                <div class="preset-row">
                    <input type="number" id="presetId" value="1" min="1" max="8" placeholder="预设位ID">
                    <button onclick="goToPreset()">转到预设位</button>
                    <button onclick="savePreset()">保存预设位</button>
                </div>
            </div>
            <div class="preset-controls">
                <button onclick="goToPreset(1)">预设1</button>
                <button onclick="goToPreset(2)">预设2</button>
                <button onclick="goToPreset(3)">预设3</button>
                <button onclick="goToPreset(4)">预设4</button>
            </div>
        </div>

        <!-- 日志区域 -->
        <div class="control-section">
            <h3>📋 操作日志</h3>
            <div id="log"></div>
        </div>
    </div>

    <script>
        let isConnected = false;
        let currentAction = null;

        function log(message, type = 'info') {
            const now = new Date().toLocaleTimeString();
            const logElement = document.getElementById('log');
            const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
            logElement.textContent += `[${now}] ${prefix} ${message}\n`;
            logElement.scrollTop = logElement.scrollHeight;
        }

        function setStatus(message, isError = false) {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = 'status ' + (isError ? 'error' : 'success');
        }

        async function connect() {
            log('正在连接摄像头...');
            try {
                const response = await fetch('/api/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        ip: document.getElementById('cameraIp').value,
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });

                const result = await response.json();
                if (result.success) {
                    isConnected = true;
                    setStatus('已连接到摄像头');
                    log('连接成功！', 'success');
                } else {
                    setStatus('连接失败', true);
                    log(`连接失败: ${result.message}`, 'error');
                }
            } catch (error) {
                setStatus('连接失败', true);
                log(`连接错误: ${error.message}`, 'error');
            }
        }

        async function sendCommand(endpoint, params = {}) {
            if (!isConnected) {
                log('请先连接摄像头', 'error');
                return;
            }

            try {
                const response = await fetch(`/api/${endpoint}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(params)
                });

                const result = await response.json();
                if (!result.success) {
                    log(`命令失败: ${result.message}`, 'error');
                }
                return result.success;
            } catch (error) {
                log(`请求错误: ${error.message}`, 'error');
                return false;
            }
        }

        function startMove(direction) {
            if (currentAction === direction) return;
            currentAction = direction;

            const speed = parseInt(document.getElementById('speed').value);
            log(`开始移动: ${direction} (速度: ${speed})`);
            sendCommand('move', {direction, speed});
        }

        function startZoom(type) {
            if (currentAction === `zoom_${type}`) return;
            currentAction = `zoom_${type}`;

            const speed = parseInt(document.getElementById('speed').value);
            log(`开始缩放: ${type} (速度: ${speed})`);
            sendCommand('zoom', {type, speed});
        }

        function stopMove() {
            if (!currentAction) return;

            log('停止移动');
            currentAction = null;
            sendCommand('stop');
        }

        function goToPreset(id = null) {
            const presetId = id || parseInt(document.getElementById('presetId').value);
            log(`转到预设位: ${presetId}`);
            sendCommand('preset/goto', {id: presetId});
        }

        function savePreset() {
            const presetId = parseInt(document.getElementById('presetId').value);
            log(`保存预设位: ${presetId}`);
            sendCommand('preset/save', {id: presetId});
        }

        // 防止触摸事件冒泡
        document.addEventListener('touchstart', function(e) {
            e.preventDefault();
        }, {passive: false});

        document.addEventListener('touchend', function(e) {
            e.preventDefault();
        }, {passive: false});

        // 页面加载完成后初始化
        window.onload = function() {
            log('PTZ控制器已就绪');
            setStatus('请点击"连接摄像头"按钮');
        };

        // 键盘控制
        document.addEventListener('keydown', function(e) {
            if (!isConnected) return;

            switch(e.key.toLowerCase()) {
                case 'w': startMove('up'); break;
                case 's': startMove('down'); break;
                case 'a': startMove('left'); break;
                case 'd': startMove('right'); break;
                case 'q': startZoom('in'); break;
                case 'e': startZoom('out'); break;
                case ' ': e.preventDefault(); stopMove(); break;
            }
        });

        document.addEventListener('keyup', function(e) {
            if (['w','s','a','d','q','e'].includes(e.key.toLowerCase())) {
                stopMove();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/connect', methods=['POST'])
def connect():
    """连接摄像头"""
    data = request.get_json()
    ptz_controller.camera_ip = data.get('ip', '192.168.31.146')
    ptz_controller.username = data.get('username', 'admin')
    ptz_controller.password = data.get('password', 'admin123')

    if ptz_controller.login():
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "登录失败"})

@app.route('/api/move', methods=['POST'])
def move():
    """移动控制"""
    data = request.get_json()
    direction = data.get('direction')
    speed = data.get('speed', 120)

    params = {}
    if direction == 'up':
        params['tiltUp'] = speed
    elif direction == 'down':
        params['tiltUp'] = -speed
    elif direction == 'left':
        params['panLeft'] = speed
    elif direction == 'right':
        params['panRight'] = speed

    result = ptz_controller.send_command('ptz_move_start', params)
    return jsonify(result)

@app.route('/api/zoom', methods=['POST'])
def zoom():
    """缩放控制"""
    data = request.get_json()
    zoom_type = data.get('type')
    speed = data.get('speed', 120)

    params = {}
    if zoom_type == 'in':
        params['zoomIn'] = speed
    elif zoom_type == 'out':
        params['zoomOut'] = speed

    result = ptz_controller.send_command('ptz_move_start', params)
    return jsonify(result)

@app.route('/api/stop', methods=['POST'])
def stop():
    """停止移动"""
    result = ptz_controller.send_command('ptz_move_stop', {})
    return jsonify(result)

@app.route('/api/preset/goto', methods=['POST'])
def goto_preset():
    """转到预设位"""
    data = request.get_json()
    preset_id = data.get('id')

    result = ptz_controller.send_command('ptz_preset_goto', {'presetId': preset_id})
    return jsonify(result)

@app.route('/api/preset/save', methods=['POST'])
def save_preset():
    """保存预设位"""
    data = request.get_json()
    preset_id = data.get('id')

    result = ptz_controller.send_command('ptz_preset_set', {'presetId': preset_id})
    return jsonify(result)

if __name__ == '__main__':
    print("🎥 小米摄像头PTZ Web控制器")
    print("=" * 50)
    print("启动Web服务器...")
    print("打开浏览器访问: http://localhost:5000")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)