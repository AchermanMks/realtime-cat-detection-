# 🎥 Web版智能摄像头监控系统 + PTZ云台控制

基于Flask + VLM + PTZ的全功能实时摄像头Web监控和云台控制系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-orange.svg)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red.svg)](https://pytorch.org/)
[![PTZ](https://img.shields.io/badge/PTZ-Supported-purple.svg)](https://en.wikipedia.org/wiki/Pan%E2%80%93tilt%E2%80%93zoom_camera)

## ✨ 主要功能

### 🎥 视频监控功能
- 🌐 **Web界面访问** - 通过浏览器实时查看摄像头画面
- 🤖 **VLM智能分析** - 使用Qwen2-VL-7B-Instruct模型进行视觉理解
- 📺 **实时视频流** - 支持RTSP网络摄像头和本地摄像头
- 📊 **实时监控面板** - 显示FPS、帧数、分析次数等统计信息
- 🔄 **定期AI分析** - 每10秒自动进行智能场景分析
- 📱 **响应式界面** - 支持桌面和移动设备访问

### 🎮 PTZ云台控制功能 (新增)
- 🔄 **全方位云台控制** - 支持Pan(水平)、Tilt(垂直)、Zoom(变焦)操作
- 🎯 **多协议支持** - 自动检测并支持ONVIF、海康威视、大华等主流协议
- 📍 **预设位置管理** - 设置和调用多个预设监控位置
- ⌨️ **键盘快捷控制** - 使用方向键、+/-键快速控制云台
- 🎚️ **可调节速度** - 支持1-100级速度调节
- 📱 **触屏友好** - 移动设备触屏控制支持
- 🔍 **智能检测** - 自动检测摄像头PTZ能力

### 🛠️ 技术特性
- 🚀 **多线程架构** - 视频捕获、AI分析、PTZ控制独立线程
- 🔌 **RESTful API** - 完整的API接口支持
- ⚡ **实时响应** - 低延迟的PTZ控制体验
- 🛡️ **错误处理** - 完善的异常处理和恢复机制
- 📝 **详细日志** - 操作日志记录和故障诊断

## 🚀 快速开始

### 环境要求

- Python 3.8+
- CUDA支持的GPU (推荐，可选)
- 至少8GB内存
- 支持PTZ的网络摄像头 (RTSP协议)

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/AchermanMks/webcam-ai-monitor.git
cd webcam-ai-monitor

# 安装Python依赖 (PTZ版本)
pip install -r requirements_with_ptz.txt

# 安装Qwen VL工具包
pip install qwen-vl-utils

# 安装系统依赖 (Ubuntu/Debian)
sudo apt-get install libgl1-mesa-glx libglib2.0-0 nmap

# 安装系统依赖 (CentOS/RHEL)
sudo yum install mesa-libGL glib2 nmap
```

### 配置摄像头和PTZ

编辑配置文件 `config_with_ptz.py`:

```python
# 摄像头配置
DEFAULT_CAMERA = "rtsp://192.168.1.100:8554/unicast"

# PTZ配置
PTZ_CONFIG = {
    'enabled': True,
    'camera_ip': '192.168.1.100',    # 摄像头IP地址
    'username': 'admin',             # 登录用户名
    'password': 'your_password',     # 登录密码
    'protocol': 'auto',              # 自动检测协议
}

# 预设位置配置
PTZ_PRESETS = {
    1: {'name': '正门入口', 'description': '监控正门人员进出'},
    2: {'name': '大厅中央', 'description': '大厅全景监控'},
    # ... 更多预设
}
```

### 运行系统

```bash
# 使用PTZ增强版
python app_with_ptz.py
```

然后在浏览器中访问: **http://localhost:5000**

## 🎮 PTZ控制功能详解

### 支持的摄像头协议

| 协议类型 | 厂商 | 支持状态 | 备注 |
|---------|------|----------|------|
| ONVIF | 通用标准 | ✅ 完全支持 | 推荐使用 |
| 海康威视 | Hikvision | ✅ 完全支持 | ISAPI接口 |
| 大华 | Dahua | ✅ 完全支持 | CGI接口 |
| 通用HTTP | 多厂商 | ✅ 基础支持 | 基本PTZ功能 |

### PTZ控制界面

#### 方向控制
```
    ⬆️
⬅️  ⏹️  ➡️
    ⬇️
```
- **⬆️⬇️**: 垂直转动 (Tilt)
- **⬅️➡️**: 水平转动 (Pan)
- **⏹️**: 停止所有运动

#### 变焦控制
- **🔍+ 放大**: 拉近镜头
- **🔍- 缩小**: 拉远镜头

#### 预设位置
- **1-5号预设**: 快速跳转到预设监控位置
- **自定义预设**: 支持设置新的预设位置

#### 键盘快捷键
- **方向键** (↑↓←→): 控制云台方向
- **+/-键**: 控制变焦
- **空格键**: 停止所有运动
- **数字键 1-5**: 快速跳转到预设位置

### API接口

#### PTZ控制API

```bash
# 方向控制
POST /api/ptz/control
{
    "command": "pan",      # pan, tilt, zoom, stop
    "direction": "left",   # left, right, up, down, in, out, all
    "speed": 50           # 1-100
}

# 预设位置
POST /api/ptz/preset/1          # 跳转到预设1
POST /api/ptz/preset/1/set      # 设置当前位置为预设1

# PTZ状态查询
GET /api/ptz/status
```

#### 系统状态API

```bash
# 完整系统状态 (包含PTZ)
GET /api/status
{
    "fps": 25.6,
    "total_frames": 15420,
    "total_analyses": 154,
    "ptz_status": {
        "supported": true,
        "type": "hikvision",
        "current_preset": 1,
        "presets": {...}
    }
}
```

## ⚙️ 配置说明

### 基础配置

```python
# 摄像头源 (必须是RTSP协议才支持PTZ)
DEFAULT_CAMERA = "rtsp://admin:password@192.168.1.100:8554/unicast"

# PTZ基本设置
PTZ_CONFIG = {
    'enabled': True,                    # 启用PTZ控制
    'camera_ip': '192.168.1.100',      # 自动从RTSP URL提取
    'username': 'admin',                # 摄像头登录用户名
    'password': 'admin123',             # 摄像头登录密码
    'protocol': 'auto',                 # auto, onvif, hikvision, dahua
    'connection_timeout': 3,            # 连接超时时间
}
```

### 高级配置

```python
# PTZ速度设置
PTZ_SPEEDS = {
    'pan_speed': 50,        # 水平转动速度
    'tilt_speed': 50,       # 垂直转动速度
    'zoom_speed': 50,       # 变焦速度
}

# 安全设置
SECURITY = {
    'rate_limit': {
        'ptz_commands_per_minute': 30,  # PTZ命令频率限制
    },
    'ptz_access_control': {
        'enable_ip_whitelist': True,    # IP白名单
        'allowed_ips': ['192.168.1.0/24'],
    }
}
```

## 📁 项目结构

```
webcam-ai-monitor/
├── 📄 app_with_ptz.py           # PTZ增强版主应用
├── 📄 app.py                    # 基础版本应用
├── ⚙️ config_with_ptz.py        # PTZ完整配置文件
├── ⚙️ config.py                 # 基础配置文件
├── 📋 requirements_with_ptz.txt # PTZ版本依赖列表
├── 📋 requirements.txt          # 基础版本依赖列表
├── 📖 README_PTZ.md             # PTZ版本说明文档 (本文件)
├── 📖 README.md                 # 基础版本说明文档
├── 🔧 setup.sh                  # 自动安装脚本
├── 🚀 start.sh                  # 快速启动脚本
├── 📜 LICENSE                   # MIT许可证
├── 🚫 .gitignore                # Git忽略文件配置
└── 📚 DEPLOYMENT_GUIDE.md       # GitHub部署指南
```

## 🎯 使用场景

### 安防监控
- 🏢 **办公楼监控**: 大厅、走廊、出入口全方位监控
- 🏪 **商店监控**: 收银台、货架、库房重点区域监控
- 🏠 **家庭安防**: 客厅、院子、车库智能监控

### 智能跟踪
- 👤 **人员跟踪**: 自动跟踪可疑人员移动
- 🚗 **车辆监控**: 停车场车辆进出管理
- 📦 **物品监控**: 仓库、货场物品安全监控

### 远程监控
- 🌐 **远程管理**: 通过网络远程控制摄像头
- 📱 **移动监控**: 手机、平板随时随地监控
- 🤖 **智能分析**: AI自动识别异常情况

## 🛠️ 故障排除

### PTZ控制问题

1. **PTZ不响应**
   ```
   ✅ 检查摄像头IP地址是否正确
   ✅ 验证用户名密码
   ✅ 确认摄像头支持PTZ功能
   ✅ 检查网络连接状态
   ```

2. **协议检测失败**
   ```
   ✅ 手动指定协议类型 (protocol: 'hikvision')
   ✅ 检查摄像头厂商和型号
   ✅ 查看控制台错误日志
   ✅ 尝试不同的API端点
   ```

3. **权限问题**
   ```
   ✅ 确认用户有PTZ控制权限
   ✅ 检查摄像头用户权限设置
   ✅ 验证网络防火墙设置
   ✅ 确认摄像头未被其他客户端占用
   ```

### 常见摄像头配置

#### 海康威视
```python
PTZ_CONFIG = {
    'protocol': 'hikvision',
    'camera_ip': '192.168.1.100',
    'username': 'admin',
    'password': 'admin123',
}
# URL示例: rtsp://admin:admin123@192.168.1.100:554/h264/ch1/main/av_stream
```

#### 大华
```python
PTZ_CONFIG = {
    'protocol': 'dahua',
    'camera_ip': '192.168.1.101',
    'username': 'admin',
    'password': 'admin123',
}
# URL示例: rtsp://admin:admin123@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0
```

#### ONVIF标准
```python
PTZ_CONFIG = {
    'protocol': 'onvif',
    'camera_ip': '192.168.1.102',
    'username': 'admin',
    'password': 'admin123',
}
# 大多数现代IP摄像头都支持ONVIF
```

## 📊 技术架构

### 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web前端界面    │    │   Flask后端     │    │   摄像头设备     │
│  ┌─────────────┐ │    │  ┌─────────────┐ │    │  ┌─────────────┐ │
│  │ 视频显示    │ │◄──►│  │ 视频流处理   │ │◄──►│  │ RTSP视频流  │ │
│  │ PTZ控制面板 │ │    │  │ PTZ控制器   │ │    │  │ PTZ接口     │ │
│  │ AI分析显示  │ │    │  │ VLM分析引擎 │ │    │  │ HTTP API    │ │
│  └─────────────┘ │    │  └─────────────┘ │    │  └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────── 网络通信 ──────┴───────── 网络通信 ─────┘
```

### 核心组件

1. **WebCameraVLM类**: 主控制器
   - 视频流管理
   - VLM分析协调
   - PTZ控制集成

2. **PTZController类**: PTZ控制器
   - 多协议支持
   - 命令封装
   - 状态管理

3. **Web前端**: 用户界面
   - 实时视频显示
   - PTZ控制界面
   - 键盘快捷键

## 🤝 贡献指南

### 开发环境设置

```bash
# 克隆开发分支
git clone -b develop https://github.com/AchermanMks/webcam-ai-monitor.git

# 安装开发依赖
pip install -r requirements_with_ptz.txt
pip install pytest pytest-cov black

# 运行测试
python -m pytest tests/ -v

# 代码格式化
black *.py
```

### 添加新的PTZ协议支持

1. 在 `PTZController` 类中添加新的协议检测方法
2. 实现对应的命令发送方法
3. 更新配置文件中的厂商配置
4. 添加测试用例

### 功能请求

欢迎提交以下类型的功能请求：
- [ ] 新厂商PTZ协议支持
- [ ] 自动巡航功能
- [ ] 运动检测跟踪
- [ ] 录像功能
- [ ] 多摄像头支持

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 🐛 [提交Issue](https://github.com/AchermanMks/webcam-ai-monitor/issues)
- 💬 [GitHub Discussions](https://github.com/AchermanMks/webcam-ai-monitor/discussions)
- 📧 技术支持: [在Issues中提问]

## 🙏 致谢

- [Qwen2-VL](https://github.com/QwenLM/Qwen2-VL) - 优秀的视觉语言模型
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [Flask](https://flask.palletsprojects.com/) - Python Web框架
- [ONVIF](https://www.onvif.org/) - 开放网络视频接口标准

---

⭐ 如果这个项目对你有帮助，请给个star支持一下！

**版本**: v2.0.0-PTZ
**更新时间**: 2026-03-16
**Python兼容性**: 3.8+
**PTZ支持**: ONVIF, 海康威视, 大华, 通用HTTP