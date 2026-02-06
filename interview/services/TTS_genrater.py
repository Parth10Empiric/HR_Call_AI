# import requests

# url = "https://global.api.murf.ai/v1/speech/stream"
# headers = {
#     "api-key": "ap2_e69e75d1-682e-4a7d-b937-dd0eae7cd475", # that is my murfAPI key
#     "Content-Type": "application/json"
# }

# #  ------------------------ SAMAR'S VOICE -----------------------
# data = {
#    "voice_id": "en-IN-samar",
#    "style": "Conversational",
#    "text": "Whenever you are done, press one and we will go to the next question. ",
#    "multi_native_locale": "en-IN",
#    "model": "FALCON",
#    "format": "MP3",
#    "sampleRate": 24000,
#    "channelType": "MONO"
# }

# #  ---------------- ANUSHA'S VOICE ------------------------
# # data = {
# #    "voice_id": "en-IN-anusha",
# #    "style": "Conversational",
# #    "text": "Hello, this is the HR team calling. Thank you for taking the time to speak with us today. This interview will take only a few minutes. Lets begin.",
# #    "multi_native_locale": "en-IN",
# #    "model": "FALCON",
# #    "format": "MP3",
# #    "sampleRate": 24000,
# #    "channelType": "MONO"
# # }

# response = requests.post(url, headers=headers, json=data, stream=True)

# if response.status_code == 200:
#     with open("presskey1.mp3", "wb") as f:
#         for chunk in response.iter_content(chunk_size=1024):
#             if chunk:
#                 f.write(chunk)
#                 print(f"Received {len(chunk)} bytes")
#     print("Audio streaming completed")
# else:
#     print(f"Error: {response}")


# interview/services/TTS_generator.py


# interview/services/TTS_genrater.py
import os, hashlib, requests

MURF_URL = "https://global.api.murf.ai/v1/speech/stream"
MURF_API_KEY = os.getenv("MURF_API_KEY")

HEADERS = {
    "api-key": MURF_API_KEY,
    "Content-Type": "application/json"
}

def murf_tts(text: str) -> str:
    text = text.strip()
    if not text:
        raise ValueError("Empty text passed to TTS")

    # cache audio
    h = hashlib.md5(text.encode()).hexdigest()
    out_path = f"media/tts/{h}.mp3"
    os.makedirs("media/tts", exist_ok=True)

    if os.path.exists(out_path):
        return out_path

    payload = {
        "voice_id": "en-IN-samar",
        "text": text,
        "format": "MP3"
    }

    r = requests.post(
        MURF_URL,
        headers=HEADERS,
        json=payload,
        stream=True,
        timeout=20
    )

    if r.status_code != 200:
        print("❌ Murf error:", r.status_code, r.text)
        raise RuntimeError("Murf TTS failed")

    with open(out_path, "wb") as f:
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)

    return out_path
