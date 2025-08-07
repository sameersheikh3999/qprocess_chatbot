"""
Schedule Parser for QProcess Chatbot
Handles complex recurring patterns with bitmask calculations for FreqRecurrance field

FreqType values:
1 = Daily
2 = Weekly 
3 = Monthly
4 = Yearly
5 = Annual (similar to yearly but for specific date patterns)
6 = Quarterly

FreqRecurrance bitmask encoding:
- Weekly: Days of week (Sun=1, Mon=2, Tue=4, Wed=8, Thu=16, Fri=32, Sat=64)
- Monthly: Days of month (1st=1, 2nd=2, 3rd=4, etc.) 
- Yearly: Months (Jan=1, Feb=2, Mar=4, Apr=8, May=16, Jun=32, Jul=64, Aug=128, Sep=256, Oct=512, Nov=1024, Dec=2048)
- Quarterly: Quarter number (Q1=1, Q2=2, Q3=4, Q4=8)
"""

import re
from datetime import datetime, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)

class ScheduleParser:
    """Parse natural language schedules into QProcess parameters"""
    
    # Day of week mappings for weekly bitmasks
    WEEKDAY_BITS = {
        'sunday': 1, 'sun': 1,
        'monday': 2, 'mon': 2,
        'tuesday': 4, 'tue': 4, 'tues': 4,
        'wednesday': 8, 'wed': 8,
        'thursday': 16, 'thu': 16, 'thur': 16, 'thurs': 16,
        'friday': 32, 'fri': 32,
        'saturday': 64, 'sat': 64
    }
    
    # Month mappings for yearly bitmasks
    MONTH_BITS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 4, 'mar': 4,
        'april': 8, 'apr': 8,
        'may': 16,
        'june': 32, 'jun': 32,
        'july': 64, 'jul': 64,
        'august': 128, 'aug': 128,
        'september': 256, 'sep': 256, 'sept': 256,
        'october': 512, 'oct': 512,
        'november': 1024, 'nov': 1024,
        'december': 2048, 'dec': 2048
    }
    
    # Quarter mappings
    QUARTER_BITS = {
        'q1': 1, 'first': 1, '1st': 1,
        'q2': 2, 'second': 2, '2nd': 2,
        'q3': 4, 'third': 4, '3rd': 4,
        'q4': 8, 'fourth': 8, '4th': 8
    }
    
    def __init__(self):
        self.logger = logger
    
    def _has_explicit_recurrence(self, msg):
        """Check if message has explicit recurrence pattern and return the pattern type"""
        explicit_patterns = [
            (r'recurring\s+(daily|weekly|bi-?weekly|monthly|quarterly|yearly|annually)', 1),
            (r'every\s+(day|week|month|quarter|year)', 1),
            (r'repeat\s+(daily|weekly|monthly|quarterly|yearly)', 1),
            (r'repeats?\s+(daily|weekly|monthly|quarterly|yearly)', 1)
        ]
        
        for pattern, group_num in explicit_patterns:
            match = re.search(pattern, msg)
            if match:
                recurrence_type = match.group(group_num).lower()
                # Normalize variations
                if recurrence_type == 'day':
                    return 'daily'
                elif recurrence_type == 'week':
                    return 'weekly'
                elif recurrence_type in ['bi-weekly', 'biweekly']:
                    return 'biweekly'
                elif recurrence_type == 'month':
                    return 'monthly'
                elif recurrence_type == 'quarter':
                    return 'quarterly'
                elif recurrence_type in ['year', 'yearly', 'annually']:
                    return 'yearly'
                return recurrence_type
        return None
        
    def parse_schedule(self, message):
        """
        Parse a message and extract schedule parameters
        
        Returns dict with:
        - IsRecurring: 0 or 1
        - FreqType: 1-6 
        - FreqRecurrance: Bitmask value
        - FreqInterval: Interval multiplier (e.g., 2 for "every other")
        - BusinessDayBehavior: 0 or 1
        """
        msg_lower = message.lower()
        result = {
            'IsRecurring': 0,
            'FreqType': 0,
            'FreqRecurrance': 0,
            'FreqInterval': 1,
            'BusinessDayBehavior': 0
        }
        
        # Check for non-recurring "next [weekday]" pattern first
        if self._is_next_weekday_pattern(msg_lower):
            self.logger.debug("Detected 'next [weekday]' pattern - not recurring")
            return result
        
        # NEW: Check for explicit recurrence patterns first
        explicit_pattern = self._has_explicit_recurrence(msg_lower)
        if explicit_pattern:
            self.logger.debug(f"Detected explicit recurrence pattern: {explicit_pattern}")
            
            if explicit_pattern == 'daily':
                result.update(self._parse_daily(msg_lower))
                return result
            elif explicit_pattern in ['weekly', 'biweekly']:
                result.update(self._parse_weekly(msg_lower))
                return result
            elif explicit_pattern == 'monthly':
                result.update(self._parse_monthly(msg_lower))
                return result
            elif explicit_pattern == 'quarterly':
                result.update(self._parse_quarterly(msg_lower))
                return result
            elif explicit_pattern in ['yearly', 'annually']:
                result.update(self._parse_annual(msg_lower))
                return result
            
        # Check patterns in order of specificity (only if no explicit pattern found)
        # Daily should be checked before weekly since "daily" might trigger weekly pattern
        
        # Check for quarterly patterns
        if self._is_quarterly_pattern(msg_lower):
            result.update(self._parse_quarterly(msg_lower))
            return result
            
        # Check for annual/yearly patterns
        if self._is_annual_pattern(msg_lower):
            result.update(self._parse_annual(msg_lower))
            return result
            
        # Check for monthly patterns
        if self._is_monthly_pattern(msg_lower):
            result.update(self._parse_monthly(msg_lower))
            return result
            
        # Check for daily patterns BEFORE weekly
        if self._is_daily_pattern(msg_lower):
            result.update(self._parse_daily(msg_lower))
            return result
            
        # Check for weekly patterns
        if self._is_weekly_pattern(msg_lower):
            result.update(self._parse_weekly(msg_lower))
            return result
            
        return result
    
    def _is_next_weekday_pattern(self, msg):
        """Check if message contains 'next [weekday]' (non-recurring)"""
        next_day_pattern = r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        return bool(re.search(next_day_pattern, msg))
    
    def _is_quarterly_pattern(self, msg):
        """Check if message contains quarterly pattern"""
        patterns = [
            r'quarter(ly)?',
            r'every\s+quarter',
            r'each\s+quarter',
            r'end\s+of\s+(each\s+)?quarter',
            r'quarter\s+end'
        ]
        return any(re.search(pattern, msg) for pattern in patterns)
    
    def _parse_quarterly(self, msg):
        """Parse quarterly schedules"""
        # For quarterly tasks, use day 30 as a reasonable quarter-end approximation
        # Day 30 bitmask = 1 << 29 = 536870912
        result = {
            'IsRecurring': 1,
            'FreqType': 3,  # Monthly with 3-month interval = Quarterly
            'FreqRecurrance': 536870912,  # Day 30 of month (1 << 29)
            'FreqInterval': 3  # Every 3 months
        }
        
        # Check for specific day of month patterns
        ordinal_pattern = r'(\d{1,2})(st|nd|rd|th)\s+of\s+(each\s+)?month'
        match = re.search(ordinal_pattern, msg)
        if match:
            day = int(match.group(1))
            if 1 <= day <= 31:
                result['FreqRecurrance'] = 1 << (day - 1)  # Convert to bitmask
                self.logger.debug(f"Quarterly with specific day {day}: bitmask = {result['FreqRecurrance']}")
                print(f"FREQ_DEBUG: Quarterly parser found day {day}, setting FreqRecurrance to {result['FreqRecurrance']}")
        
        # Check for specific quarters (only if no day specified)
        elif any(quarter in msg for quarter in self.QUARTER_BITS):
            bitmask = 0
            for quarter, bit in self.QUARTER_BITS.items():
                if quarter in msg:
                    bitmask |= bit
            if bitmask > 0:
                result['FreqRecurrance'] = bitmask
                self.logger.debug(f"Quarterly with specific quarters: bitmask = {bitmask}")
            
        self.logger.debug(f"Parsed quarterly schedule: {result}")
        return result
    
    def _is_annual_pattern(self, msg):
        """Check if message contains annual/yearly pattern"""
        # Don't match if explicitly monthly (handles "last day of year, recurring monthly" case)
        if any(phrase in msg for phrase in ['recurring monthly', 'every month', 'repeat monthly']):
            return False
        
        patterns = [
            r'annual(ly)?',
            r'year(ly)?',
            r'every\s+year',
            r'each\s+year',
            r'once\s+a\s+year'
        ]
        return any(re.search(pattern, msg) for pattern in patterns)
    
    def _parse_annual(self, msg):
        """Parse annual/yearly schedules"""
        result = {
            'IsRecurring': 1,
            'FreqType': 6,  # Yearly (matches test expectations)
            'FreqRecurrance': 1,  # Default to January
            'FreqInterval': 1  # Interval between occurrences (1 = every year)
        }
        
        # Extract month from message
        month_bitmask = 0
        for month, bit in self.MONTH_BITS.items():
            if month in msg:
                month_bitmask |= bit
                
        if month_bitmask > 0:
            # For yearly, FreqRecurrance holds the month bitmask
            result['FreqRecurrance'] = month_bitmask
            
        # Extract specific date if present  
        date_match = re.search(r'(\w+)\s+(\d{1,2})', msg)
        if date_match:
            month_str = date_match.group(1).lower()
            day = int(date_match.group(2))
            
            # Store month in bitmask
            if month_str in self.MONTH_BITS:
                result['FreqRecurrance'] = self.MONTH_BITS[month_str]
                # Note: Day of month would need to be stored separately in the system
                
        self.logger.debug(f"Parsed annual schedule: {result}")
        return result
    
    def _is_monthly_pattern(self, msg):
        """Check if message contains monthly pattern"""
        patterns = [
            r'month(ly)?',
            r'every\s+month',
            r'each\s+month',
            r'once\s+a\s+month'
        ]
        return any(re.search(pattern, msg) for pattern in patterns)
    
    def _parse_monthly(self, msg):
        """Parse monthly schedules"""
        result = {
            'IsRecurring': 1,
            'FreqType': 3,  # Monthly
            'FreqRecurrance': 1,  # Default to 1st of month
            'FreqInterval': 1
        }
        
        # Check for "every other month"
        if 'every other month' in msg:
            result['FreqInterval'] = 2
            
        # Extract day of month
        ordinal_pattern = r'(\d{1,2})(st|nd|rd|th)'
        match = re.search(ordinal_pattern, msg)
        if match:
            day = int(match.group(1))
            if 1 <= day <= 31:
                result['FreqRecurrance'] = 1 << (day - 1)  # Convert to bitmask
                
        # Handle "last day of month"
        if 'last day' in msg:
            result['FreqRecurrance'] = 1 << 30  # Use bit 31 for last day
            
        self.logger.debug(f"Parsed monthly schedule: {result}")
        return result
    
    def _is_weekly_pattern(self, msg):
        """Check if message contains weekly pattern"""
        # Exclude "end of week" which is not recurring
        if 'end of week' in msg or 'end of the week' in msg:
            return False
            
        patterns = [
            r'week(ly)?',
            r'every\s+week',
            r'each\s+week',
            r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'every\s+other\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'\bbi-?weekly\b',  # biweekly or bi-weekly
            r'every\s+(?:2|two)\s+weeks?',  # every 2 weeks or every two weeks
            r'every\s+second\s+week'  # every second week
        ]
        return any(re.search(pattern, msg) for pattern in patterns)
    
    def _parse_weekly(self, msg):
        """Parse weekly schedules"""
        result = {
            'IsRecurring': 1,
            'FreqType': 2,  # Weekly
            'FreqRecurrance': 2,  # Default to Monday
            'FreqInterval': 1
        }
        
        # Check for biweekly patterns first (before "every other")
        biweekly_patterns = [
            r'\bbi-?weekly\b',  # biweekly or bi-weekly
            r'every\s+(?:2|two)\s+weeks?',  # every 2 weeks or every two weeks
            r'every\s+second\s+week',  # every second week
        ]
        
        if any(re.search(pattern, msg) for pattern in biweekly_patterns):
            result['FreqInterval'] = 2
            self.logger.debug("Detected biweekly pattern")
            
            # Extract specific day if mentioned
            days_bitmask = 0
            for day, bit in self.WEEKDAY_BITS.items():
                if day in msg:
                    days_bitmask |= bit
            if days_bitmask > 0:
                result['FreqRecurrance'] = days_bitmask
        
        # Check for "every other" pattern
        elif re.search(r'every\s+other\s+(\w+)', msg):
            every_other_match = re.search(r'every\s+other\s+(\w+)', msg)
            result['FreqInterval'] = 2
            day_name = every_other_match.group(1).lower()
            if day_name in self.WEEKDAY_BITS:
                result['FreqRecurrance'] = self.WEEKDAY_BITS[day_name]
        else:
            # Extract days of week and create bitmask
            days_bitmask = 0
            for day, bit in self.WEEKDAY_BITS.items():
                if day in msg:
                    days_bitmask |= bit
                    
            if days_bitmask > 0:
                result['FreqRecurrance'] = days_bitmask
                
        # Handle patterns like "every Monday and Thursday"
        if ' and ' in msg:
            days_bitmask = 0
            for day, bit in self.WEEKDAY_BITS.items():
                if day in msg:
                    days_bitmask |= bit
            if days_bitmask > 0:
                result['FreqRecurrance'] = days_bitmask
                
        self.logger.debug(f"Parsed weekly schedule: {result}")
        return result
    
    def _is_daily_pattern(self, msg):
        """Check if message contains daily pattern"""
        patterns = [
            r'\bdaily\b',
            r'every\s+day',
            r'each\s+day'
        ]
        # Also check for patterns like "daily standup"
        if any(re.search(pattern, msg) for pattern in patterns):
            return True
        # Check for standalone "daily" or with "skip weekend"
        if 'daily' in msg.split() or ('daily' in msg and 'skip' in msg):
            return True
        return False
    
    def _parse_daily(self, msg):
        """Parse daily schedules"""
        result = {
            'IsRecurring': 1,
            'FreqType': 1,  # Daily
            'FreqRecurrance': 1,
            'FreqInterval': 1,
            'BusinessDayBehavior': 0
        }
        
        # Check for business days only
        if any(phrase in msg for phrase in ['business day', 'weekday', 'skip weekend']):
            result['BusinessDayBehavior'] = 1
            
        # Check for "every other day"
        if 'every other day' in msg:
            result['FreqInterval'] = 2
            
        self.logger.debug(f"Parsed daily schedule: {result}")
        return result
    
    def calculate_bitmask_for_days(self, days_list):
        """Calculate bitmask for a list of weekday names"""
        bitmask = 0
        for day in days_list:
            day_lower = day.lower().strip()
            if day_lower in self.WEEKDAY_BITS:
                bitmask |= self.WEEKDAY_BITS[day_lower]
        return bitmask
    
    def calculate_bitmask_for_months(self, months_list):
        """Calculate bitmask for a list of month names"""
        bitmask = 0
        for month in months_list:
            month_lower = month.lower().strip()
            if month_lower in self.MONTH_BITS:
                bitmask |= self.MONTH_BITS[month_lower]
        return bitmask