import json
import os
import threading
import time

import speech_recognition as sr
from vosk import KaldiRecognizer, Model


class WakeWordListener:
    def __init__(self, callback):
        self.callback = callback
        self.running = True
        self.wake_word = "ulysses"
        self.recognizer = sr.Recognizer()

        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

        self.model_path = "wakeword/model"

        if not os.path.exists(self.model_path):
            self.running = False
            return

        self.vosk_model = Model(self.model_path)

    def listen_loop(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

            while self.running:
                try:
                    audio = self.recognizer.listen(
                        source, timeout=None, phrase_time_limit=2
                    )
                    raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)

                    rec = KaldiRecognizer(self.vosk_model, 16000)

                    if rec.AcceptWaveform(raw_data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").lower()
                    else:
                        partial = json.loads(rec.PartialResult())
                        text = partial.get("partial", "").lower()

                    if self.wake_word in text:
                        self.callback()
                        time.sleep(1)

                except Exception as e:
                    continue

    def start(self):
        if self.running:
            t = threading.Thread(target=self.listen_loop)
            t.daemon = True
            t.start()
