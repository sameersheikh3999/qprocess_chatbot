"""
API Package

This package contains the refactored API layer with modular views and configuration.
All views delegate business logic to services and handle only HTTP request/response.
"""

# Import all views for easy access
from .views.chat import ChatView
from .views.users import UserListView
from .views.admin import RunStoredProcedureView

__all__ = ['ChatView', 'UserListView', 'RunStoredProcedureView']