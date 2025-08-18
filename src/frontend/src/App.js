import React from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';

import { AppProvider } from './contexts/AppContext';
import ConnectionStatus from './components/ConnectionStatus';
import PolarizationControl from './components/PolarizationControl';
import CalibrateFibers from './components/CalibrateFibers';
import LaserPower from './components/LaserPower';
import HomeWaveplates from './components/HomeWaveplates';
import MoveMotors from './components/MoveMotors';
import CommandConsole from './components/CommandConsole';
import CountsTable from './components/CountsTable';

function App() {

  return (
    <AppProvider>
      <div className="App">
        <div className="container-fluid py-4">
          <div className="row justify-content-center">
            <div className="col-12" style={{ maxWidth: '720px' }}>
              <header className="mb-4">
                <h1 className="display-5 text-center mb-2" style={{ color: 'var(--flat-wet-asphalt)' }}>
                  Polarization Control Interface
                </h1>
                <p className="text-center text-muted">
                  Control optical waveplates and manage polarization states
                </p>
              </header>

              {/* Redis Counts Table at the top */}
              <div className="mb-4">
                <CountsTable />
              </div>
              
              {/* Control Sections */}
              <div className="mb-3">
                <PolarizationControl />
              </div>
              
              <div className="mb-3">
                <CalibrateFibers />
              </div>
              
              <div className="mb-3">
                <LaserPower />
              </div>
              
              <div className="mb-4">
                <HomeWaveplates />
              </div>
              
              {/* Move Motors Component */}
              <div className="mb-4">
                <MoveMotors />
              </div>
              
              {/* Command Console at the bottom */}
              <div className="mb-4">
                <CommandConsole />
              </div>
              
              {/* Connection Status at the very bottom */}
              <ConnectionStatus />

              <footer className="mt-3 pt-3 border-top">
                <div className="text-center text-muted">
                  <small>
                    Polarization Interface v1.0.0 | 
                    ZMQ: {status.zmq_status?.connection || 'Connecting...'} | 
                    Redis: {status.redis_status?.connection || 'Connecting...'}
                  </small>
                </div>
              </footer>
            </div>
          </div>
        </div>
      </div>
    </AppProvider>
  );
}

export default App;