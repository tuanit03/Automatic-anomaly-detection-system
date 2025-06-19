// src/components/TimeSeriesChart.js
import React, { useState, useEffect, useMemo } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart
} from 'recharts';
import { fetchTimeSeriesData } from '../services/api';
import { format } from 'date-fns';
import { 
  Box, 
  ToggleButtonGroup, 
  ToggleButton, 
  CircularProgress, 
  Alert, 
  Paper,
  Stack,
  styled
} from '@mui/material';
import COLORS from '../utils/colors';
import '../styles/TimeSeriesChart.css';

// Styled components for modern UI
const StyledToggleButtonGroup = styled(ToggleButtonGroup)(({ theme }) => ({
  '& .MuiToggleButtonGroup-grouped': {
    margin: theme.spacing(0.25),
    border: 0,
    borderRadius: '6px',
    '&.Mui-disabled': {
      border: 0,
    },
  },
}));

const StyledToggleButton = styled(ToggleButton)(({ theme }) => ({
  textTransform: 'none',
  fontWeight: 500,
  padding: '2px 8px',
  fontSize: '0.8rem',
  borderRadius: '6px',
  '&.Mui-selected': {
    backgroundColor: theme.palette.primary.main + '20',
    color: theme.palette.primary.main,
    fontWeight: 600,
  },
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
}));

const LabelToggleButton = styled(ToggleButton)(({ color, theme }) => ({
  textTransform: 'none',
  fontWeight: 500,
  padding: '2px 8px',
  fontSize: '0.8rem',
  borderRadius: '6px',
  '&.Mui-selected': {
    backgroundColor: `${color}20`,
    color: color,
    fontWeight: 600,
    boxShadow: `inset 0 0 0 1px ${color}60`,
  },
  '&:hover': {
    backgroundColor: `${color}10`,
  },
}));

const ChartControlsWrapper = styled(Paper)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'space-between',
  padding: theme.spacing(1),
  alignItems: 'center',
  borderRadius: '8px',
  boxShadow: '0 2px 6px rgba(0, 0, 0, 0.06)',
  marginBottom: theme.spacing(1),
  minHeight: 'auto',
}));

