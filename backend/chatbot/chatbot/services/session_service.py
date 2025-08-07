"""
Session Service Module

This module provides centralized session management for the chatbot application,
handling PendingTaskSession creation, parameter persistence, history tracking,
and session lifecycle management.
"""

import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone

from ..models import PendingTaskSession

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service class for handling session management operations.
    Manages PendingTaskSession instances for task creation workflows.
    """
    
    @staticmethod
    def get_or_create_session(user_name: str) -> PendingTaskSession:
        """
        Get an existing session or create a new one for the user.
        
        Args:
            user_name: Username for session identification
            
        Returns:
            PendingTaskSession instance
        """
        session, created = PendingTaskSession.objects.get_or_create(user=user_name)
        
        if created:
            logger.info(f"Created new session for user: {user_name}")
        else:
            logger.debug(f"Retrieved existing session for user: {user_name}")
            
        return session
    
    @staticmethod
    def manage_task_session(user_name: str, user_message: str) -> PendingTaskSession:
        """
        Manage the task session for parameter persistence with intelligent session handling.
        
        This method implements smart session management:
        - Creates or retrieves a session for the user
        - Clears session parameters for new task creation requests
        - Preserves session for continuation messages
        
        Args:
            user_name: Username for session key
            user_message: User's message to determine if new session needed
            
        Returns:
            PendingTaskSession instance
        """
        # Get or create session
        session = SessionService.get_or_create_session(user_name)
        
        # CRITICAL: Clear session parameters for each new task creation request
        # This prevents old task names from being cached and causing duplicate errors
        if user_message and not SessionService._is_continuation_message(user_message):
            # This is a new task creation request, not a continuation
            session.parameters = {'params': {}, 'history': []}
            session.save()
            logger.info(f"Cleared session for new task creation request from {user_name}")
        
        return session
    
    @staticmethod
    def _is_continuation_message(user_message: str) -> bool:
        """
        Determine if a user message is a continuation of an existing conversation.
        
        Args:
            user_message: The user's message
            
        Returns:
            True if this appears to be a continuation, False for new task creation
        """
        continuation_keywords = ['more', 'continue', 'what else', 'anything else', 'also', 'and']
        return any(keyword in user_message.lower() for keyword in continuation_keywords)
    
    @staticmethod
    def get_session_parameters(session: PendingTaskSession) -> Dict[str, Any]:
        """
        Get parameters from a session with safe defaults.
        
        Args:
            session: PendingTaskSession instance
            
        Returns:
            Dictionary containing session parameters
        """
        return session.parameters.get('params', {})
    
    @staticmethod
    def get_session_history(session: PendingTaskSession) -> List[Dict[str, str]]:
        """
        Get conversation history from a session with safe defaults.
        
        Args:
            session: PendingTaskSession instance
            
        Returns:
            List of conversation history entries
        """
        return session.parameters.get('history', [])
    
    @staticmethod
    def add_to_session_history(session: PendingTaskSession, role: str, content: str) -> None:
        """
        Add a message to the session conversation history.
        
        Args:
            session: PendingTaskSession instance
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        if 'history' not in session.parameters:
            session.parameters['history'] = []
        
        session.parameters['history'].append({"role": role, "content": content})
        logger.debug(f"Added {role} message to session history for user: {session.user}")
    
    @staticmethod
    def update_session_parameters(session: PendingTaskSession, new_params: Dict[str, Any]) -> None:
        """
        Update session parameters with new data.
        
        Args:
            session: PendingTaskSession instance
            new_params: New parameters to merge with existing ones
        """
        if 'params' not in session.parameters:
            session.parameters['params'] = {}
        
        session.parameters['params'].update(new_params)
        logger.debug(f"Updated session parameters for user: {session.user}")
    
    @staticmethod
    def save_session(session: PendingTaskSession) -> None:
        """
        Save session changes to the database.
        
        Args:
            session: PendingTaskSession instance to save
        """
        session.save()
        logger.debug(f"Saved session for user: {session.user}")
    
    @staticmethod
    def clear_session(session: PendingTaskSession) -> None:
        """
        Clear all session data and reset to defaults.
        
        Args:
            session: PendingTaskSession instance to clear
        """
        session.parameters = {'params': {}, 'history': []}
        session.save()
        logger.info(f"Cleared session data for user: {session.user}")
    
    @staticmethod
    def delete_session(session: PendingTaskSession) -> None:
        """
        Delete a session from the database.
        
        Args:
            session: PendingTaskSession instance to delete
        """
        user_name = session.user
        session.delete()
        logger.info(f"Deleted session for user: {user_name}")
    
    @staticmethod
    def handle_session_error(session: PendingTaskSession, error_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle session state during error conditions.
        
        Args:
            session: PendingTaskSession instance
            error_context: Optional context data to preserve during error
        """
        try:
            # Preserve history if available in error context
            if error_context and 'history' in error_context:
                session.parameters['history'] = error_context['history']
            elif 'history' not in session.parameters:
                session.parameters['history'] = []
            
            session.save()
            logger.debug(f"Handled session error state for user: {session.user}")
        except Exception as e:
            logger.error(f"Failed to handle session error state for user {session.user}: {e}")
    
    @staticmethod
    def get_session_summary(session: PendingTaskSession) -> Dict[str, Any]:
        """
        Get a summary of the session state for debugging and monitoring.
        
        Args:
            session: PendingTaskSession instance
            
        Returns:
            Dictionary containing session summary information
        """
        return {
            'user': session.user,
            'created_at': session.created_at,
            'updated_at': session.updated_at,
            'params_count': len(session.parameters.get('params', {})),
            'history_count': len(session.parameters.get('history', [])),
            'has_last_prompt': bool(session.last_prompt),
        }
    
    @staticmethod
    def cleanup_old_sessions(days_old: int = 7) -> int:
        """
        Clean up old sessions to prevent database bloat.
        
        Args:
            days_old: Number of days old a session must be to be considered for cleanup
            
        Returns:
            Number of sessions deleted
        """
        from django.utils import timezone
        import datetime
        
        cutoff_date = timezone.now() - datetime.timedelta(days=days_old)
        old_sessions = PendingTaskSession.objects.filter(updated_at__lt=cutoff_date)
        count = old_sessions.count()
        old_sessions.delete()
        
        logger.info(f"Cleaned up {count} old sessions (older than {days_old} days)")
        return count