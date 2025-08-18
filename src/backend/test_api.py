import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from .main import app
from .zmq_client import ZMQClientError


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_zmq_client():
    with patch('src.backend.main.zmq_client') as mock:
        yield mock


class TestAPI:
    
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Polarization Control API"
        assert data["version"] == "1.0.0"
    
    def test_health_check_healthy(self, client, mock_zmq_client):
        mock_zmq_client.test_connection.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["zmq_connection"] is True
    
    def test_health_check_degraded(self, client, mock_zmq_client):
        mock_zmq_client.test_connection.return_value = False
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["zmq_connection"] is False
    
    def test_health_check_exception(self, client, mock_zmq_client):
        mock_zmq_client.test_connection.side_effect = Exception("Connection error")
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["zmq_connection"] is False
    
    def test_get_paths_success(self, client, mock_zmq_client):
        mock_paths_data = {
            "paths": ["1", "2", "a_calib"],
            "settings": {"1": {"AHWP1": 0}, "2": {"AHWP1": 45}}
        }
        mock_zmq_client.get_paths.return_value = mock_paths_data
        
        response = client.get("/paths")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_paths_data
    
    def test_get_paths_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.get_paths.side_effect = ZMQClientError("ZMQ connection failed")
        
        response = client.get("/paths")
        assert response.status_code == 503
        assert "ZMQ communication error" in response.json()["detail"]
    
    def test_set_polarization_success(self, client, mock_zmq_client):
        mock_zmq_client.set_polarization.return_value = {"message": "Polarization set"}
        
        response = client.post("/polarization/set", json={"setting": "1"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Polarization set to 1" in data["message"]
        mock_zmq_client.set_polarization.assert_called_once_with("1")
    
    def test_set_polarization_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.set_polarization.side_effect = ZMQClientError("Invalid setting")
        
        response = client.post("/polarization/set", json={"setting": "invalid"})
        assert response.status_code == 400
        assert "Invalid setting" in response.json()["detail"]
    
    def test_calibrate_success(self, client, mock_zmq_client):
        mock_zmq_client.calibrate.return_value = {"message": "Calibration started"}
        
        response = client.post("/calibrate", json={"party": "alice"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Calibration started for alice" in data["message"]
        mock_zmq_client.calibrate.assert_called_once_with("alice")
    
    def test_calibrate_invalid_party(self, client, mock_zmq_client):
        response = client.post("/calibrate", json={"party": "invalid"})
        assert response.status_code == 400
        assert "Party must be" in response.json()["detail"]
    
    def test_calibrate_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.calibrate.side_effect = ZMQClientError("Calibration failed")
        
        response = client.post("/calibrate", json={"party": "alice"})
        assert response.status_code == 400
        assert "Calibration failed" in response.json()["detail"]
    
    def test_set_power_success(self, client, mock_zmq_client):
        mock_zmq_client.set_power.return_value = {"message": "Power set"}
        
        response = client.post("/power/set", json={"power": 0.5})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Power set to 0.5" in data["message"]
        mock_zmq_client.set_power.assert_called_once_with(0.5)
    
    def test_set_power_invalid_range_too_high(self, client):
        response = client.post("/power/set", json={"power": 1.5})
        assert response.status_code == 422  # Pydantic validation error
    
    def test_set_power_invalid_range_too_low(self, client):
        response = client.post("/power/set", json={"power": -0.5})
        assert response.status_code == 422  # Pydantic validation error
    
    def test_set_power_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.set_power.side_effect = ZMQClientError("Power setting failed")
        
        response = client.post("/power/set", json={"power": 0.5})
        assert response.status_code == 400
        assert "Power setting failed" in response.json()["detail"]
    
    def test_home_success(self, client, mock_zmq_client):
        mock_zmq_client.home.return_value = {"message": "Homing started"}
        
        response = client.post("/home", json={"party": "alice"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Homing alice" in data["message"]
        mock_zmq_client.home.assert_called_once_with("alice")
    
    def test_home_invalid_party(self, client, mock_zmq_client):
        response = client.post("/home", json={"party": "invalid"})
        assert response.status_code == 400
        assert "Party must be" in response.json()["detail"]
    
    def test_home_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.home.side_effect = ZMQClientError("Homing failed")
        
        response = client.post("/home", json={"party": "alice"})
        assert response.status_code == 400
        assert "Homing failed" in response.json()["detail"]
    
    def test_set_bell_angles_no_angles(self, client, mock_zmq_client):
        mock_zmq_client.set_pc_to_bell_angles.return_value = {"message": "Bell angles set"}
        
        response = client.post("/bell-angles/set", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Bell angles set" in data["message"]
        mock_zmq_client.set_pc_to_bell_angles.assert_called_once_with(None)
    
    def test_set_bell_angles_with_angles(self, client, mock_zmq_client):
        mock_zmq_client.set_pc_to_bell_angles.return_value = {"message": "Bell angles set"}
        angles = [41.6, 59.6, 33.8]
        
        response = client.post("/bell-angles/set", json={"angles": angles})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_zmq_client.set_pc_to_bell_angles.assert_called_once_with(angles)
    
    def test_set_bell_angles_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.set_pc_to_bell_angles.side_effect = ZMQClientError("Bell angles failed")
        
        response = client.post("/bell-angles/set", json={})
        assert response.status_code == 400
        assert "Bell angles failed" in response.json()["detail"]
    
    def test_get_info_success(self, client, mock_zmq_client):
        mock_info = {"message": {"status": "Running", "name": "polarization_server"}}
        mock_zmq_client.get_info.return_value = mock_info
        
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_info
    
    def test_get_info_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.get_info.side_effect = ZMQClientError("Info request failed")
        
        response = client.get("/info")
        assert response.status_code == 503
        assert "ZMQ communication error" in response.json()["detail"]
    
    def test_get_commands_success(self, client, mock_zmq_client):
        mock_commands = {"message": {"1": {"cmd": "set_polarization"}}}
        mock_zmq_client.get_commands.return_value = mock_commands
        
        response = client.get("/commands")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_commands
    
    def test_get_commands_zmq_error(self, client, mock_zmq_client):
        mock_zmq_client.get_commands.side_effect = ZMQClientError("Commands request failed")
        
        response = client.get("/commands")
        assert response.status_code == 503
        assert "ZMQ communication error" in response.json()["detail"]