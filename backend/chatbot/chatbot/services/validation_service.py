"""
Validation Service Module

This module provides centralized validation logic for the chatbot application,
consolidating parameter validation, input validation, and business rule validation.
"""

import datetime
import re
import logging
from typing import Dict, Any, List, Tuple, Optional

from .database_service import DatabaseService
from .error_handler import ValidationError

logger = logging.getLogger(__name__)


# ValidationError is now imported from error_handler


class ValidationService:
    """
    Service class for handling all validation logic across the application.
    Provides parameter validation, input validation, and business rule validation.
    """
    
    # Configuration constants
    MAX_MESSAGE_LENGTH = 5000
    MIN_TASK_NAME_LENGTH = 3
    MAX_TASK_NAME_LENGTH = 200
    MAX_ASSIGNEES_COUNT = 10
    
    @staticmethod
    def validate_required_fields(params: Dict[str, Any]) -> None:
        """
        Validate that all required fields are present and properly formatted.
        
        Args:
            params: Dictionary of task parameters
            
        Raises:
            ValidationError: If required fields are missing or invalid
        """
        base_required = ['TaskName', 'Assignees']
        
        # Only check recurring fields if it's a recurring task
        if params.get('IsRecurring', 0) == 1:
            recurring_required = ['FreqType', 'FreqRecurrance', 'FreqInterval', 'BusinessDayBehavior']
            required_fields = base_required + recurring_required
        else:
            required_fields = base_required
        
        missing = [f for f in required_fields if f not in params or params[f] in [None, '']]
        if missing:
            if 'TaskName' in missing:
                raise ValidationError("I need to know what task to create. What would you like to name this task?", 'MISSING_TASK_NAME')
            elif 'Assignees' in missing:
                raise ValidationError("Who should be assigned to this task? Please provide one or more names (comma-separated if multiple).", 'MISSING_ASSIGNEES')
            else:
                raise ValidationError(f"I need a bit more information for the recurring schedule: {', '.join(missing)}")
    
    @staticmethod
    def validate_message_length(message: str) -> None:
        """
        Validate that the user message is within acceptable length limits.
        
        Args:
            message: User input message
            
        Raises:
            ValidationError: If message is too long or empty
        """
        if not message or not message.strip():
            raise ValidationError("Please provide a message describing the task you'd like to create.", 'EMPTY_MESSAGE')
        
        if len(message) > ValidationService.MAX_MESSAGE_LENGTH:
            raise ValidationError(
                f"Your message is too long ({len(message)} characters). "
                f"Please keep it under {ValidationService.MAX_MESSAGE_LENGTH} characters."
            )
    
    @staticmethod
    def validate_task_name(task_name: str) -> None:
        """
        Validate task name requirements.
        
        Args:
            task_name: The task name to validate
            
        Raises:
            ValidationError: If task name doesn't meet requirements
        """
        if not task_name or not task_name.strip():
            raise ValidationError("Task name cannot be empty.", 'EMPTY_TASK_NAME')
        
        task_name = task_name.strip()
        
        if len(task_name) < ValidationService.MIN_TASK_NAME_LENGTH:
            raise ValidationError(
                f"Task name is too short. Please provide at least {ValidationService.MIN_TASK_NAME_LENGTH} characters."
            )
        
        if len(task_name) > ValidationService.MAX_TASK_NAME_LENGTH:
            raise ValidationError(
                f"Task name is too long ({len(task_name)} characters). "
                f"Please keep it under {ValidationService.MAX_TASK_NAME_LENGTH} characters."
            )
        
        # Check for invalid characters that might cause database issues
        invalid_chars = ['<', '>', '"', "'", '\\', '|', '\x00']
        found_invalid = [char for char in invalid_chars if char in task_name]
        if found_invalid:
            raise ValidationError(
                f"Task name contains invalid characters: {', '.join(found_invalid)}. "
                f"Please remove these characters and try again."
            )
    
    @staticmethod
    def validate_assignees(assignees: str) -> List[str]:
        """
        Validate and parse assignees list.
        
        Args:
            assignees: Comma-separated string of assignee names
            
        Returns:
            List of validated assignee names
            
        Raises:
            ValidationError: If assignees are invalid
        """
        if not assignees or not assignees.strip():
            raise ValidationError("At least one assignee must be specified.")
        
        # Split and clean assignee names
        assignee_list = [name.strip() for name in assignees.split(',') if name.strip()]
        
        if not assignee_list:
            raise ValidationError("Please provide valid assignee names.")
        
        if len(assignee_list) > ValidationService.MAX_ASSIGNEES_COUNT:
            raise ValidationError(
                f"Too many assignees ({len(assignee_list)}). "
                f"Maximum allowed is {ValidationService.MAX_ASSIGNEES_COUNT}."
            )
        
        # Validate each assignee name
        for assignee in assignee_list:
            if len(assignee) < 2:
                raise ValidationError(f"Assignee name '{assignee}' is too short.")
            if len(assignee) > 100:
                raise ValidationError(f"Assignee name '{assignee}' is too long.")
            
            # Check for valid name format (allow letters, spaces, periods, hyphens)
            if not re.match(r'^[a-zA-Z\s\.\-]+$', assignee):
                raise ValidationError(
                    f"Assignee name '{assignee}' contains invalid characters. "
                    f"Please use only letters, spaces, periods, and hyphens."
                )
        
        return assignee_list
    
    @staticmethod
    def validate_group(group_name: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate if a group exists and provide suggestions if not found.
        
        Args:
            group_name: Name of the group to validate
            
        Returns:
            Tuple of (exists, found_name, similar_groups)
            
        Raises:
            ValidationError: If group validation fails with specific error
        """
        if not group_name or not group_name.strip():
            raise ValidationError("Group name cannot be empty.")
        
        try:
            # NEW LOGIC: If this is an active user, let the backend stored procedure handle everything
            if ValidationService.is_active_user(group_name):
                logger.info(f"Active user '{group_name}' - bypassing frontend validation, letting backend handle resolution")
                return True, group_name, []
            
            # LEGACY LOGIC: Use existing database service validation for non-users
            group_exists, user_fullname, similar_groups = DatabaseService.validate_group_exists(group_name)
            
            if not group_exists:
                # Check if this is a user who isn't properly configured
                if ValidationService.is_unconfigured_user(group_name):
                    raise ValidationError(
                        f'"{group_name}" is not configured for task creation. '
                        f'This user needs to be set up as a group by an administrator. '
                        f'Please contact your system admin or select a different user from the dropdown.'
                    )
                elif similar_groups:
                    suggestions = ", ".join(similar_groups[:3])
                    raise ValidationError(
                        f'"{group_name}" is not a valid group. Did you mean one of these: {suggestions}?'
                    )
                else:
                    raise ValidationError(
                        f'"{group_name}" is not found in the system. Please use a valid group name.'
                    )
            
            return group_exists, user_fullname, similar_groups
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating group '{group_name}': {e}")
            raise ValidationError(f"Unable to validate group '{group_name}'. Please try again.")
    
    @staticmethod
    def is_unconfigured_user(name: str) -> bool:
        """
        Check if a name belongs to a user who exists but isn't configured for task creation.
        
        Args:
            name: The name to check
            
        Returns:
            True if user exists but isn't configured, False otherwise
        """
        try:
            # Get all active users (including unconfigured ones)
            all_users = DatabaseService.get_all_active_users()
            
            # Get properly configured users
            configured_users = DatabaseService.get_active_users()
            
            # Check if user exists but isn't configured
            return name in all_users and name not in configured_users
            
        except Exception as e:
            logger.error(f"Error checking user configuration for '{name}': {e}")
            return False
    
    @staticmethod
    def is_active_user(name: str) -> bool:
        """
        Check if a name belongs to an active user in the system.
        This allows the backend stored procedure to handle user resolution.
        
        Args:
            name: The name to check
            
        Returns:
            True if user is active, False otherwise
        """
        try:
            # Get all active users from the system
            all_users = DatabaseService.get_all_active_users()
            return name in all_users
            
        except Exception as e:
            logger.error(f"Error checking if user '{name}' is active: {e}")
            return False
    
    @staticmethod
    def validate_date_time(date_str: str = None, time_str: str = None) -> None:
        """
        Validate date and time parameters.
        
        Args:
            date_str: Date string to validate (optional)
            time_str: Time string to validate (optional)
            
        Raises:
            ValidationError: If date or time format is invalid
        """
        if date_str is not None:
            ValidationService._validate_date_format(date_str)
        
        if time_str is not None:
            ValidationService._validate_time_format(time_str)
    
    @staticmethod
    def _validate_date_format(date_str: str) -> None:
        """
        Validate date format and ensure it's not in the past.
        
        Args:
            date_str: Date string in various formats
            
        Raises:
            ValidationError: If date format is invalid or date is in the past
        """
        if not date_str or not date_str.strip():
            return
        
        try:
            # Try to parse the date string in common formats
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y']
            parsed_date = None
            
            for date_format in date_formats:
                try:
                    parsed_date = datetime.datetime.strptime(date_str.strip(), date_format).date()
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                raise ValidationError(
                    f"Invalid date format: '{date_str}'. "
                    f"Please use formats like YYYY-MM-DD, MM/DD/YYYY, or MM-DD-YYYY."
                )
            
            # Check if date is in the past (allow today)
            today = datetime.date.today()
            if parsed_date < today:
                raise ValidationError(
                    f"Due date '{date_str}' is in the past. "
                    f"Please provide a date that is today or in the future."
                )
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating date '{date_str}': {e}")
            raise ValidationError(f"Unable to validate date '{date_str}'. Please check the format.")
    
    @staticmethod
    def _validate_time_format(time_str: str) -> None:
        """
        Validate time format.
        
        Args:
            time_str: Time string in HH:MM format
            
        Raises:
            ValidationError: If time format is invalid
        """
        if not time_str or not time_str.strip():
            return
        
        try:
            # Try to parse time in HH:MM format
            time_obj = datetime.datetime.strptime(time_str.strip(), '%H:%M')
            
            # Validate hour and minute ranges
            hour = time_obj.hour
            minute = time_obj.minute
            
            if hour < 0 or hour > 23:
                raise ValidationError(f"Invalid hour '{hour}'. Hours must be between 00 and 23.")
            
            if minute < 0 or minute > 59:
                raise ValidationError(f"Invalid minute '{minute}'. Minutes must be between 00 and 59.")
                
        except ValueError:
            raise ValidationError(
                f"Invalid time format: '{time_str}'. "
                f"Please use HH:MM format (e.g., 14:30 for 2:30 PM)."
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating time '{time_str}': {e}")
            raise ValidationError(f"Unable to validate time '{time_str}'. Please check the format.")
    
    @staticmethod
    def validate_recurring_parameters(params: Dict[str, Any]) -> None:
        """
        Validate recurring task parameters.
        
        Args:
            params: Dictionary containing recurring task parameters
            
        Raises:
            ValidationError: If recurring parameters are invalid
        """
        if params.get('IsRecurring', 0) != 1:
            return  # Not a recurring task, no validation needed
        
        freq_type = params.get('FreqType')
        freq_recurrence = params.get('FreqRecurrance', 1)
        freq_interval = params.get('FreqInterval', 1)
        business_day_behavior = params.get('BusinessDayBehavior', 0)
        
        # Validate FreqType
        valid_freq_types = {1: 'daily', 2: 'weekly', 3: 'monthly', 4: 'custom', 5: 'monthly_relative', 6: 'yearly'}
        if freq_type not in valid_freq_types:
            raise ValidationError(
                f"Invalid frequency type. Please specify one of: "
                f"daily, weekly, monthly, yearly."
            )
        
        # Validate FreqRecurrence based on frequency type (bitmask values)
        if not isinstance(freq_recurrence, int) or freq_recurrence < 1:
            raise ValidationError(
                f"Frequency recurrence must be a positive integer. Got: {freq_recurrence}"
            )
        
        # Validate based on frequency type
        if freq_type == 1:  # Daily
            if freq_recurrence != 1:
                raise ValidationError(
                    f"Daily tasks must have FreqRecurrance = 1. Got: {freq_recurrence}"
                )
        elif freq_type == 2:  # Weekly
            if freq_recurrence > 127:  # 7-bit mask for days (Sunday-Saturday)
                raise ValidationError(
                    f"Weekly FreqRecurrance must be 1-127 (day bitmask). Got: {freq_recurrence}"
                )
        elif freq_type == 3:  # Monthly
            if freq_recurrence > 2147483647:  # 31-bit mask for days (1-31)
                raise ValidationError(
                    f"Monthly FreqRecurrance must be valid day bitmask. Got: {freq_recurrence}"
                )
            # UC08 Translation Layer: Large bitmasks are now handled automatically
            if freq_recurrence >= 16384:
                import math
                day = int(math.log2(freq_recurrence)) + 1
                logger.info(f"UC08 large bitmask detected for day {day} - will be handled by translation layer")
        elif freq_type == 4:  # Yearly
            if freq_recurrence > 4095:  # 12-bit mask for months (Jan-Dec)
                raise ValidationError(
                    f"Yearly FreqRecurrance must be valid month bitmask (1-4095). Got: {freq_recurrence}"
                )
        
        # Validate FreqInterval (interval between occurrences)
        if not isinstance(freq_interval, int) or freq_interval < 1 or freq_interval > 365:
            raise ValidationError(
                f"Frequency interval must be between 1 and 365. Got: {freq_interval}"
            )
        
        # Validate BusinessDayBehavior
        if business_day_behavior not in [0, 1, 2]:
            raise ValidationError(
                f"Business day behavior must be 0 (ignore), 1 (skip), or 2 (move). "
                f"Got: {business_day_behavior}"
            )
    
    @staticmethod
    def validate_priority_list_parameter(add_to_priority: Any) -> int:
        """
        Validate and normalize the AddToPriorityList parameter.
        
        Args:
            add_to_priority: Value to validate and convert
            
        Returns:
            Normalized integer value (0 or 1)
            
        Raises:
            ValidationError: If value cannot be converted to valid boolean
        """
        if add_to_priority is None:
            return 0
        
        if isinstance(add_to_priority, bool):
            return 1 if add_to_priority else 0
        
        if isinstance(add_to_priority, int):
            return 1 if add_to_priority != 0 else 0
        
        if isinstance(add_to_priority, str):
            add_to_priority_lower = add_to_priority.lower().strip()
            if add_to_priority_lower in ['yes', 'true', '1', 'on', 'priority']:
                return 1
            elif add_to_priority_lower in ['no', 'false', '0', 'off', '']:
                return 0
            else:
                raise ValidationError(
                    f"Invalid priority list value: '{add_to_priority}'. "
                    f"Please use 'yes', 'no', 'true', 'false', '1', or '0'."
                )
        
        raise ValidationError(
            f"Invalid priority list value type: {type(add_to_priority)}. "
            f"Expected boolean, integer, or string."
        )
    
    @staticmethod
    def validate_content_safety(content: str) -> None:
        """
        Validate content for safety and appropriateness.
        
        Args:
            content: Content to validate
            
        Raises:
            ValidationError: If content contains inappropriate material
        """
        if not content:
            return
        
        content_lower = content.lower()
        
        # Check for potentially harmful patterns
        suspicious_patterns = [
            r'<script[^>]*>',  # JavaScript injection
            r'javascript:',     # JavaScript protocol
            r'on\w+\s*=',      # Event handlers
            r'<iframe[^>]*>',  # Iframes
            r'eval\s*\(',      # Eval function
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                raise ValidationError(
                    "Your message contains content that appears to be code or scripting. "
                    "Please provide a simple description of the task you'd like to create."
                )
        
        # Check for excessively long words (potential buffer overflow attempts)
        words = content.split()
        for word in words:
            if len(word) > 100:  # Reasonable limit for a single word
                raise ValidationError(
                    f"Your message contains an unusually long word ({len(word)} characters). "
                    f"Please check your input and try again."
                )
    
    @staticmethod
    def validate_checklist_items(items: str) -> List[str]:
        """
        Validate and parse checklist items.
        
        Args:
            items: Comma-separated string of checklist items
            
        Returns:
            List of validated checklist items
            
        Raises:
            ValidationError: If checklist items are invalid
        """
        if not items or not items.strip():
            return []
        
        # Split and clean items
        item_list = [item.strip() for item in items.split(',') if item.strip()]
        
        if len(item_list) > 50:  # Reasonable limit for checklist items
            raise ValidationError(
                f"Too many checklist items ({len(item_list)}). "
                f"Please limit to 50 items or fewer."
            )
        
        # Validate each item
        validated_items = []
        for item in item_list:
            if len(item) > 200:  # Reasonable limit for a single checklist item
                raise ValidationError(
                    f"Checklist item is too long ({len(item)} characters): '{item[:50]}...'. "
                    f"Please keep items under 200 characters."
                )
            
            # Basic content safety check
            ValidationService.validate_content_safety(item)
            validated_items.append(item)
        
        return validated_items