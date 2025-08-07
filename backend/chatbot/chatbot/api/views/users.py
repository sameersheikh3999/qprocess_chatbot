"""
Users API View

Handles user-related endpoint requests by delegating to DatabaseService.
Focused on HTTP request/response handling only.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class UserListView(APIView):
    """
    API view for retrieving active users.
    
    Delegates all database operations to DatabaseService.
    """
    
    def get(self, request):
        """
        Retrieve list of active users.
        
        Returns:
            Response: JSON response containing list of active users
        """
        try:
            # Delegate to DatabaseService
            users = DatabaseService.get_active_users()
            return Response(users)
            
        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve users'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )