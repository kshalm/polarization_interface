from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import uvicorn
from datetime import datetime
from collections import deque
import asyncio
import uuid
from logging.handlers import RotatingFileHandler
import os
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor

try:
    from .config import config
    from .zmq_client import PolarizationZMQClient, ZMQClientError
    from .redis_client import RedisCountsClient, RedisClientError
    from .command_history import CommandHistoryManager
except ImportError:
    from config import config
    from zmq_client import PolarizationZMQClient, ZMQClientError
    from redis_client import RedisCountsClient, RedisClientError
    from command_history import CommandHistoryManager

# Configure structured logging
def setup_logging():
    """Setup structured logging with rotation"""
    # Create logs directory - use /app/logs/ to match Docker volume mount
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,  # INFO for production, DEBUG for development
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # Main backend log
            RotatingFileHandler(
                os.path.join(log_dir, 'backend.log'),
                maxBytes=20*1024*1024,  # 20MB
                backupCount=3
                ),
            # Error log with rotation
            RotatingFileHandler(
                os.path.join(log_dir, 'errors.log'),
                maxBytes=20*1024*1024,  # 20MB
                backupCount=3
                )
        ]
        )
    
    # Separate logger for operations
    operations_logger = logging.getLogger('operations')
    operations_handler = RotatingFileHandler(
        os.path.join(log_dir, 'operations.log'),
        maxBytes=20*1024*1024,  # 20MB
        backupCount=3
        )
    operations_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
    operations_logger.addHandler(operations_handler)
    operations_logger.setLevel(logging.INFO)
    
    # Separate logger for Redis debugging
    redis_debug_logger = logging.getLogger('redis_debug')
    redis_debug_handler = RotatingFileHandler(
        os.path.join(log_dir, 'redis_debug.log'),
        maxBytes=20*1024*1024,  # 20MB
        backupCount=3
        )
    redis_debug_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
    redis_debug_logger.addHandler(redis_debug_handler)
    redis_debug_logger.setLevel(logging.DEBUG)  # Enable debug level for Redis
    
    # Suppress watchfiles spam in logs - keep reloader active but silence routine messages
    watchfiles_logger = logging.getLogger('watchfiles.main')
    watchfiles_logger.setLevel(logging.WARNING)  # Only show warnings/errors, not INFO
    
    return operations_logger

# Setup logging and get loggers
operations_logger = setup_logging()
logger = logging.getLogger(__name__)

# Global clients - will be initialized in lifespan
zmq_client = None
redis_client = None

# Background polling task for Redis
redis_polling_task = None
latest_redis_data = None
latest_redis_timestamp = None

# Process executor for GIL-free ZMQ operations
process_executor = None


async def redis_polling_loop():
    """Background task to continuously poll Redis for counts data"""
    global latest_redis_data, latest_redis_timestamp
    
    while True:
        try:
            if redis_client and redis_client._started:
                result = await redis_client.get_formatted_counts('VV')
                if result is not None:
                    latest_redis_data = result
                    latest_redis_timestamp = datetime.now()
            
            # Poll every 200ms to match frontend expectation
            await asyncio.sleep(0.2)
            
        except Exception as e:
            logger.error(f"Error in Redis polling loop: {e}")
            await asyncio.sleep(1.0)  # Wait longer on error


