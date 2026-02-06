import os
import uuid
import requests

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render

from twilio.twiml.voice_response import VoiceResponse
from requests.auth import HTTPBasicAuth

from interview.models import Candidate
from interview.services.speech_to_text import transcribe_audio
from interview.services.ai_analysis import (
    generate_ai_turn,
    evaluate_full_interview_from_conversation
)
from interview.services.twilio_service import start_call
from config.settings import BASE_URL


MIN_QUESTIONS = 4


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def normalize_ai_turn(ai_turn):
    action = ai_turn.get("action")

    if action == "ask":
        action = "ask_question"

    return {
        "action": action or "ask_question",
        "intent": ai_turn.get("intent", "general"),
        "text": ai_turn.get("text", "Could you explain more?")
    }



def count_ai_questions(conversation):
    return sum(
        1 for turn in conversation
        if turn.get("role") == "ai"
        and turn.get("type") == "question"
    )


def is_warmup_reply(text: str) -> bool:
    if not text:
        return True
    return len(text.strip().split()) <= 3


def twilio_record(vr: VoiceResponse):
    vr.pause(length=1)
    vr.record(
        max_length=120,
        timeout=5,
        play_beep=True,
        action=f"{settings.BASE_URL}/voice/",
        method="POST"
    )

def safe_record(vr, prompt=None):
    if prompt:
        vr.say(prompt, voice="alice")

    vr.pause(length=1)

    vr.record(
        max_length=120,
        timeout=5,
        play_beep=True,
        action=f"{settings.BASE_URL}/voice/",
        method="POST"
    )
# --------------------------------------------------
# Main Voice Endpoint
# --------------------------------------------------

@csrf_exempt
def voice_interview(request):
    vr = VoiceResponse()
    phone = request.POST.get("From") or request.POST.get("To")

    candidate, _ = Candidate.objects.get_or_create(phone=phone)
    conversation = candidate.conversation or []

    # --------------------------------------------------
    # 1️⃣ AI INTRO (ONLY ONCE)
    # --------------------------------------------------
    if not conversation:
        intro_text = (
            "Hello, this is an automated interview call from the HR team. "
            "I will ask you a few questions to understand your experience and skills. "
            "Please answer clearly. Can You ready for that?"
        )

        conversation.append({
            "role": "ai",
            "type": "intro",
            "intent": "intro",
            "text": intro_text
        })
        candidate.conversation = conversation
        candidate.save(update_fields=["conversation"])

        vr.say(intro_text, voice="alice")
        twilio_record(vr)
        return HttpResponse(str(vr), content_type="text/xml")

    # --------------------------------------------------
    # 2️⃣ HANDLE CANDIDATE ANSWER
    # --------------------------------------------------
    if "RecordingUrl" in request.POST:
        recording_url = request.POST["RecordingUrl"] + ".wav"
        local_path = f"media/recordings/{candidate.id}_{uuid.uuid4().hex}.wav"

        audio = requests.get(
            recording_url,
            auth=HTTPBasicAuth(settings.TWILIO_SID, settings.TWILIO_AUTH)
        )

        with open(local_path, "wb") as f:
            f.write(audio.content)

        text = transcribe_audio(local_path)
        os.remove(local_path)

        # Ignore warm-up replies
        if not is_warmup_reply(text):
            conversation.append({
                "role": "candidate",
                "type": "answer",
                "text": text
            })
            candidate.conversation = conversation
            candidate.save(update_fields=["conversation"])

    # --------------------------------------------------
    # 3️⃣ AI DECISION (AFTER ANSWER)
    # --------------------------------------------------
    question_count = count_ai_questions(conversation)
    ai_turn = normalize_ai_turn(generate_ai_turn(conversation))

    # 🚫 Enforce minimum questions
    if question_count < MIN_QUESTIONS:
        ai_turn["action"] = "ask_question"

    # --------------------------------------------------
    # 4️⃣ END INTERVIEW (ONLY IF VALID)
    # --------------------------------------------------
    if ai_turn["action"] == "end_interview" and question_count >= MIN_QUESTIONS:
        vr.say(
            "Thank you for your time. We have enough information for now. "
            "Our HR team will contact you.",
            voice="alice"
        )
        vr.hangup()

        result = evaluate_full_interview_from_conversation(
            candidate.conversation
        )

        # ✅ SAVE EVERYTHING EXPLICITLY
        candidate.final_score = result.get("final_score", 0)
        candidate.decision = result.get("decision", "REJECT")
        candidate.red_flags = result.get("red_flags", [])
        candidate.hr_summary = result.get("hr_summary", "")
        candidate.questions_asked = count_ai_questions(candidate.conversation)

        candidate.save(
            update_fields=[
                "final_score",
                "decision",
                "red_flags",
                "hr_summary",
                "questions_asked",
            ]
        )

        return HttpResponse(str(vr), content_type="text/xml")


    # --------------------------------------------------
    # 5️⃣ ASK NEXT QUESTION
    # --------------------------------------------------
    conversation.append({
        "role": "ai",
        "type": "question",
        "intent": ai_turn["intent"],
        "text": ai_turn["text"]
    })
    candidate.conversation = conversation
    candidate.save(update_fields=["conversation"])

    vr.say(ai_turn["text"], voice="alice")
    twilio_record(vr)
    return HttpResponse(str(vr), content_type="text/xml")


# --------------------------------------------------
# Call UI
# --------------------------------------------------

def call_ui(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        if phone:
            start_call(phone)
            return render(
                request,
                "interview/call_ui.html",
                {"message": "Call initiated successfully"}
            )

    return render(request, "interview/call_ui.html")
