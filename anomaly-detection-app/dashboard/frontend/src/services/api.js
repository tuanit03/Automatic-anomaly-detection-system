// src/services/api.js
import axios from 'axios';

// Use environment variable with fallback for local development
// In React, browser environment variables must be prefixed with REACT_APP_
const BASE_URL = process.env.REACT_APP_BACKEND_URL;

console.log('API connecting to:', BASE_URL); // Debug log to help troubleshoot

// Remove trailing slash from BASE_URL if present to avoid double slash issues
const normalizedBaseUrl = BASE_URL.endsWith('/') ? BASE_URL.slice(0, -1) : BASE_URL;

const api = axios.create({
  baseURL: normalizedBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  // Add timeout and handle proxy redirects properly
  timeout: 30000,
  maxRedirects: 5,
});

// Add response interceptor to handle errors consistently
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.message, error.response?.status);
    return Promise.reject(error);
  }
);

/**
 * Fetch logs with optional filtering parameters
 * @param {Object} params - Query parameters
 * @returns {Promise} API response
 */
export const fetchLogs = async (params) => {
  const response = await api.get('/api/logs', { params });
  return response.data;
};

/**
 * Fetch classification statistics
 * @param {Object} params - Query parameters (e.g. time range)
 * @returns {Promise} API response
 */
export const fetchClassifications = async (params) => {
  const response = await api.get('/api/statistics/classifications', { params });
  return response.data;
};

/**
 * Fetch anomaly parameters list
 * @param {Object} params - Query parameters (e.g. classification_type, limit)
 * @returns {Promise} API response
 */
export const fetchAnomalyParams = async (params) => {
  const response = await api.get('/api/anomalies/', { params });
  return response.data;
};

/**
 * Synchronize current anomaly data to Slack
 * @param {Object} params - Query parameters (e.g. limit)
 * @returns {Promise} API response
 */
export const syncAnomalyDataToSlack = async (params = {}) => {
  const response = await api.post('/api/anomalies/sync-to-slack', null, { params });
  return response.data;
};

/**
 * Fetch time series data for charting
 * @param {Object} params - Query parameters (e.g. hours, interval_minutes)
 * @returns {Promise} API response
 */
export const fetchTimeSeriesData = async (params) => {
  const response = await api.get('/api/statistics/time-series', { params });
  return response.data;
};

/**
 * Fetch summary statistics
 * @param {Object} params - Query parameters
 * @returns {Promise} API response
 */
export const fetchSummaryStatistics = async (params) => {
  const response = await api.get('/api/statistics/summary', { params });
  return response.data;
};

/**
 * List all available API test reports
 * @returns {Promise} API response with list of report files
 */
export const fetchTestReports = async () => {
  const response = await api.get('/api/test-reports/list');
  return response.data;
};

/**
 * Get the latest API test report
 * @returns {Promise} API response with latest report info
 */
export const fetchLatestTestReport = async () => {
  const response = await api.get('/api/test-reports/latest');
  return response.data;
};

/**
 * Run API tests and generate a new report
 * @returns {Promise} API response with test results and new report info
 */
export const runApiTests = async () => {
  // Create a custom instance with longer timeout for this specific call
  const response = await axios({
    method: 'post',
    url: `${normalizedBaseUrl}/api/test-reports/run`,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 60000, // Increase timeout to 60 seconds for this call
  });
  return response.data;
};

/**
 * Check if there's new anomaly data since a given timestamp
 * @param {Object} params - Query parameters (e.g. since timestamp)
 * @returns {Promise} API response
 */
export const checkNewAnomalyData = async (params) => {
  const response = await api.get('/api/anomalies/check-new', { params });
  return response.data;
};

/**
 * Manually send new data to Slack
 * @returns {Promise} API response
 */
export const sendNewDataToSlack = async () => {
  const response = await api.post('/api/slack/send-new-data');
  return response.data;
};

/**
 * Toggle auto-send functionality for Slack
 * @param {boolean} enabled - Whether to enable auto-send
 * @returns {Promise} API response
 */
export const toggleSlackAutoSend = async (enabled) => {
  const response = await api.post('/api/slack/toggle-auto-send', null, { params: { enabled } });
  return response.data;
};

/**
 * Clear sent records tracking (for testing)
 * @returns {Promise} API response
 */
export const clearSentRecords = async () => {
  const response = await api.post('/api/slack/clear-sent-records');
  return response.data;
};

/**
 * Get Slack status
 * @returns {Promise} API response
 */
export const getSlackStatus = async () => {
  const response = await api.get('/api/slack/status');
  return response.data;
};

// Keep other functions as they are...
export default api;