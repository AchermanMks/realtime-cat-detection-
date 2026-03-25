# 🎥 实时监控分析系统使用指南

## 📋 系统概述

本项目提供了多种实时监控和AI视觉分析解决方案，支持多摄像头、VLM(视觉语言模型)分析、数据记录和报警功能。

## 🚀 快速开始

### 1. 系统测试
首先运行系统测试，确保所有依赖和硬件正常：
```bash
python3 quick_system_test.py
```

### 2. 启动监控系统
使用启动器选择合适的监控方式：
```bash
python3 launch_monitoring.py
```

## 🔧 监控系统选择

### 1. 🖥️ 桌面版实时监控 (`realtime_camera_display.py`)
**特点：**
- 基于OpenCV的桌面界面
- 实时视频显示+信息叠加
- 支持快捷键操作
- 适合本地监控

**快捷键：**
- `q` - 退出程序
- `s` - 截图保存
- `f` - 全屏切换
- `空格` - 暂停/继续

**启动：**
```bash
python3 realtime_camera_display.py
```

### 2. 🌐 Web版监控界面 (`web_camera_stream.py`)
**特点：**
- 基于Flask的Web界面
- 支持远程访问
- 移动端兼容
- 实时统计图表

**启动：**
```bash
python3 web_camera_stream.py
```
然后访问：http://localhost:5000

### 3. 📊 高级监控仪表板 (`advanced_monitoring_dashboard.py`)
**特点：**
- 完整的GUI仪表板
- SQLite数据库存储
- 智能报警系统
- 统计分析和数据导出
- 历史数据回放

**启动：**
```bash
python3 advanced_monitoring_dashboard.py
```

### 4. 🧪 简单VLM测试 (`simple_camera_vlm.py`)
**特点：**
- 轻量级测试工具
- 快速VLM验证
- 适合开发调试

**启动：**
```bash
python3 simple_camera_vlm.py
```

## ⚙️ 配置说明

### 摄像头配置
默认支持以下摄像头源：
- **RTSP摄像头：** `rtsp://192.168.31.146:8554/unicast`
- **USB摄像头：** 设备ID 0, 1, 2...

### VLM模型配置
- **默认模型：** Qwen2-VL-7B-Instruct
- **设备：** 自动检测CUDA/CPU
- **分析间隔：** 8秒（可调整）

### 报警系统配置
- **关键词检测：** 人、车辆、异常、动作
- **风险级别：** 低/中/高
- **报警冷却：** 30秒

## 🔗 依赖要求

### 核心依赖
- Python 3.8+
- OpenCV (`pip install opencv-python`)
- PyTorch (`pip install torch torchvision torchaudio`)
- Transformers (`pip install transformers`)
- qwen_vl_utils (`pip install qwen_vl_utils`)

### Web界面依赖
- Flask (`pip install flask`)

### 高级功能依赖
- Matplotlib (`pip install matplotlib`)
- Pandas (`pip install pandas`)
- Pillow (`pip install Pillow`)
- NumPy (`pip install numpy`)

### 快速安装
```bash
pip install opencv-python torch transformers qwen_vl_utils flask matplotlib pandas Pillow numpy
```

## 📁 文件说明

```
vlm_test.py/
├── 🚀 监控系统核心
│   ├── realtime_camera_display.py      # 桌面版监控
│   ├── web_camera_stream.py            # Web版监控
│   ├── advanced_monitoring_dashboard.py # 高级仪表板
│   └── simple_camera_vlm.py            # 简单测试
├── 🔧 工具和配置
│   ├── launch_monitoring.py            # 启动器
│   ├── quick_system_test.py           # 系统测试
│   ├── vision_analyzer.py             # 视觉分析器
│   └── robot_vision_config.py         # 配置文件
├── 📋 文档和示例
│   ├── MONITORING_GUIDE.md            # 本指南
│   └── README_ROBOT_VISION.md         # 机器人视觉文档
└── 🗄️ 数据和日志
    ├── monitoring_data.db              # 数据库（运行时生成）
    ├── *.jpg                          # 截图和测试图片
    └── *.txt                          # 系统报告
```

## 🔍 故障排除

### 1. 摄像头连接失败
- 检查摄像头URL是否正确
- 确认网络连接状态
- 尝试其他摄像头设备

### 2. VLM模型加载失败
- 检查网络连接（首次需要下载模型）
- 确认显存/内存充足（建议8GB+）
- 检查CUDA驱动（如使用GPU）

### 3. 依赖包安装失败
- 更新pip：`pip install --upgrade pip`
- 使用国内源：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`
- 单独安装问题包

### 4. 性能问题
- 调整分析间隔（增大间隔值）
- 降低视频分辨率
- 使用CPU模式（如果GPU显存不足）

## 📊 性能参考

### 硬件要求
| 功能 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 基础监控 | 4GB内存 + 2核CPU | 8GB内存 + 4核CPU |
| VLM分析 | 8GB内存 + GTX1060 | 16GB内存 + RTX3060 |
| 多摄像头 | 16GB内存 + RTX3070 | 32GB内存 + RTX4080 |

### 性能指标
- **视频FPS：** 15-30fps（取决于网络和硬件）
- **分析延迟：** 2-8秒（取决于模型和硬件）
- **存储使用：** ~100MB/小时（含图片）

## 🆘 技术支持

### 日志查看
系统运行时会输出详细日志，包含：
- 摄像头连接状态
- VLM分析结果
- 错误和异常信息

### 数据导出
高级仪表板支持导出：
- 分析历史数据（JSON格式）
- 系统统计信息
- 报警记录

### 调试模式
在脚本开头添加调试信息：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔮 未来发展

计划中的功能：
- [ ] 多摄像头同步显示
- [ ] 目标跟踪和轨迹记录
- [ ] 移动端APP
- [ ] 云端部署支持
- [ ] 自定义AI模型训练

---

**最后更新：** 2026-03-16
**版本：** v1.0