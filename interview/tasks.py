# interview/tasks.py
from celery import shared_task
from interview.services.ai_analysis import generate_ai_turn
from interview.services.TTS_genrater import murf_tts
from interview.services.speech_to_text import transcribe_audio
from interview.models import Candidate
from config.settings import BASE_URL, MEDIA_URL
import os

@shared_task
def process_candidate_answer(candidate_id):
    candidate = Candidate.objects.get(id=candidate_id)
    conversation = candidate.conversation

    # 1️⃣ Transcribe last answer
    last = conversation[-1]
    text = transcribe_audio(last["audio_path"])
    os.remove(last["audio_path"])

    last["text"] = text
    candidate.save(update_fields=["conversation"])

    # 2️⃣ Ask LLM
    ai_turn = generate_ai_turn(conversation)

    # 3️⃣ End decision
    if ai_turn.get("action") == "end_interview":
        candidate.pending_ai_audio = f"{BASE_URL}/static/audio/end.mp3"
        candidate.save(update_fields=["pending_ai_audio"])
        return

    # 4️⃣ Generate Murf TTS
    audio_file = murf_tts(ai_turn["text"])

    conversation.append({
        "role": "ai",
        "type": "question",
        "intent": ai_turn.get("intent", "general"),
        "text": ai_turn["text"]
    })

    candidate.conversation = conversation
    candidate.pending_ai_audio = f"{BASE_URL}{MEDIA_URL}tts/{audio_file}"
    candidate.questions_asked += 1

    candidate.save(update_fields=[
        "conversation",
        "pending_ai_audio",
        "questions_asked"
    ])

