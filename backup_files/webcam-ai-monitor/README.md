# 🎥 智能摄像头监控与PTZ控制系统

基于Flask + VLM的实时摄像头Web监控、AI分析和PTZ云台控制系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-orange.svg)](https://opencv.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red.svg)](https://pytorch.org/)
[![Node.js](https://img.shields.io/badge/Node.js-16+-green.svg)](https://nodejs.org/)

## ✨ 主要功能

### 📺 视频监控
- 🌐 **Web界面访问** - 通过浏览器实时查看摄像头画面
- 🤖 **VLM智能分析** - 使用Qwen2-VL-7B-Instruct模型进行视觉理解
- 📺 **实时视频流** - 支持RTSP网络摄像头和本地摄像头
- 📊 **实时监控面板** - 显示FPS、帧数、分析次数等统计信息
- 🔄 **定期AI分析** - 每10秒自动进行智能场景分析
- 📱 **响应式界面** - 支持桌面和移动设备访问
- 🎯 **RESTful API** - 提供状态查询API接口

### 🎮 PTZ控制
- 🌐 **Web控制界面** - 无需安装客户端，浏览器直接控制
- 🕹️ **实时云台控制** - 支持上下左右移动和变焦
- 🔧 **多种控制方式** - Web界面、命令行、Shell脚本
- 🔐 **无需Root权限** - 避免系统权限问题
- 🌉 **SSL兼容性** - Node.js代理解决OpenSSL兼容问题
- ⚡ **即时响应** - 低延迟的实时控制体验

## 🚀 快速开始

### 环境要求

- Python 3.8+
- CUDA支持的GPU (推荐，可选)
- 至少8GB内存
- 网络摄像头或RTSP摄像头

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/AchermanMks/webcam-ai-monitor.git
cd webcam-ai-monitor

# 安装Python依赖
pip install -r requirements.txt

# 安装Qwen VL工具包
pip install qwen-vl-utils

# 安装Node.js (PTZ控制需要)
# Ubuntu/Debian:
sudo apt update && sudo apt install nodejs npm

# CentOS/RHEL:
sudo yum install nodejs npm

# 或下载安装: https://nodejs.org/
```

### 运行系统

#### 仅视频监控
```bash
# 启动视频监控Web应用
python web_camera_stream.py
# 或
python app.py
```

#### 完整系统 (视频监控 + PTZ控制)
```bash
# 1. 启动Node.js PTZ代理 (新终端)
node ptz_proxy.js

# 2. 启动视频监控 (新终端)
python web_camera_stream.py --rtsp "rtsp://192.168.31.146:8554/unicast"

# 3. 启动PTZ控制界面 (新终端)
python no_root_ptz_controller.py
```

访问地址:
- **视频监控**: http://localhost:5000
- **PTZ控制**: http://localhost:9999

#### 快捷命令行测试
```bash
# Shell脚本快速测试
chmod +x simple_control.sh
./simple_control.sh
```

## ⚙️ 配置说明

### 摄像头配置

编辑 `app.py` 文件第24行，修改摄像头URL：

```python
# RTSP网络摄像头
self.camera_url = "rtsp://192.168.31.146:8554/unicast"

# 或使用本地摄像头
self.camera_url = 0  # 第一个摄像头
self.camera_url = 1  # 第二个摄像头
```

### AI分析配置

可以调整以下参数：

```python
# 分析间隔 (秒)
self.analysis_interval = 10.0

# 显示缩放比例
scale = 0.7  # 在get_frame_as_jpeg函数中

# JPEG质量
[cv2.IMWRITE_JPEG_QUALITY, 85]  # 在get_frame_as_jpeg函数中
```

### PTZ控制配置

编辑 `ptz_proxy.js` 和 `no_root_ptz_controller.py` 中的摄像头设置：

```javascript
// PTZ代理配置
const options = {
    hostname: '192.168.31.146',    // 摄像头IP地址
    port: 443,                     // HTTPS端口
    path: '/ipc/grpc_cmd',         // API路径
    headers: {
        'SessionId': '8E7EB2F6FE2304F134901333A05631A'  // 会话ID
    }
};
```

```python
# Python控制器配置
def __init__(self, camera_ip="192.168.31.146",
             session_id="8E7EB2F6FE2304F134901333A05631A"):
```

**注意**: SessionId需要从浏览器开发者工具中获取最新值

## 📁 项目结构

```
webcam-ai-monitor/
├── README.md                    # 项目说明文档
├── LICENSE                      # MIT许可证
├── requirements.txt             # Python依赖列表
├── .gitignore                  # Git忽略文件
│
├── 📺 视频监控模块
├── web_camera_stream.py        # 主视频监控应用
├── app.py                      # 简化版监控应用
│
├── 🎮 PTZ控制模块
├── no_root_ptz_controller.py   # 主PTZ控制器(Web界面)
├── ptz_proxy.js               # Node.js SSL代理服务器
├── simple_control.sh          # Shell脚本控制器
│
└── 📋 配置和文档
    ├── config.py              # 配置文件
    ├── setup.sh              # 安装脚本
    └── start.sh              # 启动脚本
```

## 🎯 系统架构

### 核心组件

#### 视频监控子系统
1. **Flask Web服务器** - 提供HTTP服务和Web界面
2. **视频捕获线程** - 实时获取摄像头数据
3. **VLM分析线程** - 定期进行AI视觉分析
4. **视频流生成器** - 生成MJPEG视频流
5. **API接口** - 提供状态和分析结果API

#### PTZ控制子系统
1. **Node.js SSL代理** - 解决OpenSSL兼容性问题
2. **Python Web控制器** - 提供PTZ控制Web界面
3. **命令行控制器** - 交互式控制台操作
4. **Shell脚本控制器** - 快速命令行测试

### 工作流程

```
┌─────────────── 视频监控流程 ───────────────┐
│ 摄像头 → 视频捕获 → 帧缓存 → Web流媒体      │
│                 ↓                        │
│             VLM分析 → 结果缓存 → API输出   │
└──────────────────────────────────────────┘

┌─────────────── PTZ控制流程 ───────────────┐
│ Web界面 → Python控制器 → Node.js代理 →    │
│                                ↓         │
│                        HTTPS请求 → 摄像头 │
└──────────────────────────────────────────┘
```

## 🌐 Web界面功能

### 视频监控界面 (端口5000)
- 实时视频流显示
- AI分析结果展示
- 系统状态监控
- 统计信息面板

### PTZ控制界面 (端口9999)
- 方向控制面板 (上下左右)
- 变焦控制 (放大/缩小)
- 一键停止功能
- 自动演示模式
- 键盘快捷键支持 (WASD + 方向键)

### API接口

#### 视频监控API
- `GET /` - 监控主页面
- `GET /video_feed` - MJPEG视频流
- `GET /api/status` - 系统状态JSON

#### PTZ控制API
- `GET /` - PTZ控制主页面
- `GET /ptz/left` - 向左移动
- `GET /ptz/right` - 向右移动
- `GET /ptz/up` - 向上移动
- `GET /ptz/down` - 向下移动
- `GET /ptz/stop` - 停止移动
- `GET /ptz/zoom_in` - 放大
- `GET /ptz/zoom_out` - 缩小

## 🔧 故障排除

### 常见问题

1. **摄像头连接失败**
   ```
   ❌ 检查RTSP地址是否正确
   ❌ 确认摄像头是否在线
   ❌ 尝试降低分辨率或帧率
   ```

2. **VLM模型加载失败**
   ```
   ❌ 确认网络连接正常 (需下载模型)
   ❌ 检查内存是否充足 (推荐8GB+)
   ❌ 检查CUDA环境 (GPU加速可选)
   ```

3. **Web页面无法访问**
   ```
   ❌ 检查5000/9999端口是否被占用
   ❌ 确认防火墙设置
   ❌ 查看控制台错误信息
   ```

4. **PTZ控制失败**
   ```
   ❌ 确认Node.js代理服务器运行正常 (端口8899)
   ❌ 检查摄像头IP地址是否正确
   ❌ 验证SessionId是否有效 (从浏览器开发者工具获取)
   ❌ 确认摄像头支持PTZ控制协议
   ```

5. **SSL连接错误**
   ```
   ❌ 确认Node.js版本 (推荐16+)
   ❌ 检查摄像头SSL证书设置
   ❌ 尝试重启PTZ代理服务
   ```

### 性能优化

- **GPU加速**: 安装CUDA和PyTorch GPU版本
- **内存优化**: 调整队列大小和缓冲区设置
- **网络优化**: 调整JPEG质量和帧缩放
- **分析频率**: 根据需要调整AI分析间隔

## 📊 技术栈

| 组件 | 技术栈 | 版本 |
|------|--------|------|
| Web框架 | Flask | 2.0+ |
| 视觉处理 | OpenCV | 4.x |
| AI模型 | Qwen2-VL-7B-Instruct | Latest |
| 深度学习 | PyTorch | 2.x |
| PTZ代理 | Node.js | 16+ |
| SSL处理 | Node.js HTTPS | - |
| 前端 | HTML5/CSS3/JavaScript | - |
| 视频编码 | MJPEG | - |
| 协议 | RTSP/HTTP/HTTPS | - |

## 🛡️ 安全注意事项

- **网络访问**: 默认绑定所有接口 (0.0.0.0)，生产环境请限制访问
- **数据隐私**: 注意摄像头数据的隐私保护
- **资源管理**: 监控内存和CPU使用情况
- **日志管理**: 定期清理临时文件和日志

## 📈 扩展功能

可以考虑添加的功能：

- [ ] 用户认证和权限管理
- [ ] 多摄像头支持
- [ ] 录像功能
- [ ] 移动检测
- [ ] 人脸识别
- [ ] 报警通知
- [ ] 数据库存储
- [ ] 云端部署支持

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 🐛 [提交Issue](https://github.com/AchermanMks/webcam-ai-monitor/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/AchermanMks/webcam-ai-monitor/discussions)

## 🙏 致谢

- [Qwen2-VL](https://github.com/QwenLM/Qwen2-VL) - 优秀的视觉语言模型
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [Flask](https://flask.palletsprojects.com/) - Python Web框架

---

⭐ 如果这个项目对你有帮助，请给个star支持一下！

**版本**: v1.0.0
**更新时间**: 2026-03-16
**Python兼容性**: 3.8+