import axios from 'axios';

// Use environment variable for backend URL, fallback to localhost for development
// Example: REACT_APP_BACKEND_URL=http://192.168.1.100:8000
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 125000, // 125 seconds (slightly higher than backend 120s)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const polarizationAPI = {
  // Health check
  healthCheck: () => api.get('/health'),

  // Get available paths
  getPaths: () => api.get('/paths'),

  // Set polarization
  setPolarization: (setting) => 
    api.post('/polarization/set', { setting }),

  // Calibrate fibers
  calibrate: (party) => 
    api.post('/calibrate', { party }),

  // Set laser power
  setPower: (power) => 
    api.post('/power/set', { power }),

  // Home waveplates
  home: (party) => 
    api.post('/home', { party }),

  // Set bell angles
  setBellAngles: (angles = null) => 
    api.post('/bell-angles/set', angles ? { angles } : {}),

  // Get server info
  getInfo: () => api.get('/info'),

  // Get available commands
  getCommands: () => api.get('/commands'),

  // Get current polarization path
  getCurrentPath: () => api.get('/current-path'),

  // Motor control endpoints
  getMotorInfo: () => api.get('/motor-info'),
  getPositions: () => api.get('/positions'),
  moveWaveplateForward: (party, waveplate, position) => 
    api.post('/waveplate/forward', { party, waveplate, position }),
  moveWaveplateBackward: (party, waveplate, position) => 
    api.post('/waveplate/backward', { party, waveplate, position }),
  moveWaveplateGoto: (party, waveplate, position) => 
    api.post('/waveplate/goto', { party, waveplate, position }),

  // Redis endpoints
  getRedisHealth: () => api.get('/redis/health'),
  getRedisCounts: () => api.get('/redis/counts'),
};

export const commandAPI = {
  // Get command history
  getHistory: () => api.get('/commands/history'),
  
  // Add command to history
  addCommand: (command, response, isError = false) => 
    api.post('/commands/add', { command, response, isError })
};

export const operationAPI = {
  // Get operation status
  getOperationStatus: (operationId) => api.get(`/operations/${operationId}`),
  
  // Get all operations
  getAllOperations: () => api.get('/operations')
};

export default api;