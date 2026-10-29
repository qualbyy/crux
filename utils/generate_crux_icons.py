#!/usr/bin/env python3
"""
Generates Crux minimalist icon assets:
- SVG vector source
- High-res PNG (512x512)
- Multi-resolution Windows ICO (256, 128, 64, 48, 32, 16)
- Mirrors for legacy Zephyrium filenames
"""
from pathlib import Path
from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"

CRUX_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <!-- Crux Minimalist Geometric Icon (Anthropic / Minimal Dark Aesthetic) -->
  <rect x="0" y="0" width="128" height="128" fill="#121214"/>
  <rect x="0.5" y="0.5" width="127" height="127" fill="none" stroke="#27272a" stroke-width="1"/>
  <rect x="5.5" y="5.5" width="117" height="117" fill="none" stroke="#3f3f46" stroke-width="1" opacity="0.3"/>

  <defs>
    <linearGradient id="cruxPurpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#c084fc"/>
      <stop offset="50%" stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#7e22ce"/>
    </linearGradient>
    <linearGradient id="coreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#e9d5ff"/>
    </linearGradient>
  </defs>

  <!-- Crux 4-Pointed Star Cross (Pure geometry, sharp and recognizable) -->
  <path d="M 64 14 L 74 52 L 114 64 L 74 76 L 64 114 L 54 76 L 14 64 L 54 52 Z" 
        fill="url(#cruxPurpleGrad)" />

  <!-- Inner Diamond Core -->
  <polygon points="64,46 74,64 64,82 54,64" fill="url(#coreGrad)"/>

  <!-- Center Focal Dot -->
  <circle cx="64" cy="64" r="3.5" fill="#581c87"/>
</svg>"""

def render_png(svg_str: str, size: int) -> Image.Image:
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    qimg = QImage(size, size, QImage.Format.Format_ARGB32)
    qimg.fill(Qt.GlobalColor.transparent)
    painter = QPainter(qimg)
    renderer.render(painter)
    painter.end()

    # Convert QImage to PIL Image
    ptr = qimg.bits()
    ptr.setsize(qimg.sizeInBytes())
    pil_img = Image.frombuffer("RGBA", (size, size), bytes(ptr), "raw", "BGRA", 0, 1)
    return pil_img

def main():
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Write SVG
    crux_svg_path = RESOURCES_DIR / "crux.svg"
    crux_svg_path.write_text(CRUX_SVG, encoding="utf-8")
    (RESOURCES_DIR / "zephyrium.svg").write_text(CRUX_SVG, encoding="utf-8")
    print(f"  ✓ Written SVG to {crux_svg_path}")

    # 2. Render 512x512 Master PNG
    master_img = render_png(CRUX_SVG, 512)
    crux_png_path = RESOURCES_DIR / "crux.png"
    master_img.save(crux_png_path, "PNG")
    master_img.save(RESOURCES_DIR / "zephyrium.png", "PNG")
    print(f"  ✓ Written PNG (512x512) to {crux_png_path}")

    # 3. Render Windows ICO with multi-resolution icon sizes
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_imgs = [master_img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    
    crux_ico_path = RESOURCES_DIR / "crux.ico"
    ico_imgs[0].save(
        crux_ico_path,
        format="ICO",
        sizes=sizes,
        append_images=ico_imgs[1:]
    )
    ico_imgs[0].save(
        RESOURCES_DIR / "zephyrium.ico",
        format="ICO",
        sizes=sizes,
        append_images=ico_imgs[1:]
    )
    print(f"  ✓ Written multi-resolution ICO to {crux_ico_path}")

    # 4. Copy to website if it exists
    website_images = Path("/home/qualbyy/Документы/zephyrium-website/images")
    if website_images.exists():
        (website_images / "crux.svg").write_text(CRUX_SVG, encoding="utf-8")
        (website_images / "zephyrium.svg").write_text(CRUX_SVG, encoding="utf-8")
        print(f"  ✓ Updated website icons in {website_images}")

if __name__ == "__main__":
    main()
