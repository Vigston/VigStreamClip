import matplotlib.font_manager as fm

fonts = fm.findSystemFonts(fontpaths=None, fontext='ttf')
for f in fonts:
    if "Gothic" in f or "Mincho" in f or "Noto" in f or "Maru" in f or "Yu" in f or "Meiryo" in f:
        print(f)