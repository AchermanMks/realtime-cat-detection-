"""导出微调后模型为 TensorRT FP16 engine，并替换现役引擎。"""
from pathlib import Path
import shutil
from ultralytics import YOLO

BEST = Path('runs/detect/runs/cat_finetune/v1/weights/best.pt')
TARGET_PT = Path('yolo11x_cat.pt')          # 独立命名，避免覆盖原生COCO权重
TARGET_ENGINE = Path('yolo11x_cat.engine')
IMGSZ = 960

if not BEST.exists():
    raise SystemExit(f'❌ 未找到 {BEST}')

shutil.copy(BEST, TARGET_PT)
print(f'✅ 权重复制到 {TARGET_PT}')

m = YOLO(str(TARGET_PT))
print('🔧 导出 TensorRT FP16 engine ...')
m.export(format='engine', half=True, imgsz=IMGSZ, device=0, workspace=4)

# Ultralytics 导出到 yolo11x_cat.engine（同名 .pt → .engine）
if TARGET_ENGINE.exists():
    print(f'✅ engine 就绪：{TARGET_ENGINE}')
else:
    # fallback: search
    for p in Path('.').glob('*.engine'):
        print(f'  found: {p}')
