#!/usr/bin/env python3
"""
自动登录Web管理界面并配置PTZ设置
"""

import requests
import re
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class JovisionWebManager:
    def __init__(self, camera_ip, username, password):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False

        # 配置SSL适配器来处理遗留SSL
        import ssl
        from urllib3.util.ssl_ import create_urllib3_context

        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')

        # 尝试HTTPS，如果失败则使用HTTP
        self.protocols = [f"https://{camera_ip}", f"http://{camera_ip}"]
        self.base_url = None
        self.login_success = False

    def login(self):
        """自动登录Web管理界面"""
        print("🔐 尝试登录Web管理界面...")
        print(f"👤 凭据: {self.username}/{self.password}")

        # 尝试不同的协议
        for protocol_url in self.protocols:
            print(f"📡 尝试协议: {protocol_url}")

            try:
                # 方法1: 基础认证
                self.session.auth = (self.username, self.password)
                response = self.session.get(protocol_url, timeout=10)

                if response.status_code == 200:
                    print("✅ 基础认证成功")
                    self.base_url = protocol_url
                    self.login_success = True
                    return True

            except Exception as e:
                print(f"⚠️ {protocol_url} 基础认证失败: {str(e)[:50]}...")

            # 方法2: 表单登录
            login_urls = [
                f"{protocol_url}/login.html",
                f"{protocol_url}/index.html",
                f"{protocol_url}/",
                f"{protocol_url}/web/login.html"
            ]

            for login_url in login_urls:
                if self._try_form_login(login_url, protocol_url):
                    return True

            # 方法3: API登录
            if self._try_api_login(protocol_url):
                return True

        print("❌ 所有协议和登录方法失败")
        return False

    def _try_form_login(self, login_url, protocol_url=None):
        """尝试表单登录"""
        try:
            print(f"🔍 尝试表单登录: {login_url}")
            response = self.session.get(login_url, timeout=5)

            if response.status_code != 200:
                return False

            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找登录表单
            forms = soup.find_all('form')
            for form in forms:
                action = form.get('action', '')

                # 构建登录数据
                login_data = {}

                # 查找用户名和密码字段
                for input_field in form.find_all('input'):
                    input_type = input_field.get('type', '').lower()
                    input_name = input_field.get('name', '')

                    if input_type in ['text', 'email'] or 'user' in input_name.lower():
                        login_data[input_name] = self.username
                    elif input_type == 'password' or 'pass' in input_name.lower():
                        login_data[input_name] = self.password
                    elif input_type == 'hidden':
                        login_data[input_name] = input_field.get('value', '')

                if login_data:
                    # 提交登录表单
                    submit_url = urljoin(login_url, action) if action else login_url

                    print(f"📝 提交登录表单: {login_data}")
                    login_response = self.session.post(submit_url, data=login_data, timeout=5)

                    if login_response.status_code == 200:
                        # 检查是否登录成功
                        if self._check_login_success(login_response.text):
                            print("✅ 表单登录成功")
                            self.base_url = protocol_url or login_url.split('/')[0:3]
                            if isinstance(self.base_url, list):
                                self.base_url = '://'.join([self.base_url[0], '/'.join(self.base_url[1:])])
                            self.login_success = True
                            return True

        except Exception as e:
            print(f"⚠️ 表单登录失败: {e}")

        return False

    def _try_api_login(self, protocol_url=None):
        """尝试API登录"""
        try:
            print("🔍 尝试API登录...")

            base = protocol_url or self.base_url or f"https://{self.camera_ip}"

            api_endpoints = [
                f"{base}/api/login",
                f"{base}/cgi-bin/login.cgi",
                f"{base}/login.cgi"
            ]

            login_data = {
                "username": self.username,
                "password": self.password
            }

            for endpoint in api_endpoints:
                try:
                    response = self.session.post(endpoint, data=login_data, timeout=5)
                    if response.status_code == 200:
                        response_text = response.text.lower()
                        if any(success_word in response_text for success_word in ['success', 'ok', 'true']):
                            print("✅ API登录成功")
                            self.base_url = base
                            self.login_success = True
                            return True
                except:
                    continue

        except Exception as e:
            print(f"⚠️ API登录失败: {e}")

        return False

    def _check_login_success(self, html_content):
        """检查登录是否成功"""
        content_lower = html_content.lower()

        # 登录失败的标识
        fail_indicators = ['login', 'password', 'username', '登录', '密码', 'unauthorized']

        # 登录成功的标识
        success_indicators = ['dashboard', 'config', 'setting', 'device', 'admin', '设备', '配置']

        fail_score = sum(1 for indicator in fail_indicators if indicator in content_lower)
        success_score = sum(1 for indicator in success_indicators if indicator in content_lower)

        return success_score > fail_score

    def find_ptz_settings(self):
        """查找PTZ设置页面"""
        if not self.login_success:
            print("❌ 需要先登录")
            return None

        print("\n🔍 查找PTZ设置页面...")

        # 可能的PTZ设置页面
        ptz_pages = [
            "/setting.html",
            "/device.html",
            "/ptz.html",
            "/control.html",
            "/config.html",
            "/admin.html",
            "/web/setting.html",
            "/web/device.html",
            "/web/ptz.html",
            "/system.html",
            "/advanced.html"
        ]

        ptz_settings_found = []

        for page_path in ptz_pages:
            try:
                url = f"{self.base_url}{page_path}"
                print(f"🔍 检查: {page_path}")

                response = self.session.get(url, timeout=5)

                if response.status_code == 200:
                    content = response.text
                    ptz_content = self._extract_ptz_content(content)

                    if ptz_content:
                        print(f"   ✅ 发现PTZ设置")
                        ptz_settings_found.append({
                            'url': url,
                            'content': content,
                            'ptz_settings': ptz_content
                        })

                        # 显示发现的设置
                        for setting in ptz_content[:3]:
                            print(f"      • {setting}")

            except Exception as e:
                print(f"   ❌ 访问失败: {str(e)[:30]}...")

        return ptz_settings_found

    def _extract_ptz_content(self, html_content):
        """提取PTZ相关内容"""
        ptz_keywords = ['ptz', '云台', 'pan', 'tilt', 'zoom', 'preset', '预设']

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            ptz_elements = []

            # 查找包含PTZ关键词的元素
            for element in soup.find_all(['input', 'select', 'label', 'span', 'div', 'td']):
                element_text = element.get_text().lower() if element.get_text() else ""
                element_attrs = " ".join([str(v) for v in element.attrs.values()]).lower()

                full_text = element_text + " " + element_attrs

                if any(keyword in full_text for keyword in ptz_keywords):
                    # 获取元素的完整信息
                    element_info = {
                        'tag': element.name,
                        'text': element.get_text().strip(),
                        'attrs': dict(element.attrs),
                        'parent_text': element.parent.get_text().strip() if element.parent else ""
                    }

                    if element_info['text'] or element_info['attrs']:
                        ptz_elements.append(element_info)

            # 去重并格式化
            unique_elements = []
            seen_texts = set()

            for element in ptz_elements:
                text_key = element['text'][:50] if element['text'] else str(element['attrs'])
                if text_key not in seen_texts and text_key.strip():
                    seen_texts.add(text_key)

                    formatted = f"{element['tag']}"
                    if element['text']:
                        formatted += f": {element['text'][:50]}"
                    if element['attrs']:
                        formatted += f" {element['attrs']}"

                    unique_elements.append(formatted)

            return unique_elements[:10]  # 返回前10个

        except Exception as e:
            print(f"⚠️ PTZ内容提取失败: {e}")
            return []

    def enable_ptz_settings(self, ptz_settings_pages):
        """尝试启用PTZ设置"""
        if not ptz_settings_pages:
            print("❌ 没有找到PTZ设置页面")
            return False

        print("\n🔧 尝试启用PTZ设置...")

        for page_info in ptz_settings_pages:
            print(f"\n🔍 处理页面: {page_info['url']}")

            if self._try_enable_ptz_on_page(page_info):
                print("✅ PTZ设置可能已启用")
                return True

        return False

    def _try_enable_ptz_on_page(self, page_info):
        """在特定页面上尝试启用PTZ"""
        try:
            soup = BeautifulSoup(page_info['content'], 'html.parser')

            # 查找PTZ相关的表单
            forms = soup.find_all('form')

            for form in forms:
                form_data = {}
                ptz_fields_found = False

                # 分析表单字段
                for input_elem in form.find_all(['input', 'select']):
                    name = input_elem.get('name', '')
                    input_type = input_elem.get('type', '').lower()

                    if name:
                        if any(keyword in name.lower() for keyword in ['ptz', '云台']):
                            ptz_fields_found = True

                            # 如果是checkbox或radio，尝试启用
                            if input_type in ['checkbox', 'radio']:
                                form_data[name] = '1'  # 或 'on', 'true'
                            # 如果是select，寻找启用选项
                            elif input_elem.name == 'select':
                                for option in input_elem.find_all('option'):
                                    if any(enable_word in option.get_text().lower()
                                          for enable_word in ['enable', 'on', '启用', 'true']):
                                        form_data[name] = option.get('value', '1')
                                        break
                            # 文本字段，设置默认值
                            elif input_type in ['text', 'number']:
                                if 'address' in name.lower() or '地址' in name.lower():
                                    form_data[name] = '1'
                                elif 'speed' in name.lower() or '速度' in name.lower():
                                    form_data[name] = '30'
                                elif 'port' in name.lower() or '端口' in name.lower():
                                    form_data[name] = '34567'
                        else:
                            # 其他字段保持原值
                            current_value = input_elem.get('value', '')
                            if current_value:
                                form_data[name] = current_value

                # 如果找到PTZ相关字段，提交表单
                if ptz_fields_found and form_data:
                    action = form.get('action', '')
                    submit_url = urljoin(page_info['url'], action) if action else page_info['url']

                    print(f"📝 提交PTZ配置: {form_data}")

                    response = self.session.post(submit_url, data=form_data, timeout=5)

                    if response.status_code == 200:
                        print("✅ PTZ配置提交成功")
                        return True

        except Exception as e:
            print(f"⚠️ PTZ设置失败: {e}")

        return False

    def test_ptz_after_config(self):
        """配置后测试PTZ功能"""
        print("\n🎮 配置后测试PTZ功能...")

        # 等待配置生效
        print("⏳ 等待配置生效 (5秒)...")
        time.sleep(5)

        # 使用我们之前发现的工作命令
        camera_ip = self.camera_ip
        port = 34567
        username = self.username
        password = self.password

        test_command = {
            "Name": "PTZControl",
            "Login": {
                "UserName": username,
                "Password": password
            },
            "PTZ": {"Direction": "Left", "Speed": 30}
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)

            json_data = json.dumps(test_command).encode('utf-8')
            sock.sendto(json_data, (camera_ip, port))

            try:
                response, addr = sock.recvfrom(1024)
                response_text = response.decode('utf-8', errors='ignore')
                print(f"📡 PTZ测试响应: {response_text}")

                if '"Ret": "OK"' in response_text:
                    print("✅ PTZ命令仍然返回OK")
                    print("📹 请观察摄像头是否现在开始移动...")
                    print("⏳ 等待观察 (5秒)...")
                    time.sleep(5)

                    # 发送停止命令
                    stop_command = {
                        "Name": "PTZControl",
                        "Login": {"UserName": username, "Password": password},
                        "PTZ": {"Direction": "Stop"}
                    }
                    stop_json = json.dumps(stop_command).encode('utf-8')
                    sock.sendto(stop_json, (camera_ip, port))
                    print("🛑 已发送停止命令")

                    return True

            except socket.timeout:
                print("⏳ PTZ测试无响应")

            sock.close()

        except Exception as e:
            print(f"❌ PTZ测试异常: {e}")

        return False

def main():
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    print("🎯 JOVISION自动Web管理界面PTZ配置")
    print("=" * 60)

    manager = JovisionWebManager(camera_ip, username, password)

    # 1. 登录
    if not manager.login():
        print("❌ 登录失败，无法继续")
        return

    # 2. 查找PTZ设置
    ptz_pages = manager.find_ptz_settings()

    if not ptz_pages:
        print("❌ 没有找到PTZ设置页面")
        print("💡 建议手动检查Web界面")
        return

    # 3. 尝试启用PTZ设置
    if manager.enable_ptz_settings(ptz_pages):
        print("\n🎉 PTZ配置操作完成!")

        # 4. 测试PTZ功能
        if manager.test_ptz_after_config():
            print("\n✅ PTZ功能测试完成")
            print("💡 如果摄像头开始移动，说明配置成功!")
        else:
            print("\n⚠️ PTZ功能仍需手动检查")
    else:
        print("\n⚠️ 自动配置失败，可能需要手动操作")

        print("\n📋 发现的PTZ相关页面:")
        for page in ptz_pages:
            print(f"🌐 {page['url']}")

if __name__ == "__main__":
    import socket
    main()