from django.db import models

class TranslationLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    source_language = models.CharField(max_length=30)
    target_language = models.CharField(max_length=30)
    duration = models.DurationField(null=True, blank=True)  # Optional, to log the duration of the recording

    def __str__(self):
        return f"Translation from {self.source_language} to {self.target_language} on {self.created_at}"