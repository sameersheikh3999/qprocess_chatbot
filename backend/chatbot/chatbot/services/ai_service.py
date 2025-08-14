"""
AI Service Module

This module provides centralized AI functionality for the chatbot application,
including Groq API integration, request handling, and response processing.
"""

import os
import json
import re
import time
import logging
import requests
import csv
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

from ..config.prompts import SystemPrompts, PromptHints
from .error_handler import error_handler, AIServiceError, retry_ai_service_call

logger = logging.getLogger(__name__)


# AIServiceError is now imported from error_handler


class AIService:
    """
    Service class for handling Groq AI API interactions, including
    configuration, request processing, and response parsing.
    """
    
    def __init__(self):
        """Initialize the AI service with Groq API configuration."""
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set. Please set it in your .env file or environment.")
        
        self.api_url = 'https://api.groq.com/openai/v1/chat/completions'
        self.model = 'llama3-70b-8192'  # Using Llama 3 70B model on Groq
        self.max_tokens = 1024
        
        # Default headers for Groq API
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        # Retry configuration
        self.max_retries = 2
        self.base_timeout = 30
        
        # Token usage tracking
        self.token_log_file = os.path.join(os.path.dirname(__file__), '../../token_usage.csv')
        self._ensure_token_log_file()
    
    def _ensure_token_log_file(self):
        """Ensure the token usage CSV file exists with headers."""
        if not os.path.exists(self.token_log_file):
            with open(self.token_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'model', 'input_tokens', 'output_tokens', 'total_tokens', 'cost_usd', 'success', 'error'])
    
    def _log_token_usage(self, model: str, input_tokens: int, output_tokens: int, success: bool = True, error: str = ''):
        """Log token usage to CSV file."""
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost based on Groq model pricing (prices per million tokens)
        if 'llama3-70b' in model.lower():
            # Llama 3 70B: $0.59 input, $0.79 output per million
            cost = (input_tokens * 0.59 / 1_000_000) + (output_tokens * 0.79 / 1_000_000)
        elif 'llama3-8b' in model.lower():
            # Llama 3 8B: $0.05 input, $0.10 output per million
            cost = (input_tokens * 0.05 / 1_000_000) + (output_tokens * 0.10 / 1_000_000)
        elif 'mixtral' in model.lower():
            # Mixtral 8x7B: $0.14 input, $0.42 output per million
            cost = (input_tokens * 0.14 / 1_000_000) + (output_tokens * 0.42 / 1_000_000)
        else:
            # Default to Llama 3 70B pricing if unknown
            cost = (input_tokens * 0.59 / 1_000_000) + (output_tokens * 0.79 / 1_000_000)
        
        timestamp = datetime.now().isoformat()
        
        try:
            with open(self.token_log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, model, input_tokens, output_tokens, total_tokens, f"{cost:.6f}", success, error])
            logger.debug(f"Logged token usage: {input_tokens} input, {output_tokens} output, ${cost:.6f}")
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")
    
    def calculate_timeout(self, message_length: int, is_batch: bool = False, is_complex_recurring: bool = False) -> int:
        """
        Calculate dynamic timeout based on request complexity.
        
        Args:
            message_length (int): Length of the user message
            is_batch (bool): Whether this is a batch request
            is_complex_recurring (bool): Whether this involves complex recurring patterns
            
        Returns:
            int: Timeout in seconds
        """
        timeout = self.base_timeout
        
        if message_length > 200:
            timeout += 15
        if is_batch:
            timeout += 20
        if is_complex_recurring:
            timeout += 10
            
        return timeout
    
    def send_request_to_groq(self, messages: List[Dict], system_prompt: str, 
                              timeout: int, debug_mode: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Send a request to Groq API with retry logic and error handling.
        
        Args:
            messages (List[Dict]): Conversation history messages
            system_prompt (str): System prompt for the conversation
            timeout (int): Request timeout in seconds
            debug_mode (bool): Enable debug logging
            
        Returns:
            Tuple[bool, Dict]: (success, response_data)
        """
        # Convert to Groq API format (OpenAI-compatible)
        groq_messages = [{"role": "system", "content": system_prompt}] + messages
        
        payload = {
            'model': self.model,
            'messages': groq_messages,
            'max_tokens': self.max_tokens,
            'temperature': 0.1,  # Low temperature for consistent task extraction
            'stream': False
        }
        
        try:
            logger.debug(f"Sending Groq API request")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=timeout)
            response_data = response.json()
            
            if response.status_code != 200:
                error_message = response_data.get("error", {}).get("message", str(response_data))
                logger.error(f"Groq API error: Status {response.status_code}, Response: {response_data}")
                
                # Log failed request with available token info
                if 'usage' in response_data:
                    input_tokens = response_data['usage'].get('prompt_tokens', 0)
                    output_tokens = response_data['usage'].get('completion_tokens', 0)
                    self._log_token_usage(self.model, input_tokens, output_tokens, success=False, error=error_message)
                
                raise AIServiceError(f'LLM error: {error_message}', 'GROQ_API_ERROR')
            
            # Validate response structure
            if 'choices' not in response_data or not response_data['choices']:
                logger.error(f"No choices in Groq response: {response_data}")
                raise AIServiceError('Invalid LLM response format', 'INVALID_RESPONSE_FORMAT')
            
            # Extract content from response
            content = response_data['choices'][0]['message']['content']
            
            # Extract and log token usage
            if 'usage' in response_data:
                input_tokens = response_data['usage'].get('prompt_tokens', 0)
                output_tokens = response_data['usage'].get('completion_tokens', 0)
                self._log_token_usage(self.model, input_tokens, output_tokens, success=True)
                logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}")
            
            # Log the response for debugging
            if debug_mode:
                logger.info(f"Groq raw response: {content}")
            else:
                logger.debug(f"Groq raw response: {content[:500]}...")
            
            return True, {'content': content, 'raw_response': response_data}
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Groq API timeout: {e}")
            raise AIServiceError('Request timeout - please try again', 'GROQ_API_TIMEOUT')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request error: {e}")
            raise AIServiceError('Failed to communicate with AI service', 'GROQ_API_REQUEST_ERROR')
            
        except AIServiceError:
            # Re-raise AIServiceError as-is
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {type(e).__name__}: {e}")
            error_handler.log_error(e, {'operation': 'groq_api_call'})
            raise AIServiceError('Sorry, I could not understand the AI response. Please try again.', 'UNEXPECTED_ERROR')
    
    def parse_json_response(self, content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse JSON from Groq's response content.
        
        Args:
            content (str): Raw response content from Groq
            
        Returns:
            Tuple[bool, Dict]: (is_json_response, parsed_json)
        """
        # First try to find JSON block in code fence
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', content)
        if not json_match:
            # Try to find any JSON object
            json_match = re.search(r'\{[\s\S]*?\}', content)
        
        if json_match:
            try:
                json_str = json_match.group(1) if '```' in content else json_match.group(0)
                parsed_json = json.loads(json_str)
                logger.debug(f"Successfully parsed JSON from Groq response")
                return True, parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}, Content: {json_match.group(0)[:200]}...")
                return False, {}
        else:
            logger.warning(f"No JSON found in response: {content[:200]}...")
            return False, {}
    
    def process_task_extraction(self, user_message: str, main_controller: str, 
                               current_date, pre_extracted: Dict[str, Any], 
                               history: List[Dict], debug_mode: bool = False) -> Tuple[bool, Dict[str, Any], str]:
        """
        Process task parameter extraction using Groq AI.
        
        Args:
            user_message (str): User's input message
            main_controller (str): Main controller name
            current_date: Current date object
            pre_extracted (Dict): Pre-extracted parameters
            history (List[Dict]): Conversation history
            debug_mode (bool): Enable debug mode
            
        Returns:
            Tuple[bool, Dict, str]: (success, extracted_params, response_content)
        """
        # Generate hint text from pre-extracted parameters
        pre_extracted_with_message = pre_extracted.copy()
        pre_extracted_with_message['_original_message'] = user_message
        hint_text = PromptHints.generate_hint_text(pre_extracted_with_message)
        
        # Generate system prompt
        system_prompt = SystemPrompts.get_task_extraction_prompt(
            current_date, main_controller, hint_text
        )
        
        # Calculate timeout based on request complexity
        message_length = len(user_message)
        is_batch = '_batch_tasks' in pre_extracted
        is_complex_recurring = (pre_extracted.get('IsRecurring') == 1 and 
                               pre_extracted.get('FreqType', 0) in [5, 6])
        
        timeout = self.calculate_timeout(message_length, is_batch, is_complex_recurring)
        
        logger.debug(f"Using API timeout: {timeout}s (message_length={message_length}, "
                    f"batch={is_batch}, complex_recurring={is_complex_recurring})")
        
        # Validate history before sending to Groq API
        if not history or len(history) == 0:
            logger.warning("Empty history detected, creating fallback message")
            history = [{"role": "user", "content": user_message}]
        
        # Ensure all messages have required fields
        validated_history = []
        for msg in history:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                validated_history.append(msg)
            else:
                logger.warning(f"Invalid message format in history: {msg}")
        
        if not validated_history:
            validated_history = [{"role": "user", "content": user_message}]
            logger.warning("No valid messages in history, using fallback")
        
        logger.debug(f"Validated history with {len(validated_history)} messages")
        
        # Send request to Groq
        try:
            success, response_data = self.send_request_to_groq(
                validated_history, system_prompt, timeout, debug_mode
            )
        except AIServiceError as e:
            error_handler.log_error(e, {'operation': 'task_extraction', 'message_length': message_length})
            return False, {}, str(e)
        
        if not success:
            return False, {}, response_data.get('error', 'Unknown error')
        
        content = response_data['content']
        
        # Parse JSON from response
        is_json_response, parsed_json = self.parse_json_response(content)
        
        if is_json_response:
            # Debug logging for parameter analysis
            logger.info("="*60)
            logger.info("PARAMETER EXTRACTION DEBUG")
            logger.info(f"Pre-extracted params: {pre_extracted}")
            logger.info(f"LLM JSON params: {parsed_json}")
            
            # Special debug for UC08 monthly pattern
            if "on the" in user_message.lower() and "month" in user_message.lower():
                logger.warning(f"UC08 PATTERN DETECTED: Monthly with specific day")
                logger.warning(f"User message: {user_message}")
                logger.warning(f"Groq's FreqType: {parsed_json.get('FreqType')}")
                logger.warning(f"Groq's FreqRecurrance: {parsed_json.get('FreqRecurrance')}")
                logger.warning(f"Groq's FreqInterval: {parsed_json.get('FreqInterval')}")
            
            # Merge pre-extracted parameters with LLM parameters
            final_params = self._merge_parameters(parsed_json, pre_extracted)
            
            logger.info(f"Final merged params: {final_params}")
            logger.info("="*60)
            
            return True, final_params, content
        else:
            # Return the text response if no JSON was found
            return False, {}, content
    
    def _merge_parameters(self, llm_json: Dict[str, Any], pre_extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge pre-extracted parameters with LLM-extracted parameters.
        
        Args:
            llm_json (Dict): Parameters extracted by LLM
            pre_extracted (Dict): Pre-extracted parameters
            
        Returns:
            Dict: Merged parameters with proper precedence
        """
        merged = llm_json.copy()
        
        # Special handling for schedule parser results - they should take precedence
        if pre_extracted.get('IsRecurring') == 1:
            # If schedule parser detected recurring pattern, preserve its parameters
            schedule_params = ['IsRecurring', 'FreqType', 'FreqInterval', 'FreqRecurrance', 'BusinessDayBehavior']
            for param in schedule_params:
                if param in pre_extracted and pre_extracted[param] is not None:
                    if param in merged and merged[param] != pre_extracted[param]:
                        logger.warning(f"Schedule parser {param}={pre_extracted[param]} overriding LLM {param}={merged.get(param)}")
                    merged[param] = pre_extracted[param]
                    logger.debug(f"Using schedule parser value for {param}: {pre_extracted[param]}")
            # Add explicit logging for FreqRecurrance debugging
            logger.info(f"FREQ_DEBUG: After merge, FreqRecurrance={merged.get('FreqRecurrance')} (from schedule parser={pre_extracted.get('FreqRecurrance')})")
        
        for key, value in pre_extracted.items():
            # Skip internal pre-extraction markers
            if key.startswith('_'):
                continue
            
            # Skip schedule params already handled above
            if pre_extracted.get('IsRecurring') == 1 and key in ['IsRecurring', 'FreqType', 'FreqInterval', 'FreqRecurrance', 'BusinessDayBehavior']:
                continue
                
            # Special handling for AddToPriorityList - always preserve if set to 1
            if key == 'AddToPriorityList' and value == 1:
                merged[key] = value
                logger.debug(f"Preserving pre-extracted AddToPriorityList=1")
            elif key not in merged or merged[key] in [None, '', 0]:
                merged[key] = value
                logger.debug(f"Using pre-extracted value for {key}: {value}")
            elif merged[key] != value:
                logger.debug(f"LLM overrode pre-extracted {key}: {value} -> {merged[key]}")
                # Special case: don't let LLM override priority list to 0 if we detected it
                if key == 'AddToPriorityList' and value == 1 and merged[key] == 0:
                    logger.warning(f"LLM tried to override AddToPriorityList from 1 to 0, keeping 1")
                    merged[key] = 1
        
        # CRITICAL FIX: Set IsRecurring to 0 by default if not explicitly set
        if 'IsRecurring' not in merged or merged['IsRecurring'] is None:
            merged['IsRecurring'] = 0
            logger.debug("Set IsRecurring to 0 (default for non-recurring tasks)")
        
        # Force non-recurring for "next [weekday]" patterns
        msg_lower = pre_extracted.get('_original_message', '').lower()
        if 'next' in msg_lower and any(day in msg_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            if merged.get('IsRecurring') == 1:
                logger.warning(f"LLM incorrectly set IsRecurring=1 for 'next [weekday]' pattern. Forcing to 0.")
            merged['IsRecurring'] = 0
            merged['FreqType'] = 0
            merged['FreqRecurrance'] = 0
            merged['FreqInterval'] = 0
            logger.debug("Forced IsRecurring=0 for 'next [weekday]' pattern")
        
        return merged
    
    def check_conditional_logic(self, user_message: str) -> bool:
        """
        Check if user message contains conditional logic patterns.
        
        Args:
            user_message (str): User's input message
            
        Returns:
            bool: True if conditional logic is detected
        """
        msg_lower = user_message.lower()
        patterns = SystemPrompts.get_conditional_logic_patterns()
        
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                logger.debug("Detected conditional logic in message")
                return True
        
        return False
    
    def get_conditional_logic_error(self) -> str:
        """
        Get the error message for conditional logic rejection.
        
        Returns:
            str: Error message
        """
        return SystemPrompts.get_conditional_logic_error_message()