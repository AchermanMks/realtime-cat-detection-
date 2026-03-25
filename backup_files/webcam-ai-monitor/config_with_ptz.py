"""
配置文件 - Web版智能摄像头监控系统 + PTZ云台控制
根据实际环境修改以下配置
"""

# =============================================================================
# 摄像头配置
# =============================================================================

# 摄像头源配置
CAMERA_CONFIGS = {
    # RTSP网络摄像头 (推荐，支持PTZ控制)
    'rtsp': "rtsp://192.168.31.146:8554/unicast",

    # 本地USB摄像头 (不支持PTZ控制)
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
# PTZ云台控制配置
# =============================================================================

# PTZ基本配置
PTZ_CONFIG = {
    'enabled': True,                    # 启用PTZ控制
    'camera_ip': '192.168.31.146',     # 摄像头IP地址 (自动从RTSP URL提取)
    'username': 'admin',                # 登录用户名
    'password': 'admin',                # 登录密码
    'protocol': 'auto',                 # 协议类型: auto, onvif, hikvision, dahua, generic
    'connection_timeout': 3,            # 连接超时 (秒)
    'command_timeout': 5,               # 命令超时 (秒)
    'auto_stop_delay': 100,            # 自动停止延迟 (毫秒)
}

# PTZ速度配置
PTZ_SPEEDS = {
    'pan_speed': 50,        # 水平转动速度 (1-100)
    'tilt_speed': 50,       # 垂直转动速度 (1-100)
    'zoom_speed': 50,       # 变焦速度 (1-100)
    'default_speed': 50,    # 默认速度
    'min_speed': 1,         # 最小速度
    'max_speed': 100,       # 最大速度
}

# PTZ预设位置配置
PTZ_PRESETS = {
    1: {
        'name': '正门入口',
        'description': '监控正门人员进出',
        'pan': 0,
        'tilt': 0,
        'zoom': 1
    },
    2: {
        'name': '大厅中央',
        'description': '大厅全景监控',
        'pan': 90,
        'tilt': -15,
        'zoom': 1
    },
    3: {
        'name': '侧门出口',
        'description': '侧门区域监控',
        'pan': 180,
        'tilt': 0,
        'zoom': 2
    },
    4: {
        'name': '停车场',
        'description': '停车场监控',
        'pan': 270,
        'tilt': 15,
        'zoom': 1
    },
    5: {
        'name': '后门区域',
        'description': '后门安全监控',
        'pan': 45,
        'tilt': -10,
        'zoom': 1.5
    },
}

# PTZ厂商特定配置
PTZ_VENDOR_CONFIGS = {
    'hikvision': {
        'base_url_template': 'http://{ip}/ISAPI/PTZ/channels/{channel}',
        'default_channel': 1,
        'auth_method': 'digest',
        'api_version': 'v2.0',
        'commands': {
            'pan_left': 'momentary?arg1=LEFT&arg2={speed}&arg3=1',
            'pan_right': 'momentary?arg1=RIGHT&arg2={speed}&arg3=1',
            'tilt_up': 'momentary?arg1=UP&arg2={speed}&arg3=1',
            'tilt_down': 'momentary?arg1=DOWN&arg2={speed}&arg3=1',
            'zoom_in': 'momentary?arg1=ZOOMIN&arg2={speed}&arg3=1',
            'zoom_out': 'momentary?arg1=ZOOMOUT&arg2={speed}&arg3=1',
            'stop': 'momentary?arg1=STOP&arg2=0&arg3=0',
            'goto_preset': 'presets/{preset}/goto',
            'set_preset': 'presets/{preset}'
        }
    },
    'dahua': {
        'base_url_template': 'http://{ip}/cgi-bin/ptz.cgi',
        'default_channel': 0,
        'auth_method': 'basic',
        'commands': {
            'pan_left': '?action=start&channel={channel}&code=Left&arg1={speed}&arg2={speed}',
            'pan_right': '?action=start&channel={channel}&code=Right&arg1={speed}&arg2={speed}',
            'tilt_up': '?action=start&channel={channel}&code=Up&arg1={speed}&arg2={speed}',
            'tilt_down': '?action=start&channel={channel}&code=Down&arg1={speed}&arg2={speed}',
            'zoom_in': '?action=start&channel={channel}&code=ZoomTele&arg1={speed}&arg2={speed}',
            'zoom_out': '?action=start&channel={channel}&code=ZoomWide&arg1={speed}&arg2={speed}',
            'stop': '?action=stop&channel={channel}',
            'goto_preset': '?action=start&channel={channel}&code=GotoPreset&arg1=0&arg2={preset}',
            'set_preset': '?action=start&channel={channel}&code=SetPreset&arg1=0&arg2={preset}'
        }
    },
    'onvif': {
        'soap_endpoint': '/onvif/device_service',
        'ptz_endpoint': '/onvif/ptz_service',
        'auth_method': 'wsse',
        'profile_token': 'Profile_1',
        'pan_tilt_space': 'http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace',
        'zoom_space': 'http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace',
    },
    'generic': {
        'base_url_template': 'http://{ip}/cgi-bin/ptz.cgi',
        'auth_method': 'basic',
        'commands': {
            'pan_left': '?move=left&speed={speed}',
            'pan_right': '?move=right&speed={speed}',
            'tilt_up': '?move=up&speed={speed}',
            'tilt_down': '?move=down&speed={speed}',
            'zoom_in': '?zoom=in&speed={speed}',
            'zoom_out': '?zoom=out&speed={speed}',
            'stop': '?move=stop',
            'goto_preset': '?preset={preset}',
            'set_preset': '?setpreset={preset}'
        }
    }
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
    'page_title': "🎥 实时摄像头监控 + AI分析 + 云台控制",
    'update_interval': 2000,    # 前端更新间隔 (毫秒)
    'max_fps_display': 60,      # 最大显示FPS
    'enable_keyboard_control': True,  # 启用键盘控制
    'keyboard_shortcuts': {
        'up': '↑',
        'down': '↓',
        'left': '←',
        'right': '→',
        'zoom_in': '+',
        'zoom_out': '-',
        'stop': 'Space'
    }
}

# =============================================================================
# 存储和日志配置
# =============================================================================

# 文件路径配置
PATHS = {
    'temp_dir': '/tmp',                    # 临时文件目录
    'logs_dir': './logs',                  # 日志目录
    'captures_dir': './captures',          # 截图保存目录
    'temp_frame_path': '/tmp/web_frame.jpg',  # 临时帧文件路径
    'ptz_config_file': './ptz_settings.json',  # PTZ设置文件
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',            # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_logging': True,       # 是否记录到文件
    'console_logging': True,    # 是否输出到控制台
    'max_log_size': '10MB',     # 单个日志文件最大大小
    'backup_count': 5,          # 保留的日志文件数量
    'ptz_log_enabled': True,    # 启用PTZ操作日志
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
    'ptz_response_cache': 10,   # PTZ响应缓存时间 (秒)
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
        'ptz_timeout': 5,       # PTZ超时警告阈值 (秒)
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
        'enabled': True,        # 启用速率限制
        'requests_per_minute': 60,
        'ptz_commands_per_minute': 30,  # PTZ命令速率限制
    },
    'ptz_access_control': {
        'enable_ip_whitelist': False,  # 启用IP白名单
        'allowed_ips': ['192.168.1.0/24'],  # 允许的IP范围
        'enable_user_auth': False,     # 启用用户认证
        'require_https': False,        # 要求HTTPS
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
    'mock_ptz': False,          # 使用模拟PTZ控制
    'profile_performance': False, # 性能分析
    'save_debug_frames': False, # 保存调试帧
    'ptz_simulation': {
        'enabled': False,       # 启用PTZ模拟
        'response_delay': 0.1,  # 模拟响应延迟 (秒)
        'failure_rate': 0.0,    # 模拟失败率 (0.0-1.0)
    }
}

# 测试配置
TESTING = {
    'test_mode': False,         # 测试模式
    'test_duration': 60,        # 测试持续时间 (秒)
    'test_output_dir': './test_output',  # 测试输出目录
    'ptz_test_sequences': [
        {'command': 'pan', 'direction': 'left', 'duration': 2},
        {'command': 'pan', 'direction': 'right', 'duration': 2},
        {'command': 'tilt', 'direction': 'up', 'duration': 2},
        {'command': 'tilt', 'direction': 'down', 'duration': 2},
        {'command': 'preset', 'number': 1},
    ]
}

# =============================================================================
# 高级PTZ功能配置
# =============================================================================

# 自动巡航配置
AUTO_PATROL = {
    'enabled': False,           # 启用自动巡航
    'patrol_sequence': [1, 2, 3, 4],  # 巡航预设序列
    'dwell_time': 10,          # 每个位置停留时间 (秒)
    'transition_speed': 80,     # 切换速度
    'loop_count': 0,           # 循环次数 (0=无限循环)
}

# 运动检测触发PTZ
MOTION_TRIGGERED_PTZ = {
    'enabled': False,           # 启用运动触发PTZ
    'sensitivity': 0.3,         # 运动检测灵敏度
    'tracking_enabled': False,  # 启用目标跟踪
    'auto_zoom': True,         # 自动变焦
    'return_to_home': True,    # 运动停止后返回初始位置
    'home_preset': 1,          # 初始位置预设
    'timeout': 30,             # 无运动后返回超时 (秒)
}

# 时间表控制
SCHEDULED_PTZ = {
    'enabled': False,           # 启用计划任务
    'schedules': [
        {
            'name': '白天监控',
            'time_range': ['08:00', '18:00'],
            'actions': [
                {'time': '08:00', 'preset': 1},
                {'time': '12:00', 'preset': 2},
                {'time': '16:00', 'preset': 3},
            ]
        },
        {
            'name': '夜间巡逻',
            'time_range': ['18:00', '08:00'],
            'actions': [
                {'time': '18:00', 'action': 'start_patrol'},
                {'time': '08:00', 'action': 'stop_patrol', 'preset': 1},
            ]
        }
    ]
}

# =============================================================================
# 运行时配置检查
# =============================================================================

def validate_config():
    """验证配置有效性"""
    import os
    import ipaddress

    print("🔧 验证系统配置...")

    # 检查必要目录
    for path_key, path_value in PATHS.items():
        dir_path = os.path.dirname(path_value) if os.path.isfile(path_value) else path_value
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ 创建目录: {dir_path}")
            except Exception as e:
                print(f"❌ 无法创建目录 {dir_path}: {e}")

    # 验证PTZ配置
    try:
        camera_ip = PTZ_CONFIG.get('camera_ip')
        if camera_ip:
            ipaddress.ip_address(camera_ip)
            print(f"✅ PTZ IP地址有效: {camera_ip}")
        else:
            print("⚠️ 未配置PTZ IP地址")
    except ValueError:
        print(f"❌ PTZ IP地址无效: {camera_ip}")

    # 检查PTZ预设配置
    if len(PTZ_PRESETS) > 0:
        print(f"✅ PTZ预设配置: {len(PTZ_PRESETS)}个位置")
    else:
        print("⚠️ 未配置PTZ预设位置")

    # 检查端口可用性
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((FLASK_CONFIG['host'], FLASK_CONFIG['port']))
    sock.close()
    if result == 0:
        print(f"⚠️ 警告: 端口 {FLASK_CONFIG['port']} 已被占用")
    else:
        print(f"✅ 端口 {FLASK_CONFIG['port']} 可用")

    print("✅ 配置验证完成")

if __name__ == "__main__":
    validate_config()