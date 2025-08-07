"""
Chat API View

Handles chat endpoint requests by delegating all business logic to TaskService.
Focused on HTTP request/response handling only.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...services import TaskService, AIService
from ...config.rules import ERROR_PHRASES
from ...config.settings import API_SETTINGS

logger = logging.getLogger(__name__)


class ChatView(APIView):
    """
    API view for handling chat requests.
    
    Validates request data and delegates all business logic to TaskService.
    Handles user-friendly vs technical error responses.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize services with dependency injection
        try:
            self.ai_service = AIService()
            self.task_service = TaskService(self.ai_service)
        except ValueError as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    def post(self, request):
        """
        Handle chat POST requests.
        
        Expected request data:
        - message: User's chat message
        - user: Username
        - mainController: Main controller (or defaults to user)
        - timezone: User timezone (optional, defaults to UTC)
        - debug: Debug mode flag (optional, defaults to False)
        """
        # Extract and validate request data
        user_message = request.data.get('message')
        user_name = request.data.get('user')
        main_controller = request.data.get('mainController') or request.data.get('user')
        user_timezone = request.data.get('timezone', API_SETTINGS['DEFAULT_TIMEZONE'])
        debug_mode = request.data.get('debug', False)
        
        # Validate required parameters
        validation_error = self._validate_required_fields(
            user_message, user_name, main_controller
        )
        if validation_error:
            return validation_error
        
        try:
            # Delegate business logic to TaskService
            response_data = self.task_service.create_task(
                user_message=user_message,
                user_name=user_name,
                main_controller=main_controller,
                user_timezone=user_timezone,
                debug_mode=debug_mode
            )
            return Response(response_data)
            
        except Exception as e:
            return self._handle_task_creation_error(e)
    
    def _validate_required_fields(self, user_message, user_name, main_controller):
        """Validate required request fields."""
        if not user_message:
            return Response(
                {'error': 'No message provided.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not user_name:
            return Response(
                {'error': 'No user provided.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not main_controller:
            return Response(
                {'error': 'No mainController provided.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        return None
    
    def _handle_task_creation_error(self, error):
        """Handle task creation errors with appropriate response type."""
        error_str = str(error)
        
        # Check if it's a user-friendly error message
        if any(phrase in error_str for phrase in ERROR_PHRASES):
            return Response({'reply': error_str})
        else:
            # Log technical errors and return generic message
            logger.error(f"Task creation error: {error_str}")
            return Response(
                {'error': f'Failed to create task: {error_str}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )