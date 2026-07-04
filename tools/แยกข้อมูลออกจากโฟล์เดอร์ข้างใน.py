import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

def get_unique_filename(folder, filename):
    name, ext = os.path.splitext(filename)
    new_filename = filename
    counter = 1

    while os.path.exists(os.path.join(folder, new_filename)):
        new_filename = f"{name}_{counter}{ext}"
        counter += 1

    return new_filename

def merge_files():
    root = tk.Tk()
    root.withdraw()

    source_folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ต้นทาง")
    if not source_folder:
        messagebox.showwarning("ยกเลิก", "ไม่ได้เลือกโฟลเดอร์ต้นทาง")
        return

    destination_folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
    if not destination_folder:
        messagebox.showwarning("ยกเลิก", "ไม่ได้เลือกโฟลเดอร์ปลายทาง")
        return

    count = 0

    for root_dir, dirs, files in os.walk(source_folder):
        for file in files:
            source_path = os.path.join(root_dir, file)

            # กันไม่ให้ดึงไฟล์จากโฟลเดอร์ปลายทาง ถ้าอยู่ข้างในต้นทาง
            if os.path.commonpath([source_path, destination_folder]) == destination_folder:
                continue

            new_filename = get_unique_filename(destination_folder, file)
            destination_path = os.path.join(destination_folder, new_filename)

            shutil.copy2(source_path, destination_path)
            count += 1

    messagebox.showinfo(
        "สำเร็จ",
        f"ดึงไฟล์เสร็จแล้วทั้งหมด {count} ไฟล์\n\nรวมไว้ที่:\n{destination_folder}"
    )

merge_files()