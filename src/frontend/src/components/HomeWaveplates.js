import React, { useState } from 'react';
import { polarizationAPI } from '../services/api';
import { useApp } from '../contexts/AppContext';

const HomeWaveplates = () => {
  const [selectedParty, setSelectedParty] = useState('alice');
  const { pendingOperations, startOperation } = useApp();

  const partyOptions = [
    { value: 'alice', label: 'Alice' },
    { value: 'bob', label: 'Bob' },
    { value: 'source', label: 'Source' }
  ];

  const handleHome = async () => {
    if (!selectedParty) {
      return;
    }

    try {
      const response = await polarizationAPI.home(selectedParty);

      if (response.data.success && response.data.operation_id) {
        startOperation(response.data.operation_id);
      }
    } catch (error) {
      console.error('Failed to start home operation:', error);
    }
  };

  return (
    <div className="card card-flat control-section">
      <div className="card-header card-header-flat">
        <h5 className="mb-0">Home Waveplates</h5>
      </div>
      <div className="card-body">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="home-select" className="form-label">
              Select Waveplates to Home:
            </label>
            <select
              id="home-select"
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
              onClick={handleHome}
              disabled={pendingOperations.size > 0 || !selectedParty}
            >
              {pendingOperations.size > 0 ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Homing...
                </>
              ) : (
                'Home'
              )}
            </button>
          </div>
        </div>
        <div className="mt-2">
          <small className="text-muted">
            Warning: Homing will move waveplates to their reference positions. This may take several minutes.
          </small>
        </div>
      </div>
    </div>
  );
};

export default HomeWaveplates;