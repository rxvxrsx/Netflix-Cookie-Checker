import os
import tkinter as tk
from tkinter import filedialog

def normalize_ext(ext):
    ext = ext.strip()

    if not ext:
        return ""

    if not ext.startswith("."):
        ext = "." + ext

    return ext.lower()

def browse_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(
        title="เลือกโฟลเดอร์ที่ต้องการเปลี่ยนนามสกุลไฟล์"
    )

    root.destroy()
    return folder

def change_extensions():
    print("=" * 55)
    print("โปรแกรมเปลี่ยนนามสกุลไฟล์ทั้งหมดในโฟลเดอร์")
    print("=" * 55)

    print("\nกำลังเปิดหน้าต่างเลือกโฟลเดอร์...")
    folder = browse_folder()

    if not folder:
        print("\n❌ ไม่ได้เลือกโฟลเดอร์")
        input("กด Enter เพื่อปิดโปรแกรม...")
        return

    print("\nโฟลเดอร์ที่เลือก:")
    print(folder)

    new_ext = input("\nใส่นามสกุลใหม่ เช่น jpg, png, pdf: ").strip()

    if not new_ext:
        print("\n❌ กรุณาใส่นามสกุลใหม่")
        input("กด Enter เพื่อปิดโปรแกรม...")
        return

    new_ext = normalize_ext(new_ext)

    confirm = input(f"\nยืนยันเปลี่ยนไฟล์ทั้งหมดเป็น {new_ext} ? (y/n): ").strip().lower()

    if confirm != "y":
        print("\nยกเลิกการทำงาน")
        input("กด Enter เพื่อปิดโปรแกรม...")
        return

    count = 0
    skipped = 0

    for filename in os.listdir(folder):
        old_path = os.path.join(folder, filename)

        if not os.path.isfile(old_path):
            continue

        name, old_ext = os.path.splitext(filename)

        if old_ext.lower() == new_ext:
            skipped += 1
            continue

        new_filename = name + new_ext
        new_path = os.path.join(folder, new_filename)

        counter = 1
        while os.path.exists(new_path):
            new_filename = f"{name}_{counter}{new_ext}"
            new_path = os.path.join(folder, new_filename)
            counter += 1

        os.rename(old_path, new_path)
        count += 1

    print("\n" + "=" * 55)
    print("✅ เสร็จแล้ว")
    print(f"เปลี่ยนนามสกุลสำเร็จ: {count} ไฟล์")
    print(f"ข้ามไฟล์ที่เป็นนามสกุลนี้อยู่แล้ว: {skipped} ไฟล์")
    print("=" * 55)

    input("\nกด Enter เพื่อปิดโปรแกรม...")

change_extensions()