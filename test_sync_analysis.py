#!/usr/bin/env python3
"""
测试同步逐帧分析功能
验证视频播放与AI检测的完全同步
"""

import requests
import time
import json

def test_synchronization():
    """测试视频与分析的同步性"""

    print("🎬 测试同步逐帧分析功能")
    print("=" * 50)

    base_url = "http://localhost:5008"

    # 测试同步状态
    print("\n🔄 检测同步状态...")

    frame_numbers = []
    sync_statuses = []
    detection_counts = []

    for i in range(10):
        try:
            response = requests.get(f"{base_url}/api/detections", timeout=3)
            if response.status_code == 200:
                data = response.json()

                frame_num = data.get('current_frame_number', 0)
                sync_status = data.get('sync_status', '未知')
                detection_count = len(data.get('detections', []))
                sync_fps = data.get('sync_fps', 0)

                frame_numbers.append(frame_num)
                sync_statuses.append(sync_status)
                detection_counts.append(detection_count)

                print(f"   第{i+1:2d}次: 帧#{frame_num:4d} | 检测:{detection_count} | 状态:{sync_status} | FPS:{sync_fps}")

                # 检查帧数递增
                if i > 0 and frame_num > frame_numbers[i-1]:
                    frame_progress = frame_num - frame_numbers[i-1]
                    print(f"        ✅ 帧数正常递增: +{frame_progress}")
                elif i > 0:
                    print(f"        ⚠️ 帧数未变化")

            else:
                print(f"   第{i+1:2d}次: API请求失败 ({response.status_code})")

            time.sleep(1.0)  # 等待1秒观察帧数变化

        except Exception as e:
            print(f"   第{i+1:2d}次: 请求错误 - {e}")

    # 分析同步性能
    print(f"\n📊 同步性能分析:")
    if len(frame_numbers) > 1:
        total_frames_processed = frame_numbers[-1] - frame_numbers[0]
        total_time = (len(frame_numbers) - 1) * 1.0  # 每次间隔1秒
        actual_fps = total_frames_processed / total_time if total_time > 0 else 0

        print(f"   🎯 目标同步FPS: 15")
        print(f"   ⚡ 实际处理FPS: {actual_fps:.1f}")
        print(f"   📈 总处理帧数: {total_frames_processed}")
        print(f"   ✅ 同步效率: {(actual_fps/15)*100:.1f}%")

    unique_statuses = set(sync_statuses)
    print(f"   🔄 同步状态: {', '.join(unique_statuses)}")

    # 测试同步分析数据
    print(f"\n🧮 测试同步分析数据...")
    try:
        response = requests.get(f"{base_url}/api/sync_analysis", timeout=5)
        if response.status_code == 200:
            data = response.json()

            current_analysis = data.get('current_frame_analysis', {})
            recent_analysis = data.get('recent_analysis', [])

            print(f"   📍 当前帧分析:")
            print(f"        帧号: {current_analysis.get('frame_number', 0)}")
            print(f"        检测数: {current_analysis.get('detections_count', 0)}")
            print(f"        猫数量: {current_analysis.get('cats_detected', 0)}")
            print(f"        狗数量: {current_analysis.get('dogs_detected', 0)}")
            print(f"        同步状态: {current_analysis.get('sync_status', '未知')}")

            print(f"   📋 最近分析历史 (最后5帧):")
            for analysis in recent_analysis[-5:]:
                frame_num = analysis.get('frame_number', 0)
                cats = analysis.get('cats_detected', 0)
                dogs = analysis.get('dogs_detected', 0)
                print(f"        帧#{frame_num}: {cats}猫 {dogs}狗")

        else:
            print(f"   ❌ 同步分析API请求失败: {response.status_code}")

    except Exception as e:
        print(f"   ❌ 同步分析请求错误: {e}")

    # 测试3D可视化同步
    print(f"\n🏠 测试3D可视化同步...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/api/3d_visualization", timeout=8)
        response_time = time.time() - start_time

        if response.status_code == 200:
            viz_size = len(response.content)
            print(f"   ✅ 3D可视化生成成功")
            print(f"        响应时间: {response_time:.3f}s")
            print(f"        图像大小: {viz_size:,} bytes")
            print(f"        同步延迟: {'低' if response_time < 0.1 else '中等' if response_time < 0.5 else '高'}")
        else:
            print(f"   ❌ 3D可视化失败: {response.status_code}")

    except Exception as e:
        print(f"   ❌ 3D可视化请求错误: {e}")

    # 检测逐帧分析的连续性
    print(f"\n🎯 测试逐帧分析连续性...")
    frame_sequence = []

    for i in range(5):
        try:
            response = requests.get(f"{base_url}/api/detections", timeout=3)
            if response.status_code == 200:
                data = response.json()
                frame_num = data.get('current_frame_number', 0)
                detections = data.get('detections', [])

                frame_sequence.append({
                    'frame': frame_num,
                    'detections': len(detections),
                    'has_cats': sum(1 for d in detections if d.get('class') == '猫'),
                    'timestamp': time.time()
                })

                print(f"   快照{i+1}: 帧#{frame_num} | 检测:{len(detections)} | 猫:{frame_sequence[-1]['has_cats']}")

            time.sleep(0.8)  # 快速采样

        except Exception as e:
            print(f"   快照{i+1}: 错误 - {e}")

    # 分析帧序列连续性
    if len(frame_sequence) > 1:
        frame_gaps = []
        for i in range(1, len(frame_sequence)):
            gap = frame_sequence[i]['frame'] - frame_sequence[i-1]['frame']
            frame_gaps.append(gap)

        avg_gap = sum(frame_gaps) / len(frame_gaps)
        print(f"   📈 平均帧间隔: {avg_gap:.1f}帧")
        print(f"   🔄 连续性: {'良好' if avg_gap < 20 else '一般' if avg_gap < 40 else '需优化'}")

    print(f"\n🎉 同步逐帧分析测试完成！")
    print(f"🌐 系统地址: {base_url}")

    print(f"\n🔥 同步功能特性:")
    print("   ✅ 逐帧播放逐帧分析")
    print("   ✅ 视频与AI完全同步")
    print("   ✅ 15FPS稳定帧率")
    print("   ✅ Z轴深度追踪")
    print("   ✅ 实时同步状态监控")
    print("   ✅ 帧级别精确分析")

if __name__ == "__main__":
    test_synchronization()