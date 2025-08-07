# Database Setup Instructions for QProcess Chatbot

## Required Stored Procedure Installation

The QProcess Chatbot requires a custom stored procedure to be installed in your QCheck database. This procedure integrates with your existing QCheck system.

## Step 1: Install the Stored Procedure

Run the following SQL script in SQL Server Management Studio while connected to your QTasks database:

```sql
-- =============================================
-- QProcess Chatbot Database Installation Script
-- =============================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateTaskThroughChatbot')
BEGIN
    DROP PROCEDURE [dbo].[QCheck_CreateTaskThroughChatbot]
END
GO

CREATE PROCEDURE [dbo].[QCheck_CreateTaskThroughChatbot]
(
	@TaskName NVARCHAR(500),
	@MainController NVARCHAR(100),
	@Controllers NVARCHAR(MAX) = '',
	@Assignees NVARCHAR(MAX),
	@DueDate DATETIME,
	@LocalDueDate DATETIME,
	@Location NVARCHAR(50),
	@DueTime INT = 0,
	@SoftDueDate DATETIME = NULL,
	@FinalDueDate DATETIME = NULL,
	@Items NVARCHAR(MAX) = '',
	@IsRecurring BIT = 0,
	@FreqType INT = 0,
	@FreqRecurrance INT = NULL,
	@FreqInterval INT = NULL,
	@BusinessDayBehavior INT = 0,
	@Activate BIT = 1,
	@IsReminder BIT = 0,
	@ReminderDate DATETIME = NULL,
	@AddToPriorityList BIT = 0,
	@NewInstanceId INT OUTPUT
)
AS
BEGIN
	DECLARE @StatusReportId INT
	DECLARE @TaskTypeId INT = NULL
	DECLARE @RowsUpdated INT
	DECLARE @NewChecklistId INT
	DECLARE @NewActiveId INT
	DECLARE @nextIteration INT
	DECLARE @nextItemIteration NVARCHAR(MAX)
	DECLARE @UniqueTaskName NVARCHAR(MAX)
	DECLARE @AppName NVARCHAR(50);
 
	SELECT @AppName = AppName from QCheck_AppSettings; 

	--Basic validation
	DECLARE @OwnerGroupId INT = (SELECT TOP 1 g.ID
		FROM QCheck_Groups g
		WHERE LTRIM(RTRIM(g.Name)) = LTRIM(RTRIM(@MainController)))
	IF @OwnerGroupId IS NULL
	BEGIN
		RAISERROR('MainController not found in QCheck_Groups. Check for spaces or case mismatch.', 16, 1)
		RETURN
	END
	
	DECLARE @UserId INT = (SELECT TOP 1 u.ID
		FROM QCheck_Users u 
		WHERE  LTRIM(RTRIM(u.FullName)) = LTRIM(RTRIM(@MainController)))

	EXEC QCheck_DuplicateNameCheck @Name = @TaskName, @UserID = @UserId, @OKToUse = @UniqueTaskName OUTPUT

	if @UniqueTaskName = 0
	BEGIN
		RAISERROR('Task with the provided name already exists and is already assigned to selected group', 16, 1)
		RETURN
	END

	--Tables to hold group IDs
	CREATE TABLE #GroupIDs(
		ID INT
	);

	CREATE TABLE #Controllers(
		Name NVARCHAR(30)
	);

	INSERT INTO #Controllers (Name) SELECT UserName.c from dbo.Util_fn_List_To_Table(@Controllers, ',') as UserName;

	CREATE TABLE #Assignees(
		Name NVARCHAR(30)
	);

	INSERT INTO #Assignees (Name) SELECT UserName.c from dbo.Util_fn_List_To_Table(@Assignees, ',') as UserName;

	CREATE TABLE #Items(
		ItemText NVARCHAR(200)
	);

	INSERT INTO #Items (ItemText) SELECT ItemText.c from dbo.Util_fn_List_To_Table(@Items, ',') as ItemText

	-- Create the task
	EXEC QCheck_CreateSimple_part1 @NewChecklistId OUTPUT, @TaskName, 1, @DueDate, @UserId, NULL, 
									   @FreqType, @RowsUpdated, @NewInstanceId OUTPUT, @NewActiveId OUTPUT, @OwnerGroupId, 
									   @Activate, @IsReminder, @ReminderDate, @AddToPriorityList, @DueTime, @Location 

	-- Add controllers
	INSERT INTO #GroupIDs (ID) SELECT DISTINCT ID
		FROM QCheck_Groups
		WHERE Name IN (SELECT Name fROM #Controllers)

	DECLARE groupCursor CURSOR FOR SELECT DISTINCT ID FROM #GroupIDs

	OPEN groupCursor
	FETCH FROM groupCursor INTO @nextIteration

	WHILE @@FETCH_STATUS = 0
	BEGIN
		EXEC QCheck_AddManager @nextIteration, @NewChecklistId
		FETCH FROM groupCursor INTO @nextIteration
	END	

	CLOSE groupCursor
	DEALLOCATE groupCursor
	SET @nextIteration = 0

	-- Add assignees
	INSERT INTO #GroupIDs (ID) SELECT DISTINCT ID
		FROM QCheck_Groups
		WHERE Name IN (SELECT Name fROM #Assignees)

	DECLARE assigneeCursor CURSOR FOR SELECT DISTINCT ID FROM #GroupIDs

	OPEN assigneeCursor
	FETCH FROM assigneeCursor INTO @nextIteration

	WHILE @@FETCH_STATUS = 0
	BEGIN
		EXEC QCheck_AddAssignedTo @NewInstanceID, @nextIteration, 0
		FETCH FROM assigneeCursor INTO @nextIteration
	END	

	CLOSE assigneeCursor
	DEALLOCATE assigneeCursor
	SET @nextIteration = 0

	-- Add items
	DECLARE itemsCursor CURSOR FOR SELECT DISTINCT ItemText FROM #Items

	OPEN itemsCursor
	FETCH FROM itemsCursor INTO @nextItemIteration

	WHILE @@FETCH_STATUS = 0
	BEGIN
		EXEC QCheck_AddItem @NewChecklistId,null,1,@nextItemIteration, ' ', 0
		FETCH FROM itemsCursor INTO @nextItemIteration
	END	

	CLOSE itemsCursor
	DEALLOCATE itemsCursor
	SET @nextItemIteration = ''
	
	-- Set up recurring schedule if needed
	IF @FreqType > 0 
	BEGIN
		EXEC QCheck_UpdateSchedule_part1 
				@InstanceID = @NewInstanceId, 
				@firstDueDate = @LocalDueDate,
				@lastDueDate = @FinalDueDate,
				@freqType = @FreqType,
				@freqRecurrance = @FreqRecurrance,
				@freqInterval = @FreqInterval,
				@dueTime = @DueTime,
				@busDayBehavior = @BusinessDayBehavior,
				@PrevFreqType = 0,
				@RowsUpdated = 0,
				@Activate = @Activate,
				@TimeZone = @Location

		EXEC QCheck_UpdateSchedule_Part2 @NewInstanceId, @FreqType, @Activate
	END
    
END
GO

PRINT 'QCheck_CreateTaskThroughChatbot stored procedure created successfully'
GO
```

## Step 2: Verify Installation

Run this verification script to ensure all prerequisites are met:

```sql
PRINT 'Checking QProcess Chatbot Prerequisites...'
PRINT ''

-- Check for required procedures
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateTaskThroughChatbot')
    PRINT '[OK] QCheck_CreateTaskThroughChatbot installed'
ELSE
    PRINT '[ERROR] QCheck_CreateTaskThroughChatbot NOT FOUND'

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateSimple_part1')
    PRINT '[OK] QCheck_CreateSimple_part1 exists'
ELSE
    PRINT '[ERROR] QCheck_CreateSimple_part1 NOT FOUND'

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_AddManager')
    PRINT '[OK] QCheck_AddManager exists'
ELSE
    PRINT '[ERROR] QCheck_AddManager NOT FOUND'

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_AddAssignedTo')
    PRINT '[OK] QCheck_AddAssignedTo exists'
ELSE
    PRINT '[ERROR] QCheck_AddAssignedTo NOT FOUND'

-- Check for required tables
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_Groups')
    PRINT '[OK] QCheck_Groups table exists'
ELSE
    PRINT '[ERROR] QCheck_Groups table NOT FOUND'

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_Users')
    PRINT '[OK] QCheck_Users table exists'
ELSE
    PRINT '[ERROR] QCheck_Users table NOT FOUND'

-- Check for configured users
DECLARE @ConfiguredUsers INT = (
    SELECT COUNT(DISTINCT u.FullName)
    FROM QCheck_Users u 
    INNER JOIN QCheck_Groups g ON u.FullName = g.Name 
    WHERE u.isdeleted <> 1
)

PRINT ''
PRINT 'Configured users for chatbot: ' + CAST(@ConfiguredUsers AS VARCHAR)
PRINT '(Users must exist in both QCheck_Users and QCheck_Groups with matching names)'
```

## Prerequisites

Your QCheck database must have these existing stored procedures:
- `QCheck_CreateSimple_part1`
- `QCheck_DuplicateNameCheck`
- `QCheck_AddManager`
- `QCheck_AddAssignedTo`
- `QCheck_AddItem`
- `QCheck_UpdateSchedule_part1`
- `QCheck_UpdateSchedule_Part2`
- `Util_fn_List_To_Table`

## Troubleshooting

### Error: "MainController not found in QCheck_Groups"
- Ensure the user exists in both `QCheck_Users` and `QCheck_Groups` tables
- Check for trailing spaces or case mismatches in the group name

### Error: "Task with the provided name already exists"
- The task name must be unique for the specified group
- Try adding a timestamp or unique identifier to the task name

### No users appearing in dropdown
- Run the verification script above to check configured users
- Users must exist in both `QCheck_Users` and `QCheck_Groups` with matching names

## Support

For issues or questions about the stored procedure installation, please refer to:
- The main README.md for API usage examples
- DATABASE_STRUCTURE.md for complete schema documentation