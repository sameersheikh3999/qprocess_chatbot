"""
Admin API View

Handles administrative endpoint requests by delegating to DatabaseService.
Focused on HTTP request/response handling only.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class RunStoredProcedureView(APIView):
    """
    API view for executing stored procedures.
    
    Delegates all database operations to DatabaseService.
    """
    
    def post(self, request):
        """
        Execute a stored procedure with provided parameters.
        
        Expected request data:
        - param1: First parameter for stored procedure
        - param2: Second parameter for stored procedure
        - Additional parameters can be added as needed
        
        Returns:
            Response: JSON response containing procedure result
        """
        try:
            # Extract parameters from request
            param1 = request.data.get('param1')
            param2 = request.data.get('param2')
            # Add more params as needed
            
            # Delegate to DatabaseService
            result = DatabaseService.call_stored_procedure(
                'my_stored_procedure', 
                [param1, param2]
            )
            
            return Response({'result': result}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error executing stored procedure: {str(e)}")
            return Response(
                {'error': 'Failed to execute stored procedure'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )