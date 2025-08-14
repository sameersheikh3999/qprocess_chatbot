"""
System prompts and prompt engineering configuration for the chatbot AI service.

This module contains all system prompts, prompt templates, and prompt engineering
logic used by the Groq AI integration.
"""

import datetime


def get_next_quarter_end_date() -> str:
    """Calculate the next quarter-end date from today"""
    today = datetime.date.today()
    current_year = today.year
    
    quarter_ends = [(3, 31), (6, 30), (9, 30), (12, 31)]
    
    for month, day in quarter_ends:
        quarter_end_date = datetime.date(current_year, month, day)
        if quarter_end_date > today:
            return quarter_end_date.strftime('%Y-%m-%d')
    
    # If all quarters this year have passed, use Q1 of next year
    next_year_q1 = datetime.date(current_year + 1, 3, 31)
    return next_year_q1.strftime('%Y-%m-%d')


class SystemPrompts:
    """
    Container class for all system prompts used in the AI service.
    """
    
    @staticmethod
    def get_task_extraction_prompt(current_date, main_controller, hint_text=""):
        """
        Generate the main system prompt for task parameter extraction.
        
        Args:
            current_date (datetime.date): Current date for context
            main_controller (str): Main controller name
            hint_text (str): Additional hints from pre-extraction
            
        Returns:
            str: Complete system prompt for task extraction
        """
        return (
            f"You must extract task parameters from user messages. Today: {current_date.strftime('%Y-%m-%d')}\n\n"
            
            "RULES:\n"
            "1. Extract TaskName from quotes - if task is 'quoted', use ONLY the quoted text\n"
            "2. NEVER add words before/after quoted task names (no 'Check', 'Create', etc.)\n"
            "3. Extract Assignees from patterns like 'for X', 'with X', 'to X'\n"
            "4. If message says 'remind me', set Assignees = MainController\n"
            "5. Extract recurring patterns (daily, weekly, monthly, yearly)\n"
            "6. Return JSON with all parameters\n"
            "7. Only ask if you cannot determine TaskName or Assignees\n\n"
            
            "EXTRACTION PATTERNS:\n"
            "- 'with NAME and NAME' → Assignees='NAME,NAME'\n"
            "- 'for NAME' → Assignees='NAME'\n"
            "- 'remind me' → Assignees=MainController\n"
            f"- MainController = '{main_controller}'\n"
            "- 'confidential' → Prepend [CONFIDENTIAL] to TaskName\n"
            "- 'with checkboxes for: X, Y, Z' → Items='X\\nY\\nZ'\n"
            "- 'for [Group Name]' → Assignees='Group Name'\n"
            "- 'next Friday' → Calculate actual date\n"
            "- 'managed by NAME' → Controllers='NAME'\n"
            "- 'add to priority list' or 'priority' → AddToPriorityList=1\n\n"
            
            "TASK NAME EXTRACTION EXAMPLES:\n"
            "- Check 'Project Update' daily → TaskName='Project Update' (NOT 'Check Project Update')\n"
            "- 'Team Meeting' at 3pm → TaskName='Team Meeting'\n"
            "- Create task 'Bug Fix' → TaskName='Bug Fix' (NOT 'Create task Bug Fix')\n"
            "- Use template for 'Release' → TaskName='Release' (NOT 'Use template for Release')\n\n"
            
            "VALID USER NAMES (examples):\n"
            "Tim Germany, Bruce Lacoe, Charlie Williamson, Frank Bonner, Greg Hamilton,\n"
            "Pat Walker, Amanda Krueger, Beth Looney, Daniel Schwarz, Heidi McDonald,\n"
            "John Pruitt, Kim Carpenter, Tanya Schmidt, Christopher Smith, Tony Boehm\n\n"
            
            "ONE-TIME TASKS (IsRecurring=0):\n"
            "- 'next Monday/Tuesday/etc' → One-time task on that specific date\n"
            "- 'tomorrow' → One-time task\n"
            "- 'on [specific date]' → One-time task\n"
            "- Default: Tasks are ONE-TIME unless explicitly recurring\n\n"
            
            "RECURRING PATTERNS (IsRecurring=1):\n"
            "- 'every day/daily' → IsRecurring=1, FreqType=1, FreqRecurrance=1, FreqInterval=1\n"
            "- 'every week/weekly' → IsRecurring=1, FreqType=2, FreqInterval=1\n"
            "  - Monday=2, Tuesday=3, Wednesday=4, Thursday=5, Friday=6, Saturday=7, Sunday=1\n"
            "- 'biweekly/every 2 weeks/every other week' → IsRecurring=1, FreqType=2, FreqInterval=2\n"
            "  - FreqInterval=2 means every OTHER week (biweekly)\n"
            "- 'every month/monthly' → IsRecurring=1, FreqType=3, FreqRecurrance=day of month, FreqInterval=1\n"
            "- 'every quarter/quarterly' → IsRecurring=1, FreqType=3, FreqRecurrance=day_bitmask, FreqInterval=3\n"
            f"  - For quarterly tasks, use {get_next_quarter_end_date()} as the due date (next available quarter-end)\n"
            "  - Quarter-end dates: Mar 31, Jun 30, Sep 30, Dec 31 → FreqRecurrance based on day\n"
            "- 'every year/yearly' → IsRecurring=1, FreqType=6, FreqInterval=1\n"
            "  - Month bitmask in FreqRecurrance: Jan=1, Feb=2, Mar=4, Apr=8, May=16, Jun=32, Jul=64, Aug=128, Sep=256, Oct=512, Nov=1024, Dec=2048\n\n"
            
            "IMPORTANT FREQUENCY RULES:\n"
            "- FreqInterval indicates repetition interval (1=every, 2=every other, 3=every third, etc.)\n"
            "- FreqRecurrance is a bitmask for days/months selection\n"
            "- For weekly tasks: FreqRecurrance = day bitmask, FreqInterval = weeks between occurrences\n"
            "- CRITICAL: For 'quarterly' or 'quarter-end' tasks: MUST use FreqType=3, FreqInterval=3\n\n"
            
            "IMPORTANT: 'next [weekday]' means ONE occurrence, not recurring!\n\n"
            
            "YOUR RESPONSE MUST FOLLOW THIS FORMAT:\n\n"
            "[Brief message like: \"I'll create a task for [description] and assign it to [names].\"]\n\n"
            "IMPORTANT: For checklist items, use COMMA-SEPARATED format, not newlines!\n"
            "Example: \"Items\": \"task 1,task 2,task 3\"\n\n"
            "```json\n"
            "{\n"
            "  \"TaskName\": \"[extracted task name]\",\n"
            "  \"Assignees\": \"[comma-separated names]\",\n"
            f"  \"Controllers\": \"{main_controller}\",\n"
            "  \"DueDate\": \"[YYYY-MM-DD or null]\",\n"
            "  \"DueTime\": \"[HH:MM or null]\",\n"
            "  \"SoftDueDate\": \"[YYYY-MM-DD or null]\",\n"
            "  \"Items\": \"[comma-separated checklist items or empty string]\",\n"
            "  \"IsRecurring\": 0,\n"
            "  \"FreqType\": 0,\n"
            "  \"FreqRecurrance\": 0,\n"
            "  \"FreqInterval\": 1,\n"
            "  \"BusinessDayBehavior\": 0,\n"
            "  \"AddToPriorityList\": 0\n"
            "}\n"
            "```\n\n"
            
            "CRITICAL RULES:\n"
            f"• MainController = '{main_controller}' (already set)\n"
            "• ALWAYS include the JSON block in your response\n"
            "• Extract assignees from 'for', 'with', 'to' patterns\n"
            "• 'Remind me' means assign to MainController\n"
            "• Only ask questions if TaskName or Assignees are truly missing\n"
            "• If you can guess the assignees from context, do so!"
            f"{hint_text}"
        )
    
    @staticmethod
    def get_conditional_logic_patterns():
        """
        Get patterns that indicate conditional logic in user messages.
        
        Returns:
            list: List of regex patterns for conditional logic detection
        """
        return [
            r'\bif\s+.*\s+then\b',
            r'\bif\s+.*\s+change',  # "if X changes" pattern
            r'\bwhen\s+.*\s+happens\b',
            r'\bafter\s+.*\s+approval\b',
            r'\brequiring\s+.*\s+approval\b',
            r'\bescalates?\s+if\b',
            r'\bif\s+.*\s+exceeds?\b',
            r'\bafter\s+.*\s+sign-?off\b',
            r'\bdepends?\s+on\b',
            r'\bconditional\s+on\b'
        ]
    
    @staticmethod
    def get_conditional_logic_error_message():
        """
        Get the error message for conditional logic rejection.
        
        Returns:
            str: Error message for conditional logic
        """
        return (
            'I cannot create tasks with conditional logic like "if/then" statements. '
            'Please create the task without conditions, or set up the conditions '
            'separately in the QProcess system.'
        )


class PromptHints:
    """
    Helper class for generating prompt hints based on pre-extracted parameters.
    """
    
    @staticmethod
    def generate_hint_text(pre_extracted):
        """
        Generate hint text for Groq based on pre-extracted parameters.
        
        Args:
            pre_extracted (dict): Pre-extracted parameters
            
        Returns:
            str: Hint text to append to system prompt
        """
        if not pre_extracted:
            return ""
        
        hint_text = f"\n\nHINT: I already detected: {pre_extracted}"
        
        # Add explicit hint for next [weekday] patterns
        msg_lower = pre_extracted.get('_original_message', '').lower()
        if 'next' in msg_lower and any(day in msg_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            hint_text += "\nNOTE: 'next [weekday]' means ONE-TIME task, not recurring!"
        
        return hint_text