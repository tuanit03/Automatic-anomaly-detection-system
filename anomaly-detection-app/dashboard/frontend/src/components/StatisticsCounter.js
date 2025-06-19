// src/components/StatisticsCounter.js
import React, { useState, useEffect } from 'react';
import { connectToSSE } from '../services/eventSource';
import COLORS from '../utils/colors';
import '../styles/StatisticsCounter.css';

const StatisticsCounter = () => {
  const [stats, setStats] = useState({
    normal_count: 0,
    anomaly_count: 0,
    unidentified_count: 0,
    total_events: 0,
    normal_percent: 0,
    anomaly_percent: 0,
    unidentified_percent: 0
  });
  const [connectionError, setConnectionError] = useState(false);
  const [lastPing, setLastPing] = useState(null);
  
  useEffect(() => {
    const handleError = (error) => {
      console.error('StatisticsCounter SSE error:', error);
      setConnectionError(true);
    };
    
    const eventSource = connectToSSE('/api/statistics/stream', handleError);
    
    if (eventSource) {
      // Handle main statistics events
      eventSource.addEventListener('statistics', (event) => {
        try {
          if (!event.data) {
            console.warn('Received empty data in statistics event');
            return;
          }
          
          const newStats = JSON.parse(event.data);
          
          setStats(prevStats => {
            const total = newStats.normal_count + newStats.anomaly_count + newStats.unidentified_count;
            return {
              ...newStats,
              total_events: total,
              normal_percent: total > 0 ? (newStats.normal_count / total * 100).toFixed(1) : 0,
              anomaly_percent: total > 0 ? (newStats.anomaly_count / total * 100).toFixed(1) : 0,
              unidentified_percent: total > 0 ? (newStats.unidentified_count / total * 100).toFixed(1) : 0,
            };
          });
          
          // Connection is working if we're receiving valid data
          setConnectionError(false);
        } catch (error) {
          console.error('Error parsing statistics data:', error, event.data);
        }
      });
      
      // Handle keepalive ping events
      eventSource.addEventListener('ping', (event) => {
        try {
          const pingData = JSON.parse(event.data);
          setLastPing(new Date());
          setConnectionError(false); // Connection is working
          console.log('Statistics received ping:', pingData);
        } catch (error) {
          console.error('Error parsing statistics ping data:', error);
        }
      });
      
      return () => {
        eventSource.close();
      };
    }
  }, []);
  
  return (
    <div className="statistics-counter">
      {connectionError && (
        <div className="connection-error">
          Connection error. Attempting to reconnect...
        </div>
      )}
      
      <div className="circles-container">
        <div className="stat-circle-container">
          <div 
            className="stat-circle-progress" 
            style={{ 
              background: `conic-gradient(${COLORS.NORMAL} 0deg ${stats.normal_percent * 3.6}deg, rgba(240, 240, 240, 0.5) ${stats.normal_percent * 3.6}deg 360deg)` 
            }}
          >
            <div className="stat-circle-inner">
              <div className="circle-value" style={{ color: COLORS.NORMAL }}>{stats.normal_count}</div>
              <div className="circle-label">Normal</div>
              <div className="circle-percent">{stats.normal_percent}%</div>
            </div>
          </div>
        </div>
        
        <div className="stat-circle-container">
          <div 
            className="stat-circle-progress" 
            style={{ 
              background: `conic-gradient(${COLORS.ANOMALY} 0deg ${stats.anomaly_percent * 3.6}deg, rgba(240, 240, 240, 0.5) ${stats.anomaly_percent * 3.6}deg 360deg)` 
            }}
          >
            <div className="stat-circle-inner">
              <div className="circle-value" style={{ color: COLORS.ANOMALY }}>{stats.anomaly_count}</div>
              <div className="circle-label">Anomaly</div>
              <div className="circle-percent">{stats.anomaly_percent}%</div>
            </div>
          </div>
        </div>
        
        <div className="stat-circle-container">
          <div 
            className="stat-circle-progress" 
            style={{ 
              background: `conic-gradient(${COLORS.UNIDENTIFIED} 0deg ${stats.unidentified_percent * 3.6}deg, rgba(240, 240, 240, 0.5) ${stats.unidentified_percent * 3.6}deg 360deg)` 
            }}
          >
            <div className="stat-circle-inner">
              <div className="circle-value" style={{ color: COLORS.UNIDENTIFIED }}>{stats.unidentified_count}</div>
              <div className="circle-label">Unidentified</div>
              <div className="circle-percent">{stats.unidentified_percent}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatisticsCounter;