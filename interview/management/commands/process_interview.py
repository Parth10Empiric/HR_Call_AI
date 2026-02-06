from django.core.management.base import BaseCommand
from interview.models import Candidate
from interview.services.speech_to_text import download_and_convert
from interview.services.ai_analysis import evaluate_full_interview
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        c = Candidate.objects.last()

        files = []
        if c.q1_audio_url:
            f = download_and_convert(c.q1_audio_url, "q1")
            c.intro_answer = "transcribed text"
            files.append(f)

        if c.q2_audio_url:
            f = download_and_convert(c.q2_audio_url, "q2")
            c.technical_answer = "transcribed text"
            files.append(f)

        if c.q3_audio_url:
            f = download_and_convert(c.q3_audio_url, "q3")
            c.problem_answer = "transcribed text"
            files.append(f)

        if c.q4_audio_url:
            f = download_and_convert(c.q4_audio_url, "q4")
            c.communication_answer = "transcribed text"
            files.append(f)

        c.final_score = evaluate_full_interview(c)
        c.save()

        for f in files:
            os.remove(f)

        print("Interview processed & temp files deleted.")
