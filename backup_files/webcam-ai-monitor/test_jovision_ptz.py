#!/usr/bin/env python3
"""
JOVISION PTZ控制测试 - 支持多种认证方式
"""

import requests
import time

def test_jovision_credentials():
    """测试JOVISION常见的默认凭据"""

    camera_ip = "192.168.31.146"

    # JOVISION常见的默认用户名/密码组合
    credentials = [
        ("admin", "admin"),
        ("admin", ""),
        ("admin", "123456"),
        ("admin", "admin123"),
        ("root", "root"),
        ("user", "user"),
        ("admin", "888888"),
    ]

    print("🔐 测试JOVISION常见默认凭据...")

    for username, password in credentials:
        print(f"🔑 测试: {username} / {'(空)' if not password else password}")

        # 测试Web登录
        try:
            response = requests.get(
                f"http://{camera_ip}/",
                auth=(username, password),
                timeout=3
            )

            if response.status_code == 200:
                print(f"  ✅ Web认证成功: {username}/{password}")
                return username, password
            elif response.status_code == 401:
                print(f"  ❌ 认证失败")
            else:
                print(f"  ⚠️ 其他状态: {response.status_code}")
        except:
            print(f"  ❌ 连接失败")

    print("❌ 所有默认凭据测试失败")
    return None, None

def test_jovision_ptz_direct():
    """直接测试JOVISION PTZ控制"""

    camera_ip = "192.168.31.146"

    # 先尝试找到正确凭据
    username, password = test_jovision_credentials()

    if not username:
        # 如果找不到，使用用户输入
        print("\n🔐 请提供摄像头凭据:")
        username = input("用户名: ").strip() or "admin"
        password = input("密码: ").strip() or ""

    print(f"\n🎮 使用凭据测试PTZ: {username}/{password}")

    # JOVISION特有的PTZ API端点
    ptz_endpoints = [
        # 标准JOVISION API
        "/cgi-bin/ptz.cgi?action=move&direction=left&speed=50",
        "/cgi-bin/ptz?move=left&speed=50",
        # CGI PTZ控制
        "/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=left&-speed=50",
        # 通用PTZ
        "/ptz.cgi?move=left",
        "/web/cgi-bin/ptz.cgi?move=left&speed=50",
    ]

    for endpoint in ptz_endpoints:
        print(f"\n🔍 测试端点: {endpoint}")

        try:
            url = f"http://{camera_ip}{endpoint}"
            response = requests.get(
                url,
                auth=(username, password),
                timeout=5
            )

            print(f"响应状态: {response.status_code}")
            print(f"响应内容: {response.text[:100]}...")

            if response.status_code == 200 and ("OK" in response.text or response.text.strip() == ""):
                print("✅ PTZ命令发送成功!")
                print("📹 摄像头应该向左转动...")

                # 等待2秒
                time.sleep(2)

                # 发送停止命令
                stop_url = url.replace("left", "stop")
                requests.get(stop_url, auth=(username, password), timeout=3)
                print("⏹️ 发送停止命令")

                return True

            elif response.status_code == 401:
                print("❌ 认证失败")
            elif response.status_code == 404:
                print("❌ API端点不存在")
            else:
                print(f"❌ 失败: {response.status_code}")

        except Exception as e:
            print(f"❌ 测试异常: {str(e)[:50]}...")

    return False

def show_web_interface_info():
    """显示Web界面信息"""

    print("\n🌐 JOVISION摄像头Web管理界面:")
    print("地址: http://192.168.31.146")
    print("")
    print("🔧 在Web界面中你可以:")
    print("1. 查看正确的用户名/密码")
    print("2. 手动测试PTZ控制")
    print("3. 检查PTZ设置是否启用")
    print("4. 确认PTZ权限配置")

if __name__ == "__main__":
    print("🎯 JOVISION PTZ球机控制测试")
    print("=" * 50)

    success = test_jovision_ptz_direct()

    if success:
        print("\n🎉 JOVISION PTZ控制成功!")
        print("💡 现在可以配置真实PTZ控制版本")
    else:
        print("\n❌ JOVISION PTZ控制失败")
        show_web_interface_info()

        print("\n💡 建议:")
        print("1. 检查摄像头Web管理界面获取正确凭据")
        print("2. 确认PTZ功能已启用")
        print("3. 检查用户权限设置")