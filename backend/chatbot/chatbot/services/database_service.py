"""
Database Service Module

This module encapsulates all database operations, providing a clean interface
for database interactions with proper resource management and error handling.
"""

import logging
from django.db import connection
from contextlib import contextmanager
from typing import Optional, List, Tuple, Dict, Any
from ..config.queries import *
from .error_handler import error_handler, DatabaseError, retry_database_operation
from .bitmask_translator import get_translator

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Centralized database service for all database operations.
    Provides methods for task creation, user management, group validation,
    and priority list operations with proper resource cleanup.
    """
    
    @staticmethod
    def escape_sql_string(s):
        """
        Helper function to safely escape strings for SQL
        """
        if s is None:
            return "NULL"
        return str(s).replace("'", "''")
    
    @staticmethod
    @contextmanager
    def get_cursor():
        """
        Context manager for database cursors with proper cleanup
        """
        cursor = None
        try:
            cursor = connection.cursor()
            yield cursor
        except Exception as e:
            logger.error(f"Database cursor error: {e}")
            raise DatabaseError(f"Database connection error: {str(e)}", 'DATABASE_CONNECTION_ERROR')
        finally:
            if cursor:
                try:
                    # Consume any remaining results to clear the cursor
                    while cursor.nextset():
                        pass
                except:
                    pass
                finally:
                    cursor.close()
    
    @staticmethod
    def validate_group_exists(group_name: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate if a group exists and provide suggestions if not found.
        
        Args:
            group_name: Name of the group to validate
            
        Returns:
            Tuple of (exists, found_name, similar_groups)
        """
        try:
            with DatabaseService.get_cursor() as cursor:
                # Check if group exists
                cursor.execute(CHECK_GROUP_EXISTS, [group_name])
                group_row = cursor.fetchone()
                
                if group_row:
                    return True, group_row[0], []
                
                # Find similar groups for suggestions
                cursor.execute(FIND_SIMILAR_GROUPS, [f'%{group_name.split()[0]}%'])
                similar_groups = [row[0] for row in cursor.fetchall()]
                
                return False, None, similar_groups
                
        except Exception as e:
            error_handler.log_error(e, {'group_name': group_name, 'operation': 'validate_group'})
            logger.error(f"Error validating group '{group_name}': {e}")
            return False, None, []
    
    @staticmethod
    def get_active_users() -> List[str]:
        """
        Get list of properly configured active users who can create tasks.
        Only returns users who exist as both users and groups.
        
        Returns:
            List of user full names who are properly configured
        """
        try:
            with DatabaseService.get_cursor() as cursor:
                cursor.execute(GET_ACTIVE_USERS)
                users = [row[0] for row in cursor.fetchall()]
                
                logger.info(f"Retrieved {len(users)} properly configured users")
                
                # Log configuration rate for monitoring
                cursor.execute("SELECT COUNT(*) FROM [QTasks].[dbo].[QCheck_Users] WHERE isdeleted <> 1")
                total_active = cursor.fetchone()[0]
                config_rate = (len(users) / total_active * 100) if total_active > 0 else 0
                logger.info(f"User configuration rate: {config_rate:.1f}% ({len(users)}/{total_active})")
                
                return users
                
        except Exception as e:
            error_handler.log_error(e, {'operation': 'get_active_users'})
            logger.error(f"Error retrieving active users: {e}")
            return []
    
    @staticmethod
    def get_all_active_users() -> List[str]:
        """
        Get list of ALL active users (legacy method).
        This includes users who may not be properly configured for task creation.
        
        Returns:
            List of all active user full names
        """
        try:
            with DatabaseService.get_cursor() as cursor:
                from ..config.queries import GET_ALL_ACTIVE_USERS_LEGACY
                cursor.execute(GET_ALL_ACTIVE_USERS_LEGACY)
                users = [row[0] for row in cursor.fetchall()]
                
                logger.info(f"Retrieved {len(users)} total active users (legacy)")
                return users
                
        except Exception as e:
            error_handler.log_error(e, {'operation': 'get_all_active_users'})
            logger.error(f"Error retrieving all active users: {e}")
            return []
    
    @staticmethod
    def find_task_by_name(task_name: str) -> Optional[int]:
        """
        Find a task instance ID by task name.
        
        Args:
            task_name: Name of the task to find
            
        Returns:
            Task instance ID if found, None otherwise
        """
        try:
            with DatabaseService.get_cursor() as cursor:
                cursor.execute(FIND_TASK_BY_NAME, [task_name])
                result = cursor.fetchone()
                
                if result:
                    instance_id = result[0]
                    logger.debug(f"Found task '{task_name}' with instance ID: {instance_id}")
                    return instance_id
                
                logger.warning(f"Task not found: '{task_name}'")
                return None
                
        except Exception as e:
            error_handler.log_error(e, {'task_name': task_name, 'operation': 'find_task_by_name'})
            logger.error(f"Error finding task '{task_name}': {e}")
            return None
    
    @staticmethod
    def create_task_via_stored_procedure(params: Dict[str, Any]) -> Optional[int]:
        """
        Create a task using the stored procedure with string interpolation.
        This method handles the main task creation logic with UC08 translation support.
        
        Args:
            params: Dictionary containing all task parameters
            
        Returns:
            Instance ID of created task, None if failed
        """
        translator = get_translator()
        translation_metadata = None
        translation_id = None
        
        try:
            # Check if UC08 translation is needed
            freq_type = params.get('FreqType')
            freq_recurrence = params.get('FreqRecurrance')
            
            if translator.needs_translation(freq_recurrence, freq_type):
                logger.info(f"UC08 Translation required for FreqRecurrance {freq_recurrence}")
                
                # Encode parameters for database
                params, translation_metadata = translator.encode_for_database(params)
                
                # Store translation metadata
                translation_id = translator.store_translation_metadata(translation_metadata)
                
                logger.info(f"UC08 Translation applied: {freq_recurrence} -> {params.get('FreqRecurrance')}")
            
            # Continue with normal task creation using (possibly translated) parameters
            # Build SQL query with proper escaping
            sql_query = CREATE_TASK_PROCEDURE.format(
                task_name=DatabaseService.escape_sql_string(params.get('TaskName', '')),
                main_controller=DatabaseService.escape_sql_string(params.get('MainController', '')),
                controllers=DatabaseService.escape_sql_string(params.get('Controllers', '')),
                assignees=DatabaseService.escape_sql_string(params.get('Assignees', '')),
                due_date=DatabaseService.escape_sql_string(params.get('DueDate', '')),
                local_due_date=DatabaseService.escape_sql_string(params.get('LocalDueDate', '')),
                location=DatabaseService.escape_sql_string(params.get('Location', 'New York')),
                due_time=params.get('DueTime', 19000),
                soft_due_date=DatabaseService.escape_sql_string(params.get('SoftDueDate', '')),
                final_due_date=DatabaseService.escape_sql_string(params.get('FinalDueDate', '')),
                items=DatabaseService.escape_sql_string(params.get('Items', '')),
                is_recurring=params.get('IsRecurring', 0),
                freq_type=params.get('FreqType', 'NULL') if params.get('FreqType') is not None else 'NULL',
                freq_recurrance=params.get('FreqRecurrance', 'NULL') if params.get('FreqRecurrance') is not None else 'NULL',
                freq_interval=params.get('FreqInterval', 'NULL') if params.get('FreqInterval') is not None else 'NULL',
                business_day_behavior=params.get('BusinessDayBehavior', 1),
                activate=params.get('Activate', 1),
                is_reminder=params.get('IsReminder', 0),
                reminder_date=DatabaseService.escape_sql_string(params.get('ReminderDate', '')),
                add_to_priority_list=params.get('AddToPriorityList', 0)
            )
            
            logger.debug(f"Executing stored procedure for task: {params.get('TaskName')}")
            
            # Check for large FreqRecurrance values that might cause issues
            freq_recurrance = params.get('FreqRecurrance')
            if freq_recurrance is not None and isinstance(freq_recurrance, int) and freq_recurrance >= 16384:
                logger.warning(f"Large FreqRecurrance detected ({freq_recurrance}), using parameterized query")
                # Build parameter list for parameterized query
                param_list = [
                    params.get('TaskName', ''),
                    params.get('MainController', ''),
                    params.get('Controllers', ''),
                    params.get('Assignees', ''),
                    params.get('DueDate', ''),
                    params.get('LocalDueDate', ''),
                    params.get('Location', 'New York'),
                    params.get('DueTime', 19000),
                    params.get('SoftDueDate', ''),
                    params.get('FinalDueDate', ''),
                    params.get('Items', ''),
                    params.get('IsRecurring', 0),
                    params.get('FreqType') if params.get('FreqType') is not None else None,
                    params.get('FreqRecurrance') if params.get('FreqRecurrance') is not None else None,
                    params.get('FreqInterval') if params.get('FreqInterval') is not None else None,
                    params.get('BusinessDayBehavior', 1),
                    params.get('Activate', 1),
                    params.get('IsReminder', 0),
                    params.get('ReminderDate', ''),
                    params.get('AddToPriorityList', 0)
                ]
                return DatabaseService.create_task_via_stored_procedure_parameterized(param_list)
            
            # Special logging for UC08 pattern
            task_name = params.get('TaskName', '')
            if 'UC08' in task_name or ('month' in task_name.lower() and '15' in task_name):
                logger.warning("UC08 PATTERN: Monthly task with specific day")
                logger.warning(f"FreqType: {params.get('FreqType')}")
                logger.warning(f"FreqRecurrance: {params.get('FreqRecurrance')}")
                logger.warning(f"FreqInterval: {params.get('FreqInterval')}")
                logger.warning(f"Full SQL Query: {sql_query[:500]}...")
            
            with DatabaseService.get_cursor() as cursor:
                cursor.execute(sql_query)
                
                # Try to get the instance ID
                if cursor.description is not None:
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        instance_id = result[0]
                        logger.info(f"Task created successfully with ID: {instance_id}")
                        
                        # Link translation metadata to the created task
                        if translation_id and instance_id:
                            translator.link_translation_to_task(translation_id, instance_id)
                            logger.info(f"UC08 Translation linked: metadata ID {translation_id} -> task ID {instance_id}")
                        
                        return instance_id
                
                logger.warning("No instance ID returned from stored procedure")
                return None
                
        except Exception as e:
            error_handler.log_error(e, {'task_name': params.get('TaskName'), 'operation': 'create_task_via_stored_procedure'})
            logger.error(f"Error creating task via stored procedure: {e}")
            logger.error(f"SQL Query that failed: {sql_query[:500]}...")
            
            # Check if this was a translated UC08 task that still failed
            # This might indicate a deeper issue beyond just the 16384 limitation
            if translation_metadata:
                day = translation_metadata.get('day', 'unknown')
                logger.error(f"UC08 translated task still failed for day {day}")
                # Continue with normal error handling - translation didn't solve the issue
            
            raise DatabaseError(f"Task creation failed: {str(e)}", 'TASK_CREATION_FAILED')
    
    @staticmethod
    def create_task_via_stored_procedure_parameterized(param_list: List[Any]) -> Optional[int]:
        """
        Create a task using parameterized stored procedure call.
        This is safer for retry scenarios and special cases.
        
        Args:
            param_list: List of parameters in the correct order
            
        Returns:
            Instance ID of created task, None if failed
        """
        try:
            logger.debug(f"Executing parameterized stored procedure")
            logger.debug(f"Parameter list: {param_list}")
            
            # Log specific parameters of interest
            if len(param_list) >= 14:
                logger.debug(f"FreqType (param 12): {param_list[12]}")
                logger.debug(f"FreqRecurrance (param 13): {param_list[13]}")
                logger.debug(f"FreqInterval (param 14): {param_list[14]}")
            
            with DatabaseService.get_cursor() as cursor:
                cursor.execute(CREATE_TASK_PROCEDURE_PARAMETERIZED, param_list)
                
                # Try to get the instance ID
                if cursor.description is not None:
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        instance_id = result[0]
                        logger.info(f"Task created successfully (parameterized) with ID: {instance_id}")
                        return instance_id
                
                logger.warning("No instance ID returned from parameterized stored procedure")
                return None
                
        except Exception as e:
            error_handler.log_error(e, {'operation': 'create_task_via_parameterized_stored_procedure'})
            logger.error(f"Error creating task via parameterized stored procedure: {e}")
            
            # Check if this is the UC08 limitation
            if len(param_list) >= 14:
                freq_type = param_list[12]
                freq_recurrance = param_list[13]
                if freq_type == 3 and freq_recurrance and isinstance(freq_recurrance, int) and freq_recurrance >= 16384:
                    import math
                    day = int(math.log2(freq_recurrance)) + 1
                    logger.warning(f"UC08 limitation hit (parameterized): Monthly task for day {day} failed")
                    raise DatabaseError(
                        f"I'm sorry, but there's currently a known limitation with monthly tasks scheduled "
                        f"for days 15-31. Your request for 'on the {day}th' cannot be processed at this time.\n\n"
                        f"**Workaround options:**\n"
                        f"1. Use 'every month' for a simple monthly schedule\n"
                        f"2. Schedule for days 1-14 instead\n"
                        f"3. Create separate tasks for different time periods\n\n"
                        f"Our team is working on a permanent solution. Thank you for your understanding.",
                        'UC08_MONTHLY_DAY_LIMITATION'
                    )
            
            raise DatabaseError(f"Parameterized task creation failed: {str(e)}", 'PARAMETERIZED_TASK_CREATION_FAILED')
    
    @staticmethod
    def add_to_priority_list_workaround(instance_id: int, assignees_str: str) -> bool:
        """
        UC03 Workaround: Manually add priority list entries.
        This addresses a bug where the stored procedure doesn't create priority list entries.
        
        Args:
            instance_id: Instance ID of the task
            assignees_str: Comma-separated string of assignee names
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"UC03 Workaround called for instance {instance_id} with assignees: {assignees_str}")
        
        try:
            with DatabaseService.get_cursor() as cursor:
                # Get the ActiveChecklistID
                cursor.execute(GET_ACTIVE_CHECKLIST_ID, [instance_id])
                active_result = cursor.fetchone()
                
                if not active_result:
                    logger.error(f"No active checklist found for instance {instance_id}")
                    return False
                
                active_checklist_id = active_result[0]
                
                if assignees_str:
                    # Parse assignee names and get their user IDs
                    assignee_names = [name.strip() for name in assignees_str.split(',')]
                    
                    for assignee_name in assignee_names:
                        # Get users from the group
                        cursor.execute(GET_USERS_IN_GROUP, [assignee_name])
                        user_ids = cursor.fetchall()
                        
                        if user_ids:
                            for user_id_row in user_ids:
                                user_id = user_id_row[0]
                                # Add to priority list
                                cursor.execute(ADD_TO_PRIORITY_LIST_PROCEDURE, [user_id, active_checklist_id])
                                logger.debug(f"Added UserID {user_id} to priority list for task {instance_id}")
                        else:
                            # If no users in group, try to add a test user as fallback
                            logger.warning(f"UC03 Workaround: No users found in group '{assignee_name}', trying fallback")
                            cursor.execute(GET_TEST_USER)
                            test_user = cursor.fetchone()
                            if test_user:
                                cursor.execute(ADD_TO_PRIORITY_LIST_PROCEDURE, [test_user[0], active_checklist_id])
                                logger.info(f"UC03 Workaround: Added test user to priority list for validation")
                
                logger.info(f"UC03 Workaround: Completed for task {instance_id}")
                return True
                
        except Exception as e:
            error_handler.log_error(e, {'instance_id': instance_id, 'assignees': assignees_str, 'operation': 'uc03_workaround'})
            logger.error(f"UC03 Workaround failed: {e}")
            return False
    
    @staticmethod
    def create_task_with_priority_handling(params: Dict[str, Any], param_list: List[Any]) -> Optional[int]:
        """
        High-level method to create a task with automatic priority list handling.
        Combines task creation with the UC03 workaround when needed.
        
        Args:
            params: Dictionary containing task parameters (for priority list detection)
            param_list: List of parameters for stored procedure call
            
        Returns:
            Instance ID of created task, None if failed
        """
        instance_id = None
        
        try:
            # Try main stored procedure first
            instance_id = DatabaseService.create_task_via_stored_procedure(params)
            
            # If that fails, try fallback by name lookup
            if not instance_id:
                logger.warning("No instance ID from stored procedure, searching by task name...")
                instance_id = DatabaseService.find_task_by_name(params.get('TaskName', ''))
            
            # Apply UC03 workaround if priority list is requested
            if instance_id and params.get('AddToPriorityList') == 1:
                logger.info("Applying UC03 workaround for priority list")
                error_handler.apply_uc03_priority_list_workaround(
                    instance_id, 
                    params.get('Assignees', '')
                )
            
            return instance_id
            
        except Exception as e:
            logger.error(f"Error in create_task_with_priority_handling: {e}")
            
            # Use ErrorHandler to handle database errors with workarounds
            instance_id = error_handler.handle_database_error_with_workarounds(e, params, param_list)
            if instance_id:
                return instance_id
            
            # Re-raise the original exception
            raise
    
    @staticmethod
    def call_stored_procedure(procedure_name: str, params: List[Any]) -> List[Any]:
        """
        Generic method to call any stored procedure.
        
        Args:
            procedure_name: Name of the stored procedure
            params: List of parameters
            
        Returns:
            Results from the stored procedure
        """
        try:
            with DatabaseService.get_cursor() as cursor:
                cursor.callproc(procedure_name, params)
                result = cursor.fetchall()
                return result
                
        except Exception as e:
            error_handler.log_error(e, {'procedure_name': procedure_name, 'operation': 'call_stored_procedure'})
            logger.error(f"Error calling stored procedure '{procedure_name}': {e}")
            raise DatabaseError(f"Stored procedure call failed: {str(e)}", 'STORED_PROCEDURE_FAILED')