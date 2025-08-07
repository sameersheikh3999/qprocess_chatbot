from django.db import models
from django.contrib.auth.models import User

class ChatUser(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class ChatHistory(models.Model):
    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE)
    user_message = models.TextField()
    bot_reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} @ {self.timestamp:%Y-%m-%d %H:%M}"

class Task(models.Model):
    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_time = models.TimeField(null=True, blank=True)  # e.g., 10:00 for 'morning'
    due_date = models.DateField(null=True, blank=True)
    recurrence = models.CharField(max_length=50, blank=True)  # daily, weekly, monthly, etc.
    priority = models.CharField(max_length=20, blank=True)  # e.g., High, Medium, Low
    status = models.CharField(max_length=20, default='pending')  # e.g., pending, completed
    alert = models.BooleanField(default=False)
    soft_due = models.BooleanField(default=False)
    confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} for {self.user.name}"

class PendingTaskSession(models.Model):
    user = models.CharField(max_length=255)  # Username string
    parameters = models.JSONField(default=dict)  # Collected parameters so far
    last_prompt = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
