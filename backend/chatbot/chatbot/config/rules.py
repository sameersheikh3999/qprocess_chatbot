"""
Business Rules Configuration

Contains constants and configuration for business rules used across the API layer.
These rules define error handling patterns, validation criteria, and business logic constants.
"""

# Error message patterns that indicate user-friendly errors
ERROR_PHRASES = [
    'Did you mean',
    'Please try',
    'Who should be assigned',
    'What would you like'
]

# Validation rules
VALIDATION_RULES = {
    'MIN_MESSAGE_LENGTH': 1,
    'MAX_MESSAGE_LENGTH': 10000,
    'MIN_USERNAME_LENGTH': 1,
    'MAX_USERNAME_LENGTH': 100,
    'ALLOWED_TIMEZONES': [
        'UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
        'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'Australia/Sydney'
    ]
}

# Business logic constants
BUSINESS_RULES = {
    'DEFAULT_TASK_PRIORITY': 'medium',
    'MAX_ASSIGNEES_PER_TASK': 10,
    'DEFAULT_TASK_STATUS': 'pending',
    'TASK_TIMEOUT_MINUTES': 60,
    'SESSION_TIMEOUT_MINUTES': 30
}

# Response constants
RESPONSE_MESSAGES = {
    'MISSING_MESSAGE': 'No message provided.',
    'MISSING_USER': 'No user provided.',
    'MISSING_CONTROLLER': 'No mainController provided.',
    'TASK_CREATION_FAILED': 'Failed to create task',
    'USERS_RETRIEVAL_FAILED': 'Failed to retrieve users',
    'PROCEDURE_EXECUTION_FAILED': 'Failed to execute stored procedure'
}