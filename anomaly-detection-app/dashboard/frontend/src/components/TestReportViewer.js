import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Button, 
  CircularProgress, 
  Alert, 
  Box, 
  Card, 
  CardContent,
  Link,
  Snackbar,
  Tooltip
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { runApiTests, fetchLatestTestReport, fetchTestReports } from '../services/api';
import '../styles/TestReportViewer.css';

const TestReportViewer = () => {
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [lastRunTime, setLastRunTime] = useState(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeError, setIframeError] = useState(false);
  const [reportUrl, setReportUrl] = useState('');
  const [notification, setNotification] = useState({ open: false, message: '' });

  // Function to load the latest report
  const loadLatestReport = async () => {
    setLoading(true);
    setError(null);
    setIframeLoaded(false);
    setIframeError(false);
    
    try {
      const latestReport = await fetchLatestTestReport();
      setReport(latestReport);
      updateReportUrl(latestReport);
    } catch (err) {
      console.error('Failed to fetch latest report:', err);
      setError('No reports available. Please run the API tests to generate a report.');
    } finally {
      setLoading(false);
    }
  };

  // Update the report URL with cache busting
  const updateReportUrl = (reportData) => {
    if (!reportData) return;
    
    const baseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
    const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    // Add timestamp to prevent caching
    const cacheBuster = `?t=${Date.now()}`;
    setReportUrl(`${normalizedBaseUrl}${reportData.path}${cacheBuster}`);
  };

  // Check for new reports periodically
  const checkForNewReport = async (startTime, maxAttempts = 12, interval = 5000) => {
    let attempts = 0;
    const checkInterval = setInterval(async () => {
      attempts++;
      console.log(`Checking for new reports (attempt ${attempts}/${maxAttempts})...`);
      
      try {
        const reports = await fetchTestReports();
        if (reports && reports.length > 0) {
          // Check if there's a newer report than when we started
          const latestReport = reports[0];
          const reportTime = new Date(latestReport.created_at).getTime();
          
          if (reportTime > startTime) {
            console.log('Found new report:', latestReport.filename);
            clearInterval(checkInterval);
            setReport(latestReport);
            updateReportUrl(latestReport);
            setLastRunTime(new Date().toISOString());
            setRunning(false);
            setNotification({
              open: true,
              message: 'API tests completed successfully!'
            });
            return;
          }
        }
        
        // Stop checking after max attempts
        if (attempts >= maxAttempts) {
          clearInterval(checkInterval);
          setRunning(false);
          setError('Tests may still be running. Please refresh in a minute to check for new reports.');
        }
      } catch (err) {
        console.error('Error checking for new reports:', err);
        // Keep trying until max attempts is reached
        if (attempts >= maxAttempts) {
          clearInterval(checkInterval);
          setRunning(false);
          setError('Failed to check for new test reports. Please refresh manually.');
        }
      }
    }, interval);
    
    // Clean up interval on component unmount
    return () => clearInterval(checkInterval);
  };

  // Function to run tests and get the new report
  const handleRunTests = async () => {
    setRunning(true);
    setError(null);
    setIframeLoaded(false);
    setIframeError(false);
    
    // Record the time when we started the tests
    const startTime = Date.now();
    
    // Show notification that tests are running
    setNotification({
      open: true,
      message: 'API tests are running. This may take a minute or more...'
    });
    
    try {
      // First run the tests
      const result = await runApiTests();
      console.log('Run tests result:', result);
      
      if (result.success) {
        // The tests completed within the timeout period
        if (result.report) {
          setReport(result.report);
          updateReportUrl(result.report);
          setLastRunTime(new Date().toISOString());
          setRunning(false);
          setNotification({
            open: true,
            message: 'API tests completed successfully!'
          });
        } else {
          // No report in the response, try to fetch the latest
          const cleanupInterval = checkForNewReport(startTime);
          return () => cleanupInterval();
        }
      } else {
        setError(`Failed to run tests: ${result.message}`);
        setRunning(false);
      }
    } catch (err) {
      console.error('Error running tests:', err);
      
      // Check if it's a timeout error
      if (err.message && err.message.includes('timeout')) {
        console.log('Test run timeout - checking for new reports...');
        // Start checking for new reports periodically
        const cleanupInterval = checkForNewReport(startTime);
        return () => cleanupInterval();
      } else {
        // For other errors, try to fetch the latest report anyway
        try {
          const latestReports = await fetchTestReports();
          if (latestReports && latestReports.length > 0) {
            const latestReport = latestReports[0];
            const reportTime = new Date(latestReport.created_at).getTime();
            
            // Only update if this report was created after we started the tests
            if (reportTime > startTime) {
              setReport(latestReport);
              updateReportUrl(latestReport);
              setLastRunTime(new Date().toISOString());
              setError('There was an error communicating with the server, but a new report was found.');
            } else {
              setError('An error occurred while running API tests. Please try again.');
            }
          } else {
            setError('An error occurred while running API tests. Please try again.');
          }
        } catch (fetchErr) {
          setError('An error occurred while running API tests. Please try again.');
        }
        setRunning(false);
      }
    }
  };

  // Load the latest report on component mount
  useEffect(() => {
    loadLatestReport();
  }, []);

  // Format date for display - fix for timezone issues
  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    try {
      // Parse the date string and force it to be treated as UTC
      const date = new Date(dateString);
      
      // Format options for consistent display
      const options = { 
        year: 'numeric', 
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: false,
        timeZone: 'UTC'  // Force UTC timezone display
      };
      
      // Format with UTC timezone indicator
      return `${date.toLocaleString('en-US', options)} UTC`;
    } catch (e) {
      console.error('Date formatting error:', e);
      return dateString; // Return original string if parsing fails
    }
  };

  const handleIframeLoad = () => {
    setIframeLoaded(true);
  };

  const handleIframeError = () => {
    setIframeError(true);
    console.error('Failed to load iframe content');
  };

  // Regenerate report URL when report changes
  useEffect(() => {
    if (report) {
      updateReportUrl(report);
    }
  }, [report]);

  const handleOpenReport = () => {
    if (reportUrl) {
      window.open(reportUrl, '_blank');
    }
  };

  const handleNotificationClose = () => {
    setNotification({ ...notification, open: false });
  };

  return (
    <div className="test-report-viewer">
      {/* Removed the title as requested */}
      <Box className="report-header">
        <Box className="report-controls">
          <Button
            variant="contained"
            color="primary"
            startIcon={<PlayArrowIcon />}
            onClick={handleRunTests}
            disabled={running}
            className="action-button"
          >
            {running ? 'Running Tests...' : 'Run API Tests'}
          </Button>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<RefreshIcon />}
            onClick={loadLatestReport}
            disabled={loading || running}
            className="action-button"
            sx={{ minWidth: '120px' }} // Ensure enough width for the text
          >
            Refresh
          </Button>
        </Box>
      </Box>
      
      {(loading || running) && (
        <Box className="loading-container">
          <CircularProgress />
          <Typography color="textSecondary" sx={{ mt: 2 }}>
            {running ? 'Running API tests... This may take a minute or more.' : 'Loading report...'}
          </Typography>
          {running && (
            <Typography variant="caption" color="textSecondary" sx={{ mt: 1 }}>
              You can wait or come back later - the report will be available when tests complete.
            </Typography>
          )}
        </Box>
      )}
      
      {error && !loading && !running && (
        <Alert severity="warning" sx={{ m: 2 }}>
          {error}
        </Alert>
      )}
      
      {report && !loading && !running && (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start',
              flexDirection: { xs: 'column', sm: 'row' },
              gap: 1
            }}>
              <div>
                <Typography variant="body1">
                  <strong>Latest Report:</strong> {report.filename}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  <strong>Generated:</strong> {formatDate(report.created_at)}
                  {lastRunTime && (
                    <>
                      <br />
                      <strong>Last Run:</strong> {formatDate(lastRunTime)}
                    </>
                  )}
                </Typography>
              </div>
              <Button
                variant="text"
                color="primary"
                startIcon={<OpenInNewIcon />}
                onClick={handleOpenReport}
              >
                Open in new window
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}
      
      {report && !loading && !running && (
        <div className="iframe-container">
          {!iframeLoaded && !iframeError && (
            <Box className="loading-container iframe-loading">
              <CircularProgress size={30} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                Loading report content...
              </Typography>
            </Box>
          )}
          
          {iframeError && (
            <Alert severity="error" sx={{ m: 2 }}>
              Failed to load the report in the iframe. Please use the "Open in new window" button above.
            </Alert>
          )}
          
          <iframe 
            src={reportUrl} 
            title="API Test Report" 
            className={`report-iframe ${iframeLoaded ? 'loaded' : ''}`}
            onLoad={handleIframeLoad}
            onError={handleIframeError}
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      )}
      
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleNotificationClose}
        message={notification.message}
      />
    </div>
  );
};

export default TestReportViewer;