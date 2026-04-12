#!/usr/bin/env python3
"""
诊断猫咪检测问题
检查视频文件和检测模型
"""

import cv2
import torch
from ultralytics import YOLO
import numpy as np

def diagnose_cat_detection():
    """诊断猫咪检测问题"""
    print("🔍 诊断猫咪检测问题...")
    print("=" * 50)

    # 1. 检查视频文件
    print("\n📹 检查视频文件...")
    video_file = "real_cat.mp4"
    try:
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            print(f"❌ 无法打开视频文件: {video_file}")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"✅ 视频文件正常")
        print(f"   总帧数: {total_frames}")
        print(f"   FPS: {fps:.1f}")
        print(f"   分辨率: {width}x{height}")

        # 读取几帧进行测试
        test_frames = []
        for i in [100, 500, 1000, 2000, 5000]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                test_frames.append((i, frame))
                print(f"   ✅ 帧 #{i} 读取成功")

        cap.release()

    except Exception as e:
        print(f"❌ 视频文件检查失败: {e}")
        return

    # 2. 检查YOLO模型
    print(f"\n🤖 检查YOLO模型...")
    try:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"   设备: {device}")

        # 尝试不同模型
        models_to_try = ['yolov8x.pt', 'yolov8n.pt']
        yolo_model = None

        for model_name in models_to_try:
            try:
                print(f"   尝试加载: {model_name}")
                yolo_model = YOLO(model_name)
                yolo_model.to(device)
                print(f"   ✅ {model_name} 加载成功")
                break
            except Exception as e:
                print(f"   ⚠️ {model_name} 加载失败: {e}")

        if yolo_model is None:
            print("❌ 所有YOLO模型加载失败")
            return

    except Exception as e:
        print(f"❌ YOLO模型检查失败: {e}")
        return

    # 3. 测试不同帧的检测
    print(f"\n🐱 测试猫咪检测...")
    cat_detected_frames = []

    for frame_num, frame in test_frames:
        try:
            print(f"\n   测试帧 #{frame_num}:")

            # 使用极低阈值检测
            results = yolo_model(frame, conf=0.001, iou=0.2, verbose=False, device=device)

            cats_found = 0
            all_detections = 0

            for result in results:
                for box in result.boxes:
                    cls = int(box.cls.cpu().numpy()[0])
                    conf = float(box.conf.cpu().numpy()[0])
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0]

                    all_detections += 1

                    # COCO类别15是猫
                    if cls == 15:
                        bbox_area = (x2 - x1) * (y2 - y1)
                        print(f"     🐱 检测到猫! 置信度:{conf:.3f} 面积:{bbox_area:.0f} 位置:({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})")
                        cats_found += 1
                        cat_detected_frames.append(frame_num)
                    else:
                        # 显示其他检测到的对象
                        if conf > 0.1:  # 只显示较高置信度的其他对象
                            class_names = {0: 'person', 1: 'bicycle', 2: 'car', 16: 'dog', 17: 'horse'}
                            class_name = class_names.get(cls, f'class_{cls}')
                            print(f"     📷 检测到: {class_name} 置信度:{conf:.3f}")

            print(f"     📊 本帧总计: {cats_found}只猫, {all_detections}个对象")

        except Exception as e:
            print(f"     ❌ 帧 #{frame_num} 检测失败: {e}")

    # 4. 总结
    print(f"\n📋 诊断总结:")
    print(f"   🎬 视频文件: ✅ 正常 ({total_frames}帧)")
    print(f"   🤖 YOLO模型: ✅ 正常")
    print(f"   🐱 检测到猫的帧: {len(cat_detected_frames)}")

    if cat_detected_frames:
        print(f"   ✅ 在帧 {cat_detected_frames} 检测到猫")
        print(f"   💡 建议: 系统应该能正常检测到猫")
    else:
        print(f"   ⚠️ 测试的几帧中未检测到猫")
        print(f"   💡 建议: 可能需要测试更多帧，或者猫咪不在这些特定帧中")

    # 5. 实时系统检查
    print(f"\n🌐 检查实时系统状态...")
    try:
        import requests
        response = requests.get("http://localhost:5008/api/detections", timeout=3)
        if response.status_code == 200:
            data = response.json()
            current_frame = data.get('total_frames', 0)
            cats_detected = data.get('cat_detections', 0)
            print(f"   ✅ 实时系统运行中")
            print(f"   📊 当前帧: {current_frame}")
            print(f"   🐱 检测到猫: {cats_detected}")

            if current_frame == 0:
                print(f"   ⚠️ 系统可能刚启动，还未开始处理帧")
            elif cats_detected == 0:
                print(f"   💡 系统运行中但还未检测到猫，可能需要等待视频播放到有猫的帧")
        else:
            print(f"   ❌ 实时系统API异常: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 无法连接实时系统: {e}")

    return cat_detected_frames

if __name__ == "__main__":
    detected_frames = diagnose_cat_detection()

    if detected_frames:
        print(f"\n🎉 诊断完成: 系统应该能检测到猫!")
        print(f"🔧 如果Web界面未显示猫，请等待视频播放到帧 {min(detected_frames)} 附近")
    else:
        print(f"\n🤔 需要进一步检查视频内容或调整检测参数")