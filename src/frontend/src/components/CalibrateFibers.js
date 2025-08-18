import React, { useState } from 'react';
import { polarizationAPI } from '../services/api';
import { useApp } from '../contexts/AppContext';

const CalibrateFibers = () => {
  const [selectedParty, setSelectedParty] = useState('alice');
  const { pendingOperations, startOperation } = useApp();

  const partyOptions = [
    { value: 'alice', label: "Alice's Fiber" },
    { value: 'bob', label: "Bob's Fiber" },
    { value: 'source', label: "Source Waveplates" }
  ];

  const handleCalibrate = async () => {
    if (!selectedParty) {
      return;
    }

    try {
      const response = await polarizationAPI.calibrate(selectedParty);

      if (response.data.success && response.data.operation_id) {
        startOperation(response.data.operation_id);
      }
    } catch (error) {
      console.error('Failed to start calibration:', error);
    }
  };

  return (
    <div className="card card-flat control-section">
      <div className="card-header card-header-flat">
        <h5 className="mb-0">Calibrate Fibers</h5>
      </div>
      <div className="card-body">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="calibrate-select" className="form-label">
              Select Fiber to Calibrate:
            </label>
            <select
              id="calibrate-select"
              className="form-select form-select-flat"
              value={selectedParty}
              onChange={(e) => setSelectedParty(e.target.value)}
              disabled={pendingOperations.size > 0}
            >
              {partyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="set-button">
            <button
              className="btn btn-flat-primary"
              onClick={handleCalibrate}
              disabled={pendingOperations.size > 0 || !selectedParty}
            >
              {pendingOperations.size > 0 ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Calibrating...
                </>
              ) : (
                'Calibrate'
              )}
            </button>
          </div>
        </div>
        <div className="mt-2">
          <small className="text-muted">
            Note: Calibration may take several minutes to complete.
          </small>
        </div>
      </div>
    </div>
  );
};

export default CalibrateFibers;