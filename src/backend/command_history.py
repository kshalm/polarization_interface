import json
import os
from datetime import datetime
from typing import List, Dict, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)

class CommandHistoryManager:
    """Manages persistent command history with timestamps"""
    
    def __init__(self, history_file_path: str = None, max_history: int = 200):
        # Default to logs directory if no path specified
        if history_file_path is None:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            history_file_path = os.path.join(log_dir, 'command_history.jsonl')
        
        self.history_file_path = history_file_path
        self.max_history = max_history
        self.command_history = deque(maxlen=max_history)
        
        # Load existing history on initialization
        self._load_history()
        
    def _load_history(self):
        """Load command history from file on startup"""
        try:
            if not os.path.exists(self.history_file_path):
                logger.info(f"Command history file not found at {self.history_file_path}, starting with empty history")
                return
            
            # Read the last 10 lines from the file (most recent commands)
            with open(self.history_file_path, 'r') as f:
                lines = f.readlines()
            
            # Take the last 10 lines (most recent commands)
            recent_lines = lines[-10:] if len(lines) >= 10 else lines
            
            # Parse each line as JSON and add to history
            loaded_count = 0
            for line in reversed(recent_lines):  # Reverse to maintain chronological order in deque
                line = line.strip()
                if line:
                    try:
                        command_entry = json.loads(line)
                        # Validate required fields
                        if all(key in command_entry for key in ['id', 'timestamp', 'command', 'response']):
                            self.command_history.appendleft(command_entry)
                            loaded_count += 1
                        else:
                            logger.warning(f"Invalid command entry format: {line}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse command history line: {line} - {e}")
            
            logger.info(f"Loaded {loaded_count} command history entries from {self.history_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load command history from {self.history_file_path}: {e}")
    
    def add_command(self, command: str, response: str, is_error: bool = False) -> Dict[str, Any]:
        """Add a command to the history with timestamp and persist to file"""
        try:
            # Create command entry
            command_entry = {
                "id": str(int(datetime.now().timestamp() * 1000)),  # Millisecond timestamp as ID
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "response": response,
                "isError": is_error
            }
            
            # Add to in-memory history
            self.command_history.appendleft(command_entry)
            
            # Persist to file (append mode)
            self._append_to_file(command_entry)
            
            logger.debug(f"Added command to history: {command}")
            return command_entry
            
        except Exception as e:
            logger.error(f"Failed to add command to history: {e}")
            raise
    
    def _append_to_file(self, command_entry: Dict[str, Any]):
        """Append a command entry to the history file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.history_file_path), exist_ok=True)
            
            # Append as JSON line
            with open(self.history_file_path, 'a') as f:
                json.dump(command_entry, f, separators=(',', ':'))
                f.write('\n')
                
        except Exception as e:
            logger.error(f"Failed to append command to history file {self.history_file_path}: {e}")
            # Don't re-raise - we don't want file I/O issues to break the API
    
    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get command history as a list, most recent first"""
        try:
            history_list = list(self.command_history)
            
            if limit:
                history_list = history_list[:limit]
            
            return history_list
            
        except Exception as e:
            logger.error(f"Failed to get command history: {e}")
            return []
    
    def clear_history(self):
        """Clear all command history (memory and file)"""
        try:
            self.command_history.clear()
            
            # Remove the history file
            if os.path.exists(self.history_file_path):
                os.remove(self.history_file_path)
            
            logger.info("Command history cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear command history: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about command history"""
        try:
            total_commands = len(self.command_history)
            error_commands = sum(1 for cmd in self.command_history if cmd.get('isError', False))
            
            return {
                "total_commands": total_commands,
                "error_commands": error_commands,
                "success_commands": total_commands - error_commands,
                "history_file": self.history_file_path,
                "file_exists": os.path.exists(self.history_file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get command history stats: {e}")
            return {}