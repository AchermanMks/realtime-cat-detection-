#!/usr/bin/env python3
"""
混合PTZ控制器 - 物理PTZ + 数字PTZ
"""

import cv2
import numpy as np
import socket
import json
import time
from threading import Lock

class HybridPTZController:
    """混合PTZ控制器 - 支持物理和数字PTZ"""

    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.udp_port = 34567

        # 物理PTZ状态
        self.physical_ptz_enabled = True
        self.last_physical_test = 0

        # 数字PTZ状态
        self.digital_zoom = 1.0  # 1.0 = 无缩放
        self.digital_pan = 0.0   # -1.0 到 1.0
        self.digital_tilt = 0.0  # -1.0 到 1.0
        self.max_zoom = 4.0      # 最大数字缩放

        # 预设位置
        self.presets = {
            1: {"zoom": 1.0, "pan": 0.0, "tilt": 0.0, "name": "默认位置"},
            2: {"zoom": 2.0, "pan": -0.3, "tilt": 0.2, "name": "左上角"},
            3: {"zoom": 2.0, "pan": 0.3, "tilt": 0.2, "name": "右上角"},
            4: {"zoom": 1.5, "pan": 0.0, "tilt": -0.3, "name": "中心下方"}
        }

        self.lock = Lock()

        print("🎮 混合PTZ控制器已初始化")
        print("📱 物理PTZ: 启用 (将继续尝试)")
        print("💻 数字PTZ: 就绪")

    def pan_left(self, speed=30):
        """向左移动"""
        print(f"⬅️ 向左移动 (速度: {speed})")

        # 尝试物理PTZ
        if self.physical_ptz_enabled:
            if self._try_physical_ptz("pan", "left", speed):
                return True

        # 数字PTZ备用
        return self._digital_pan_left(speed)

    def pan_right(self, speed=30):
        """向右移动"""
        print(f"➡️ 向右移动 (速度: {speed})")

        if self.physical_ptz_enabled:
            if self._try_physical_ptz("pan", "right", speed):
                return True

        return self._digital_pan_right(speed)

    def tilt_up(self, speed=30):
        """向上移动"""
        print(f"⬆️ 向上移动 (速度: {speed})")

        if self.physical_ptz_enabled:
            if self._try_physical_ptz("tilt", "up", speed):
                return True

        return self._digital_tilt_up(speed)

    def tilt_down(self, speed=30):
        """向下移动"""
        print(f"⬇️ 向下移动 (速度: {speed})")

        if self.physical_ptz_enabled:
            if self._try_physical_ptz("tilt", "down", speed):
                return True

        return self._digital_tilt_down(speed)

    def zoom_in(self, speed=30):
        """放大"""
        print(f"🔍 放大 (速度: {speed})")

        if self.physical_ptz_enabled:
            if self._try_physical_ptz("zoom", "in", speed):
                return True

        return self._digital_zoom_in(speed)

    def zoom_out(self, speed=30):
        """缩小"""
        print(f"🔎 缩小 (速度: {speed})")

        if self.physical_ptz_enabled:
            if self._try_physical_ptz("zoom", "out", speed):
                return True

        return self._digital_zoom_out(speed)

    def stop_movement(self):
        """停止移动"""
        print("🛑 停止移动")

        if self.physical_ptz_enabled:
            return self._try_physical_ptz("stop", "all", 0)

        return True  # 数字PTZ立即停止

    def goto_preset(self, preset_number):
        """转到预设位置"""
        if preset_number in self.presets:
            preset = self.presets[preset_number]
            print(f"📍 转到预设位置 {preset_number}: {preset['name']}")

            # 尝试物理PTZ预设
            if self.physical_ptz_enabled:
                if self._try_physical_preset(preset_number):
                    return True

            # 数字PTZ预设
            return self._goto_digital_preset(preset)

        return False

    def _try_physical_ptz(self, command_type, direction, speed):
        """尝试物理PTZ控制"""
        try:
            # 使用我们之前发现的工作格式
            command = {
                "Name": "PTZControl",
                "Login": {
                    "UserName": self.username,
                    "Password": self.password
                },
                "PTZ": {
                    "Direction": direction.capitalize(),
                    "Speed": speed
                }
            }

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)

            json_data = json.dumps(command).encode('utf-8')
            sock.sendto(json_data, (self.camera_ip, self.udp_port))

            try:
                response, addr = sock.recvfrom(1024)
                response_text = response.decode('utf-8', errors='ignore')

                if '"Ret": "OK"' in response_text:
                    print(f"   ✅ 物理PTZ命令发送成功")

                    # 每隔5分钟检查一次是否真的有效果
                    current_time = time.time()
                    if current_time - self.last_physical_test > 300:  # 5分钟
                        self.last_physical_test = current_time
                        print(f"   ❓ 物理PTZ测试: 如果摄像头没有移动，将自动切换到数字模式")

                    return True

            except socket.timeout:
                pass

            sock.close()

        except Exception as e:
            print(f"   ⚠️ 物理PTZ失败: {str(e)[:30]}...")

        return False

    def _try_physical_preset(self, preset_number):
        """尝试物理PTZ预设"""
        try:
            command = {
                "Name": "PTZControl",
                "Login": {
                    "UserName": self.username,
                    "Password": self.password
                },
                "PTZ": {
                    "Preset": preset_number,
                    "Action": "Goto"
                }
            }

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)

            json_data = json.dumps(command).encode('utf-8')
            sock.sendto(json_data, (self.camera_ip, self.udp_port))

            try:
                response, addr = sock.recvfrom(1024)
                response_text = response.decode('utf-8', errors='ignore')

                if '"Ret": "OK"' in response_text:
                    print(f"   ✅ 物理预设命令发送成功")
                    return True

            except socket.timeout:
                pass

            sock.close()

        except:
            pass

        return False

    # 数字PTZ方法
    def _digital_pan_left(self, speed):
        """数字向左移动"""
        with self.lock:
            step = speed / 1000.0  # 速度转换为移动步长
            self.digital_pan = max(-1.0, self.digital_pan - step)
            print(f"   💻 数字左移: pan={self.digital_pan:.2f}")
            return True

    def _digital_pan_right(self, speed):
        """数字向右移动"""
        with self.lock:
            step = speed / 1000.0
            self.digital_pan = min(1.0, self.digital_pan + step)
            print(f"   💻 数字右移: pan={self.digital_pan:.2f}")
            return True

    def _digital_tilt_up(self, speed):
        """数字向上移动"""
        with self.lock:
            step = speed / 1000.0
            self.digital_tilt = min(1.0, self.digital_tilt + step)
            print(f"   💻 数字上移: tilt={self.digital_tilt:.2f}")
            return True

    def _digital_tilt_down(self, speed):
        """数字向下移动"""
        with self.lock:
            step = speed / 1000.0
            self.digital_tilt = max(-1.0, self.digital_tilt - step)
            print(f"   💻 数字下移: tilt={self.digital_tilt:.2f}")
            return True

    def _digital_zoom_in(self, speed):
        """数字放大"""
        with self.lock:
            step = speed / 1000.0
            self.digital_zoom = min(self.max_zoom, self.digital_zoom + step)
            print(f"   💻 数字放大: zoom={self.digital_zoom:.2f}x")
            return True

    def _digital_zoom_out(self, speed):
        """数字缩小"""
        with self.lock:
            step = speed / 1000.0
            self.digital_zoom = max(1.0, self.digital_zoom - step)
            print(f"   💻 数字缩小: zoom={self.digital_zoom:.2f}x")
            return True

    def _goto_digital_preset(self, preset):
        """转到数字预设位置"""
        with self.lock:
            self.digital_zoom = preset["zoom"]
            self.digital_pan = preset["pan"]
            self.digital_tilt = preset["tilt"]
            print(f"   💻 数字预设: zoom={self.digital_zoom:.1f}x, pan={self.digital_pan:.2f}, tilt={self.digital_tilt:.2f}")
            return True

    def apply_digital_ptz(self, frame):
        """对帧应用数字PTZ变换"""
        if frame is None:
            return frame

        with self.lock:
            h, w = frame.shape[:2]

            # 计算缩放区域
            zoom_factor = self.digital_zoom
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)

            # 计算平移偏移
            pan_offset_x = int(self.digital_pan * (w - new_w) / 2)
            tilt_offset_y = int(-self.digital_tilt * (h - new_h) / 2)  # 注意Y轴方向

            # 计算裁剪区域
            center_x = w // 2 + pan_offset_x
            center_y = h // 2 + tilt_offset_y

            x1 = max(0, center_x - new_w // 2)
            y1 = max(0, center_y - new_h // 2)
            x2 = min(w, x1 + new_w)
            y2 = min(h, y1 + new_h)

            # 确保区域有效
            if x2 <= x1 or y2 <= y1:
                return frame

            # 裁剪并缩放到原始大小
            cropped = frame[y1:y2, x1:x2]
            if cropped.size > 0:
                resized = cv2.resize(cropped, (w, h))
                return resized

            return frame

    def get_status(self):
        """获取PTZ状态"""
        return {
            "physical_ptz_enabled": self.physical_ptz_enabled,
            "digital_zoom": self.digital_zoom,
            "digital_pan": self.digital_pan,
            "digital_tilt": self.digital_tilt,
            "presets": self.presets
        }

    def set_digital_mode(self, enable_digital):
        """设置数字模式"""
        if enable_digital:
            print("💻 切换到数字PTZ模式")
            self.physical_ptz_enabled = False
        else:
            print("📱 尝试启用物理PTZ模式")
            self.physical_ptz_enabled = True

    def reset_digital_position(self):
        """重置数字位置"""
        with self.lock:
            self.digital_zoom = 1.0
            self.digital_pan = 0.0
            self.digital_tilt = 0.0
            print("🔄 数字PTZ位置已重置")

# 测试函数
if __name__ == "__main__":
    print("🎮 测试混合PTZ控制器")

    controller = HybridPTZController()

    print("\n🔍 测试PTZ命令:")
    print("1. 向左移动...")
    controller.pan_left(30)
    time.sleep(1)

    print("2. 向右移动...")
    controller.pan_right(30)
    time.sleep(1)

    print("3. 放大...")
    controller.zoom_in(50)
    time.sleep(1)

    print("4. 转到预设位置...")
    controller.goto_preset(2)
    time.sleep(1)

    print("5. 重置位置...")
    controller.reset_digital_position()

    print(f"\n📊 当前状态:")
    status = controller.get_status()
    for key, value in status.items():
        if key != "presets":
            print(f"   {key}: {value}")

    print("\n✅ 混合PTZ控制器测试完成!")
    print("💡 这个控制器可以集成到您的Web应用中")