# Initialize clients globally - simple synchronous initialization
zmq_client = PolarizationZMQClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown"""
    global redis_client, redis_polling_task, process_executor
    
    # Startup
    logger.info("Starting Polarization Control API...")
    logger.info("ZMQ client initialized")
    
    try:
        # Initialize process executor for GIL-free ZMQ operations (Python 3.9 compatible)
        process_executor = ProcessPoolExecutor(max_workers=2)
        logger.info("ProcessPoolExecutor initialized for ZMQ operations")
        
        # Initialize Redis client
        redis_client = RedisCountsClient()
        await redis_client.start()
        logger.info("Redis client started successfully")
        
        # Start Redis polling task
        redis_polling_task = asyncio.create_task(redis_polling_loop())
        logger.info("Redis polling task started")
        
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        # Don't fail startup - let it retry in background
        if not process_executor:
            process_executor = ProcessPoolExecutor(max_workers=2)
        redis_client = RedisCountsClient()
        asyncio.create_task(redis_client.start())
        redis_polling_task = asyncio.create_task(redis_polling_loop())
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Polarization Control API...")
    
    # Cancel Redis polling task
    if redis_polling_task and not redis_polling_task.done():
        redis_polling_task.cancel()
        try:
            await redis_polling_task
        except asyncio.CancelledError:
            pass
    
    # Stop clients
    if redis_client:
        await redis_client.stop()
    
    # Shutdown process executor  
    if process_executor:
        logger.info("Shutting down ProcessPoolExecutor...")
        process_executor.shutdown(wait=True, cancel_futures=True)
        logger.info("ProcessPoolExecutor shutdown completed")
    
    logger.info("Application shutdown completed")


app = FastAPI(
    title="Polarization Control API",
    description="REST API for controlling optical waveplates via ZMQ",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - Allow all origins for internal lab tool
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize persistent command history manager
command_history_manager = CommandHistoryManager()

# Operation status tracking for async ZMQ operations
operation_status = {}
operation_lock = asyncio.Lock()


# Pydantic models for request/response validation
class PolarizationSetRequest(BaseModel):
    setting: str = Field(..., description="Polarization setting to apply")


class CalibrateRequest(BaseModel):
    party: str = Field(..., description="Party to calibrate (alice, bob, or source)")


class PowerSetRequest(BaseModel):
    power: float = Field(..., ge=0.0, le=1.0, description="Power level between 0.0 and 1.0")


class HomeRequest(BaseModel):
    party: str = Field(..., description="Party to home (alice, bob, or source)")


class BellAnglesRequest(BaseModel):
    angles: Optional[List[float]] = Field(None, description="Optional angles array")


class CommandHistoryEntry(BaseModel):
    id: str = Field(..., description="Unique command ID")
    timestamp: str = Field(..., description="ISO timestamp when command was executed")
    command: str = Field(..., description="Command that was executed")
    response: str = Field(..., description="Response from the command")
    isError: bool = Field(False, description="Whether this was an error response")


class AddCommandRequest(BaseModel):
    command: str = Field(..., description="Command that was executed")
    response: str = Field(..., description="Response from the command")
    isError: bool = Field(False, description="Whether this was an error response")


class OperationStatus(BaseModel):
    operation_id: str = Field(..., description="Unique operation identifier")
    status: str = Field(..., description="Operation status: pending, running, completed, error")
    command: str = Field(..., description="Command being executed")
    result: Optional[str] = Field(None, description="Operation result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: str = Field(..., description="ISO timestamp when operation started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when operation completed")


class WaveplateMovementRequest(BaseModel):
    party: str = Field(..., description="Party (alice, bob, or source)")
    waveplate: str = Field(..., description="Name of the waveplate to move")
    position: float = Field(..., description="Position in degrees (relative for forward/backward, absolute for goto)")


class WaveplateMovementResponse(BaseModel):
    party: str = Field(..., description="Party that was moved")
    waveplate: str = Field(..., description="Name of waveplate that was moved")
    position: Optional[float] = Field(None, description="Current position after movement")


async def create_operation(command: str) -> str:
    """Create a new operation and return its ID"""
    operation_id = str(uuid.uuid4())
    async with operation_lock:
        operation_status[operation_id] = {
            "operation_id": operation_id,
            "status": "pending",
            "command": command,
            "result": None,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "completed_at": None
        }
    return operation_id


async def update_operation_status(operation_id: str, status: str, result: str = None, error: str = None):
    """Update operation status"""
    async with operation_lock:
        if operation_id in operation_status:
            operation_status[operation_id]["status"] = status
            if result is not None:
                operation_status[operation_id]["result"] = result
            if error is not None:
                operation_status[operation_id]["error"] = error
            if status in ["completed", "error"]:
                operation_status[operation_id]["completed_at"] = datetime.now().isoformat()



async def execute_zmq_operation(operation_id: str, operation_func, *args, **kwargs):
    """Execute ZMQ operation asynchronously with comprehensive error handling"""
    operation_info = None
    try:
        async with operation_lock:
            if operation_id not in operation_status:
                operations_logger.error(f"Operation {operation_id} not found in status tracking")
                return
            operation_info = operation_status[operation_id].copy()
        
        operations_logger.info(f"Starting operation {operation_id}: {operation_info['command']}")
        await update_operation_status(operation_id, "running")
        
        # Execute the ZMQ operation in a separate process to avoid GIL blocking
        command_name = operation_func.__name__
        operations_logger.debug(f"Executing ZMQ command '{command_name}' in subprocess")
        
        # Import the worker module for subprocess execution
        try:
            from . import zmq_worker
        except ImportError:
            import zmq_worker
        
        loop = asyncio.get_event_loop()
        subprocess_result = await loop.run_in_executor(
            process_executor,
            zmq_worker.execute_zmq_command,
            command_name,
            *args,
            **kwargs
        )
        
        # Handle subprocess result and error checking
        if not subprocess_result.get("success", False):
            error_msg = subprocess_result.get("error", "Unknown subprocess error")
            error_type = subprocess_result.get("error_type", "UnknownError")
            raise ZMQClientError(f"ZMQ subprocess {error_type}: {error_msg}")
        
        result = subprocess_result.get("result")
        operations_logger.info(f"Operation {operation_id} completed successfully")
        await update_operation_status(operation_id, "completed", result=str(result))
        
        # Add to command history using the persistent manager
        command_history_manager.add_command(
            command=operation_info["command"],
            response=str(result),
            is_error=False
            )
        
    except ZMQClientError as e:
        error_msg = f"ZMQ Error: {str(e)}"
        operations_logger.error(f"Operation {operation_id} failed with ZMQ error: {error_msg}")
        await update_operation_status(operation_id, "error", error=error_msg)
        
        # Add error to command history using the persistent manager
        command_history_manager.add_command(
            command=operation_info["command"] if operation_info else "Unknown",
            response=error_msg,
            is_error=True
            )
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        operations_logger.error(f"Operation {operation_id} failed with unexpected error: {error_msg}")
        logger.exception(f"Full exception details for operation {operation_id}")
        await update_operation_status(operation_id, "error", error=error_msg)
        
        # Add error to command history using the persistent manager
        command_history_manager.add_command(
            command=operation_info["command"] if operation_info else "Unknown",
            response=error_msg,
            is_error=True
            )
    
    finally:
        # Clean up old operations (keep only last 50)
        await cleanup_old_operations()


async def cleanup_old_operations():
    """Clean up old completed/errored operations to prevent memory leaks"""
    try:
        async with operation_lock:
            if len(operation_status) <= 50:
                return
            
            # Sort operations by completion time, keep most recent 50
            completed_ops = []
            for op_id, op_data in operation_status.items():
                if op_data["status"] in ["completed", "error"] and op_data.get("completed_at"):
                    completed_ops.append((op_data["completed_at"], op_id))
            
            if len(completed_ops) > 25:  # Keep 25 completed operations
                completed_ops.sort(reverse=True)  # Most recent first
                ops_to_remove = completed_ops[25:]  # Remove oldest
                
                for _, op_id in ops_to_remove:
                    operations_logger.debug(f"Cleaning up old operation: {op_id}")
                    del operation_status[op_id]
                    
    except Exception as e:
        logger.error(f"Error during operation cleanup: {e}")


@app.get("/")
async def root():
    return {"message": "Polarization Control API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    try:
        zmq_connected = False
        redis_connected = False
        
        if zmq_client:
            zmq_connected = zmq_client.test_connection()
        
        if redis_client:
            redis_connected = await redis_client.test_connection()
        
        overall_status = "healthy" if zmq_connected and redis_connected else "degraded"
        if not zmq_connected and not redis_connected:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "zmq_connection": zmq_connected,
            "redis_connection": redis_connected,
            "zmq_server": f"{config.zmq_host}:{config.zmq_port}",
            "redis_server": f"{config.redis_host}:{config.redis_port}"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "zmq_connection": False,
            "redis_connection": False
        }


@app.get("/paths")
async def get_paths():
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    try:
        result = zmq_client.get_paths()
        logger.info(f"get_paths result: {result}")
        return {"success": True, "data": result}
    except ZMQClientError as e:
        logger.error(f"ZMQ error in get_paths: {e}")
        raise HTTPException(status_code=503, detail=f"ZMQ communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_paths: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/polarization/set")
async def set_polarization(request: PolarizationSetRequest, background_tasks: BackgroundTasks):
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    
    command = f"Set Polarization: {request.setting}"
    operation_id = await create_operation(command)
    
    # Start async background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.set_polarization,
            request.setting
            )
        )
    
    return {
        "success": True,
        "message": f"Polarization operation started",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.post("/calibrate")
async def calibrate(request: CalibrateRequest, background_tasks: BackgroundTasks):
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    if request.party.lower() not in ["alice", "bob", "source"]:
        raise HTTPException(status_code=400, detail="Party must be 'alice', 'bob', or 'source'")
    
    command = f"Calibrate {request.party.capitalize()}"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.calibrate,
            request.party
        )
    )
    
    return {
        "success": True,
        "message": f"Calibration operation started for {request.party}",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.post("/power/set")
async def set_power(request: PowerSetRequest, background_tasks: BackgroundTasks):
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    command = f"Set Laser Power: {request.power}"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.set_power,
            request.power
        )
    )
    
    return {
        "success": True,
        "message": f"Power operation started",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.post("/home")
async def home(request: HomeRequest, background_tasks: BackgroundTasks):
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    if request.party.lower() not in ["alice", "bob", "source", "all"]:
        raise HTTPException(status_code=400, detail="Party must be 'alice', 'bob', 'source', or 'all'")
    
    command = f"Home {request.party.capitalize()}"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.home,
            request.party
        )
    )
    
    return {
        "success": True,
        "message": f"Homing operation started for {request.party}",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.post("/bell-angles/set")
async def set_bell_angles(request: BellAnglesRequest, background_tasks: BackgroundTasks):
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    command = "Set Bell Angles"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.set_pc_to_bell_angles,
            request.angles
        )
    )
    
    return {
        "success": True,
        "message": "Bell angles operation started",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.get("/info")
async def get_info():
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    try:
        result = zmq_client.get_info()
        return {"success": True, "data": result}
    except ZMQClientError as e:
        raise HTTPException(status_code=503, detail=f"ZMQ communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/commands")
async def get_commands():
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    try:
        result = zmq_client.get_commands()
        return {"success": True, "data": result}
    except ZMQClientError as e:
        raise HTTPException(status_code=503, detail=f"ZMQ communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_commands: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/positions")
async def get_positions():
    """Get current positions of all waveplates for all motor servers"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    try:
        result = zmq_client.get_all_positions()
        return {"success": True, "data": result}
    except ZMQClientError as e:
        raise HTTPException(status_code=503, detail=f"ZMQ communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/motor-info")
