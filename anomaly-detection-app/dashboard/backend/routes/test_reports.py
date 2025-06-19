import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate prefix and tags
router = APIRouter(prefix="/test-reports", tags=["test-reports"])

# Define response models
class TestReport(BaseModel):
    filename: str
    created_at: datetime
    path: str
    size_bytes: int

class RunTestResponse(BaseModel):
    success: bool
    message: str
    report: Optional[TestReport] = None

# Get the root directory (assuming this file is in backend/routes)
ROOT_DIR = Path(__file__).parent.parent.parent
REPORTS_DIR = ROOT_DIR / "reports"

# Log the reports directory for debugging
logger.info(f"Reports directory: {REPORTS_DIR}")

# Check if we're running in Docker container
if os.path.exists('/app/test_api'):
    TEST_SCRIPT_PATH = Path('/app/test_api/run_api_tests.py')
    # In Docker, reports may be in a different location
    if os.path.exists('/app/reports'):
        REPORTS_DIR = Path('/app/reports')
else:
    TEST_SCRIPT_PATH = ROOT_DIR / "test_api" / "run_api_tests.py"

@router.get("/list", response_model=List[TestReport])
async def list_reports():
    """
    Get a list of all available API test reports
    """
    try:
        # Log the reports directory path
        logger.info(f"Checking reports in: {REPORTS_DIR}")
        
        # Ensure reports directory exists
        if not REPORTS_DIR.exists():
            logger.warning(f"Reports directory does not exist: {REPORTS_DIR}")
            return []
        
        # Get all HTML files in the reports directory
        report_files = list(REPORTS_DIR.glob("api_test_report_*.html"))
        logger.info(f"Found {len(report_files)} report files")
        
        # Sort by creation time (newest first)
        report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Convert to response model
        reports = []
        for file in report_files:
            stat = file.stat()
            reports.append(TestReport(
                filename=file.name,
                created_at=datetime.fromtimestamp(stat.st_mtime),
                path=f"/reports/{file.name}",
                size_bytes=stat.st_size
            ))
        
        logger.info(f"Returning {len(reports)} reports")
        return reports
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")

@router.get("/latest", response_model=TestReport)
async def get_latest_report():
    """
    Get the latest API test report
    """
    try:
        reports = await list_reports()
        if not reports:
            raise HTTPException(status_code=404, detail="No reports found")
        return reports[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest report: {str(e)}")

@router.post("/run", response_model=RunTestResponse)
async def run_tests():
    """
    Run API tests and generate a new report
    """
    try:
        logger.info(f"Starting API tests using {TEST_SCRIPT_PATH}")
        
        # Create reports directory if it doesn't exist
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # Check if the test script exists
        if not os.path.exists(TEST_SCRIPT_PATH):
            logger.error(f"Test script not found at path: {TEST_SCRIPT_PATH}")
            raise HTTPException(status_code=500, detail=f"Test script not found at path: {TEST_SCRIPT_PATH}")
            
        logger.info(f"Test script found at: {TEST_SCRIPT_PATH}")
        
        # Create absolute path for output directory parameter
        reports_absolute_path = str(REPORTS_DIR.absolute())
        logger.info(f"Running tests with output directory: {reports_absolute_path}")
        
        # Make sure the directory exists
        os.makedirs(reports_absolute_path, exist_ok=True)
        
        # Run the tests asynchronously to avoid blocking
        process = await asyncio.create_subprocess_exec(
            "python", str(TEST_SCRIPT_PATH),
            "--output-dir", reports_absolute_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"API tests failed: {stderr.decode()}")
            return RunTestResponse(
                success=False,
                message=f"API tests failed with exit code {process.returncode}: {stderr.decode()}"
            )
        
        # Get the latest report after running tests
        try:
            latest_report = await get_latest_report()
            return RunTestResponse(
                success=True,
                message="API tests completed successfully",
                report=latest_report
            )
        except HTTPException:
            return RunTestResponse(
                success=True,
                message="API tests completed, but no report was found"
            )
            
    except Exception as e:
        logger.error(f"Error running API tests: {str(e)}")
        return RunTestResponse(
            success=False,
            message=f"Failed to run API tests: {str(e)}"
        )