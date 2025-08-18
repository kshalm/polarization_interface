import React, { useState, useEffect, useRef } from 'react';
import { polarizationAPI } from '../services/api';
import { useApp } from '../contexts/AppContext';

const MoveMotors = () => {
  const [motorInfo, setMotorInfo] = useState({});
  const [positions, setPositions] = useState({});
  const [jogSteps, setJogSteps] = useState({});
  const [inputFocus, setInputFocus] = useState({});
  const [localPositions, setLocalPositions] = useState({});
  const { pendingOperations, startOperation } = useApp();

  // Track input focus to prevent polling conflicts
  const inputRefs = useRef({});

  useEffect(() => {
    loadMotorInfo();
    loadPositions();

    // Set up periodic polling for position updates every 5 seconds
    const interval = setInterval(() => {
      loadPositions();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const loadMotorInfo = async () => {
    try {
      const response = await polarizationAPI.getMotorInfo();
      console.log('Full motor info response:', response);
      console.log('Response data:', response.data);
      
      if (response.data.success) {
        const info = response.data.data || {};
        console.log('Extracted motor info:', info);
        setMotorInfo(info);
        
        // Initialize jog steps with default 5.0 for all waveplates
        const initialJogSteps = {};
        Object.keys(info).forEach(party => {
          if (info[party].names) {
            info[party].names.forEach(waveplate => {
              const key = `${party}_${waveplate}`;
              initialJogSteps[key] = 5.0;
            });
          }
        });
        setJogSteps(initialJogSteps);
      } else {
        console.error('Motor info request failed:', response.data);
      }
    } catch (error) {
      console.error('Failed to load motor info:', error);
      console.error('Error details:', error.response || error);
    }
  };

  const loadPositions = async () => {
    try {
      const response = await polarizationAPI.getPositions();
      if (response.data.success) {
        const newPositions = response.data.data.message || {};
        
        // Only update positions for inputs that don't have focus
        const filteredPositions = {};
        Object.keys(newPositions).forEach(party => {
          filteredPositions[party] = {};
          if (newPositions[party]) {
            Object.keys(newPositions[party]).forEach(waveplate => {
              const key = `${party}_${waveplate}`;
              if (!inputFocus[key]) {
                filteredPositions[party][waveplate] = newPositions[party][waveplate];
              } else {
                // Keep existing position for focused inputs
                filteredPositions[party][waveplate] = positions[party]?.[waveplate] || 0;
              }
            });
          }
        });
        
        setPositions(filteredPositions);
      }
    } catch (error) {
      console.error('Failed to load positions:', error);
    }
  };

  const handlePositionFocus = (party, waveplate) => {
    const key = `${party}_${waveplate}`;
    setInputFocus(prev => ({ ...prev, [key]: true }));
    
    // Store current position as local value for editing
    const currentPos = positions[party]?.[waveplate] || 0;
    setLocalPositions(prev => ({ ...prev, [key]: currentPos }));
  };

  const handlePositionBlur = (party, waveplate) => {
    const key = `${party}_${waveplate}`;
    setInputFocus(prev => ({ ...prev, [key]: false }));
  };

  const handlePositionChange = (party, waveplate, value) => {
    const key = `${party}_${waveplate}`;
    setLocalPositions(prev => ({ ...prev, [key]: value }));
  };

  const handlePositionKeyPress = async (event, party, waveplate) => {
    if (event.key === 'Enter') {
      const key = `${party}_${waveplate}`;
      const newPosition = parseFloat(localPositions[key]);
      
      // Validate position range (-360 to 360)
      if (isNaN(newPosition) || newPosition < -360 || newPosition > 360) {
        alert('Position must be between -360 and 360 degrees');
        return;
      }

      try {
        const response = await polarizationAPI.moveWaveplateGoto(party, waveplate, newPosition);
        if (response.data.success && response.data.operation_id) {
          startOperation(response.data.operation_id);
          
          // Update local position state immediately for feedback
          setPositions(prev => ({
            ...prev,
            [party]: {
              ...prev[party],
              [waveplate]: newPosition
            }
          }));
        }
      } catch (error) {
        console.error('Failed to move waveplate:', error);
        alert('Failed to move waveplate. Please try again.');
      }
    }
  };

  const handleJogStepChange = (party, waveplate, value) => {
    const key = `${party}_${waveplate}`;
    const stepValue = parseFloat(value);
    if (!isNaN(stepValue) && stepValue >= 0 && stepValue <= 360) {
      setJogSteps(prev => ({ ...prev, [key]: stepValue }));
    }
  };

  const handleJog = async (party, waveplate, direction) => {
    const key = `${party}_${waveplate}`;
    const stepSize = jogSteps[key] || 5.0;
    
    try {
      let response;
      if (direction === 'left') {
        response = await polarizationAPI.moveWaveplateBackward(party, waveplate, stepSize);
      } else {
        response = await polarizationAPI.moveWaveplateForward(party, waveplate, stepSize);
      }

      if (response.data.success && response.data.operation_id) {
        startOperation(response.data.operation_id);
      }
    } catch (error) {
      console.error('Failed to jog waveplate:', error);
      alert('Failed to jog waveplate. Please try again.');
    }
  };

  const renderWaveplateRow = (party, waveplate, index) => {
    const key = `${party}_${waveplate}`;
    const currentPosition = positions[party]?.[waveplate] || 0;
    const localPosition = localPositions[key];
    const displayPosition = inputFocus[key] ? localPosition : currentPosition;
    const jogStep = jogSteps[key] || 5.0;
    const isOperationPending = pendingOperations.size > 0;

    return (
      <div key={waveplate} className="waveplate-row">
        <div className="waveplate-name">
          <span className="text-monospace">{waveplate}</span>
        </div>
        
        <div className="waveplate-position">
          <div className="input-group input-group-sm">
            <input
              ref={el => inputRefs.current[key] = el}
              type="number"
              className="form-control text-center"
              value={
                typeof displayPosition === 'number' 
                  ? displayPosition.toFixed(1)
                  : displayPosition?.toString() || '0.0'
              }
              onChange={(e) => handlePositionChange(party, waveplate, e.target.value)}
              onFocus={() => handlePositionFocus(party, waveplate)}
              onBlur={() => handlePositionBlur(party, waveplate)}
              onKeyPress={(e) => handlePositionKeyPress(e, party, waveplate)}
              min={-360}
              max={360}
              step={0.1}
              disabled={isOperationPending}
              title="Press Enter to move to absolute position"
            />
            <span className="input-group-text">°</span>
          </div>
        </div>
        
        <div className="waveplate-jog">
          <div className="jog-controls">
            <button
              className="btn btn-sm btn-outline-secondary jog-btn"
              onClick={() => handleJog(party, waveplate, 'left')}
              disabled={isOperationPending}
              title={`Move backward by ${jogStep}°`}
            >
              ◀
            </button>
            <input
              type="number"
              className="form-control form-control-sm jog-step-input"
              value={jogStep}
              onChange={(e) => handleJogStepChange(party, waveplate, e.target.value)}
              min={0}
              max={360}
              step={0.1}
              disabled={isOperationPending}
              title="Jog step size in degrees"
            />
            <button
              className="btn btn-sm btn-outline-secondary jog-btn"
              onClick={() => handleJog(party, waveplate, 'right')}
              disabled={isOperationPending}
              title={`Move forward by ${jogStep}°`}
            >
              ▶
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderPartySection = (partyName) => {
    const partyData = motorInfo[partyName];
    if (!partyData || !partyData.names || partyData.names.length === 0) {
      return null;
    }

    return (
      <div key={partyName} className="party-section mb-3">
        <div className="party-header">
          <h6 className="mb-2 text-muted font-weight-bold">{partyName.toUpperCase()}</h6>
        </div>
        
        <div className="party-content">
          <div className="waveplate-header">
            <div className="waveplate-name">
              <small className="text-muted">Waveplate</small>
            </div>
            <div className="waveplate-position">
              <small className="text-muted">Position</small>
            </div>
            <div className="waveplate-jog">
              <small className="text-muted">Jog</small>
            </div>
          </div>
          
          <div className="waveplate-list">
            {partyData.names.map((waveplate, index) => 
              renderWaveplateRow(partyName, waveplate, index)
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="card card-flat control-section">
      <div className="card-header card-header-flat">
        <h5 className="mb-0">Move Motors</h5>
      </div>
      <div className="card-body">
        <div className="move-motors-content">
          {['source', 'alice', 'bob'].map(party => renderPartySection(party))}
        </div>
        
        {pendingOperations.size > 0 && (
          <div className="mt-3">
            <div className="alert alert-info alert-sm">
              <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              Motor operation in progress...
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MoveMotors;