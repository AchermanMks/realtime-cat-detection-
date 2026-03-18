#!/usr/bin/env python3
"""
Web界面PTZ控制分析工具
通过HTTP代理方式分析PTZ控制协议
"""

import json
import time
import requests
import threading
from datetime import datetime
from urllib.parse import parse_qs, urlparse
import re
import base64

class WebPTZAnalyzer:
    """Web界面PTZ分析器"""

    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False

        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"web_ptz_analysis_{self.timestamp}.txt"

        print(f"📝 分析日志: {self.log_file}")

    def log_message(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def analyze_web_page(self, url):
        """分析Web页面内容"""
        self.log_message(f"🌐 分析页面: {url}")

        try:
            response = self.session.get(url, auth=(self.username, self.password), timeout=10)
            self.log_message(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                content = response.text

                # 查找JavaScript中的PTZ相关函数
                js_patterns = [
                    r'function\s+(\w*(?:ptz|move|pan|tilt|zoom|preset|control)\w*)\s*\([^)]*\)',
                    r'(\w*(?:ptz|move|pan|tilt|zoom|preset|control)\w*)\s*:\s*function',
                    r'\.(\w*(?:ptz|move|pan|tilt|zoom|preset|control)\w*)\s*\(',
                    r'ajax.*?url.*?["\']([^"\']*(?:ptz|move|pan|tilt|zoom|control)[^"\']*)["\']',
                    r'fetch\s*\(\s*["\']([^"\']*(?:ptz|move|pan|tilt|zoom|control)[^"\']*)["\']',
                ]

                for pattern in js_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        self.log_message(f"   🎯 发现PTZ相关代码: {matches}")

                # 查找API端点
                api_patterns = [
                    r'["\']([^"\']*(?:cgi-bin|api)[^"\']*(?:ptz|move|control)[^"\']*)["\']',
                    r'["\']([^"\']*(?:ptz|move|control)[^"\']*\.(?:cgi|php|asp|action))["\']',
                    r'action\s*=\s*["\']([^"\']*(?:ptz|move|control)[^"\']*)["\']',
                ]

                for pattern in api_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        self.log_message(f"   📡 发现API端点: {matches}")

                # 保存页面内容
                filename = f"web_page_{url.split('/')[-1].replace('.html', '')}_{self.timestamp}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log_message(f"   💾 页面已保存: {filename}")

                return content

        except Exception as e:
            self.log_message(f"   ❌ 分析失败: {e}")
            return None

    def discover_ptz_endpoints(self):
        """发现PTZ控制端点"""
        self.log_message("🔍 发现PTZ控制端点...")

        # 常见的PTZ端点
        endpoints = [
            "/setting.html",
            "/index.html",
            "/main.html",
            "/control.html",
            "/ptz.html",
            "/cgi-bin/ptz.cgi",
            "/web/cgi-bin/hi3510/ptzctrl.cgi",
            "/PSIA/PTZ/channels/1/continuous",
            "/api/ptz",
            "/api/v1/ptz",
            "/control/ptz",
            "/ptz/control",
            "/device/ptz",
            "/cam/ptz",
        ]

        found_endpoints = []

        for endpoint in endpoints:
            url = f"https://{self.camera_ip}{endpoint}"
            try:
                response = self.session.get(url, auth=(self.username, self.password), timeout=5)
                if response.status_code in [200, 401, 403]:
                    found_endpoints.append((endpoint, response.status_code))
                    self.log_message(f"   ✅ {endpoint} -> {response.status_code}")

                    if response.status_code == 200:
                        # 分析页面内容
                        self.analyze_web_page(url)

            except Exception as e:
                self.log_message(f"   ❌ {endpoint} -> {e}")

        return found_endpoints

    def test_common_ptz_commands(self):
        """测试常见的PTZ命令"""
        self.log_message("🎮 测试常见PTZ命令...")

        # 常见的PTZ命令参数
        commands = [
            # 海康威视风格
            {"action": "start", "channel": "0", "code": "Left", "arg1": "0", "arg2": "5", "arg3": "0"},
            {"action": "start", "channel": "0", "code": "Right", "arg1": "0", "arg2": "5", "arg3": "0"},
            {"action": "start", "channel": "0", "code": "Up", "arg1": "0", "arg2": "5", "arg3": "0"},
            {"action": "start", "channel": "0", "code": "Down", "arg1": "0", "arg2": "5", "arg3": "0"},

            # 大华风格
            {"command": "ptz", "action": "moveLeft", "speed": "3"},
            {"command": "ptz", "action": "moveRight", "speed": "3"},
            {"command": "ptz", "action": "moveUp", "speed": "3"},
            {"command": "ptz", "action": "moveDown", "speed": "3"},

            # 通用风格
            {"cmd": "ptz", "move": "left", "speed": "50"},
            {"cmd": "ptz", "move": "right", "speed": "50"},
            {"cmd": "ptz", "move": "up", "speed": "50"},
            {"cmd": "ptz", "move": "down", "speed": "50"},
        ]

        endpoints = [
            "/cgi-bin/ptz.cgi",
            "/web/cgi-bin/hi3510/ptzctrl.cgi",
            "/PSIA/PTZ/channels/1/continuous",
            "/api/ptz",
            "/control/ptz",
        ]

        for endpoint in endpoints:
            url = f"https://{self.camera_ip}{endpoint}"
            self.log_message(f"🔗 测试端点: {url}")

            for i, cmd in enumerate(commands):
                try:
                    # 尝试GET请求
                    response = self.session.get(url, params=cmd, auth=(self.username, self.password), timeout=5)
                    self.log_message(f"   GET #{i+1}: {response.status_code} - {cmd}")

                    # 尝试POST请求
                    response = self.session.post(url, data=cmd, auth=(self.username, self.password), timeout=5)
                    self.log_message(f"   POST #{i+1}: {response.status_code} - {cmd}")

                    # 尝试JSON格式
                    response = self.session.post(url, json=cmd, auth=(self.username, self.password), timeout=5)
                    self.log_message(f"   JSON #{i+1}: {response.status_code} - {cmd}")

                except Exception as e:
                    pass  # 忽略错误，继续测试

                time.sleep(0.5)  # 避免过于频繁的请求

    def analyze_network_requests(self):
        """分析网络请求模式"""
        self.log_message("📊 分析网络请求模式...")

        # 模拟浏览器访问设置页面
        setting_url = f"https://{self.camera_ip}/setting.html"

        try:
            # 设置浏览器请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            self.session.headers.update(headers)

            response = self.session.get(setting_url, auth=(self.username, self.password))
            self.log_message(f"   设置页面状态: {response.status_code}")

            if response.status_code == 200:
                content = response.text

                # 查找页面中加载的JavaScript文件
                js_files = re.findall(r'<script[^>]*src=["\']([^"\']+\.js)["\']', content, re.IGNORECASE)
                self.log_message(f"   发现JS文件: {js_files}")

                # 分析JavaScript文件
                for js_file in js_files:
                    if not js_file.startswith('http'):
                        js_url = f"https://{self.camera_ip}/{js_file.lstrip('/')}"
                        try:
                            js_response = self.session.get(js_url, auth=(self.username, self.password))
                            if js_response.status_code == 200:
                                js_content = js_response.text

                                # 查找PTZ相关的函数和URL
                                ptz_functions = re.findall(r'function\s+(\w*ptz\w*)', js_content, re.IGNORECASE)
                                ptz_urls = re.findall(r'["\']([^"\']*(?:ptz|move|control)[^"\']*)["\']', js_content, re.IGNORECASE)

                                if ptz_functions or ptz_urls:
                                    self.log_message(f"   📄 {js_file} - PTZ函数: {ptz_functions}")
                                    self.log_message(f"   📄 {js_file} - PTZ URLs: {ptz_urls}")

                                    # 保存JS文件
                                    js_filename = f"js_{js_file.split('/')[-1]}_{self.timestamp}"
                                    with open(js_filename, 'w', encoding='utf-8') as f:
                                        f.write(js_content)
                                    self.log_message(f"   💾 JS文件已保存: {js_filename}")

                        except Exception as e:
                            self.log_message(f"   ❌ 无法获取JS文件 {js_file}: {e}")

        except Exception as e:
            self.log_message(f"   ❌ 分析失败: {e}")

    def generate_curl_commands(self):
        """生成curl测试命令"""
        self.log_message("📋 生成curl测试命令...")

        curl_file = f"curl_commands_{self.timestamp}.sh"

        with open(curl_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# PTZ控制测试命令\n")
            f.write(f"# 摄像头IP: {self.camera_ip}\n")
            f.write(f"# 用户名: {self.username}\n\n")

            # 常见的curl命令
            commands = [
                'curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0"',
                'curl -k -u admin:admin123 -X POST -d "action=start&channel=0&code=Right&arg1=0&arg2=5&arg3=0" "https://192.168.31.146/cgi-bin/ptz.cgi"',
                'curl -k -u admin:admin123 -X POST -H "Content-Type: application/json" -d \'{"command":"ptz","action":"moveUp","speed":"3"}\' "https://192.168.31.146/api/ptz"',
                'curl -k -u admin:admin123 "https://192.168.31.146/PSIA/PTZ/channels/1/continuous?pan=50&tilt=50"',
            ]

            for cmd in commands:
                f.write(f"echo '测试: {cmd}'\n")
                f.write(f"{cmd}\n")
                f.write("echo ''\n\n")

        self.log_message(f"💾 curl命令已保存: {curl_file}")

    def run_analysis(self):
        """运行完整分析"""
        self.log_message("🚀 开始PTZ协议分析...")

        try:
            # 1. 发现端点
            endpoints = self.discover_ptz_endpoints()

            # 2. 分析网络请求模式
            self.analyze_network_requests()

            # 3. 测试PTZ命令
            self.test_common_ptz_commands()

            # 4. 生成测试命令
            self.generate_curl_commands()

            self.log_message("✅ 分析完成!")

        except Exception as e:
            self.log_message(f"❌ 分析出错: {e}")

def main():
    """主函数"""
    print("🔍 Web PTZ协议分析工具")
    print("=" * 50)

    analyzer = WebPTZAnalyzer()

    print(f"📡 目标摄像头: {analyzer.camera_ip}")
    print(f"🔑 认证信息: {analyzer.username}/***")
    print()

    try:
        analyzer.run_analysis()
    except KeyboardInterrupt:
        print("\n⏹️  用户中断分析")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()