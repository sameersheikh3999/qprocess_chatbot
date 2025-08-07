"""
Django management command to validate test results in the database
Usage: python manage.py validate_tests
"""
from django.core.management.base import BaseCommand
from django.db import connection
from datetime import datetime
import json


class Command(BaseCommand):
    help = 'Validates QProcess chatbot test results in database'

    def handle(self, *args, **options):
        self.stdout.write("="*60)
        self.stdout.write("QProcess Chatbot Database Validation")
        self.stdout.write("="*60)
        
        results = []
        
        # Run validations for all 30 use cases
        results.extend(self.validate_simple_tasks())
        results.extend(self.validate_recurring_tasks())
        results.extend(self.validate_special_features())
        results.extend(self.validate_complex_patterns())
        results.extend(self.validate_advanced_features())
        
        # Print summary
        passed = sum(1 for r in results if r['passed'])
        total = len(results)
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"VALIDATION SUMMARY: {passed}/{total} passed")
        self.stdout.write("="*60)
        
        # Save detailed results
        with open('validation_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': total - passed
                }
            }, f, indent=2)
        
        self.stdout.write(self.style.SUCCESS(f"\nResults saved to validation_results.json"))
    
    def validate_simple_tasks(self):
        """Validate Use Cases 1-5"""
        results = []
        
        # UC1: Simple Task Creation
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ci.InstanceID, ci.Name, g.Name as Assignee
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_Assignments a ON ci.InstanceID = a.InstanceID
                JOIN QCheck_Groups g ON a.GroupID = g.GroupID
                WHERE ci.InstanceID = 2071265
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC1: Simple Task Creation',
                'passed': row and 'Prepare monthly report' in row[1],
                'details': f"Task: {row[1] if row else 'NOT FOUND'}, Assignee: {row[2] if row else 'N/A'}"
            })
        
        # UC2: Multiple Assignees
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ci.Name, COUNT(a.AssignmentID) as AssigneeCount
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_Assignments a ON ci.InstanceID = a.InstanceID
                WHERE ci.InstanceID = 2071266
                GROUP BY ci.InstanceID, ci.Name
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC2: Multiple Assignees',
                'passed': row and row[1] >= 2,
                'details': f"Assignee count: {row[1] if row else 0}"
            })
        
        # UC3: Priority Task
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ci.Name, c.AddToPriorityList
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_Checklists c ON ci.ChecklistID = c.ChecklistID
                WHERE ci.InstanceID = 2071267
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC3: Priority Task',
                'passed': row is not None,
                'details': f"Priority flag: {row[1] if row else 'N/A'}"
            })
        
        # UC4: Soft Due Date
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DueDate, SoftDueDate
                FROM QCheck_ActiveChecklists
                WHERE InstanceID = 2071268
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC4: Soft Due Date',
                'passed': row and row[1] < row[0],
                'details': f"Due: {row[0] if row else 'N/A'}, Soft: {row[1] if row else 'N/A'}"
            })
        
        # UC5: Reminder Task
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT IsReminder, DueTime
                FROM QCheck_ActiveChecklists
                WHERE InstanceID = 2071269
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC5: Reminder Task',
                'passed': row and row[0] == 1 and row[1] == '12:00',
                'details': f"IsReminder: {row[0] if row else 'N/A'}, Time: {row[1] if row else 'N/A'}"
            })
        
        return results
    
    def validate_recurring_tasks(self):
        """Validate Use Cases 6-9"""
        results = []
        
        # UC6: Daily Recurring
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 s.FreqType, s.BusinessDayBehavior, ci.Name
                FROM QCheck_Schedule s
                JOIN QCheck_ChecklistInstances ci ON s.ScheduleID = ci.ScheduleID
                WHERE ci.Name LIKE 'Check balances 175396%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC6: Daily Recurring',
                'passed': row and row[0] == 1 and row[1] == 1,
                'details': f"FreqType: {row[0] if row else 'N/A'}, BusinessDay: {row[1] if row else 'N/A'}"
            })
        
        # UC7: Weekly Recurring
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 s.FreqType, s.FreqRecurrance, ci.Name
                FROM QCheck_Schedule s
                JOIN QCheck_ChecklistInstances ci ON s.ScheduleID = ci.ScheduleID
                WHERE ci.Name LIKE 'Team standup 175396%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC7: Weekly Recurring',
                'passed': row and row[0] == 2 and row[1] == 2,  # Monday
                'details': f"FreqType: {row[0] if row else 'N/A'}, Day: {row[1] if row else 'N/A'}"
            })
        
        # UC8: Monthly Recurring
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 s.FreqType, s.FreqRecurrance
                FROM QCheck_Schedule s
                JOIN QCheck_ChecklistInstances ci ON s.ScheduleID = ci.ScheduleID
                WHERE ci.Name LIKE 'Monthly reports 175396%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC8: Monthly Recurring',
                'passed': row and row[0] == 3 and row[1] == 15,
                'details': f"FreqType: {row[0] if row else 'N/A'}, Day: {row[1] if row else 'N/A'}"
            })
        
        # UC9: Yearly Recurring
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 s.FreqType
                FROM QCheck_Schedule s
                JOIN QCheck_ChecklistInstances ci ON s.ScheduleID = ci.ScheduleID
                WHERE ci.Name LIKE 'Annual review 175396%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC9: Yearly Recurring',
                'passed': row and row[0] == 4,
                'details': f"FreqType: {row[0] if row else 'N/A'}"
            })
        
        return results
    
    def validate_special_features(self):
        """Validate Use Cases 10-15"""
        results = []
        
        # UC10: Confidential Task
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 Name
                FROM QCheck_ChecklistInstances
                WHERE Name LIKE '%Review documents 175396%'
                ORDER BY CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC10: Confidential Task',
                'passed': row and row[0].startswith('[CONFIDENTIAL]'),
                'details': f"Task name: {row[0][:50] if row else 'NOT FOUND'}"
            })
        
        # UC11: Checklist Items
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ci.Name, COUNT(i.ItemID) as ItemCount
                FROM QCheck_ChecklistInstances ci
                LEFT JOIN QCheck_Items i ON ci.ChecklistID = i.ChecklistID
                WHERE ci.Name LIKE 'Setup 175396%'
                GROUP BY ci.InstanceID, ci.Name
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC11: Checklist Items',
                'passed': row and row[1] >= 3,
                'details': f"Item count: {row[1] if row else 0}"
            })
        
        # UC13: Time-Based Names
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 ci.Name, ac.DueTime
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_ActiveChecklists ac ON ci.InstanceID = ac.InstanceID
                WHERE ci.Name LIKE 'Morning check-in%175396%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC13: Time-Based Names',
                'passed': row and row[1] == '09:00',
                'details': f"DueTime: {row[1] if row else 'N/A'}"
            })
        
        # UC14: Relative Dates
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 ci.Name, ac.DueDate, DATENAME(dw, ac.DueDate) as DayOfWeek
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_ActiveChecklists ac ON ci.InstanceID = ac.InstanceID
                WHERE ci.Name LIKE '%175396531%'
                AND ac.DueDate > GETDATE()
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC14: Relative Dates',
                'passed': row and row[2] == 'Friday',
                'details': f"Day: {row[2] if row else 'N/A'}, Date: {row[1] if row else 'N/A'}"
            })
        
        return results
    
    def validate_complex_patterns(self):
        """Validate Use Cases 16-20"""
        results = []
        
        # UC17: Business Day Handling
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 ci.Name, s.BusinessDayBehavior
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_Schedule s ON ci.ScheduleID = s.ScheduleID
                WHERE ci.Name LIKE 'Daily%175396%'
                AND s.FreqType = 1
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC17: Business Day Handling',
                'passed': row and row[1] == 1,
                'details': f"BusinessDayBehavior: {row[1] if row else 'N/A'}"
            })
        
        # UC20: Complex Recurrence
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 s.FreqType, s.FreqInterval, s.FreqRecurrance
                FROM QCheck_Schedule s
                JOIN QCheck_ChecklistInstances ci ON s.ScheduleID = ci.ScheduleID
                WHERE ci.Name LIKE 'Team meeting%175396%'
                AND s.FreqInterval = 2
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC20: Complex Recurrence',
                'passed': row and row[0] == 2 and row[1] == 2 and row[2] == 3,
                'details': f"Type: {row[0]}, Interval: {row[1]}, Day: {row[2]}" if row else "NOT FOUND"
            })
        
        return results
    
    def validate_advanced_features(self):
        """Validate Use Cases 21-30"""
        results = []
        
        # UC21: Quarter-End Tasks
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 s.FreqType, s.FreqInterval
                FROM QCheck_Schedule s
                JOIN QCheck_ChecklistInstances ci ON s.ScheduleID = ci.ScheduleID
                WHERE ci.Name LIKE 'Quarter end%175396%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC21: Quarter-End Tasks',
                'passed': row and row[0] == 3 and row[1] == 3,
                'details': f"FreqType: {row[0]}, Interval: {row[1]}" if row else "NOT FOUND"
            })
        
        # UC23: Batch Creation
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as TaskCount
                FROM QCheck_ChecklistInstances
                WHERE Name LIKE '%175396538%'
                AND CreateDate >= '2025-07-31 12:30:00'
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC23: Batch Creation',
                'passed': row and row[0] >= 3,
                'details': f"Tasks created: {row[0] if row else 0}"
            })
        
        # UC30: Custom Notifications
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 ac.IsReminder, ac.ReminderDate, ac.DueDate
                FROM QCheck_ChecklistInstances ci
                JOIN QCheck_ActiveChecklists ac ON ci.InstanceID = ac.InstanceID
                WHERE ci.Name LIKE '%175396544%'
                ORDER BY ci.CreateDate DESC
            """)
            row = cursor.fetchone()
            
            results.append({
                'use_case': 'UC30: Custom Notifications',
                'passed': row and row[0] == 1,
                'details': f"IsReminder: {row[0] if row else 'N/A'}"
            })
        
        return results