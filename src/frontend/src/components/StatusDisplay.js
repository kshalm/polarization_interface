import React, { useState, useEffect } from 'react';

const StatusDisplay = ({ status, message }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (status && message) {
      setIsVisible(true);
      
      // Auto-hide success messages after 5 seconds
      if (status === 'success') {
        const timer = setTimeout(() => {
          setIsVisible(false);
        }, 5000);
        return () => clearTimeout(timer);
      }
    }
  }, [status, message]);

  const handleDismiss = () => {
    setIsVisible(false);
  };

  if (!isVisible || !status || !message) {
    return null;
  }

  const getAlertClass = () => {
    switch (status) {
      case 'success':
        return 'alert-flat-success';
      case 'error':
        return 'alert-flat-danger';
      case 'warning':
        return 'alert-flat-warning';
      default:
        return 'alert-primary';
    }
  };

  const getIcon = () => {
    switch (status) {
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      case 'warning':
        return '⚠';
      default:
        return 'ℹ';
    }
  };

  return (
    <div className={`alert ${getAlertClass()} alert-dismissible fade show`} role="alert">
      <strong>{getIcon()} {status.charAt(0).toUpperCase() + status.slice(1)}:</strong> {message}
      <button
        type="button"
        className="btn-close"
        onClick={handleDismiss}
        aria-label="Close"
      ></button>
    </div>
  );
};

export default StatusDisplay;