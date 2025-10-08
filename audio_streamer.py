import ffmpeg
import numpy as np
import serial
import time
import sounddevice as sd
import threading

def stream_audio(
    file_path,
    sample_rate=3000,
    window_size=256,
    hop_size=128,
    smooth_neighbors=3,
    serial_port="COM3",
    baud_rate=115200
):
    """
    Stream audio magnitude and frequency over serial.
    Magnitude is normalized to 0–127.
    Frequency is normalized to 0–99 (clamped).
    Plays audio through the computer speakers simultaneously.
    """
    # === Decode audio to PCM ===
    try:
        out, _ = (
            ffmpeg
            .input(file_path)
            .output(
                'pipe:',
                format='f32le',
                acodec='pcm_f32le',
                ac=1,
                ar=str(sample_rate)
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e}")
        return

    audio = np.frombuffer(out, np.float32)
    window = np.hanning(window_size)
    freqs = np.fft.rfftfreq(window_size, 1 / sample_rate)

    avg_amps = []
    avg_freqs = []

    # === Play audio in background thread ===
    def play_audio():
        sd.play(audio, samplerate=sample_rate)
        sd.wait()  # wait until playback is done

    threading.Thread(target=play_audio, daemon=True).start()

    # === Compute magnitude & frequency per window ===
    for start in range(0, len(audio) - window_size, hop_size):
        segment = audio[start:start + window_size] * window
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

    # === Smooth magnitudes ===
    smoothed_amps = np.copy(avg_amps)
    n = smooth_neighbors
    for i in range(len(avg_amps)):
        start = max(0, i - n)
        end = min(len(avg_amps), i + n + 1)
        smoothed_amps[i] = np.mean(avg_amps[start:end])

    # === Normalize ===
    def normalize_to_range(arr, min_val, max_val):
        if np.max(arr) - np.min(arr) == 0:
            return np.full_like(arr, min_val)
        return min_val + (arr - np.min(arr)) * (max_val - min_val) / (np.max(arr) - np.min(arr))

    # Magnitude 0–127
    scaled_amps = normalize_to_range(smoothed_amps, 0, 127)

    # Frequency 0–99 (clamped)
    scaled_freqs = normalize_to_range(avg_freqs, 0, 100)
    scaled_freqs = np.clip(scaled_freqs, 0, 99)

    # === Serial connection ===
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Connected to {serial_port}")
    except serial.SerialException:
        ser = None
        print("Serial port not available, streaming skipped.")

    # === Calculate delay per window ===
    delay = hop_size / sample_rate
    print(f"Streaming delay: {delay:.4f} seconds per frame")

    # === Stream over serial while audio plays ===
    for amp, freq in zip(scaled_amps, scaled_freqs):
        message = f"{int(round(amp))},{int(round(freq))}\n"
        if ser:
            ser.write(message.encode('utf-8'))
        print(f"Sent: {message.strip()}")
        time.sleep(delay)

    if ser:
        ser.close()

    print("Streaming complete")
