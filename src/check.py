import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import tkinter as tk

def show_plot():
    print("SHOW!")  # 確認用
    plt.plot([1, 2, 3], [4, 5, 6])
    plt.title("テストグラフ")
    plt.grid()
    plt.tight_layout()
    plt.show()

root = tk.Tk()
tk.Button(root, text="グラフを表示", command=lambda: root.after(100, show_plot)).pack(padx=20, pady=20)
root.mainloop()