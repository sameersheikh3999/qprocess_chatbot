from dotenv import load_dotenv
load_dotenv()

from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
import requests
from .models import ChatHistory, Task, PendingTaskSession
from .serializers import TaskSerializer
import datetime
from dateutil.relativedelta import relativedelta
from .task_utils import apply_task_defaults, describe_recurrence, parse_recurrence_from_user_input

# Claude Opus API integration
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY environment variable is not set. Please set it in your .env file or environment.")
CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'

class ChatAPIView(APIView):
    def post(self, request):
        user_message = request.data.get('message')
        user_name = request.data.get('user')
        main_controller = request.data.get('mainController') or request.data.get('user')
        if not user_message:
            return Response({'error': 'No message provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_name:
            return Response({'error': 'No user provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not main_controller:
            return Response({'error': 'No mainController provided.'}, status=status.HTTP_400_BAD_REQUEST)
        # Fetch user FullName from SQL Server
        with connection.cursor() as cursor:
            cursor.execute("SELECT FullName FROM [QTasks].[dbo].[QCheck_Users] WHERE FullName=%s", [main_controller])
            row = cursor.fetchone()
            if not row:
                return Response({'error': f'User {main_controller} not found in QCheck_Users.'}, status=status.HTTP_400_BAD_REQUEST)
            user_fullname = row[0]
        # Use username as session key
        session, _ = PendingTaskSession.objects.get_or_create(user=user_name)
        # Get current parameters from session
        params = session.parameters.get('params', {})
        history = session.parameters.get('history', [])
        history.append({"role": "user", "content": user_message})
        system_prompt = (
            "You are a helpful assistant. When the user gives a prompt, extract as many of the following parameters as possible: "
            "TaskName, Controllers, Assignees, DueDate, LocalDueDate, Location, DueTime, SoftDueDate, FinalDueDate, Items, IsRecurring, FreqType, FreqRecurrance, FreqInterval, BusinessDayBehavior, Activate, IsReminder, ReminderDate, AddToPriorityList. "
            "If any are missing, ask for them one at a time, specifying the required type and an example. When you have all parameters, return a JSON object with all fields. Do not proceed until all are collected. The MainController is already provided."
        )
        llm_payload = {
            'model': 'claude-opus-4-20250514',
            'max_tokens': 1024,
            'system': system_prompt,
            'messages': history
        }
        headers = {
            'x-api-key': CLAUDE_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        llm_response = requests.post(CLAUDE_API_URL, headers=headers, json=llm_payload, timeout=30)
        llm_data = llm_response.json()
        import re
        import json as pyjson
        if llm_response.status_code != 200 or 'content' not in llm_data:
            return Response({'error': 'LLM error: ' + str(llm_data)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            content = llm_data['content'][0]['text'] if isinstance(llm_data['content'], list) else llm_data['content']
            match = re.search(r'\{[\s\S]*?\}', content)
            if match:
                llm_json = pyjson.loads(match.group(0))
                is_json_response = True
            else:
                llm_json = {}
                is_json_response = False
        except Exception as e:
            session.parameters['history'] = history
            session.save()
            return Response({'reply': 'Sorry, I could not understand the AI response. Please try again.'})
        if is_json_response:
            # Merge new parameters from LLM with those already stored
            params.update(llm_json)
            
            # Parse recurrence from user input if not already set
            if not params.get('IsRecurring') and user_message:
                recurrence_params = parse_recurrence_from_user_input(user_message)
                params.update(recurrence_params)
            
            # Apply business logic for defaults and presentation
            user_timezone = params.get('Location', 'UTC')
            params['user_input'] = user_message  # Pass user input for advanced field detection
            params, fields_to_prompt = apply_task_defaults(params, user_timezone=user_timezone)
            session.parameters['params'] = params
            session.parameters['history'] = history
            session.save()
            # Only prompt for fields that are not defaulted and should be shown
            missing = [f for f in fields_to_prompt if f not in params or params[f] in [None, '']]
            if missing:
                return Response({'reply': f"Missing parameters: {', '.join(missing)}. Please provide them."})
            # All parameters present, call stored procedure
            with connection.cursor() as cursor:
                cursor.execute("""
                    DECLARE @NewInstanceId INT;
                    EXEC [QTasks].[dbo].[QCheck_CreateTaskThroughChatbot]
                        @TaskName=%s,
                        @MainController=%s,
                        @Controllers=%s,
                        @Assignees=%s,
                        @DueDate=%s,
                        @LocalDueDate=%s,
                        @Location=%s,
                        @DueTime=%s,
                        @SoftDueDate=%s,
                        @FinalDueDate=%s,
                        @Items=%s,
                        @IsRecurring=%s,
                        @FreqType=%s,
                        @FreqRecurrance=%s,
                        @FreqInterval=%s,
                        @BusinessDayBehavior=%s,
                        @Activate=%s,
                        @IsReminder=%s,
                        @ReminderDate=%s,
                        @AddToPriorityList=%s,
                        @NewInstanceId=@NewInstanceId OUTPUT;
                    SELECT @NewInstanceId;
                """, [
                    params['TaskName'],
                    user_fullname,
                    params['Controllers'],
                    params['Assignees'],
                    params['DueDate'],
                    params['LocalDueDate'],
                    params['Location'],
                    params['DueTime'],
                    params['SoftDueDate'],
                    params['FinalDueDate'],
                    params['Items'],
                    int(params['IsRecurring']),
                    params['FreqType'],
                    params['FreqRecurrance'],
                    params['FreqInterval'],
                    params['BusinessDayBehavior'],
                    int(params['Activate']),
                    int(params['IsReminder']),
                    params['ReminderDate'],
                    int(params['AddToPriorityList']),
                ])
                new_instance_id = cursor.fetchone()[0]
            session.delete()
            # Add recurrence description if recurring
            recurrence_desc = None
            if params.get('IsRecurring') and params.get('FreqType'):
                recurrence_desc = describe_recurrence(params['FreqType'], params['FreqRecurrance'], params['FreqInterval'])
            reply_msg = f'Task created! NewInstanceId: {new_instance_id}'
            if recurrence_desc:
                reply_msg += f'\nRecurrence: {recurrence_desc}'
            return Response({'reply': reply_msg})
        else:
            session.parameters['history'] = history
            session.save()
            return Response({'reply': content})

class UserListView(APIView):
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT FullName FROM [QTasks].[dbo].[QCheck_Users]")
            users = [row[0] for row in cursor.fetchall()]
        return Response(users)

class RunStoredProcedureView(APIView):
    def post(self, request):
        param1 = request.data.get('param1')
        param2 = request.data.get('param2')
        # Add more params as needed
        with connection.cursor() as cursor:
            cursor.callproc('my_stored_procedure', [param1, param2])
            result = cursor.fetchall()  # Adjust as needed
        return Response({'result': result}, status=status.HTTP_200_OK)

def parse_natural_date(date_str):
    today = datetime.date.today()
    if not date_str:
        return None
    s = date_str.strip().lower()
    if s == 'today':
        return today.isoformat()
    if s == 'tomorrow':
        return (today + datetime.timedelta(days=1)).isoformat()
    if s == 'day after tomorrow':
        return (today + datetime.timedelta(days=2)).isoformat()
    if s == 'yesterday':
        return (today - datetime.timedelta(days=1)).isoformat()
    if s.startswith('next week'):
        return (today + datetime.timedelta(weeks=1)).isoformat()
    # Add more patterns as needed
    # If already in YYYY-MM-DD, return as is
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except Exception:
        return None

# New function to parse natural language time references

def parse_natural_time(time_str):
    if not time_str:
        return None
    s = time_str.strip().lower()
    if s == 'morning':
        return '10:00'
    if s == 'after close':
        return '15:00'
    if s == 'evening':
        return '19:00'
    # If already in HH:MM format, return as is
    try:
        datetime.datetime.strptime(time_str, '%H:%M')
        return time_str
    except Exception:
        return None
