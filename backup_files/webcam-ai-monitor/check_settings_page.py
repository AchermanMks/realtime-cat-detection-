#!/usr/bin/env python3
"""
检查摄像头设置页面内容
"""

import requests
import re
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def analyze_settings_page():
    """分析设置页面内容"""

    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    print("🔍 分析摄像头设置页面")
    print("=" * 50)

    # 要检查的页面
    pages_to_check = [
        "/setting.html",
        "/settings.html",
        "/config.html",
        "/web/setting.html",
        "/admin/setting.html",
        "/ptz.html",
        "/control.html",
        "/device.html"
    ]

    session = requests.Session()
    session.verify = False
    session.auth = (username, password)

    for page in pages_to_check:
        url = f"https://{camera_ip}{page}"
        print(f"\n🔍 检查页面: {url}")

        try:
            response = session.get(url, timeout=10)

            print(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ 页面加载成功")
                print(f"   📏 内容长度: {len(response.text)} 字符")

                # 搜索PTZ相关内容
                content = response.text.lower()
                ptz_keywords = ['ptz', '云台', 'pan', 'tilt', 'zoom', 'control', '控制', 'preset', '预设']

                found_keywords = []
                for keyword in ptz_keywords:
                    if keyword in content:
                        found_keywords.append(keyword)

                if found_keywords:
                    print(f"   🎯 发现PTZ相关关键词: {', '.join(found_keywords)}")

                    # 尝试解析HTML结构
                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # 查找PTZ相关的表单元素
                        ptz_elements = []

                        # 查找包含PTZ的输入框、选择框等
                        for element in soup.find_all(['input', 'select', 'button']):
                            if element.get('name') or element.get('id'):
                                name_or_id = (element.get('name', '') + ' ' + element.get('id', '')).lower()
                                if any(keyword in name_or_id for keyword in ptz_keywords):
                                    ptz_elements.append(element)

                        # 查找包含PTZ的标签或文本
                        for element in soup.find_all(text=True):
                            if any(keyword in element.lower() for keyword in ptz_keywords):
                                parent = element.parent
                                if parent.name in ['label', 'span', 'div', 'td', 'th']:
                                    ptz_elements.append(parent)

                        if ptz_elements:
                            print(f"   🎮 发现 {len(ptz_elements)} 个PTZ相关元素")

                            # 显示前几个元素的详情
                            for i, element in enumerate(ptz_elements[:5]):
                                print(f"      {i+1}. {element.name}: {str(element)[:100]}...")

                        # 查找导航菜单或选项卡
                        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=lambda x: x and any(word in x.lower() for word in ['nav', 'menu', 'tab']))

                        if nav_elements:
                            print(f"   📋 发现导航菜单:")
                            for nav in nav_elements[:3]:
                                # 提取菜单项文本
                                menu_items = [item.get_text().strip() for item in nav.find_all(['a', 'li', 'span']) if item.get_text().strip()]
                                if menu_items:
                                    print(f"      菜单项: {', '.join(menu_items[:10])}")

                    except Exception as e:
                        print(f"   ⚠️ HTML解析失败: {e}")

                    # 直接显示包含PTZ的文本段落
                    ptz_lines = []
                    for line in response.text.split('\n'):
                        if any(keyword in line.lower() for keyword in ptz_keywords):
                            clean_line = re.sub(r'<[^>]+>', '', line).strip()
                            if clean_line and len(clean_line) < 200:
                                ptz_lines.append(clean_line)

                    if ptz_lines:
                        print(f"   📝 PTZ相关文本:")
                        for line in ptz_lines[:10]:
                            print(f"      • {line}")

                else:
                    print(f"   ⚠️ 未发现PTZ相关内容")

            elif response.status_code == 404:
                print(f"   ❌ 页面不存在")
            elif response.status_code == 401:
                print(f"   ❌ 需要认证")
            else:
                print(f"   ⚠️ 其他状态: {response.status_code}")

        except requests.exceptions.ConnectTimeout:
            print(f"   ❌ 连接超时")
        except requests.exceptions.SSLError:
            print(f"   ❌ SSL错误")
        except Exception as e:
            print(f"   ❌ 异常: {str(e)[:50]}...")

def check_api_endpoints():
    """检查可能的API端点"""

    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    print(f"\n🔍 检查API端点")
    print("=" * 50)

    # 可能的API端点
    api_endpoints = [
        "/cgi-bin/configManager.cgi?action=getConfig&name=PTZ",
        "/cgi-bin/ptz.cgi",
        "/api/ptz",
        "/web/api/ptz",
        "/admin/api/ptz",
        "/cgi-bin/hi3510/param.cgi?cmd=getptzpreset",
        "/device/ptz",
    ]

    session = requests.Session()
    session.verify = False
    session.auth = (username, password)

    for endpoint in api_endpoints:
        url = f"https://{camera_ip}{endpoint}"
        print(f"\n🔍 测试API: {endpoint}")

        try:
            response = session.get(url, timeout=5)

            if response.status_code == 200:
                print(f"   ✅ API响应成功")
                print(f"   📄 内容: {response.text[:200]}...")

                if 'ptz' in response.text.lower() or 'error' not in response.text.lower():
                    print(f"   🎯 可能的PTZ配置API!")

        except Exception as e:
            print(f"   ❌ API测试失败: {str(e)[:50]}...")

if __name__ == "__main__":
    print("🎯 JOVISION摄像头设置页面分析")
    print("🌐 URL: https://192.168.31.146/setting.html")
    print("=" * 60)

    # 分析设置页面
    analyze_settings_page()

    # 检查API端点
    check_api_endpoints()