import os
import json
import time
import threading
import pyaudio
from vosk import Model, KaldiRecognizer
from gi.repository import GLib
from .config import MODEL_PATH, SAMPLE_RATE, FRAMES_PER_BUFFER, READ_CHUNK_SIZE

class Transcriber(threading.Thread):
    """
    Background thread for audio recording and speech recognition.
    """
    def __init__(self, update_callback, status_callback):
        super().__init__()
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.running = False
        self.paused = True
        self.daemon = True
        self.model = None
        
        # Load Vosk Model
        self._load_model()

    def _load_model(self):
        if not MODEL_PATH or not os.path.exists(MODEL_PATH):
            self.status_callback(f"Error: Model not found at {MODEL_PATH}")
            self.model = None
        else:
            try:
                self.model = Model(MODEL_PATH)
                self.status_callback("Model loaded. Ready.")
            except Exception as e:
                self.status_callback(f"Error loading model: {e}")
                self.model = None

    def run(self):
        if not self.model:
            return

        self.rec = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.p = pyaudio.PyAudio()
        
        stream = None
        try:
            stream = self.p.open(format=pyaudio.paInt16, 
                               channels=1, 
                               rate=SAMPLE_RATE, 
                               input=True, 
                               frames_per_buffer=FRAMES_PER_BUFFER)
            stream.start_stream()
            self.running = True
            
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue

                data = stream.read(READ_CHUNK_SIZE, exception_on_overflow=False)
                if len(data) == 0:
                    break
                
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = res['text']
                    if text:
                        GLib.idle_add(self.update_callback, text, True)
                else:
                    partial = json.loads(self.rec.PartialResult())
                    if partial['partial']:
                        GLib.idle_add(self.update_callback, partial['partial'], False)

        except Exception as e:
            GLib.idle_add(self.status_callback, f"Audio Error: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            self.p.terminate()

    def start_listening(self):
        self.paused = False
        self.status_callback("Listening...")

    def stop_listening(self):
        self.paused = True
        self.status_callback("Paused.")

    def stop_app(self):
        self.running = False
