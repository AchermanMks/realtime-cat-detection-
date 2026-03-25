#!/usr/bin/env python3
"""
PTZ快速修复脚本 - 启用演示模式或修复配置
"""

import json
import time

def create_demo_ptz_version():
    """创建演示版本的PTZ应用"""

    print("🔧 创建PTZ演示版本...")

    # 读取原始应用文件
    with open('app_with_ptz.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 修改PTZ控制器为演示模式
    demo_content = content.replace(
        'self.ptz_supported = False',
        'self.ptz_supported = True  # 演示模式'
    ).replace(
        'return False',
        'return True  # 演示模式: 模拟成功'
    ).replace(
        'print(f"❌ PTZ命令发送失败: {e}")',
        'print(f"🎭 PTZ演示模式: 模拟执行 {command_type} {direction}")'
    )

    # 添加演示模式标识
    demo_content = demo_content.replace(
        'class PTZController:',
        '''class PTZController:
    """云台控制器类 - 演示模式版本"""'''
    )

    # 保存演示版本
    with open('app_with_ptz_demo.py', 'w', encoding='utf-8') as f:
        f.write(demo_content)

    print("✅ 创建完成: app_with_ptz_demo.py")

def test_camera_ptz_support():
    """测试摄像头PTZ支持"""

    import requests

    camera_ip = "192.168.31.146"

    print(f"🔍 测试摄像头PTZ支持: {camera_ip}")

    # 常见的PTZ测试端点
    test_urls = [
        f"http://{camera_ip}/cgi-bin/ptz.cgi",
        f"http://{camera_ip}/ISAPI/PTZ/channels/1/status",
        f"http://{camera_ip}/axis-cgi/com/ptz.cgi",
        f"http://{camera_ip}/web/cgi-bin/hi3510/ptzctrl.cgi",
    ]

    for url in test_urls:
        try:
            print(f"测试: {url}")
            response = requests.head(url, timeout=2)
            print(f"  ✅ 响应: {response.status_code}")
            if response.status_code < 500:
                return True
        except Exception as e:
            print(f"  ❌ 失败: {str(e)[:50]}...")

    print("⚠️ 未检测到PTZ支持")
    return False

def main():
    """主函数"""

    print("🎥 PTZ控制修复工具")
    print("=" * 40)

    print("\n选择修复方案:")
    print("1. 启用PTZ演示模式 (推荐)")
    print("2. 测试摄像头PTZ支持")
    print("3. 手动配置PTZ设置")

    choice = input("\n请选择 (1-3): ").strip()

    if choice == "1":
        create_demo_ptz_version()
        print("\n🎭 演示模式已启用!")
        print("启动命令: python3 app_with_ptz_demo.py")
        print("演示模式特点:")
        print("- ✅ 所有PTZ命令都显示'成功'")
        print("- ✅ 界面完全正常显示")
        print("- ✅ 可以测试所有PTZ功能")
        print("- 🎭 实际不控制真实摄像头")

    elif choice == "2":
        if test_camera_ptz_support():
            print("\n✅ 检测到PTZ支持，可能需要认证配置")
        else:
            print("\n❌ 未检测到PTZ支持，建议使用演示模式")

    elif choice == "3":
        print("\n🔧 手动配置PTZ设置:")
        print("编辑 config_with_ptz.py 文件:")
        print("1. 设置正确的用户名密码")
        print("2. 指定协议类型 (hikvision, dahua, onvif)")
        print("3. 确认摄像头IP地址正确")

        config_example = {
            'PTZ_CONFIG': {
                'enabled': True,
                'camera_ip': '192.168.31.146',
                'username': 'admin',
                'password': 'your_password',
                'protocol': 'hikvision'  # 或 'dahua', 'onvif'
            }
        }

        print(f"\n示例配置:\n{json.dumps(config_example, indent=2, ensure_ascii=False)}")

    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    main()