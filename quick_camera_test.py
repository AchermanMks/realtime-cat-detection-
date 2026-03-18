#!/usr/bin/env python3
"""
快速摄像头测试 - 验证连接和基本显示
"""

import cv2
import time
import numpy as np
from datetime import datetime
from robot_vision_config import Config

class QuickCameraTest:
    def __init__(self):
        self.camera_url = Config.RTSP_URL
        self.backup_camera = 0
        self.cap = None
        self.running = False

    def test_camera_connection(self):
        """测试摄像头连接"""
        print("📡 测试摄像头连接...")

        # 尝试主摄像头
        print(f"🎥 尝试连接: {self.camera_url}")
        cap = cv2.VideoCapture(self.camera_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"✅ 主摄像头连接成功: {w}x{h} @{fps:.1f}fps")
            cap.release()
            return True, self.camera_url
        else:
            cap.release()
            print("⚠️ 主摄像头连接失败，尝试本地摄像头...")

            # 尝试本地摄像头
            cap = cv2.VideoCapture(self.backup_camera)
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"✅ 本地摄像头连接成功: {w}x{h}")
                cap.release()
                return True, self.backup_camera
            else:
                cap.release()
                print("❌ 所有摄像头连接失败")
                return False, None

    def simple_display_test(self):
        """简单显示测试"""
        success, camera_source = self.test_camera_connection()
        if not success:
            print("❌ 无法连接任何摄像头")
            return False

        print("🎬 启动实时显示测试...")
        print("💡 按 'q' 键退出，'s' 键截图")

        self.cap = cv2.VideoCapture(camera_source)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # 设置窗口
        window_name = "🎥 摄像头连接测试"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)

        frame_count = 0
        start_time = time.time()

        while True:
            ret, frame = self.cap.read()

            if not ret or frame is None:
                print("⚠️ 读取帧失败")
                time.sleep(0.1)
                continue

            frame_count += 1
            current_time = time.time()

            # 计算FPS
            elapsed = current_time - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
            else:
                fps = 0

            # 添加信息叠加
            display_frame = self.add_basic_overlay(frame.copy(), fps, frame_count)

            # 显示
            cv2.imshow(window_name, display_frame)

            # 处理按键
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # Q或ESC退出
                break
            elif key == ord('s'):  # 截图
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"test_screenshot_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"📸 截图保存: {filename}")

        # 清理
        self.cap.release()
        cv2.destroyAllWindows()

        # 显示统计
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0

        print(f"\n📊 测试统计:")
        print(f"   运行时间: {total_time:.1f}秒")
        print(f"   总帧数: {frame_count}")
        print(f"   平均FPS: {avg_fps:.1f}")
        print("✅ 摄像头显示测试完成")

        return True

    def add_basic_overlay(self, frame, fps, frame_count):
        """添加基本信息叠加"""
        h, w = frame.shape[:2]

        # 创建信息面板
        overlay_height = 80
        overlay = np.zeros((overlay_height, w, 3), dtype=np.uint8)
        overlay[:] = (40, 40, 40)  # 深灰色背景

        # 字体设置
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1

        # 时间信息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(overlay, f"🎥 摄像头测试  📅 {current_time}",
                   (10, 25), font, font_scale, (0, 255, 255), thickness)

        # FPS和帧数
        cv2.putText(overlay, f"📊 FPS: {fps:.1f}  📈 帧数: {frame_count}",
                   (10, 50), font, font_scale, (0, 255, 0), thickness)

        # 控制说明
        cv2.putText(overlay, "控制: Q-退出 S-截图",
                   (w-200, 50), font, 0.5, (200, 200, 200), 1)

        # 合并
        result = np.vstack((overlay, frame))
        return result

def main():
    """主函数"""
    print("🎥 快速摄像头连接测试")
    print("=" * 40)

    tester = QuickCameraTest()

    # 先测试连接
    success, _ = tester.test_camera_connection()
    if not success:
        return

    print("\n🎬 启动实时显示测试...")

    # 启动显示测试
    tester.simple_display_test()

if __name__ == "__main__":
    main()