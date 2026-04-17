"""
独立查看 scan.usd 的所有几何对象。

用法：
    python view_usd.py              # matplotlib 弹窗，可鼠标旋转
    python view_usd.py --save out.png  # 输出图片不弹窗
    python view_usd.py --o3d        # 用 open3d（需 pip install open3d，更流畅）
"""
import argparse
from collections import defaultdict
import numpy as np
from pxr import Usd, UsdGeom

# 类别 → 颜色（matplotlib RGB 0-1）
CATEGORY_COLOR = {
    'Wall':       (0.78, 0.78, 0.78),
    'Floor':      (0.55, 0.45, 0.35),
    'Door':       (0.85, 0.55, 0.30),
    'Window':     (0.50, 0.75, 0.95),
    'Chair':      (0.95, 0.55, 0.55),
    'Table':      (0.65, 0.50, 0.35),
    'Television': (0.20, 0.20, 0.20),
}

def cat_of(name):
    import re
    m = re.match(r'([A-Za-z]+)', name)
    return m.group(1) if m else 'Other'

def extract_meshes(stage):
    """返回 [(name, vertices Nx3, faces Mx3 or None)]"""
    out = []
    for prim in stage.Traverse():
        if prim.GetTypeName() != 'Mesh':
            continue
        mesh = UsdGeom.Mesh(prim)
        pts = np.array(mesh.GetPointsAttr().Get())
        if pts is None or len(pts) == 0:
            continue
        # 应用 world transform
        xform_cache = UsdGeom.XformCache(0.0)
        m = xform_cache.GetLocalToWorldTransform(prim)
        mat = np.array([[m[i][j] for j in range(4)] for i in range(4)])
        homo = np.hstack([pts, np.ones((len(pts), 1))])
        world = (homo @ mat)[:, :3]

        face_counts = mesh.GetFaceVertexCountsAttr().Get()
        face_indices = mesh.GetFaceVertexIndicesAttr().Get()
        faces = None
        if face_counts is not None and face_indices is not None:
            faces = []
            i = 0
            for c in face_counts:
                idx = list(face_indices[i:i + c])
                # 三角化（fan）
                for k in range(1, c - 1):
                    faces.append([idx[0], idx[k], idx[k + 1]])
                i += c
            faces = np.array(faces, dtype=int) if faces else None
        out.append((prim.GetName(), world, faces))
    return out

def view_matplotlib(meshes, save_path=None):
    import matplotlib
    matplotlib.use('Agg')  # 始终离屏渲染，弹窗交给cv2/系统图查看器
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    # 类别专属透明度：墙/地板低，让内部家具可见
    ALPHA = {'Wall': 0.10, 'Floor': 0.20, 'Window': 0.35,
             'Door': 0.55, 'Chair': 0.85, 'Table': 0.85, 'Television': 0.95}

    fig = plt.figure(figsize=(16, 8))

    # 全场景 bbox
    all_pts = np.vstack([v for _, v, _ in meshes])
    mn, mx = all_pts.min(0), all_pts.max(0)

    def render(ax, title, view):
        plotted_categories = set()
        for name, verts, faces in meshes:
            cat = cat_of(name)
            color = CATEGORY_COLOR.get(cat, (0.6, 0.6, 0.6))
            alpha = ALPHA.get(cat, 0.6)
            if faces is not None and len(faces) > 0:
                tris = verts[faces]
                poly = Poly3DCollection(
                    tris, alpha=alpha, facecolor=color,
                    edgecolor=(0, 0, 0, 0.25), linewidth=0.2)
                ax.add_collection3d(poly)
            else:
                ax.scatter(verts[:, 0], verts[:, 1], verts[:, 2], c=[color], s=2)
            if cat not in plotted_categories:
                ax.scatter([], [], [], c=[color], label=cat, s=60)
                plotted_categories.add(cat)
        ax.set_xlim(mn[0], mx[0]); ax.set_ylim(mn[1], mx[1]); ax.set_zlim(mn[2], mx[2])
        ax.set_box_aspect([mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]])
        ax.set_xlabel('X (m)'); ax.set_ylabel('Y (m)'); ax.set_zlabel('Z (m)')
        ax.set_title(title)
        ax.view_init(elev=view[0], azim=view[1])
        ax.legend(loc='upper right', fontsize=8)

    ax1 = fig.add_subplot(121, projection='3d')
    render(ax1, '透视视角 (perspective)', view=(25, 45))

    ax2 = fig.add_subplot(122, projection='3d')
    render(ax2, '俯视视角 (top-down)', view=(89, -90))

    fig.suptitle(f'scan.usd  -  {len(meshes)} meshes  -  '
                 f'{round(mx[0]-mn[0],2)}×{round(mx[1]-mn[1],2)}×{round(mx[2]-mn[2],2)} m',
                 fontsize=13)
    plt.tight_layout()

    out = save_path or '/tmp/_scan_view.png'
    plt.savefig(out, dpi=140, bbox_inches='tight')
    print(f'✅ 已保存 {out}')
    if not save_path:
        # 用 cv2 弹窗显示（按任意键关闭）
        import cv2
        img = cv2.imread(out)
        if img is None:
            print('⚠️ 读取渲染图失败'); return
        # 太大就缩到屏幕能放下
        h, w = img.shape[:2]
        scale = min(1600 / w, 900 / h, 1.0)
        if scale < 1:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        cv2.imshow('scan.usd  (按任意键关闭)', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def view_open3d(meshes):
    import open3d as o3d
    geoms = []
    for name, verts, faces in meshes:
        cat = cat_of(name)
        color = CATEGORY_COLOR.get(cat, (0.6, 0.6, 0.6))
        if faces is not None and len(faces) > 0:
            m = o3d.geometry.TriangleMesh(
                vertices=o3d.utility.Vector3dVector(verts),
                triangles=o3d.utility.Vector3iVector(faces),
            )
            m.compute_vertex_normals()
            m.paint_uniform_color(color)
            geoms.append(m)
        else:
            pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(verts))
            pc.paint_uniform_color(color)
            geoms.append(pc)
    # 加坐标轴
    geoms.append(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5))
    print('🖱️  鼠标左键旋转 / 中键平移 / 滚轮缩放 / Q退出')
    o3d.visualization.draw_geometries(geoms, window_name=f'scan.usd ({len(meshes)} meshes)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', help='保存为图片不弹窗')
    ap.add_argument('--o3d', action='store_true', help='用 open3d（需 pip install open3d）')
    ap.add_argument('--usd', default='scan.usd')
    args = ap.parse_args()

    print(f'📥 加载 {args.usd}')
    stage = Usd.Stage.Open(args.usd)
    meshes = extract_meshes(stage)
    print(f'🔷 提取到 {len(meshes)} 个 mesh')

    by_cat = defaultdict(int)
    for name, _, _ in meshes:
        by_cat[cat_of(name)] += 1
    for c, n in sorted(by_cat.items()):
        print(f'   {c:12s} x{n}')

    if args.o3d:
        view_open3d(meshes)
    else:
        view_matplotlib(meshes, save_path=args.save)

if __name__ == '__main__':
    main()
