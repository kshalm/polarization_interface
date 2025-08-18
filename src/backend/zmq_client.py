import json
import logging
from typing import Dict, Any, Optional
from zmqhelper import Client
try:
    from .config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)


class ZMQClientError(Exception):
    pass


class PolarizationZMQClient:
    def __init__(self):
        self.client = None
        self._connect()
    
    def _connect(self):
        try:
            self.client = Client(
                ip=config.zmq_host,
                port=config.zmq_port
            )
            logger.info(f"Connected to ZMQ server at {config.zmq_host}:{config.zmq_port}")
        except Exception as e:
            logger.error(f"Failed to connect to ZMQ server: {e}")
            raise ZMQClientError(f"Failed to connect to ZMQ server: {e}")
    
    def _get_fresh_connection(self):
        """Get a fresh ZMQ connection for each request to avoid state issues"""
        try:
            fresh_client = Client(
                ip=config.zmq_host,
                port=config.zmq_port
            )
            logger.debug(f"Created fresh ZMQ connection to {config.zmq_host}:{config.zmq_port}")
            return fresh_client
        except Exception as e:
            logger.error(f"Failed to create fresh ZMQ connection: {e}")
            raise ZMQClientError(f"Failed to create fresh ZMQ connection: {e}")
    
    def send_command(self, cmd: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        
        message = json.dumps({"cmd": cmd, "params": params})
        logger.debug(f"Sending ZMQ command: {message}")
        
        # Use fresh connection for each command to avoid state issues
        client = self._get_fresh_connection()
        
        try:
            response = client.send_message(message, timeout=config.zmq_timeout)
            logger.debug(f"Raw ZMQ response: {repr(response)}")
            
            # Check if response is empty or None
            if not response or response.strip() == "":
                logger.error("Received empty response from ZMQ server")
                raise ZMQClientError("Received empty response from ZMQ server")
            
            # Check for timeout response (not JSON)
            if response.strip().lower() == "timeout":
                logger.error("ZMQ server request timed out")
                raise ZMQClientError("ZMQ server request timed out - hardware may be unavailable")
            
            # Try to parse JSON response
            response_data = json.loads(response)
            logger.debug(f"Parsed ZMQ response: {response_data}")
            
            if "error" in response_data:
                raise ZMQClientError(f"ZMQ command error: {response_data['error']}")
            
            return response_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode ZMQ response: {e}. Raw response: {repr(response) if 'response' in locals() else 'No response'}")
            # Check if it's a known non-JSON response
            if 'response' in locals():
                response_str = str(response).strip().lower()
                if 'timeout' in response_str:
                    raise ZMQClientError("ZMQ server request timed out - hardware may be unavailable")
                elif 'error' in response_str:
                    raise ZMQClientError(f"ZMQ server error: {response}")
                else:
                    raise ZMQClientError(f"Invalid response format from ZMQ server: {repr(response)}")
            else:
                raise ZMQClientError(f"Failed to decode ZMQ response: {e}")
        except Exception as e:
            logger.error(f"ZMQ communication error: {e}")
            raise ZMQClientError(f"ZMQ communication error: {e}")
        finally:
            # Clean up the fresh connection
            try:
                if hasattr(client, 'close'):
                    client.close()
            except:
                pass
    
    def _reconnect(self):
        """Attempt to reconnect to the ZMQ server"""
        try:
            logger.info("Attempting to reconnect to ZMQ server...")
            self.client = Client(
                ip=config.zmq_host,
                port=config.zmq_port
            )
            logger.info(f"Reconnected to ZMQ server at {config.zmq_host}:{config.zmq_port}")
        except Exception as e:
            logger.error(f"Failed to reconnect to ZMQ server: {e}")
            raise ZMQClientError(f"Failed to reconnect to ZMQ server: {e}")
    
    def test_connection(self) -> bool:
        try:
            response = self.send_command("test")
            return response.get("message") == "Test successful"
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False
    
    def get_paths(self) -> Dict[str, Any]:
        try:
            # First get the settings from info command
            info_response = self.send_command("info")
            settings = info_response.get("message", {}).get("settings", {})
            
            # Return the available paths (settings keys)
            paths = list(settings.keys())
            return {"paths": paths, "settings": settings}
        except Exception as e:
            logger.error(f"Failed to get paths: {e}")
            raise ZMQClientError(f"Failed to get paths: {e}")
    
    def set_polarization(self, setting: str) -> Dict[str, Any]:
        return self.send_command("set_polarization", {"setting": setting})
    
    def calibrate(self, party: str) -> Dict[str, Any]:
        return self.send_command("calibrate", {"party": party.lower()})
    
    def set_power(self, power: float) -> Dict[str, Any]:
        if not (0.0 <= power <= 1.0):
            raise ValueError("Power must be between 0.0 and 1.0")
        return self.send_command("set_power", {"power": power})
    
    def home(self, party: str) -> Dict[str, Any]:
        return self.send_command("home", {"party": party.lower()})
    
    def set_pc_to_bell_angles(self, angles: Optional[list] = None) -> Dict[str, Any]:
        params = {}
        if angles:
            params["angles"] = angles
        return self.send_command("set_pc_to_bell_angles", params)
    
    def get_commands(self) -> Dict[str, Any]:
        return self.send_command("commands")
    
    def get_info(self) -> Dict[str, Any]:
        return self.send_command("info")
    
    # Additional methods that were added in newer versions, but kept synchronous
    def get_all_positions(self) -> Dict[str, Any]:
        """Get current positions of all waveplates for all motor servers"""
        return self.send_command("positions")

    def get_motor_info(self) -> Dict[str, Any]:
        """Get motor server information including waveplate names for each party"""
        result = self.send_command("get_motor_info")
        # ZMQ server returns {"message": motor_info_dict}, extract the motor info
        if isinstance(result, dict) and "message" in result:
            return result["message"]
        return result

    def get_current_path(self) -> Dict[str, Any]:
        """Get the currently active polarization path"""
        return self.send_command("get_current_path")

    def move_waveplate(self, party: str, waveplate: str, position: float, direction: str) -> Dict[str, Any]:
        """Move specific waveplate forward, backward, or to absolute position
        
        Args:
            party: alice, bob, or source
            waveplate: name of the waveplate to move
            position: degrees (relative for forward/backward, absolute for goto)  
            direction: 'forward', 'backward', or 'goto'
        """
        if direction not in ['forward', 'backward', 'goto']:
            raise ValueError("Direction must be 'forward', 'backward', or 'goto'")
        
        valid_parties = ['alice', 'bob', 'source']
        if party.lower() not in valid_parties:
            raise ValueError(f"Party must be one of: {', '.join(valid_parties)}")
        
        return self.send_command(direction, {
            "party": party.lower(),
            "waveplate": waveplate,
            "position": position
        })