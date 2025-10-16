import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from audio_streamer import stream_audio

# === Appearance settings ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# === Functions ===
def add_files():
    """Add one or more audio files to the list."""
    files = filedialog.askopenfilenames(filetypes=[("Audio files", "*.wav *.mp3")])
    for f in files:
        if f not in file_list:
            file_list.append(f)
            file_listbox.insert(ctk.END, f)

def remove_selected():
    """Remove selected files from the list."""
    selected = file_listbox.curselection()
    for index in reversed(selected):  # remove from end to preserve indices
        file_listbox.delete(index)
        file_list.pop(index)

def start_stream():
    """Start audio streaming in a separate thread."""
    if not file_list:
        messagebox.showwarning("Warning", "Please add at least one audio file.")
        return

    try:
        sr = int(sr_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Sample rate must be a number.")
        return

    serial_port = port_entry.get()
    if not serial_port:
        messagebox.showwarning("Warning", "Please enter a serial port.")
        return

    # Disable start button while running
    start_button.configure(state="disabled", text="Streaming...")

    def run_stream():
        stream_audio(file_list, sr, serial_port)
        start_button.configure(state="normal", text="Start Streaming")

    threading.Thread(target=run_stream, daemon=True).start()

# === Root Window ===
root = ctk.CTk()
root.title("Multi-Layer Audio Streamer")
root.geometry("600x500")
root.resizable(False, False)

# === Variables ===
file_list = []
sr_entry = ctk.StringVar(value="3000")
port_entry = ctk.StringVar(value="COM3")

# === File List Frame ===
file_frame = ctk.CTkFrame(root, corner_radius=10)
file_frame.pack(padx=20, pady=15, fill="both", expand=True)

ctk.CTkLabel(file_frame, text="Audio Layers:", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=5)

file_listbox = ctk.CTkTextbox(file_frame, height=200)
file_listbox.pack(padx=10, pady=5, fill="x")

button_row = ctk.CTkFrame(file_frame)
button_row.pack(pady=5)
ctk.CTkButton(button_row, text="Add Files", command=add_files, width=120).pack(side="left", padx=5)
ctk.CTkButton(button_row, text="Remove Selected", command=remove_selected, width=150).pack(side="left", padx=5)

# === Parameters Frame ===
param_frame = ctk.CTkFrame(root, corner_radius=10)
param_frame.pack(padx=20, pady=15, fill="x")

ctk.CTkLabel(param_frame, text="Sample Rate:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
ctk.CTkEntry(param_frame, textvariable=sr_entry).grid(row=0, column=1, padx=5, pady=5)

ctk.CTkLabel(param_frame, text="Serial Port:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
ctk.CTkEntry(param_frame, textvariable=port_entry).grid(row=1, column=1, padx=5, pady=5)

# === Start Button ===
start_button = ctk.CTkButton(root, text="Start Streaming", command=start_stream, height=40)
start_button.pack(pady=20)

# === Run App ===
root.mainloop()
