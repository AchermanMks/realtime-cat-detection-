#!/usr/bin/env python3
"""
摄像头URL查找指南
提供常见品牌的RTSP和控制URL格式
"""

def show_common_camera_urls():
    """显示常见品牌摄像头的URL格式"""

    camera_configs = {
        "海康威视 (Hikvision)": {
            "rtsp_urls": [
                "rtsp://admin:password@IP:554/Streaming/Channels/101",
                "rtsp://admin:password@IP:554/Streaming/Channels/1/Preview_01_sub",
                "rtsp://admin:password@IP:554/h264/ch1/main/av_stream"
            ],
            "ptz_url": "http://IP/PSIA/PTZ/channels/1/continuous",
            "web_url": "http://IP",
            "default_port": 554,
            "default_user": "admin",
            "default_pass": "12345",
            "notes": "端口通常是554，默认用户名admin，默认密码12345或admin"
        },

        "大华 (Dahua)": {
            "rtsp_urls": [
                "rtsp://admin:admin@IP:554/cam/realmonitor?channel=1&subtype=0",
                "rtsp://admin:admin@IP:554/cam/realmonitor?channel=1&subtype=1"
            ],
            "ptz_url": "http://IP/cgi-bin/ptz.cgi",
            "web_url": "http://IP",
            "default_port": 554,
            "default_user": "admin",
            "default_pass": "admin",
            "notes": "subtype=0是主码流，subtype=1是子码流"
        },

        "TP-Link": {
            "rtsp_urls": [
                "rtsp://admin:admin@IP:554/stream1",
                "rtsp://admin:admin@IP:554/stream2"
            ],
            "ptz_url": "http://IP/cgi/ptdc.cgi",
            "web_url": "http://IP",
            "default_port": 554,
            "default_user": "admin",
            "default_pass": "admin",
            "notes": "stream1是高清流，stream2是标清流"
        },

        "小米 (Xiaomi)": {
            "rtsp_urls": [
                "rtsp://IP:8554/unicast",
                "rtsp://IP/stream/0"
            ],
            "ptz_url": "http://IP/cgi-bin/ptz.cgi",
            "web_url": "http://IP",
            "default_port": 8554,
            "default_user": "admin",
            "default_pass": "",
            "notes": "端口通常是8554，可能不需要密码"
        },

        "萤石 (EZVIZ)": {
            "rtsp_urls": [
                "rtsp://admin:password@IP:554/h264/ch1/main/av_stream",
                "rtsp://admin:password@IP:554/h264/ch1/sub/av_stream"
            ],
            "ptz_url": "http://IP/api/ptz/move",
            "web_url": "http://IP",
            "default_port": 554,
            "default_user": "admin",
            "default_pass": "验证码",
            "notes": "密码通常是设备验证码"
        },

        "Axis": {
            "rtsp_urls": [
                "rtsp://admin:password@IP:554/axis-media/media.amp",
                "rtsp://admin:password@IP:554/mjpg/video.mjpg"
            ],
            "ptz_url": "http://IP/axis-cgi/com/ptz.cgi",
            "web_url": "http://IP",
            "default_port": 554,
            "default_user": "root",
            "default_pass": "pass",
            "notes": "高端摄像头，用户名通常是root"
        }
    }

    print("📹 常见摄像头品牌URL格式")
    print("=" * 60)

    for brand, config in camera_configs.items():
        print(f"\n🏷️  {brand}")
        print("-" * 40)

        print("📡 RTSP地址:")
        for rtsp in config["rtsp_urls"]:
            print(f"   {rtsp}")

        print(f"🎮 PTZ控制: {config['ptz_url']}")
        print(f"🌐 Web界面: {config['web_url']}")
        print(f"⚙️  默认设置: {config['default_user']}:{config['default_pass']}:{config['default_port']}")
        print(f"💡 说明: {config['notes']}")

