"""
伪标签生成：用当前 yolo11x 扫描 real_cat.mp4，产出 YOLO 训练数据。

输出结构：
    dataset_cat/
        images_raw/      高置信(>=0.6) 自动标注的训练图
        labels_raw/      对应 YOLO txt（单类：0=cat）
        review/          中等置信(0.3-0.6)候选，需手动过一遍
            xxx.jpg              原图（用于重标）
            xxx_preview.jpg      可视化预览（黄框+置信度）
            xxx_suggest.txt      建议标注（格式同YOLO，含conf注释）
        negatives/       确定无猫的帧，作为负样本

使用：
    python pseudo_label.py
"""
from pathlib import Path
import cv2
from ultralytics import YOLO

VIDEO = 'real_cat.mp4'
MODEL_PT = 'yolo11x.pt'
OUT = Path('dataset_cat')

SAMPLE_STRIDE = 10      # 每 N 帧采样一次（11177 / 10 ≈ 1118 候选）
NEG_STRIDE = 60         # 无猫帧的采样密度（避免负样本过多）
AUTO_CONF = 0.50        # >= 此阈值：自动标注直接入训练集
REVIEW_LOW = 0.30       # [0.30, 0.50)：进入人工审核
IOU_DEDUP = 0.97        # 只过滤几乎一模一样的帧；静止猫的多角度连续帧保留

def main():
    for d in ['images_raw', 'labels_raw', 'review', 'negatives']:
        (OUT / d).mkdir(parents=True, exist_ok=True)

    print(f'📦 加载模型 {MODEL_PT}')
    model = YOLO(MODEL_PT)

    cap = cv2.VideoCapture(VIDEO)
    if not cap.isOpened():
        print(f'❌ 打不开 {VIDEO}'); return
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f'📹 视频 {W}x{H}, {total} 帧')

    auto_n, review_n, neg_n, dup_n = 0, 0, 0, 0
    prev_box = None
    idx = -1

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        idx += 1
        if idx % SAMPLE_STRIDE != 0:
            continue

        # 单类 cat (COCO class=15)，阈值设低以同时拿到review候选
        res = model(frame, conf=REVIEW_LOW, iou=0.5, classes=[15],
                    imgsz=960, verbose=False)[0]
        boxes = res.boxes

        if boxes is None or len(boxes) == 0:
            if idx % NEG_STRIDE == 0:
                cv2.imwrite(str(OUT / 'negatives' / f'neg_{idx:06d}.jpg'), frame)
                neg_n += 1
            prev_box = None
            continue

        confs = [float(b.conf) for b in boxes]
        xyxys = [b.xyxy[0].float().tolist() for b in boxes]
        max_idx = max(range(len(confs)), key=lambda i: confs[i])
        top_conf = confs[max_idx]
        top_box = xyxys[max_idx]

        # 去冗余：连续采样框重叠过高的帧跳过
        if prev_box is not None and _iou(top_box, prev_box) > IOU_DEDUP:
            dup_n += 1
            continue
        prev_box = top_box

        if top_conf >= AUTO_CONF:
            # 高置信：所有 >=AUTO_CONF 的框入标注
            keep = [(c, xy) for c, xy in zip(confs, xyxys) if c >= AUTO_CONF]
            stem = f'auto_{idx:06d}'
            cv2.imwrite(str(OUT / 'images_raw' / f'{stem}.jpg'), frame)
            with open(OUT / 'labels_raw' / f'{stem}.txt', 'w') as f:
                for _, xy in keep:
                    f.write(_yolo_line(xy, W, H))
            auto_n += 1
        else:
            # 中等置信：推入review
            stem = f'review_{idx:06d}'
            cv2.imwrite(str(OUT / 'review' / f'{stem}.jpg'), frame)
            annot = frame.copy()
            with open(OUT / 'review' / f'{stem}_suggest.txt', 'w') as f:
                for c, xy in zip(confs, xyxys):
                    x1, y1, x2, y2 = [int(v) for v in xy]
                    cv2.rectangle(annot, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(annot, f'{c:.2f}', (x1, max(y1-5, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    f.write(_yolo_line(xy, W, H, conf=c))
            cv2.imwrite(str(OUT / 'review' / f'{stem}_preview.jpg'), annot)
            review_n += 1

        if (auto_n + review_n + neg_n) % 100 == 0 and (auto_n + review_n + neg_n) > 0:
            print(f'  进度 frame {idx}/{total} | auto={auto_n} review={review_n} neg={neg_n} dup={dup_n}')

    cap.release()
    print('\n========== 完成 ==========')
    print(f'✅ 自动标注训练图: {auto_n}')
    print(f'🔍 待人工审核:     {review_n}   -> dataset_cat/review/')
    print(f'📭 负样本:         {neg_n}')
    print(f'♻️  去重跳过:       {dup_n}')
    print(f'\n下一步：')
    print(f'  1. 浏览 dataset_cat/review/*_preview.jpg，把 _真实含猫_ 的图复制到 images_raw/，suggest.txt 改好后复制到 labels_raw/')
    print(f'  2. 明显错的框需要修正坐标；完全没猫的review图直接丢弃')
    print(f'  3. 告诉我审核完成，进入训练')


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a; bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def _yolo_line(xyxy, W, H, conf=None):
    x1, y1, x2, y2 = xyxy
    cx = ((x1 + x2) / 2) / W
    cy = ((y1 + y2) / 2) / H
    w = (x2 - x1) / W
    h = (y2 - y1) / H
    tail = f'  # conf={conf:.2f}' if conf is not None else ''
    return f'0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}{tail}\n'


if __name__ == '__main__':
    main()
