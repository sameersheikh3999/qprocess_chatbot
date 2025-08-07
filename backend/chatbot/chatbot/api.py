"""
API Router Module

This module serves as a simple router that imports and exposes views from the 
modular API structure. All business logic has been moved to services, and 
views are focused on HTTP request/response handling only.

Legacy Note: This file previously contained all API logic. The original 
implementation has been backed up to api_original.py for reference.
"""

from dotenv import load_dotenv
load_dotenv()

# Import the new modular API views
from .api.views.chat import ChatView
from .api.views.users import UserListView  
from .api.views.admin import RunStoredProcedureView

# Maintain backward compatibility with existing class names
# These aliases ensure existing URL configurations continue to work
ChatAPIView = ChatView
UserListView = UserListView
RunStoredProcedureView = RunStoredProcedureView

# Legacy function for backward compatibility
# This function is deprecated - use DatabaseService.add_to_priority_list_workaround instead
def add_to_priority_list_workaround(instance_id, assignees_str):
    """
    UC03 Workaround: Manually add priority list entries - Deprecated
    
    This function is maintained for backward compatibility only.
    Use DatabaseService.add_to_priority_list_workaround instead.
    
    Args:
        instance_id: Task instance ID
        assignees_str: Comma-separated assignees string
        
    Returns:
        Result from DatabaseService.add_to_priority_list_workaround
    """
    import logging
    from .services.database_service import DatabaseService
    
    logger = logging.getLogger(__name__)
    logger.warning(
        "add_to_priority_list_workaround called - this function is deprecated, "
        "use DatabaseService.add_to_priority_list_workaround"
    )
    return DatabaseService.add_to_priority_list_workaround(instance_id, assignees_str)

# Export all views for external use
__all__ = [
    'ChatView', 
    'ChatAPIView',  # Backward compatibility alias
    'UserListView', 
    'RunStoredProcedureView',
    'add_to_priority_list_workaround'  # Legacy function
]