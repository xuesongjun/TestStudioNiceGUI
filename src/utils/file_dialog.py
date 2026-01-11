"""
Windows文件对话框工具
使用tkinter创建文件/文件夹选择对话框
"""
import tkinter as tk
from tkinter import filedialog
import threading


def select_folder(title="选择文件夹", initial_dir=None):
    """
    打开Windows文件夹选择对话框

    参数:
        title: 对话框标题
        initial_dir: 初始目录

    返回:
        选择的文件夹路径,如果取消则返回None
    """
    result = {'path': None}

    def open_dialog():
        # 创建隐藏的根窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes('-topmost', True)  # 置顶显示

        # 打开文件夹选择对话框
        folder_path = filedialog.askdirectory(
            title=title,
            initialdir=initial_dir
        )

        result['path'] = folder_path if folder_path else None
        root.destroy()

    # 在主线程中运行对话框
    thread = threading.Thread(target=open_dialog)
    thread.start()
    thread.join()  # 等待对话框关闭

    return result['path']


def select_file(title="选择文件", initial_dir=None, filetypes=None):
    """
    打开Windows文件选择对话框

    参数:
        title: 对话框标题
        initial_dir: 初始目录
        filetypes: 文件类型过滤,例如 [("文本文件", "*.txt"), ("所有文件", "*.*")]

    返回:
        选择的文件路径,如果取消则返回None
    """
    result = {'path': None}

    if filetypes is None:
        filetypes = [("所有文件", "*.*")]

    def open_dialog():
        # 创建隐藏的根窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes('-topmost', True)  # 置顶显示

        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title=title,
            initialdir=initial_dir,
            filetypes=filetypes
        )

        result['path'] = file_path if file_path else None
        root.destroy()

    # 在主线程中运行对话框
    thread = threading.Thread(target=open_dialog)
    thread.start()
    thread.join()  # 等待对话框关闭

    return result['path']
