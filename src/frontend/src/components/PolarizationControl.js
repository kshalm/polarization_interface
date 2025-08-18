import React, { useState, useEffect } from 'react';
import { polarizationAPI } from '../services/api';
import { useApp } from '../contexts/AppContext';

const PolarizationControl = () => {
  const [selectedPath, setSelectedPath] = useState('');
  const [availablePaths, setAvailablePaths] = useState([]);
  const [currentPath, setCurrentPath] = useState(null);
  const { pendingOperations, startOperation } = useApp();

  useEffect(() => {
    loadAvailablePaths();
    loadCurrentPath();

    // Set up periodic polling for current path updates every 5 seconds
    const interval = setInterval(loadCurrentPath, 5000);

    return () => clearInterval(interval);
  }, []);

  const loadAvailablePaths = async () => {
    try {
      const response = await polarizationAPI.getPaths();
      console.log('Full paths response:', response);
      console.log('Response data:', response.data);
      
      if (response.data.success) {
        const paths = response.data.data.paths || [];
        console.log('Extracted paths:', paths);
        setAvailablePaths(paths);
        if (paths.length > 0) {
          setSelectedPath(paths[0]);
        }
      } else {
        console.error('Paths request failed:', response.data);
      }
    } catch (error) {
      console.error('Failed to load paths:', error);
      console.error('Error details:', error.response || error);
    }
  };

  const loadCurrentPath = async () => {
    try {
      const response = await polarizationAPI.getCurrentPath();
      if (response.data.success) {
        const currentPathValue = response.data.data.message?.current_path;
        setCurrentPath(currentPathValue);
      }
    } catch (error) {
      console.error('Failed to load current path:', error);
    }
  };

  const handleSetPolarization = async () => {
    if (!selectedPath) {
      return;
    }

    try {
      let response;
      
      if (selectedPath === 'Bell Angles') {
        response = await polarizationAPI.setBellAngles();
      } else {
        response = await polarizationAPI.setPolarization(selectedPath);
      }

      if (response.data.success && response.data.operation_id) {
        // Start tracking the operation
        startOperation(response.data.operation_id);
        
        // Update current path immediately to provide real-time feedback
        if (selectedPath === 'Bell Angles') {
          setCurrentPath('bell angles');
        } else {
          setCurrentPath(selectedPath);
        }
      }
    } catch (error) {
      console.error('Failed to start operation:', error);
    }
  };

  const getDisplayOptions = () => {
    const options = ['Bell Angles', ...availablePaths];
    return options;
  };

  const getCardTitle = () => {
    if (!currentPath) {
      return 'Polarization State';
    }
    
    if (currentPath.toLowerCase() === 'bell angles') {
      return 'Polarization State: Bell Angles';
    }
    
    return `Polarization State: Current path ${currentPath}`;
  };

  return (
    <div className="card card-flat control-section">
      <div className="card-header card-header-flat">
        <h5 className="mb-0">{getCardTitle()}</h5>
      </div>
      <div className="card-body">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="polarization-select" className="form-label">
              Select Polarization Path:
            </label>
            <select
              id="polarization-select"
              className="form-select form-select-flat"
              value={selectedPath}
              onChange={(e) => setSelectedPath(e.target.value)}
              disabled={pendingOperations.size > 0}
            >
              {getDisplayOptions().map((path) => (
                <option key={path} value={path}>
                  {path === 'Bell Angles' ? 'Bell Angles' : path}
                </option>
              ))}
            </select>
          </div>
          <div className="set-button">
            <button
              className="btn btn-flat-primary"
              onClick={handleSetPolarization}
              disabled={pendingOperations.size > 0 || !selectedPath}
            >
              {pendingOperations.size > 0 ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Setting...
                </>
              ) : (
                'Set'
              )}
            </button>
          </div>
        </div>
        <div className="mt-2">
          <small className="text-muted">
            Available paths: {availablePaths.length > 0 ? availablePaths.join(', ') : 'Loading...'}
          </small>
        </div>
      </div>
    </div>
  );
};

export default PolarizationControl;