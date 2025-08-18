import React from 'react';
import { useApp } from '../contexts/AppContext';

const LoadingOverlay = () => {
  const { isLoading } = useApp();

  if (!isLoading) return null;

  return (
    <div 
      className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        zIndex: 9999,
        backdropFilter: 'blur(2px)'
      }}
    >
      <div className="text-center text-white">
        <div className="spinner-border spinner-border-lg mb-3" role="status" style={{ color: 'var(--flat-emerald)' }}>
          <span className="visually-hidden">Loading...</span>
        </div>
        <div>
          <h5 className="mb-2">Processing Request...</h5>
          <p className="mb-0 text-muted">
            <small>Please wait while the hardware responds</small>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoadingOverlay;