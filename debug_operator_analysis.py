#!/usr/bin/env python3
"""
Debug script to analyze specific operator patterns in detail.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from adif_parser import ADIFParser


def analyze_operator_patterns(qsos: List[Dict[str, Any]], target_operator: str) -> None:
    """
    Analyze QSO patterns for a specific operator to understand S&P classification.
    
    Args:
        qsos: List of QSO records
        target_operator: Operator call sign to analyze
    """
    # Filter QSOs for target operator
    operator_qsos = [qso for qso in qsos if qso.get('operator') == target_operator]
    
    if not operator_qsos:
        print(f"No QSOs found for operator {target_operator}")
        return
    
    print(f"=" * 60)
    print(f"DETAILED ANALYSIS FOR OPERATOR: {target_operator}")
    print(f"=" * 60)
    print(f"Total QSOs: {len(operator_qsos)}")
    print()
    
    # Sort by time
    operator_qsos.sort(key=lambda x: x.get('time', 0))
    
    print("QSO SEQUENCE ANALYSIS:")
    print("-" * 40)
    
    run_count = 0
    sp_count = 0
    prev_qso = None
    
    for i, qso in enumerate(operator_qsos):
        freq = qso.get('freq', 0.0)
        band = qso.get('band', 'UNK')
        time = qso.get('time', 0)
        call = qso.get('call', 'UNKNOWN')
        
        # Format time for display
        time_str = f"{time:06d}" if time else "000000"
        formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        classification = "RUN"  # Default
        reason = "First QSO"
        
        if prev_qso is not None:
            prev_freq = prev_qso.get('freq', 0.0)
            prev_band = prev_qso.get('band', 'UNK')
            
            if band == prev_band and freq is not None and prev_freq is not None:
                freq_diff_mhz = abs(freq - prev_freq)
                freq_diff_khz = freq_diff_mhz * 1000  # Convert MHz to kHz
                
                if freq_diff_mhz > 0.000200:  # 200 Hz threshold
                    classification = "S&P"
                    reason = f"Freq change: {freq_diff_khz:.1f} kHz"
                    sp_count += 1
                else:
                    classification = "RUN"
                    reason = f"Same freq: {freq_diff_khz:.1f} kHz"
                    run_count += 1
            elif band != prev_band:
                classification = "S&P"
                reason = f"Band change: {prev_band} -> {band}"
                sp_count += 1
            else:
                classification = "RUN"
                reason = "Same band, no freq data"
                run_count += 1
        else:
            run_count += 1
        
        # Show first 10 and last 10 QSOs, or all if <= 20
        if len(operator_qsos) <= 20 or i < 10 or i >= len(operator_qsos) - 10:
            print(f"{i+1:3d}. {formatted_time} {freq:8.3f} {band:>4s} {call:<12s} -> {classification:3s} ({reason})")
        elif i == 10:
            print("    ... (middle QSOs omitted) ...")
        
        prev_qso = qso
    
    print()
    print(f"CLASSIFICATION SUMMARY:")
    total_classified = run_count + sp_count
    if total_classified > 0:
        print(f"  Run QSOs: {run_count}")
        print(f"  S&P QSOs: {sp_count}")
        print(f"  Run %: {run_count/total_classified*100:.1f}%")
        print(f"  S&P %: {sp_count/total_classified*100:.1f}%")
    else:
        print("  No QSOs classified")
    
    # Analyze frequency patterns
    print()
    print("FREQUENCY ANALYSIS:")
    print("-" * 40)
    
    frequencies = {}
    for qso in operator_qsos:
        freq = qso.get('freq')
        if freq is not None:
            freq_key = f"{freq:.3f}"
            frequencies[freq_key] = frequencies.get(freq_key, 0) + 1
    
    print(f"Unique frequencies used: {len(frequencies)}")
    if len(frequencies) <= 10:
        for freq_str, count in sorted(frequencies.items()):
            print(f"  {freq_str} MHz: {count} QSOs")
    else:
        print("  (Too many unique frequencies to list)")
        
    # Show frequency distribution stats
    if frequencies:
        freq_values = [float(f) for f in frequencies.keys()]
        min_freq = min(freq_values)
        max_freq = max(freq_values)
        freq_range_khz = (max_freq - min_freq) * 1000
        
        print(f"  Frequency range: {min_freq:.3f} - {max_freq:.3f} MHz ({freq_range_khz:.1f} kHz span)")


def main() -> None:
    """Main function for operator analysis."""
    if len(sys.argv) < 2:
        print("Usage: python debug_operator_analysis.py <adif_file> [operator_call]")
        sys.exit(1)
    
    filename = sys.argv[1]
    target_operator = sys.argv[2] if len(sys.argv) > 2 else "VGO"
    
    try:
        qsos = ADIFParser.parse_adi(filename)
        analyze_operator_patterns(qsos, target_operator)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

