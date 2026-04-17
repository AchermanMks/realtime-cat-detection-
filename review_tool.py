"""
快速审核 review 候选：按键决定每张图

按键：
    y / SPACE / ENTER  → 接受（框正确，并入训练集）
    n / BACKSPACE      → 丢弃（非猫 / 框错得离谱）
    b                  → 回退上一张
    q / ESC            → 退出并保存进度

接受的图：复制到 images_raw/，suggest.txt 清洗后复制到 labels_raw/
丢弃的图：留在 review/ 不动（保险起见不删除）
进度保存在 review/.progress.json
"""
from pathlib import Path
import cv2
import json
import shutil

ROOT = Path('dataset_cat')
REVIEW = ROOT / 'review'
IMG_DIR = ROOT / 'images_raw'
LBL_DIR = ROOT / 'labels_raw'
PROGRESS_FILE = REVIEW / '.progress.json'

def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {'accepted': [], 'rejected': []}

def save_progress(p):
    PROGRESS_FILE.write_text(json.dumps(p, indent=2))

def clean_label(suggest_path, dst_label_path):
    # suggest.txt 行格式: "0 cx cy w h  # conf=0.45"
    lines = []
    for ln in suggest_path.read_text().strip().split('\n'):
        if '#' in ln:
            ln = ln.split('#')[0].strip()
        if ln:
            lines.append(ln)
    dst_label_path.write_text('\n'.join(lines) + '\n')

def main():
    previews = sorted(REVIEW.glob('review_*_preview.jpg'))
    if not previews:
        print('❌ 没有找到 review_*_preview.jpg')
        return

    p = load_progress()
    done = set(p['accepted']) | set(p['rejected'])
    print(f'📋 共 {len(previews)} 张 | 已完成 {len(done)}')
    print(f'按键: y=接受 / n=丢弃 / b=回退 / q=退出\n')

    idx = 0
    history = []
    while idx < len(previews):
        preview = previews[idx]
        stem = preview.stem.replace('_preview', '')
        if stem in done:
            idx += 1
            continue

        img = cv2.imread(str(preview))
        disp = img.copy()
        bar = f'{idx+1}/{len(previews)}  accepted={len(p["accepted"])}  [y]es [n]o [b]ack [q]uit'
        cv2.putText(disp, bar, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow('review', disp)
        k = cv2.waitKey(0) & 0xFF

        if k in (ord('y'), ord(' '), 13):  # y / space / enter
            # accept: copy image + clean label
            src_img = REVIEW / f'{stem}.jpg'
            src_lbl = REVIEW / f'{stem}_suggest.txt'
            shutil.copy(src_img, IMG_DIR / f'{stem}.jpg')
            clean_label(src_lbl, LBL_DIR / f'{stem}.txt')
            p['accepted'].append(stem)
            history.append(('accept', stem))
            idx += 1
        elif k in (ord('n'), 8):  # n / backspace
            p['rejected'].append(stem)
            history.append(('reject', stem))
            idx += 1
        elif k == ord('b') and history:
            act, prev_stem = history.pop()
            if act == 'accept':
                (IMG_DIR / f'{prev_stem}.jpg').unlink(missing_ok=True)
                (LBL_DIR / f'{prev_stem}.txt').unlink(missing_ok=True)
                p['accepted'].remove(prev_stem)
            else:
                p['rejected'].remove(prev_stem)
            # rewind pointer
            prev_idx = next(i for i, pv in enumerate(previews)
                            if pv.stem.replace('_preview','') == prev_stem)
            idx = prev_idx
        elif k in (ord('q'), 27):  # q / esc
            break

        save_progress(p)

    cv2.destroyAllWindows()
    save_progress(p)
    print(f'\n✅ 完成: 接受 {len(p["accepted"])} / 丢弃 {len(p["rejected"])}')
    print(f'训练集现有图片数: {len(list(IMG_DIR.glob("*.jpg")))}')

if __name__ == '__main__':
    main()
