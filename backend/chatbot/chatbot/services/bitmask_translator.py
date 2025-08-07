"""
UC08 Bitmask Translation Service
Production-ready implementation for Phase 2

Handles FreqRecurrance values >= 16384 for monthly tasks (FreqType=3)
Uses compressed encoding to store large bitmasks as smaller values
"""

import logging
import math
import json
from typing import Dict, Any, Tuple, Optional, List
from django.db import connection
from .error_handler import ValidationError, DatabaseError

logger = logging.getLogger(__name__)

class BitmaskTranslator:
    """
    Production implementation of UC08 bitmask translation
    
    Handles FreqRecurrance values >= 16384 for monthly tasks (FreqType=3)
    Uses compressed encoding to store large bitmasks as smaller values
    """
    
    # Encoding method constants
    ENCODING_NONE = 0
    ENCODING_COMPRESSED = 3
    
    # Compressed range: 8000-8031 for days 15-31
    COMPRESSED_BASE = 8000
    COMPRESSED_MAX = 8031
    
    def __init__(self):
        self.encode_table = {}
        self.decode_table = {}
        self._initialize_compression_tables()
        
        # Performance tracking
        self.stats = {
            'translations_performed': 0,
            'decoding_performed': 0,
            'cache_hits': 0,
            'errors': 0
        }
    
    def _initialize_compression_tables(self):
        """Initialize bidirectional compression lookup tables"""
        try:
            for day in range(15, 32):  # Days 15-31
                original_bitmask = 1 << (day - 1)
                compressed_value = self.COMPRESSED_BASE + (day - 15)
                
                self.encode_table[original_bitmask] = compressed_value
                self.decode_table[compressed_value] = original_bitmask
                
                logger.debug(f"UC08 Mapping: Day {day} -> {original_bitmask} -> {compressed_value}")
                
            logger.info(f"UC08 Translation tables initialized: {len(self.encode_table)} mappings")
            
        except Exception as e:
            logger.error(f"Failed to initialize UC08 translation tables: {e}")
            raise ValidationError("UC08 translation system initialization failed")
    
    def needs_translation(self, freq_recurrence: int, freq_type: int) -> bool:
        """
        Determine if translation is required
        
        Args:
            freq_recurrence: FreqRecurrance value from task parameters
            freq_type: FreqType value (3=monthly)
            
        Returns:
            True if translation is needed, False otherwise
        """
        return (freq_type == 3 and 
                freq_recurrence >= 16384 and 
                self._is_single_day_monthly(freq_recurrence))
    
    def _is_single_day_monthly(self, bitmask: int) -> bool:
        """Check if bitmask represents exactly one day (power of 2)"""
        return bitmask > 0 and (bitmask & (bitmask - 1)) == 0
    
    def encode_for_database(self, params: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Encode task parameters for database storage
        
        Args:
            params: Original task parameters dict
            
        Returns:
            Tuple of (encoded_params, translation_metadata)
            
        Raises:
            ValidationError: If encoding fails
        """
        try:
            freq_recurrence = params.get('FreqRecurrance', 0)
            original_bitmask = freq_recurrence
            
            if original_bitmask not in self.encode_table:
                raise ValidationError(f"UC08: Cannot encode bitmask {original_bitmask} - not in translation table")
            
            # Create encoded parameters
            encoded_params = params.copy()
            encoded_value = self.encode_table[original_bitmask]
            encoded_params['FreqRecurrance'] = encoded_value
            
            # Calculate day number for metadata
            day = int(math.log2(original_bitmask)) + 1
            
            # Create translation metadata
            metadata = {
                'encoding_method': self.ENCODING_COMPRESSED,
                'original_bitmask': original_bitmask,
                'encoded_value': encoded_value,
                'day': day,
                'task_name': params.get('TaskName', 'Unknown')
            }
            
            # Update statistics
            self.stats['translations_performed'] += 1
            
            logger.info(f"UC08 Encoded: Day {day} (bitmask {original_bitmask}) -> {encoded_value}")
            return encoded_params, metadata
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"UC08 encoding failed: {e}")
            raise ValidationError(f"Failed to encode UC08 parameters: {str(e)}")
    
    def decode_for_display(self, stored_params: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decode parameters for display/execution
        
        Args:
            stored_params: Parameters as stored in database
            metadata: Translation metadata from UC08_TranslationMetadata table
            
        Returns:
            Original parameters with correct FreqRecurrance value
        """
        try:
            encoding_method = metadata.get('encoding_method', self.ENCODING_NONE)
            
            if encoding_method == self.ENCODING_NONE:
                return stored_params
            
            encoded_value = stored_params.get('FreqRecurrance', 0)
            
            if encoded_value not in self.decode_table:
                logger.error(f"UC08: Cannot decode value {encoded_value} - not in decode table")
                return stored_params
            
            # Create decoded parameters
            decoded_params = stored_params.copy()
            original_bitmask = self.decode_table[encoded_value]
            decoded_params['FreqRecurrance'] = original_bitmask
            
            # Update statistics
            self.stats['decoding_performed'] += 1
            
            logger.debug(f"UC08 Decoded: {encoded_value} -> {original_bitmask}")
            return decoded_params
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"UC08 decoding failed: {e}")
            return stored_params
    
    def store_translation_metadata(self, metadata: Dict[str, Any]) -> Optional[int]:
        """
        Store translation metadata in database
        
        Args:
            metadata: Translation metadata dict
            
        Returns:
            Translation record ID or None if failed
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO UC08_TranslationMetadata 
                    (TaskName, EncodingMethod, OriginalBitmask, EncodedValue, Day, CreatedBy, Notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    metadata['task_name'],
                    metadata['encoding_method'],
                    metadata['original_bitmask'],
                    metadata['encoded_value'],
                    metadata['day'],
                    'Django UC08 Translator',
                    f"Automatic translation for day {metadata['day']}"
                ])
                
                # Get the inserted ID
                cursor.execute("SELECT SCOPE_IDENTITY()")
                result = cursor.fetchone()
                translation_id = result[0] if result else None
                
                logger.info(f"UC08 metadata stored with ID {translation_id}")
                return translation_id
                
        except Exception as e:
            logger.error(f"Failed to store UC08 metadata: {e}")
            return None
    
    def link_translation_to_task(self, translation_id: int, instance_id: int):
        """
        Link translation metadata to created task instance
        
        Args:
            translation_id: ID from UC08_TranslationMetadata table
            instance_id: ID from QCheck_ChecklistInstances table
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE UC08_TranslationMetadata 
                    SET InstanceID = %s,
                        ChecklistID = (
                            SELECT ChecklistID 
                            FROM QCheck_ChecklistInstances 
                            WHERE ID = %s
                        )
                    WHERE ID = %s
                """, [instance_id, instance_id, translation_id])
                
                logger.info(f"UC08 translation {translation_id} linked to task {instance_id}")
                
        except Exception as e:
            logger.error(f"Failed to link UC08 translation {translation_id} to task {instance_id}: {e}")
    
    def get_translation_info(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve translation information for a task instance
        
        Args:
            instance_id: Task instance ID
            
        Returns:
            Translation info dict or None if not found
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EncodingMethod, OriginalBitmask, EncodedValue, Day, CreatedDate
                    FROM UC08_TranslationMetadata
                    WHERE InstanceID = %s
                """, [instance_id])
                
                row = cursor.fetchone()
                if row:
                    return {
                        'encoding_method': row[0],
                        'original_bitmask': row[1],
                        'encoded_value': row[2],
                        'day': row[3],
                        'created_date': row[4]
                    }
                
        except Exception as e:
            logger.error(f"Failed to retrieve UC08 translation info for task {instance_id}: {e}")
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get translation service statistics"""
        return {
            'translations_performed': self.stats['translations_performed'],
            'decoding_performed': self.stats['decoding_performed'],
            'cache_hits': self.stats['cache_hits'],
            'errors': self.stats['errors'],
            'encode_table_size': len(self.encode_table),
            'decode_table_size': len(self.decode_table)
        }
    
    def validate_translation_integrity(self) -> bool:
        """
        Validate that all translation tables are consistent
        
        Returns:
            True if all tables are consistent, False otherwise
        """
        try:
            # Check that encode and decode tables are mirrors
            for original, encoded in self.encode_table.items():
                if encoded not in self.decode_table:
                    logger.error(f"UC08 integrity error: encoded value {encoded} not in decode table")
                    return False
                
                if self.decode_table[encoded] != original:
                    logger.error(f"UC08 integrity error: decode mismatch for {encoded}")
                    return False
            
            # Check day range coverage
            expected_days = set(range(15, 32))
            actual_days = set()
            
            for original_bitmask in self.encode_table.keys():
                day = int(math.log2(original_bitmask)) + 1
                actual_days.add(day)
            
            if expected_days != actual_days:
                logger.error(f"UC08 integrity error: day coverage mismatch")
                return False
            
            logger.info("UC08 translation integrity check passed")
            return True
            
        except Exception as e:
            logger.error(f"UC08 integrity check failed: {e}")
            return False

# Global translator instance
_translator_instance = None

def get_translator() -> BitmaskTranslator:
    """Get global translator instance (singleton pattern)"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = BitmaskTranslator()
    return _translator_instance