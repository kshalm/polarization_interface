import React, { useState, useEffect } from 'react';
import { polarizationAPI } from '../services/api';

const ConnectionStatus = () => {
  const [connectionStatus, setConnectionStatus] = useState({
    status: 'checking',
    zmq_connection: false,
    zmq_server: '',
    lastCheck: null
  });

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const checkConnection = async () => {
    try {
      const response = await polarizationAPI.healthCheck();
      setConnectionStatus({
        ...response.data,
        lastCheck: new Date()
      });
    } catch (error) {
      setConnectionStatus({
        status: 'error',
        zmq_connection: false,
        zmq_server: 'Unknown',
        lastCheck: new Date(),
        error: error.message
      });
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus.status) {
      case 'healthy':
        return 'text-success';
      case 'degraded':
        return 'text-warning';
      case 'checking':
        return 'text-primary';
      default:
        return 'text-danger';
    }
  };

  const getStatusIcon = () => {
    switch (connectionStatus.status) {
      case 'healthy':
        return '🟢';
      case 'degraded':
        return '🟡';
      case 'checking':
        return '🔵';
      default:
        return '🔴';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus.status) {
      case 'healthy':
        return 'Connected';
      case 'degraded':
        return 'Backend Connected, ZMQ Disconnected';
      case 'checking':
        return 'Checking...';
      default:
        return 'Disconnected';
    }
  };

  return (
    <div className="card card-flat mb-3">
      <div className="card-body py-2">
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center">
            <span className="me-2">{getStatusIcon()}</span>
            <span className={`fw-bold ${getStatusColor()}`}>
              System Status: {getStatusText()}
            </span>
          </div>
          <div className="d-flex align-items-center gap-3">
            {connectionStatus.zmq_server && (
              <small className="text-muted">
                ZMQ: {connectionStatus.zmq_server}
              </small>
            )}
            <button
              className="btn btn-sm btn-outline-secondary"
              onClick={checkConnection}
              title="Refresh connection status"
            >
              🔄
            </button>
          </div>
        </div>
        {connectionStatus.lastCheck && (
          <small className="text-muted">
            Last checked: {connectionStatus.lastCheck.toLocaleTimeString()}
          </small>
        )}
        {connectionStatus.error && (
          <div className="mt-1">
            <small className="text-danger">
              Error: {connectionStatus.error}
            </small>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConnectionStatus;