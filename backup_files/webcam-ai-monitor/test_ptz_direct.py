#!/usr/bin/env python3
"""
直接测试真实PTZ控制
"""

import requests
import time

def test_camera_ptz():
    """直接测试摄像头PTZ控制"""

    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print(f"🎮 开始测试真实PTZ控制")
    print(f"📡 摄像头IP: {camera_ip}")
    print(f"👤 用户名: {username}")
    print("=" * 50)

    # 测试海康威视协议
    print("\n🔍 测试海康威视协议...")

    try:
        # 向左转动
        url_left = f"http://{camera_ip}/ISAPI/PTZ/channels/1/momentary?arg1=LEFT&arg2=30&arg3=1"
        print(f"发送命令: 向左转动")
        response = requests.put(url_left, auth=(username, password), timeout=5)
        print(f"响应状态: {response.status_code}")

        if response.status_code == 200:
            print("✅ 海康威视LEFT命令发送成功")
            print("📹 如果摄像头支持PTZ，现在应该看到画面向左移动...")
            time.sleep(3)

            # 停止移动
            url_stop = f"http://{camera_ip}/ISAPI/PTZ/channels/1/momentary?arg1=STOP&arg2=0&arg3=0"
            print("发送停止命令...")
            stop_response = requests.put(url_stop, auth=(username, password), timeout=5)
            if stop_response.status_code == 200:
                print("✅ 停止命令发送成功")

            # 向右转动
            time.sleep(1)
            url_right = f"http://{camera_ip}/ISAPI/PTZ/channels/1/momentary?arg1=RIGHT&arg2=30&arg3=1"
            print("发送命令: 向右转动")
            right_response = requests.put(url_right, auth=(username, password), timeout=5)
            if right_response.status_code == 200:
                print("✅ 海康威视RIGHT命令发送成功")
                print("📹 如果摄像头支持PTZ，现在应该看到画面向右移动...")
                time.sleep(3)

                # 最终停止
                print("发送最终停止命令...")
                requests.put(url_stop, auth=(username, password), timeout=5)
                print("✅ PTZ测试完成")

            return True

        elif response.status_code == 401:
            print("❌ 认证失败 - 用户名或密码错误")
        elif response.status_code == 404:
            print("❌ 海康威视API不存在 - 可能不是海康威视摄像头")
        else:
            print(f"❌ 海康威视测试失败: HTTP {response.status_code}")

    except requests.exceptions.ConnectTimeout:
        print("❌ 连接超时 - 检查IP地址和网络连接")
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误 - 摄像头可能不在线")
    except Exception as e:
        print(f"❌ 海康威视测试异常: {e}")

    # 测试大华协议
    print("\n🔍 测试大华协议...")

    try:
        # 向上转动
        url_up = f"http://{camera_ip}/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=30&arg2=30"
        print("发送命令: 向上转动")
        response = requests.get(url_up, auth=(username, password), timeout=5)
        print(f"响应状态: {response.status_code}")
        print(f"响应内容: {response.text[:50]}...")

        if response.status_code == 200 and ("OK" in response.text or response.text.strip() == ""):
            print("✅ 大华UP命令发送成功")
            print("📹 如果摄像头支持PTZ，现在应该看到画面向上移动...")
            time.sleep(3)

            # 停止移动
            url_stop = f"http://{camera_ip}/cgi-bin/ptz.cgi?action=stop&channel=0"
            print("发送停止命令...")
            requests.get(url_stop, auth=(username, password), timeout=5)
            print("✅ 大华测试完成")

            return True

        elif response.status_code == 401:
            print("❌ 认证失败")
        elif response.status_code == 404:
            print("❌ 大华API不存在 - 可能不是大华摄像头")
        else:
            print(f"❌ 大华测试失败: HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ 大华测试异常: {e}")

    # 测试通用协议
    print("\n🔍 测试通用协议...")

    try:
        # 通用PTZ命令
        generic_urls = [
            f"http://{camera_ip}/cgi-bin/ptz.cgi?move=left&speed=30",
            f"http://{camera_ip}/axis-cgi/com/ptz.cgi?move=left",
            f"http://{camera_ip}/web/cgi-bin/hi3510/ptzctrl.cgi?move=left",
        ]

        for i, url in enumerate(generic_urls):
            print(f"测试通用API {i+1}: {url.split('/')[-1]}")
            try:
                response = requests.get(url, auth=(username, password), timeout=3)
                if response.status_code < 400:
                    print(f"✅ 通用API {i+1} 响应正常: {response.status_code}")
                    time.sleep(2)
                    # 尝试停止
                    stop_url = url.replace("move=left", "move=stop")
                    requests.get(stop_url, auth=(username, password), timeout=3)
                    return True
                else:
                    print(f"❌ 通用API {i+1} 失败: {response.status_code}")
            except:
                print(f"❌ 通用API {i+1} 连接失败")

    except Exception as e:
        print(f"❌ 通用协议测试异常: {e}")

    print("\n❌ 所有PTZ协议测试失败")
    print("💡 可能的原因:")
    print("   1. 摄像头是固定式，不支持PTZ功能")
    print("   2. 需要不同的用户名/密码")
    print("   3. 摄像头使用特殊的PTZ协议")
    print("   4. PTZ功能被禁用")

    return False

if __name__ == "__main__":
    success = test_camera_ptz()

    print("\n" + "=" * 50)
    if success:
        print("🎉 PTZ测试成功!")
        print("💡 如果看到画面移动，说明摄像头支持PTZ控制")
        print("💡 如果没有画面移动，可能是固定式摄像头")
    else:
        print("❌ PTZ测试失败")
        print("💡 你的摄像头很可能是固定式，不支持PTZ功能")
        print("💡 建议继续使用演示模式体验PTZ界面功能")