async def get_motor_info():
    """Get motor server information including waveplate names for each party"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    try:
        result = zmq_client.get_motor_info()
        logger.info(f"get_motor_info result: {result}")
        return {"success": True, "data": result}
    except ZMQClientError as e:
        logger.error(f"ZMQ error in get_motor_info: {e}")
        raise HTTPException(status_code=503, detail=f"ZMQ communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_motor_info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/current-path")
async def get_current_path():
    """Get the currently active polarization path"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    try:
        result = zmq_client.get_current_path()
        return {"success": True, "data": result}
    except ZMQClientError as e:
        raise HTTPException(status_code=503, detail=f"ZMQ communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_current_path: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/waveplate/forward")
async def move_waveplate_forward(request: WaveplateMovementRequest, background_tasks: BackgroundTasks):
    """Move specific waveplate forward by relative amount"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    command = f"Move {request.waveplate} forward {request.position}° on {request.party}"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.move_waveplate,
            request.party,
            request.waveplate,
            request.position,
            "forward"
        )
    )
    
    return {
        "success": True,
        "message": f"Forward movement operation started",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.post("/waveplate/backward")
async def move_waveplate_backward(request: WaveplateMovementRequest, background_tasks: BackgroundTasks):
    """Move specific waveplate backward by relative amount"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    command = f"Move {request.waveplate} backward {request.position}° on {request.party}"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.move_waveplate,
            request.party,
            request.waveplate,
            request.position,
            "backward"
        )
    )
    
    return {
        "success": True,
        "message": f"Backward movement operation started",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.post("/waveplate/goto")
async def move_waveplate_goto(request: WaveplateMovementRequest, background_tasks: BackgroundTasks):
    """Move specific waveplate to absolute position"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")
    command = f"Move {request.waveplate} to {request.position}° on {request.party}"
    operation_id = await create_operation(command)
    
    # Start background task
    asyncio.create_task(
        execute_zmq_operation(
            operation_id,
            zmq_client.move_waveplate,
            request.party,
            request.waveplate,
            request.position,
            "goto"
        )
    )
    
    return {
        "success": True,
        "message": f"Goto position operation started",
        "operation_id": operation_id,
        "status": "pending"
    }


@app.get("/redis/health")
async def redis_health_check():
    """Check Redis connection status"""
    if redis_client is None:
        return {
            "status": "unavailable",
            "redis_connection": False,
            "message": "Redis client not initialized"
        }
    
    try:
        is_connected = await redis_client.test_connection()
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "redis_connection": is_connected,
            "redis_server": f"{config.redis_host}:{config.redis_port}"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis_connection": False,
            "error": str(e)
        }


@app.get("/redis/counts")
async def get_redis_counts():
    """Get current counts data from Redis via background polling"""
    global latest_redis_data, latest_redis_timestamp
    
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis client not available")
    
    try:
        # Return data from background polling task - this prevents blocking
        if latest_redis_data is not None:
            # Check if data is recent (within last 2 seconds)
            if latest_redis_timestamp and (datetime.now() - latest_redis_timestamp).total_seconds() < 2.0:
                return {"success": True, "data": latest_redis_data}
        
        # No recent data available 
        logger.debug("No recent counts data available from background polling")
        return {
            "success": False, 
            "message": "No recent counts data available",
            "data": None
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in get_redis_counts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/redis/debug/stats")
async def get_redis_debug_stats():
    """Get Redis client debugging statistics"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis client not available")
    
    try:
        stats = redis_client.get_client_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Failed to get Redis debug stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Redis debug stats")


