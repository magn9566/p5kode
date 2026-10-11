import cv2
import csv
import tkinter as tk
from tkinter import font
import serial
import time
import numpy as np
import os

root = tk.Tk()
root.title("pyCam")
root.geometry("350x300")

# ---- Serial ----

try:
    ser = serial.Serial("COM3", 115200, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
except serial.SerialException:
    print("Could not open COM3. Running without serial connection.")
    ser = None

# ---- GUI variabler ----

running = False
show_img = False
testing = False

count = 0
current_frame = None
image_files = ["image1.png", "image2.png", "image3.png", "image4.png"]
captured_images = [False, False, False, False]
result_folder = r"C:\Users\Public\TcVision\Images"
combined_image_file = os.path.join(result_folder, "combined_image.png")

os.makedirs(result_folder, exist_ok=True)

counterText = tk.StringVar()
statusText = tk.StringVar()

counterText.set("0/4")
statusText.set("")

# ---- Fonts ----

custom_font = font.Font(family="Arial", size=16)
customtitle_font = font.Font(family="Arial", size=24)
counter_font = font.Font(family="Arial", size=48, weight="bold")

# ---- Cam ----

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_SETTINGS, 1)
if not (cap.isOpened()): print("Could not open video device")

# cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
# cap.set(cv2.CAP_PROP_EXPOSURE, -10)
# cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

# ---- Counter function ----

def increase_counter():
    global count, current_frame, captured_images

    if count == 4:
        count = 0
        captured_images = [False, False, False, False]

    count += 1

    if current_frame is None:
        statusText.set("NO CAMERA")
        Statuslabel.config(fg="red")
        return

    filename = image_files[count - 1]
    cv2.imwrite(filename, current_frame)
    captured_images[count - 1] = True

    counterText.set(f"{count}/4")
    if all(captured_images):
        combined = build_combined_image((320, 240))
        cv2.imwrite(combined_image_file, combined)
        statusText.set("DONE")
        Statuslabel.config(fg="green")
    else:
        statusText.set(f"Saved {filename}")
        Statuslabel.config(fg="black")

# ---- GUI ----

title = tk.Label(
    root,
    text="Counter",
    font=customtitle_font,
    pady=20
)
title.pack()

Counterlabel = tk.Label(
    root,
    textvariable=counterText,
    font=counter_font
)
Counterlabel.pack(pady=10)

Statuslabel = tk.Label(
    root,
    textvariable=statusText,
    font=customtitle_font,
    fg="green"
)
Statuslabel.pack(pady=5)

count_button = tk.Button(
    root,
    text="Next",
    font=custom_font,
    command=increase_counter,
    width=12,
    height=2
)
count_button.pack(pady=15)


def make_placeholder(text, size):
    width, height = size
    image = np.full((height, width, 3), 230, dtype=np.uint8)
    cv2.rectangle(image, (0, 0), (width - 1, height - 1), (170, 170, 170), 2)
    cv2.putText(
        image,
        text,
        (20, height // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (80, 80, 80),
        2,
        cv2.LINE_AA,
    )
    return image


def read_image_or_placeholder(filename, size, is_updated):
    if is_updated and os.path.exists(filename):
        image = cv2.imread(filename)
        if image is not None:
            return cv2.resize(image, size)

    return make_placeholder(filename, size)


def build_combined_image(tile_size):
    images = [
        read_image_or_placeholder(filename, tile_size, captured_images[index])
        for index, filename in enumerate(image_files)
    ]

    top = cv2.hconcat(images[:2])
    bottom = cv2.hconcat(images[2:])
    return cv2.vconcat([top, bottom])


def show_combined_images(tile_size):
    combined = build_combined_image(tile_size)
    cv2.imshow("Combined Image", combined)


def update_loop():
    global current_frame

    ret, frame = cap.read()

    if ret:
        current_frame = frame.copy()
        cv2.imshow("Camera", frame)
        cv2.waitKey(1)

    show_combined_images((320, 240))

    # Kør update_loop igen efter 30 ms
    root.after(30, update_loop)


def on_close():
    cap.release()
    cv2.destroyAllWindows()

    if ser is not None:
        ser.close()

    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

# Start kamera loop
root.after(30, update_loop)

# Start Tkinter
root.mainloop()
