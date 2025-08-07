from dotenv import load_dotenv
load_dotenv()

# from django.db import connection  # Now handled by DatabaseService
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
import requests
from .models import ChatHistory, Task, PendingTaskSession
from .serializers import TaskSerializer
from .services import DateTimeService, AIService, TaskService
from .services.database_service import DatabaseService
import datetime
from dateutil.relativedelta import relativedelta
import pytz
import time
import logging
import re
import json as pyjson

# Import the new schedule parser
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schedule_parser import ScheduleParser

logger = logging.getLogger(__name__)

# Initialize services
try:
    ai_service = AIService()
    task_service = TaskService(ai_service)
except ValueError as e:
    logger.error(f"Failed to initialize services: {e}")
    raise


# escape_sql_string function moved to DatabaseService



# set_automatic_parameters function moved to TaskService




class ChatAPIView(APIView):
    def post(self, request):
        user_message = request.data.get('message')
        user_name = request.data.get('user')
        main_controller = request.data.get('mainController') or request.data.get('user')
        user_timezone = request.data.get('timezone', 'UTC')  # Get timezone from frontend, default to UTC
        debug_mode = request.data.get('debug', False)  # Enable debug mode for testing
        
        # Validate required parameters
        if not user_message:
            return Response({'error': 'No message provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_name:
            return Response({'error': 'No user provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not main_controller:
            return Response({'error': 'No mainController provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Use TaskService to handle all task creation orchestration
            response_data = task_service.create_task(
                user_message=user_message,
                user_name=user_name,
                main_controller=main_controller,
                user_timezone=user_timezone,
                debug_mode=debug_mode
            )
            return Response(response_data)
            
        except Exception as e:
            # Handle TaskCreationError and other exceptions
            error_str = str(e)
            
            # Check if it's a user-friendly error message (contains suggestions or explanations)
            if any(phrase in error_str for phrase in ['Did you mean', 'Please try', 'Who should be assigned', 'What would you like']):
                return Response({'reply': error_str})
            else:
                # Log technical errors and return generic message
                logger.error(f"Task creation error: {error_str}")
                return Response({
                    'error': f'Failed to create task: {error_str}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserListView(APIView):
    def get(self, request):
        users = DatabaseService.get_active_users()
        return Response(users)

class RunStoredProcedureView(APIView):
    def post(self, request):
        param1 = request.data.get('param1')
        param2 = request.data.get('param2')
        # Add more params as needed
        result = DatabaseService.call_stored_procedure('my_stored_procedure', [param1, param2])
        return Response({'result': result}, status=status.HTTP_200_OK)



def add_to_priority_list_workaround(instance_id, assignees_str):
    """UC03 Workaround: Manually add priority list entries - Deprecated, use DatabaseService"""
    logger.warning("add_to_priority_list_workaround called - this function is deprecated, use DatabaseService.add_to_priority_list_workaround")
    return DatabaseService.add_to_priority_list_workaround(instance_id, assignees_str)
