"""
SQL Query Templates for Database Operations

This module contains all SQL query templates used throughout the application.
Organized by functionality for easy maintenance and reuse.
"""

# Group validation queries
CHECK_GROUP_EXISTS = """
    SELECT Name FROM [QTasks3].[dbo].[QCheck_Groups] WHERE Name=%s
"""

FIND_SIMILAR_GROUPS = """
    SELECT TOP 5 Name 
    FROM [QTasks3].[dbo].[QCheck_Groups] 
    WHERE Name LIKE %s 
    ORDER BY Name
"""

# User queries
GET_ACTIVE_USERS = """
    -- Only return users who are properly configured for task creation
    -- These users exist in both QCheck_Users and QCheck_Groups tables
    SELECT DISTINCT u.FullName
    FROM [QTasks3].[dbo].[QCheck_Users] u
    INNER JOIN [QTasks3].[dbo].[QCheck_Groups] g ON u.FullName = g.Name
    WHERE u.isdeleted <> 1
    ORDER BY u.FullName
"""

# Legacy query - shows all active users (kept for reference)
GET_ALL_ACTIVE_USERS_LEGACY = """
    SELECT FullName 
    FROM [QTasks3].[dbo].[QCheck_Users] 
    WHERE isdeleted <> 1
    ORDER BY FullName
"""

# Task lookup queries
FIND_TASK_BY_NAME = """
    SELECT TOP 1 ci.ID 
    FROM QCheck_ChecklistInstances ci
    INNER JOIN QCheck_Checklists c ON ci.ChecklistID = c.ID
    WHERE c.Name = %s
    ORDER BY ci.ID DESC
"""

# Priority list workaround queries
GET_ACTIVE_CHECKLIST_ID = """
    SELECT ID FROM QCheck_ActiveChecklists 
    WHERE InstanceID = %s
"""

GET_USERS_IN_GROUP = """
    SELECT DISTINCT u.ID
    FROM QCheck_Users u
    INNER JOIN QCheck_GroupMembership gm ON u.ID = gm.UserID
    INNER JOIN QCheck_Groups g ON gm.GroupID = g.ID
    WHERE g.Name = %s AND u.isdeleted = 0
"""

GET_TEST_USER = """
    SELECT TOP 1 ID FROM QCheck_Users 
    WHERE FullName = 'Test User' AND isdeleted = 0
"""

# Stored procedure calls
CREATE_TASK_PROCEDURE = """
    SET NOCOUNT ON;
    DECLARE @NewInstanceId INT;
    EXEC [QTasks3].[dbo].[QCheck_CreateTaskThroughChatbot]
        @TaskName=N'{task_name}',
        @MainController=N'{main_controller}',
        @Controllers=N'{controllers}',
        @Assignees=N'{assignees}',
        @DueDate='{due_date}',
        @LocalDueDate='{local_due_date}',
        @Location=N'{location}',
        @DueTime={due_time},
        @SoftDueDate='{soft_due_date}',
        @FinalDueDate='{final_due_date}',
        @Items=N'{items}',
        @IsRecurring={is_recurring},
        @FreqType={freq_type},
        @FreqRecurrance={freq_recurrance},
        @FreqInterval={freq_interval},
        @BusinessDayBehavior={business_day_behavior},
        @Activate={activate},
        @IsReminder={is_reminder},
        @ReminderDate='{reminder_date}',
        @AddToPriorityList={add_to_priority_list},
        @NewInstanceId=@NewInstanceId OUTPUT;
    SELECT @NewInstanceId AS CreatedInstanceID;
"""

ADD_TO_PRIORITY_LIST_PROCEDURE = """
    EXEC PriorityList_AddTask 
        @UserID = %s, 
        @ActiveChecklistID = %s
"""

# Parameterized stored procedure call (safer for retry scenarios)
CREATE_TASK_PROCEDURE_PARAMETERIZED = """
    SET NOCOUNT ON;
    DECLARE @NewInstanceId INT;
    EXEC [QTasks3].[dbo].[QCheck_CreateTaskThroughChatbot]
        @TaskName=%s,
        @MainController=%s,
        @Controllers=%s,
        @Assignees=%s,
        @DueDate=%s,
        @LocalDueDate=%s,
        @Location=%s,
        @DueTime=%s,
        @SoftDueDate=%s,
        @FinalDueDate=%s,
        @Items=%s,
        @IsRecurring=%s,
        @FreqType=%s,
        @FreqRecurrance=%s,
        @FreqInterval=%s,
        @BusinessDayBehavior=%s,
        @Activate=%s,
        @IsReminder=%s,
        @ReminderDate=%s,
        @AddToPriorityList=%s,
        @NewInstanceId=@NewInstanceId OUTPUT;
    SELECT @NewInstanceId AS CreatedInstanceID;
"""