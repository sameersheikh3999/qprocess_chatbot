"""
Task Service Module

This module provides centralized task creation orchestration for the chatbot application,
coordinating between AI, database, and validation services to handle business logic for task creation.
"""

import datetime
import re
import time
import logging
import json as pyjson
from typing import Dict, Any, List, Tuple, Optional

from .datetime_service import DateTimeService
from .ai_service import AIService  
from .database_service import DatabaseService
from .parameter_extractor import ParameterExtractor
from .validation_service import ValidationService
from .session_service import SessionService
from .error_handler import error_handler, TaskCreationError, ValidationError, DatabaseError

# Import the schedule parser
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schedule_parser import ScheduleParser

logger = logging.getLogger(__name__)


# TaskCreationError is now imported from error_handler


class TaskService:
    """
    Service class for handling task creation orchestration.
    Coordinates between AI, database, and validation services to handle
    all business logic related to task creation.
    """
    
    def __init__(self, ai_service: AIService):
        """
        Initialize the task service with required dependencies.
        
        Args:
            ai_service: AI service instance for processing task extraction
        """
        self.ai_service = ai_service
        self.schedule_parser = ScheduleParser()
        self.parameter_extractor = ParameterExtractor(self.schedule_parser)
        
    def create_task(self, user_message: str, user_name: str, main_controller: str, 
                   user_timezone: str = 'UTC', debug_mode: bool = False) -> Dict[str, Any]:
        """
        Main orchestration method for task creation.
        
        Args:
            user_message: User's task creation message
            user_name: Username making the request
            main_controller: Main controller/group for the task
            user_timezone: User's timezone
            debug_mode: Enable debug mode for testing
            
        Returns:
            Dictionary containing the response data
            
        Raises:
            TaskCreationError: If task creation fails
        """
        request_start_time = time.time()
        
        # Validate input message and group
        try:
            ValidationService.validate_message_length(user_message)
            ValidationService.validate_content_safety(user_message)
            group_exists, user_fullname, similar_groups = ValidationService.validate_group(main_controller)
        except ValidationError as e:
            raise TaskCreationError(str(e), 'VALIDATION_FAILED')
        
        # Handle session management
        session = SessionService.manage_task_session(user_name, user_message)
        
        try:
            # Get parameters and history from session
            params = SessionService.get_session_parameters(session)
            history = SessionService.get_session_history(session)
            
            # Add current user message to history BEFORE calling AI service
            SessionService.add_to_session_history(session, "user", user_message)
            # Get updated history that includes the current message
            history = SessionService.get_session_history(session)
            
            # Ensure history has at least one message for Groq API
            if not history:
                history = [{"role": "user", "content": user_message}]
            
            # Get current date in user's timezone for context
            current_date = DateTimeService.get_current_date_in_timezone(user_timezone)
            
            # Check for conditional logic patterns and reject
            if self.ai_service.check_conditional_logic(user_message):
                raise TaskCreationError('Conditional logic is not supported')
            
            # Pre-process the message to extract obvious patterns
            pre_extracted = self.parameter_extractor.pre_extract_parameters(user_message, main_controller, current_date)
            
            # Process task extraction using AI service
            logger.debug(f"Pre-extracted parameters: {pre_extracted}")
            logger.debug(f"History length: {len(history)}")
            success, llm_json, content = self.ai_service.process_task_extraction(
                user_message, main_controller, current_date, pre_extracted, history, debug_mode
            )
            
            if not success:
                # Handle AI service errors or non-JSON responses
                SessionService.save_session(session)
                return {'reply': content}
            
            # Merge new parameters from LLM with those already stored
            params.update(llm_json)
            SessionService.update_session_parameters(session, params)
            SessionService.save_session(session)
            
            # Apply smart defaults and business rules
            params = self._apply_smart_defaults(params, main_controller)
            
            # Apply fallback extraction if needed
            params = self._apply_fallback_extraction(params, user_message, main_controller)
            
            # Apply business rule transformations
            params = self._apply_business_rules(params, pre_extracted, user_timezone)
            
            # Check for batch task creation
            if pre_extracted.get('_batch_tasks'):
                return self._handle_batch_task_creation(
                    pre_extracted['_batch_tasks'], params, user_fullname, user_timezone, debug_mode
                )
            
            # Validate required fields and other parameters
            try:
                ValidationService.validate_required_fields(params)
                if 'TaskName' in params:
                    ValidationService.validate_task_name(params['TaskName'])
                if 'Assignees' in params:
                    ValidationService.validate_assignees(params['Assignees'])
                if params.get('IsRecurring', 0) == 1:
                    ValidationService.validate_recurring_parameters(params)
                if 'Items' in params and params['Items']:
                    ValidationService.validate_checklist_items(params['Items'])
            except ValidationError as e:
                raise TaskCreationError(str(e), 'VALIDATION_FAILED')
            
            # Process dates and times
            params = self._process_dates_and_times(params, user_timezone)
            
            # Set automatic parameters
            params = self._set_automatic_parameters(params, user_timezone)
            
            # Convert and validate parameter types
            params = self._convert_parameter_types(params)
            
            # Create the task
            instance_id = self._create_single_task(params, user_fullname, debug_mode)
            
            # Clean up session
            SessionService.delete_session(session)
            
            # Build response
            response_data = self._build_success_response(params, instance_id, main_controller)
            
            # Add debug information if requested
            if debug_mode:
                response_data['debug'] = {
                    'instance_id': instance_id,
                    'parameters': params,
                    'groq_response': content if 'content' in locals() else None,
                    'execution_time': time.time() - request_start_time
                }
            
            return response_data
            
        except Exception as e:
            # Ensure session cleanup on error
            try:
                error_context = {'history': history} if 'history' in locals() else None
                SessionService.handle_session_error(session, error_context)
            except:
                pass
            raise
    
    def _apply_smart_defaults(self, params: Dict[str, Any], main_controller: str) -> Dict[str, Any]:
        """Apply smart defaults before checking required fields."""
        if 'Controllers' not in params or params['Controllers'] in [None, '']:
            params['Controllers'] = main_controller  # Default to MainController
        
        if 'Items' not in params or params['Items'] in [None, '']:
            params['Items'] = ''  # Default to empty string
        
        # For non-recurring tasks, set recurring fields to 0
        if params.get('IsRecurring', 0) == 0:
            params['FreqType'] = 0
            params['FreqRecurrance'] = 0
            params['FreqInterval'] = 0
            params['BusinessDayBehavior'] = 0
        else:
            # For recurring tasks, ensure proper defaults
            if 'FreqInterval' not in params or params['FreqInterval'] == 0:
                params['FreqInterval'] = 1  # Default to 1 instead of 0
            if 'FreqRecurrance' not in params or params['FreqRecurrance'] == 0:
                params['FreqRecurrance'] = 1  # Default to 1 instead of 0
        
        return params
    
    def _apply_fallback_extraction(self, params: Dict[str, Any], user_message: str, main_controller: str) -> Dict[str, Any]:
        """Apply fallback extraction if AI didn't extract assignees."""
        if ('Assignees' not in params or params['Assignees'] in [None, '']) and user_message:
            msg_lower = user_message.lower()
            
            # Check for "remind me" pattern
            if 'remind me' in msg_lower:
                params['Assignees'] = main_controller
                logger.debug(f"Fallback extraction: 'remind me' → Assignees='{main_controller}'")
            else:
                # Try various patterns
                patterns = [
                    (r'with\s+([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+and\s+([A-Z][a-z]+\s+[A-Z][a-z]+))?', 'with'),
                    (r'for\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', 'for'),
                    (r'to\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', 'to')
                ]
                
                for pattern, pattern_name in patterns:
                    match = re.search(pattern, user_message)
                    if match:
                        assignees = [match.group(1)]
                        if match.group(2):  # Second group for 'with' pattern
                            assignees.append(match.group(2))
                        params['Assignees'] = ','.join(assignees)
                        logger.debug(f"Fallback extraction: '{pattern_name}' pattern → Assignees='{params['Assignees']}'")
                        break
        
        # Extract priority list if missing
        current_priority = params.get('AddToPriorityList')
        if current_priority is None or str(current_priority) in ['', '0', 'None', '0.0']:
            if 'priority list' in user_message.lower() or 'add to priority' in user_message.lower():
                params['AddToPriorityList'] = 1
                logger.debug("Fallback extraction: Found 'priority list' → AddToPriorityList=1")
            else:
                params['AddToPriorityList'] = 0
        
        return params
    
    def _apply_business_rules(self, params: Dict[str, Any], pre_extracted: Dict[str, Any], user_timezone: str) -> Dict[str, Any]:
        """Apply business rules based on pre-extracted data."""
        
        # UC10: Apply [CONFIDENTIAL] prefix if detected
        if pre_extracted.get('_is_confidential') and 'TaskName' in params:
            if not params['TaskName'].startswith('[CONFIDENTIAL]'):
                params['TaskName'] = f"[CONFIDENTIAL] {params['TaskName']}"
                logger.debug(f"Applied confidential prefix to task: {params['TaskName']}")
        
        # UC15: Apply controller override if detected
        if pre_extracted.get('_override_controller'):
            params['Controllers'] = pre_extracted['_override_controller']
            logger.debug(f"Overrode controller to: {params['Controllers']}")
        
        # UC16: Apply multi-controller if detected
        if pre_extracted.get('_multi_controllers'):
            params['Controllers'] = pre_extracted['_multi_controllers']
            logger.debug(f"Set multiple controllers: {params['Controllers']}")
        
        # UC22: Handle timezone conversion if source timezone specified
        if pre_extracted.get('_source_timezone'):
            logger.debug(f"Source timezone detected: {pre_extracted['_source_timezone']}")
            # For now, just log it - actual conversion would require pytz or similar
        
        # UC30: Calculate reminder date based on offset
        if pre_extracted.get('_reminder_offset_hours'):
            try:
                offset_hours = pre_extracted['_reminder_offset_hours']
                due_date = datetime.datetime.strptime(params['DueDate'], '%Y-%m-%d')
                due_time_parts = params.get('DueTime', '19:00').split(':')
                due_datetime = due_date.replace(hour=int(due_time_parts[0]), minute=int(due_time_parts[1]))
                reminder_datetime = due_datetime - datetime.timedelta(hours=offset_hours)
                params['ReminderDate'] = reminder_datetime.date().isoformat()
                logger.debug(f"Calculated reminder date {offset_hours} hours before: {params['ReminderDate']}")
            except Exception as e:
                logger.error(f"Error calculating reminder date: {e}")
        
        return params
    
    
    def _process_dates_and_times(self, params: Dict[str, Any], user_timezone: str) -> Dict[str, Any]:
        """Process date and time parameters with timezone conversion."""
        # Validate date and time formats before processing
        try:
            if 'DueDate' in params and params['DueDate']:
                ValidationService.validate_date_time(date_str=params['DueDate'])
            if 'DueTime' in params and params['DueTime']:
                ValidationService.validate_date_time(time_str=params['DueTime'])
            if 'SoftDueDate' in params and params['SoftDueDate']:
                ValidationService.validate_date_time(date_str=params['SoftDueDate'])
        except ValidationError as e:
            raise TaskCreationError(str(e), 'VALIDATION_FAILED')
        
        if 'DueDate' in params:
            params['DueDate'] = DateTimeService.parse_natural_date_with_timezone(params['DueDate'], user_timezone)
        if 'DueTime' in params:
            params['DueTime'] = DateTimeService.parse_natural_time_with_timezone(params['DueTime'], user_timezone)
        if 'SoftDueDate' in params and params['SoftDueDate']:
            params['SoftDueDate'] = DateTimeService.parse_natural_date_with_timezone(params['SoftDueDate'], user_timezone)
        
        # Apply default due date and time if missing, and set LocalDueDate/SoftDueDate to match DueDate
        params = DateTimeService.set_default_due_date_time(params, user_timezone)
        
        return params
    
    def _set_automatic_parameters(self, params: Dict[str, Any], user_timezone: str) -> Dict[str, Any]:
        """Set automatic parameters that don't need user input."""
        # Set Location to user's timezone
        params['Location'] = user_timezone
        
        # Set Activate to 1 (always active)
        params['Activate'] = 1
        
        # Set AddToPriorityList using validation service
        if 'AddToPriorityList' not in params or params['AddToPriorityList'] in [None, '']:
            params['AddToPriorityList'] = 0
        else:
            try:
                params['AddToPriorityList'] = ValidationService.validate_priority_list_parameter(params['AddToPriorityList'])
            except ValidationError as e:
                logger.warning(f"Invalid AddToPriorityList value, using default: {e}")
                params['AddToPriorityList'] = 0
        
        # Set IsReminder to 1 (reminder enabled) unless user specifies
        if 'IsReminder' not in params or params['IsReminder'] in [None, '']:
            params['IsReminder'] = 1
        
        # Set ReminderDate to day before DueDate unless user specifies
        if 'ReminderDate' not in params or params['ReminderDate'] in [None, '']:
            if params.get('DueDate'):
                try:
                    due_date = datetime.datetime.strptime(params['DueDate'], '%Y-%m-%d').date()
                    reminder_date = due_date - datetime.timedelta(days=1)
                    params['ReminderDate'] = reminder_date.isoformat()
                except:
                    current_date = DateTimeService.get_current_date_in_timezone(user_timezone)
                    tomorrow = current_date + datetime.timedelta(days=1)
                    params['ReminderDate'] = tomorrow.isoformat()
            else:
                current_date = DateTimeService.get_current_date_in_timezone(user_timezone)
                tomorrow = current_date + datetime.timedelta(days=1)
                params['ReminderDate'] = tomorrow.isoformat()
        
        # Set FinalDueDate to match DueDate (if DueDate exists)
        if params.get('DueDate'):
            params['FinalDueDate'] = params['DueDate']
        else:
            current_date = DateTimeService.get_current_date_in_timezone(user_timezone)
            tomorrow = current_date + datetime.timedelta(days=1)
            params['FinalDueDate'] = tomorrow.isoformat()
        
        return params
    
    def _convert_parameter_types(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert and validate parameter types."""
        
        # Convert text-based frequency types to integers
        def convert_freq_type_to_int(freq_type):
            if isinstance(freq_type, int):
                return freq_type
            if isinstance(freq_type, str):
                freq_lower = freq_type.lower().strip()
                if freq_lower in ['daily', 'day', '1']:
                    return 1
                elif freq_lower in ['weekly', 'week', '2']:
                    return 2
                elif freq_lower in ['monthly', 'month', '3']:
                    return 3
                elif freq_lower in ['yearly', 'year', '4']:
                    return 4
            return 1  # Default to Daily
        
        # Convert FreqType to integer if it's a string
        if 'FreqType' in params:
            params['FreqType'] = convert_freq_type_to_int(params['FreqType'])
        
        # Ensure all integer parameters are actually integers
        def convert_to_int(value, param_name):
            """Convert value to integer with proper handling for boolean-like strings"""
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                value_lower = value.lower().strip()
                # Handle boolean-like strings
                if value_lower in ['yes', 'true', '1', 'on']:
                    return 1
                elif value_lower in ['no', 'false', '0', 'off']:
                    return 0
                # Try direct conversion
                try:
                    return int(value)
                except ValueError:
                    pass
            # Set default values if conversion fails
            default_values = {
                'IsRecurring': 0,
                'FreqRecurrance': 1,
                'FreqInterval': 1,
                'BusinessDayBehavior': 0,
                'Activate': 1,
                'IsReminder': 1,
                'AddToPriorityList': 0
            }
            return default_values.get(param_name, 0)
        
        integer_params = ['IsRecurring', 'FreqRecurrance', 'FreqInterval', 'BusinessDayBehavior', 'Activate', 'IsReminder', 'AddToPriorityList']
        for param in integer_params:
            if param in params:
                params[param] = convert_to_int(params[param], param)
        
        return params
    
    def _create_single_task(self, params: Dict[str, Any], user_fullname: str, debug_mode: bool = False) -> Optional[int]:
        """Create a single task using the database service."""
        
        # Convert time format from HH:MM to integer format
        due_time_int = self._convert_time_to_int(params.get('DueTime', '19:00'))
        
        # Format dates for SQL Server
        def format_date_for_sql(date_str, time_str=None):
            if not date_str:
                return None
            try:
                if ' ' in date_str or 'T' in date_str:
                    return date_str
                if time_str:
                    return f"{date_str} {time_str}:00"
                else:
                    return f"{date_str} 00:00:00"
            except:
                return None
        
        # Debug logging for multiple assignees and checklist items
        if ',' in params.get('Assignees', ''):
            logger.info(f"Multiple assignees detected: {params['Assignees']}")
        
        if params.get('Items'):
            logger.info(f"Checklist items detected: {params['Items']}")
        
        # Prepare parameters for stored procedure
        stored_proc_params = [
            params['TaskName'],
            user_fullname,
            params['Controllers'],
            params['Assignees'],
            format_date_for_sql(params['DueDate'], params.get('DueTime')),
            format_date_for_sql(params['LocalDueDate'], params.get('DueTime')),
            params['Location'],
            due_time_int,
            format_date_for_sql(params['SoftDueDate'], params.get('DueTime')),
            format_date_for_sql(params['FinalDueDate'], params.get('DueTime')),
            params['Items'],
            int(params['IsRecurring']),
            params['FreqType'],
            params['FreqRecurrance'],
            params['FreqInterval'],
            params['BusinessDayBehavior'],
            int(params['Activate']),
            int(params['IsReminder']),
            format_date_for_sql(params['ReminderDate'], params.get('DueTime')),
            int(params['AddToPriorityList']),
        ]
        
        # Validate recurring parameters before sending to stored procedure
        if params.get('IsRecurring') == 1:
            freq_type = params.get('FreqType', 0)
            freq_interval = params.get('FreqInterval', 1)
            freq_recurrance = params.get('FreqRecurrance', 0)
            
            # Sanity check for common errors
            if freq_type == 2 and freq_interval > 10:
                logger.warning(f"Suspicious FreqInterval={freq_interval} for weekly task. Possible parameter swap?")
                # Check if it matches a day bitmask
                if freq_interval in [1, 2, 4, 8, 16, 32, 64]:
                    logger.error(f"FreqInterval={freq_interval} looks like a day bitmask! This suggests parameter corruption.")
            
            if freq_type == 2 and freq_recurrance > 127:  # Max valid day bitmask is 127 (all days)
                logger.warning(f"Invalid FreqRecurrance={freq_recurrance} for weekly task (max should be 127)")
        
        # Log parameters for debugging
        if debug_mode or params.get('IsRecurring') == 1:
            # Add explicit logging for FreqRecurrance debugging
            logger.info(f"FREQ_DEBUG: Before stored proc, FreqRecurrance={params.get('FreqRecurrance')} for task: {params.get('TaskName', '')[:50]}")
            logger.info("="*60)
            logger.info(f"STORED PROCEDURE CALL for task: {params['TaskName']}")
            logger.info("="*60)
            
            param_names = [
                'TaskName', 'MainController', 'Controllers', 'Assignees', 'DueDate',
                'LocalDueDate', 'Location', 'DueTime', 'SoftDueDate', 'FinalDueDate',
                'Items', 'IsRecurring', 'FreqType', 'FreqRecurrance', 'FreqInterval',
                'BusinessDayBehavior', 'Activate', 'IsReminder', 'ReminderDate', 'AddToPriorityList'
            ]
            
            logger.info("Parameters being sent to stored procedure:")
            for i, (name, value) in enumerate(zip(param_names, stored_proc_params)):
                logger.info(f"  {name}: '{value}' (type: {type(value).__name__})")
        
        try:
            # Create task using DatabaseService
            main_task_params = {
                'TaskName': stored_proc_params[0],
                'MainController': stored_proc_params[1],
                'Controllers': stored_proc_params[2],
                'Assignees': stored_proc_params[3],
                'DueDate': stored_proc_params[4],
                'LocalDueDate': stored_proc_params[5],
                'Location': stored_proc_params[6],
                'DueTime': stored_proc_params[7],
                'SoftDueDate': stored_proc_params[8],
                'FinalDueDate': stored_proc_params[9],
                'Items': stored_proc_params[10],
                'IsRecurring': stored_proc_params[11],
                'FreqType': stored_proc_params[12],
                'FreqRecurrance': stored_proc_params[13],
                'FreqInterval': stored_proc_params[14],
                'BusinessDayBehavior': stored_proc_params[15],
                'Activate': stored_proc_params[16],
                'IsReminder': stored_proc_params[17],
                'ReminderDate': stored_proc_params[18],
                'AddToPriorityList': stored_proc_params[19],
            }
            
            logger.info("Executing stored procedure...")
            new_instance_id = DatabaseService.create_task_with_priority_handling(
                main_task_params, stored_proc_params
            )
            
            if new_instance_id:
                logger.info(f"STORED PROCEDURE RESULT: Task='{params['TaskName']}', InstanceID={new_instance_id}")
                return new_instance_id
            else:
                logger.error(f"Task creation failed - no instance ID returned for task: {params.get('TaskName', 'Unknown')}")
                raise TaskCreationError('Task creation failed - no instance ID returned')
                
        except Exception as e:
            error_str = str(e)
            
            # Use ErrorHandler to format user-friendly error messages
            context = {
                'user_fullname': user_fullname,
                'task_name': params.get('TaskName', 'Unknown'),
                'operation': 'task_creation'
            }
            
            # Log the error with context
            tracking_id = error_handler.log_error(e, context, user_fullname)
            
            # Format user-friendly error message
            user_message = error_handler.format_user_error(e, context)
            
            logger.error(f"Stored procedure error [{tracking_id}]: {str(e)}. Parameters: {stored_proc_params}")
            raise TaskCreationError(user_message, 'TASK_CREATION_FAILED', {'tracking_id': tracking_id})
    
    def _convert_time_to_int(self, time_str: str) -> int:
        """Convert time string to integer format for SQL Server."""
        try:
            time_parts = time_str.split(':')
            if len(time_parts) == 2:
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                return hours * 100 + minutes
            else:
                return 19000  # Default to 7 PM
        except:
            return 19000  # Default to 7 PM
    
    def _handle_batch_task_creation(self, batch_tasks: List[str], base_params: Dict[str, Any], 
                                  user_fullname: str, user_timezone: str, debug_mode: bool = False) -> Dict[str, Any]:
        """Handle creation of multiple tasks in a batch."""
        logger.info(f"Starting batch task creation for {len(batch_tasks)} tasks")
        created_tasks = []
        failed_tasks = []
        
        for task_name in batch_tasks:
            batch_params = base_params.copy()
            batch_params['TaskName'] = task_name.strip()
            
            # Skip if task name is empty
            if not batch_params['TaskName']:
                continue
            
            try:
                # Validate batch task parameters
                ValidationService.validate_task_name(batch_params['TaskName'])
                if 'Assignees' in batch_params:
                    ValidationService.validate_assignees(batch_params['Assignees'])
                
                # Apply defaults and automatic parameters for each task
                batch_params = DateTimeService.set_default_due_date_time(batch_params, user_timezone)
                batch_params = self._set_automatic_parameters(batch_params, user_timezone)
                batch_params = self._convert_parameter_types(batch_params)
                
                # Create the task
                instance_id = self._create_single_task(batch_params, user_fullname, debug_mode)
                
                if instance_id:
                    created_tasks.append((batch_params['TaskName'], instance_id))
                    logger.debug(f"Successfully created batch task: {batch_params['TaskName']} with ID: {instance_id}")
                else:
                    failed_tasks.append((batch_params['TaskName'], "Task creation failed"))
                    
            except Exception as e:
                logger.error(f"Failed to create batch task '{batch_params['TaskName']}': {e}")
                failed_tasks.append((batch_params['TaskName'], str(e)))
        
        # Build response
        if created_tasks:
            task_list_items = []
            instance_ids = []
            for task_info in created_tasks:
                if isinstance(task_info, tuple):
                    task_name, instance_id = task_info
                    if instance_id:
                        task_list_items.append(f"• {task_name} (ID: {instance_id})")
                        instance_ids.append(instance_id)
                    else:
                        task_list_items.append(f"• {task_name}")
                else:
                    task_list_items.append(f"• {task_info}")
            
            task_list = '\n'.join(task_list_items)
            response_msg = f"I've created {len(created_tasks)} tasks:\n{task_list}"
            
            if failed_tasks:
                failed_list = '\n'.join([f"• {t}: {err}" for t, err in failed_tasks])
                response_msg += f"\n\nFailed to create {len(failed_tasks)} tasks:\n{failed_list}"
            
            response_data = {'reply': response_msg}
            
            if instance_ids:
                response_data['instance_ids'] = instance_ids
            
            if debug_mode:
                response_data['debug'] = {'created': created_tasks, 'failed': failed_tasks}
            
            return response_data
        else:
            error_msg = 'Failed to create any tasks from the batch'
            if debug_mode:
                return {'error': error_msg, 'debug': {'failed': failed_tasks}}
            else:
                raise TaskCreationError(error_msg)
    
    def _build_success_response(self, params: Dict[str, Any], instance_id: int, main_controller: str) -> Dict[str, Any]:
        """Build a conversational success response."""
        task_name = params.get('TaskName', 'the task')
        
        # Format the due date nicely
        due_date_str = ""
        if params.get('DueDate'):
            try:
                due_date = datetime.datetime.strptime(params['DueDate'], '%Y-%m-%d')
                due_date_str = due_date.strftime('%A, %b %d')
            except:
                due_date_str = params['DueDate']
        
        # Format time nicely
        time_str = ""
        if params.get('DueTime') and params['DueTime'] != '19:00':
            try:
                time_obj = datetime.datetime.strptime(params['DueTime'], '%H:%M')
                time_str = f" at {time_obj.strftime('%-I:%M %p').lower()}"
            except:
                time_str = f" at {params['DueTime']}"
        
        # Build assignee string
        assignee_str = ""
        if params.get('Assignees') and params['Assignees'] != main_controller:
            assignees_list = [a.strip() for a in params['Assignees'].split(',')]
            if len(assignees_list) == 1:
                assignee_str = f", assigned to {assignees_list[0]}"
            elif len(assignees_list) == 2:
                assignee_str = f", assigned to {assignees_list[0]} and {assignees_list[1]}"
            else:
                assignee_str = f", assigned to {', '.join(assignees_list[:-1])}, and {assignees_list[-1]}"
        
        # Build the conversational response
        if due_date_str:
            reply = f"✓ I've created '{task_name}' for {due_date_str}{time_str}{assignee_str}."
        else:
            reply = f"✓ I've created '{task_name}'{assignee_str}."
        
        # Add recurrence info if applicable
        if params.get('IsRecurring') == 1:
            freq_type = params.get('FreqType', 0)
            freq_interval = params.get('FreqInterval', 1)
            
            # Debug logging
            logger.info(f"DEBUG: Response generation - FreqType: {freq_type}, FreqInterval: {freq_interval}, FreqRecurrance: {params.get('FreqRecurrance', 0)}")
            logger.info(f"DEBUG: Full params: {params}")
            
            # Base frequency names
            freq_map = {1: 'day', 2: 'week', 3: 'month', 4: 'year'}
            base_freq = freq_map.get(freq_type, 'interval')
            
            # Format the frequency text based on interval
            if freq_interval == 1:
                # Standard frequencies
                freq_text_map = {1: 'daily', 2: 'weekly', 3: 'monthly', 4: 'yearly'}
                freq_text = freq_text_map.get(freq_type, 'recurring')
            elif freq_interval == 2 and freq_type == 2:
                # Special case for biweekly
                freq_text = 'every 2 weeks'
            else:
                # General case: "every N [units]"
                plural_s = 's' if freq_interval > 1 else ''
                freq_text = f'every {freq_interval} {base_freq}{plural_s}'
            
            reply += f" This will repeat {freq_text}."
        
        logger.info(f"API SUCCESS: Returning instance_id={instance_id}")
        
        return {
            'reply': reply,
            'instance_id': instance_id
        }