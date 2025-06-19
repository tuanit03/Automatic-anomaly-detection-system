#!/usr/bin/env python3
# filepath: /home/dev/DoAn6/enhanced_api_test.py

import asyncio
import aiohttp
import json
import time
import argparse
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlencode

# Default API base URL
DEFAULT_BASE_URL = "http://localhost:8000/api"

class APITester:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, output_directory: str = "reports"):
        self.base_url = base_url
        self.session = None
        self.running = False
        self.active_sse_connections = []
        self.output_directory = output_directory
        
        # Test results tracking
        self.test_results = {
            "test_start_time": datetime.now().isoformat(),
            "test_end_time": None,
            "total_duration": 0,
            "base_url": base_url,
            "api_groups": {
                "logs": {"success": 0, "failed": 0, "endpoints": [], "stream_events": 0},
                "statistics": {"success": 0, "failed": 0, "endpoints": [], "stream_events": 0},
                "anomalies": {"success": 0, "failed": 0, "endpoints": [], "stream_events": 0},
            },
            "summary": {
                "total_endpoints": 0,
                "successful_endpoints": 0,
                "failed_endpoints": 0,
                "success_rate": 0,
                "average_response_time": 0,
                "total_stream_events": 0,
            }
        }
    
    async def create_session(self):
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_request(self, endpoint: str, params: Optional[Dict] = None, api_group: str = None) -> Tuple[Dict, float, bool]:
        """Make a GET request to a regular API endpoint and track results"""
        if not self.session:
            await self.create_session()
        
        url = urljoin(self.base_url, endpoint)
        start_time = time.time()
        success = False
        
        try:
            print(f"Making GET request to {url}")
            if params:
                print(f"With params: {params}")
                
            async with self.session.get(url, params=params) as response:
                status = response.status
                response_time = time.time() - start_time
                
                if status == 200:
                    result = await response.json()
                    print(f"Response status: {status} (took {response_time:.3f}s)")
                    success = True
                    if api_group:
                        self.test_results["api_groups"][api_group]["success"] += 1
                    return result, response_time, success
                else:
                    text = await response.text()
                    print(f"Error {status}: {text} (took {response_time:.3f}s)")
                    if api_group:
                        self.test_results["api_groups"][api_group]["failed"] += 1
                    return {"error": text}, response_time, success
        except Exception as e:
            response_time = time.time() - start_time
            print(f"Request failed: {str(e)} (took {response_time:.3f}s)")
            if api_group:
                self.test_results["api_groups"][api_group]["failed"] += 1
            return {"error": str(e)}, response_time, success
    
    async def stream_sse(self, endpoint: str, event_callback, duration_seconds: int = 30, api_group: str = None):
        """Connect to an SSE endpoint and process events for the specified duration"""
        if not self.session:
            await self.create_session()
        
        url = urljoin(self.base_url, endpoint)
        print(f"Connecting to SSE stream: {url}")
        print(f"Will listen for {duration_seconds} seconds...")
        
        start_time = time.time()
        success = False
        event_count = 0
        
        try:
            response = await self.session.get(url)
            connection_time = time.time() - start_time
            
            if response.status != 200:
                text = await response.text()
                print(f"Error connecting to SSE stream: {response.status} - {text} (took {connection_time:.3f}s)")
                if api_group:
                    self.test_results["api_groups"][api_group]["failed"] += 1
                return
            
            print(f"Connected to SSE stream (took {connection_time:.3f}s)")
            success = True
            
            # Track this connection so we can close it during shutdown
            self.active_sse_connections.append(response)
            
            # Set up event stream processing
            end_time = start_time + duration_seconds
            buffer = ""
            
            while time.time() < end_time and self.running:
                chunk = await response.content.read(1024)
                if not chunk:
                    print("SSE connection closed by server")
                    break
                
                buffer += chunk.decode('utf-8')
                
                # Process complete events in the buffer
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    lines = event.strip().split("\n")
                    
                    event_type = None
                    event_data = None
                    event_id = None
                    
                    for line in lines:
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            event_data = line[5:].strip()
                        elif line.startswith("id:"):
                            event_id = line[3:].strip()
                    
                    if event_data:
                        try:
                            data = json.loads(event_data)
                            await event_callback(event_type, data, event_id)
                            event_count += 1
                            if api_group:
                                self.test_results["api_groups"][api_group]["stream_events"] += 1
                        except json.JSONDecodeError:
                            print(f"Failed to parse event data as JSON: {event_data}")
                            await event_callback(event_type, event_data, event_id)
                            event_count += 1
                            if api_group:
                                self.test_results["api_groups"][api_group]["stream_events"] += 1
            
            # Remove this connection from active connections
            if response in self.active_sse_connections:
                self.active_sse_connections.remove(response)
            
            # Close the response
            response.close()
            total_time = time.time() - start_time
            print(f"Finished listening to SSE stream after {total_time:.3f} seconds, received {event_count} events")
            
            # Record stream test results
            if api_group:
                if success:
                    self.test_results["api_groups"][api_group]["success"] += 1
                else:
                    self.test_results["api_groups"][api_group]["failed"] += 1
                
                self.test_results["api_groups"][api_group]["endpoints"].append({
                    "endpoint": endpoint,
                    "type": "stream",
                    "success": success,
                    "response_time": connection_time,
                    "total_duration": total_time,
                    "events_received": event_count
                })
            
        except Exception as e:
            total_time = time.time() - start_time
            print(f"SSE connection error: {str(e)} (after {total_time:.3f}s)")
            if response in self.active_sse_connections:
                self.active_sse_connections.remove(response)
            
            if api_group:
                self.test_results["api_groups"][api_group]["failed"] += 1
                self.test_results["api_groups"][api_group]["endpoints"].append({
                    "endpoint": endpoint,
                    "type": "stream",
                    "success": False,
                    "error": str(e),
                    "total_duration": total_time,
                    "events_received": event_count
                })
    
    async def close_all_connections(self):
        """Close all active SSE connections"""
        for conn in self.active_sse_connections[:]:
            try:
                conn.close()
                self.active_sse_connections.remove(conn)
            except Exception as e:
                print(f"Error closing connection: {str(e)}")
    
    async def test_logs_api(self):
        """Test the logs API endpoints"""
        api_group = "logs"
        print("\n===== Testing Logs API =====")
        
        # Test GET /api/logs/
        print("\n--- Testing GET /api/logs/ ---")
        endpoint = "/api/logs/"
        logs, response_time, success = await self.get_request(endpoint, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "success": success,
            "response_time": response_time,
            "result_count": len(logs) if not isinstance(logs, dict) or "error" not in logs else 0
        })
        
        if not isinstance(logs, dict) or "error" not in logs:
            print(f"Found {len(logs)} log entries")
            if logs:
                print("Sample log entry:")
                print(json.dumps(logs[0], indent=2))
        
        # Test logs with query parameters
        print("\n--- Testing GET /api/logs/ with parameters ---")
        endpoint = "/api/logs/"
        params = {
            "skip": 0, 
            "limit": 5,
            "log_level": "INFO"
        }
        filtered_logs, response_time, success = await self.get_request(endpoint, params, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "params": params,
            "success": success,
            "response_time": response_time,
            "result_count": len(filtered_logs) if not isinstance(filtered_logs, dict) or "error" not in filtered_logs else 0
        })
        
        if not isinstance(filtered_logs, dict) or "error" not in filtered_logs:
            print(f"Found {len(filtered_logs)} filtered log entries")
            if filtered_logs:
                print("Sample filtered log entry:")
                print(json.dumps(filtered_logs[0], indent=2))
        
        # Test SSE stream
        print("\n--- Testing GET /api/logs/stream (SSE) ---")
        async def log_event_callback(event_type, data, event_id):
            if event_type == "ping":
                print(f"Received ping: {data}")
            elif event_type == "log":
                print(f"Received log event: {json.dumps(data, indent=2)}")
            else:
                print(f"Received unknown event type: {event_type}, data: {data}")
        
        await self.stream_sse("/api/logs/stream", log_event_callback, duration_seconds=1, api_group=api_group)
    
    async def test_statistics_api(self):
        """Test the statistics API endpoints"""
        api_group = "statistics"
        print("\n===== Testing Statistics API =====")
        
        # Test GET /api/statistics/classifications
        print("\n--- Testing GET /api/statistics/classifications ---")
        endpoint = "/api/statistics/classifications"
        classifications, response_time, success = await self.get_request(endpoint, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "success": success,
            "response_time": response_time,
            "result_count": len(classifications) if not isinstance(classifications, dict) or "error" not in classifications else 0
        })
        
        if not isinstance(classifications, dict) or "error" not in classifications:
            print(f"Found {len(classifications)} classification entries")
            if classifications:
                print("Sample classification entry:")
                print(json.dumps(classifications[0], indent=2))
        
        # Test GET /api/statistics/time-series
        print("\n--- Testing GET /api/statistics/time-series ---")
        endpoint = "/api/statistics/time-series"
        params = {"interval_minutes": 5, "hours": 1}
        time_series, response_time, success = await self.get_request(endpoint, params, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "params": params,
            "success": success,
            "response_time": response_time,
            "result_count": len(time_series) if not isinstance(time_series, dict) or "error" not in time_series else 0
        })
        
        if not isinstance(time_series, dict) or "error" not in time_series:
            print(f"Found {len(time_series)} time series entries")
            if time_series:
                print("Sample time series entry:")
                print(json.dumps(time_series[0], indent=2))
        
        # Test GET /api/statistics/summary
        print("\n--- Testing GET /api/statistics/summary ---")
        endpoint = "/api/statistics/summary"
        params = {"hours": 24}
        summary, response_time, success = await self.get_request(endpoint, params, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "params": params,
            "success": success,
            "response_time": response_time,
            "result_count": 1 if summary and not isinstance(summary, dict) or "error" not in summary else 0
        })
        
        if summary and not isinstance(summary, dict) or "error" not in summary:
            print("Statistics summary:")
            print(json.dumps(summary, indent=2))
        
        # Test SSE stream
        print("\n--- Testing GET /api/statistics/stream (SSE) ---")
        async def stats_event_callback(event_type, data, event_id):
            if event_type == "ping":
                print(f"Received ping: {data}")
            elif event_type == "statistics":
                print(f"Received statistics event: {json.dumps(data, indent=2)}")
            else:
                print(f"Received unknown event type: {event_type}, data: {data}")
        
        await self.stream_sse("/api/statistics/stream", stats_event_callback, duration_seconds=1, api_group=api_group)
    
    async def test_anomalies_api(self):
        """Test the anomalies API endpoints"""
        api_group = "anomalies"
        print("\n===== Testing Anomalies API =====")
        
        # Test GET /api/anomalies/
        print("\n--- Testing GET /api/anomalies/ ---")
        endpoint = "/api/anomalies/"
        anomalies, response_time, success = await self.get_request(endpoint, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "success": success,
            "response_time": response_time,
            "result_count": len(anomalies) if not isinstance(anomalies, dict) or "error" not in anomalies else 0
        })
        
        if not isinstance(anomalies, dict) or "error" not in anomalies:
            print(f"Found {len(anomalies)} anomaly entries")
            if anomalies:
                print("Sample anomaly entry:")
                print(json.dumps(anomalies[0], indent=2))
        
        # Test GET /api/anomalies/recent
        print("\n--- Testing GET /api/anomalies/recent ---")
        endpoint = "/api/anomalies/recent"
        params = {"hours": 24, "limit": 5}
        recent, response_time, success = await self.get_request(endpoint, params, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "params": params,
            "success": success,
            "response_time": response_time,
            "result_count": len(recent) if not isinstance(recent, dict) or "error" not in recent else 0
        })
        
        if not isinstance(recent, dict) or "error" not in recent:
            print(f"Found {len(recent)} recent anomaly entries")
            if recent:
                print("Sample recent anomaly entry:")
                print(json.dumps(recent[0], indent=2))
        
        # Test GET /api/anomalies/unidentified
        print("\n--- Testing GET /api/anomalies/unidentified ---")
        endpoint = "/api/anomalies/unidentified"
        params = {"hours": 24, "limit": 5}
        unidentified, response_time, success = await self.get_request(endpoint, params, api_group=api_group)
        self.test_results["api_groups"][api_group]["endpoints"].append({
            "endpoint": endpoint,
            "type": "rest",
            "params": params,
            "success": success,
            "response_time": response_time,
            "result_count": len(unidentified) if not isinstance(unidentified, dict) or "error" not in unidentified else 0
        })
        
        if not isinstance(unidentified, dict) or "error" not in unidentified:
            print(f"Found {len(unidentified)} unidentified entries")
            if unidentified:
                print("Sample unidentified entry:")
                print(json.dumps(unidentified[0], indent=2))
        
        # Test SSE stream
        print("\n--- Testing GET /api/anomalies/stream (SSE) ---")
        async def anomaly_event_callback(event_type, data, event_id):
            if event_type == "ping":
                print(f"Received ping: {data}")
            elif event_type == "anomaly":
                print(f"Received anomaly event: {json.dumps(data, indent=2)}")
            else:
                print(f"Received unknown event type: {event_type}, data: {data}")
        
        await self.stream_sse("/api/anomalies/stream", anomaly_event_callback, duration_seconds=1, api_group=api_group)
    
    def generate_summary(self):
        """Generate summary statistics from test results"""
        # Calculate total endpoints tested
        total_endpoints = 0
        successful_endpoints = 0
        failed_endpoints = 0
        total_response_time = 0
        endpoints_with_time = 0
        total_stream_events = 0
        
        for group_name, group_data in self.test_results["api_groups"].items():
            # Count endpoints
            total_endpoints += len(group_data["endpoints"])
            
            # Count successes and failures
            for endpoint_data in group_data["endpoints"]:
                if endpoint_data["success"]:
                    successful_endpoints += 1
                else:
                    failed_endpoints += 1
                
                # Sum response times for REST endpoints
                if endpoint_data["type"] == "rest" and "response_time" in endpoint_data:
                    total_response_time += endpoint_data["response_time"]
                    endpoints_with_time += 1
                
                # Count stream events
                if endpoint_data["type"] == "stream" and "events_received" in endpoint_data:
                    total_stream_events += endpoint_data["events_received"]
        
        # Calculate average response time
        average_response_time = total_response_time / endpoints_with_time if endpoints_with_time > 0 else 0
        
        # Calculate success rate as percentage
        success_rate = (successful_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        
        # Update summary in test results
        self.test_results["summary"] = {
            "total_endpoints": total_endpoints,
            "successful_endpoints": successful_endpoints,
            "failed_endpoints": failed_endpoints,
            "success_rate": success_rate,
            "average_response_time": average_response_time,
            "total_stream_events": total_stream_events,
        }
        
        return self.test_results["summary"]
    
    def save_results(self, output_dir="reports"):
        """Save test results to JSON and generate HTML report"""
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set test end time
        self.test_results["test_end_time"] = datetime.now().isoformat()
        
        # Calculate total duration
        start_time = datetime.fromisoformat(self.test_results["test_start_time"])
        end_time = datetime.fromisoformat(self.test_results["test_end_time"])
        self.test_results["total_duration"] = (end_time - start_time).total_seconds()
        
        # Generate summary
        self.generate_summary()
        
        # Format timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_filename = f"{output_dir}/api_test_results_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"Test results saved to {json_filename}")
        
        # Generate and save HTML report
        html_filename = f"{output_dir}/api_test_report_{timestamp}.html"
        self.generate_html_report(html_filename)
        print(f"HTML report saved to {html_filename}")
        
        return json_filename, html_filename
    
    def generate_html_report(self, filename):
        """Generate HTML report from test results"""
        # Format timestamp for display
        start_time = datetime.fromisoformat(self.test_results["test_start_time"])
        end_time = datetime.fromisoformat(self.test_results["test_end_time"])
        formatted_start = start_time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_end = end_time.strftime("%Y-%m-%d %H:%M:%S")
        duration = self.test_results["total_duration"]
        
        # Format summary data
        summary = self.test_results["summary"]
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Test Report - {formatted_start}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f7fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background-color: #3498db;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
            margin-bottom: 30px;
        }}
        header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        header p {{
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .summary-card {{
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 30px;
        }}
        .summary-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
        }}
        .summary-item {{
            text-align: center;
            padding: 15px;
            border-radius: 5px;
            background-color: #f8f9fa;
        }}
        .summary-item .value {{
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-item .label {{
            font-size: 14px;
            color: #6c757d;
        }}
        .success {{
            color: #2ecc71;
        }}
        .failure {{
            color: #e74c3c;
        }}
        .neutral {{
            color: #3498db;
        }}
        .api-group {{
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 30px;
        }}
        .api-group-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #2c3e50;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .api-group-stats {{
            font-size: 14px;
            color: #6c757d;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .badge-danger {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .badge-rest {{
            background-color: #e3f2fd;
            color: #0c5460;
        }}
        .badge-stream {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .params-container {{
            background-color: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            max-width: 300px;
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
        }}
        .chart-container {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin-bottom: 30px;
        }}
        .chart {{
            width: 45%;
            min-width: 300px;
            height: 300px;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            padding: 15px;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 14px;
            border-top: 1px solid #eee;
            margin-top: 30px;
        }}
        .test-meta {{
            text-align: right;
            font-size: 12px;
            color: #6c757d;
            margin-top: 10px;
        }}
    </style>
    <!-- Chart.js for beautiful charts -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>API Test Report</h1>
            <p>Generated on {formatted_end}</p>
            <div class="test-meta">
                <div>Test Duration: {duration:.2f} seconds</div>
                <div>User: buimutroi</div>
                <div>Date: 2025-05-19 14:20:20</div>
            </div>
        </header>
        
        <div class="summary-card">
            <div class="summary-title">Test Summary</div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Duration</div>
                    <div class="value neutral">{duration:.2f}s</div>
                </div>
                <div class="summary-item">
                    <div class="label">Total Endpoints Tested</div>
                    <div class="value neutral">{summary["total_endpoints"]}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Success Rate</div>
                    <div class="value success">{summary["success_rate"]:.1f}%</div>
                </div>
                <div class="summary-item">
                    <div class="label">Avg Response Time</div>
                    <div class="value">{summary["average_response_time"]:.3f}s</div>
                </div>
                <div class="summary-item">
                    <div class="label">Successful Calls</div>
                    <div class="value success">{summary["successful_endpoints"]}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Failed Calls</div>
                    <div class="value failure">{summary["failed_endpoints"]}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Stream Events</div>
                    <div class="value neutral">{summary["total_stream_events"]}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Base URL</div>
                    <div class="value" style="font-size: 14px;">{self.test_results["base_url"]}</div>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart">
                <canvas id="successRateChart"></canvas>
            </div>
            <div class="chart">
                <canvas id="responseTimeChart"></canvas>
            </div>
        </div>
