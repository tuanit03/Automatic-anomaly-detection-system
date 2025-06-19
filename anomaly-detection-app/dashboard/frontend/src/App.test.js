import { render, screen } from '@testing-library/react';
import App from './App';

// Mock services that use browser APIs or network calls
jest.mock('./services/eventSource', () => ({
  connectToSSE: jest.fn(() => ({ close: jest.fn() })),
  __esModule: true,
  default: { connectToSSE: jest.fn(() => ({ close: jest.fn() })) }
}));

jest.mock('./services/api', () => ({
  fetchAnomalyData: jest.fn(() => Promise.resolve([])),
  fetchTimeSeriesData: jest.fn(() => Promise.resolve([])),
  fetchLogs: jest.fn(() => Promise.resolve([])),
  fetchTestReports: jest.fn(() => Promise.resolve([])),
  fetchTestReportDetails: jest.fn(() => Promise.resolve({})),
  __esModule: true
}));

test('renders dashboard title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Anomaly Detection Dashboard/i);
  expect(titleElement).toBeInTheDocument();
});