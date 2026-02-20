import threading
import time

import speech_recognition as sr


class WakeWordListener:
    def __init__(self, callback):
        self.callback = callback
        self.running = True
        self.wake_word = "ulysses"
        self.recognizer = sr.Recognizer()

    def listen_loop(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

            while self.running:
                try:
                    audio = self.recognizer.listen(
                        source, timeout=3, phrase_time_limit=3
                    )
                    text = self.recognizer.recognize_google(
                        audio, language="en-US"
                    ).lower()

                    if self.wake_word in text:
                        self.callback()
                        time.sleep(1)

                except:
                    pass

    def start(self):
        t = threading.Thread(target=self.listen_loop)
        t.daemon = True
        t.start()
