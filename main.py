import os
import subprocess
import threading
import time
from queue import Queue

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

from stt.VoiceActivityDetection import VADDetector
from wakeword import WakeWordListener

master_prompt = "You are a helpful assistant designed to run offline with decent latency. Answer the following input from the user in no more than three sentences. Address them as Sir at all times. Only respond with the dialogue, nothing else"


class Client:
    def __init__(self):
        self.listening = False
        self.is_awake = False
        self.history = []
        self.last_interaction_time = time.time()
        self.timeout_limit = 60

        self.vad = VADDetector(lambda: None, self.onSpeechEnd, sensitivity=0.3)
        self.vad_data = Queue()
        self.stt = WhisperModel("small.en", device="cpu", compute_type="int8")
        self.last_suggested_app = None

        # Mac'e geçince '.exe'yi silersin
        self.piper_exe = os.path.join("piper", "piper.exe")
        self.piper_model = os.path.join("piper", "en_GB-alan-medium.onnx")
        self.tts_output_file = "response_audio.wav"

        self.lm_studio_url = "http://localhost:1234/v1/chat/completions"
        self.headers = {"Content-Type": "application/json"}

        print("System Ready.")

        self.startListening()
        t = threading.Thread(target=self.transcription_loop)
        t.daemon = True
        t.start()

        self.listener = WakeWordListener(callback=self.on_wake)
        self.listener.start()

    def on_wake(self):
        if not self.is_awake:
            print("Ulysses Ready!")
            self.is_awake = True
            self.last_interaction_time = time.time()

            if not self.listening:
                self.speak("Yes Sir?")

    def startListening(self):
        t = threading.Thread(target=self.vad.startListening)
        t.daemon = True
        t.start()

    def toggleListening(self):
        if not self.listening:
            print()
            print("\033[33mListening...\033[0m")
            self.last_interaction_time = time.time()

        while not self.vad_data.empty():
            self.vad_data.get()

        self.listening = not self.listening

    def onSpeechEnd(self, data):
        if data.any():
            self.vad_data.put(data)

    def addToHistory(self, content: str, role: str):
        if role == "user":
            print(f"\033[97m{content}\033[0m")
        else:
            print(f"\033[36m {content}\033[0m")

        if role == "user":
            content = f"""{master_prompt}\n\n{content}"""

        self.history.append({"role": role, "content": content})

    def check_system_commands(self, text):
        return False

    def transcription_loop(self):
        while True:
            if self.listening and (
                time.time() - self.last_interaction_time > self.timeout_limit
            ):
                print("\n\033[90m(Timeout - Going to Standby)\033[0m")
                self.toggleListening()
                continue

            if not self.vad_data.empty():
                data = self.vad_data.get()
                if self.listening and len(data) > 12000:
                    self.toggleListening()

                    if data.dtype == np.int16:
                        audio_float32 = data.astype(np.float32) / 32768.0
                    else:
                        audio_float32 = data

                    segments, _ = self.stt.transcribe(audio_float32, language="en")
                    text_output = "".join([s.text for s in segments]).strip()

                    if text_output:
                        self.addToHistory(text_output, "user")
                        self.last_interaction_time = time.time()

                        if self.check_system_commands(text_output):
                            self.last_interaction_time = time.time()
                            continue

                        payload = {
                            "messages": [
                                {"role": "system", "content": master_prompt},
                                *self.history,
                            ],
                            "temperature": 0.7,
                            "max_tokens": -1,
                            "stream": False,
                        }

                        try:
                            response = requests.post(
                                self.lm_studio_url, headers=self.headers, json=payload
                            )

                            if response.status_code == 200:
                                result = response.json()
                                answer = result["choices"][0]["message"]["content"]
                                self.addToHistory(answer, "assistant")
                                self.speak(answer)
                            else:
                                print(f"LM Studio Error: {response.status_code}")
                                self.toggleListening()

                        except Exception as e:
                            print(f"Connection Error: {e}")
                            self.toggleListening()
                    else:
                        self.toggleListening()
            else:
                time.sleep(0.1)

    def speak(self, text):
        try:
            if os.path.exists(self.tts_output_file):
                try:
                    os.remove(self.tts_output_file)
                except:
                    pass

            command = [
                self.piper_exe,
                "--model",
                self.piper_model,
                "--output_file",
                self.tts_output_file,
            ]

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
            )
            process.communicate(input=text.encode("utf-8"))

            if os.path.exists(self.tts_output_file):
                data, fs = sf.read(self.tts_output_file, dtype="float32")
                sd.play(data, fs)
                sd.wait()
            else:
                print("Error: Audio file not generated.")

        except Exception as e:
            print(f"TTS Error: {e}")

        self.toggleListening()


if __name__ == "__main__":
    jc = Client()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        os._exit(0)
