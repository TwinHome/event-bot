from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Transcript(models.Model):
    video_id = models.CharField(max_length=100, unique=True)
    original_file = models.FileField(upload_to='transcripts/original/')
  #  processed_file = models.FileField(upload_to='transcripts/processed/', null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    duration = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.video_id


class ChatHistory(models.Model):
    transcript = models.ForeignKey(Transcript, on_delete=models.CASCADE)
    user_message = models.TextField()
    bot_reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.transcript.video_id} at {self.timestamp}"
