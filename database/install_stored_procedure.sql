-- =============================================
-- QProcess Chatbot Database Installation Script
-- =============================================
-- This script creates the stored procedure required for the chatbot integration
-- 
-- Prerequisites:
-- 1. QCheck database with existing procedures:
--    - QCheck_CreateSimple_part1
--    - QCheck_AddManager
--    - QCheck_AddAssignedTo
--    - QCheck_AddItem
--    - QCheck_UpdateSchedule_part1
--    - QCheck_UpdateSchedule_Part2
--    - QCheck_DuplicateNameCheck
--    - Util_fn_List_To_Table
-- 
-- 2. Required tables:
--    - QCheck_Groups
--    - QCheck_Users
--    - QCheck_Checklists
--    - QCheck_ChecklistInstances
--    - QCheck_ActiveChecklists
--    - QCheck_Assignments
--    - QCheck_ChecklistManagers
-- =============================================

-- Drop existing procedure if it exists
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateTaskThroughChatbot')
BEGIN
    DROP PROCEDURE [dbo].[QCheck_CreateTaskThroughChatbot]
END
GO

-- Create the stored procedure
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


--Basic validation here

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

--This table will be passed around to hold group IDs for either controllers or assignees

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


EXEC QCheck_CreateSimple_part1 @NewChecklistId OUTPUT, @TaskName, 1, @DueDate, @UserId, NULL, 
								   @FreqType, @RowsUpdated, @NewInstanceId OUTPUT, @NewActiveId OUTPUT, @OwnerGroupId, 
								   @Activate, @IsReminder, @ReminderDate, @AddToPriorityList, @DueTime, @Location 


--First we add controllers

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


--Second we add more assignees

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

	--Finally we add all items

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

-- Verify the procedure was created successfully
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateTaskThroughChatbot')
BEGIN
    PRINT 'SUCCESS: QCheck_CreateTaskThroughChatbot stored procedure created successfully'
END
ELSE
BEGIN
    PRINT 'ERROR: Failed to create QCheck_CreateTaskThroughChatbot stored procedure'
END
GO