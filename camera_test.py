#!/usr/bin/env python3
"""
摄像头检测和测试脚本
"""

import cv2
import time

def test_camera_devices():
    """测试可用的摄像头设备"""
    print("🔍 检测摄像头设备...")

    available_cameras = []

    # 测试设备ID 0-4
    for i in range(5):
        print(f"测试设备 {i}...")
        cap = cv2.VideoCapture(i)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                fps = cap.get(cv2.CAP_PROP_FPS)
                available_cameras.append({
                    "id": i,
                    "width": w,
                    "height": h,
                    "fps": fps
                })
                print(f"✅ 设备 {i}: {w}x{h}, {fps}fps")
            else:
                print(f"❌ 设备 {i}: 无法读取帧")
        else:
            print(f"❌ 设备 {i}: 无法打开")

        cap.release()

    return available_cameras

def test_specific_camera(device_id):
    """测试特定摄像头"""
    print(f"\n📹 测试摄像头设备 {device_id}...")

    cap = cv2.VideoCapture(device_id)

    if not cap.isOpened():
        print(f"❌ 无法打开摄像头设备 {device_id}")
        return False

    # 获取摄像头属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"📊 摄像头信息:")
    print(f"   分辨率: {width}x{height}")
    print(f"   帧率: {fps}")

    # 测试获取几帧
    print("🎬 测试视频流...")
    for i in range(10):
        ret, frame = cap.read()
        if ret:
            print(f"✅ 帧 {i+1}: 正常")
        else:
            print(f"❌ 帧 {i+1}: 失败")
            break
        time.sleep(0.1)

    cap.release()
    return True

def create_virtual_camera():
    """如果没有物理摄像头，创建虚拟摄像头演示"""
    print("\n📱 创建虚拟摄像头演示...")

    import numpy as np
    import threading
    import queue

    frame_queue = queue.Queue(maxsize=30)

    def generate_frames():
        frame_count = 0
        while frame_count < 300:  # 生成300帧 (约10秒)
            # 创建动态图像
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

            # 添加动态元素
            t = frame_count * 0.1
            center_x = int(320 + 100 * np.sin(t))
            center_y = int(240 + 50 * np.cos(t))

            # 绘制移动的圆圈
            cv2.circle(frame, (center_x, center_y), 30, (0, 255, 255), -1)

            # 添加文字
            cv2.putText(frame, f"Virtual Camera Frame {frame_count}",
                       (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, f"Time: {frame_count/30:.1f}s",
                       (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if not frame_queue.full():
                frame_queue.put(frame)

            frame_count += 1
            time.sleep(1/30)  # 30fps

    # 启动帧生成线程
    generator_thread = threading.Thread(target=generate_frames, daemon=True)
    generator_thread.start()

    print("✅ 虚拟摄像头已创建，可用于演示")
    return frame_queue

def main():
    """主函数"""
    print("🎥 摄像头检测和测试工具")
    print("=" * 40)

    # 1. 检测可用摄像头
    cameras = test_camera_devices()

    if cameras:
        print(f"\n✅ 找到 {len(cameras)} 个可用摄像头:")
        for cam in cameras:
            print(f"   设备 {cam['id']}: {cam['width']}x{cam['height']}, {cam['fps']:.1f}fps")

        # 测试第一个可用摄像头
        first_cam = cameras[0]['id']
        test_specific_camera(first_cam)

        print(f"\n🎯 建议在配置中使用: RTSP_URL = {first_cam}")

    else:
        print("\n❌ 未检测到可用的摄像头设备")
        print("\n💡 可能的解决方案:")
        print("1. 确认摄像头已正确连接")
        print("2. 检查摄像头驱动程序")
        print("3. 尝试重新连接摄像头")
        print("4. 使用虚拟摄像头进行演示")

        # 询问是否创建虚拟摄像头
        choice = input("\n是否创建虚拟摄像头进行演示? [y/N]: ")
        if choice.lower() == 'y':
            virtual_queue = create_virtual_camera()
            return virtual_queue

    return None

if __name__ == "__main__":
    main()