const TimeSeriesChart = () => {
  const TIME_OPTIONS = [
    { label: '5M', hours: 1, interval: 1 }, // Use minimum 1 hour for backend compatibility but set interval to 1 min
    { label: '1H', hours: 1, interval: 5 },
    { label: '6H', hours: 6, interval: 15 },
    { label: '12H', hours: 12, interval: 30 },
  ];
  
  const LABEL_OPTIONS = [
    { key: 'normal_count', label: 'Normal', color: COLORS.NORMAL },
    { key: 'anomaly_count', label: 'Anomaly', color: COLORS.ANOMALY },
    { key: 'unidentified_count', label: 'Unidentified', color: COLORS.UNIDENTIFIED },
  ];
  
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeOption, setTimeOption] = useState(TIME_OPTIONS[1].label); // Default to 1H
  const [lastUpdate, setLastUpdate] = useState(null);
  const [selectedLabels, setSelectedLabels] = useState(['normal_count', 'anomaly_count', 'unidentified_count']);
  
  // Function to fetch time series data
  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Find the selected time option
      const selectedOption = TIME_OPTIONS.find(option => option.label === timeOption);
      
      // Get the hours and interval
      const hours = selectedOption ? selectedOption.hours : 1;
      const interval = selectedOption ? selectedOption.interval : 5;
      
      // Call the API
      const data = await fetchTimeSeriesData({ hours, interval });
      
      // Process the data for the chart
      const processedData = data.map(item => ({
        ...item,
        timestamp: new Date(item.timestamp),
        formattedTime: format(new Date(item.timestamp), 'HH:mm')
      }));
      
      setTimeSeriesData(processedData);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      console.error('Error fetching time series data:', err);
      setError('Failed to load time series data');
    } finally {
      setLoading(false);
    }
  };
  
  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, [timeOption]);
  
  // Set up an auto-refresh based on the selected time option
  useEffect(() => {
    const selectedOption = TIME_OPTIONS.find(option => option.label === timeOption);
    const refreshInterval = selectedOption.label === '5M' ? 60000 : 3600000; // 1 minute for 5M, 1 hour for others
    
    const interval = setInterval(() => {
      fetchData();
    }, refreshInterval);
    
    return () => clearInterval(interval);
  }, [timeOption]);
  
  // Handle time option change
  const handleTimeChange = (event, newTimeOption) => {
    if (newTimeOption !== null) {
      setTimeOption(newTimeOption);
    }
  };
  
  // Handle label filter change
  const handleLabelChange = (event, newLabels) => {
    // Prevent deselecting all labels
    if (newLabels && newLabels.length > 0) {
      setSelectedLabels(newLabels);
    }
  };
  
  // Calculate Y-axis domain based on selected labels
  const calculateYDomain = useMemo(() => {
    if (timeSeriesData.length === 0) return [0, 10];
    
    let minValue = 0;
    let maxValue = 0;
    
    timeSeriesData.forEach(item => {
      selectedLabels.forEach(label => {
        if (item[label] > maxValue) maxValue = item[label];
      });
    });
    
    // Add some padding to the max value
    maxValue = Math.ceil(maxValue * 1.1);
    if (maxValue === 0) maxValue = 10; // Default if no data
    
    return [minValue, maxValue];
  }, [timeSeriesData, selectedLabels]);
  
  return (
    <div className="time-series-chart">
      <ChartControlsWrapper>
        <Box>
          <StyledToggleButtonGroup
            value={timeOption}
            exclusive
            onChange={handleTimeChange}
            aria-label="time range"
            size="small"
          >
            {TIME_OPTIONS.map(option => (
              <StyledToggleButton key={option.label} value={option.label}>
                {option.label}
              </StyledToggleButton>
            ))}
          </StyledToggleButtonGroup>
        </Box>
        
        <Stack direction="row" spacing={0.5}>
          <StyledToggleButtonGroup
            value={selectedLabels}
            onChange={handleLabelChange}
            aria-label="label filter"
            size="small"
          >
            {LABEL_OPTIONS.map(option => (
              <LabelToggleButton 
                key={option.key} 
                value={option.key}
                color={option.color}
              >
                {option.label}
              </LabelToggleButton>
            ))}
          </StyledToggleButtonGroup>
        </Stack>
      </ChartControlsWrapper>
      
      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 1, 
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
            fontSize: '0.85rem',
            py: 0.5
          }}
        >
          {error}
        </Alert>
      )}
      
      {loading ? (
        <Box className="loading-box">
          <CircularProgress size={30} />
        </Box>
      ) : (
        <Paper className="chart-container" elevation={1} sx={{ borderRadius: '8px' }}>
          <div className="scrollable-chart-container">
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart 
                data={timeSeriesData} 
                margin={{ top: 10, right: 20, left: 5, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.5} />
                <XAxis 
                  dataKey="formattedTime" 
                  tick={{ fontSize: 11 }}
                  tickMargin={8}
                />
                <YAxis 
                  tick={{ fontSize: 11 }}
                  tickMargin={8}
                  domain={calculateYDomain}
                  label={selectedLabels.length === 1 ? { 
                    value: 'Count', 
                    angle: -90, 
                    position: 'insideLeft',
                    style: { textAnchor: 'middle', fontSize: 11 }
                  } : null}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: 'none',
                    borderRadius: '6px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                    padding: '8px 10px',
                    fontSize: '0.8rem'
                  }}
                  formatter={(value, name) => {
                    const label = LABEL_OPTIONS.find(opt => opt.key === name)?.label || name;
                    return [value, label];
                  }}
                  labelFormatter={(label) => `Time: ${label}`}
                />
                <Legend 
                  verticalAlign="top" 
                  height={25} 
                  formatter={(value) => {
                    const label = LABEL_OPTIONS.find(opt => opt.key === value)?.label || value;
                    return label;
                  }}
                  wrapperStyle={{
                    fontSize: '0.85rem',
                    paddingTop: '5px'
                  }}
                />
                
                {selectedLabels.includes('normal_count') && (
                  <Area 
                    type="monotone" 
                    dataKey="normal_count" 
                    name="normal_count"
                    fill={COLORS.NORMAL} 
                    stroke={COLORS.NORMAL}
                    fillOpacity={selectedLabels.length === 1 ? 0.3 : 0.2}
                    strokeWidth={selectedLabels.length === 1 ? 2.5 : 1.5}
                  />
                )}
                
                {selectedLabels.includes('anomaly_count') && (
                  <Line 
                    type="monotone" 
                    dataKey="anomaly_count" 
                    name="anomaly_count"
                    stroke={COLORS.ANOMALY} 
                    strokeWidth={selectedLabels.length === 1 ? 2.5 : 1.5}
                    dot={{ r: selectedLabels.length === 1 ? 2.5 : 1.5, fill: COLORS.ANOMALY }}
                    activeDot={{ r: selectedLabels.length === 1 ? 6 : 5 }}
                  />
                )}
                
                {selectedLabels.includes('unidentified_count') && (
                  <Line 
                    type="monotone" 
                    dataKey="unidentified_count" 
                    name="unidentified_count"
                    stroke={COLORS.UNIDENTIFIED} 
                    strokeWidth={selectedLabels.length === 1 ? 2.5 : 1.5}
                    dot={{ r: selectedLabels.length === 1 ? 2.5 : 1.5, fill: COLORS.UNIDENTIFIED }}
                    activeDot={{ r: selectedLabels.length === 1 ? 6 : 5 }}
                  />
                )}
                
                {selectedLabels.length === 1 && selectedLabels[0] === 'anomaly_count' && (
                  <ReferenceLine 
                    y={calculateYDomain[1] * 0.7} 
                    stroke={COLORS.ANOMALY} 
                    strokeDasharray="3 3" 
                    label={{ 
                      value: 'Warning Threshold', 
                      fill: COLORS.ANOMALY,
                      position: 'right',
                      fontSize: 11
                    }} 
                  />
                )}
                
                <ReferenceLine y={0} stroke="#000" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Paper>
      )}
    </div>
  );
};

export default TimeSeriesChart;