#!/usr/bin/env python3
"""
简单PTZ协议分析工具
支持HTTP和HTTPS，避免SSL问题
"""

import requests
import time
import re
from datetime import datetime
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SimplePTZAnalyzer:
    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password

        # 尝试HTTP和HTTPS
        self.protocols = ["http", "https"]
        self.working_protocol = None

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"ptz_analysis_{self.timestamp}.txt"

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def test_connection(self):
        """测试哪个协议可以连接"""
        self.log("🔍 测试连接协议...")

        for protocol in self.protocols:
            test_url = f"{protocol}://{self.camera_ip}/"

            try:
                session = requests.Session()
                if protocol == "https":
                    # 设置更宽松的SSL配置
                    session.verify = False
                    import ssl
                    session.mount('https://', requests.adapters.HTTPAdapter())

                response = session.get(test_url,
                                     auth=(self.username, self.password),
                                     timeout=5)

                if response.status_code in [200, 401, 403]:
                    self.working_protocol = protocol
                    self.log(f"   ✅ {protocol.upper()} 连接成功 (状态: {response.status_code})")
                    return True

            except Exception as e:
                self.log(f"   ❌ {protocol.upper()} 连接失败: {str(e)[:50]}...")

        return False

    def analyze_page(self, path):
        """分析特定页面"""
        if not self.working_protocol:
            return None

        url = f"{self.working_protocol}://{self.camera_ip}{path}"

        try:
            session = requests.Session()
            if self.working_protocol == "https":
                session.verify = False

            response = session.get(url,
                                 auth=(self.username, self.password),
                                 timeout=10)

            if response.status_code == 200:
                content = response.text

                # 查找PTZ相关内容
                ptz_patterns = [
                    r'ptz[^"\']*["\']([^"\']+)["\']',  # PTZ相关URL
                    r'["\']([^"\']*ptz[^"\']*)["\']',  # 包含PTZ的字符串
                    r'function[^{]*ptz[^{]*{',        # PTZ函数
                    r'move[^"\']*["\']([^"\']+)["\']', # move相关
                    r'control[^"\']*["\']([^"\']+)["\']', # control相关
                ]

                found_items = []
                for pattern in ptz_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    found_items.extend(matches)

                if found_items:
                    self.log(f"   📍 发现PTZ相关内容: {list(set(found_items))}")

                    # 保存页面
                    filename = f"page_{path.replace('/', '_')}_{self.timestamp}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.log(f"   💾 页面已保存: {filename}")

                return content

        except Exception as e:
            self.log(f"   ❌ 无法分析 {path}: {str(e)[:50]}...")

        return None

    def manual_ptz_test(self):
        """手动PTZ测试"""
        if not self.working_protocol:
            self.log("❌ 无可用协议")
            return

        self.log("🎮 开始手动PTZ测试...")

        # 常见的PTZ命令URL模式
        test_urls = [
            "/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5",
            "/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=0&arg2=5",
            "/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=0&arg2=5",
            "/cgi-bin/ptz.cgi?action=start&channel=0&code=Down&arg1=0&arg2=5",
            "/api/ptz?cmd=left&speed=3",
            "/api/ptz?cmd=right&speed=3",
            "/control?move=left&speed=50",
            "/control?move=right&speed=50",
        ]

        session = requests.Session()
        if self.working_protocol == "https":
            session.verify = False

        for test_url in test_urls:
            url = f"{self.working_protocol}://{self.camera_ip}{test_url}"

            try:
                response = session.get(url,
                                     auth=(self.username, self.password),
                                     timeout=5)
                self.log(f"   测试: {test_url} -> {response.status_code}")

                if response.status_code == 200:
                    self.log(f"     响应: {response.text[:100]}...")

            except Exception as e:
                self.log(f"   测试: {test_url} -> 错误: {str(e)[:30]}...")

            time.sleep(0.5)

    def generate_test_commands(self):
        """生成测试命令"""
        if not self.working_protocol:
            return

        self.log("📋 生成测试命令...")

        cmd_file = f"ptz_test_commands_{self.timestamp}.sh"

        base_url = f"{self.working_protocol}://{self.camera_ip}"
        auth = f"-u {self.username}:{self.password}"
        ssl_flag = "-k" if self.working_protocol == "https" else ""

        commands = [
            f'curl {ssl_flag} {auth} "{base_url}/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5"',
            f'curl {ssl_flag} {auth} "{base_url}/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=0&arg2=5"',
            f'curl {ssl_flag} {auth} "{base_url}/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=0&arg2=5"',
            f'curl {ssl_flag} {auth} "{base_url}/cgi-bin/ptz.cgi?action=start&channel=0&code=Down&arg1=0&arg2=5"',
            f'curl {ssl_flag} {auth} "{base_url}/api/ptz?cmd=left&speed=3"',
            f'curl {ssl_flag} {auth} -X POST -d "action=moveLeft&speed=3" "{base_url}/api/ptz"',
            f'curl {ssl_flag} {auth} -X POST -H "Content-Type: application/json" -d \'{{"command":"moveLeft","speed":3}}\' "{base_url}/api/ptz"',
        ]

        with open(cmd_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# PTZ测试命令\n\n")
            for cmd in commands:
                f.write(f"echo '测试: {cmd}'\n")
                f.write(f"{cmd}\n")
                f.write("sleep 1\n\n")

        self.log(f"💾 测试命令已保存: {cmd_file}")

    def run_analysis(self):
        """运行分析"""
        self.log("🚀 开始PTZ协议分析...")

        # 1. 测试连接
        if not self.test_connection():
            self.log("❌ 无法连接到摄像头")
            return

        # 2. 分析主要页面
        pages_to_analyze = [
            "/",
            "/index.html",
            "/setting.html",
            "/main.html",
            "/control.html"
        ]

        for page in pages_to_analyze:
            self.log(f"🌐 分析页面: {page}")
            self.analyze_page(page)

        # 3. 手动PTZ测试
        self.manual_ptz_test()

        # 4. 生成测试命令
        self.generate_test_commands()

        self.log("✅ 分析完成!")

def main():
    print("🔍 简单PTZ协议分析工具")
    print("=" * 50)

    analyzer = SimplePTZAnalyzer()

    print(f"📡 目标摄像头: {analyzer.camera_ip}")
    print(f"🔑 认证信息: {analyzer.username}/***")
    print()

    try:
        analyzer.run_analysis()
        print(f"\n📝 详细日志请查看: {analyzer.log_file}")

    except KeyboardInterrupt:
        print("\n⏹️  用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()