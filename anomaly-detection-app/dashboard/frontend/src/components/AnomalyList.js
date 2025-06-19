// src/components/AnomalyList.js
import React, { useState, useEffect } from 'react';
import { fetchAnomalyParams, sendNewDataToSlack, getSlackStatus, toggleSlackAutoSend } from '../services/api';
import { Box, Tabs, Tab, CircularProgress, Button, Alert, Typography, Paper, Stack, Chip } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import SendIcon from '@mui/icons-material/Send';
import SettingsIcon from '@mui/icons-material/Settings';
import COLORS from '../utils/colors';
import '../styles/AnomalyList.css';

const AnomalyList = () => {
  const [anomalyParams, setAnomalyParams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('anomaly'); // 'anomaly' or 'unidentified'
  const [retryCount, setRetryCount] = useState(0);
  const [lastSyncTime, setLastSyncTime] = useState(null);
  const [lastCheckTime, setLastCheckTime] = useState(null);
  const [lastDataUpdateTime, setLastDataUpdateTime] = useState(null);
  const [seenRecordIds, setSeenRecordIds] = useState(new Set()); // Track seen record IDs
  const [slackStatus, setSlackStatus] = useState(null);
  const [slackSending, setSlackSending] = useState(false);
  
  const fetchData = async (forceUpdate = false) => {
    try {
      if (!forceUpdate) {
        setLoading(false); // Don't show loading spinner for periodic checks
      } else {
        setLoading(true);
      }
      
      const params = { 
        classification_type: activeTab,
        limit: 20
      };
      
      // Always fetch current data
      const data = await fetchAnomalyParams(params);
      
      // Check if we have truly new records (not seen before)
      const currentRecordIds = new Set(data.map(item => item.id));
      const newRecords = data.filter(item => !seenRecordIds.has(item.id));
      
      // Only update state if we have new records or it's a force update
      if (newRecords.length > 0 || forceUpdate) {
        setAnomalyParams(data);
        setError(null);
        setLastDataUpdateTime(new Date());
        
        // Update seen records
        setSeenRecordIds(prev => new Set([...prev, ...currentRecordIds]));
        
        if (newRecords.length > 0) {
          console.log(`Found ${newRecords.length} new ${activeTab} records`);
        }
        
        // Reset retry count on success
        setRetryCount(0);
      } else {
        console.log(`No new ${activeTab} records found`);
      }
    } catch (err) {
      console.error('Error fetching anomaly parameters:', err);
      setError('Failed to load parameters. Please try again.');
      setRetryCount(prevCount => prevCount + 1);
    } finally {
      if (forceUpdate) {
        setLoading(false);
      }
    }
  };
  
  const syncToSlack = async () => {
    try {
      setSlackSending(true);
      const result = await sendNewDataToSlack();
      console.log('Manual Slack sync result:', result);
      
      // Refresh Slack status after sending
      await fetchSlackStatus();
      
    } catch (err) {
      console.error('Error in manual Slack sync:', err);
    } finally {
      setSlackSending(false);
    }
  };
  
  const fetchSlackStatus = async () => {
    try {
      const status = await getSlackStatus();
      setSlackStatus(status);
    } catch (err) {
      console.error('Error fetching Slack status:', err);
    }
  };
  
  const toggleAutoSend = async () => {
    try {
      const newState = !slackStatus?.auto_send_enabled;
      await toggleSlackAutoSend(newState);
      await fetchSlackStatus(); // Refresh status
    } catch (err) {
      console.error('Error toggling auto-send:', err);
    }
  };
  
  // Initial data fetch
  useEffect(() => {
    setLastCheckTime(new Date()); // Set initial check time
    setSeenRecordIds(new Set()); // Clear seen records when tab changes
    fetchData(true); // Force initial fetch
    fetchSlackStatus(); // Get initial Slack status
  }, [activeTab]);
  
  // Set up auto-refresh every 10 seconds - always check but only update if truly new
  useEffect(() => {
    const interval = setInterval(() => {
      setLastCheckTime(new Date()); // Update check time
      fetchData(false); // Check for new data, only update UI if needed
    }, 10000);
    
    return () => clearInterval(interval);
  }, [activeTab, seenRecordIds]);
  
  // Remove Slack auto-sync - make it manual only
  // No more automatic Slack synchronization
  
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  
  const handleRefresh = () => {
    setLastCheckTime(new Date());
    fetchData(true); // Force refresh when user clicks refresh
  };
  
  return (
    <div className="anomaly-list">
      <Tabs
        value={activeTab}
        onChange={handleTabChange}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
        sx={{
          '& .MuiTab-root': {
            fontWeight: 'bold',
          }
        }}
      >
        <Tab 
          value="anomaly" 
          label="Anomalies" 
          icon={<ReportProblemIcon />} 
          iconPosition="start"
          sx={{ color: COLORS.ANOMALY }}
        />
        <Tab 
          value="unidentified" 
          label="Unidentified" 
          icon={<HelpOutlineIcon />} 
          iconPosition="start"
          sx={{ color: COLORS.UNIDENTIFIED }}
        />
      </Tabs>
      
      {/* Slack Control Panel */}
      {slackStatus && (
        <Paper elevation={1} sx={{ p: 2, mb: 2, bgcolor: '#f8f9fa' }}>
          <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between" flexWrap="wrap">
            <Box>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SendIcon /> Slack Integration
              </Typography>
              <Stack direction="row" spacing={1} mt={1}>
                <Chip 
                  label={slackStatus.task_running ? "Connected" : "Disconnected"} 
                  color={slackStatus.task_running ? "success" : "error"} 
                  size="small" 
                />
                <Chip 
                  label={`Auto-send: ${slackStatus.auto_send_enabled ? "ON" : "OFF"}`} 
                  color={slackStatus.auto_send_enabled ? "primary" : "default"} 
                  size="small" 
                />
                <Chip 
                  label={`Sent: ${slackStatus.sent_records_count}`} 
                  variant="outlined" 
                  size="small" 
                />
              </Stack>
            </Box>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                onClick={syncToSlack}
                disabled={slackSending || !slackStatus.task_running}
                startIcon={slackSending ? <CircularProgress size={16} /> : <SendIcon />}
                size="small"
              >
                {slackSending ? 'Sending...' : 'Send New to Slack'}
              </Button>
              <Button
                variant="outlined"
                onClick={toggleAutoSend}
                startIcon={<SettingsIcon />}
                size="small"
              >
                {slackStatus.auto_send_enabled ? 'Disable Auto' : 'Enable Auto'}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      )}
      
      {error && (
        <Alert 
          severity="error" 
          action={
            <Button 
              color="inherit" 
              size="small" 
              onClick={handleRefresh}
              startIcon={<RefreshIcon />}
            >
              Retry
            </Button>
          }
          sx={{ my: 2 }}
        >
          {error}
        </Alert>
      )}
      
      {loading ? (
        <Box className="loading-box">
          <CircularProgress />
        </Box>
      ) : anomalyParams.length === 0 ? (
        <Box className="empty-list">
          <Typography variant="body1">No {activeTab} parameters found</Typography>
        </Box>
      ) : (
        <div className="params-container">
          {anomalyParams.map((param) => (
            <div 
              key={param.id} 
              className="param-item"
              style={{ 
                borderLeft: `4px solid ${activeTab === 'anomaly' ? COLORS.ANOMALY : COLORS.UNIDENTIFIED}`,
                backgroundColor: activeTab === 'anomaly' ? `${COLORS.ANOMALY}10` : `${COLORS.UNIDENTIFIED}10`
              }}
            >
              <div className="param-timestamp">
                {new Date(param.timestamp).toLocaleString()}
              </div>
              <div className="param-value">{param.param_value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AnomalyList;
