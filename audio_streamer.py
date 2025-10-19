import ffmpeg
import numpy as np
import serial
import time
import sounddevice as sd
import threading


 # === Constants ===
WINDOW_SIZE = 256
HOP_SIZE = 128
SMOOTH_NEIGHBORS = 3
BAUD_RATE = 115200

def stream_vibr_file(file_path, serial_port):

    file = open(file_path, "r")
    sample_rate = file.readline()

     # === Serial connection ===
    try:
        ser = serial.Serial(serial_port, BAUD_RATE, timeout=1)
        print(f"Connected to {serial_port}")
    except serial.SerialException:
        ser = None
        print("Serial port not available, streaming skipped.")
    delay = HOP_SIZE / int(sample_rate);  
    print(f"Streaming delay: {delay:.4f} seconds per frame")

    #stream
    for l in file:
        if ser:
            ser.write(l.encode("utf-8"))
        print(f"Sent: {l.strip()}")
        time.sleep(delay)
    file.close()


def stream_audio(file_paths, sample_rate=3000, serial_port="COM3", output_file="output.vibr"):
    """
    Stream multiple audio layers concurrently and log data to a text file.
    Each serial line contains amp,freq pairs for each file separated by semicolons.
    Example: "120,45;98,32;110,40"
    """

    # === Decode all audio layers ===
    audio_layers = []
    for path in file_paths:
        try:
            out, _ = (
                ffmpeg
                .input(path)
                .output(
                    'pipe:',
                    format='f32le',
                    acodec='pcm_f32le',
                    ac=1,
                    ar=str(sample_rate)
                )
                .run(capture_stdout=True, capture_stderr=True)
            )
            audio_layers.append(np.frombuffer(out, np.float32))
        except ffmpeg.Error as e:
            print(f"FFmpeg error decoding {path}: {e}")
            return

    if not audio_layers:
        print("No valid audio files provided.")
        return

    # === Match all layers to same length ===
    min_length = min(len(a) for a in audio_layers)
    audio_layers = [a[:min_length] for a in audio_layers]

    # === Frequency bins ===
    window = np.hanning(WINDOW_SIZE)
    freqs = np.fft.rfftfreq(WINDOW_SIZE, 1 / sample_rate)

    # === Play all layers concurrently ===
    def play_all():
        combined = np.sum(audio_layers, axis=0)
        combined /= np.max(np.abs(combined))
        sd.play(combined, samplerate=sample_rate)
        sd.wait()

    threading.Thread(target=play_all, daemon=True).start()

    # === Analyze each layer ===
    all_amps = []
    all_freqs = []

    for audio in audio_layers:
        avg_amps, avg_freqs = [], []

        for start in range(0, len(audio) - WINDOW_SIZE, HOP_SIZE):
            segment = audio[start:start + WINDOW_SIZE] * window
            spectrum = np.fft.rfft(segment)
            magnitude = np.abs(spectrum)

            if np.sum(magnitude) > 0:
                avg_freq = np.sum(freqs * magnitude) / np.sum(magnitude)
                avg_amp = np.mean(magnitude)
            else:
                avg_freq = 0
                avg_amp = 0

            avg_amps.append(avg_amp)
            avg_freqs.append(avg_freq)

        avg_amps = np.array(avg_amps)
        avg_freqs = np.array(avg_freqs)

        # Smooth amplitude
        smoothed = np.copy(avg_amps)
        for i in range(len(avg_amps)):
            s = max(0, i - SMOOTH_NEIGHBORS)
            e = min(len(avg_amps), i + SMOOTH_NEIGHBORS + 1)
            smoothed[i] = np.mean(avg_amps[s:e])

        # Normalize
        def normalize(arr, min_val, max_val):
            if np.max(arr) == np.min(arr):
                return np.full_like(arr, min_val)
            return min_val + (arr - np.min(arr)) * (max_val - min_val) / (np.max(arr) - np.min(arr))

        scaled_amps = normalize(smoothed, 0, 127)
        scaled_freqs = np.clip(normalize(avg_freqs, 0, 100), 0, 99)

        all_amps.append(scaled_amps)
        all_freqs.append(scaled_freqs)

    # === Sync all layers to same frame count ===
    min_frames = min(len(a) for a in all_amps)
    all_amps = [a[:min_frames] for a in all_amps]
    all_freqs = [f[:min_frames] for f in all_freqs]

    # === Serial connection ===
    try:
        ser = serial.Serial(serial_port, BAUD_RATE, timeout=1)
        print(f"Connected to {serial_port}")
    except serial.SerialException:
        ser = None
        print("Serial port not available, streaming skipped.")

    delay = HOP_SIZE / sample_rate
    print(f"Streaming delay: {delay:.4f} seconds per frame")

    # === Open file for logging ===
    with open(output_file, "w") as f:

        f.write(str(sample_rate) + '/\n')
        # Stream data
        for frame in range(min_frames):
            message_parts = []
            for i in range(len(audio_layers)):
                amp = int(round(all_amps[i][frame]))
                freq = int(round(all_freqs[i][frame]))
                message_parts.append(f"{amp},{freq}")

            message = ";".join(message_parts) + "\n"
            
            # Serial output
            if ser:
                ser.write(message.encode("utf-8"))

            # File output
            f.write(message)

            print(f"Sent: {message.strip()}")
            time.sleep(delay)

    if ser:
        ser.close()

    print(f"Streaming complete. Data saved to {output_file}")
