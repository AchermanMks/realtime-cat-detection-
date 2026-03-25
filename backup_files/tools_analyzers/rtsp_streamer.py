import cv2
import threading
import queue
import time
import numpy as np
from robot_vision_config import Config

class RTSPStreamer:
    """RTSP视频流获取器"""

    def __init__(self, rtsp_url=None):
        self.rtsp_url = rtsp_url or Config.RTSP_URL
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=Config.BUFFER_SIZE)
        self.running = False
        self.capture_thread = None
        self.last_frame = None
        self.frame_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()

        print(f"初始化RTSP流获取器: {self.rtsp_url}")

    def connect(self):
        """连接到RTSP流"""
        try:
            print("正在连接RTSP流...")
            self.cap = cv2.VideoCapture(self.rtsp_url)

            # 设置缓冲区大小
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 设置视频属性
            if Config.FRAME_WIDTH and Config.FRAME_HEIGHT:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.FRAME_HEIGHT)

            if Config.FPS:
                self.cap.set(cv2.CAP_PROP_FPS, Config.FPS)

            # 测试连接
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                print(f"✅ RTSP连接成功")
                print(f"   分辨率: {w}x{h}")
                print(f"   帧率: {self.cap.get(cv2.CAP_PROP_FPS)}")
                self.last_frame = test_frame
                return True
            else:
                print("❌ RTSP连接失败：无法获取测试帧")
                return False

        except Exception as e:
            print(f"❌ RTSP连接异常: {e}")
            return False

    def start_capture(self):
        """开始捕获视频流"""
        if not self.cap or not self.cap.isOpened():
            if not self.connect():
                return False

        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
        self.capture_thread.start()
        print("🎥 开始视频流捕获")
        return True

    def stop_capture(self):
        """停止捕获视频流"""
        print("停止视频流捕获...")
        self.running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=5)

        if self.cap:
            self.cap.release()

        # 清空队列
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        print("✅ 视频流已停止")

    def _capture_frames(self):
        """内部帧捕获循环"""
        skip_count = 0

        while self.running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()

                if not ret or frame is None:
                    # 如果是视频文件，尝试循环播放
                    if isinstance(self.rtsp_url, str) and not self.rtsp_url.startswith('rtsp'):
                        print("📹 视频播放完毕，重新开始...")
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置到开头
                        continue
                    else:
                        print("⚠️ 无法读取帧，尝试重连...")
                        time.sleep(1)
                        self._reconnect()
                        continue

                # 跳帧处理
                skip_count += 1
                if skip_count < Config.SKIP_FRAMES:
                    continue
                skip_count = 0

                # 更新帧计数和FPS
                self.frame_count += 1
                self.fps_counter += 1
                current_time = time.time()

                if current_time - self.last_fps_time >= 1.0:
                    actual_fps = self.fps_counter / (current_time - self.last_fps_time)
                    if self.frame_count % 100 == 0:  # 每100帧显示一次FPS
                        print(f"📊 实际FPS: {actual_fps:.1f}, 总帧数: {self.frame_count}")
                    self.fps_counter = 0
                    self.last_fps_time = current_time

                # 存储帧到队列
                if not self.frame_queue.full():
                    self.frame_queue.put(frame.copy())
                else:
                    # 队列满时，丢弃最老的帧
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame.copy())
                    except queue.Empty:
                        pass

                self.last_frame = frame.copy()

            except Exception as e:
                print(f"⚠️ 帧捕获异常: {e}")
                time.sleep(0.1)

    def _reconnect(self):
        """重新连接RTSP流"""
        print("尝试重新连接RTSP流...")
        if self.cap:
            self.cap.release()

        time.sleep(2)  # 等待一段时间再重连
        self.connect()

    def get_latest_frame(self):
        """获取最新的视频帧"""
        try:
            # 获取队列中最新的帧，丢弃旧帧
            latest_frame = None
            while not self.frame_queue.empty():
                try:
                    latest_frame = self.frame_queue.get_nowait()
                except queue.Empty:
                    break

            return latest_frame if latest_frame is not None else self.last_frame

        except Exception as e:
            print(f"获取帧时出错: {e}")
            return self.last_frame

    def save_frame(self, frame, filename=None):
        """保存当前帧"""
        if frame is None:
            return False

        if filename is None:
            timestamp = int(time.time())
            filename = f"{Config.SAVE_PATH}/frame_{timestamp}.jpg"

        try:
            success = cv2.imwrite(filename, frame)
            if success:
                print(f"💾 帧已保存: {filename}")
            return success
        except Exception as e:
            print(f"保存帧失败: {e}")
            return False

    def get_stream_info(self):
        """获取视频流信息"""
        if not self.cap or not self.cap.isOpened():
            return None

        info = {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "frame_count": self.frame_count,
            "is_connected": self.cap.isOpened(),
            "buffer_size": self.frame_queue.qsize()
        }
        return info

    def is_connected(self):
        """检查连接状态"""
        return self.cap is not None and self.cap.isOpened() and self.running

    def test_stream(self, duration=10):
        """测试视频流稳定性"""
        print(f"开始测试视频流稳定性({duration}秒)...")

        if not self.start_capture():
            return False

        start_time = time.time()
        frame_count = 0
        error_count = 0

        while time.time() - start_time < duration:
            frame = self.get_latest_frame()
            if frame is not None:
                frame_count += 1
            else:
                error_count += 1

            time.sleep(0.1)

        self.stop_capture()

        success_rate = (frame_count / (frame_count + error_count)) * 100 if frame_count + error_count > 0 else 0

        print(f"📊 测试结果:")
        print(f"   总帧数: {frame_count}")
        print(f"   错误数: {error_count}")
        print(f"   成功率: {success_rate:.1f}%")

        return success_rate > 90