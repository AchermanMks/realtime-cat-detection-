import cv2
import numpy as np
import os

def create_test_video():
    # 视频参数
    width, height = 640, 480
    fps = 30
    duration = 5  # 5秒
    total_frames = fps * duration

    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('test.mp4', fourcc, fps, (width, height))

    print("正在创建测试视频...")

    for frame_num in range(total_frames):
        # 创建黑色背景
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # 动态时间进度
        progress = frame_num / total_frames

        # 添加动态文字
        text1 = f"测试视频 - 帧 {frame_num + 1}/{total_frames}"
        text2 = f"时间: {progress*duration:.1f}秒"
        text3 = "这是一个用于VLM测试的视频"

        # 移动的圆圈
        circle_x = int(100 + (width - 200) * progress)
        circle_y = height // 2
        cv2.circle(frame, (circle_x, circle_y), 30, (0, 255, 255), -1)

        # 添加文字
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, text1, (50, 50), font, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, text2, (50, 100), font, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, text3, (50, 150), font, 0.7, (255, 100, 100), 2)

        # 颜色渐变背景
        color_value = int(50 * (1 + np.sin(progress * 4 * np.pi)))
        frame[:, :, 2] = np.clip(frame[:, :, 2] + color_value, 0, 255)

        # 写入帧
        out.write(frame)

        if frame_num % 30 == 0:
            print(f"进度: {frame_num/total_frames*100:.1f}%")

    # 释放资源
    out.release()

    # 检查文件大小
    file_size = os.path.getsize('test.mp4') / (1024 * 1024)
    print(f"测试视频创建完成！")
    print(f"文件: test.mp4")
    print(f"大小: {file_size:.1f} MB")
    print(f"时长: {duration}秒, {fps}fps")

if __name__ == "__main__":
    create_test_video()