def show_discovery_methods():
    """显示发现摄像头的方法"""

    print("\n🔍 查找摄像头URL的方法")
    print("=" * 50)

    methods = [
        {
            "title": "1. 路由器设备列表",
            "description": "登录路由器管理界面，查看连接设备列表",
            "steps": [
                "打开浏览器，访问 192.168.1.1 或 192.168.0.1",
                "输入路由器管理员账号密码",
                "查找'设备管理'或'连接设备'菜单",
                "找到摄像头设备的IP地址"
            ]
        },
        {
            "title": "2. 网络扫描工具",
            "description": "使用网络扫描工具查找设备",
            "steps": [
                "运行: python3 camera_discovery.py",
                "或使用 nmap: nmap -sn 192.168.1.1/24",
                "或使用 Advanced IP Scanner (Windows)",
                "查找开放554端口的设备"
            ]
        },
        {
            "title": "3. 厂商配置工具",
            "description": "使用摄像头厂商提供的配置软件",
            "steps": [
                "海康威视: SADP工具",
                "大华: ConfigTool",
                "TP-Link: TP-Link Camera Tool",
                "下载对应厂商的设备发现工具"
            ]
        },
        {
            "title": "4. 移动APP查看",
            "description": "通过摄像头配套的手机APP查看",
            "steps": [
                "打开摄像头对应的手机APP",
                "进入设备设置页面",
                "查找'设备信息'或'网络设置'",
                "记录IP地址和端口信息"
            ]
        }
    ]

    for method in methods:
        print(f"\n{method['title']}")
        print(f"📝 {method['description']}")
        print("步骤:")
        for step in method['steps']:
            print(f"   • {step}")

def generate_test_config(ip, brand="Unknown"):
    """生成测试配置"""

    print(f"\n📋 生成测试配置 - IP: {ip}")
    print("=" * 40)

    config = f'''# 摄像头配置 - {brand}
# 修改 robot_vision_config.py 文件

class Config:
    # RTSP配置
    RTSP_URL = "rtsp://admin:admin@{ip}:554/stream1"

    # 云台控制配置
    PTZ_BASE_URL = "http://{ip}"
    PTZ_USERNAME = "admin"
    PTZ_PASSWORD = "admin"

    # 如果上述配置不工作，尝试以下地址:
    # RTSP备选:
    # "rtsp://admin:password@{ip}:554/Streaming/Channels/101"  # 海康威视
    # "rtsp://admin:admin@{ip}:554/cam/realmonitor?channel=1&subtype=0"  # 大华
    # "rtsp://admin:admin@{ip}:8554/unicast"  # 小米
'''

    print(config)

def quick_test_camera(ip, username="admin", password="admin"):
    """快速测试摄像头连接"""

    print(f"\n🧪 快速测试摄像头: {ip}")
    print("-" * 30)

    # 测试常见RTSP地址
    test_urls = [
        f"rtsp://{username}:{password}@{ip}:554/stream1",
        f"rtsp://{username}:{password}@{ip}:554/Streaming/Channels/101",
        f"rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0",
        f"rtsp://{username}:{password}@{ip}:8554/unicast"
    ]

    working_urls = []

    for url in test_urls:
        print(f"🔍 测试: {url.replace(password, '***')}")

        try:
            import cv2
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                print(f"✅ 连接成功!")
                working_urls.append(url)
            else:
                print(f"❌ 连接失败")

        except Exception as e:
            print(f"❌ 错误: {e}")

    if working_urls:
        print(f"\n🎉 找到 {len(working_urls)} 个可用URL:")
        for url in working_urls:
            print(f"  ✅ {url}")

        # 生成配置
        generate_test_config(ip)

        return working_urls
    else:
        print("\n❌ 未找到可用的RTSP地址")
        print("\n💡 建议:")
        print("1. 确认IP地址正确")
        print("2. 检查用户名密码")
        print("3. 尝试不同的端口 (554, 8554)")
        print("4. 查看摄像头说明书")

        return []

def main():
    """主函数"""
    print("🎥 摄像头URL查找指南")
    print("=" * 50)

    while True:
        print("\n请选择操作:")
        print("1. 查看常见品牌URL格式")
        print("2. 查看发现摄像头的方法")
        print("3. 快速测试摄像头连接")
        print("4. 生成测试配置")
        print("5. 运行网络扫描工具")
        print("0. 退出")

        choice = input("\n输入选择 (0-5): ").strip()

        if choice == '1':
            show_common_camera_urls()
        elif choice == '2':
            show_discovery_methods()
        elif choice == '3':
            ip = input("输入摄像头IP地址: ").strip()
            if ip:
                username = input("用户名 (默认 admin): ").strip() or "admin"
                password = input("密码 (默认 admin): ").strip() or "admin"
                quick_test_camera(ip, username, password)
        elif choice == '4':
            ip = input("输入摄像头IP地址: ").strip()
            brand = input("摄像头品牌 (可选): ").strip() or "Unknown"
            if ip:
                generate_test_config(ip, brand)
        elif choice == '5':
            print("正在启动网络扫描工具...")
            import subprocess
            try:
                subprocess.run(["python3", "camera_discovery.py"])
            except FileNotFoundError:
                print("❌ 请先确保 camera_discovery.py 文件存在")
        elif choice == '0':
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    main()