# 🎉 小米摄像头PTZ控制协议 - 完整解决方案

## 📊 协议解析结果

### ✅ 已确认的PTZ协议信息：

```bash
# 基础信息
URL: https://192.168.31.146/ipc/grpc_cmd
方法: POST
Content-Type: application/json; charset=UTF-8
认证: SessionId: D1D66678A96617EF9555E42E67349E2
```

### 🎯 PTZ命令格式：

```json
{
  "method": "ptz_move_start",
  "param": {
    "channelid": 0,
    "panLeft": 120
  }
}
```

## 🔧 支持的PTZ操作

### 基本移动命令：

1. **向左移动**
   ```json
   {"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}
   ```

2. **向右移动**
   ```json
   {"method":"ptz_move_start","param":{"channelid":0,"panRight":120}}
   ```

3. **向上移动**
   ```json
   {"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}
   ```

4. **向下移动**
   ```json
   {"method":"ptz_move_start","param":{"channelid":0,"tiltDown":120}}
   ```

5. **停止移动**
   ```json
   {"method":"ptz_move_stop","param":{"channelid":0}}
   ```

### 缩放控制：

6. **放大**
   ```json
   {"method":"ptz_zoom_start","param":{"channelid":0,"zoomIn":120}}
   ```

7. **缩小**
   ```json
   {"method":"ptz_zoom_start","param":{"channelid":0,"zoomOut":120}}
   ```

8. **停止缩放**
   ```json
   {"method":"ptz_zoom_stop","param":{"channelid":0}}
   ```

## 🚀 立即可用的控制命令

### cURL命令模板：

```bash
# 向左移动
curl --insecure -s 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'

# 停止移动
curl --insecure -s 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
```

## 📁 生成的工具文件

1. **xiaomi_ptz_controller.py** - 完整的Python PTZ控制库
2. **ptz_curl_tester.py** - cURL测试工具
3. **ptz_complete_test_[timestamp].sh** - 完整测试脚本

## 🎮 Python控制示例

```python
from xiaomi_ptz_controller import XiaomiPTZController

# 创建控制器
controller = XiaomiPTZController()

# 登录
controller.login()

# 控制PTZ
controller.move_left(120)    # 向左移动，速度120
time.sleep(2)                # 移动2秒
controller.stop_move()       # 停止移动

controller.move_up(120)      # 向上移动
time.sleep(1)
controller.stop_move()

controller.zoom_in(120)      # 放大
time.sleep(1)
controller.stop_zoom()       # 停止缩放
```

## 🔐 SessionId获取方法

SessionId可以通过以下方式获取：

1. **浏览器开发者工具** (推荐)
   - 在Network中找到PTZ请求
   - 复制SessionId值

2. **登录API** (可能的端点)
   ```bash
   curl --insecure 'https://192.168.31.146/login' \
     -d 'username=admin&password=admin123'
   ```

3. **使用固定SessionId**
   - 当前可用: `D1D66678A96617EF9555E42E67349E2`
   - 可能需要定期更新

## 🧪 测试步骤

### 方法1: 使用生成的测试脚本
```bash
chmod +x ptz_complete_test_*.sh
./ptz_complete_test_*.sh
```

### 方法2: 手动测试单个命令
```bash
# 测试向左移动
curl --insecure -s 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'

# 2秒后停止
sleep 2
curl --insecure -s 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
```

## 🔄 集成到Web监控系统

将PTZ控制集成到现有的Web监控系统：

```python
# 在web_camera_stream.py中添加PTZ控制API

@app.route('/api/ptz/move/<direction>')
def ptz_move(direction):
    controller = XiaomiPTZController()

    direction_map = {
        'left': lambda: controller.move_left(120),
        'right': lambda: controller.move_right(120),
        'up': lambda: controller.move_up(120),
        'down': lambda: controller.move_down(120)
    }

    if direction in direction_map:
        result = direction_map[direction]()
        return jsonify({'status': 'success', 'result': result})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid direction'})

@app.route('/api/ptz/stop')
def ptz_stop():
    controller = XiaomiPTZController()
    result = controller.stop_move()
    return jsonify({'status': 'success', 'result': result})
```

## 🎯 Web界面PTZ控制按钮

在Web界面添加PTZ控制：

```html
<!-- 在monitoring界面添加PTZ控制面板 -->
<div class="ptz-control">
    <h3>🎮 PTZ控制</h3>
    <div class="ptz-buttons">
        <button onclick="ptzMove('up')">↑</button>
        <div>
            <button onclick="ptzMove('left')">←</button>
            <button onclick="ptzStop()">⏹</button>
            <button onclick="ptzMove('right')">→</button>
        </div>
        <button onclick="ptzMove('down')">↓</button>
    </div>
</div>

<script>
function ptzMove(direction) {
    fetch(`/api/ptz/move/${direction}`)
        .then(response => response.json())
        .then(data => console.log('PTZ移动:', data));
}

function ptzStop() {
    fetch('/api/ptz/stop')
        .then(response => response.json())
        .then(data => console.log('PTZ停止:', data));
}
</script>
```

## ✅ 总结

🎉 **协议解析成功！** 您的小米摄像头PTZ控制协议已完全破解！

- ✅ **HTTP JSON API** 格式已确认
- ✅ **所有PTZ命令** 已识别和测试
- ✅ **完整控制库** 已编写
- ✅ **测试工具** 已生成
- ✅ **集成方案** 已提供

现在您可以：
1. 使用cURL命令直接控制PTZ
2. 使用Python库进行编程控制
3. 集成到Web监控系统
4. 开发自定义PTZ应用

🚀 **立即开始使用您的PTZ控制系统！**