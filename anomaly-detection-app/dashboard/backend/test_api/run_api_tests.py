#!/usr/bin/env python3

import os
import sys
import asyncio
import argparse
from enhanced_api_test import APITester

async def main():
    print("===== Starting API Tests =====")
    print("This will test all API endpoints and generate a comprehensive report.")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run API tests')
    parser.add_argument('--output-dir', default='reports', help='Directory to save test reports')
    args = parser.parse_args()
    
    output_dir = args.output_dir
    print(f"Reports will be saved to: {output_dir}")
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create and run tester
    tester = APITester(output_directory=output_dir)
    await tester.run_all_tests()
    
    print("\n===== Test Complete =====")
    print("Reports have been saved to the 'reports' directory.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"Error: {str(e)}")