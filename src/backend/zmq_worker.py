"""
Standalone ZMQ worker module for subprocess execution.

This module provides a clean interface for executing ZMQ operations in separate processes,
avoiding GIL blocking issues with Redis polling.
"""

def execute_zmq_command(command_name, *args, **kwargs):
    """
    Execute a ZMQ command in a subprocess with proper error handling.
    
    This function is designed to be called via ProcessPoolExecutor and must be
    importable and serializable for subprocess execution.
    
    Args:
        command_name (str): Name of the ZMQ client method to execute
        *args: Positional arguments for the method
        **kwargs: Keyword arguments for the method
        
    Returns:
        dict: Result dictionary with success/error information
              {"success": bool, "result": any} or {"success": False, "error": str, "error_type": str}
    """
    try:
        # Import ZMQ client within the subprocess to avoid import issues
        from zmq_client import PolarizationZMQClient
        
        # Create a fresh ZMQ client instance for this subprocess
        client = PolarizationZMQClient()
        
        # Get the method by name and execute it
        method = getattr(client, command_name)
        result = method(*args, **kwargs)
        
        return {
            "success": True, 
            "result": result
        }
        
    except AttributeError as e:
        return {
            "success": False,
            "error": f"Method '{command_name}' not found on ZMQ client: {str(e)}",
            "error_type": "AttributeError"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }