# -*- coding: utf-8 -*-
"""윈도우 탐색기 창으로 파일을 고른다. 화면을 띄우는 부분이라 테스트에서는 대역을 쓴다."""
import threading


class NativeDialogs:
    VIDEO_TYPES = [("Video", "*.mp4 *.mov *.mkv *.webm *.avi *.m4v"), ("All", "*.*")]

    def __init__(self):
        self._lock = threading.Lock()

    def _with_root(self, fn):
        import tkinter as tk
        with self._lock:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                return fn(root) or ""
            finally:
                root.destroy()

    def open_video(self) -> str:
        from tkinter import filedialog
        return self._with_root(lambda root: filedialog.askopenfilename(
            parent=root, title="영상 선택", filetypes=self.VIDEO_TYPES))

    def open_image(self) -> str:
        from tkinter import filedialog
        return self._with_root(lambda root: filedialog.askopenfilename(
            parent=root, title="스티커 그림 선택",
            filetypes=[("그림", "*.png *.jpg *.jpeg *.gif *.webp"), ("All", "*.*")]))

    def save_mp4(self, suggest: str) -> str:
        from tkinter import filedialog
        return self._with_root(lambda root: filedialog.asksaveasfilename(
            parent=root, title="mp4 저장", defaultextension=".mp4", initialfile=suggest,
            filetypes=[("MP4", "*.mp4")]))
