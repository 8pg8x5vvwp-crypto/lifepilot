import speech_recognition as sr

class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def listen(self) -> str:
        try:
            with sr.Microphone() as source:
                print("🎤 Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=20)

            result = self.recognizer.recognize_google(audio, language="en-US")
            print(f"[VOICE INPUT] {result}")
            return result

        except sr.WaitTimeoutError:
            print("[VOICE] No speech detected.")
        except sr.UnknownValueError:
            print("[VOICE] Could not understand audio.")
        except sr.RequestError:
            print("[VOICE] Speech service unavailable.")
        except Exception as e:
            print(f"[VOICE ERROR] {e}")

        return ""
