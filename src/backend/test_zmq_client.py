import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from .zmq_client import PolarizationZMQClient, ZMQClientError


class TestPolarizationZMQClient:
    
    @patch('src.backend.zmq_client.Client')
    def test_init_success(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        client = PolarizationZMQClient()
        
        mock_client_class.assert_called_once_with(ip='test-zmq-server', port=5100)
        assert client.client == mock_client
    
    @patch('src.backend.zmq_client.Client')
    def test_init_connection_failure(self, mock_client_class):
        mock_client_class.side_effect = Exception("Connection failed")
        
        with pytest.raises(ZMQClientError, match="Failed to connect to ZMQ server"):
            PolarizationZMQClient()
    
    @patch('src.backend.zmq_client.Client')
    def test_send_command_success(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Test successful"}'
        
        client = PolarizationZMQClient()
        result = client.send_command("test")
        
        expected_message = json.dumps({"cmd": "test", "params": {}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Test successful"}
    
    @patch('src.backend.zmq_client.Client')
    def test_send_command_with_params(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Command executed"}'
        
        client = PolarizationZMQClient()
        params = {"setting": "1"}
        result = client.send_command("set_polarization", params)
        
        expected_message = json.dumps({"cmd": "set_polarization", "params": params})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Command executed"}
    
    @patch('src.backend.zmq_client.Client')
    def test_send_command_error_response(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"error": "Invalid command"}'
        
        client = PolarizationZMQClient()
        
        with pytest.raises(ZMQClientError, match="ZMQ command error: Invalid command"):
            client.send_command("invalid_command")
    
    @patch('src.backend.zmq_client.Client')
    def test_send_command_json_decode_error(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = 'invalid json'
        
        client = PolarizationZMQClient()
        
        with pytest.raises(ZMQClientError, match="Failed to decode ZMQ response"):
            client.send_command("test")
    
    @patch('src.backend.zmq_client.Client')
    def test_test_connection_success(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Test successful"}'
        
        client = PolarizationZMQClient()
        result = client.test_connection()
        
        assert result is True
    
    @patch('src.backend.zmq_client.Client')
    def test_test_connection_failure(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.side_effect = Exception("Connection failed")
        
        client = PolarizationZMQClient()
        result = client.test_connection()
        
        assert result is False
    
    @patch('src.backend.zmq_client.Client')
    def test_get_paths(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = {
            "message": {
                "settings": {
                    "1": {"AHWP1": 0, "BHWP1": 0, "PHWP": 45},
                    "2": {"AHWP1": 45, "BHWP1": 45, "PHWP": 0}
                }
            }
        }
        mock_client.send_message.return_value = json.dumps(mock_response)
        
        client = PolarizationZMQClient()
        result = client.get_paths()
        
        expected = {
            "paths": ["1", "2"],
            "settings": {
                "1": {"AHWP1": 0, "BHWP1": 0, "PHWP": 45},
                "2": {"AHWP1": 45, "BHWP1": 45, "PHWP": 0}
            }
        }
        assert result == expected
    
    @patch('src.backend.zmq_client.Client')
    def test_set_polarization(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Polarization set"}'
        
        client = PolarizationZMQClient()
        result = client.set_polarization("1")
        
        expected_message = json.dumps({"cmd": "set_polarization", "params": {"setting": "1"}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Polarization set"}
    
    @patch('src.backend.zmq_client.Client')
    def test_calibrate(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Calibration started"}'
        
        client = PolarizationZMQClient()
        result = client.calibrate("Alice")
        
        expected_message = json.dumps({"cmd": "calibrate", "params": {"party": "alice"}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Calibration started"}
    
    @patch('src.backend.zmq_client.Client')
    def test_set_power_valid(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Power set"}'
        
        client = PolarizationZMQClient()
        result = client.set_power(0.5)
        
        expected_message = json.dumps({"cmd": "set_power", "params": {"power": 0.5}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Power set"}
    
    @patch('src.backend.zmq_client.Client')
    def test_set_power_invalid_range(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        client = PolarizationZMQClient()
        
        with pytest.raises(ValueError, match="Power must be between 0.0 and 1.0"):
            client.set_power(1.5)
        
        with pytest.raises(ValueError, match="Power must be between 0.0 and 1.0"):
            client.set_power(-0.1)
    
    @patch('src.backend.zmq_client.Client')
    def test_home(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Homing started"}'
        
        client = PolarizationZMQClient()
        result = client.home("Bob")
        
        expected_message = json.dumps({"cmd": "home", "params": {"party": "bob"}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Homing started"}
    
    @patch('src.backend.zmq_client.Client')
    def test_set_pc_to_bell_angles_no_angles(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Bell angles set"}'
        
        client = PolarizationZMQClient()
        result = client.set_pc_to_bell_angles()
        
        expected_message = json.dumps({"cmd": "set_pc_to_bell_angles", "params": {}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Bell angles set"}
    
    @patch('src.backend.zmq_client.Client')
    def test_set_pc_to_bell_angles_with_angles(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Bell angles set"}'
        
        client = PolarizationZMQClient()
        angles = [41.6, 59.6, 33.8]
        result = client.set_pc_to_bell_angles(angles)
        
        expected_message = json.dumps({"cmd": "set_pc_to_bell_angles", "params": {"angles": angles}})
        mock_client.send_message.assert_called_once_with(expected_message, timeout=120000)
        assert result == {"message": "Bell angles set"}