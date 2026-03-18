# 🤖 机器人视觉识别系统

一个集成RTSP视频流、VLM视觉识别、云台控制的完整机器人视觉解决方案。

## 🌟 主要功能

- ✅ **RTSP视频流获取**: 支持实时拉流取流
- ✅ **VLM视觉识别**: 使用Qwen2-VL进行智能图像分析
- ✅ **云台控制**: 支持PTZ摄像头控制
- ✅ **自动跟踪**: 智能目标跟踪
- ✅ **实时显示**: 可视化识别结果
- ✅ **交互控制**: 手动云台操作模式

## 🛠️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RTSP摄像头    │───▶│   视频流获取    │───▶│   帧缓冲队列    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐             │
│   云台控制      │◀───│   主控制器      │◀────────────┘
└─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   VLM视觉分析   │
                       └─────────────────┘
```

## 📋 安装依赖

```bash
# 安装Python依赖
pip install torch torchvision transformers opencv-python requests qwen-vl-utils

# Ubuntu系统可能需要额外安装
sudo apt install libgl1-mesa-glx libglib2.0-0
```

## ⚙️ 配置说明

编辑 `robot_vision_config.py` 设置你的设备参数：

```python
# RTSP配置 - 修改为你的摄像头地址
RTSP_URL = "rtsp://admin:password@192.168.1.100:554/stream1"

# 云台控制配置 - 修改为你的云台IP和认证信息
PTZ_BASE_URL = "http://192.168.1.100"
PTZ_USERNAME = "admin"
PTZ_PASSWORD = "password"
```

### 📡 RTSP地址格式示例

```bash
# 海康威视
rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101

# 大华
rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0

# 通用格式
rtsp://username:password@ip:port/path
```

## 🚀 快速启动

### 方法1: 使用启动脚本
```bash
chmod +x start_robot_vision.sh
./start_robot_vision.sh
```

### 方法2: 直接运行
```bash
# 自动模式
python3 robot_vision_main.py

# 交互模式
python3 robot_vision_main.py interactive
```

## 🎮 操作说明

### 自动模式
- 系统自动进行视觉识别和目标跟踪
- 按 `q` 退出系统
- 按 `s` 保存当前帧
- 按 `t` 切换自动跟踪开关

### 交互模式
- `w/s` - 云台上/下移动
- `a/d` - 云台左/右移动
- `+/-` - 放大/缩小
- `space` - 停止移动
- `p` - 设置预设位置
- `g` - 移动到预设位置
- `q` - 退出

## 📁 文件说明

| 文件 | 功能 |
|------|------|
| `robot_vision_main.py` | 主程序入口 |
| `robot_vision_config.py` | 系统配置 |
| `rtsp_streamer.py` | RTSP视频流处理 |
| `vision_analyzer.py` | VLM视觉分析 |
| `ptz_controller.py` | 云台控制 |
| `start_robot_vision.sh` | 启动脚本 |

## 🔧 系统调试

### 测试RTSP连接
```python
from rtsp_streamer import RTSPStreamer
streamer = RTSPStreamer("your_rtsp_url")
streamer.test_stream(10)  # 测试10秒
```

### 测试云台控制
```python
from ptz_controller import PTZController
ptz = PTZController()
ptz.test_connection()  # 测试连接
ptz.pan_left(50)      # 向左移动
ptz.stop()            # 停止移动
```

### 测试VLM模型
```python
from vision_analyzer import VisionAnalyzer
analyzer = VisionAnalyzer()
analyzer.load_model()  # 测试模型加载
```

## ⚡ 性能优化

### 硬件要求
- **GPU**: NVIDIA RTX 3060 或更高 (推荐RTX 4090)
- **内存**: 16GB+ RAM
- **存储**: 20GB+ 可用空间

### 性能配置
```python
# 在 robot_vision_config.py 中调整:
ANALYSIS_INTERVAL = 3.0    # 分析间隔(秒)，增加可降低GPU负载
SKIP_FRAMES = 2           # 跳帧数，增加可降低处理负载
BUFFER_SIZE = 10          # 缓冲区大小
```

## 🐛 常见问题

### 1. RTSP连接失败
- 检查网络连接和摄像头IP
- 确认用户名密码正确
- 尝试不同的RTSP路径

### 2. 云台控制无响应
- 确认云台API接口类型
- 检查HTTP认证信息
- 查看云台厂商文档

### 3. VLM模型加载慢
- 首次运行需下载模型(约15GB)
- 使用SSD存储可提升速度
- 设置HF_TOKEN加速下载

### 4. GPU显存不足
- 减少批处理大小
- 增加分析间隔时间
- 使用CPU模式(较慢)

## 📝 日志和监控

系统运行时会显示详细状态信息：
```
🤖 机器人视觉识别系统运行中...
📊 实际FPS: 28.5, 总帧数: 1250
🎯 检测到对象: 人, 汽车
⭐ 优先目标: 人
🎮 执行跟踪动作: pan_right (30)
```

## 🔮 扩展功能

### 添加新的目标识别
在 `vision_analyzer.py` 中修改提示词：
```python
prompt = """识别以下特定目标：
1. 安全帽佩戴检测
2. 违规行为识别
3. 异常情况警报
"""
```

### 添加云台厂商支持
在 `ptz_controller.py` 中添加新的API接口。

### 集成报警系统
```python
# 在检测到特定目标时发送报警
if "危险" in analysis_result:
    send_alert_notification()
```

## 📧 技术支持

如遇问题请检查：
1. 系统日志输出
2. 网络连接状态
3. 硬件资源使用情况
4. 配置文件参数

---

🎉 **恭喜！现在你有了一个完整的机器人视觉识别系统！**