"""
        
        # Add API group details
        for group_name, group_data in self.test_results["api_groups"].items():
            total = group_data["success"] + group_data["failed"]
            success_rate = (group_data["success"] / total * 100) if total > 0 else 0
            
            html_content += f"""
        <div class="api-group">
            <div class="api-group-title">
                <span>{group_name.capitalize()} API</span>
                <span class="api-group-stats">
                    {group_data["success"]}/{total} successful ({success_rate:.1f}%)
                </span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Type</th>
                        <th>Parameters</th>
                        <th>Status</th>
                        <th>Response Time</th>
                        <th>Results</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            # Add endpoints for this group
            for endpoint in group_data["endpoints"]:
                status_badge = f'<span class="badge badge-success">Success</span>' if endpoint["success"] else f'<span class="badge badge-danger">Failed</span>'
                type_badge = f'<span class="badge badge-rest">REST</span>' if endpoint["type"] == "rest" else f'<span class="badge badge-stream">Stream</span>'
                
                # Format time based on endpoint type
                if endpoint["type"] == "rest":
                    time_display = f'{endpoint["response_time"]:.3f}s'
                else:  # stream
                    time_display = f'{endpoint.get("total_duration", 0):.1f}s (Connection: {endpoint.get("response_time", 0):.3f}s)'
                
                # Format results count based on endpoint type
                if endpoint["type"] == "rest":
                    result_display = f'{endpoint.get("result_count", 0)} items'
                else:  # stream
                    result_display = f'{endpoint.get("events_received", 0)} events'
                
                # Format parameters if they exist
                if "params" in endpoint and endpoint["params"]:
                    params_display = f'<div class="params-container">{json.dumps(endpoint["params"], indent=2)}</div>'
                else:
                    params_display = '<span class="badge">None</span>'
                
                html_content += f"""
                    <tr>
                        <td>{endpoint["endpoint"]}</td>
                        <td>{type_badge}</td>
                        <td>{params_display}</td>
                        <td>{status_badge}</td>
                        <td>{time_display}</td>
                        <td>{result_display}</td>
                    </tr>
"""
            
            html_content += """
                </tbody>
            </table>
        </div>
"""
        
        # Complete the HTML
        html_content += """
        <footer>
            API Test Report generated with enhanced_api_test.py
        </footer>
    </div>
    
    <script>
        // Success Rate Chart
        const successRateCtx = document.getElementById('successRateChart').getContext('2d');
        const successRateChart = new Chart(successRateCtx, {
            type: 'pie',
            data: {
                labels: ['Successful', 'Failed'],
                datasets: [{
                    data: [SUCCESSFUL_COUNT, FAILED_COUNT],
                    backgroundColor: ['#2ecc71', '#e74c3c'],
                    borderColor: ['#27ae60', '#c0392b'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        text: 'API Test Success Rate'
                    }
                }
            }
        });
        
        // Response Time Chart
        const responseTimeCtx = document.getElementById('responseTimeChart').getContext('2d');
        const responseTimeChart = new Chart(responseTimeCtx, {
            type: 'bar',
            data: {
                labels: API_LABELS,
                datasets: [{
                    label: 'Average Response Time (s)',
                    data: RESPONSE_TIMES,
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        text: 'API Response Times'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Seconds'
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
        
        # Replace chart data placeholders with actual data
        successful_count = summary["successful_endpoints"]
        failed_count = summary["failed_endpoints"]
        html_content = html_content.replace("SUCCESSFUL_COUNT", str(successful_count))
        html_content = html_content.replace("FAILED_COUNT", str(failed_count))
        
        # Calculate average response times for each API group
        api_labels = []
        response_times = []
        
        for group_name, group_data in self.test_results["api_groups"].items():
            api_labels.append(f"'{group_name.capitalize()}'")
            
            # Calculate average response time for REST endpoints in this group
            total_time = 0
            count = 0
            for endpoint in group_data["endpoints"]:
                if endpoint["type"] == "rest" and "response_time" in endpoint:
                    total_time += endpoint["response_time"]
                    count += 1
            
            avg_time = total_time / count if count > 0 else 0
            response_times.append(str(round(avg_time, 3)))
        
        html_content = html_content.replace("API_LABELS", "[" + ", ".join(api_labels) + "]")
        html_content = html_content.replace("RESPONSE_TIMES", "[" + ", ".join(response_times) + "]")
        
        # Write HTML to file
        with open(filename, 'w') as f:
            f.write(html_content)
    
    async def run_all_tests(self):
        """Run all API tests"""
        self.running = True
        start_time = time.time()
        
        try:
            await self.create_session()
            
            # Test each API group
            await self.test_logs_api()
            await self.test_statistics_api()
            await self.test_anomalies_api()
            
            # Save results
            self.save_results(self.output_directory)
            
        finally:
            # Make sure to close all connections
            self.running = False
            await self.close_all_connections()
            await self.close_session()
            
            # Print duration
            duration = time.time() - start_time
            print(f"\nTotal test duration: {duration:.2f} seconds")


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test APIs for the dashboard')
    parser.add_argument('--url', type=str, default=DEFAULT_BASE_URL,
                        help=f'Base URL for API (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--output-dir', type=str, default='reports',
                        help='Directory where reports will be saved (default: reports)')
    args = parser.parse_args()
    
    # Create and run tester
    tester = APITester(base_url=args.url)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        tester.running = False
    
    # Register signal handlers
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, signal_handler)
    
    # Run the tests
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        print("Tests completed")