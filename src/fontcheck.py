import matplotlib.font_manager as fm

# 日本語っぽいフォントだけをフィルタして表示
for font in fm.findSystemFonts(fontpaths=None, fontext='ttf'):
    font_name = fm.FontProperties(fname=font).get_name()
    if any(keyword in font_name for keyword in ['Gothic', 'Mincho', 'Noto', 'Meiryo', 'IPA', 'Yu']):
        print(font_name)