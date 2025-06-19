// src/components/Dashboard.js
import React, { useEffect, useRef, useState } from 'react';
import LogViewer from './LogViewer';
import StatisticsCounter from './StatisticsCounter';
import AnomalyList from './AnomalyList';
import TimeSeriesChart from './TimeSeriesChart';
import TestReportViewer from './TestReportViewer';
import { Typography, Container, Paper, Button } from '@mui/material';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const headerRef = useRef(null);
  const [activeView, setActiveView] = useState('dashboard');
  
  useEffect(() => {
    // Update CSS variable with actual header height when it renders
    if (headerRef.current) {
      const headerHeight = headerRef.current.offsetHeight;
      document.documentElement.style.setProperty('--header-height', `${headerHeight}px`);
    }
    
    // Also update on resize
    const handleResize = () => {
      if (headerRef.current) {
        const headerHeight = headerRef.current.offsetHeight;
        document.documentElement.style.setProperty('--header-height', `${headerHeight}px`);
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [activeView]); // Re-run when view changes as header height might change
  
  return (
    <div className="dashboard">
      <div ref={headerRef} className="dashboard-header">
        <Typography variant="h5" component="h1" className="dashboard-title">
          Anomaly Detection Dashboard
        </Typography>
        <div className="view-selector">
          <Button 
            variant={activeView === 'dashboard' ? 'contained' : 'text'} 
            color="inherit"
            className={`view-button ${activeView === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveView('dashboard')}
          >
            Dashboard
          </Button>
          <Button 
            variant={activeView === 'reports' ? 'contained' : 'text'}
            color="inherit"
            className={`view-button ${activeView === 'reports' ? 'active' : ''}`}
            onClick={() => setActiveView('reports')}
          >
            API Test Reports
          </Button>
        </div>
      </div>
      
      <Container maxWidth={false} className="dashboard-container">
        {activeView === 'dashboard' && (
          <div className="dashboard-grid">
            <Paper elevation={3} className="grid-item quadrant-1">
              <LogViewer />
            </Paper>
            
            <Paper elevation={3} className="grid-item quadrant-2">
              <StatisticsCounter />
            </Paper>
            
            <Paper elevation={3} className="grid-item quadrant-3">
              <AnomalyList />
            </Paper>
            
            <Paper elevation={3} className="grid-item quadrant-4">
              <TimeSeriesChart />
            </Paper>
          </div>
        )}
        
        {activeView === 'reports' && (
          <div className="reports-view">
            <TestReportViewer />
          </div>
        )}
      </Container>
    </div>
  );
};

export default Dashboard;