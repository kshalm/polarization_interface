import React, { useState } from 'react';
import { polarizationAPI } from '../services/api';
import { useApp } from '../contexts/AppContext';

const LaserPower = () => {
  const [power, setPower] = useState('');
  const [error, setError] = useState('');
  const { pendingOperations, startOperation } = useApp();

  const validatePower = (value) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      return 'Power must be a valid number';
    }
    if (numValue < 0.0 || numValue > 1.0) {
      return 'Power must be between 0.0 and 1.0';
    }
    return null;
  };

  const handlePowerChange = (e) => {
    const value = e.target.value;
    setPower(value);
    
    if (value && validatePower(value)) {
      setError(validatePower(value));
    } else {
      setError('');
    }
  };

  const handleSetPower = async () => {
    const validation = validatePower(power);
    if (validation) {
      setError(validation);
      return;
    }

    if (!power) {
      setError('Please enter a power value');
      return;
    }

    setError('');
    
    try {
      const response = await polarizationAPI.setPower(parseFloat(power));

      if (response.data.success && response.data.operation_id) {
        startOperation(response.data.operation_id);
        setPower(''); // Clear input on success
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to set power';
      setError(errorMessage);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSetPower();
    }
  };

  return (
    <div className="card card-flat control-section">
      <div className="card-header card-header-flat">
        <h5 className="mb-0">Set Laser Power</h5>
      </div>
      <div className="card-body">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="power-input" className="form-label">
              Power Level (0.0 - 1.0):
            </label>
            <input
              id="power-input"
              type="number"
              className="form-control form-control-flat"
              value={power}
              onChange={handlePowerChange}
              onKeyPress={handleKeyPress}
              min="0.0"
              max="1.0"
              step="0.01"
              placeholder="Enter power (e.g., 0.5)"
              disabled={pendingOperations.size > 0}
            />
          </div>
          <div className="set-button">
            <button
              className="btn btn-flat-primary"
              onClick={handleSetPower}
              disabled={pendingOperations.size > 0 || !power || !!error}
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
            Enter a decimal value between 0.0 and 1.0. Press Enter to apply.
          </small>
        </div>
      </div>
    </div>
  );
};

export default LaserPower;