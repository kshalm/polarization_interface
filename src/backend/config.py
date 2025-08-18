import yaml
import os
from pathlib import Path


class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Try Docker path first (/app/config/app.yaml), then local development path
            docker_path = Path("/app/config/app.yaml")
            local_path = Path(__file__).parent.parent.parent / "config" / "app.yaml"
            
            if docker_path.exists():
                config_path = docker_path
            else:
                config_path = local_path
        
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    @property
    def zmq_host(self) -> str:
        return self._config['zmq_server']['host']
    
    @property
    def zmq_port(self) -> int:
        return self._config['zmq_server']['port']
    
    @property
    def zmq_timeout(self) -> int:
        return self._config['zmq_server']['timeout'] * 1000  # Convert to ms
    
    @property
    def backend_port(self) -> int:
        return self._config['web_app']['backend_port']
    
    @property
    def frontend_port(self) -> int:
        return self._config['web_app']['frontend_port']
    
    @property
    def cors_origins(self) -> list:
        return self._config['development']['cors_origins']
    
    @property
    def debug(self) -> bool:
        return self._config['development']['debug']
    
    @property
    def redis_host(self) -> str:
        return self._config['redis_server']['host']
    
    @property
    def redis_port(self) -> int:
        return self._config['redis_server']['port']
    
    @property
    def redis_db(self) -> int:
        return self._config['redis_server']['db']
    
    @property
    def redis_refresh_rate(self) -> int:
        return self._config['redis_server']['refresh_rate']
    
    @property
    def zmq_retry_config(self) -> dict:
        return self._config['zmq_server']['connection_retry']
    
    @property
    def redis_retry_config(self) -> dict:
        return self._config['redis_server']['connection_retry']


config = Config()