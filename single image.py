import cv2
import tkinter as tk
from tkinter import font
import numpy as np
import os
from ids_peak import ids_peak
from ids_peak import ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl

root = tk.Tk()
root.title("pyCam")
root.geometry("350x300")

# ---- GUI variabler ----

running = False
show_img = False
testing = False

count = 0
current_frame = None
image_file = "coner.png"
captured_image = False

counterText = tk.StringVar()
statusText = tk.StringVar()

counterText.set("0/1")
statusText.set("")

# ---- Fonts ----

custom_font = font.Font(family="Arial", size=16)
customtitle_font = font.Font(family="Arial", size=24)
counter_font = font.Font(family="Arial", size=48, weight="bold")

# ---- Cam ----

ids_device = None
ids_remote = None
ids_data_stream = None
ids_started = False
ids_library_initialized = False


def close_ids_camera():
    global ids_device, ids_remote, ids_data_stream, ids_started
    global ids_library_initialized

    if ids_remote is not None and ids_started:
        try:
            ids_remote.FindNode("AcquisitionStop").Execute()
            ids_remote.FindNode("AcquisitionStop").WaitUntilDone()
        except Exception as error:
            print(f"Could not stop IDS acquisition: {error}")

    if ids_data_stream is not None:
        if ids_started:
            try:
                ids_data_stream.StopAcquisition(
                    ids_peak.AcquisitionStopMode_Default
                )
            except Exception as error:
                print(f"Could not stop IDS data stream: {error}")

        try:
            ids_data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
        except Exception as error:
            print(f"Could not flush IDS data stream: {error}")

        try:
            for buffer in ids_data_stream.AnnouncedBuffers():
                ids_data_stream.RevokeBuffer(buffer)
        except Exception as error:
            print(f"Could not revoke IDS buffers: {error}")

    if ids_remote is not None:
        try:
            ids_remote.FindNode("TLParamsLocked").SetValue(0)
        except Exception as error:
            print(f"Could not unlock IDS transport layer: {error}")

    if ids_library_initialized:
        ids_peak.Library.Close()

    ids_device = None
    ids_remote = None
    ids_data_stream = None
    ids_started = False
    ids_library_initialized = False


def open_ids_camera():
    global ids_device, ids_remote, ids_data_stream, ids_started
    global ids_library_initialized

    try:
        ids_peak.Library.Initialize()
        ids_library_initialized = True

        manager = ids_peak.DeviceManager.Instance()
        manager.Update()

        if len(manager.Devices()) == 0:
            print("No IDS camera found!")
            statusText.set("NO CAMERA")
            close_ids_camera()
            return False

        ids_device = manager.Devices()[0].OpenDevice(
            ids_peak.DeviceAccessType_Control
        )
        ids_remote = ids_device.RemoteDevice().NodeMaps()[0]

        ids_remote.FindNode("AcquisitionMode").SetCurrentEntry("Continuous")
        ids_remote.FindNode("TriggerMode").SetCurrentEntry("Off")

        ids_data_stream = ids_device.DataStreams()[0].OpenDataStream()
        payload_size = ids_remote.FindNode("PayloadSize").Value()
        buffer_count = ids_data_stream.NumBuffersAnnouncedMinRequired()

        for _ in range(buffer_count):
            buffer = ids_data_stream.AllocAndAnnounceBuffer(payload_size)
            ids_data_stream.QueueBuffer(buffer)

        ids_remote.FindNode("TLParamsLocked").SetValue(1)
        ids_data_stream.StartAcquisition()
        ids_remote.FindNode("AcquisitionStart").Execute()
        ids_remote.FindNode("AcquisitionStart").WaitUntilDone()
        ids_started = True

        print("IDS camera running.")
        return True

    except Exception as error:
        print(f"Could not open IDS camera: {error}")
        statusText.set("NO CAMERA")
        close_ids_camera()
        return False


def read_ids_frame(timeout_ms=30):
    if ids_data_stream is None or not ids_started:
        return None

    buffer = None

    try:
        buffer = ids_data_stream.WaitForFinishedBuffer(timeout_ms)
        image = ids_peak_ipl_extension.BufferToImage(buffer)
        converted = image.ConvertTo(ids_peak_ipl.PixelFormatName_BGR8)
        return converted.get_numpy_3D().copy()

    except Exception:
        return None

    finally:
        if buffer is not None:
            try:
                ids_data_stream.QueueBuffer(buffer)
            except Exception as error:
                print(f"Could not requeue IDS buffer: {error}")


camera_ok = open_ids_camera()

# ---- Counter function ----

def increase_counter():
    global count, current_frame, captured_image

    if count == 1:
        count = 0
        captured_image = False

    count += 1

    if current_frame is None:
        statusText.set("NO CAMERA")
        Statuslabel.config(fg="red")
        return

    cv2.imwrite(image_file, current_frame)
    captured_image = True

    counterText.set(f"{count}/1")
    statusText.set("DONE")
    Statuslabel.config(fg="green")

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

if not camera_ok:
    Statuslabel.config(fg="red")

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


def build_single_image(tile_size):
    return read_image_or_placeholder(image_file, tile_size, captured_image)


def show_saved_image(tile_size):
    image = build_single_image(tile_size)
    cv2.imshow("Saved Image", image)


def update_loop():
    global current_frame

    frame = read_ids_frame()

    if frame is not None:
        current_frame = frame.copy()
        preview = cv2.resize(frame, (1000, 750))
        cv2.imshow("IDS Camera", preview)

    show_saved_image((320, 240))
    cv2.waitKey(1)

    # Kør update_loop igen efter 30 ms
    root.after(30, update_loop)


def on_close():
    close_ids_camera()
    cv2.destroyAllWindows()


    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

# Start kamera loop
root.after(30, update_loop)

# Start Tkinter
root.mainloop()
