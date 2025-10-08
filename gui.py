import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from audio_streamer import stream_audio

# === Appearance settings ===
ctk.set_appearance_mode("dark")   # "dark", "light", or "system"
ctk.set_default_color_theme("dark-blue")  # "blue", "green", "dark-blue"

# === Functions ===
def browse_file():
    filename = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
    if filename:
        file_entry.set(filename)

def start_stream():
    file_path = file_entry.get()
    if not file_path:
        messagebox.showwarning("Warning", "Please select an audio file")
        return
    try:
        sr = int(sr_entry.get())
        window_size = int(window_entry.get())
        hop_size = int(hop_entry.get())
        smooth_neighbors = int(smooth_entry.get())
        serial_port = port_entry.get()
        baud_rate = int(baud_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Invalid numeric input")
        return

    threading.Thread(
        target=stream_audio,
        args=(file_path, sr, window_size, hop_size, smooth_neighbors, serial_port, baud_rate),
        daemon=True
    ).start()

# === Root Window ===
root = ctk.CTk()
root.title("vibrant!")
root.geometry("600x400")
root.resizable(False, False)

# === Variables ===
file_entry = ctk.StringVar()
sr_entry = ctk.StringVar(value="3000")
window_entry = ctk.StringVar(value="256")
hop_entry = ctk.StringVar(value="128")
smooth_entry = ctk.StringVar(value="3")
port_entry = ctk.StringVar(value="COM3")
baud_entry = ctk.StringVar(value="115200")

# === Layout Frames ===
file_frame = ctk.CTkFrame(root, corner_radius=10)
file_frame.pack(padx=20, pady=15, fill="x")

param_frame = ctk.CTkFrame(root, corner_radius=10)
param_frame.pack(padx=20, pady=15, fill="x")

button_frame = ctk.CTkFrame(root, corner_radius=10)
button_frame.pack(padx=20, pady=15, fill="x")

# === File Selection ===
ctk.CTkLabel(file_frame, text="Audio File:").grid(row=0, column=0, padx=5, pady=10, sticky="w")
ctk.CTkEntry(file_frame, textvariable=file_entry, width=300).grid(row=0, column=1, padx=5, pady=10)
ctk.CTkButton(file_frame, text="Browse", command=browse_file).grid(row=0, column=2, padx=5, pady=10)

# === Parameters ===
labels = ["Sample Rate:", "Window Size:", "Hop Size:", "Smooth Neighbors:", "Serial Port:", "Baud Rate:"]
variables = [sr_entry, window_entry, hop_entry, smooth_entry, port_entry, baud_entry]

for i, (label, var) in enumerate(zip(labels, variables)):
    ctk.CTkLabel(param_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="w")
    ctk.CTkEntry(param_frame, textvariable=var).grid(row=i, column=1, padx=5, pady=5)

# === Start Button ===
ctk.CTkButton(button_frame, text="Start Streaming", command=start_stream, height=40).pack(pady=10)

root.mainloop()
