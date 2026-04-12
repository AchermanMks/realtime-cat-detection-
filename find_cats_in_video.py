#!/usr/bin/env python3
"""
在视频中搜索猫咪
扫描更多帧寻找猫咪出现的位置
"""

import cv2
import torch
from ultralytics import YOLO
import numpy as np

def find_cats_in_video():
    """在视频中搜索猫咪"""
    print("🔍 在视频中搜索猫咪...")
    print("=" * 50)

    # 初始化
    video_file = "real_cat.mp4"
    cap = cv2.VideoCapture(video_file)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    yolo_model = YOLO('yolov8x.pt')
    yolo_model.to(device)

    print(f"📹 视频文件: {video_file}")
    print(f"📊 总帧数: {total_frames}")
    print(f"🤖 使用模型: YOLOv8x ({device})")

    # 搜索策略：扫描更多帧
    frames_to_check = []

    # 1. 开始部分 (0-1000)
    frames_to_check.extend(range(0, min(1000, total_frames), 100))

    # 2. 中间部分 (每500帧采样)
    frames_to_check.extend(range(1000, total_frames, 500))

    # 3. 结束部分
    if total_frames > 2000:
        frames_to_check.extend(range(total_frames-1000, total_frames, 100))

    print(f"🎯 将检查 {len(frames_to_check)} 帧...")

    cat_frames = []
    dog_frames = []
    person_frames = []

    for i, frame_num in enumerate(frames_to_check):
        if frame_num >= total_frames:
            continue

        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                continue

            # 检测
            results = yolo_model(frame, conf=0.001, iou=0.2, verbose=False, device=device)

            cats_in_frame = 0
            dogs_in_frame = 0
            persons_in_frame = 0

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])

                    if cls == 15:  # 猫
                        cats_in_frame += 1
                    elif cls == 16:  # 狗
                        dogs_in_frame += 1
                    elif cls == 0:  # 人
                        persons_in_frame += 1

            # 记录结果
            if cats_in_frame > 0:
                cat_frames.append(frame_num)
                print(f"🐱 帧 #{frame_num}: 发现 {cats_in_frame} 只猫!")

            if dogs_in_frame > 0 and frame_num not in dog_frames:
                dog_frames.append(frame_num)

            if persons_in_frame > 0 and frame_num not in person_frames:
                person_frames.append(frame_num)

            # 进度显示
            if i % 20 == 0:
                progress = (i / len(frames_to_check)) * 100
                print(f"   进度: {progress:.1f}% ({i}/{len(frames_to_check)})")

        except Exception as e:
            print(f"   ❌ 帧 #{frame_num} 检测失败: {e}")

    cap.release()

    # 总结结果
    print(f"\n📋 搜索完成!")
    print(f"🐱 发现猫的帧: {len(cat_frames)} 个")
    if cat_frames:
        print(f"   帧位置: {cat_frames}")
        print(f"   最早出现: 帧 #{min(cat_frames)}")
        print(f"   最晚出现: 帧 #{max(cat_frames)}")

    print(f"🐕 发现狗的帧: {len(dog_frames)} 个")
    print(f"👤 发现人的帧: {len(person_frames)} 个")

    if not cat_frames:
        print(f"\n❌ 未在视频中找到猫咪")
        print(f"💡 建议:")
        print(f"   1. 检查视频文件名是否正确")
        print(f"   2. 视频内容可能主要是狗或人")
        print(f"   3. 猫可能被误识别为其他类别")
        print(f"   4. 尝试其他包含猫咪的视频文件")

        # 建议替代方案
        print(f"\n🔧 临时解决方案:")
        if dog_frames:
            print(f"   可以临时将检测类别16(狗)当作猫来测试系统")
        print(f"   或者使用包含真实猫咪的视频文件")

    else:
        print(f"\n✅ 找到猫咪! 系统应该能正常工作")
        print(f"🎬 建议等待视频播放到帧 #{min(cat_frames)} 附近")

    return cat_frames, dog_frames

if __name__ == "__main__":
    cat_frames, dog_frames = find_cats_in_video()

    # 如果没有猫但有狗，提供修改建议
    if not cat_frames and dog_frames:
        print(f"\n💡 临时修改建议:")
        print(f"可以修改代码将狗(类别16)当作猫来测试:")
        print(f"将 'cls == 15' 改为 'cls == 16'")
        print(f"这样系统就会显示绿色方框围绕检测到的狗")