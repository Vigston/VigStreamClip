from pathlib import Path
from fontTools.ttLib import TTFont

def scan_custom_fonts(font_dir: Path) -> list:
    font_dir.mkdir(exist_ok=True)
    font_names = set()

    for font_path in font_dir.rglob("*.ttf"):
        try:
            tt = TTFont(font_path)
            for record in tt["name"].names:
                if record.nameID == 1 and record.platformID == 3:
                    name = record.string.decode("utf-16-be").strip()
                    font_names.add(name)
                    break
        except Exception as e:
            print(f"[ERROR] {font_path.name}: {e}")

    return sorted(font_names)

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    font_dir = base_dir / "fonts"
    output_file = font_dir / "font_list.txt"

    fonts = scan_custom_fonts(font_dir)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("AVAILABLE_FONTS = [\n")
        for name in fonts:
            f.write(f'    "{name}",\n')
        f.write("]\n")

    print(f"✅ 改行ありリスト形式でフォント名を書き出しました → {output_file}")