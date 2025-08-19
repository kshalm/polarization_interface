import asyncio
import redis.asyncio as redis
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
try:
    from .config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)
redis_debug_logger = logging.getLogger('redis_debug')

CHANNEL_COUNTS = 'monitor:counts'
LAST_TIMESTAMP = '0-0'


class RedisClientError(Exception):
    pass


class RedisCountsClient:
    """Async Redis client with fresh connection per request pattern"""
    
    def __init__(self):
        self.last_timestamp = LAST_TIMESTAMP
        self.connection_attempts = 0
        self.last_successful_read = None
        self.total_reads = 0
        self.failed_reads = 0
        self.filtered_reads = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.last_reset_time = None
        self._started = False
        redis_debug_logger.info(f"Initializing RedisCountsClient with initial timestamp: {self.last_timestamp}")

    async def start(self):
        """Start the Redis client - test initial connection"""
        if not self._started:
            try:
                # Test initial connection
                await self._test_fresh_connection()
                self._started = True
                logger.info("RedisCountsClient started and connection verified")
            except Exception as e:
                logger.warning(f"RedisCountsClient started but initial connection failed: {e}")
                # Still mark as started to allow retry attempts
                self._started = True

    async def stop(self):
        """Stop the Redis client"""
        if self._started:
            self._started = False
            logger.info("RedisCountsClient stopped")

    async def _get_fresh_connection(self) -> redis.Redis:
        """Create a fresh Redis connection for each request"""
        try:
            self.connection_attempts += 1
            
            connection = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                decode_responses=False,  # Keep as bytes for stream processing
                socket_connect_timeout=10.0,  # Connection timeout
                socket_timeout=10.0,  # Socket timeout
                retry_on_timeout=True
            )
            
            # Test the connection immediately
            await asyncio.wait_for(connection.ping(), timeout=5.0)
            return connection
            
        except Exception as e:
            redis_debug_logger.error(f"Failed to create fresh Redis connection #{self.connection_attempts}: {e}")
            raise RedisClientError(f"Failed to create fresh Redis connection: {e}")

    async def _test_fresh_connection(self):
        """Test Redis connectivity by creating and closing a fresh connection"""
        connection = None
        try:
            connection = await self._get_fresh_connection()
            return True
        finally:
            if connection:
                try:
                    await connection.aclose()
                except:
                    pass

    def decode_dict(self, data_dict: dict) -> dict:
        """Decode Redis dictionary data from bytes to Python objects"""
        ret_dict = {}
        for key, value in data_dict.items():
            # Decode key
            key_str = key.decode() if isinstance(key, bytes) else key
            
            # Decode value
            if isinstance(value, bytes):
                val_str = value.decode()
                try:
                    # Try to parse as JSON
                    val_parsed = json.loads(val_str)
                except json.JSONDecodeError:
                    # If not JSON, keep as string
                    val_parsed = val_str
            else:
                val_parsed = value
            
            ret_dict[key_str] = val_parsed
        
        return ret_dict

    def decode_stream_data(self, raw_data: list) -> Optional[list]:
        """Decode Redis stream data"""
        if not raw_data or len(raw_data) == 0:
            return None
        
        channel, encoded_data = raw_data[0]
        
        msg_decode = []
        for timestamp, data in encoded_data:
            timestamp_str = timestamp.decode() if isinstance(timestamp, bytes) else timestamp
            decoded_data = self.decode_dict(data)
            msg_decode.append((timestamp_str, decoded_data))
        
        return msg_decode

    async def get_counts_data(self) -> Optional[Dict[str, Any]]:
        """Get the latest counts data from Redis stream - only returns NEW data"""
        if not self._started:
            raise RedisClientError("Redis client not started. Call start() first.")

        start_time = time.time()
        self.total_reads += 1
        connection = None
        
        try:
            # Get fresh connection for this request
            connection = await self._get_fresh_connection()

            # Read from the counts stream - only get messages AFTER our last timestamp
            stream = {CHANNEL_COUNTS: self.last_timestamp}
            
            # Use asyncio timeout to prevent hanging
            messages = await asyncio.wait_for(
                connection.xread(stream, count=1, block=100),  # 100ms timeout
                timeout=5.0  # Overall timeout
            )
            
            read_time = time.time() - start_time
            
            # If no messages, means no NEW data is available
            if not messages:
                return None
            
            decoded_messages = self.decode_stream_data(messages)
            if not decoded_messages:
                self.failed_reads += 1
                redis_debug_logger.error("Failed to decode Redis stream messages")
                return None
            
            # Get the latest message and update our timestamp
            timestamp, counts_data = decoded_messages[-1]
            
            # Only return data if we got a genuinely new timestamp
            if timestamp != self.last_timestamp:
                self.last_timestamp = timestamp
                self.last_successful_read = datetime.now()
                self.consecutive_failures = 0  # Reset failure counter on success
                return counts_data
            else:
                return None
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.failed_reads += 1
            self.consecutive_failures += 1
            redis_debug_logger.error(f"Error during Redis read: {e}")
            logger.error(f"Failed to get counts data from Redis: {e}")
            
            # Check if we should reset stream position due to persistent failures
            self._check_recovery_needed()
            raise RedisClientError(f"Failed to get counts data: {e}")
        finally:
            # Always clean up the fresh connection
            if connection:
                try:
                    await connection.aclose()
                except Exception as e:
                    redis_debug_logger.debug(f"Error closing Redis connection: {e}")

    def _check_recovery_needed(self):
        """Check if we need to reset stream position due to persistent failures"""
        if self.consecutive_failures >= self.max_consecutive_failures:
            now = datetime.now()
            # Only reset once every 5 minutes to avoid excessive resets
            if (self.last_reset_time is None or 
                (now - self.last_reset_time).total_seconds() > 300):
                
                redis_debug_logger.warning(f"Too many consecutive failures ({self.consecutive_failures}), resetting stream position to latest")
                old_timestamp = self.last_timestamp
                self.reset_stream_position('$')  # Reset to latest
                self.last_reset_time = now
                self.consecutive_failures = 0
                redis_debug_logger.info(f"Stream position recovery: {old_timestamp} -> $ (latest)")

    async def test_connection(self) -> bool:
        """Test Redis connection by creating a fresh connection"""
        try:
            if not self._started:
                return False
            return await self._test_fresh_connection()
        except Exception as e:
            redis_debug_logger.debug(f"Redis connection test failed: {e}")
            return False

    async def get_formatted_counts(self, prefix: str = 'VV') -> Optional[Dict[str, Any]]:
        """Get counts data and format it for the frontend - only trimmed data"""
        try:
            counts_data = await self.get_counts_data()
            if not counts_data:
                return None
            
            # Only return trimmed data (matching STCounts behavior)
            is_trim = counts_data.get('isTrim', 0)
            if is_trim == 0:
                self.filtered_reads += 1
                redis_debug_logger.warning(f"FILTERING OUT non-trimmed data (isTrim={is_trim}) - this may be why data stops!")
                return None
            
            # Extract the counts for the specified prefix
            if prefix not in counts_data:
                redis_debug_logger.error(f"Prefix '{prefix}' not found in counts data. Available keys: {list(counts_data.keys())}")
                logger.warning(f"Prefix '{prefix}' not found in counts data. Available keys: {list(counts_data.keys())}")
                return None
            
            prefix_data = counts_data[prefix]
            
            # Extract Alice singles, Bob singles, and coincidences
            alice_singles = int(prefix_data.get('As', 0))
            bob_singles = int(prefix_data.get('Bs', 0))
            coincidences = int(prefix_data.get('C', 0))
            
            # Calculate efficiencies (exact STCounts logic)
            alice_eff = 0
            bob_eff = 0
            joint_eff = 0
            
            if bob_singles > 0:
                alice_eff = round(100 * coincidences / bob_singles, 1)
            
            if alice_singles > 0:
                bob_eff = round(100 * coincidences / alice_singles, 1)
            
            if alice_singles > 0 and bob_singles > 0:
                joint_eff = round(100 * coincidences / (alice_singles * bob_singles) ** 0.5, 1)
            
            result = {
                'alice_singles': alice_singles,
                'alice_efficiency': alice_eff,
                'bob_singles': bob_singles,
                'bob_efficiency': bob_eff,
                'coincidences': coincidences,
                'joint_efficiency': joint_eff
            }
            
            return result
            
        except Exception as e:
            redis_debug_logger.error(f"Failed to format counts data: {e}")
            logger.error(f"Failed to format counts data: {e}")
            raise RedisClientError(f"Failed to format counts data: {e}")

    def get_client_stats(self) -> Dict[str, Any]:
        """Get Redis client statistics for debugging"""
        now = datetime.now()
        time_since_last_read = None
        if self.last_successful_read:
            time_since_last_read = (now - self.last_successful_read).total_seconds()
        
        return {
            'connection_attempts': self.connection_attempts,
            'last_successful_read': self.last_successful_read.isoformat() if self.last_successful_read else None,
            'time_since_last_read_seconds': time_since_last_read,
            'total_reads': self.total_reads,
            'failed_reads': self.failed_reads,
            'filtered_reads': self.filtered_reads,
            'consecutive_failures': self.consecutive_failures,
            'max_consecutive_failures': self.max_consecutive_failures,
            'last_reset_time': self.last_reset_time.isoformat() if self.last_reset_time else None,
            'current_timestamp': self.last_timestamp,
            'is_connected': None,  # Async call not available in sync method
            'health_status': self._get_health_status(),
            'started': self._started
        }

    def _get_health_status(self) -> str:
        """Get overall health status of Redis client"""
        if not self._started:
            return 'not_started'
        elif self.consecutive_failures >= self.max_consecutive_failures:
            return 'failing'
        elif self.last_successful_read is None:
            return 'no_data_yet'
        else:
            now = datetime.now()
            time_since_last = (now - self.last_successful_read).total_seconds()
            if time_since_last > 60:  # No data for over 1 minute
                return 'stale'
            elif time_since_last > 10:  # No data for over 10 seconds
                return 'warning'
            else:
                return 'healthy'

    def reset_stream_position(self, new_position: str = '$'):
        """Reset stream reading position ($ means latest)"""
        redis_debug_logger.warning(f"Resetting stream position from {self.last_timestamp} to {new_position}")
        self.last_timestamp = new_position
        redis_debug_logger.info(f"Stream position reset to {new_position}")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics - simplified for fresh connection approach"""
        return {
            "connection_type": "fresh_per_request",
            "total_connection_attempts": self.connection_attempts,
            "status": "started" if self._started else "not_started"
        }