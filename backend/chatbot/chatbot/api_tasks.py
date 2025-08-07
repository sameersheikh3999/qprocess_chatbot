from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Task, ChatUser
from .serializers import TaskSerializer
import re
from datetime import datetime, timedelta
import dateparser

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_name = self.request.query_params.get('user')
        if user_name:
            try:
                user = ChatUser.objects.get(name=user_name)
                return Task.objects.filter(user=user).order_by('-created_at')
            except ChatUser.DoesNotExist:
                return Task.objects.none()
        return Task.objects.all().order_by('-created_at')

    def extract_task_info(self, prompt):
        # Enhanced extraction logic with defaults and auto-generation
        # Extract title as first sentence or phrase before a period, or generate if missing
        title_match = re.match(r'^(.*?)(\.|$)', prompt)
        title = title_match.group(1).strip() if title_match and title_match.group(1).strip() else None
        if not title:
            # Generate a default title if none found
            title = "New Task"

        # Extract description as the rest of the prompt after the title or use full prompt if title is default
        description = prompt[len(title):].strip() if title != "New Task" else prompt.strip()

        # Extract due date/time using dateparser
        due_date = None
        due_time = None
        recurrence = ''
        priority = 'Medium'
        status = 'pending'
        alert = False
        soft_due = False
        confidential = False

        # Look for keywords for recurrence
        if re.search(r'\bdaily\b', prompt, re.IGNORECASE):
            recurrence = 'daily'
        elif re.search(r'\bweekly\b', prompt, re.IGNORECASE):
            recurrence = 'weekly'
        elif re.search(r'\bmonthly\b', prompt, re.IGNORECASE):
            recurrence = 'monthly'
        elif re.search(r'\bquarterly\b', prompt, re.IGNORECASE):
            recurrence = 'quarterly'
        elif re.search(r'\bannual\b', prompt, re.IGNORECASE):
            recurrence = 'annual'

        # Map time keywords to times
        time_map = {
            r'\bmorning\b': "10:00",
            r'\bafter close\b': "15:00",
            r'\bevening\b': "19:00"
        }
        for pattern, time_str in time_map.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                due_time = datetime.strptime(time_str, "%H:%M").time()
                break

        # If no time from keywords, parse date and time from prompt
        if not due_time:
            parsed_date = dateparser.parse(prompt, settings={'PREFER_DATES_FROM': 'future'})
            if parsed_date:
                due_date = parsed_date.date()
                due_time = parsed_date.time()

        # If still no due_time, default to 10:00 AM
        if not due_time:
            due_time = datetime.strptime("10:00", "%H:%M").time()

        # Extract priority
        if re.search(r'\bhigh priority\b', prompt, re.IGNORECASE):
            priority = 'High'
        elif re.search(r'\blow priority\b', prompt, re.IGNORECASE):
            priority = 'Low'

        # Extract status
        if re.search(r'\bcompleted\b', prompt, re.IGNORECASE):
            status = 'completed'
        elif re.search(r'\bpending\b', prompt, re.IGNORECASE):
            status = 'pending'

        # Extract alert
        if re.search(r'\balert\b', prompt, re.IGNORECASE):
            alert = True

        # Extract soft_due
        if re.search(r'\bsoft due\b', prompt, re.IGNORECASE):
            soft_due = True

        # Extract confidential
        if re.search(r'\[confidential\]', prompt, re.IGNORECASE):
            confidential = True

        return {
            'title': title,
            'description': description,
            'due_date': due_date,
            'due_time': due_time,
            'recurrence': recurrence,
            'priority': priority,
            'status': status,
            'alert': alert,
            'soft_due': soft_due,
            'confidential': confidential
        }

    def create(self, request, *args, **kwargs):
        user_name = request.data.get('user')
        prompt = request.data.get('prompt', '')

        if not prompt:
            return Response({'error': 'Prompt is required to create a task.'}, status=status.HTTP_400_BAD_REQUEST)

        task_info = self.extract_task_info(prompt)

        # Remove strict requirement for title, due_date, recurrence
        # Set defaults if missing
        if not task_info['title']:
            task_info['title'] = "New Task"
        if not task_info['due_date']:
            # Default due date to today
            task_info['due_date'] = datetime.now().date()
        if not task_info['recurrence']:
            task_info['recurrence'] = ''

        if user_name:
            user, _ = ChatUser.objects.get_or_create(name=user_name)
        else:
            user = None

        task_data = {
            'user': user.id if user else None,
            'title': task_info['title'],
            'description': task_info['description'],
            'due_date': task_info['due_date'],
            'due_time': task_info['due_time'],
            'recurrence': task_info['recurrence'],
            'priority': task_info.get('priority', 'Medium'),  # use extracted or default
            'status': task_info.get('status', 'pending'),
            'alert': task_info.get('alert', False),
            'soft_due': task_info.get('soft_due', False),
            'confidential': task_info.get('confidential', False)  # use extracted or default
        }

        serializer = self.get_serializer(data=task_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # Add chatbot follow-up message in response
        response_data = serializer.data
        response_data['message'] = "Task saved successfully. Can I help you with anything else or show saved tasks?"

        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