@app.post("/redis/debug/reset-position")
async def reset_redis_stream_position(position: str = '$'):
    """Reset Redis stream reading position ($ = latest, 0-0 = beginning)"""
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis client not available")
    
    try:
        old_position = redis_client.last_timestamp
        redis_client.reset_stream_position(position)
        return {
            "success": True, 
            "message": f"Stream position reset from {old_position} to {position}",
            "old_position": old_position,
            "new_position": position
        }
    except Exception as e:
        logger.error(f"Failed to reset Redis stream position: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset stream position")


@app.get("/commands/history")
async def get_command_history():
    """Get the command history with timestamps"""
    try:
        history_list = command_history_manager.get_history()
        
        return {
            "success": True,
            "data": history_list,
            "count": len(history_list)
        }
    except Exception as e:
        logger.error(f"Failed to get command history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get command history")


@app.post("/commands/add")
async def add_command_to_history(request: AddCommandRequest):
    """Add a command to the history with persistent storage"""
    try:
        command_entry = command_history_manager.add_command(
            command=request.command,
            response=request.response,
            is_error=request.isError
            )
        
        return {
            "success": True,
            "message": "Command added to history",
            "data": command_entry
        }
    except Exception as e:
        logger.error(f"Failed to add command to history: {e}")
        raise HTTPException(status_code=500, detail="Failed to add command to history")


