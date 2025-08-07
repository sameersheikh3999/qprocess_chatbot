"""
DateTime Service Module

This module provides centralized datetime functionality for the chatbot application,
including timezone handling, natural language date/time parsing, and smart defaults.
"""

import datetime
import pytz
import re
import logging
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class DateTimeService:
    """
    Service class for handling datetime operations, timezone conversions,
    and natural language date/time parsing.
    """

    @staticmethod
    def convert_to_user_timezone(date_str, time_str, user_timezone):
        """
        Convert date and time strings to the user's timezone.
        
        Args:
            date_str (str|date): Date string in 'YYYY-MM-DD' format or date object
            time_str (str|time): Time string in 'HH:MM' format or time object
            user_timezone (str): Timezone string (e.g., 'America/New_York')
            
        Returns:
            tuple: (date_str, time_str) converted to user timezone
            
        Raises:
            None: Returns original values if conversion fails
        """
        try:
            if not date_str or not time_str:
                return date_str, time_str
                
            # Parse the date and time
            if isinstance(date_str, str):
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_obj = date_str
                
            if isinstance(time_str, str):
                time_obj = datetime.datetime.strptime(time_str, '%H:%M').time()
            else:
                time_obj = time_str
                
            # Combine date and time
            datetime_obj = datetime.datetime.combine(date_obj, time_obj)
            
            # Convert to user timezone
            user_tz = pytz.timezone(user_timezone)
            local_dt = user_tz.localize(datetime_obj)
            
            return local_dt.date().isoformat(), local_dt.time().strftime('%H:%M')
        except Exception as e:
            logger.warning(f"Failed to convert to user timezone: {e}")
            # If conversion fails, return original values
            return date_str, time_str

    @staticmethod
    def get_current_date_in_timezone(user_timezone):
        """
        Get the current date in the user's timezone.
        
        Args:
            user_timezone (str): Timezone string (e.g., 'America/New_York')
            
        Returns:
            date: Current date in the specified timezone
            
        Raises:
            None: Returns UTC date if timezone is invalid
        """
        try:
            user_tz = pytz.timezone(user_timezone)
            current_time = datetime.datetime.now(user_tz)
            return current_time.date()
        except Exception as e:
            logger.warning(f"Invalid timezone '{user_timezone}': {e}")
            # Fallback to UTC if timezone is invalid
            return datetime.date.today()

    @classmethod
    def parse_natural_date_with_timezone(cls, date_str, user_timezone):
        """
        Parse natural language dates in the context of user's timezone.
        
        Args:
            date_str (str): Natural language date string (e.g., 'tomorrow', 'next monday')
            user_timezone (str): Timezone string for context
            
        Returns:
            str|None: ISO format date string (YYYY-MM-DD) or None if parsing fails
        """
        # Get current date in user's timezone
        today = cls.get_current_date_in_timezone(user_timezone)
        
        if not date_str:
            return None
        
        s = date_str.strip().lower()
        
        # Handle relative dates
        if s == 'today':
            return today.isoformat()
        elif s == 'tomorrow' or s == 'tmrw':
            return (today + datetime.timedelta(days=1)).isoformat()
        elif s == 'day after tomorrow' or s == 'day after tmrw':
            return (today + datetime.timedelta(days=2)).isoformat()
        elif s == 'yesterday':
            return (today - datetime.timedelta(days=1)).isoformat()
        
        # Handle "next [weekday]" patterns - FIXED!
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day_name in enumerate(weekdays):
            if f'next {day_name}' in s:
                current_weekday = today.weekday()
                target_weekday = i
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # If today is the target day, go to next week
                target_date = today + datetime.timedelta(days=days_ahead)
                logger.debug(f"Parsed 'next {day_name}' as {target_date.isoformat()}")
                return target_date.isoformat()
        
        # Handle "this [weekday]" patterns
        for i, day_name in enumerate(weekdays):
            if f'this {day_name}' in s:
                current_weekday = today.weekday()
                target_weekday = i
                days_ahead = (target_weekday - current_weekday) % 7
                # For "this", include today if it matches
                target_date = today + datetime.timedelta(days=days_ahead)
                logger.debug(f"Parsed 'this {day_name}' as {target_date.isoformat()}")
                return target_date.isoformat()
        
        # Handle end of week/month
        if 'end of week' in s or 'end of the week' in s:
            # Go to Friday - matching validator logic
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7  # If today is Friday, go to next Friday
            return (today + datetime.timedelta(days=days_until_friday)).isoformat()
        
        elif s.startswith('next week'):
            return (today + datetime.timedelta(weeks=1)).isoformat()
        elif s.startswith('next month'):
            # Add one month to current date
            next_month = today.replace(day=1) + datetime.timedelta(days=32)
            next_month = next_month.replace(day=1)
            return next_month.isoformat()
        elif s.startswith('this week'):
            # Find the start of current week (Monday)
            days_since_monday = today.weekday()
            monday = today - datetime.timedelta(days=days_since_monday)
            return monday.isoformat()
        elif s.startswith('this month'):
            # First day of current month
            first_day = today.replace(day=1)
            return first_day.isoformat()
        elif s.startswith('in ') and ' days' in s:
            # Handle "in X days"
            try:
                days = int(s.split('in ')[1].split(' days')[0])
                return (today + datetime.timedelta(days=days)).isoformat()
            except:
                pass
        elif s.startswith('in ') and ' day' in s:
            # Handle "in X day" (singular)
            try:
                days = int(s.split('in ')[1].split(' day')[0])
                return (today + datetime.timedelta(days=days)).isoformat()
            except:
                pass
        
        # If already in YYYY-MM-DD format, return as is
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except Exception:
            return None

    @staticmethod
    def parse_natural_time_with_timezone(time_str, user_timezone):
        """
        Parse natural language time references in the context of user's timezone.
        
        Args:
            time_str (str): Natural language time string (e.g., 'morning', '2pm')
            user_timezone (str): Timezone string for context
            
        Returns:
            str|None: Time string in HH:MM format or None if parsing fails
        """
        if not time_str:
            return None
        
        s = time_str.strip().lower()
        
        # Handle common time references
        if s == 'morning' or s == 'early morning':
            return '09:00'
        elif s == 'late morning':
            return '11:00'
        elif s == 'noon' or s == 'midday':
            return '12:00'
        elif s == 'afternoon' or s == 'early afternoon':
            return '14:00'
        elif s == 'late afternoon':
            return '16:00'
        elif s == 'evening' or s == 'early evening':
            return '18:00'
        elif s == 'late evening':
            return '20:00'
        elif s == 'night' or s == 'late night':
            return '22:00'
        elif s == 'midnight':
            return '00:00'
        elif s == 'after close' or s == 'after closing':
            return '19:00'  # 7 PM after close
        elif s == 'before close' or s == 'before closing':
            return '16:00'
        
        # Handle AM/PM format (e.g., "2pm", "12:30am", "3:45 PM")
        am_pm_match = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', s)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            minute = int(am_pm_match.group(2) or 0)
            meridian = am_pm_match.group(3)
            
            # Convert to 24-hour format
            if meridian == 'pm' and hour != 12:
                hour += 12
            elif meridian == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:{minute:02d}"
        
        # If already in HH:MM format, return as is
        try:
            datetime.datetime.strptime(time_str, '%H:%M')
            return time_str
        except Exception:
            return None

    @staticmethod
    def parse_natural_date(date_str):
        """
        Parse natural language dates (timezone-agnostic version).
        
        Args:
            date_str (str): Natural language date string
            
        Returns:
            str|None: ISO format date string (YYYY-MM-DD) or None if parsing fails
        """
        today = datetime.date.today()
        if not date_str:
            return None
        s = date_str.strip().lower()
        if s == 'today':
            return today.isoformat()
        if s == 'tomorrow' or s == 'tmrw':
            return (today + datetime.timedelta(days=1)).isoformat()
        if s == 'day after tomorrow':
            return (today + datetime.timedelta(days=2)).isoformat()
        if s == 'yesterday':
            return (today - datetime.timedelta(days=1)).isoformat()
        
        # Handle "next [weekday]" patterns
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day_name in enumerate(weekdays):
            if f'next {day_name}' in s:
                current_weekday = today.weekday()
                target_weekday = i
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # If today is the target day, go to next week
                return (today + datetime.timedelta(days=days_ahead)).isoformat()
        
        # Handle "this [weekday]" patterns
        for i, day_name in enumerate(weekdays):
            if f'this {day_name}' in s:
                current_weekday = today.weekday()
                target_weekday = i
                days_ahead = (target_weekday - current_weekday) % 7
                return (today + datetime.timedelta(days=days_ahead)).isoformat()
        
        if s.startswith('next week'):
            return (today + datetime.timedelta(weeks=1)).isoformat()
        # Add more patterns as needed
        # If already in YYYY-MM-DD, return as is
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except Exception:
            return None

    @staticmethod
    def parse_natural_time(time_str):
        """
        Parse natural language time references (timezone-agnostic version).
        
        Args:
            time_str (str): Natural language time string
            
        Returns:
            str|None: Time string in HH:MM format or None if parsing fails
        """
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

    @staticmethod
    def guess_time_from_task_type(task_name):
        """
        Guess appropriate time based on task type.
        
        Args:
            task_name (str): Name of the task
            
        Returns:
            str: Time in HH:MM format based on task type patterns
        """
        task_lower = task_name.lower()
        
        # Meeting patterns
        if any(word in task_lower for word in ['meeting', 'standup', 'sync', 'huddle', 'call']):
            return '14:00'  # 2 PM for meetings
        
        # Morning tasks
        elif any(word in task_lower for word in ['check email', 'daily check', 'morning']):
            return '09:00'  # 9 AM for morning tasks
        
        # Reports/reviews
        elif any(word in task_lower for word in ['report', 'review', 'analysis', 'summary']):
            return '19:00'  # 7 PM for reports
        
        # Reminders
        elif 'remind' in task_lower:
            return '10:00'  # 10 AM for reminders
        
        # End of day tasks
        elif any(word in task_lower for word in ['end of day', 'eod', 'close']):
            return '19:00'  # 7 PM default
        
        # Default
        else:
            return '19:00'  # 7 PM default - per requirement

    @classmethod
    def set_default_due_date_time(cls, params, user_timezone):
        """
        Set default due date to tomorrow at smart time based on task type.
        Default time is 19:00 (7:00 PM) local time when not specified.
        Also automatically set LocalDueDate and SoftDueDate to match the DueDate.
        
        Args:
            params (dict): Task parameters dictionary to modify
            user_timezone (str): User's timezone string
            
        Returns:
            dict: Modified parameters with default due date and time set
        """
        current_date = cls.get_current_date_in_timezone(user_timezone)
        tomorrow = current_date + datetime.timedelta(days=1)
        
        # Set default due date if not provided
        if not params.get('DueDate') or params['DueDate'] in [None, '']:
            # Check for urgency indicators
            task_name = params.get('TaskName', '').lower()
            if any(word in task_name for word in ['urgent', 'asap', 'immediately', 'now']):
                params['DueDate'] = current_date.isoformat()  # Today for urgent tasks
            else:
                params['DueDate'] = tomorrow.isoformat()  # Tomorrow by default
        
        # Set default due time if not provided - use smart defaults
        if not params.get('DueTime') or params['DueTime'] in [None, '']:
            task_name = params.get('TaskName', '')
            params['DueTime'] = cls.guess_time_from_task_type(task_name)
        
        # Always set LocalDueDate to match the DueDate
        params['LocalDueDate'] = params['DueDate']
        
        # Only set SoftDueDate to match DueDate if not explicitly provided
        if not params.get('SoftDueDate') or params['SoftDueDate'] in [None, '']:
            params['SoftDueDate'] = params['DueDate']
        
        return params