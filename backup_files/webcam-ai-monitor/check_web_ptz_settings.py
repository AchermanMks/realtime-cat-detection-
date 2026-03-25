#!/usr/bin/env python3
"""
检查Web界面PTZ设置
"""

import requests
import re
from urllib.parse import urljoin
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def check_web_ptz_settings():
    """检查Web界面的PTZ设置"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    print("🌐 检查Web界面PTZ设置")
    print(f"🔑 凭据: {username}/{password}")
    print("=" * 50)

    session = requests.Session()
    session.auth = (username, password)
    session.verify = False

    # 可能的Web页面
    web_pages = [
        # HTTPS页面
        "https://192.168.31.146/",
        "https://192.168.31.146/index.html",
        "https://192.168.31.146/setting.html",
        "https://192.168.31.146/device.html",
        "https://192.168.31.146/ptz.html",
        "https://192.168.31.146/control.html",
        "https://192.168.31.146/config.html",
        "https://192.168.31.146/admin.html",

        # HTTP页面
        "http://192.168.31.146/",
        "http://192.168.31.146/index.html",
        "http://192.168.31.146/setting.html",
    ]

    accessible_pages = []

    for url in web_pages:
        try:
            print(f"\n🔍 检查: {url}")
            response = session.get(url, timeout=5)

            if response.status_code == 200:
                print(f"   ✅ 页面可访问 ({len(response.text)} 字符)")

                # 检查是否包含PTZ相关内容
                content_lower = response.text.lower()
                ptz_keywords = ['ptz', '云台', 'pan', 'tilt', 'zoom', 'control', '控制']

                found_ptz = []
                for keyword in ptz_keywords:
                    if keyword in content_lower:
                        found_ptz.append(keyword)

                if found_ptz:
                    print(f"   🎯 发现PTZ关键词: {', '.join(found_ptz)}")
                    accessible_pages.append({
                        'url': url,
                        'content': response.text,
                        'ptz_keywords': found_ptz
                    })

                    # 查找PTZ相关的设置项
                    ptz_settings = find_ptz_settings(response.text)
                    if ptz_settings:
                        print(f"   ⚙️ 发现PTZ设置项:")
                        for setting in ptz_settings[:5]:  # 显示前5个
                            print(f"      • {setting}")

                # 查找可能的配置页面链接
                config_links = find_config_links(response.text)
                if config_links:
                    print(f"   🔗 发现配置链接:")
                    for link in config_links[:3]:
                        print(f"      • {link}")

            elif response.status_code == 401:
                print(f"   ❌ 需要认证")
            elif response.status_code == 404:
                print(f"   ❌ 页面不存在")
            else:
                print(f"   ⚠️ 状态码: {response.status_code}")

        except requests.exceptions.SSLError:
            print(f"   ❌ SSL证书错误")
        except requests.exceptions.ConnectTimeout:
            print(f"   ❌ 连接超时")
        except Exception as e:
            print(f"   ❌ 异常: {str(e)[:50]}...")

    return accessible_pages

def find_ptz_settings(html_content):
    """查找HTML中的PTZ设置项"""
    ptz_patterns = [
        r'ptz[_\-]?enable',
        r'ptz[_\-]?protocol',
        r'ptz[_\-]?address',
        r'ptz[_\-]?speed',
        r'ptz[_\-]?control',
        r'enable[_\-]?ptz',
        r'云台.*启用',
        r'云台.*协议',
        r'preset.*position',
        r'name=["\']ptz',
        r'id=["\']ptz',
    ]

    found_settings = []
    for pattern in ptz_patterns:
        matches = re.finditer(pattern, html_content, re.IGNORECASE)
        for match in matches:
            # 获取匹配周围的上下文
            start = max(0, match.start() - 50)
            end = min(len(html_content), match.end() + 50)
            context = html_content[start:end].strip()
            # 清理HTML标签
            clean_context = re.sub(r'<[^>]+>', ' ', context)
            clean_context = ' '.join(clean_context.split())

            if clean_context not in found_settings and len(clean_context) > 10:
                found_settings.append(clean_context)

    return found_settings

def find_config_links(html_content):
    """查找配置相关的链接"""
    link_patterns = [
        r'href=["\']([^"\']*(?:ptz|config|setting|device|control)[^"\']*)["\']',
        r'href=["\']([^"\']*\.html?)["\']'
    ]

    found_links = set()
    for pattern in link_patterns:
        matches = re.finditer(pattern, html_content, re.IGNORECASE)
        for match in matches:
            link = match.group(1)
            if any(keyword in link.lower() for keyword in ['ptz', 'config', 'setting', 'device', 'control']):
                found_links.add(link)

    return list(found_links)

def test_config_api():
    """测试配置API"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    print(f"\n🔧 测试配置API")
    print("=" * 50)

    session = requests.Session()
    session.auth = (username, password)
    session.verify = False

    # 可能的配置API
    config_apis = [
        "https://192.168.31.146/cgi-bin/configManager.cgi?action=getConfig&name=PTZ",
        "https://192.168.31.146/cgi-bin/configManager.cgi?action=getConfig&name=Ptz",
        "https://192.168.31.146/cgi-bin/configManager.cgi?action=getConfig",
        "https://192.168.31.146/api/config/ptz",
        "https://192.168.31.146/web/api/config",
        "http://192.168.31.146/cgi-bin/configManager.cgi?action=getConfig&name=PTZ",
    ]

    for api in config_apis:
        try:
            print(f"\n🔍 测试API: {api}")
            response = session.get(api, timeout=3)

            if response.status_code == 200:
                print(f"   ✅ API响应成功")
                content = response.text[:300]
                print(f"   📄 内容预览: {content}...")

                if 'ptz' in content.lower():
                    print(f"   🎯 包含PTZ配置信息!")

        except Exception as e:
            print(f"   ❌ API测试失败: {str(e)[:50]}...")

if __name__ == "__main__":
    print("🎯 JOVISION Web界面PTZ设置检查")
    print("🔍 查找PTZ相关的启用/禁用设置")
    print("=" * 60)

    # 检查Web页面
    pages = check_web_ptz_settings()

    # 测试配置API
    test_config_api()

    # 总结
    print(f"\n" + "=" * 60)
    print(f"📋 检查总结:")

    if pages:
        print(f"✅ 找到 {len(pages)} 个包含PTZ内容的页面")

        print(f"\n💡 建议检查的页面:")
        for page in pages:
            print(f"   🌐 {page['url']}")
            print(f"      关键词: {', '.join(page['ptz_keywords'])}")

        print(f"\n🔧 下一步:")
        print(f"   1. 浏览器访问找到的页面")
        print(f"   2. 查找PTZ启用/协议设置")
        print(f"   3. 确认PTZ功能已激活")
        print(f"   4. 检查PTZ用户权限")

    else:
        print(f"❌ 没有找到包含PTZ内容的Web页面")
        print(f"\n💡 可能的原因:")
        print(f"   1. PTZ设置在隐藏或高级菜单中")
        print(f"   2. 需要JavaScript才能显示PTZ控制")
        print(f"   3. PTZ功能可能完全禁用")

    print(f"\n🎯 关键问题:")
    print(f"   虽然UDP命令返回'OK'，但摄像头不移动")
    print(f"   很可能PTZ功能在Web界面中被禁用了")