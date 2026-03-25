# 📺 RTSP摄像头实时显示指南

本指南说明如何使用不同方式显示RTSP摄像头的实时影像。

## 🎯 可用选项

### 1. **完整Web界面 + AI分析** (推荐)
使用现有的`web_camera_stream.py`，包含AI视觉分析功能。

### 2. **简化RTSP查看器**
专门的轻量级RTSP显示器，支持PTZ控制。

### 3. **快速启动脚本**
一键启动任何模式的便捷工具。

## 🚀 快速开始

### 方法1: 快速启动脚本 (最简单)
```bash
# 交互式设置
python start_rtsp_monitor.py

# 或直接指定摄像头IP
python start_rtsp_monitor.py --ip 192.168.31.146
```

### 方法2: 使用现有完整系统
```bash
# 启动完整Web界面 + AI分析
python web_camera_stream.py --rtsp "rtsp://admin:admin123@192.168.31.146:554/unicast/c1/s1/live"
```

### 方法3: 简化RTSP查看器
```bash
# Web界面模式
python rtsp_viewer.py "rtsp://admin:admin123@192.168.31.146:554/unicast/c1/s1/live"

# OpenCV窗口模式
python rtsp_viewer.py "rtsp://admin:admin123@192.168.31.146:554/unicast/c1/s1/live" --mode opencv

# 带PTZ控制
python rtsp_viewer.py "rtsp://admin:admin123@192.168.31.146:554/unicast/c1/s1/live" --ptz-ip 192.168.31.146
```

## 🎮 PTZ控制集成

### Web界面控制
- 🖱️ **鼠标**: 按住方向按钮控制移动
- ⌨️ **键盘**: W/A/S/D控制方向，Q/E控制缩放，空格停止

### OpenCV窗口控制
- ⌨️ **W**: 向上
- ⌨️ **S**: 向下
- ⌨️ **A**: 向左
- ⌨️ **D**: 向右
- ⌨️ **Q**: 放大
- ⌨️ **E**: 缩小
- ⌨️ **空格**: 停止
- ⌨️ **Q键**: 退出

## 📡 小米摄像头RTSP URL格式

### 常用格式
```bash
# 格式1 (最常用)
rtsp://用户名:密码@IP:554/unicast/c1/s1/live

# 格式2
rtsp://用户名:密码@IP:554/cam/realmonitor?channel=1&subtype=0

# 格式3
rtsp://用户名:密码@IP:554/stream1

# 示例
rtsp://admin:admin123@192.168.31.146:554/unicast/c1/s1/live
```

### 不同流质量
- **主码流**: `c1/s0` (高清)
- **子码流**: `c1/s1` (标清，推荐用于网络传输)

## 🔧 配置选项

### Web界面模式配置
```bash
python start_rtsp_monitor.py \
  --ip 192.168.31.146 \
  --username admin \
  --password admin123 \
  --port 8080
```

### 简单查看器配置
```bash
python rtsp_viewer.py \
  "rtsp://admin:admin123@192.168.31.146:554/unicast/c1/s1/live" \
  --mode web \
  --port 5000 \
  --ptz-ip 192.168.31.146
```

## 🛠️ 故障排除

### RTSP连接问题
1. **测试RTSP连接**
   ```bash
   python start_rtsp_monitor.py --ip 192.168.31.146 --test
   ```

2. **检查网络连接**
   ```bash
   ping 192.168.31.146
   ```

3. **尝试不同RTSP路径**
   - 修改`c1/s1`为`c1/s0` (主码流)
   - 尝试其他路径格式

### 常见错误及解决方案

#### ❌ "无法打开RTSP流"
- 检查IP地址和端口
- 确认用户名密码正确
- 检查摄像头RTSP功能是否开启

#### ❌ "无法读取RTSP帧"
- 尝试降低分辨率 (使用子码流)
- 检查网络带宽
- 尝试不同的OpenCV后端

#### ❌ "PTZ控制无响应"
- 确认PTZ IP地址正确
- 检查摄像头PTZ功能是否开启
- 验证登录凭据

## 📋 功能对比

| 功能 | 完整Web界面 | 简化查看器 | OpenCV窗口 |
|------|------------|-----------|-----------|
| RTSP显示 | ✅ | ✅ | ✅ |
| Web界面 | ✅ | ✅ | ❌ |
| AI分析 | ✅ | ❌ | ❌ |
| PTZ控制 | ❌ | ✅ | ✅ |
| 移动设备 | ✅ | ✅ | ❌ |
| 资源占用 | 高 | 中 | 低 |

## 🎥 支持的摄像头类型

### 已测试
- ✅ **小米摄像头** (Xiaomi Camera)
- ✅ **海康威视** (Hikvision)
- ✅ **大华** (Dahua)

### 理论支持
- 📡 任何支持RTSP协议的IP摄像头
- 🔄 支持标准RTSP/RTP流的设备

## 🌐 Web界面访问

### 本地访问
```
http://localhost:5000
```

### 局域网访问
```
http://您的电脑IP:5000
```

### 移动设备访问
在同一网络下，用手机浏览器访问电脑IP地址。

## 🔒 安全注意事项

1. **网络安全**
   - RTSP流通常未加密
   - 建议在可信网络环境使用
   - 避免在公网暴露RTSP端口

2. **认证安全**
   - 修改默认密码
   - 使用强密码
   - 定期更换认证凭据

3. **访问控制**
   - 限制Web界面访问IP范围
   - 考虑添加Web认证
   - 监控异常访问

## 💡 性能优化建议

### 网络优化
- 使用有线连接而非WiFi
- 确保足够的网络带宽
- 优先使用子码流 (s1) 而非主码流 (s0)

### 系统优化
- 关闭不必要的AI分析功能
- 调整视频编码质量
- 使用适当的缓冲区大小

### 显示优化
- 降低显示分辨率
- 调整帧率设置
- 优化JPEG压缩质量

## 📞 获取帮助

如果遇到问题：
1. 查看控制台错误信息
2. 测试RTSP连接
3. 检查网络连接
4. 验证摄像头设置

---

🎉 **享受您的实时摄像头监控体验！** 📹✨