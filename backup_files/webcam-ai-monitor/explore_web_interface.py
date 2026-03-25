#!/usr/bin/env python3
"""
探索Web界面的所有页面和设置
"""

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def explore_web_interface():
    """探索Web界面"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"
    base_url = f"http://{camera_ip}"

    session = requests.Session()
    session.auth = (username, password)
    session.verify = False

    print("🔍 探索JOVISION Web界面")
    print(f"📡 基础URL: {base_url}")
    print("=" * 50)

    # 1. 获取首页内容
    print("📄 分析首页内容...")
    try:
        response = session.get(base_url, timeout=10)
        if response.status_code == 200:
            print(f"✅ 首页加载成功 ({len(response.text)} 字符)")

            # 分析HTML内容
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找所有链接
            links = soup.find_all(['a', 'iframe', 'frame'])
            print(f"🔗 发现 {len(links)} 个链接:")

            unique_hrefs = set()
            for link in links:
                href = link.get('href') or link.get('src')
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    unique_hrefs.add(href)

            for href in sorted(unique_hrefs):
                print(f"   • {href}")

            # 查找JavaScript中的路径
            scripts = soup.find_all('script')
            print(f"\n📜 发现 {len(scripts)} 个脚本块")

            js_paths = set()
            for script in scripts:
                if script.string:
                    # 查找.html、.cgi、.jsp等路径
                    paths = re.findall(r'["\']([^"\']*\.(?:html|cgi|jsp|php|asp)[^"\']*)["\']', script.string)
                    for path in paths:
                        js_paths.add(path)

            if js_paths:
                print("🎯 JavaScript中发现的路径:")
                for path in sorted(js_paths):
                    print(f"   • {path}")

        else:
            print(f"❌ 首页加载失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 首页分析失败: {e}")

    # 2. 暴力扫描常见页面
    print(f"\n🔍 扫描常见页面...")
    common_pages = [
        # 设置页面
        "setup.html", "setup.cgi", "setup.jsp",
        "configuration.html", "configuration.cgi",
        "settings.html", "settings.cgi",
        "config.html", "config.cgi",
        "system.html", "system.cgi",

        # PTZ页面
        "ptz.html", "ptz.cgi", "ptz.jsp",
        "camera.html", "camera.cgi",
        "control.html", "control.cgi",
        "device.html", "device.cgi",
        "motor.html", "motor.cgi",

        # 管理页面
        "admin.html", "admin.cgi",
        "management.html", "manage.html",
        "advance.html", "advanced.html",
        "expert.html",

        # 网络页面
        "network.html", "network.cgi",
        "net.html", "net.cgi",

        # 常见文件夹
        "web/index.html", "web/setup.html", "web/ptz.html",
        "admin/index.html", "admin/setup.html", "admin/ptz.html",
        "cgi-bin/setup.cgi", "cgi-bin/ptz.cgi", "cgi-bin/config.cgi",

        # JOVISION特有
        "jovision.html", "jvs.html",
        "webpages/index.html", "webpages/setup.html"
    ]

    accessible_pages = []

    for page in common_pages:
        try:
            url = f"{base_url}/{page}"
            response = session.get(url, timeout=3)

            if response.status_code == 200:
                print(f"✅ 发现页面: {page} ({len(response.text)} 字符)")
                accessible_pages.append((page, response.text))

                # 快速检查是否包含PTZ内容
                content_lower = response.text.lower()
                ptz_keywords = ['ptz', '云台', 'pan', 'tilt', 'zoom', 'preset', '预设', 'control', '控制']

                found_keywords = [kw for kw in ptz_keywords if kw in content_lower]
                if found_keywords:
                    print(f"   🎯 包含PTZ关键词: {', '.join(found_keywords[:3])}")

        except Exception as e:
            continue

    # 3. 详细分析包含PTZ的页面
    print(f"\n🔍 详细分析包含PTZ的页面...")

    for page_name, content in accessible_pages:
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ['ptz', '云台', 'control', '控制']):
            print(f"\n📄 分析页面: {page_name}")
            analyze_ptz_page(content, f"{base_url}/{page_name}")

def analyze_ptz_page(html_content, page_url):
    """详细分析PTZ相关页面"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 查找表单
        forms = soup.find_all('form')
        if forms:
            print(f"   📝 发现 {len(forms)} 个表单")

            for i, form in enumerate(forms):
                action = form.get('action', '')
                method = form.get('method', 'GET')

                print(f"      表单 {i+1}: {method} -> {action}")

                # 分析表单字段
                inputs = form.find_all(['input', 'select', 'textarea'])
                ptz_fields = []

                for input_field in inputs:
                    name = input_field.get('name', '')
                    input_type = input_field.get('type', '')
                    value = input_field.get('value', '')

                    field_info = f"{input_field.name} {name} ({input_type})"
                    if value:
                        field_info += f" = {value}"

                    # 检查是否是PTZ相关字段
                    field_text = f"{name} {input_type} {value}".lower()
                    if any(keyword in field_text for keyword in ['ptz', '云台', 'pan', 'tilt', 'zoom', 'preset', 'control']):
                        ptz_fields.append(field_info)

                if ptz_fields:
                    print(f"         🎯 PTZ相关字段:")
                    for field in ptz_fields[:5]:  # 显示前5个
                        print(f"            • {field}")

        # 查找JavaScript变量和函数
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # 查找PTZ相关的JavaScript函数
                js_functions = re.findall(r'function\s+(\w*ptz\w*|\w*control\w*|\w*云台\w*)\s*\([^)]*\)', script.string, re.IGNORECASE)
                if js_functions:
                    print(f"   🔧 发现PTZ相关JS函数: {', '.join(js_functions)}")

                # 查找PTZ相关的变量
                js_vars = re.findall(r'var\s+(\w*ptz\w*|\w*control\w*)\s*=', script.string, re.IGNORECASE)
                if js_vars:
                    print(f"   🔧 发现PTZ相关JS变量: {', '.join(js_vars)}")

        # 查找可能的AJAX端点
        ajax_patterns = [
            r'url\s*:\s*["\']([^"\']*(?:ptz|control|云台)[^"\']*)["\']',
            r'["\']([^"\']*\.cgi[^"\']*)["\']',
            r'["\']([^"\']*api[^"\']*)["\']'
        ]

        for pattern in ajax_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                print(f"   🌐 发现可能的API端点: {', '.join(set(matches))}")

    except Exception as e:
        print(f"   ❌ 页面分析失败: {e}")

