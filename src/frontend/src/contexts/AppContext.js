import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { commandAPI, operationAPI } from '../services/api';

const AppContext = createContext();

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [commandHistory, setCommandHistory] = useState([]);
  const [pendingOperations, setPendingOperations] = useState(new Set());

  // Load command history from backend on startup and periodically refresh
  useEffect(() => {
    const loadCommandHistory = async () => {
      try {
        const response = await commandAPI.getHistory();
        if (response.data.success) {
          setCommandHistory(response.data.data || []);
        }
      } catch (error) {
        console.error('Failed to load command history:', error);
        setCommandHistory([]);
      }
    };

    loadCommandHistory();

    // Set up periodic polling for command history updates
    const interval = setInterval(loadCommandHistory, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const addCommandToHistory = useCallback(async (command, response, isError = false) => {
    try {
      // Add to backend
      const backendResponse = await commandAPI.addCommand(command, response, isError);
      
      if (backendResponse.data.success) {
        // Update local state with the new entry from backend
        const newEntry = backendResponse.data.data;
        setCommandHistory(prev => [newEntry, ...prev]);
      }
    } catch (error) {
      console.error('Failed to add command to history:', error);
      // Fallback: add to frontend only if backend fails
      const newEntry = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        command,
        response,
        isError
      };
      setCommandHistory(prev => [newEntry, ...prev].slice(0, 200));
    }
  }, []);

  const setLoadingState = useCallback((loading) => {
    setIsLoading(loading);
  }, []);

  const refreshCommandHistory = useCallback(async () => {
    try {
      const response = await commandAPI.getHistory();
      if (response.data.success) {
        setCommandHistory(response.data.data || []);
      }
    } catch (error) {
      console.error('Failed to refresh command history:', error);
    }
  }, []);

  const startOperation = useCallback((operationId) => {
    setPendingOperations(prev => new Set(prev).add(operationId));
    
    // Poll for operation completion
    const checkOperation = async () => {
      try {
        const response = await operationAPI.getOperationStatus(operationId);
        const operation = response.data.data;
        
        if (operation.status === 'completed' || operation.status === 'error') {
          setPendingOperations(prev => {
            const newSet = new Set(prev);
            newSet.delete(operationId);
            return newSet;
          });
          
          // Refresh command history when operation completes
          await refreshCommandHistory();
          return; // Stop polling
        }
        
        // Continue polling if still pending/running
        setTimeout(checkOperation, 1000); // Poll every second
      } catch (error) {
        console.error('Failed to check operation status:', error);
        // Remove from pending operations on error
        setPendingOperations(prev => {
          const newSet = new Set(prev);
          newSet.delete(operationId);
          return newSet;
        });
      }
    };
    
    // Start polling after a brief delay
    setTimeout(checkOperation, 500);
  }, [refreshCommandHistory]);

  const value = {
    isLoading,
    setLoadingState,
    commandHistory,
    addCommandToHistory,
    refreshCommandHistory,
    pendingOperations,
    startOperation
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};