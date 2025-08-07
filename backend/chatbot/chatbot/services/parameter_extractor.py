"""
Parameter Extractor Module

This module provides centralized parameter extraction functionality for the chatbot application,
handling all pattern recognition and parameter extraction from user messages.
"""

import datetime
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ParameterExtractor:
    """
    Service class for extracting parameters from user messages.
    Handles all pattern recognition and parameter extraction patterns.
    """
    
    def __init__(self, schedule_parser=None):
        """
        Initialize the parameter extractor.
        
        Args:
            schedule_parser: Schedule parser instance for recurring patterns
        """
        self.schedule_parser = schedule_parser
        
    def pre_extract_parameters(self, user_message: str, main_controller: str, current_date: datetime.date) -> Dict[str, Any]:
        """
        Pre-process the message to extract obvious patterns before AI processing.
        
        Args:
            user_message: User's task creation message
            main_controller: Main controller/group
            current_date: Current date in user's timezone
            
        Returns:
            Dictionary of pre-extracted parameters
        """
        pre_extracted = {}
        msg_lower = user_message.lower()
        
        # Pre-extract reminder settings
        if 'remind me' in msg_lower:
            pre_extracted['Assignees'] = main_controller
            pre_extracted['IsReminder'] = 1
            logger.debug("Detected reminder task - setting IsReminder=1")
            
            # Extract the exact task name for reminders
            quoted_task_match = re.search(r"'([^']+)'", user_message)
            if quoted_task_match:
                task_name = quoted_task_match.group(1).strip()
                pre_extracted['TaskName'] = task_name
                logger.debug(f"Pre-extracted reminder task name from quotes: '{task_name}'")
            else:
                # Fallback: Pattern "remind me ... to [task name]"
                remind_match = re.search(r'remind\s+me.*?to\s+(.+?)(?:\s+at\s+|\s+by\s+|$)', msg_lower)
                if remind_match:
                    task_name = remind_match.group(1).strip()
                    task_name = task_name.strip("'\"")
                    if task_name.startswith("follow up on "):
                        task_name = task_name[13:].strip()
                    pre_extracted['TaskName'] = task_name
                    logger.debug(f"Pre-extracted reminder task name: '{task_name}'")
        else:
            # Extract assignees with various patterns
            pre_extracted.update(self.extract_assignees(user_message))
        
        # Pre-extract priority list
        if any(keyword in msg_lower for keyword in ['priority list', 'add to priority', 'urgent', 'high priority', 'critical']):
            pre_extracted['AddToPriorityList'] = 1
            logger.debug("Detected priority/urgent task - setting AddToPriorityList=1")
        
        # UC10: Confidential task detection
        if 'confidential' in msg_lower:
            pre_extracted['_is_confidential'] = True
        
        # UC12: Team assignment parsing
        team_assignment = self.extract_team_assignments(user_message)
        if team_assignment:
            pre_extracted.update(team_assignment)
        
        # UC11: Checklist items extraction
        checklist_items = self.extract_checklist_items(user_message)
        if checklist_items:
            pre_extracted['Items'] = checklist_items
        
        # UC13: Time-based names detection
        time_based = self.extract_time_based_names(msg_lower)
        if time_based:
            pre_extracted.update(time_based)
        
        # UC14: Relative dates parsing
        relative_dates = self.extract_relative_dates(msg_lower, current_date)
        if relative_dates:
            pre_extracted.update(relative_dates)
        
        # UC15: Controller override
        controller_override = self.extract_controller_override(user_message)
        if controller_override:
            pre_extracted.update(controller_override)
        
        # UC16: Multi-controller detection
        multi_controllers = self.extract_multi_controllers(user_message)
        if multi_controllers:
            pre_extracted.update(multi_controllers)
        
        # UC17: Business day handling
        if 'skip weekend' in msg_lower or 'business day' in msg_lower or 'weekday' in msg_lower:
            pre_extracted['BusinessDayBehavior'] = 1
        
        # UC22: Timezone awareness
        timezone_info = self.extract_timezone_aware(user_message)
        if timezone_info:
            pre_extracted.update(timezone_info)
        
        # UC24: Template reference handling
        template_ref = self.extract_template_reference(user_message, main_controller)
        if template_ref:
            pre_extracted.update(template_ref)
        
        # UC23: Batch task creation
        batch_tasks = self.extract_batch_tasks(user_message)
        if batch_tasks:
            pre_extracted['_batch_tasks'] = batch_tasks
        
        # UC30: Custom notifications
        notification_info = self.extract_custom_notifications(msg_lower)
        if notification_info:
            pre_extracted.update(notification_info)
        
        # Use the schedule parser for recurring patterns
        if self.schedule_parser:
            schedule_params = self.schedule_parser.parse_schedule(user_message)
            if schedule_params['IsRecurring'] == 1:
                pre_extracted.update(schedule_params)
                logger.debug(f"Schedule parser detected recurring pattern: {schedule_params}")
                # Add explicit logging for FreqRecurrance debugging
                logger.info(f"FREQ_DEBUG: Schedule parser returned FreqRecurrance={schedule_params.get('FreqRecurrance')} for message: {user_message[:100]}")
        else:
            # Fallback recurring pattern extraction
            recurring_patterns = self.extract_recurring_patterns(user_message)
            if recurring_patterns:
                pre_extracted.update(recurring_patterns)
        
        # Pre-extract time patterns
        time_patterns = self.extract_time_patterns(msg_lower, current_date)
        if time_patterns:
            pre_extracted.update(time_patterns)
        
        return pre_extracted
    
    def extract_assignees(self, user_message: str) -> Dict[str, Any]:
        """Extract assignees using various patterns."""
        assignee_data = {}
        
        # Enhanced "with" pattern to handle multiple assignees
        with_pattern = r'with\s+((?:[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,?\s*(?:and|&|plus)\s*)?)+)'
        with_match = re.search(with_pattern, user_message)
        if with_match:
            assignees_text = with_match.group(1)
            assignees = re.split(r'\s*,\s*|\s+and\s+|\s+&\s+|\s+plus\s+', assignees_text)
            assignees = [a.strip() for a in assignees if a.strip() and re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', a.strip())]
            if assignees:
                assignee_data['Assignees'] = ','.join(assignees)
        else:
            # "for" pattern - handle both names and groups
            for_match = re.search(r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:Team|Group|Department|Control))?)', user_message)
            if for_match:
                assignee_data['Assignees'] = for_match.group(1)
        
        return assignee_data
    
    def extract_team_assignments(self, user_message: str) -> Dict[str, Any]:
        """Extract team assignment patterns."""
        team_patterns = [
            r'for\s+(\w+)\s+[Tt]eam',  # "for Marketing Team"
            r'[Tt]eam\s+(\w+)\s+to',   # "Team Marketing to"
            r'(\w+)\s+[Tt]eam\s+(?:to|should|will|must)', # "Marketing Team to complete"
        ]
        for pattern in team_patterns:
            team_match = re.search(pattern, user_message)
            if team_match:
                team_name = team_match.group(1)
                logger.debug(f"Detected team assignment: {team_name} Team")
                return {'Assignees': f"{team_name} Team"}
        return {}
    
    def extract_checklist_items(self, user_message: str) -> Optional[str]:
        """Extract checklist items from the message."""
        checklist_match = re.search(r'with\s+(?:checkboxes?|checklist|items)(?:\s+for)?[:\s]+(.+?)(?:\.|$)', user_message, re.IGNORECASE)
        if not checklist_match:
            checklist_match = re.search(r'with\s+items[:\s]+(.+?)(?:\.|$)', user_message, re.IGNORECASE)
        
        if checklist_match:
            items_text = checklist_match.group(1)
            # Split on commas, semicolons, and numbered items
            items = [item.strip() for item in re.split(r'[,;]|\d+\.\s*', items_text) if item.strip()]
            # Remove empty items and clean up
            cleaned_items = []
            for item in items:
                if item and item.strip() and len(item.strip()) > 1:
                    cleaned_items.append(item.strip())
            
            if cleaned_items:
                checklist_items = ','.join(cleaned_items)
                logger.debug(f"Extracted {len(cleaned_items)} checklist items: {checklist_items}")
                return checklist_items
        return None
    
    def extract_time_based_names(self, msg_lower: str) -> Dict[str, Any]:
        """Extract time-based scheduling information."""
        time_data = {}
        if any(time_word in msg_lower for time_word in ['morning', 'afternoon', 'evening', 'night']):
            if 'morning' in msg_lower:
                time_data['DueTime'] = '09:00'
            elif 'afternoon' in msg_lower:
                time_data['DueTime'] = '14:00'
            elif 'evening' in msg_lower or 'night' in msg_lower:
                time_data['DueTime'] = '18:00'
        return time_data
    
    def extract_relative_dates(self, msg_lower: str, current_date: datetime.date) -> Dict[str, Any]:
        """Extract relative date patterns."""
        date_data = {}
        
        # Handle "next [weekday]"
        next_day_match = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', msg_lower)
        if next_day_match:
            target_day = next_day_match.group(1)
            days = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            target_weekday = days[target_day]
            current_weekday = current_date.weekday()
            days_ahead = (target_weekday - current_weekday) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week, not today
            target_date = current_date + datetime.timedelta(days=days_ahead)
            date_data['DueDate'] = target_date.strftime('%Y-%m-%d')
            # Explicitly mark as non-recurring for "next [weekday]" patterns
            date_data['IsRecurring'] = 0
            date_data['FreqType'] = 0
        # Handle "tomorrow"
        elif 'tomorrow' in msg_lower:
            tomorrow = current_date + datetime.timedelta(days=1)
            date_data['DueDate'] = tomorrow.strftime('%Y-%m-%d')
        
        return date_data
    
    def extract_controller_override(self, user_message: str) -> Dict[str, Any]:
        """Extract controller override patterns."""
        controller_match = re.search(r'(?:managed|controlled)\s+by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', user_message)
        if controller_match:
            return {'_override_controller': controller_match.group(1)}
        return {}
    
    def extract_multi_controllers(self, user_message: str) -> Dict[str, Any]:
        """Extract multi-controller patterns."""
        multi_controller_match = re.search(r'controlled\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:Team|Group|Department))?)(?:\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:Team|Group|Department))?))+', user_message)
        if multi_controller_match:
            controllers = [multi_controller_match.group(1)]
            if multi_controller_match.group(2):
                controllers.append(multi_controller_match.group(2))
            return {'_multi_controllers': ','.join(controllers)}
        return {}
    
    def extract_business_days(self, user_message: str) -> Dict[str, Any]:
        """Extract business day handling patterns."""
        msg_lower = user_message.lower()
        if 'skip weekend' in msg_lower or 'business day' in msg_lower or 'weekday' in msg_lower:
            return {'BusinessDayBehavior': 1}
        return {}
    
    def extract_timezone_aware(self, user_message: str) -> Dict[str, Any]:
        """Extract timezone information."""
        timezone_match = re.search(r'at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s+(ET|EST|EDT|PT|PST|PDT|CT|CST|CDT|MT|MST|MDT)', user_message, re.IGNORECASE)
        if timezone_match:
            source_tz = timezone_match.group(1).upper()
            return {'_source_timezone': source_tz}
        return {}
    
    def extract_template_reference(self, user_message: str, main_controller: str) -> Dict[str, Any]:
        """Extract template reference patterns."""
        msg_lower = user_message.lower()
        if 'template' in msg_lower:
            logger.debug(f"Template reference detected - using default assignee: {main_controller}")
            return {'Assignees': main_controller}
        return {}
    
    def extract_batch_tasks(self, user_message: str) -> Optional[List[str]]:
        """Extract batch task creation patterns."""
        msg_lower = user_message.lower()
        
        # Pattern 1: "create tasks:" or "tasks:"
        if 'create tasks:' in msg_lower or 'tasks:' in msg_lower:
            tasks_match = re.search(r'(?:create\s+)?tasks:\s*(.+)', user_message, re.IGNORECASE)
            if tasks_match:
                tasks_text = tasks_match.group(1)
                # First try to find quoted tasks
                quoted_tasks = re.findall(r"'([^']+)'", tasks_text)
                if quoted_tasks:
                    tasks = quoted_tasks
                else:
                    # Fall back to splitting by comma, semicolon
                    tasks = [t.strip() for t in re.split(r'[,;]', tasks_text) if t.strip()]
                
                # Clean up task names
                cleaned_tasks = []
                for task in tasks:
                    task = task.strip().strip("'\"")
                    if task:
                        cleaned_tasks.append(task)
                
                if len(cleaned_tasks) >= 1:
                    logger.debug(f"Detected batch task creation with {len(cleaned_tasks)} tasks")
                    return cleaned_tasks
        
        # Pattern 2: "create tasks for: task1, task2, task3"
        if 'create tasks for:' in msg_lower:
            tasks_match = re.search(r'create\s+tasks\s+for:\s*(.+)', user_message, re.IGNORECASE)
            if tasks_match:
                tasks_text = tasks_match.group(1)
                # Split by comma
                tasks = [t.strip() for t in tasks_text.split(',') if t.strip()]
                
                # Clean up task names
                cleaned_tasks = []
                for task in tasks:
                    task = task.strip().strip("'\"")
                    if task:
                        cleaned_tasks.append(task)
                
                if len(cleaned_tasks) >= 1:
                    logger.debug(f"Detected batch task creation (for pattern) with {len(cleaned_tasks)} tasks")
                    return cleaned_tasks
        
        return None
    
    def extract_custom_notifications(self, msg_lower: str) -> Dict[str, Any]:
        """Extract custom notification patterns."""
        notification_match = re.search(r'(?:email\s+)?notification\s+(\d+)\s+(hour|minute)s?\s+before', msg_lower)
        if notification_match:
            amount = int(notification_match.group(1))
            unit = notification_match.group(2)
            return {
                'IsReminder': 1,
                '_reminder_offset_hours': amount if unit == 'hour' else amount / 60
            }
        return {}
    
    def is_reminder_task(self, user_message: str) -> bool:
        """Check if the message indicates a reminder task."""
        msg_lower = user_message.lower()
        return 'remind me' in msg_lower
    
    def extract_recurring_patterns(self, user_message: str) -> Dict[str, Any]:
        """Extract recurring patterns when schedule parser is not available."""
        msg_lower = user_message.lower()
        recurring_data = {}
        
        # Daily patterns
        if any(word in msg_lower for word in ['daily', 'every day', 'each day']):
            recurring_data.update({
                'IsRecurring': 1,
                'FreqType': 1,  # Daily
                'FreqRecurrance': 1,
                'FreqInterval': 1
            })
        # Weekly patterns
        elif any(word in msg_lower for word in ['weekly', 'every week', 'each week']):
            recurring_data.update({
                'IsRecurring': 1,
                'FreqType': 2,  # Weekly
                'FreqRecurrance': 1,
                'FreqInterval': 1
            })
        # Monthly patterns
        elif any(word in msg_lower for word in ['monthly', 'every month', 'each month']):
            recurring_data.update({
                'IsRecurring': 1,
                'FreqType': 3,  # Monthly
                'FreqRecurrance': 1,
                'FreqInterval': 1
            })
        # Yearly patterns
        elif any(word in msg_lower for word in ['yearly', 'annually', 'every year', 'each year']):
            recurring_data.update({
                'IsRecurring': 1,
                'FreqType': 4,  # Yearly
                'FreqRecurrance': 1,
                'FreqInterval': 1
            })
        
        return recurring_data
    
    def extract_time_patterns(self, msg_lower: str, current_date: datetime.date) -> Dict[str, Any]:
        """Extract time patterns from message."""
        time_data = {}
        time_match = re.search(r'at\s+(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm)?', msg_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            meridian = time_match.group(3)
            if meridian == 'pm' and hour != 12:
                hour += 12
            elif meridian == 'am' and hour == 12:
                hour = 0
            time_data['DueTime'] = f"{hour:02d}:{minute:02d}"
            # If time is specified for today, set due date to today
            if 'at' in msg_lower and not any(word in msg_lower for word in ['tomorrow', 'next', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                time_data['DueDate'] = current_date.strftime('%Y-%m-%d')
        return time_data