import pytest
import asyncio
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from .main import app
from .zmq_client import PolarizationZMQClient, ZMQClientError


class TestIntegration:
    """Integration tests that test the full stack without actual ZMQ server"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_zmq_server_responses(self):
        """Mock responses that simulate the actual ZMQ server"""
        return {
            'test': '{"message": "Test successful"}',
            'info': json.dumps({
                "message": {
                    "status": "Running",
                    "name": "polarization_server",
                    "description": "Polarization control system",
                    "settings": {
                        "1": {"AHWP1": 0, "BHWP1": 0, "PHWP": 45},
                        "2": {"AHWP1": 45, "BHWP1": 45, "PHWP": 0},
                        "a_calib": {"AHWP1": 45, "BHWP1": 0, "PHWP": 45}
                    },
                    "uptime": "0:05:30"
                }
            }),
            'commands': json.dumps({
                "message": {
                    "1": {"cmd": "set_polarization", "description": "Set polarization"},
                    "2": {"cmd": "set_power", "description": "Set power"},
                    "3": {"cmd": "calibrate", "description": "Calibrate waveplates"},
                    "4": {"cmd": "positions", "description": "Get all positions"},
                    "5": {"cmd": "get_motor_info", "description": "Get motor info"},
                    "6": {"cmd": "get_current_path", "description": "Get current path"},
                    "7": {"cmd": "forward", "description": "Move forward"},
                    "8": {"cmd": "backward", "description": "Move backward"},
                    "9": {"cmd": "goto", "description": "Move to position"}
                }
            }),
            'set_polarization': '{"message": {"alice": {"alice_HWP_1": 0}, "bob": {"bob_HWP_1": 0}}}',
            'calibrate': '{"message": {"alice_HWP_1": 22.5, "bob_HWP_1": 22.5}}',
            'set_power': '{"message": 22.5}',
            'home': '{"message": "Homing completed"}',
            'set_pc_to_bell_angles': '{"message": {"alice": {"alice_HWP_1": 41.6}, "bob": {"bob_HWP_1": 59.6}}}',
            'positions': json.dumps({
                "message": {
                    "alice": {"alice_HWP_1": 45.23, "alice_QWP_1": 12.45},
                    "bob": {"bob_HWP_1": 32.15, "bob_QWP_1": 67.89},
                    "source": {"source_HWP_1": 15.67, "source_Power_1": 88.25}
                }
            }),
            'get_motor_info': json.dumps({
                "message": {
                    "alice": {"names": ["alice_HWP_1", "alice_QWP_1"], "ip": "192.168.1.100", "port": 5001},
                    "bob": {"names": ["bob_HWP_1", "bob_QWP_1"], "ip": "192.168.1.101", "port": 5002},
                    "source": {"names": ["source_HWP_1", "source_Power_1"], "ip": "192.168.1.102", "port": 5003}
                }
            }),
            'get_current_path': '{"message": {"current_path": "bell angles"}}',
            'forward': '{"message": {"party": "alice", "waveplate": "alice_HWP_1", "position": 47.5}}',
            'backward': '{"message": {"party": "alice", "waveplate": "alice_HWP_1", "position": 42.5}}',
            'goto': '{"message": {"party": "alice", "waveplate": "alice_HWP_1", "position": 45.0}}'
        }
    
    @patch('src.backend.zmq_client.Client')
    def test_full_polarization_workflow(self, mock_client_class, client, mock_zmq_server_responses):
        """Test complete polarization setting workflow"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock ZMQ responses
        mock_client.send_message.side_effect = [
            mock_zmq_server_responses['info'],  # For get_paths
            mock_zmq_server_responses['set_polarization']  # For set_polarization
        ]
        
        # First, get available paths
        response = client.get('/paths')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert '1' in data['data']['paths']
        
        # Then set polarization to path '1'
        response = client.post('/polarization/set', json={'setting': '1'})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'Polarization set to 1' in data['message']
        
        # Verify ZMQ calls
        expected_calls = [
            json.dumps({"cmd": "info", "params": {}}),
            json.dumps({"cmd": "set_polarization", "params": {"setting": "1"}})
        ]
        actual_calls = [call[0][0] for call in mock_client.send_message.call_args_list]
        assert actual_calls == expected_calls
    
    @patch('src.backend.zmq_client.Client')
    def test_full_calibration_workflow(self, mock_client_class, client, mock_zmq_server_responses):
        """Test complete calibration workflow"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = mock_zmq_server_responses['calibrate']
        
        # Test calibration for Alice
        response = client.post('/calibrate', json={'party': 'alice'})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'Calibration started for alice' in data['message']
        
        # Verify ZMQ call
        expected_message = json.dumps({"cmd": "calibrate", "params": {"party": "alice"}})
        mock_client.send_message.assert_called_with(expected_message, timeout=120000)
    
    @patch('src.backend.zmq_client.Client')
    def test_full_power_setting_workflow(self, mock_client_class, client, mock_zmq_server_responses):
        """Test complete power setting workflow"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = mock_zmq_server_responses['set_power']
        
        # Test power setting
        response = client.post('/power/set', json={'power': 0.5})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'Power set to 0.5' in data['message']
        
        # Verify ZMQ call
        expected_message = json.dumps({"cmd": "set_power", "params": {"power": 0.5}})
        mock_client.send_message.assert_called_with(expected_message, timeout=120000)
    
    @patch('src.backend.zmq_client.Client')
    def test_full_homing_workflow(self, mock_client_class, client, mock_zmq_server_responses):
        """Test complete homing workflow"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = mock_zmq_server_responses['home']
        
        # Test homing Alice
        response = client.post('/home', json={'party': 'alice'})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'Homing alice' in data['message']
        
        # Verify ZMQ call
        expected_message = json.dumps({"cmd": "home", "params": {"party": "alice"}})
        mock_client.send_message.assert_called_with(expected_message, timeout=120000)
    
    @patch('src.backend.zmq_client.Client')
    def test_error_handling_throughout_stack(self, mock_client_class, client):
        """Test error handling propagation through the entire stack"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Simulate ZMQ server error
        mock_client.send_message.return_value = '{"error": "ZMQ server internal error"}'
        
        # Test that error propagates correctly
        response = client.post('/polarization/set', json={'setting': '1'})
        assert response.status_code == 400
        assert 'ZMQ server internal error' in response.json()['detail']
    
    @patch('src.backend.zmq_client.Client')
    def test_health_check_integration(self, mock_client_class, client, mock_zmq_server_responses):
        """Test health check integration"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = mock_zmq_server_responses['test']
        
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['zmq_connection'] is True
        assert ':5100' in data['zmq_server']
    
    @patch('src.backend.zmq_client.Client')
    def test_concurrent_requests(self, mock_client_class, client, mock_zmq_server_responses):
        """Test handling of concurrent requests"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = mock_zmq_server_responses['set_polarization']
        
        # Simulate concurrent requests
        responses = []
        for i in range(5):
            response = client.post('/polarization/set', json={'setting': '1'})
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()['success'] is True
    
    @patch('src.backend.zmq_client.Client')
    def test_input_validation_integration(self, mock_client_class, client):
        """Test input validation across the API"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Test invalid power values
        response = client.post('/power/set', json={'power': 1.5})
        assert response.status_code == 422  # Pydantic validation error
        
        response = client.post('/power/set', json={'power': -0.5})
        assert response.status_code == 422
        
        # Test invalid party values
        response = client.post('/calibrate', json={'party': 'invalid_party'})
        assert response.status_code == 400
        
        response = client.post('/home', json={'party': 'invalid_party'})
        assert response.status_code == 400
    
    @patch('src.backend.zmq_client.Client')
    def test_timeout_handling(self, mock_client_class, client):
        """Test timeout handling in ZMQ communication"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Simulate timeout
        import socket
        mock_client.send_message.side_effect = socket.timeout("Timeout")
        
        response = client.post('/polarization/set', json={'setting': '1'})
        assert response.status_code == 400
        assert 'timeout' in response.json()['detail'].lower()
    
    @patch('src.backend.zmq_client.Client')
    def test_positions_endpoint(self, mock_client_class, client):
        """Test the new positions endpoint"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = json.dumps({
            "message": {
                "alice": {
                    "alice_HWP_1": 45.23,
                    "alice_QWP_1": 12.45,
                    "alice_HWP_2": 78.90
                },
                "bob": {
                    "bob_HWP_1": 32.15,
                    "bob_QWP_1": 67.89,
                    "bob_HWP_2": 91.23
                },
                "source": {
                    "source_HWP_1": 15.67,
                    "source_Power_1": 88.25
                }
            }
        })
        mock_client.send_message.return_value = mock_response
        
        response = client.get('/positions')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'alice' in data['data']['message']
        assert 'bob' in data['data']['message']
        assert 'source' in data['data']['message']
    
    @patch('src.backend.zmq_client.Client')
    def test_motor_info_endpoint(self, mock_client_class, client):
        """Test the new motor-info endpoint"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = json.dumps({
            "message": {
                "alice": {
                    "names": ["alice_HWP_1", "alice_QWP_1", "alice_HWP_2"],
                    "ip": "192.168.1.100",
                    "port": 5001
                },
                "bob": {
                    "names": ["bob_HWP_1", "bob_QWP_1", "bob_HWP_2"],
                    "ip": "192.168.1.101",
                    "port": 5002
                },
                "source": {
                    "names": ["source_HWP_1", "source_Power_1"],
                    "ip": "192.168.1.102",
                    "port": 5003
                }
            }
        })
        mock_client.send_message.return_value = mock_response
        
        response = client.get('/motor-info')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']['message']['alice']['names']) == 3
        assert len(data['data']['message']['bob']['names']) == 3
        assert len(data['data']['message']['source']['names']) == 2
    
    @patch('src.backend.zmq_client.Client')
    def test_current_path_endpoint(self, mock_client_class, client):
        """Test the new current-path endpoint"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = json.dumps({
            "message": {"current_path": "bell angles"}
        })
        mock_client.send_message.return_value = mock_response
        
        response = client.get('/current-path')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['message']['current_path'] == "bell angles"
    
    @patch('src.backend.zmq_client.Client')
    def test_waveplate_movement_endpoints(self, mock_client_class, client):
        """Test the new waveplate movement endpoints"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_response = json.dumps({
            "message": {
                "party": "alice",
                "waveplate": "alice_HWP_1",
                "position": 47.5
            }
        })
        mock_client.send_message.return_value = mock_response
        
        # Test forward movement
        response = client.post('/waveplate/forward', json={
            'party': 'alice',
            'waveplate': 'alice_HWP_1',
            'position': 2.5
        })
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert 'operation_id' in response.json()
        
        # Test backward movement
        response = client.post('/waveplate/backward', json={
            'party': 'alice',
            'waveplate': 'alice_HWP_1', 
            'position': 2.5
        })
        assert response.status_code == 200
        assert response.json()['success'] is True
        
        # Test goto movement
        response = client.post('/waveplate/goto', json={
            'party': 'alice',
            'waveplate': 'alice_HWP_1',
            'position': 45.0
        })
        assert response.status_code == 200
        assert response.json()['success'] is True
    
    @patch('src.backend.zmq_client.Client')
    def test_waveplate_movement_validation(self, mock_client_class, client):
        """Test validation for waveplate movement endpoints"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Test missing required fields
        response = client.post('/waveplate/forward', json={
            'party': 'alice',
            'position': 2.5
            # missing waveplate
        })
        assert response.status_code == 422  # Pydantic validation error
        
        # Test invalid party
        response = client.post('/waveplate/forward', json={
            'party': 'invalid',
            'waveplate': 'alice_HWP_1',
            'position': 2.5
        })
        assert response.status_code == 400


class TestSelfTests:
    """Self-test functionality for the system"""
    
    @patch('src.backend.zmq_client.Client')
    def test_zmq_connection_self_test(self, mock_client_class):
        """Test ZMQ connection self-test"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = '{"message": "Test successful"}'
        
        # Create ZMQ client and test connection
        zmq_client = PolarizationZMQClient()
        result = zmq_client.test_connection()
        
        assert result is True
        expected_message = json.dumps({"cmd": "test", "params": {}})
        mock_client.send_message.assert_called_with(expected_message, timeout=120000)
    
    @patch('src.backend.zmq_client.Client')
    def test_zmq_connection_self_test_failure(self, mock_client_class):
        """Test ZMQ connection self-test failure"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.side_effect = Exception("Connection failed")
        
        zmq_client = PolarizationZMQClient()
        result = zmq_client.test_connection()
        
        assert result is False
    
    @patch('src.backend.zmq_client.Client')
    def test_command_validation_self_test(self, mock_client_class):
        """Test that all required commands are available"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock commands response
        commands_response = {
            "message": {
                "1": {"cmd": "set_polarization"},
                "2": {"cmd": "set_power"}, 
                "3": {"cmd": "calibrate"},
                "4": {"cmd": "home"},
                "5": {"cmd": "set_pc_to_bell_angles"},
                "6": {"cmd": "get_paths"},
                "7": {"cmd": "test"}
            }
        }
        mock_client.send_message.return_value = json.dumps(commands_response)
        
        zmq_client = PolarizationZMQClient()
        result = zmq_client.get_commands()
        
        # Verify essential commands are present
        commands = result['message']
        command_names = [cmd['cmd'] for cmd in commands.values()]
        
        essential_commands = [
            'set_polarization', 'set_power', 'calibrate', 
            'home', 'set_pc_to_bell_angles'
        ]
        
        for essential_cmd in essential_commands:
            assert essential_cmd in command_names
    
    def test_configuration_self_test(self):
        """Test configuration loading and validation"""
        from .config import config
        
        # Test that all required config values are present
        assert config.zmq_host is not None
        assert config.zmq_port is not None
        assert config.zmq_timeout > 0
        assert config.backend_port is not None
        assert config.frontend_port is not None
        
        # Test specific values match expectations
        assert config.zmq_host is not None  # Don't hardcode sensitive hostnames
        assert config.zmq_port == 5100
        assert config.zmq_timeout == 120000  # Should be in milliseconds
        assert config.backend_port == 8000
        assert config.frontend_port == 8085