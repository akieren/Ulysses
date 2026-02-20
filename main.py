import os
import subprocess
import threading
import time
from queue import Queue

import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

import llm
from memory import memory_manager
from memory.temporary_memory import TemporaryMemory
from skills import app_control, weather_report, web_search
from stt.VoiceActivityDetection import VADDetector
from wakeword.wakeword import WakeWordListener


class Client:
    def __init__(self):
        self.listening = False
        self.is_awake = False
        self.last_interaction_time = time.time()
        self.timeout_limit = 60

        self.temp_memory = TemporaryMemory()
        self.long_term_memory = memory_manager.load_memory()

        self.vad = VADDetector(lambda: None, self.onSpeechEnd, sensitivity=0.3)
        self.vad_data = Queue()
        self.stt = WhisperModel("small.en", device="cpu", compute_type="int8")

        self.piper_exe = os.path.join("tts", "piper.exe")
        self.piper_model = os.path.join("tts", "en_GB-alan-medium.onnx")
        self.tts_output_file = "response_audio.wav"

        print("System Ready. Awareness initialized.")

        self.startListening()
        t = threading.Thread(target=self.transcription_loop)
        t.daemon = True
        t.start()

        self.listener = WakeWordListener(callback=self.on_wake)
        self.listener.start()

    def on_wake(self):
        if not self.is_awake:
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
            print("\n\033[33mListening...\033[0m")
            self.last_interaction_time = time.time()

        while not self.vad_data.empty():
            self.vad_data.get()

        self.listening = not self.listening

    def onSpeechEnd(self, data):
        if data.any():
            self.vad_data.put(data)

    def addToHistory(self, content: str, role: str):
        if role == "user":
            print(f"\033[97mYou: {content}\033[0m")
        else:
            print(f"\033[36mUlysses: {content}\033[0m")

        self.temp_memory.add_to_history(role, content)

    def check_system_commands(self, text):
        return False

    def transcription_loop(self):
        while True:
            if self.listening and (
                time.time() - self.last_interaction_time > self.timeout_limit
            ):
                print("\n\033[90m(Timeout - Going to Standby)\033[0m")
                self.is_awake = False
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

                        print("\033[35m[SYSTEM] Thinking...\033[0m")

                        if self.check_system_commands(text_output):
                            continue

                        try:
                            current_memory = memory_manager.load_memory()
                            history_str = self.temp_memory.get_history_for_prompt()

                            if (
                                hasattr(self.temp_memory, "pending_intent")
                                and self.temp_memory.pending_intent
                            ):
                                history_str += f"\n[CRITICAL SYSTEM NOTE: We are currently executing the '{self.temp_memory.pending_intent}' intent. The user is answering to provide the missing parameter. You MUST output the '{self.temp_memory.pending_intent}' intent and extract the parameter from the user's message.]"

                            result = llm.get_llm_output(
                                user_text=text_output,
                                memory_block=current_memory,
                                history=history_str,
                            )

                            if not result:
                                result = {
                                    "intent": "chat",
                                    "text": "Sir, I encountered a cognitive error.",
                                }

                            intent = result.get("intent")
                            parameters = result.get("parameters", {})
                            answer = result.get(
                                "text", "Sir, I couldn't generate a response."
                            )
                            memory_update = result.get("memory_update")

                            if memory_update:
                                memory_manager.update_memory(memory_update)
                                self.long_term_memory = memory_manager.load_memory()

                            self.addToHistory(answer, "assistant")

                            if intent == "open_app":
                                threading.Thread(
                                    target=app_control.open_app,
                                    args=(parameters, answer, self),
                                    daemon=True,
                                ).start()
                            elif intent == "search":
                                threading.Thread(
                                    target=web_search.perform_search,
                                    args=(parameters, answer, self),
                                    daemon=True,
                                ).start()
                            elif intent == "weather_report":
                                threading.Thread(
                                    target=weather_report.get_weather,
                                    args=(parameters, answer, self),
                                    daemon=True,
                                ).start()
                            else:
                                self.speak(answer)

                        except Exception as e:
                            print(
                                f"\033[31m[ERROR] Brain Connection or Execution Error: {e}\033[0m"
                            )
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

            if self.is_awake:
                self.listening = True
                self.last_interaction_time = time.time()
                print("\n\033[33mListening...\033[0m")

        except Exception as e:
            print(f"TTS Error: {e}")

        if self.is_awake and not self.listening:
            self.toggleListening()


if __name__ == "__main__":
    jc = Client()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        os._exit(0)
