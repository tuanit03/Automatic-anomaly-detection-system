// src/services/eventSource.js

// Use environment variable with fallback for local development
// In React, browser environment variables must be prefixed with REACT_APP_
const BASE_URL = process.env.REACT_APP_BACKEND_URL;

console.log('SSE connecting to:', BASE_URL); // Debug log to help troubleshoot

/**
 * Creates and connects to a Server-Sent Events (SSE) endpoint
 * @param {string} endpoint - The API endpoint to connect to (starts with '/')
 * @param {function} [onError] - Optional custom error handler
 * @returns {EventSource} The EventSource instance
 */
export const connectToSSE = (endpoint, onError) => {
  const url = `${BASE_URL}${endpoint}`;
  
  try {
    const eventSource = new EventSource(url);
    
    eventSource.onopen = () => {
      console.log(`Connected to SSE endpoint: ${url}`);
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      
      if (onError && typeof onError === 'function') {
        onError(error);
      } else {
        // Default reconnection logic
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log('SSE connection closed. Attempting to reconnect in 5s...');
          // Close the current connection first to avoid memory leaks
          eventSource.close();
          
          setTimeout(() => {
            console.log('Reconnecting to SSE...');
            connectToSSE(endpoint, onError);
          }, 5000);
        }
      }
    };
    
    return eventSource;
  } catch (err) {
    console.error(`Failed to create EventSource for ${url}:`, err);
    return null;
  }
};

/**
 * Creates an SSE connection and sets up event listeners for specific event types
 * @param {string} endpoint - The API endpoint to connect to (starts with '/')
 * @param {Object} eventHandlers - Object mapping event names to handler functions
 * @param {function} [onError] - Optional custom error handler
 * @returns {EventSource} The EventSource instance
 */
export const connectToSSEWithEvents = (endpoint, eventHandlers, onError) => {
  const eventSource = connectToSSE(endpoint, onError);
  
  if (!eventSource) return null;
  
  // Set up event listeners
  if (eventHandlers && typeof eventHandlers === 'object') {
    Object.entries(eventHandlers).forEach(([eventName, handler]) => {
      if (typeof handler === 'function') {
        eventSource.addEventListener(eventName, (event) => {
          try {
            if (event.data) {
              const data = JSON.parse(event.data);
              handler(data, event);
            } else {
              console.warn(`Received empty data for ${eventName} event`);
            }
          } catch (error) {
            console.error(`Error parsing JSON for ${eventName} event:`, error, event.data);
            // Fall back to raw data only if it's not empty or malformed JSON
            if (event.data && typeof event.data === 'string' && event.data.trim() !== '') {
              handler(event.data, event);
            }
          }
        });
      }
    });
  }
  
  return eventSource;
};

export default {
  connectToSSE,
  connectToSSEWithEvents
};