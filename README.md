# RTSP AI监控系统

🎥 基于AI的智能实时摄像头监控系统，支持RTSP流、VLM分析和PTZ控制

## ✨ 功能特性

- 📹 **实时RTSP视频流** - 支持IP摄像头实时监控
- 🤖 **AI场景分析** - 基于Qwen2-VL模型自动分析视频内容
- 🎮 **PTZ控制** - 支持摄像头平移、倾斜、缩放控制
- 🌐 **Web界面** - 黑色主题的现代化监控界面
- ⌨️ **键盘控制** - WASD键控制摄像头移动
- 📊 **实时状态** - FPS、帧数、运行时间等状态监控
- 🔍 **摄像头发现** - 自动扫描网络中的IP摄像头

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- CUDA支持的GPU (推荐)
- 网络摄像头或RTSP流

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 发现网络摄像头

```bash
python quick_scan.py
```

### 4. 启动监控系统

**使用RTSP摄像头:**
```bash
python integrated_camera_system.py --rtsp "rtsp://username:password@ip:port/stream" --port 5000
```

**使用本地摄像头:**
```bash
python integrated_camera_system.py --camera 0 --port 5000
```

### 5. 访问Web界面

打开浏览器访问: `http://localhost:5000`

## 🎯 使用示例

### RTSP摄像头连接
```bash
# 小米摄像头示例
python integrated_camera_system.py --rtsp "rtsp://admin:admin123@192.168.1.100:8554/unicast" --port 5000

# 海康威视摄像头示例
python integrated_camera_system.py --rtsp "rtsp://admin:password@192.168.1.101:554/stream1" --port 5000
```

### PTZ控制
- 🎮 **鼠标点击** - 点击界面按钮控制
- ⌨️ **键盘控制**:
  - `W/↑` - 向上
  - `S/↓` - 向下
  - `A/←` - 向左
  - `D/→` - 向右
  - `空格` - 停止
  - `+/=` - 放大
  - `-` - 缩小

## 📋 命令行参数

```bash
python integrated_camera_system.py [选项]

选项:
  --rtsp TEXT     RTSP摄像头URL
  --camera INT    本地摄像头索引 (默认: 0)
  --port INT      Web服务器端口 (默认: 5000)
  --host TEXT     Web服务器主机 (默认: 0.0.0.0)
```

## 🔧 配置说明

### RTSP URL格式
```
rtsp://[用户名:密码@]IP地址:端口/流路径
```

### 常用摄像头配置
- **小米摄像头**: `rtsp://admin:admin123@ip:8554/unicast`
- **海康威视**: `rtsp://admin:password@ip:554/stream1`
- **大华**: `rtsp://admin:admin@ip:554/cam/realmonitor?channel=1&subtype=0`

## 🌟 界面功能

- **实时视频流** - 高清视频显示
- **AI分析结果** - 自动场景描述和分析
- **PTZ控制面板** - 方向控制和缩放
- **系统状态** - FPS、帧数、分析次数、运行时间
- **响应式设计** - 支持桌面和移动设备

## 🛠️ 技术栈

- **后端**: Flask, OpenCV, PyTorch
- **AI模型**: Qwen2-VL-7B-Instruct
- **前端**: HTML5, CSS3, JavaScript
- **视频处理**: OpenCV, FFMPEG
- **协议支持**: RTSP, HTTP

## 📱 界面预览

- 🖤 **暗色主题** - 专业监控界面
- 📺 **视频区域** - 占据主要显示区域
- 🎛️ **控制面板** - 右侧PTZ控制和状态显示
- 📊 **实时状态** - 底部状态栏显示系统信息

## 🔍 故障排除

### RTSP连接失败
1. 检查网络连接和摄像头IP
2. 确认用户名密码正确
3. 尝试不同的流路径格式
4. 使用摄像头发现工具: `python quick_scan.py`

### AI分析缓慢
1. 确保GPU可用: `torch.cuda.is_available()`
2. 调整分析间隔参数
3. 考虑使用更小的AI模型

### Web界面无法访问
1. 检查防火墙设置
2. 确认端口未被占用
3. 尝试使用localhost:5000

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## ⭐ Star History

如果这个项目对你有帮助，请给一个Star ⭐