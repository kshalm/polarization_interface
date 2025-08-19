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
        """Get CORS origins with support for dynamic host configuration"""
        import os
        
        # Get static origins from config
        if 'cors' in self._config and 'allowed_origins' in self._config['cors']:
            base_origins = list(self._config['cors']['allowed_origins'])  # Make a copy
        else:
            # Fallback for older config format or missing config
            base_origins = ["http://localhost:8085", "http://127.0.0.1:8085"]
        
        # Add dynamic origins based on environment variables
        backend_host = os.getenv('BACKEND_HOST')
        frontend_port = self.frontend_port
        
        if backend_host and backend_host != 'localhost':
            # Add the frontend URL for the detected/configured backend host
            dynamic_origin = f"http://{backend_host}:{frontend_port}"
            if dynamic_origin not in base_origins:
                base_origins.append(dynamic_origin)
        
        # For production deployments, also check for common hostname patterns
        # Check if we're in a production environment (not localhost)
        if backend_host and backend_host != 'localhost' and not backend_host.startswith('127.'):
            # Add additional origin patterns for cross-hostname scenarios
            # This handles cases where frontend and backend hostnames resolve differently
            
            # If BACKEND_HOST is an IP, also allow the hostname equivalent
            additional_origins = []
            
            # Allow both HTTP and HTTPS for the backend host
            additional_origins.append(f"https://{backend_host}:{frontend_port}")
            
            # For government/institutional networks, allow .gov domains with the same IP pattern
            # but only add generic patterns, not specific sensitive hostnames
            if '.' in backend_host:
                # Split IP/hostname to see if we can infer network patterns
                parts = backend_host.split('.')
                if len(parts) >= 2:
                    # Add common institutional domain patterns (without exposing sensitive names)
                    # This is a placeholder - we would normally configure this properly
                    pass
            
            for origin in additional_origins:
                if origin not in base_origins:
                    base_origins.append(origin)
        
        # Add environment-specific CORS override
        cors_override = os.getenv('CORS_ALLOW_ORIGINS')
        if cors_override:
            # Allow manual override via environment variable for specific deployments
            additional_origins = [origin.strip() for origin in cors_override.split(',')]
            for origin in additional_origins:
                if origin not in base_origins:
                    base_origins.append(origin)
        
        return base_origins
    
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