def test_discovered_endpoints():
    """测试发现的端点"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"
    base_url = f"http://{camera_ip}"

    session = requests.Session()
    session.auth = (username, password)

    # 基于JOVISION常见的端点
    test_endpoints = [
        "/cgi-bin/configManager.cgi?action=getConfig&name=Ptz",
        "/cgi-bin/configManager.cgi?action=getConfig&name=PTZ",
        "/cgi-bin/ptz.cgi?action=start&channel=0&code=Left",
        "/cgi-bin/hi3510/ptzctrl.cgi",
        "/api/ptz",
        "/web/api/ptz",
        "/device/ptz",
        "/system/ptz"
    ]

    print(f"\n🔍 测试发现的端点...")

    for endpoint in test_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = session.get(url, timeout=3)

            if response.status_code == 200:
                print(f"✅ 可访问: {endpoint}")
                print(f"   响应: {response.text[:100]}...")

                if 'ptz' in response.text.lower():
                    print(f"   🎯 包含PTZ配置信息!")

        except Exception as e:
            continue

if __name__ == "__main__":
    explore_web_interface()
    test_discovered_endpoints()

    print(f"\n💡 下一步建议:")
    print(f"1. 手动访问发现的页面: http://192.168.31.146")
    print(f"2. 查找PTZ/云台/控制相关的设置选项")
    print(f"3. 启用PTZ功能并保存配置")
    print(f"4. 重新测试PTZ控制是否工作")