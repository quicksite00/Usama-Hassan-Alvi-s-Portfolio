import sys
import time
import wave
import array
import math
import pyaudio
import whisper
import warnings

# Suppress whisper warnings
warnings.filterwarnings("ignore")

# Configuration from GEMINI_phase3_4.md
WHISPER_MODEL = "tiny"
SILENCE_THRESHOLD_SECONDS = 2.0
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Load model globally to avoid reloading
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model(WHISPER_MODEL)
    return _model

def listen() -> str:
    """Record from mic. Stop after 2 seconds of silence. Return transcribed string."""
    p = pyaudio.PyAudio()
    
    # Debug: Check default input device
    try:
        default_device = p.get_default_input_device_info()
        print(f"DEBUG: Using device: {default_device['name']}")
    except Exception as e:
        print(f"DEBUG Error: No default input device found! {e}")
        return ""

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK_SIZE)

    print("🎤 Listening... (speak now)")
    
    frames = []
    silent_chunks = 0
    # Calculate how many chunks represent the silence threshold
    threshold_chunks = int(SILENCE_THRESHOLD_SECONDS * RATE / CHUNK_SIZE)
    
    # Simple RMS threshold for silence (can be adjusted)
    # 50 is better for low-gain mics (seen 107 in debug)
    RMS_THRESHOLD = 50 

    max_rms = 0
    try:
        while True:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)
            
            # Check for silence
            audio_data = array.array('h', data)
            rms = math.sqrt(sum([abs(x)**2 for x in audio_data]) / len(audio_data))
            if rms > max_rms: max_rms = rms
            
            if rms < RMS_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            if silent_chunks > threshold_chunks:
                print(f"DEBUG: Stopped after {SILENCE_THRESHOLD_SECONDS}s silence. Max RMS seen: {max_rms:.2f}")
                break
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    if max_rms < RMS_THRESHOLD:
        print("DEBUG: No sound detected (below threshold).")
        return ""

    if len(frames) < 10: # Very short recording
        print("DEBUG: Recording too short, likely no audio captured.")
        return ""

    print("Transcribing...")
    
    # Save to temp file for whisper
    temp_filename = "temp_recording.wav"
    wf = wave.open(temp_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    model = _get_model()
    
    # Use soundfile to load the audio as a numpy array
    # This avoids dependency on ffmpeg
    import soundfile as sf
    import numpy as np
    
    audio_data, samplerate = sf.read(temp_filename)
    # Whisper expects 16k float32
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
        
    result = model.transcribe(audio_data)
    
    return result["text"].strip()

def text_mode() -> str:
    """Read a line from stdin. Return it as string. Used as --text fallback."""
    try:
        return input("⌨  Type your instruction: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""

if __name__ == "__main__":
    # Standalone test
    print("Testing STT Mode...")
    text = listen()
    if text:
        print(f"Result: {text}")
    else:
        print("No audio captured. Testing Text Mode fallback...")
        text = text_mode()
        print(f"Result: {text}")
