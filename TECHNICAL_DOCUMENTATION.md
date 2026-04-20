# 实时AI宠物监控系统 - 技术文档

> 基于 YOLOv11x + TensorRT + ByteTrack + Qwen3-VL + Open3D 的端到端实时宠物检测与3D空间追踪系统

---

## 目录

- [1. 系统架构总览](#1-系统架构总览)
- [2. 核心模型与原理](#2-核心模型与原理)
  - [2.1 目标检测：YOLOv11x + TensorRT](#21-目标检测yolov11x--tensorrt)
  - [2.2 多目标跟踪：ByteTrack](#22-多目标跟踪bytetrack)
  - [2.3 视觉语言模型：Qwen3-VL-8B-Instruct](#23-视觉语言模型qwen3-vl-8b-instruct)
  - [2.4 3D空间定位：单应矩阵 + 深度估算](#24-3d空间定位单应矩阵--深度估算)
  - [2.5 3D渲染：Open3D + USD场景模型](#25-3d渲染open3d--usd场景模型)
- [3. 信息流与数据管线](#3-信息流与数据管线)
- [4. 多线程架构](#4-多线程架构)
- [5. 检测管线详解](#5-检测管线详解)
  - [5.1 双阈值检测策略](#51-双阈值检测策略)
  - [5.2 质量评分过滤](#52-质量评分过滤)
  - [5.3 帧去重机制](#53-帧去重机制)
- [6. 3D追踪与可视化](#6-3d追踪与可视化)
  - [6.1 坐标系定义](#61-坐标系定义)
  - [6.2 EMA坐标平滑](#62-ema坐标平滑)
  - [6.3 Open3D渲染管线](#63-open3d渲染管线)
- [7. 视频流优化](#7-视频流优化)
- [8. Web前端与用户交互](#8-web前端与用户交互)
  - [8.1 页面布局](#81-页面布局)
  - [8.2 API接口](#82-api接口)
  - [8.3 交互逻辑](#83-交互逻辑)
- [9. 关键优化手段](#9-关键优化手段)
- [10. 训练与微调管线](#10-训练与微调管线)
- [11. 部署与运维](#11-部署与运维)
- [12. 文件结构](#12-文件结构)
- [13. 配置参数速查](#13-配置参数速查)

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Browser (用户)                        │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│   │ 视频流   │ │ 实时数据 │ │ AI分析   │ │ 3D空间追踪      │  │
│   │ /video   │ │ /api/det │ │ /api/vlm │ │ /api/3d_viz     │  │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────────────┘  │
│        │ MJPEG      │ JSON       │ JSON       │ PNG            │
└────────┼────────────┼────────────┼────────────┼────────────────┘
         │            │            │            │
┌────────┴────────────┴────────────┴────────────┴────────────────┐
│                    Flask Web Server (端口5008)                   │
│                      threaded=True                              │
└────────┬────────────────────────────────────────────────────────┘
         │
┌────────┴────────────────────────────────────────────────────────┐
│              RealtimePetMonitor 核心引擎                         │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐ │
│  │ 视频解码线程 │  │ 异步检测线程 │  │ VLM线程  │  │ Open3D    │ │
│  │ (主请求线程) │  │ (后台守护)   │  │ (按需)   │  │ 渲染线程  │ │
│  │             │  │             │  │          │  │           │ │
│  │ cap.read()  │→│ YOLO.track()│  │ Qwen3-VL │  │ 离屏渲染  │ │
│  │ bbox绘制   │  │ ByteTrack   │  │ generate │  │ USD模型   │ │
│  │ JPEG编码   │  │ 质量过滤    │  │          │  │ 球体+投影 │ │
│  └─────────────┘  └──────┬──────┘  └──────────┘  └───────────┘ │
│                          │                                       │
│  ┌───────────────────────┴──────────────────────────────────┐   │
│  │            共享状态 (线程锁保护)                           │   │
│  │  latest_detections_async / detection_history /            │   │
│  │  track_bbox_history / vlm_analysis / track_trajectory     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
         │
┌────────┴────────────────────────────────────────────────────────┐
│                      硬件层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐       │
│  │ GPU (CUDA)   │  │ TensorRT     │  │ OpenGL/EGL      │       │
│  │ YOLO推理     │  │ FP16加速     │  │ Open3D离屏      │       │
│  │ VLM推理      │  │ yolo11x.engine│ │ 渲染            │       │
│  └──────────────┘  └──────────────┘  └─────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心模型与原理

### 2.1 目标检测：YOLOv11x + TensorRT

**模型**：`yolo11x.engine`（TensorRT FP16 量化）

**原理**：YOLO (You Only Look Once) 是单阶段目标检测网络，将检测任务转化为回归问题，在单次前向传播中同时预测边界框坐标和类别概率。YOLOv11x 是 Ultralytics 最新的大规模变体，backbone 采用 C3k2 + SPPF 结构，neck 采用 PAN-FPN 多尺度特征融合。

**TensorRT 加速**：将 PyTorch 模型导出为 NVIDIA TensorRT 引擎，通过以下手段加速：
- FP16 半精度推理：精度损失可忽略，吞吐量翻倍
- 层融合：将 Conv + BN + ReLU 等连续操作合并为单个 kernel
- Tensor Core 利用：在 Ampere/Ada GPU 上启用硬件加速矩阵运算

**类别映射**：
- COCO 原模型：class 15 = 猫，class 16 = 狗
- 微调模型（可选）：class 0 = 猫（单类）

**推理参数**：
| 参数 | 值 | 说明 |
|------|-----|------|
| `imgsz` | 960 | 主推理分辨率，比1280快~1.7×，精度基本不变 |
| `conf` (猫) | 0.30 | COCO猫类精度较高，适度阈值平衡漏检与误检 |
| `conf` (狗) | 0.40 | 狗在COCO易被误判为猫/熊，需更严阈值 |
| `iou` | 0.5 | NMS IoU阈值 |

### 2.2 多目标跟踪：ByteTrack

**原理**：ByteTrack 是一种基于运动预测的在线多目标跟踪算法，核心创新在于**充分利用低分检测框**：
1. 第一轮关联：将高分检测框与已有轨迹通过 IoU 矩阵匹配（Hungarian算法）
2. 第二轮关联：将未匹配的低分检测框与剩余轨迹做二次匹配
3. 新轨迹初始化：连续出现的未匹配高分框创建新轨迹

**配置**（`bytetrack.yaml`）：
```yaml
tracker_type: botsort
track_high_thresh: 0.25    # 高分检测阈值
track_low_thresh: 0.1      # 低分检测阈值
track_buffer: 60           # 轨迹最大丢失帧数
match_thresh: 0.8          # IoU匹配阈值
with_reid: False           # 禁用ReID避免bfloat16冲突
```

**`persist=True`**：跨帧保持跟踪器状态，使同一目标的 `track_id` 在整个视频中保持一致。

### 2.3 视觉语言模型：Qwen3-VL-8B-Instruct

**模型**：`Qwen/Qwen3-VL-8B-Instruct`（通义千问 VL 第三代，80亿参数）

**原理**：Qwen3-VL 是多模态大语言模型，架构包含：
- **视觉编码器**：ViT (Vision Transformer) 将图像切分为 patch 并编码为 token 序列
- **跨模态对齐层**：将视觉 token 与文本 token 对齐到统一语义空间
- **语言解码器**：基于 Transformer 的自回归文本生成

**应用方式**：
- 每 30 帧触发一次（~1秒间隔）
- 异步执行：在独立线程中运行，不阻塞视频流
- 输入：当前帧 RGB 图像 + 中文提示词
- 输出：一句话场景描述（max 128 tokens，贪心解码）

**提示词**：
```
简要描述场景和宠物行为，用中文，一句话。
```

**推理配置**：
| 参数 | 值 |
|------|-----|
| `torch_dtype` | bfloat16 |
| `device_map` | auto |
| `max_new_tokens` | 128 |
| `do_sample` | False（贪心解码，结果确定性） |

### 2.4 3D空间定位：单应矩阵 + 深度估算

**单应矩阵 (Homography)**

将 2D 像素坐标映射到物理平面坐标的 3×3 透视变换矩阵。通过 6 个地面控制点标定：

| 控制点 | 像素坐标 | 物理坐标 (m) |
|--------|----------|-------------|
| 左下角（原点） | [128, 648] | (0.0, 0.0) |
| 右下角 | [1152, 648] | (4.0, 0.0) |
| 右上角 | [1152, 216] | (4.0, 3.0) |
| 左上角 | [128, 216] | (0.0, 3.0) |
| 房间中心 | [640, 432] | (2.0, 1.5) |
| 辅助点 | [384, 503] | (1.2, 0.8) |

变换公式：`cv2.perspectiveTransform(pixel_point, H)` → `(X_meters, Y_meters)`

**Z轴深度估算**

由于单目摄像头无法直接获取深度，Z轴通过多因素启发式估算：
1. **垂直位置**：画面上方 → 高处（近似透视关系）
2. **检测框面积**：大框 → 离地面近或体型大，增加0.2m修正
3. **边缘距离**：靠近画面边缘略微修正
4. **范围钳位**：最终结果限制在 [0.0, 2.5] 米

### 2.5 3D渲染：Open3D + USD场景模型

**USD 模型**：`scan.usd` 是房间的3D扫描模型（LiDAR/摄影测量），包含 20 个语义分类网格：墙壁、地板、门、窗、椅子、桌子、电视等。

**Open3D 离屏渲染**：
- 720×540 分辨率
- EGL headless 模式（无需显示器）
- 语义着色方案：

| 类别 | RGB 颜色 | 渲染方式 |
|------|----------|---------|
| Wall | (0.65, 0.65, 0.70) | 线框 LineSet |
| Floor | (0.40, 0.36, 0.30) | 线框 LineSet |
| Window | (0.45, 0.75, 0.95) | 线框 LineSet |
| Door | (0.90, 0.55, 0.30) | 实体 defaultLit |
| Chair | (0.95, 0.55, 0.55) | 实体 defaultLit |
| Table | (0.60, 0.45, 0.30) | 实体 defaultLit |
| Television | (0.18, 0.18, 0.20) | 实体 defaultLit |

---

## 3. 信息流与数据管线

```
视频帧 (real_cat.mp4, 1280×720, 30fps)
    │
    ├──→ [视频线程] get_next_frame()
    │       │
    │       ├──→ latest_raw_frame (共享变量，供检测线程读取)
    │       │
    │       ├──→ 每30帧 → [VLM线程] analyze_frame_vlm()
    │       │                  │
    │       │                  └──→ vlm_analysis {"scene": "...", "behavior": "..."}
    │       │
    │       └──→ get_display_detections() → bbox外推 → 绘制方框 → JPEG编码 → MJPEG流
    │
    └──→ [检测线程] _multi_threshold_detection()
            │
            ├──→ YOLO.track(conf=0.30, imgsz=960, ByteTrack)
            │       │
            │       └──→ _extract_detections() → 类别过滤 → 狗阈值(0.40)
            │                                   → 面积/宽高比过滤
            │                                   → quality_score > 0.55
            │
            ├──→ [兜底] 连续3帧无猫 → YOLO(conf=0.20, imgsz=1920, TTA)
            │
            ├──→ _update_3d_state() → EMA平滑 → track_trajectory累积
            │
            ├──→ latest_detections_async (线程锁保护)
            │
            ├──→ recent_detections (最近20条)
            │
            └──→ detection_history (最近30条) → 供3D渲染使用
```

**每个检测结果的数据结构**：
```python
{
    'class': '猫' | '狗',
    'confidence': 0.85,
    'bbox': [x1, y1, x2, y2],          # 像素坐标
    'center': [cx, cy],                  # 像素中心
    'physical_coords': {'x': 2.06, 'y': 2.42, 'z': 0.39},  # 米
    'area': 8853.0,
    'aspect_ratio': 0.82,
    'track_id': 23,                      # ByteTrack分配
    'detection_type': 'track' | 'secondary',
    'quality_score': 1.29,
    'ts': 1776326498.20                  # 时间戳
}
```

---

## 4. 多线程架构

系统使用 4 个线程协同工作：

| 线程 | 类型 | 职责 | 阻塞关系 |
|------|------|------|---------|
| **Flask 请求线程** | 主线程 | 视频解码、JPEG编码、HTTP响应 | 被 cap.read() 和 imencode 阻塞 |
| **检测 Worker** | daemon 线程 | YOLO推理 + ByteTrack跟踪 | 独立运行，通过共享变量通信 |
| **VLM 分析** | daemon 线程（按需） | Qwen3-VL 场景分析 | 独立运行，`_vlm_running` 标志防重入 |
| **Open3D 渲染** | daemon 线程 | 3D场景离屏渲染 | 请求-响应队列模式 |

**线程安全机制**：
- `latest_detections_lock`：`threading.Lock`，保护 `latest_detections_async` 的读写
- `_o3d_req_q`：`queue.Queue`，Open3D 渲染请求队列
- `_vlm_running`：布尔标志，防止 VLM 重复触发
- `_last_detected_frame_id`：帧号去重，防止同一帧被重复检测

**bfloat16 兼容性**：系统在导入时全局 monkey-patch `torch.Tensor.numpy` 和 `__array__`，自动将 bfloat16 张量转换为 float32，解决 VLM（使用 bfloat16）与 ByteTrack（调用 `.numpy()`）并发运行时的类型冲突。

---

## 5. 检测管线详解

### 5.1 双阈值检测策略

```
每一帧
    │
    ├──→ 主检测：YOLO.track(conf=0.30, imgsz=960, ByteTrack)
    │       └──→ 检测结果（含 track_id）
    │
    └──→ 连续3帧无猫 且 距上次兜底≥10帧？
            │
            是 → 兜底检测：YOLO(conf=0.20, imgsz=1920, TTA)
            │       └──→ 补充结果（无 track_id）
            │
            否 → 跳过
```

**TTA (Test-Time Augmentation)**：在推理时对输入做水平翻转 + 多尺度变换，综合多个预测结果，提高小目标和边缘目标的召回率。代价是推理速度降低 2-3 倍。

**节流控制**：
- `secondary_interval = 10`：兜底最多每 10 帧触发一次
- `secondary_miss_streak_min = 3`：至少连续 3 帧无猫才触发

### 5.2 质量评分过滤

每个检测经过多维质量评估，总分需 > 0.55 才保留：

```
quality_score = conf_score × 1.0    # 置信度（归一化到0.5，避免低conf饱和）
              + area_score × 0.3    # 面积（最佳区间2000-8000像素）
              + ratio_score × 0.2   # 宽高比（最佳0.8-1.5）
              + position_score × 0.1 # 位置（边缘区域降权）
```

**面积评分**：
| 面积 (px²) | 得分 |
|------------|------|
| 2000-8000 | 1.0 |
| 1000-15000 | 0.7 |
| 其他 | 0.3 |

**位置评分**：距离画面边缘 > 8% 宽度 / 7% 高度得 1.0，否则 0.5。

### 5.3 帧去重机制

异步检测线程可能比视频帧率快，导致同一帧被重复处理。通过 `frame_count` 做去重：

```python
current_fid = self.frame_count
if current_fid == self._last_detected_frame_id:
    time.sleep(0.003)
    continue
self._last_detected_frame_id = current_fid
```

效果：det/frame 比从 1.9 降到 0.04，消除了计数膨胀和 track_id 频繁刷新。

---

## 6. 3D追踪与可视化

### 6.1 坐标系定义

```
        Y (深度, 0→3m)
        ↑
        │      房间 4m × 3m
        │   ┌──────────────┐
        │   │              │
  3.0m  │   │    房间内部   │
        │   │              │
        │   │              │
  0.0m  └───┼──────────────┼──→ X (宽度, 0→4m)
            0.0m          4.0m

  Z轴：垂直高度 (0→2.5m)
  原点：房间左下角 [像素坐标 (128, 648)]
```

### 6.2 EMA坐标平滑

对每个 track_id 独立做指数移动平均，消除帧间抖动：

```
smoothed = α × raw + (1-α) × prev_smoothed
α = 0.4  (响应性与稳定性的平衡)
```

平滑后的坐标累积到 `track_trajectory[tid]`（最多保留 30 个点），供 3D 可视化使用。

### 6.3 Open3D渲染管线

```
主线程                          Open3D渲染线程
   │                                  │
   │ 1. 从detection_history           │
   │    提取最新猫/狗位置              │
   │                                  │
   │ 2. put(cat_pos, dog_pos,         │
   │        azim, elev) ──────────→   │ 3. 清旧几何
   │                                  │ 4. 创建球体(猫绿/狗青, r=0.12m)
   │                                  │ 5. 创建投影线(球体→地面)
   │                                  │ 6. render_to_image()
   │                                  │ 7. cv2叠加文字标注
   │ 8. ←─────────────── base64 PNG   │
   │                                  │
   │ 9. 返回给前端                    │
```

**文字叠加**：
- 右上：视角信息 `View az=45 el=25`
- 左上：房间尺寸 `Room 5.03 x 5.01 m`
- 左下：宠物坐标（猫绿色、狗青色分行显示）
  ```
  Cat position (m)
  X=+2.06  Y=+2.42  Z=+0.39
  Dog position (m)
  X=+1.33  Y=+1.80  Z=+0.12
  ```

---

## 7. 视频流优化

从 17 FPS 优化到 27 FPS（+58%），三个关键措施：

### 7.1 VLM异步化

**改前**：`get_next_frame()` 中同步调用 `analyze_frame_vlm()`，每 30 帧阻塞视频线程 1-5 秒。

**改后**：通过 `_vlm_running` 标志 + `threading.Thread` 将 VLM 推理移到独立线程：
```python
if not self._vlm_running:
    self._vlm_running = True
    threading.Thread(target=self._vlm_analyze_async, args=(frame.copy(),), daemon=True).start()
```

### 7.2 JPEG编码优化

- 移除 `IMWRITE_JPEG_OPTIMIZE`（Huffman 优化带来 ~30% 编码耗时，肉眼无差）
- 质量从 85 降到 80

### 7.3 流分辨率缩小

检测使用原始 1280×720 帧，MJPEG 流输出缩至 960×540：
```python
stream_frame = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_LINEAR)
```
编码像素量减少 44%，传输带宽同步降低。

---

## 8. Web前端与用户交互

### 8.1 页面布局

4 列 CSS Grid 布局，Apple 风格深色设计：

```
┌─────────────────────────────────────────────────────────────┐
│  🐾 Pet Monitor Pro          🟢 运行中   🐱1只猫 🐶1只狗   │  ← 顶部导航栏
├──────────┬──────────┬──────────┬─────────────────────────────┤
│          │          │          │                             │
│ 🎬 实时  │ 📊 实时  │ 🧠 AI    │ 🏠 3D空间追踪              │
│ 视频检测 │ 数据     │ 智能分析 │                             │
│          │          │          │                             │
│ [MJPEG]  │ 🐱 猫: 1 │ 场景:    │ [Open3D渲染]               │
│          │ 🐶 狗: 0 │ 猫在沙   │                             │
│ CAT#23   │ 帧: 1234 │ 发上休   │ Cat: X=+2.06 Y=+2.42      │
│ ┌──────┐ │ 置信度:  │ 息       │                             │
│ │ 猫   │ │ 0.854   │          │ 可拖拽旋转视角              │
│ └──────┘ │          │ 行为:    │ 双击重置                    │
│          │          │ 分析中   │                             │
├──────────┴──────────┴──────────┴─────────────────────────────┤
│  响应式：1200px 以下 2×2，768px 以下单列                      │
└─────────────────────────────────────────────────────────────┘
```

**样式特点**：
- 纯黑背景 + 径向渐变高光
- `backdrop-filter: blur(20px)` 毛玻璃效果
- SF Pro 字体栈
- 绿色（猫）/ 青色（狗）强调色
- 顶部导航栏绿色脉冲呼吸灯指示运行状态

### 8.2 API接口

| 路由 | 方法 | 返回格式 | 功能 | 刷新频率 |
|------|------|---------|------|---------|
| `/` | GET | HTML | 完整单页应用 | - |
| `/video_feed` | GET | MJPEG stream | 实时视频流 + 检测框叠加 | ~27fps |
| `/api/stats` | GET | JSON | 实时统计（猫狗数量、帧数等） | 1s |
| `/api/detections` | GET | JSON | 最近5条检测 + 置信度 | 1s |
| `/api/vlm_analysis` | GET | JSON | VLM场景分析文本 | 1s |
| `/api/3d_visualization` | GET | PNG | 3D渲染图（支持 azim/elev 参数） | 400ms |

### 8.3 交互逻辑

**实时数据同步**：
- `unique_cats` / `unique_dogs` 从 `get_display_detections()` 计数，与视频方框使用**同一数据源**
- 方框在（靠 bbox 外推 0.3s 保持期）→ 数字在；方框消失 → 数字归零

**3D视角控制**：
- 鼠标拖拽：调整方位角（azim）和仰角（elev）
- 双击：重置到默认视角 45°/25°
- 自动刷新间隔：400ms

**显示外推**：
```
get_display_detections()
  └──→ 对每个有 track_id 的检测：
        1. 从 bbox_history 取最近两帧位置
        2. 计算速度向量
        3. 线性外推到当前时刻（最大步长 0.15s）
        4. 超过 0.30s 未更新 → 丢弃（防鬼影）
```

---

## 9. 关键优化手段

| 优化项 | 方法 | 效果 |
|--------|------|------|
| **TensorRT FP16** | 模型导出为 engine，FP16 量化 + 层融合 | 推理速度 ~2× |
| **异步检测解耦** | 视频流与 AI 推理在不同线程 | 视频不卡顿 |
| **VLM 异步化** | 独立线程 + 防重入标志 | 消除周期性冻结 |
| **帧去重** | frame_count 比对 | 计数正确 + 节省 GPU |
| **JPEG 编码优化** | 去 OPTIMIZE + 降分辨率 | 编码速度 +44% |
| **bbox 外推** | 线性速度预测 | 框"粘"在目标上 |
| **EMA 坐标平滑** | α=0.4 指数滑动平均 | 3D 轨迹无抖动 |
| **TTA 节流** | miss_streak + interval 控制 | 兜底不拖累 FPS |
| **Open3D 专属线程** | 请求队列 + 离屏渲染 | 渲染不阻塞主线程 |
| **3D 渲染缓存** | 0.3s 最小间隔 + key 缓存 | 避免重复渲染 |
| **bfloat16 兼容** | numpy 全局 monkey-patch | VLM + YOLO 安全并发 |

---

## 10. 训练与微调管线

系统提供完整的 YOLO 微调工具链：

```
real_cat.mp4
    │
    ├──→ pseudo_label.py
    │       │ 每10帧采样
    │       │ yolo11x.pt 自动标注
    │       │
    │       ├──→ dataset_cat/images_raw/   (conf ≥ 0.5, 自动通过)
    │       ├──→ dataset_cat/review/       (conf 0.30-0.50, 需人工审核)
    │       └──→ dataset_cat/negatives/    (无检测帧, 负样本)
    │
    ├──→ review_tool.py
    │       │ OpenCV 交互界面
    │       │ 按键 y(通过) / n(拒绝) / b(回退) / q(退出)
    │       │
    │       └──→ 审核通过的样本合并到训练集
    │
    ├──→ prepare_and_train.py
    │       │ 80/20 train/val 划分 (seed=42)
    │       │ 生成 dataset.yaml
    │       │ Ultralytics fine-tune on yolo11x.pt
    │       │
    │       └──→ runs/detect/cat_finetune/v1/weights/best.pt
    │
    └──→ export_finetuned.py
            │ TensorRT FP16 导出
            │ imgsz=960, workspace=4GB
            │
            └──→ yolo11x_cat.engine
```

---

## 11. 部署与运维

### 启动方式

**直接启动**：
```bash
python -u realtime_pet_monitor.py [--video FILE] [--host HOST] [--port PORT]
```

**守护模式**（推荐）：
```bash
./run_monitor.sh
```
守护脚本特性：
- 崩溃自动重启（延迟 5 秒）
- 频率限制：每分钟最多重启 4 次，超限等待 60 秒
- 日志追加到 `monitor.log`，每次重启标记 `=== restart #N ===`
- `Ctrl+C` 优雅退出，自动清理子进程

### 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 运行时 |
| PyTorch | ≥ 2.0 | 深度学习框架 |
| Ultralytics | ≥ 8.0 | YOLO 推理与训练 |
| Transformers | ≥ 4.35 | Qwen3-VL 模型加载 |
| OpenCV | ≥ 4.8 | 视频处理与图像编码 |
| Flask | ≥ 2.3 | Web 服务器 |
| Open3D | (可选) | 3D 离屏渲染 |
| pxr (USD) | (可选) | USD 3D 模型加载 |
| CUDA | 11.0+ | GPU 加速 |
| TensorRT | (推荐) | FP16 推理加速 |

### GPU 显存需求

| 组件 | 显存估算 |
|------|---------|
| YOLOv11x TensorRT FP16 | ~2 GB |
| Qwen3-VL-8B bfloat16 | ~10 GB |
| Open3D 离屏渲染 | ~0.5 GB |
| 系统开销 | ~1 GB |
| **合计** | **~14 GB** |

---

## 12. 文件结构

```
realtime-cat-detection/
├── realtime_pet_monitor.py          # 主系统（2284行）
├── run_monitor.sh                   # 守护启动脚本
├── requirements.txt                 # Python 依赖
│
├── # 模型文件（.gitignore 排除）
├── yolo11x.engine                   # TensorRT FP16 引擎（生产用）
├── yolo11x.pt                       # PyTorch 权重（备用）
├── scan.usd                         # 房间3D扫描模型
│
├── # 标定数据
├── meeting_room_calibration_*.json  # 单应矩阵 + 控制点
├── step3_output_*/room_data.json    # 房间边界与物体信息
├── botsort_reid.yaml                # ByteTrack 跟踪器配置
│
├── # 训练工具链
├── pseudo_label.py                  # 伪标签生成
├── review_tool.py                   # 人工审核工具
├── prepare_and_train.py             # 数据集准备与训练
├── export_finetuned.py              # TensorRT 导出
│
├── # 辅助工具
├── view_usd.py                      # USD 3D模型查看器
├── diagnose_cat_detection.py        # 检测诊断
├── find_cats_in_video.py            # 视频帧扫描
│
├── # 文档
├── README.md                        # 项目说明
├── TECHNICAL_DOCUMENTATION.md       # 本文档
└── PROJECT_DOCUMENTATION.md         # 项目概况
```

---

## 13. 配置参数速查

### 检测参数

| 参数 | 默认值 | 位置 | 说明 |
|------|--------|------|------|
| `primary_cat_threshold` | 0.30 | `__init__` | 主检测置信度阈值 |
| `secondary_cat_threshold` | 0.20 | `__init__` | 兜底 TTA 阈值 |
| `dog_detection_threshold` | 0.40 | `__init__` | 狗类阈值（防误判） |
| `infer_imgsz` | 960 | `__init__` | 主推理分辨率 |
| `secondary_interval` | 10 | `__init__` | TTA 最小间隔帧数 |
| `secondary_miss_streak_min` | 3 | `__init__` | 触发 TTA 最小无猫帧数 |
| `min_area` / `max_area` | 200 / 50000 | `__init__` | bbox 面积过滤 |
| `quality_score 阈值` | 0.55 | `_extract_detections` | 质量分最低分 |

### 追踪与平滑参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `track_active_window` | 60 帧 | 活跃轨迹判定窗口 |
| `coord_ema_alpha` | 0.4 | 坐标平滑系数（越大越灵敏） |
| `trajectory_max_len` | 30 | 每条轨迹最多保留点数 |
| `extrapolation_max_age` | 0.30s | 检测结果最大保持时间 |
| `extrapolation_max_step` | 0.15s | bbox 外推最大步长 |

### 显示与流参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target_fps` | 30 | 视频流目标帧率 |
| `vlm_analysis_interval` | 30 帧 | VLM 分析间隔 |
| `min_3d_viz_interval` | 0.3s | 3D 渲染最小间隔 |
| JPEG quality | 80 | MJPEG 编码质量 |
| 流分辨率 | 960×540 | MJPEG 输出尺寸 |

---

*文档版本：2026-04-17 | 对应提交：6431c5f*
