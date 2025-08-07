-- =============================================
-- QProcess Chatbot Installation Verification Script
-- =============================================
-- This script verifies that all required components are installed correctly
-- Run this after installing the stored procedure to ensure everything is ready
-- =============================================

PRINT '=========================================='
PRINT 'QProcess Chatbot Installation Verification'
PRINT '=========================================='
PRINT ''

DECLARE @ErrorCount INT = 0
DECLARE @WarningCount INT = 0

-- 1. Check for main stored procedure
PRINT '1. Checking for QCheck_CreateTaskThroughChatbot...'
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateTaskThroughChatbot')
BEGIN
    PRINT '   [OK] QCheck_CreateTaskThroughChatbot exists'
END
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_CreateTaskThroughChatbot NOT FOUND - Run install_stored_procedure.sql first'
    SET @ErrorCount = @ErrorCount + 1
END
PRINT ''

-- 2. Check for required dependency procedures
PRINT '2. Checking for required dependency procedures...'

-- QCheck_CreateSimple_part1
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_CreateSimple_part1')
    PRINT '   [OK] QCheck_CreateSimple_part1 exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_CreateSimple_part1 NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_DuplicateNameCheck
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_DuplicateNameCheck')
    PRINT '   [OK] QCheck_DuplicateNameCheck exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_DuplicateNameCheck NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_AddManager
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_AddManager')
    PRINT '   [OK] QCheck_AddManager exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_AddManager NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_AddAssignedTo
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_AddAssignedTo')
    PRINT '   [OK] QCheck_AddAssignedTo exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_AddAssignedTo NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_AddItem
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_AddItem')
    PRINT '   [OK] QCheck_AddItem exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_AddItem NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_UpdateSchedule_part1
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_UpdateSchedule_part1')
    PRINT '   [OK] QCheck_UpdateSchedule_part1 exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_UpdateSchedule_part1 NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_UpdateSchedule_Part2
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'QCheck_UpdateSchedule_Part2')
    PRINT '   [OK] QCheck_UpdateSchedule_Part2 exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_UpdateSchedule_Part2 NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- Util_fn_List_To_Table
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Util_fn_List_To_Table]') AND type IN (N'FN', N'IF', N'TF', N'FS', N'FT'))
    PRINT '   [OK] Util_fn_List_To_Table function exists'
ELSE
BEGIN
    PRINT '   [ERROR] Util_fn_List_To_Table function NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

PRINT ''

-- 3. Check for required tables
PRINT '3. Checking for required tables...'

-- QCheck_Groups
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_Groups')
BEGIN
    DECLARE @GroupCount INT = (SELECT COUNT(*) FROM QCheck_Groups)
    PRINT '   [OK] QCheck_Groups exists (' + CAST(@GroupCount AS VARCHAR) + ' groups found)'
END
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_Groups table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_Users
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_Users')
BEGIN
    DECLARE @UserCount INT = (SELECT COUNT(*) FROM QCheck_Users WHERE isdeleted <> 1)
    PRINT '   [OK] QCheck_Users exists (' + CAST(@UserCount AS VARCHAR) + ' active users found)'
END
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_Users table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_Checklists
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_Checklists')
    PRINT '   [OK] QCheck_Checklists exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_Checklists table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_ChecklistInstances
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_ChecklistInstances')
    PRINT '   [OK] QCheck_ChecklistInstances exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_ChecklistInstances table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_ActiveChecklists
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_ActiveChecklists')
    PRINT '   [OK] QCheck_ActiveChecklists exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_ActiveChecklists table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_Assignments
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_Assignments')
    PRINT '   [OK] QCheck_Assignments exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_Assignments table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_ChecklistManagers
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_ChecklistManagers')
    PRINT '   [OK] QCheck_ChecklistManagers exists'
ELSE
BEGIN
    PRINT '   [ERROR] QCheck_ChecklistManagers table NOT FOUND'
    SET @ErrorCount = @ErrorCount + 1
END

-- QCheck_AppSettings
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'QCheck_AppSettings')
    PRINT '   [OK] QCheck_AppSettings exists'
ELSE
BEGIN
    PRINT '   [WARNING] QCheck_AppSettings table not found (may not be required)'
    SET @WarningCount = @WarningCount + 1
END

PRINT ''

-- 4. Check for users configured for chatbot
PRINT '4. Checking for users configured for chatbot...'
DECLARE @ConfiguredUsers INT = (
    SELECT COUNT(DISTINCT u.FullName)
    FROM QCheck_Users u 
    INNER JOIN QCheck_Groups g ON u.FullName = g.Name 
    WHERE u.isdeleted <> 1
)
IF @ConfiguredUsers > 0
BEGIN
    PRINT '   [OK] ' + CAST(@ConfiguredUsers AS VARCHAR) + ' users are configured for chatbot use'
    PRINT '   (Users must exist in both QCheck_Users and QCheck_Groups with matching names)'
END
ELSE
BEGIN
    PRINT '   [WARNING] No users configured for chatbot use'
    PRINT '   Users must exist in both QCheck_Users and QCheck_Groups with matching names'
    SET @WarningCount = @WarningCount + 1
END

PRINT ''

-- 5. Sample query to show configured users
IF @ConfiguredUsers > 0
BEGIN
    PRINT '5. Sample of configured users (top 5):'
    SELECT TOP 5 
        u.FullName as [User Name],
        u.Email as [Email],
        g.Name as [Group Name]
    FROM QCheck_Users u 
    INNER JOIN QCheck_Groups g ON u.FullName = g.Name 
    WHERE u.isdeleted <> 1
    ORDER BY u.FullName
END

PRINT ''
PRINT '=========================================='
PRINT 'Verification Summary:'
PRINT '=========================================='

IF @ErrorCount = 0 AND @WarningCount = 0
BEGIN
    PRINT 'STATUS: READY - All components installed successfully!'
    PRINT 'The chatbot integration is ready to use.'
END
ELSE IF @ErrorCount = 0 AND @WarningCount > 0
BEGIN
    PRINT 'STATUS: READY WITH WARNINGS'
    PRINT 'Errors: ' + CAST(@ErrorCount AS VARCHAR)
    PRINT 'Warnings: ' + CAST(@WarningCount AS VARCHAR)
    PRINT 'The chatbot can run but review warnings above.'
END
ELSE
BEGIN
    PRINT 'STATUS: NOT READY'
    PRINT 'Errors: ' + CAST(@ErrorCount AS VARCHAR)
    PRINT 'Warnings: ' + CAST(@WarningCount AS VARCHAR)
    PRINT 'Please resolve errors before using the chatbot.'
END

PRINT '==========================================';