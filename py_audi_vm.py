# pip install pyaudio numpy
import pyaudio, wave, numpy as np, os, sys

FILE_TO_PLAY = "sample.wav"      # put your WAV here (16- or 32-bit PCM)
TARGET_DEVICE_SUBSTR = "Voicemeeter Input"   # we WRITE to this (VAIO)
TARGET_SR = 48000
FRAMES_PER_BUFFER = 480
TARGET_VOL = 0.9

pa = pyaudio.PyAudio()

def find_output_device(substr: str) -> int:
    s = substr.lower()
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        if d.get('maxOutputChannels',0) > 0 and s in d['name'].lower():
            return i
    print("[!] OUTPUT device not found. Devices:")
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        print(f"{i:>2} | out:{d.get('maxOutputChannels',0)} in:{d.get('maxInputChannels',0)} | {d['name']}")
    pa.terminate(); sys.exit(1)

def wav_to_float_mono_48k(path: str) -> np.ndarray:
    with wave.open(path, 'rb') as wf:
        sr = wf.getframerate(); ch = wf.getnchannels(); sw = wf.getsampwidth(); n = wf.getnframes()
        raw = wf.readframes(n)
    if sw == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / (2**31)
    else:
        raise RuntimeError(f"Unsupported WAV bit depth: {sw*8} bits")
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)  # mono
    if sr != TARGET_SR:
        n_to = int(round(data.shape[0] * TARGET_SR / sr))
        xp = np.linspace(0, 1, data.shape[0], endpoint=False, dtype=np.float64)
        xq = np.linspace(0, 1, n_to,         endpoint=False, dtype=np.float64)
        data = np.interp(xq, xp, data.astype(np.float64)).astype(np.float32)
    data *= TARGET_VOL
    return data.astype(np.float32)

def play_float_mono(x: np.ndarray, dev_index: int):
    stream = pa.open(format=pyaudio.paFloat32, channels=1, rate=TARGET_SR,
                     output=True, output_device_index=dev_index,
                     frames_per_buffer=FRAMES_PER_BUFFER)
    try:
        off = 0; n = x.shape[0]
        while off < n:
            end = min(off + FRAMES_PER_BUFFER, n)
            stream.write(x[off:end].tobytes())
            off = end
    finally:
        stream.stop_stream(); stream.close()

def main():
    if not os.path.exists(FILE_TO_PLAY):
        print(f"[!] FILE_TO_PLAY not found: {FILE_TO_PLAY}")
        pa.terminate(); sys.exit(1)
    dev = find_output_device(TARGET_DEVICE_SUBSTR)
    audio = wav_to_float_mono_48k(FILE_TO_PLAY)
    print(f"→ Playing to: {pa.get_device_info_by_index(dev)['name']}")
    play_float_mono(audio, dev)
    print("✓ Done. In VoiceMeeter, B1 must be ON on the VAIO strip; in the meeting, Mic = 'Voicemeeter Out B1'.")
    pa.terminate()

if __name__ == "__main__":
    import numpy as np
    main()
