#!/usr/bin/env python3
"""
RTSP摄像头连接测试工具
用于快速测试RTSP URL是否可以正常连接
"""

import cv2
import time
import sys
import argparse


def test_rtsp_connection(rtsp_url, duration=10):
    """测试RTSP连接"""
    print(f"🔍 测试RTSP连接: {rtsp_url}")
    print(f"⏱️ 测试时长: {duration}秒")
    print("-" * 50)

    cap = None
    try:
        # 尝试不同的后端
        backends = [
            (cv2.CAP_FFMPEG, "FFMPEG"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_ANY, "默认后端")
        ]

        for backend, backend_name in backends:
            print(f"📡 尝试 {backend_name} 后端...")

            try:
                cap = cv2.VideoCapture(rtsp_url, backend)

                # 设置超时和缓冲区
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 10秒连接超时
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)   # 5秒读取超时
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if cap.isOpened():
                    print(f"✅ {backend_name} 连接成功！")

                    # 获取流信息
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    fourcc = cap.get(cv2.CAP_PROP_FOURCC)

                    print(f"📺 流信息:")
                    print(f"   - 分辨率: {width}x{height}")
                    print(f"   - 帧率: {fps}")
                    print(f"   - 编码: {fourcc}")

                    # 测试读取帧
                    print("🎬 开始读取视频帧...")
                    start_time = time.time()
                    frame_count = 0
                    error_count = 0

                    while time.time() - start_time < duration:
                        ret, frame = cap.read()

                        if ret and frame is not None:
                            frame_count += 1
                            elapsed = time.time() - start_time
                            current_fps = frame_count / elapsed if elapsed > 0 else 0

                            # 每秒输出一次统计
                            if frame_count % max(1, int(fps)) == 0:
                                print(f"📊 已读取 {frame_count} 帧, "
                                      f"实际FPS: {current_fps:.1f}, "
                                      f"时长: {elapsed:.1f}s")
                        else:
                            error_count += 1
                            if error_count > 10:
                                print(f"❌ 连续读取失败次数过多，停止测试")
                                break
                            time.sleep(0.1)

                    cap.release()
                    print(f"✅ 测试完成！")
                    print(f"📊 总统计:")
                    print(f"   - 总帧数: {frame_count}")
                    print(f"   - 错误次数: {error_count}")
                    print(f"   - 平均FPS: {frame_count/duration:.1f}")
                    return True

                else:
                    print(f"❌ {backend_name} 无法连接")
                    if cap:
                        cap.release()

            except Exception as e:
                print(f"❌ {backend_name} 连接异常: {e}")
                if cap:
                    cap.release()

        print("❌ 所有后端都无法连接RTSP流")
        return False

    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        return False
    finally:
        if cap:
            cap.release()


def main():
    parser = argparse.ArgumentParser(description='RTSP摄像头连接测试工具')
    parser.add_argument('rtsp_url', help='RTSP摄像头URL')
    parser.add_argument('--duration', '-d', type=int, default=10,
                      help='测试持续时间(秒, 默认10秒)')
    parser.add_argument('--examples', action='store_true',
                      help='显示RTSP URL格式示例')

    args = parser.parse_args()

    if args.examples:
        print("📝 RTSP URL格式示例:")
        print("")
        print("1. 基本格式:")
        print("   rtsp://192.168.1.100:554/stream")
        print("")
        print("2. 带用户名密码:")
        print("   rtsp://admin:123456@192.168.1.100:554/stream")
        print("")
        print("3. 常见摄像头厂商格式:")
        print("   海康威视: rtsp://admin:password@ip:554/Streaming/Channels/101")
        print("   大华摄像头: rtsp://admin:password@ip:554/cam/realmonitor?channel=1&subtype=0")
        print("   宇视摄像头: rtsp://admin:password@ip:554/video1s1.sdp")
        print("")
        print("4. 使用示例:")
        print("   python3 test_rtsp.py rtsp://admin:123456@192.168.1.100:554/stream")
        print("   python3 test_rtsp.py rtsp://192.168.1.100:554/stream --duration 30")
        return

    print("🎥 RTSP摄像头连接测试工具")
    print("=" * 50)

    success = test_rtsp_connection(args.rtsp_url, args.duration)

    if success:
        print("\n✅ RTSP连接测试成功！")
        print("💡 您可以使用以下命令启动Web监控:")
        print(f"   python3 web_camera_stream.py --rtsp {args.rtsp_url}")
    else:
        print("\n❌ RTSP连接测试失败！")
        print("💡 请检查:")
        print("   1. RTSP URL格式是否正确")
        print("   2. 网络连接是否正常")
        print("   3. 摄像头是否在线")
        print("   4. 用户名密码是否正确")
        print("   5. 端口是否被防火墙阻止")
        print("")
        print("🔧 调试建议:")
        print("   - 使用VLC媒体播放器测试RTSP URL")
        print("   - 检查摄像头厂商的RTSP URL格式文档")
        print("   - 尝试不同的端口(如554, 8554)")


if __name__ == "__main__":
    main()