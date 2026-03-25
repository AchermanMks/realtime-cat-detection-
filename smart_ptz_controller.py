#!/usr/bin/env python3
"""
智能PTZ控制器 - 自动处理SessionId过期
解决SessionId自动刷新和过期重新登录的问题
"""

import requests
import json
import time
import urllib3
from datetime import datetime, timedelta
import threading

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SmartPTZController:
    """智能PTZ控制器 - 自动处理SessionId过期"""

    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.base_url = f"https://{camera_ip}"
        self.api_endpoint = "/ipc/grpc_cmd"

        # 会话管理
        self.session = requests.Session()
        self.session.verify = False
        self.session_id = None
        self.session_expire_time = None
        self.session_duration = 3600  # 假设SessionId有效期1小时

        # 配置SSL适配器以支持旧设备
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context

        class LegacySSLAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)

        self.session.mount('https://', LegacySSLAdapter())

        # 登录锁，避免并发登录
        self.login_lock = threading.Lock()
        self.last_login_attempt = 0
        self.login_cooldown = 5  # 登录冷却时间5秒

        # 设置通用请求头
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json; charset=UTF-8',
            'Origin': f'https://{camera_ip}',
            'Referer': f'https://{camera_ip}/ptzManager/ptzControl.html',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        })

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")

    def is_session_expired(self):
        """检查SessionId是否过期"""
        if not self.session_id:
            return True

        if self.session_expire_time:
            # 提前5分钟判断过期，预防性刷新
            return datetime.now() >= (self.session_expire_time - timedelta(minutes=5))

        return False

    def detect_auth_error(self, response):
        """检测认证错误"""
        # 检查HTTP状态码
        if response.status_code in [401, 403]:
            return True

        # 检查响应内容中的错误指示
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
                # 检查常见的认证失败响应
                if isinstance(result, dict):
                    error_indicators = ['unauthorized', 'invalid session', 'login required', 'auth failed']
                    result_str = json.dumps(result).lower()
                    if any(indicator in result_str for indicator in error_indicators):
                        return True

                    # 检查result字段，通常0表示成功，非0表示失败
                    if result.get('result', 0) != 0:
                        error_msg = result.get('error', result.get('message', ''))
                        if 'session' in str(error_msg).lower() or 'auth' in str(error_msg).lower():
                            return True
        except:
            pass

        return False

    def auto_login(self, force_refresh=False):
        """自动登录获取SessionId"""
        with self.login_lock:
            # 检查是否需要登录
            if not force_refresh and not self.is_session_expired():
                return True

            # 登录冷却检查
            if time.time() - self.last_login_attempt < self.login_cooldown:
                self.log(f"登录冷却中，跳过 ({self.login_cooldown}秒)")
                return False

            self.last_login_attempt = time.time()
            self.log(f"🔐 {'强制刷新' if force_refresh else '自动'}登录摄像头: {self.camera_ip}")

            # 尝试多种登录方式
            login_methods = [
                self._login_via_api,
                self._login_via_web,
                self._login_via_fallback
            ]

            for i, method in enumerate(login_methods):
                try:
                    self.log(f"尝试登录方式 {i+1}/{len(login_methods)}")
                    if method():
                        # 设置SessionId过期时间
                        self.session_expire_time = datetime.now() + timedelta(seconds=self.session_duration)
                        self.session.headers['SessionId'] = self.session_id
                        self.log(f"✅ 登录成功，SessionId: {self.session_id[:16]}...")
                        return True
                except Exception as e:
                    self.log(f"登录方式 {i+1} 失败: {e}")
                    continue

            self.log("❌ 所有登录方式都失败了")
            return False

    def _login_via_api(self):
        """通过API登录"""
        login_data = {
            "username": self.username,
            "password": self.password
        }

        response = self.session.post(
            f"{self.base_url}/ipc/login",
            json=login_data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('result') == 0:
                param = result.get('param', {})
                session_id = param.get('sessionid')
                if session_id:
                    self.session_id = session_id
                    return True

        return False

    def _login_via_web(self):
        """通过Web页面登录"""
        # 访问PTZ控制页面
        response = self.session.get(
            f"{self.base_url}/ptzManager/ptzControl.html",
            auth=(self.username, self.password),
            timeout=10
        )

        if response.status_code == 200:
            # 检查cookies中的SessionId
            for cookie in self.session.cookies:
                if 'session' in cookie.name.lower():
                    self.session_id = cookie.value
                    return True

        return False

    def _login_via_fallback(self):
        """后备登录方式 - 使用已知的SessionId模式"""
        # 这是一个临时方案，使用已知有效的SessionId格式
        # 在实际应用中，你可能需要实现更复杂的SessionId获取逻辑
        known_sessions = [
            "1DD2682BD160DCAC9712EA6FC1452D6",
            "D1D66678A96617EF9555E42E67349E2"
        ]

        for session_id in known_sessions:
            # 测试SessionId是否有效
            if self._test_session_id(session_id):
                self.session_id = session_id
                return True

        return False

    def _test_session_id(self, session_id):
        """测试SessionId是否有效"""
        test_headers = self.session.headers.copy()
        test_headers['SessionId'] = session_id

        try:
            response = self.session.post(
                f"{self.base_url}{self.api_endpoint}",
                json={"method": "ptz_move_stop", "param": {"channelid": 0}},
                headers=test_headers,
                timeout=5
            )
            return response.status_code == 200 and not self.detect_auth_error(response)
        except:
            return False

    def _send_ptz_command_with_retry(self, method, params, max_retries=2):
        """发送PTZ命令，自动重试"""
        for attempt in range(max_retries + 1):
            # 检查SessionId是否需要刷新
            if self.is_session_expired():
                if not self.auto_login():
                    self.log("❌ 无法获取有效SessionId")
                    return False

            payload = {
                "method": method,
                "param": {
                    "channelid": 0,
                    **params
                }
            }

            try:
                self.log(f"📤 发送PTZ命令 (尝试 {attempt + 1}): {method}")

                response = self.session.post(
                    f"{self.base_url}{self.api_endpoint}",
                    json=payload,
                    timeout=10
                )

                self.log(f"📥 响应状态: {response.status_code}")

                if response.status_code == 200:
                    # 检查是否是认证错误
                    if self.detect_auth_error(response):
                        self.log(f"🔄 检测到认证错误，尝试重新登录 (尝试 {attempt + 1})")
                        self.session_id = None  # 清除无效SessionId
                        if attempt < max_retries:
                            if self.auto_login(force_refresh=True):
                                continue  # 重试
                        return False

                    # 解析响应
                    try:
                        result = response.json()
                        self.log(f"📄 响应: {result}")
                        return result
                    except:
                        self.log(f"📄 响应: {response.text[:100]}...")
                        return True

                else:
                    self.log(f"❌ 请求失败: HTTP {response.status_code}")
                    if attempt < max_retries and response.status_code in [401, 403]:
                        # HTTP认证错误，尝试重新登录
                        self.session_id = None
                        if self.auto_login(force_refresh=True):
                            continue

                    return False

            except Exception as e:
                self.log(f"❌ 发送命令异常: {e}")
                if attempt < max_retries:
                    time.sleep(1)  # 短暂等待后重试
                    continue
                return False

        return False

    # PTZ控制方法 - 使用自动重试机制
    def move_left(self, speed=120):
        """向左移动"""
        return self._send_ptz_command_with_retry("ptz_move_start", {"panLeft": speed})

    def move_right(self, speed=120):
        """向右移动"""
        return self._send_ptz_command_with_retry("ptz_move_start", {"panRight": speed})

    def move_up(self, speed=120):
        """向上移动"""
        return self._send_ptz_command_with_retry("ptz_move_start", {"tiltUp": speed})

    def move_down(self, speed=120):
        """向下移动"""
        return self._send_ptz_command_with_retry("ptz_move_start", {"tiltUp": -speed})

    def stop_move(self):
        """停止移动"""
        return self._send_ptz_command_with_retry("ptz_move_stop", {})

    def zoom_in(self, speed=120):
        """放大"""
        return self._send_ptz_command_with_retry("ptz_move_start", {"zoomIn": speed})

    def zoom_out(self, speed=120):
        """缩小"""
        return self._send_ptz_command_with_retry("ptz_move_start", {"zoomOut": speed})

    def move_for_duration(self, direction, speed=120, duration=1.0):
        """移动指定时间后停止"""
        direction_map = {
            'left': self.move_left,
            'right': self.move_right,
            'up': self.move_up,
            'down': self.move_down
        }

        if direction not in direction_map:
            self.log(f"❌ 不支持的方向: {direction}")
            return False

        # 开始移动
        if direction_map[direction](speed):
            time.sleep(duration)
            # 停止移动
            return self.stop_move()

        return False

    def get_session_status(self):
        """获取当前SessionId状态"""
        status = {
            'session_id': self.session_id,
            'is_expired': self.is_session_expired(),
            'expire_time': self.session_expire_time.isoformat() if self.session_expire_time else None,
            'time_remaining': None
        }

        if self.session_expire_time:
            remaining = self.session_expire_time - datetime.now()
            status['time_remaining'] = str(remaining) if remaining.total_seconds() > 0 else "已过期"

        return status

def test_smart_controller():
    """测试智能控制器"""
    print("🧪 智能PTZ控制器测试")
    print("=" * 50)

    controller = SmartPTZController()

    # 显示初始状态
    status = controller.get_session_status()
    print(f"📊 初始状态: {json.dumps(status, indent=2, ensure_ascii=False)}")

    # 自动登录
    if controller.auto_login():
        print("\n✅ 自动登录成功")

        # 显示登录后状态
        status = controller.get_session_status()
        print(f"📊 登录后状态: {json.dumps(status, indent=2, ensure_ascii=False)}")

        # 测试PTZ控制
        print("\n🎯 测试PTZ控制...")
        directions = ['left', 'right', 'up', 'down']

        for direction in directions:
            print(f"   📍 测试 {direction} 移动...")
            result = controller.move_for_duration(direction, 120, 0.5)
            print(f"   结果: {'✅ 成功' if result else '❌ 失败'}")
            time.sleep(0.5)

        print("\n✅ 智能控制器测试完成")
    else:
        print("❌ 自动登录失败")

if __name__ == "__main__":
    test_smart_controller()