# 机器人视觉系统配置文件
import os

class Config:
    # RTSP相关配置 - 真实摄像头
    RTSP_URL = "rtsp://192.168.31.146:8554/unicast"  # 你的小米摄像头
    RTSP_TIMEOUT = 30  # 连接超时时间(秒)
    FRAME_WIDTH = 1920  # 视频宽度
    FRAME_HEIGHT = 1080  # 视频高度
    FPS = 15  # 目标帧率

    # 云台控制配置
    PTZ_BASE_URL = "http://192.168.31.146"  # 你的摄像头IP
    PTZ_USERNAME = "admin"
    PTZ_PASSWORD = "admin"
    PTZ_PORT = 80

    # 云台移动参数
    PAN_SPEED = 50    # 水平移动速度 (1-100)
    TILT_SPEED = 50   # 垂直移动速度 (1-100)
    ZOOM_SPEED = 50   # 缩放速度 (1-100)

    # VLM模型配置
    MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"
    DEVICE_MAP = "auto"
    TORCH_DTYPE = "auto"

    # 视觉识别配置
    ANALYSIS_INTERVAL = 3.0  # 视觉分析间隔(秒) - 真实摄像头可以更频繁
    CONFIDENCE_THRESHOLD = 0.8  # 置信度阈值
    MAX_OBJECTS_TRACK = 10  # 最大跟踪对象数

    # 控制策略配置
    AUTO_TRACKING = False  # 小米摄像头不支持PTZ，暂时关闭
    TRACK_PRIORITY = ["person", "car", "bicycle", "motorcycle"]  # 跟踪优先级

    # 日志和存储
    LOG_LEVEL = "INFO"
    SAVE_FRAMES = False  # 是否保存关键帧
    SAVE_PATH = "./captured_frames/"

    # 性能优化
    USE_THREADING = True
    BUFFER_SIZE = 30
    SKIP_FRAMES = 1  # 跳帧处理，减少计算负载

    @classmethod
    def validate(cls):
        """验证配置参数"""
        if cls.SAVE_FRAMES and not os.path.exists(cls.SAVE_PATH):
            os.makedirs(cls.SAVE_PATH)

        # 可以添加更多验证逻辑
        print("配置验证完成")