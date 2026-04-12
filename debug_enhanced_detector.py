#!/usr/bin/env python3
"""
调试版增强猫咪检测器
"""

import cv2
import torch
from ultralytics import YOLO
import numpy as np

def debug_detection():
    """调试检测流程"""
    print("🔍 调试增强检测流程...")

    # 加载模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    fast_model = YOLO('yolov8n.pt').to(device)
    accurate_model = YOLO('yolov8x.pt').to(device)

    # 测试已知有猫的帧
    test_frames = [10500, 10577, 10677, 10977, 11000]
    video_path = "real_cat.mp4"

    cap = cv2.VideoCapture(video_path)

    for frame_num in test_frames:
        print(f"\n🎯 测试帧 #{frame_num}:")

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            print(f"   ❌ 无法读取帧")
            continue

        # 第一级：快速检测
        print(f"   ⚡ 快速检测 (YOLOv8n, conf=0.1):")
        fast_results = fast_model(frame, conf=0.1, iou=0.4, verbose=False)
        fast_cats = 0
        for result in fast_results:
            for box in result.boxes:
                cls = int(box.cls.cpu().numpy()[0])
                conf = float(box.conf.cpu().numpy()[0])
                if cls == 15:
                    fast_cats += 1
                    print(f"      🐱 快速检测到猫: 置信度 {conf:.3f}")

        if fast_cats == 0:
            print(f"      ❌ 快速检测未发现猫")
            # 尝试更低阈值
            print(f"      🔍 尝试极低阈值 (conf=0.01):")
            ultra_low_results = fast_model(frame, conf=0.01, iou=0.4, verbose=False)
            for result in ultra_low_results:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])
                    if cls == 15:
                        print(f"         🐱 极低阈值检测到猫: 置信度 {conf:.3f}")
            continue

        # 第二级：精确检测
        print(f"   🎯 精确检测 (YOLOv8x, conf=0.2):")
        accurate_results = accurate_model(frame, conf=0.2, iou=0.3, verbose=False)
        accurate_cats = 0
        for result in accurate_results:
            for box in result.boxes:
                cls = int(box.cls.cpu().numpy()[0])
                conf = float(box.conf.cpu().numpy()[0])
                if cls == 15:
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                    area = (x2 - x1) * (y2 - y1)
                    accurate_cats += 1
                    print(f"      🐱 精确检测到猫: 置信度 {conf:.3f}, 面积 {area:.0f}")

        if accurate_cats == 0:
            print(f"      ❌ 精确检测未发现猫")
            # 尝试更低阈值
            print(f"      🔍 尝试极低阈值 (conf=0.01):")
            ultra_low_accurate = accurate_model(frame, conf=0.01, iou=0.3, verbose=False)
            for result in ultra_low_accurate:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])
                    if cls == 15:
                        x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                        area = (x2 - x1) * (y2 - y1)
                        print(f"         🐱 极低阈值精确检测: 置信度 {conf:.3f}, 面积 {area:.0f}")

        print(f"   📊 本帧结果: 快速 {fast_cats} 只，精确 {accurate_cats} 只")

    cap.release()

    # 对比原始方法
    print(f"\n🔄 对比原始检测方法:")
    original_model = YOLO('yolov8x.pt').to(device)

    cap = cv2.VideoCapture(video_path)
    for frame_num in test_frames[:2]:  # 只测试前两个帧
        print(f"\n📹 原始方法测试帧 #{frame_num}:")

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue

        # 使用原始极低阈值方法
        results = original_model(frame, conf=0.001, iou=0.2, verbose=False)
        cats_found = 0
        for result in results:
            for box in result.boxes:
                cls = int(box.cls.cpu().numpy()[0])
                conf = float(box.conf.cpu().numpy()[0])
                if cls == 15:
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]
                    area = (x2 - x1) * (y2 - y1)
                    cats_found += 1
                    print(f"   🐱 原始方法检测: 置信度 {conf:.3f}, 面积 {area:.0f}")

        print(f"   📊 原始方法找到: {cats_found} 只猫")

    cap.release()

if __name__ == "__main__":
    debug_detection()