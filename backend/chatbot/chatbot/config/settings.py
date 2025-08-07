"""
API Settings Configuration

Contains configuration settings for API behavior including timeouts, limits,
and other operational parameters.
"""

import os
from typing import Dict, Any

# API operational settings
API_SETTINGS: Dict[str, Any] = {
    # Default values
    'DEFAULT_TIMEZONE': 'UTC',
    'DEFAULT_DEBUG_MODE': False,
    
    # Timeout settings (in seconds)
    'REQUEST_TIMEOUT': 30,
    'AI_SERVICE_TIMEOUT': 60,
    'DATABASE_TIMEOUT': 30,
    'TASK_PROCESSING_TIMEOUT': 120,
    
    # Rate limiting
    'MAX_REQUESTS_PER_MINUTE': 60,
    'MAX_REQUESTS_PER_HOUR': 1000,
    
    # Response limits
    'MAX_RESPONSE_SIZE_BYTES': 1048576,  # 1MB
    'MAX_ERROR_MESSAGE_LENGTH': 500,
    
    # Retry settings
    'MAX_RETRY_ATTEMPTS': 3,
    'RETRY_DELAY_SECONDS': 1,
    'EXPONENTIAL_BACKOFF': True,
    
    # Logging settings
    'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
    'LOG_REQUEST_DETAILS': os.getenv('LOG_REQUEST_DETAILS', 'false').lower() == 'true',
    
    # Feature flags
    'ENABLE_DEBUG_MODE': os.getenv('ENABLE_DEBUG_MODE', 'false').lower() == 'true',
    'ENABLE_DETAILED_ERRORS': os.getenv('ENABLE_DETAILED_ERRORS', 'false').lower() == 'true',
    'ENABLE_REQUEST_VALIDATION': True,
    
    # Cache settings
    'CACHE_TTL_SECONDS': 300,  # 5 minutes
    'ENABLE_RESPONSE_CACHING': False,
    
    # Security settings
    'ENABLE_CSRF_PROTECTION': True,
    'ENABLE_RATE_LIMITING': True,
    'ALLOWED_HOSTS': os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else [],
}

# Environment-specific overrides
def get_api_setting(key: str, default: Any = None) -> Any:
    """
    Get an API setting with optional environment variable override.
    
    Args:
        key: Setting key to retrieve
        default: Default value if key not found
        
    Returns:
        Setting value or default
    """
    # Check for environment variable override
    env_key = f"API_{key.upper()}"
    env_value = os.getenv(env_key)
    
    if env_value is not None:
        # Try to convert to appropriate type
        if key.upper().endswith('_TIMEOUT') or key.upper().endswith('_LIMIT'):
            try:
                return int(env_value)
            except ValueError:
                pass
        elif key.upper().startswith('ENABLE_'):
            return env_value.lower() == 'true'
    
    return API_SETTINGS.get(key, default)

# Development vs Production settings
def update_settings_for_environment(env: str = None):
    """
    Update settings based on environment.
    
    Args:
        env: Environment name ('development', 'production', 'testing')
    """
    env = env or os.getenv('ENVIRONMENT', 'development')
    
    if env == 'development':
        API_SETTINGS.update({
            'LOG_LEVEL': 'DEBUG',
            'LOG_REQUEST_DETAILS': True,
            'ENABLE_DEBUG_MODE': True,
            'ENABLE_DETAILED_ERRORS': True,
            'REQUEST_TIMEOUT': 60,  # Longer timeouts for debugging
        })
    elif env == 'production':
        API_SETTINGS.update({
            'LOG_LEVEL': 'WARNING',
            'LOG_REQUEST_DETAILS': False,
            'ENABLE_DEBUG_MODE': False,
            'ENABLE_DETAILED_ERRORS': False,
            'ENABLE_RATE_LIMITING': True,
        })
    elif env == 'testing':
        API_SETTINGS.update({
            'LOG_LEVEL': 'ERROR',
            'LOG_REQUEST_DETAILS': False,
            'REQUEST_TIMEOUT': 10,
            'MAX_RETRY_ATTEMPTS': 1,
            'ENABLE_RATE_LIMITING': False,
        })

# Initialize settings based on current environment
update_settings_for_environment()