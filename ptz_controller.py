import requests
import json
import time
from robot_vision_config import Config

class PTZController:
    """云台控制器类"""

    def __init__(self):
        self.base_url = Config.PTZ_BASE_URL
        self.username = Config.PTZ_USERNAME
        self.password = Config.PTZ_PASSWORD
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.current_position = {"pan": 0, "tilt": 0, "zoom": 1}

        # 设置连接超时
        self.session.timeout = 10

    def _send_command(self, endpoint, params=None):
        """发送控制命令到云台"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, params=params, timeout=5)

            if response.status_code == 200:
                return {"success": True, "response": response.text}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def pan_left(self, speed=None):
        """向左移动"""
        speed = speed or Config.PAN_SPEED
        print(f"云台向左移动，速度: {speed}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "Left",
            "arg1": speed,
            "arg2": 0,
            "arg3": 0
        })

    def pan_right(self, speed=None):
        """向右移动"""
        speed = speed or Config.PAN_SPEED
        print(f"云台向右移动，速度: {speed}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "Right",
            "arg1": speed,
            "arg2": 0,
            "arg3": 0
        })

    def tilt_up(self, speed=None):
        """向上移动"""
        speed = speed or Config.TILT_SPEED
        print(f"云台向上移动，速度: {speed}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "Up",
            "arg1": 0,
            "arg2": speed,
            "arg3": 0
        })

    def tilt_down(self, speed=None):
        """向下移动"""
        speed = speed or Config.TILT_SPEED
        print(f"云台向下移动，速度: {speed}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "Down",
            "arg1": 0,
            "arg2": speed,
            "arg3": 0
        })

    def zoom_in(self, speed=None):
        """放大"""
        speed = speed or Config.ZOOM_SPEED
        print(f"云台放大，速度: {speed}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "ZoomTele",
            "arg1": 0,
            "arg2": 0,
            "arg3": speed
        })

    def zoom_out(self, speed=None):
        """缩小"""
        speed = speed or Config.ZOOM_SPEED
        print(f"云台缩小，速度: {speed}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "ZoomWide",
            "arg1": 0,
            "arg2": 0,
            "arg3": speed
        })

    def stop(self):
        """停止所有移动"""
        print("云台停止移动")
        return self._send_command("ptz.cgi", {
            "action": "stop",
            "channel": 0,
            "code": "Stop",
            "arg1": 0,
            "arg2": 0,
            "arg3": 0
        })

    def move_to_preset(self, preset_id):
        """移动到预设位置"""
        print(f"云台移动到预设位置: {preset_id}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "GotoPreset",
            "arg1": preset_id,
            "arg2": 0,
            "arg3": 0
        })

    def set_preset(self, preset_id):
        """设置预设位置"""
        print(f"设置预设位置: {preset_id}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "SetPreset",
            "arg1": preset_id,
            "arg2": 0,
            "arg3": 0
        })

    def auto_scan(self, pattern=1):
        """开始自动扫描"""
        print(f"开始自动扫描模式: {pattern}")
        return self._send_command("ptz.cgi", {
            "action": "start",
            "channel": 0,
            "code": "AutoPan",
            "arg1": pattern,
            "arg2": 0,
            "arg3": 0
        })

    def track_object(self, x, y, frame_width, frame_height):
        """
        根据对象位置调整云台方向
        x, y: 对象在图像中的坐标
        frame_width, frame_height: 图像尺寸
        """
        center_x = frame_width // 2
        center_y = frame_height // 2

        # 计算偏移量
        offset_x = x - center_x
        offset_y = y - center_y

        # 设置死区，避免微小抖动
        dead_zone = 50

        actions = []

        # 水平方向调整
        if abs(offset_x) > dead_zone:
            if offset_x > 0:  # 目标在右侧
                actions.append(("pan_right", abs(offset_x) // 10))
            else:  # 目标在左侧
                actions.append(("pan_left", abs(offset_x) // 10))

        # 垂直方向调整
        if abs(offset_y) > dead_zone:
            if offset_y > 0:  # 目标在下方
                actions.append(("tilt_down", abs(offset_y) // 10))
            else:  # 目标在上方
                actions.append(("tilt_up", abs(offset_y) // 10))

        return actions

    def test_connection(self):
        """测试云台连接"""
        print("测试云台连接...")
        result = self._send_command("ptz.cgi", {
            "action": "getStatus",
            "channel": 0
        })

        if result["success"]:
            print("✅ 云台连接正常")
            return True
        else:
            print(f"❌ 云台连接失败: {result['error']}")
            return False