@app.get("/commands/history/stats")
async def get_command_history_stats():
    """Get command history statistics"""
    try:
        stats = command_history_manager.get_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get command history stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get command history stats")


@app.get("/operations/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get the status of a specific operation"""
    async with operation_lock:
        if operation_id not in operation_status:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        return {
            "success": True,
            "data": operation_status[operation_id]
        }


@app.get("/operations")
async def get_all_operations():
    """Get status of all operations"""
    async with operation_lock:
        return {
            "success": True,
            "data": list(operation_status.values()),
            "count": len(operation_status)
        }


@app.get("/operations/health")
async def get_operations_health():
    """Get health status of background operations"""
    try:
        async with operation_lock:
            total_ops = len(operation_status)
            pending_ops = sum(1 for op in operation_status.values() if op["status"] == "pending")
            running_ops = sum(1 for op in operation_status.values() if op["status"] == "running")
            completed_ops = sum(1 for op in operation_status.values() if op["status"] == "completed")
            error_ops = sum(1 for op in operation_status.values() if op["status"] == "error")
            
            # Check for stale operations (running for more than 10 minutes)
            stale_ops = []
            now = datetime.now()
            for op_id, op_data in operation_status.items():
                if op_data["status"] == "running":
                    started = datetime.fromisoformat(op_data["started_at"])
                    if (now - started).total_seconds() > 600:  # 10 minutes
                        stale_ops.append(op_id)
            
            return {
                "success": True,
                "data": {
                    "total_operations": total_ops,
                    "pending": pending_ops,
                    "running": running_ops,
                    "completed": completed_ops,
                    "errors": error_ops,
                    "stale_operations": stale_ops,
                    "health_status": "healthy" if len(stale_ops) == 0 else "warning"
                }
            }
    except Exception as e:
        logger.error(f"Error getting operations health: {e}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.backend_port,
        reload=config.debug,
        log_level="info"
        )