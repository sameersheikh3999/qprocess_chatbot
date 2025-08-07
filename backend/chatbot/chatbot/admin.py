from django.contrib import admin
from .models import ChatUser, ChatHistory, Task

@admin.register(ChatUser)
class ChatUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_message', 'bot_reply', 'timestamp')
    list_filter = ('user',)
    search_fields = ('user_message', 'bot_reply')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'due_date', 'due_time', 'priority', 'status', 'confidential')
    list_filter = ('priority', 'status', 'confidential', 'user')
    search_fields = ('title', 'description')
