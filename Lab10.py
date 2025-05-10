import json
import time
import os
import requests
import pyttsx3
import pyaudio
import vosk

# ====================
#   RUTAS A MODELOS
# ====================
MODEL_PATHS = {
    'ru': r'C:\Users\marki\Desktop\model\vosk-model-small-ru-0.22\vosk-model-small-ru-0.22',
    'en': r'C:\Users\marki\Desktop\model\vosk-model-small-en-us-0.15\vosk-model-small-en-us-0.15'
}


class Speech:
    def __init__(self, speaker_index=0):
        """Inicializa el motor de TTS y selecciona la voz."""
        self.tts = pyttsx3.init()
        self.voices = self.tts.getProperty('voices')
        
        # Verifica que el índice esté dentro de las voces disponibles
        if 0 <= speaker_index < len(self.voices):
            self.tts.setProperty('voice', self.voices[speaker_index].id)

    def set_voice(self, speaker_index=0):
        """Establece la voz según el índice del sistema."""
        if 0 <= speaker_index < len(self.voices):
            self.tts.setProperty('voice', self.voices[speaker_index].id)
        else:
            print("Índice de voz no válido.")

    def say(self, text: str):
        """Lee el texto por voz."""
        self.tts.say(text)
        self.tts.runAndWait()


class Recognizer:
    def __init__(self, initial_lang='ru'):
        """
        Carga ambos modelos y deja cargado el recognizer
        para el idioma inicial.
        """
        # Valida las rutas de los modelos
        for lang, path in MODEL_PATHS.items():
            if not os.path.isdir(path):
                raise FileNotFoundError(f"Carpeta de modelo Vosk no encontrada: {path}")
        
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=pyaudio.paInt16,
                                   channels=1,
                                   rate=16000,
                                   input=True,
                                   frames_per_buffer=8000)
        self.current_lang = None
        self.rec = None
        self.change_language(initial_lang)

    def change_language(self, lang_code: str):
        """Recarga el recognizer con otro modelo (ru o en)."""
        if lang_code == self.current_lang:
            return
        model = vosk.Model(MODEL_PATHS[lang_code])
        self.rec = vosk.KaldiRecognizer(model, 16000)
        self.current_lang = lang_code
        print(f">>> Recognizer cambiado a: {lang_code}")

    def listen(self):
        """Generador: cede cada frase reconocida en minúsculas."""
        while True:
            data = self.stream.read(4000, exception_on_overflow=False)
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                text = result.get('text', '').strip()
                if text:
                    yield text.lower()


# ====================
# FUNCIONES DE HECHOS Y FICHEROS
# ====================
def get_fact() -> str:
    """Obtiene un hecho aleatorio de NumbersAPI."""
    url = 'http://numbersapi.com/random/math'
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.text.strip()


def save_fact(fact: str, filename='facts.txt'):
    """Guarda el hecho en el archivo."""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(fact + '\n')


def delete_last_fact(filename='facts.txt'):
    """Borra el último hecho del archivo."""
    if not os.path.isfile(filename):
        print("No existe el archivo de hechos.")
        return
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if not lines:
        print("El archivo está vacío.")
        return
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines[:-1])


# ====================
# LÓGICA PRINCIPAL DEL ASISTENTE
# ====================
def main():
    speech = Speech(speaker_index=0)  # Voz en español por defecto
    recog = Recognizer(initial_lang='ru')  # Inicia en ruso
    current_fact = "Добро пожаловать! Скажите «fact» или «факт»."

    speech.say({
        'ru': "Ассистент запущен. Скажите «факт», чтобы получить факт, или «english/русский» для смены языка.",
        'en': "Assistant started. Say 'fact' to get a fact, or 'english/russian' to switch language."
    }[recog.current_lang])

    time.sleep(0.5)

    for phrase in recog.listen():
        print(f"[{recog.current_lang}] reconocido:", phrase)

        # Comandos para cambiar el idioma
        if phrase in ('english', 'английский'):
            recog.change_language('en')
            speech.set_voice(1)  # Cambiar a voz en inglés (índice 1 en la lista de voces)
            speech.say("Language switched to English.")
            continue
        if phrase in ('russian', 'русский'):
            recog.change_language('ru')
            speech.set_voice(0)  # Cambiar a voz en ruso (índice 0 en la lista de voces)
            speech.say("Язык переключен на русский.")
            continue

        try:
            # Comandos en inglés
            if recog.current_lang == 'en':
                if phrase == 'fact':
                    current_fact = get_fact()
                    speech.say("Here is your fact.")
                elif phrase == 'next':
                    current_fact = get_fact()
                    speech.say("Another one coming up.")
                elif phrase == 'read':
                    speech.say(current_fact)
                elif phrase == 'save':
                    save_fact(current_fact)
                    speech.say("Saved to file.")
                elif phrase == 'delete':
                    delete_last_fact()
                    speech.say("Last fact deleted.")
                elif phrase in ('exit', 'quit'):
                    speech.say("Goodbye!")
                    break
                else:
                    speech.say("Command not recognized. Try fact, read, save, delete or exit.")
            # Comandos en ruso
            else:
                if phrase in ('факт',):
                    current_fact = get_fact()
                    speech.say("Новый факт получен.")
                elif phrase in ('следующий',):
                    current_fact = get_fact()
                    speech.say("Еще один факт.")
                elif phrase in ('прочитать',):
                    speech.say(current_fact)
                elif phrase in ('записать',):
                    save_fact(current_fact)
                    speech.say("Факт сохранен.")
                elif phrase in ('удалить',):
                    delete_last_fact()
                    speech.say("Последний факт удален.")
                elif phrase in ('закрыть',):
                    speech.say("До свидания!")
                    break
                else:
                    speech.say("Команда не распознана. Скажите факт, прочитать, записать, удалить или закрыть.")
        except Exception as e:
            print("ERROR:", e)
            speech.say(str(e))

    recog.stream.stop_stream()
    recog.stream.close()


if __name__ == '__main__':
    main()

