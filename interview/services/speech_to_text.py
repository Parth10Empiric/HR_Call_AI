# import subprocess

# WHISPER_BIN = "/home/empiric/whisper.cpp/build/bin/whisper-cli"
# MODEL_PATH = "/home/empiric/whisper.cpp/models/ggml-base.en.bin"

# def transcribe_audio(file_path):
#     cmd = [
#         WHISPER_BIN,
#         "-m", MODEL_PATH,
#         "-f", file_path,
#         "-nt"
#     ]

#     result = subprocess.run(
#         cmd,
#         capture_output=True,
#         text=True
#     )

#     return result.stdout.strip()

# import assemblyai as aai
# from config import settings
# # API key from environment
# aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

# def transcribe_audio(file_path):

#     try:
#         transcriber = aai.Transcriber()

#         transcript = transcriber.transcribe(
#             file_path,
#             config=aai.TranscriptionConfig(
#                 language_code="en",
#                 punctuate=True,
#                 format_text=True
#             )
#         )

#         if transcript.status == aai.TranscriptStatus.error:
#             print("❌ AssemblyAI error:", transcript.error)
#             return ""

#         return transcript.text.strip()

#     except Exception as e:
#         print("❌ AssemblyAI exception:", e)
#         return ""

from groq import Groq
from config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                language="en"
            )

        # ✅ Groq returns an object, not dict
        return transcription.text.strip() if transcription.text else ""

    except Exception as e:
        print("❌ Groq Whisper STT error:", e)
        return ""
