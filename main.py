#!/usr/bin/env python3
"""
Main entry point for the ADIF QSO analyzer.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from adif_parser import ADIFParser
from metrics_analyzer import QSOMetrics


def main() -> None:
    """Main function for ADIF analysis."""
    # Remove this line - use VS Code breakpoints instead
    # import debugpy; debugpy.breakpoint()  # Force debugger to stop here
    
    # Check if filename provided as command line argument
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # Default filename - change this to your exported ADIF
        filename = "data/FieldDay2025_K9K.adi"
    
    # Check if file exists
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found!")
        print("Please place your ADIF file in the project directory or specify the path.")
        print("Usage: python main.py [path_to_adif_file]")
        sys.exit(1)
    
    try:
        # Parse ADIF file
        print(f"Parsing ADIF file: {filename}")
        qsos: List[Dict[str, Any]] = ADIFParser.parse_adi(filename)
        
        if not qsos:
            print("No valid QSO records found in the file.")
            return
        
        # Generate and display comprehensive report
        report = QSOMetrics.generate_summary_report(qsos)
        print(report)
        
        # Optional: Save report to file
        output_file = f"{Path(filename).stem}_analysis.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {output_file}")
        
    except (FileNotFoundError, IOError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
