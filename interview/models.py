from django.db import models

class Candidate(models.Model):
    phone = models.CharField(max_length=20)
    conversation = models.JSONField(default=list, blank=True)
    questions_asked = models.IntegerField(default=0)

    final_score = models.IntegerField(default=0)
    decision = models.CharField(max_length=20, blank=True)
    red_flags = models.JSONField(default=list, blank=True)
    hr_summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
