from fontTools.ttLib import TTFont

def extract_supported_chars(ttf_path, output_txt_path=None, print_sample=True):
    font = TTFont(ttf_path)
    cmap = font.getBestCmap()  # Unicode → GlyphName の辞書

    supported_chars = sorted(set(chr(code) for code in cmap.keys()))
    print(f"✅ フォント内の対応文字数: {len(supported_chars)}")

    if print_sample:
        print("📋 一部抜粋（最初の100文字）:")
        print("".join(supported_chars[:100]))

    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            for char in supported_chars:
                f.write(f"{char}\tU+{ord(char):04X}\n")
        print(f"💾 対応文字一覧を保存しました: {output_txt_path}")

    return supported_chars

# 使用例
ttf_path = "C:/Vigston/VigStreamClip/fonts/fuwafude_ver1/FuwaFude.ttf"
output_file = "C:/Vigston/VigStreamClip/output/FuwaFude_supported_chars.txt"
extract_supported_chars(ttf_path, output_file)