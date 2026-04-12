#!/usr/bin/env python3
"""
第4步：整合检测和3D定位
将YOLO检测、Homography转换、3D空间定位整合成完整管道
"""

import cv2
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 设置非GUI后端
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import time

# 导入前面步骤的模块
import sys
sys.path.append('.')

class IntegratedPetTracker:
    """整合的宠物追踪系统"""

    def __init__(self,
                 detection_results_file: str,
                 coordinate_results_file: str,
                 room_data_file: str):
        """
        初始化整合追踪系统

        Args:
            detection_results_file: 第1步检测结果
            coordinate_results_file: 第2步坐标转换结果
            room_data_file: 第3步房间数据
        """
        self.detection_file = Path(detection_results_file)
        self.coordinate_file = Path(coordinate_results_file)
        self.room_file = Path(room_data_file)

        # 加载所有数据
        self.detection_data = None
        self.coordinate_data = None
        self.room_data = None

        # 处理结果
        self.integrated_detections = []
        self.coordinate_transform_matrix = None
        self.room_bounds = None

        self._load_all_data()
        self._setup_coordinate_systems()

    def _load_all_data(self):
        """加载所有步骤的数据"""
        print("📥 加载前面步骤的数据...")

        # 加载第2步的坐标转换结果（包含第1步的检测数据）
        if self.coordinate_file.exists():
            with open(self.coordinate_file, 'r', encoding='utf-8') as f:
                self.coordinate_data = json.load(f)
            print(f"✅ 坐标转换数据加载成功: {len(self.coordinate_data['detections_with_coordinates'])}个检测")
        else:
            raise FileNotFoundError(f"坐标转换数据不存在: {self.coordinate_file}")

        # 加载第3步的房间数据
        if self.room_file.exists():
            with open(self.room_file, 'r', encoding='utf-8') as f:
                self.room_data = json.load(f)
            self.room_bounds = self.room_data['room_bounds']
            print(f"✅ 房间数据加载成功: {self.room_data['room_objects']}")
        else:
            raise FileNotFoundError(f"房间数据不存在: {self.room_file}")

    def _setup_coordinate_systems(self):
        """设置和协调不同的坐标系统"""
        print("🔧 设置坐标系统...")

        # 标定坐标系（从Homography）：左下角原点，4m×3m
        calibration_bounds = {
            'x_min': 0.0, 'x_max': 4.0,
            'y_min': 0.0, 'y_max': 3.0
        }

        # USD坐标系（从RoomPlan）：中心原点，约5m×5m
        usd_bounds = self.room_bounds

        print(f"   标定坐标系: {calibration_bounds}")
        print(f"   USD坐标系: {usd_bounds}")

        # 计算坐标变换矩阵（标定坐标 → USD坐标）
        self.coordinate_transform_matrix = self._calculate_coordinate_transform(
            calibration_bounds, usd_bounds
        )

        print("✅ 坐标系统设置完成")

    def _calculate_coordinate_transform(self, cal_bounds: Dict, usd_bounds: Dict) -> np.ndarray:
        """
        计算从标定坐标系到USD坐标系的变换矩阵

        Args:
            cal_bounds: 标定坐标系边界
            usd_bounds: USD坐标系边界

        Returns:
            3x3变换矩阵
        """
        # 简化的线性变换：平移+缩放
        # 标定坐标系：(0,0)~(4,3) → USD坐标系：(-2.5,-2.5)~(2.5,2.5)

        # 计算缩放和平移参数
        cal_width = cal_bounds['x_max'] - cal_bounds['x_min']  # 4m
        cal_height = cal_bounds['y_max'] - cal_bounds['y_min']  # 3m

        usd_width = usd_bounds['x_max'] - usd_bounds['x_min']  # ~5m
        usd_height = usd_bounds['y_max'] - usd_bounds['y_min']  # ~5m

        # 保持比例，使用较小的缩放因子
        scale_x = usd_width / cal_width * 0.8  # 稍微缩小以保证在范围内
        scale_y = usd_height / cal_height * 0.8

        # 平移到USD坐标系的中心
        offset_x = (usd_bounds['x_min'] + usd_bounds['x_max']) / 2
        offset_y = (usd_bounds['y_min'] + usd_bounds['y_max']) / 2

        # 构造变换矩阵
        transform = np.array([
            [scale_x, 0, offset_x - scale_x * cal_width / 2],
            [0, scale_y, offset_y - scale_y * cal_height / 2],
            [0, 0, 1]
        ])

        print(f"   变换参数: 缩放({scale_x:.3f}, {scale_y:.3f}), 平移({offset_x:.3f}, {offset_y:.3f})")

        return transform

    def transform_to_usd_coordinates(self, x: float, y: float) -> Tuple[float, float]:
        """
        将标定坐标转换为USD坐标

        Args:
            x, y: 标定坐标系中的坐标

        Returns:
            USD坐标系中的坐标
        """
        if self.coordinate_transform_matrix is None:
            return x, y

        # 齐次坐标变换
        point = np.array([x, y, 1])
        transformed = self.coordinate_transform_matrix @ point

        return float(transformed[0]), float(transformed[1])

    def process_detections(self) -> List[Dict]:
        """
        处理所有检测结果，添加3D定位信息

        Returns:
            完整的检测和定位结果
        """
        print("🔄 处理检测结果...")

        detections_with_coords = self.coordinate_data['detections_with_coordinates']
        self.integrated_detections = []

        for detection in detections_with_coords:
            # 复制原始检测数据
            integrated_det = detection.copy()

            # 如果有有效的物理坐标
            if detection.get('position_valid', False):
                real_pos = detection['real_position']

                # 转换到USD坐标系
                usd_x, usd_y = self.transform_to_usd_coordinates(
                    real_pos['x'], real_pos['y']
                )

                # 添加3D定位信息
                integrated_det['3d_position'] = {
                    'calibrated_coords': {  # 标定坐标系
                        'x': real_pos['x'],
                        'y': real_pos['y'],
                        'z': 0.0  # 假设在地面
                    },
                    'usd_coords': {  # USD坐标系
                        'x': round(usd_x, 3),
                        'y': round(usd_y, 3),
                        'z': 0.0  # 假设在地面
                    },
                    'room_position': self._get_room_position_description(usd_x, usd_y)
                }

                integrated_det['3d_valid'] = True
            else:
                integrated_det['3d_position'] = None
                integrated_det['3d_valid'] = False

            self.integrated_detections.append(integrated_det)

        valid_3d = len([d for d in self.integrated_detections if d.get('3d_valid', False)])
        print(f"✅ 3D定位完成: {valid_3d}/{len(self.integrated_detections)} 个检测")

        return self.integrated_detections

    def _get_room_position_description(self, x: float, y: float) -> str:
        """
        根据坐标获取房间位置描述

        Args:
            x, y: USD坐标系中的坐标

        Returns:
            位置描述字符串
        """
        # 房间中心在(0,0)附近
        center_threshold = 0.5

        if abs(x) < center_threshold and abs(y) < center_threshold:
            return "房间中央"
        elif x > center_threshold and y > center_threshold:
            return "右上角"
        elif x > center_threshold and y < -center_threshold:
            return "右下角"
        elif x < -center_threshold and y > center_threshold:
            return "左上角"
        elif x < -center_threshold and y < -center_threshold:
            return "左下角"
        elif x > center_threshold:
            return "右侧"
        elif x < -center_threshold:
            return "左侧"
        elif y > center_threshold:
            return "上方"
        elif y < -center_threshold:
            return "下方"
        else:
            return "中心区域"

    def create_integrated_visualization(self, save_path: str = None) -> str:
        """
        创建整合的可视化图

        Args:
            save_path: 保存路径

        Returns:
            保存的图像路径
        """
        print("📊 创建整合可视化...")

        fig = plt.figure(figsize=(20, 12))

        # 四个子图：
        # 1. 像素坐标（原始检测）
        # 2. 标定物理坐标
        # 3. USD 3D坐标
        # 4. 轨迹分析

        # 子图1：像素坐标
        ax1 = fig.add_subplot(221)
        self._plot_pixel_detections(ax1)

        # 子图2：标定物理坐标
        ax2 = fig.add_subplot(222)
        self._plot_calibrated_coordinates(ax2)

        # 子图3：USD 3D坐标
        ax3 = fig.add_subplot(223)
        self._plot_usd_coordinates(ax3)

        # 子图4：时间轨迹
        ax4 = fig.add_subplot(224)
        self._plot_trajectory_timeline(ax4)

        plt.tight_layout()

        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"step4_integrated_visualization_{timestamp}.jpg"

        try:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 整合可视化已保存: {save_path}")
        except Exception as e:
            print(f"⚠️ 可视化保存失败: {e}")
            plt.close()
            save_path = None

        return save_path

    def _plot_pixel_detections(self, ax):
        """绘制像素坐标检测结果"""
        ax.set_title("Step 1: Pixel Detections", fontweight='bold')

        # 绘制检测框和中心点
        for det in self.integrated_detections:
            center = det['center']
            bbox = det['bbox']
            color = 'green' if det['class_name'] == 'cat' else 'blue'

            # 绘制边界框
            rect = patches.Rectangle(
                (bbox['x1'], bbox['y1']),
                bbox['x2'] - bbox['x1'],
                bbox['y2'] - bbox['y1'],
                linewidth=2, edgecolor=color, facecolor='none', alpha=0.7
            )
            ax.add_patch(rect)

            # 绘制中心点
            ax.plot(center['x'], center['y'], 'o', color=color, markersize=6)

        ax.set_xlabel("Pixels X")
        ax.set_ylabel("Pixels Y")
        ax.invert_yaxis()  # 图像坐标系
        ax.grid(True, alpha=0.3)

    def _plot_calibrated_coordinates(self, ax):
        """绘制标定物理坐标"""
        ax.set_title("Step 2: Calibrated Physical Coordinates", fontweight='bold')

        # 绘制房间边界（4m × 3m）
        room_rect = patches.Rectangle(
            (0, 0), 4, 3,
            linewidth=2, edgecolor='black', facecolor='lightblue', alpha=0.2
        )
        ax.add_patch(room_rect)

        # 绘制宠物位置
        for det in self.integrated_detections:
            if det.get('position_valid', False):
                pos = det['real_position']
                color = 'green' if det['class_name'] == 'cat' else 'blue'
                marker = '^' if det['class_name'] == 'cat' else 's'

                ax.plot(pos['x'], pos['y'], marker=marker, color=color,
                       markersize=8, alpha=0.8)

        ax.set_xlabel("X (meters)")
        ax.set_ylabel("Y (meters)")
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 3.5)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)

    def _plot_usd_coordinates(self, ax):
        """绘制USD坐标系"""
        ax.set_title("Step 3: USD Room Coordinates", fontweight='bold')

        # 绘制房间边界
        bounds = self.room_bounds
        room_rect = patches.Rectangle(
            (bounds['x_min'], bounds['y_min']),
            bounds['x_max'] - bounds['x_min'],
            bounds['y_max'] - bounds['y_min'],
            linewidth=2, edgecolor='red', facecolor='lightyellow', alpha=0.2
        )
        ax.add_patch(room_rect)

        # 绘制宠物位置（USD坐标）
        for det in self.integrated_detections:
            if det.get('3d_valid', False):
                pos = det['3d_position']['usd_coords']
                color = 'green' if det['class_name'] == 'cat' else 'blue'
                marker = '^' if det['class_name'] == 'cat' else 's'

                ax.plot(pos['x'], pos['y'], marker=marker, color=color,
                       markersize=10, alpha=0.8)

                # 添加位置描述
                ax.annotate(det['3d_position']['room_position'],
                           (pos['x'], pos['y']), xytext=(5, 5),
                           textcoords='offset points', fontsize=8, alpha=0.7)

        ax.set_xlabel("USD X (meters)")
        ax.set_ylabel("USD Y (meters)")
        ax.set_xlim(bounds['x_min'] - 0.2, bounds['x_max'] + 0.2)
        ax.set_ylim(bounds['y_min'] - 0.2, bounds['y_max'] + 0.2)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)

    def _plot_trajectory_timeline(self, ax):
        """绘制时间轨迹"""
        ax.set_title("Step 4: Pet Detection Timeline", fontweight='bold')

        # 提取时间和帧信息
        valid_detections = [d for d in self.integrated_detections if d.get('3d_valid', False)]

        if not valid_detections:
            ax.text(0.5, 0.5, 'No valid detections', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            return

        frame_ids = [d['frame_id'] for d in valid_detections]
        cat_detections = [d for d in valid_detections if d['class_name'] == 'cat']
        dog_detections = [d for d in valid_detections if d['class_name'] == 'dog']

        # 绘制检测时间线
        if cat_detections:
            cat_frames = [d['frame_id'] for d in cat_detections]
            ax.scatter(cat_frames, [1] * len(cat_frames), color='green', s=50,
                      alpha=0.7, label=f'Cat ({len(cat_frames)})')

        if dog_detections:
            dog_frames = [d['frame_id'] for d in dog_detections]
            ax.scatter(dog_frames, [0.5] * len(dog_frames), color='blue', s=50,
                      alpha=0.7, label=f'Dog ({len(dog_frames)})')

        ax.set_xlabel("Frame ID")
        ax.set_ylabel("Detection Type")
        ax.set_yticks([0.5, 1])
        ax.set_yticklabels(['Dog', 'Cat'])
        ax.legend()
        ax.grid(True, alpha=0.3)

    def generate_summary_report(self) -> Dict:
        """
        生成整合处理的总结报告

        Returns:
            总结报告数据
        """
        valid_detections = [d for d in self.integrated_detections if d.get('3d_valid', False)]

        # 统计信息
        cat_count = len([d for d in valid_detections if d['class_name'] == 'cat'])
        dog_count = len([d for d in valid_detections if d['class_name'] == 'dog'])

        # 位置分布
        position_stats = {}
        for det in valid_detections:
            pos_desc = det['3d_position']['room_position']
            position_stats[pos_desc] = position_stats.get(pos_desc, 0) + 1

        # 时间分布
        frame_ids = [d['frame_id'] for d in valid_detections]
        time_span = max(frame_ids) - min(frame_ids) if frame_ids else 0

        report = {
            'integration_summary': {
                'total_detections': len(self.integrated_detections),
                'valid_3d_localizations': len(valid_detections),
                '3d_success_rate': len(valid_detections) / len(self.integrated_detections) * 100 if self.integrated_detections else 0
            },
            'pet_statistics': {
                'cat_detections': cat_count,
                'dog_detections': dog_count,
                'total_pets': cat_count + dog_count
            },
            'spatial_distribution': position_stats,
            'temporal_analysis': {
                'frame_span': time_span,
                'first_detection_frame': min(frame_ids) if frame_ids else None,
                'last_detection_frame': max(frame_ids) if frame_ids else None
            },
            'coordinate_systems': {
                'calibrated_range': '0-4m × 0-3m',
                'usd_range': f'{self.room_bounds["x_min"]:.2f}-{self.room_bounds["x_max"]:.2f}m × {self.room_bounds["y_min"]:.2f}-{self.room_bounds["y_max"]:.2f}m'
            }
        }

        return report

    def save_results(self, output_dir: str = None) -> str:
        """
        保存整合结果

        Args:
            output_dir: 输出目录

        Returns:
            输出目录路径
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"step4_output_{timestamp}"

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 保存完整的整合结果
        integrated_file = output_path / "integrated_detections_3d.json"
        integrated_data = {
            'timestamp': datetime.now().isoformat(),
            'step4_info': {
                'integration_method': 'coordinate_transform',
                'coordinate_systems': {
                    'calibrated': '4m×3m, left-bottom origin',
                    'usd': f"{self.room_bounds['x_max']-self.room_bounds['x_min']:.1f}m×{self.room_bounds['y_max']-self.room_bounds['y_min']:.1f}m, center origin"
                }
            },
            'integrated_detections': self.integrated_detections
        }

        with open(integrated_file, 'w', encoding='utf-8') as f:
            json.dump(integrated_data, f, ensure_ascii=False, indent=2)

        # 生成和保存总结报告
        summary_report = self.generate_summary_report()
        summary_file = output_path / "integration_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, ensure_ascii=False, indent=2)

        # 创建可视化
        viz_path = str(output_path / "integrated_visualization.jpg")
        self.create_integrated_visualization(viz_path)

        print(f"📁 整合结果已保存到: {output_path}")
        return str(output_path)

def main():
    """主函数 - 演示整合功能"""
    print("🚀 第4步：整合检测和3D定位")
    print("=" * 50)

    # 配置文件路径
    detection_results = "./step1_output_20260410_121622/detection_results.json"
    coordinate_results = "./step2_output_20260410_121755/detections_with_coordinates.json"
    room_data = "./step3_output_20260410_122421/room_data.json"

    try:
        # 创建整合追踪器
        print("1️⃣ 初始化整合系统...")
        tracker = IntegratedPetTracker(
            detection_results_file=detection_results,
            coordinate_results_file=coordinate_results,
            room_data_file=room_data
        )

        # 处理检测结果
        print("\n2️⃣ 整合检测和3D定位...")
        integrated_detections = tracker.process_detections()

        # 生成总结报告
        print("\n3️⃣ 生成总结报告...")
        summary = tracker.generate_summary_report()

        # 保存结果
        print("\n4️⃣ 保存整合结果...")
        output_dir = tracker.save_results()

        # 显示关键统计
        print("\n📊 第4步完成统计:")
        print(f"   总检测数: {summary['integration_summary']['total_detections']}")
        print(f"   有效3D定位: {summary['integration_summary']['valid_3d_localizations']}")
        print(f"   3D定位成功率: {summary['integration_summary']['3d_success_rate']:.1f}%")
        print(f"   猫检测: {summary['pet_statistics']['cat_detections']}")
        print(f"   狗检测: {summary['pet_statistics']['dog_detections']}")

        print("\n📍 空间分布:")
        for position, count in summary['spatial_distribution'].items():
            print(f"   {position}: {count}次")

        print("\n✅ 第4步完成！准备构建3D可视化界面")

    except Exception as e:
        print(f"❌ 整合失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()