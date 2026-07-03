"""生成 Stellar Search 应用图标：暗色圆角底 + 蓝色放大镜 + 星形闪光

用法（在 assets/ 目录下运行）：
    python make_icon.py          # 生成 icon.png
然后按 docs/macOS打包指南.md 中的 sips + iconutil 步骤转换为 AppIcon.icns。
"""
import math
from PIL import Image, ImageDraw

S = 4  # 超采样倍数
SIZE = 1024
W = SIZE * S

# 项目暗色主题配色
BG = "#1e1f22"
SURFACE = "#2b2d31"
ACCENT = "#4e8cff"
ACCENT_LIGHT = "#6ba1ff"
TEXT = "#e8eaed"

img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# macOS 风格：留边距的圆角方形底
margin = int(W * 0.09)
radius = int(W * 0.20)
d.rounded_rectangle((margin, margin, W - margin, W - margin), radius=radius, fill=BG)
# 内侧一圈微弱描边增加层次
d.rounded_rectangle((margin, margin, W - margin, W - margin), radius=radius,
                    outline=SURFACE, width=int(W * 0.008))


def star(draw, cx, cy, r, fill, points=4, inner_ratio=0.38, rot=-90):
    """四角星（闪光）"""
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner_ratio
        a = math.radians(rot + i * 180.0 / points)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    draw.polygon(pts, fill=fill)


# 放大镜：镜片圆环
lens_cx, lens_cy = W * 0.44, W * 0.42
lens_r = W * 0.21
ring_w = int(W * 0.055)
d.ellipse((lens_cx - lens_r, lens_cy - lens_r, lens_cx + lens_r, lens_cy + lens_r),
          outline=ACCENT, width=ring_w)

# 镜柄：从圆环边缘伸向右下
angle = math.radians(45)
hx1 = lens_cx + (lens_r + ring_w * 0.2) * math.cos(angle)
hy1 = lens_cy + (lens_r + ring_w * 0.2) * math.sin(angle)
hx2, hy2 = W * 0.745, W * 0.745
d.line((hx1, hy1, hx2, hy2), fill=ACCENT, width=int(ring_w * 1.25))
# 圆头收尾
cap_r = ring_w * 1.25 / 2
d.ellipse((hx2 - cap_r, hy2 - cap_r, hx2 + cap_r, hy2 + cap_r), fill=ACCENT)

# 镜片内的主星
star(d, lens_cx, lens_cy, lens_r * 0.52, TEXT)
# 周围点缀两颗小星
star(d, W * 0.72, W * 0.26, W * 0.045, ACCENT_LIGHT)
star(d, W * 0.25, W * 0.68, W * 0.032, ACCENT_LIGHT)

img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
img.save("icon.png")
print("icon.png saved")
