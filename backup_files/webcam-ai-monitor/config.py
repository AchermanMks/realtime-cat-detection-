"""
配置文件 - Web版智能摄像头监控系统
根据实际环境修改以下配置
"""

# =============================================================================
# 摄像头配置
# =============================================================================

# 摄像头源配置
CAMERA_CONFIGS = {
    # RTSP网络摄像头 (推荐)
    'rtsp': "rtsp://192.168.31.146:8554/unicast",

    # 本地USB摄像头
    'usb_primary': 0,
    'usb_secondary': 1,

    # HTTP摄像头流
    'http': "http://192.168.1.100:8080/video",
}

# 默认使用的摄像头 (从上面选择一个)
DEFAULT_CAMERA = CAMERA_CONFIGS['rtsp']

# 视频参数
VIDEO_CONFIG = {
    'buffer_size': 1,           # OpenCV缓冲区大小
    'fps_target': 30,           # 目标帧率
    'frame_scale': 0.7,         # 显示缩放比例 (0.1-1.0)
    'jpeg_quality': 85,         # JPEG压缩质量 (1-100)
    'connection_timeout': 10,    # 连接超时 (秒)
    'retry_interval': 5,        # 重连间隔 (秒)
}

# =============================================================================
# AI分析配置
# =============================================================================

# VLM模型配置
VLM_CONFIG = {
    'model_id': "Qwen/Qwen2-VL-7B-Instruct",
    'device_map': "auto",       # "auto", "cuda", "cpu"
    'torch_dtype': "auto",      # "auto", "float16", "bfloat16"
    'max_new_tokens': 150,      # 生成文本最大长度
    'analysis_interval': 10.0,  # 分析间隔 (秒)
    'analysis_prompt': "描述图像中的场景和主要内容，回复要简洁清晰，重点突出重要信息。"
}

# 队列配置
QUEUE_CONFIG = {
    'analysis_queue_size': 3,   # 分析队列最大长度
    'frame_queue_size': 10,     # 帧队列最大长度
}

# =============================================================================
# Web服务器配置
# =============================================================================

# Flask配置
FLASK_CONFIG = {
    'host': '0.0.0.0',          # 绑定地址 ('127.0.0.1' 仅本地, '0.0.0.0' 所有接口)
    'port': 5000,               # 端口号
    'debug': False,             # 调试模式
    'threaded': True,           # 多线程模式
}

# Web界面配置
WEB_CONFIG = {
    'page_title': "🎥 实时摄像头监控 + AI分析",
    'update_interval': 2000,    # 前端更新间隔 (毫秒)
    'max_fps_display': 60,      # 最大显示FPS
}

# =============================================================================
# 存储和日志配置
# =============================================================================

# 文件路径配置
PATHS = {
    'temp_dir': '/tmp',                    # 临时文件目录
    'logs_dir': './logs',                  # 日志目录
    'captures_dir': './captures',          # 截图保存目录
    'temp_frame_path': '/tmp/web_frame.jpg'  # 临时帧文件路径
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',            # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_logging': True,       # 是否记录到文件
    'console_logging': True,    # 是否输出到控制台
    'max_log_size': '10MB',     # 单个日志文件最大大小
    'backup_count': 5,          # 保留的日志文件数量
}

# =============================================================================
# 性能和优化配置
# =============================================================================

# 性能配置
PERFORMANCE = {
    'enable_gpu': True,         # 启用GPU加速 (如果可用)
    'memory_fraction': 0.8,     # GPU内存使用比例
    'worker_threads': 2,        # 工作线程数
    'enable_caching': True,     # 启用结果缓存
    'cache_ttl': 300,          # 缓存生存时间 (秒)
}

# 监控配置
MONITORING = {
    'enable_metrics': True,     # 启用性能监控
    'metrics_interval': 60,     # 性能统计间隔 (秒)
    'alert_thresholds': {
        'cpu_percent': 80,      # CPU使用率警告阈值
        'memory_percent': 85,   # 内存使用率警告阈值
        'disk_percent': 90,     # 磁盘使用率警告阈值
        'fps_minimum': 5,       # 最低FPS警告阈值
    }
}

# =============================================================================
# 安全和访问控制
# =============================================================================

# 安全配置
SECURITY = {
    'enable_auth': False,       # 启用认证 (TODO: 实现)
    'secret_key': 'your-secret-key-here',  # Flask会话密钥
    'session_timeout': 3600,    # 会话超时 (秒)
    'rate_limit': {
        'enabled': False,       # 启用速率限制
        'requests_per_minute': 60,
    }
}

# CORS配置
CORS_CONFIG = {
    'enabled': False,           # 启用跨域支持
    'origins': '*',             # 允许的源
    'methods': ['GET', 'POST'], # 允许的方法
}

# =============================================================================
# 开发和调试配置
# =============================================================================

# 开发模式配置
DEVELOPMENT = {
    'fake_camera': False,       # 使用虚拟摄像头 (开发测试用)
    'mock_analysis': False,     # 使用模拟分析结果
    'profile_performance': False, # 性能分析
    'save_debug_frames': False, # 保存调试帧
}

# 测试配置
TESTING = {
    'test_mode': False,         # 测试模式
    'test_duration': 60,        # 测试持续时间 (秒)
    'test_output_dir': './test_output',  # 测试输出目录
}

# =============================================================================
# 运行时配置检查
# =============================================================================

def validate_config():
    """验证配置有效性"""
    import os

    # 检查必要目录
    for path_key, path_value in PATHS.items():
        if not os.path.exists(os.path.dirname(path_value)):
            try:
                os.makedirs(os.path.dirname(path_value), exist_ok=True)
                print(f"✅ 创建目录: {os.path.dirname(path_value)}")
            except Exception as e:
                print(f"❌ 无法创建目录 {path_value}: {e}")

    # 检查端口可用性
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((FLASK_CONFIG['host'], FLASK_CONFIG['port']))
    sock.close()
    if result == 0:
        print(f"⚠️ 警告: 端口 {FLASK_CONFIG['port']} 已被占用")

    print("✅ 配置验证完成")

if __name__ == "__main__":
    validate_config()