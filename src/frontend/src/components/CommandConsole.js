import React, { useEffect, useRef } from 'react';
import { useApp } from '../contexts/AppContext';

const CommandConsole = () => {
  const { commandHistory } = useApp();
  const consoleRef = useRef(null);
  const contentRef = useRef(null);

  useEffect(() => {
    // Use direct DOM manipulation to prevent flashing
    updateConsoleContent();
  }, [commandHistory]);

  const updateConsoleContent = () => {
    if (!contentRef.current) return;
    
    // Clear existing content
    contentRef.current.innerHTML = '';
    
    if (commandHistory.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.className = 'p-3 text-center text-muted';
      emptyDiv.innerHTML = '<i class="fas fa-info-circle me-2"></i>No commands executed yet';
      contentRef.current.appendChild(emptyDiv);
      return;
    }
    
    // Create content container
    const containerDiv = document.createElement('div');
    containerDiv.className = 'p-2';
    
    // Add each command entry
    commandHistory.forEach(entry => {
      const entryDiv = document.createElement('div');
      entryDiv.className = 'mb-3 pb-2';
      entryDiv.style.borderBottom = '1px solid var(--flat-concrete)';
      
      entryDiv.innerHTML = `
        <div class="mb-1">
          <div style="color: var(--flat-concrete); font-size: 0.75em; font-weight: bold;">
            [${formatTimestamp(entry.timestamp)}]
          </div>
        </div>
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="badge" style="background-color: ${entry.isError ? 'var(--flat-alizarin)' : 'var(--flat-emerald)'}; color: white">
            ${entry.isError ? 'ERROR' : 'SUCCESS'}
          </span>
        </div>
        <div class="mb-1">
          <span class="text-warning">$ </span>
          <span style="color: var(--flat-clouds)">${entry.command}</span>
        </div>
        <div class="ps-3" style="color: ${entry.isError ? 'var(--flat-alizarin)' : 'var(--flat-silver)'}; white-space: pre-wrap; word-break: break-word;">
          ${formatResponse(entry.response)}
        </div>
      `;
      
      containerDiv.appendChild(entryDiv);
    });
    
    contentRef.current.appendChild(containerDiv);
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  };

  const formatResponse = (response) => {
    if (typeof response === 'object') {
      return JSON.stringify(response, null, 2);
    }
    return String(response);
  };

  return (
    <div className="card" style={{ backgroundColor: 'var(--flat-midnight-blue)', color: 'white' }}>
      <div className="card-header" style={{ backgroundColor: 'var(--flat-wet-asphalt)', borderBottom: '1px solid var(--flat-concrete)' }}>
        <h5 className="mb-0" style={{ color: 'white' }}>
          <i className="fas fa-terminal me-2"></i>
          Command Console
        </h5>
        <small className="text-light opacity-75">
          Last {commandHistory.length} commands (max 200)
        </small>
      </div>
      <div 
        className="card-body p-0" 
        style={{ 
          height: '400px', 
          overflow: 'auto',
          fontFamily: 'monospace',
          fontSize: '0.85em'
        }}
        ref={consoleRef}
      >
        <div ref={contentRef}></div>
      </div>
    </div>
  );
};

export default CommandConsole;