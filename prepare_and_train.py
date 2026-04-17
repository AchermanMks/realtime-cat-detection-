"""
准备数据集并训练：
  1. 汇总 images_raw/ + negatives/（负样本用空 .txt 标签）
  2. 80/20 切分 train/val
  3. 写 dataset.yaml
  4. 调用 Ultralytics 微调 yolo11x.pt
"""
from pathlib import Path
import random
import shutil

ROOT = Path('dataset_cat')
SRC_IMG = ROOT / 'images_raw'
SRC_LBL = ROOT / 'labels_raw'
SRC_NEG = ROOT / 'negatives'

# 目标结构（YOLO 标准）
TRAIN_IMG = ROOT / 'images' / 'train'
VAL_IMG = ROOT / 'images' / 'val'
TRAIN_LBL = ROOT / 'labels' / 'train'
VAL_LBL = ROOT / 'labels' / 'val'

SPLIT_SEED = 42
VAL_RATIO = 0.2

def _reset(d):
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)

def split_dataset():
    for d in [TRAIN_IMG, VAL_IMG, TRAIN_LBL, VAL_LBL]:
        _reset(d)

    pos_imgs = sorted(SRC_IMG.glob('*.jpg'))
    neg_imgs = sorted(SRC_NEG.glob('*.jpg'))
    random.seed(SPLIT_SEED)
    random.shuffle(pos_imgs)
    random.shuffle(neg_imgs)

    def split(lst, ratio):
        n_val = max(1, int(len(lst) * ratio))
        return lst[n_val:], lst[:n_val]

    pos_train, pos_val = split(pos_imgs, VAL_RATIO)
    neg_train, neg_val = split(neg_imgs, VAL_RATIO)

    def place(imgs, img_dst, lbl_dst, is_positive):
        for img in imgs:
            shutil.copy(img, img_dst / img.name)
            lbl_out = lbl_dst / (img.stem + '.txt')
            if is_positive:
                src_lbl = SRC_LBL / (img.stem + '.txt')
                if src_lbl.exists():
                    shutil.copy(src_lbl, lbl_out)
                else:
                    lbl_out.write_text('')
            else:
                lbl_out.write_text('')  # 负样本空标签

    place(pos_train, TRAIN_IMG, TRAIN_LBL, True)
    place(pos_val, VAL_IMG, VAL_LBL, True)
    place(neg_train, TRAIN_IMG, TRAIN_LBL, False)
    place(neg_val, VAL_IMG, VAL_LBL, False)

    yaml_path = ROOT / 'dataset.yaml'
    yaml_path.write_text(
        f"path: {ROOT.resolve()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: cat\n"
    )

    print(f'✅ 切分完成')
    print(f'  train: 正={len(pos_train)} 负={len(neg_train)} 合计={len(pos_train)+len(neg_train)}')
    print(f'  val:   正={len(pos_val)} 负={len(neg_val)} 合计={len(pos_val)+len(neg_val)}')
    print(f'  yaml:  {yaml_path}')
    return yaml_path


def train(yaml_path):
    from ultralytics import YOLO
    print(f'\n🚀 开始训练 yolo11x.pt → single-class cat')
    model = YOLO('yolo11x.pt')
    model.train(
        data=str(yaml_path),
        imgsz=960,
        epochs=50,
        batch=8,
        patience=15,        # 15 epoch 无提升提前停
        freeze=10,          # 冻结前 10 层 backbone，防过拟合
        cos_lr=True,
        lr0=0.003,
        warmup_epochs=3,
        project='runs/cat_finetune',
        name='v1',
        exist_ok=True,
        device=0,
        workers=4,
        # 增强：小数据集强增强
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.1,
        hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
        degrees=5, translate=0.1, scale=0.5, fliplr=0.5,
        close_mosaic=10,    # 最后10epoch关mosaic，用干净图收敛
    )
    print('\n✅ 训练完成')
    print(f'权重：runs/cat_finetune/v1/weights/best.pt')


if __name__ == '__main__':
    yp = split_dataset()
    train(yp)
