
#!/usr/bin/env python3
"""
Debug script to analyze session duration calculations and identify zero-duration issues.

This script helps diagnose problems with operator session tracking, particularly
when sessions are being calculated with zero duration.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from adif_parser import ADIFParser

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def debug_session_calculations(qsos: List[Dict[str, Any]], target_operator: str = None) -> None:
    """
    Debug session duration calculations to find zero-duration issues.
    
    This analysis is particularly important for merged logs from multiple
    stations where operators may have been working simultaneously on different
    computers, resulting in apparent rapid operator changes when logs are merged.
    
    Args:
        qsos: List of QSO records
        target_operator: Specific operator to analyze (optional, analyzes all if None)
    """
    print("SESSION DURATION DEBUG ANALYSIS")
    print("=" * 50)
    if target_operator:
        print(f"Analyzing specific operator: {target_operator}")
    else:
        print("NOTE: This appears to be a merged log from multiple stations.")
        print("Zero-duration sessions may indicate concurrent operation on separate computers.")
    
    # Group QSOs by operator
    operators = {}
    for qso in qsos:
        operator = qso.get('operator', 'Unknown')
        if operator not in operators:
            operators[operator] = []
        operators[operator].append(qso)
    
    # Filter to specific operator if requested
    if target_operator:
        if target_operator.upper() in [op.upper() for op in operators.keys()]:
            # Find the exact case match
            actual_operator = next(op for op in operators.keys() if op.upper() == target_operator.upper())
            operators = {actual_operator: operators[actual_operator]}
            print(f"Found operator: {actual_operator}")
        else:
            print(f"Operator '{target_operator}' not found in log.")
            print(f"Available operators: {', '.join(operators.keys())}")
            return
    
    for operator, operator_qsos in operators.items():
        if len(operator_qsos) < 1:
            continue
            
        print(f"\nOperator: {operator}")
        print(f"Total QSOs: {len(operator_qsos)}")
        
        # Sort by time
        operator_qsos.sort(key=lambda x: x.get('time', 0))
        
        # Calculate sessions using same logic as metrics analyzer
        sessions = []
        current_session_start = None
        current_session_qsos = []
        
        for i, qso in enumerate(operator_qsos):
            qso_time = qso.get('time')
            if qso_time is None:
                continue
                
            if current_session_start is None:
                # Start new session
                current_session_start = qso_time
                current_session_qsos = [qso]
            else:
                # Check time gap
                prev_time = current_session_qsos[-1].get('time')
                time_gap_minutes = calculate_time_gap_minutes(prev_time, qso_time)
                
                if time_gap_minutes > 15:  # 15 minute gap threshold (matching metrics_analyzer)
                    # End current session and start new one
                    session_end = current_session_qsos[-1].get('time')
                    duration_minutes = calculate_time_gap_minutes(current_session_start, session_end)
                    
                    sessions.append({
                        'start': current_session_start,
                        'end': session_end,
                        'duration_minutes': duration_minutes,
                        'qso_count': len(current_session_qsos)
                    })
                    
                    # Start new session
                    current_session_start = qso_time
                    current_session_qsos = [qso]
                else:
                    # Continue current session
                    current_session_qsos.append(qso)
        
        # Don't forget the last session
        if current_session_start is not None and current_session_qsos:
            session_end = current_session_qsos[-1].get('time')
            duration_minutes = calculate_time_gap_minutes(current_session_start, session_end)
            
            sessions.append({
                'start': current_session_start,
                'end': session_end,
                'duration_minutes': duration_minutes,
                'qso_count': len(current_session_qsos)
            })
        
        # Analyze sessions
        print(f"Sessions found: {len(sessions)}")
        
        zero_duration_count = 0
        total_duration = 0
        
        for i, session in enumerate(sessions, 1):
            start_str = format_time(session['start'])
            end_str = format_time(session['end'])
            duration_minutes = session['duration_minutes']
            duration_hours = duration_minutes / 60.0
            qso_count = session['qso_count']
            
            status = "ZERO DURATION!" if duration_minutes == 0 else "OK"
            if duration_minutes == 0:
                zero_duration_count += 1
            
            total_duration += duration_minutes
            
            print(f"  Session {i}: {start_str} - {end_str} "
                  f"({duration_hours:.1f}h, {qso_count} QSOs) {status}")
            
            if duration_minutes == 0:
                print(f"    DEBUG: start={session['start']}, end={session['end']}")
                print(f"    Raw time diff: {session['end'] - session['start']}")
                
                # Show QSO details for zero-duration sessions
                if qso_count == 1:
                    print("    CAUSE: Single QSO session (start == end)")
                    print("    LIKELY: Operator logged single QSO on separate station during multi-station operation")
                else:
                    print(f"    CAUSE: {qso_count} QSOs logged within same minute")
                    print("    NORMAL: Multiple QSOs per minute are common in contest operations")
                    
        print(f"\nSUMMARY:")
        print(f"  Zero-duration sessions: {zero_duration_count}/{len(sessions)}")
        print(f"  Total session time: {total_duration/60.0:.1f} hours")
        
        # Show time gaps between consecutive QSOs
        if len(operator_qsos) > 1:
            print(f"\nTIME GAPS ANALYSIS:")
            large_gaps = 0
            for i in range(len(operator_qsos) - 1):
                current_time = operator_qsos[i].get('time')
                next_time = operator_qsos[i + 1].get('time')
                
                if current_time and next_time:
                    gap_minutes = calculate_time_gap_minutes(current_time, next_time)
                    if gap_minutes > 15:
                        large_gaps += 1
                        print(f"    Gap {large_gaps}: {gap_minutes:.0f} minutes "
                              f"({format_time(current_time)} -> {format_time(next_time)})")
            
            if large_gaps == 0:
                print("    No gaps > 15 minutes found")


def calculate_time_gap_minutes(time1: int, time2: int) -> int:
    """
    Calculate time gap between two HHMMSS times in minutes.
    
    Args:
        time1: First time in HHMMSS format
        time2: Second time in HHMMSS format
        
    Returns:
        Time gap in minutes (always positive)
    """
    def time_to_minutes(time_hhmmss: int) -> int:
        """Convert HHMMSS time to minutes since midnight."""
        time_str = f"{time_hhmmss:06d}"
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])
        return hours * 60 + minutes
    
    minutes1 = time_to_minutes(time1)
    minutes2 = time_to_minutes(time2)
    
    # Handle day rollover
    if minutes2 < minutes1:
        minutes2 += 24 * 60
    
    return abs(minutes2 - minutes1)


def format_time(time_hhmmss: int) -> str:
    """
    Format HHMMSS time for display.
    
    Args:
        time_hhmmss: Time in HHMMSS format
        
    Returns:
        Formatted time string (HH:MM:SS)
    """
    time_str = f"{time_hhmmss:06d}"
    return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"


def analyze_qso_distribution(qsos: List[Dict[str, Any]], target_operator: str = None) -> None:
    """
    Analyze QSO time distribution to understand session patterns.
    
    Args:
        qsos: List of QSO records
        target_operator: Specific operator to analyze (optional, analyzes all if None)
    """
    print("\nQSO TIME DISTRIBUTION ANALYSIS")
    print("=" * 40)
    
    # Group by operator
    operators = {}
    for qso in qsos:
        operator = qso.get('operator', 'Unknown')
        if operator not in operators:
            operators[operator] = []
        operators[operator].append(qso)
    
    # Filter to specific operator if requested
    if target_operator:
        if target_operator.upper() in [op.upper() for op in operators.keys()]:
            # Find the exact case match
            actual_operator = next(op for op in operators.keys() if op.upper() == target_operator.upper())
            operators = {actual_operator: operators[actual_operator]}
        else:
            print(f"Operator '{target_operator}' not found for QSO distribution analysis.")
            return
    
    for operator, operator_qsos in operators.items():
        if len(operator_qsos) < 2:
            continue
            
        # Sort by time
        operator_qsos.sort(key=lambda x: x.get('time', 0))
        
        times = [qso.get('time') for qso in operator_qsos if qso.get('time')]
        if len(times) < 2:
            continue
            
        print(f"\nOperator: {operator}")
        print(f"  First QSO: {format_time(times[0])}")
        print(f"  Last QSO: {format_time(times[-1])}")
        
        # Calculate time span
        first_minutes = calculate_time_gap_minutes(0, times[0])
        last_minutes = calculate_time_gap_minutes(0, times[-1])
        if last_minutes < first_minutes:
            last_minutes += 24 * 60
        
        total_span_minutes = last_minutes - first_minutes
        total_span_hours = total_span_minutes / 60.0
        
        print(f"  Time span: {total_span_hours:.1f} hours")
        print(f"  QSO density: {len(times)/total_span_hours:.1f} QSOs/hour")
        
        # Find unique time values (to detect same-time QSOs)
        unique_times = set(times)
        if len(unique_times) != len(times):
            duplicate_count = len(times) - len(unique_times)
            print(f"  NORMAL: {duplicate_count} QSOs share timestamps (multiple QSOs per minute)")
            print("  This is typical for active contest operators")


def analyze_session_algorithm(qsos: List[Dict[str, Any]], target_operator: str = None) -> None:
    """
    Analyze the session detection algorithm step by step.
    
    Args:
        qsos: List of QSO records
        target_operator: Specific operator to analyze (optional, analyzes all if None)
    """
    print("\nSESSION ALGORITHM STEP-BY-STEP ANALYSIS")
    print("=" * 50)
    
    # Sort all QSOs by time (like metrics_analyzer does)
    sorted_qsos = sorted([qso for qso in qsos if qso['time'] is not None], 
                        key=lambda x: x['time'])
    
    # Filter to specific operator if requested
    if target_operator:
        sorted_qsos = [qso for qso in sorted_qsos 
                      if qso.get('operator', 'UNKNOWN').upper() == target_operator.upper()]
        print(f"Analyzing {len(sorted_qsos)} QSOs for operator: {target_operator}")
    else:
        print(f"Total QSOs sorted by time: {len(sorted_qsos)}")
    
    # Track current sessions for each operator (like metrics_analyzer)
    current_sessions = {}
    session_count = 0
    
    for i, qso in enumerate(sorted_qsos):
        operator = qso.get('operator', 'UNKNOWN')
        current_time = qso['time']
        
        print(f"\nQSO {i+1}: {format_time(current_time)} - {operator}")
        
        # Check if this is a new session for this operator
        if operator not in current_sessions:
            # Start new session
            current_sessions[operator] = {
                'start_time': current_time,
                'last_qso_time': current_time,
                'qso_count': 1
            }
            print(f"  -> Started new session for {operator}")
        else:
            # Update existing session
            current_sessions[operator]['last_qso_time'] = current_time
            current_sessions[operator]['qso_count'] += 1
            print(f"  -> Continuing session for {operator} (QSO #{current_sessions[operator]['qso_count']})")
        
        # Look ahead to see if there's a gap or operator change
        if i < len(sorted_qsos) - 1:
            next_qso = sorted_qsos[i + 1]
            next_operator = next_qso.get('operator', 'UNKNOWN')
            next_time = next_qso['time']
            
            # Calculate gap between current and next QSO
            gap_minutes = calculate_time_gap_minutes(current_time, next_time)
            print(f"  -> Next QSO: {format_time(next_time)} - {next_operator} (gap: {gap_minutes} min)")
            
            # End session if gap > 15 minutes or operator changes
            if gap_minutes > 15 or next_operator != operator:
                # End current session
                session = current_sessions[operator]
                session_duration = calculate_time_gap_minutes(
                    session['start_time'], session['last_qso_time'])
                
                session_count += 1
                print(f"  -> ENDING session {session_count} for {operator}:")
                print(f"     Duration: {session_duration} minutes ({session_duration/60.0:.1f}h)")
                print(f"     QSOs: {session['qso_count']}")
                print(f"     Reason: {'Gap > 15 min' if gap_minutes > 15 else 'Operator change'}")
                
                if session_duration == 0:
                    print(f"     WARNING: Zero duration session!")
                
                # Remove from current sessions
                del current_sessions[operator]
        else:
            print(f"  -> Last QSO in log")
    
    # End any remaining sessions
    print(f"\nEnding remaining active sessions:")
    for operator, session in current_sessions.items():
        session_duration = calculate_time_gap_minutes(
            session['start_time'], session['last_qso_time'])
        
        session_count += 1
        print(f"  Session {session_count} for {operator}:")
        print(f"    Duration: {session_duration} minutes ({session_duration/60.0:.1f}h)")
        print(f"    QSOs: {session['qso_count']}")
        
        if session_duration == 0:
            print(f"    WARNING: Zero duration session!")


def main() -> None:
    """Main function for session debug analysis."""
    if len(sys.argv) < 2:
        print("Usage: python debug_sessions.py <adif_file> [operator]")
        print("\nThis script analyzes operator session calculations to identify")
        print("why some sessions show zero duration.")
        print("\nExamples:")
        print("  python debug_sessions.py data/file.adi        # Analyze all operators")
        print("  python debug_sessions.py data/file.adi 9ZV    # Analyze specific operator")
        sys.exit(1)
    
    filename = sys.argv[1]
    target_operator = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        print(f"Loading ADIF file: {filename}")
        qsos = ADIFParser.parse_adi(filename)
        print(f"Loaded {len(qsos)} QSO records")
        
        if not qsos:
            print("No QSO records found in file.")
            sys.exit(1)
        
        # Run debug analysis
        debug_session_calculations(qsos, target_operator)
        analyze_qso_distribution(qsos, target_operator)
        analyze_session_algorithm(qsos, target_operator)
        
        print("\nDEBUG COMPLETE")
        print("=" * 50)
        print("ANALYSIS SUMMARY:")
        print("1. Sessions with zero duration")
        print("2. Single QSO sessions (start == end)")
        print("3. Time gaps between QSOs")
        print("4. Session algorithm step-by-step execution")
        print("5. Multi-station operation patterns")
        print("")
        print("MULTI-STATION FIELD DAY EXPLANATION:")
        print("Zero-duration sessions are NORMAL for merged logs from multiple")
        print("logging computers. When operators work simultaneously on different")
        print("stations and logs are merged by time, it creates apparent rapid")
        print("operator changes. This is correct behavior, not a bug.")
        print("")
        print("CONTEST OPERATION NOTES:")
        print("- Multiple QSOs per minute are common and normal")
        print("- Skilled operators can make 60+ QSOs/hour during peak times")
        print("- Sessions with same start/end minute contain rapid QSOs")
        print("")
        print("RECOMMENDATION:")
        print("Consider grouping sessions by station/frequency/band to get")
        print("more accurate per-station operator time accounting.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
