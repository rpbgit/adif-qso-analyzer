"""QSO metrics analyzer for contest statistics."""

from typing import List, Dict, Any
from collections import defaultdict


class QSOMetrics:
    """Calculate various QSO metrics and statistics."""
    
    @staticmethod
    def calculate_sp_percentage(qsos: List[Dict[str, Any]]) -> float:
        """
        Calculate Search & Pounce percentage.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            S&P percentage as a float
        """
        s_and_p = 0
        total = 0
        prev = None
        
        for qso in qsos:
            if prev is not None:
                # Check if same band
                if qso['band'] == prev['band']:
                    freq_diff = abs(qso['freq'] - prev['freq'])
                    # Frequency change > 200 Hz indicates S&P
                    if freq_diff > 0.000200:
                        s_and_p += 1
                    total += 1
            prev = qso
        
        if total == 0:
            return 0.0
        return 100.0 * s_and_p / total
    
    @staticmethod
    def calculate_qso_rates(qsos: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Calculate QSO rates per operator.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            Dictionary with operator statistics including rates and counts
        """
        operator_stats = defaultdict(lambda: {
            'qso_count': 0,
            'times': [],
            'avg_rate_per_hour': 0.0,
            'peak_rate_per_hour': 0.0,
            'run_percentage': 0.0,
            'sp_percentage': 0.0
        })
        
        # Group QSOs by operator and collect times
        for qso in qsos:
            operator = qso.get('operator', 'UNKNOWN')
            operator_stats[operator]['qso_count'] += 1
            if qso['time'] is not None:
                operator_stats[operator]['times'].append(qso['time'])
        
        # Calculate rates for each operator
        for operator, stats in operator_stats.items():
            times = sorted(stats['times'])
            if len(times) >= 2:
                # Calculate average rate
                duration_hours = QSOMetrics._calculate_duration_hours(times)
                if duration_hours > 0:
                    stats['avg_rate_per_hour'] = stats['qso_count'] / duration_hours
                
                # Calculate peak rate (best hour)
                stats['peak_rate_per_hour'] = QSOMetrics._calculate_peak_rate(times)
        
        # Calculate Run vs S&P percentages for each operator
        QSOMetrics._calculate_operator_sp_percentages(qsos, operator_stats)
        
        return dict(operator_stats)
    
    @staticmethod
    def _calculate_duration_hours(times: List[int]) -> float:
        """
        Calculate duration in hours from list of HHMMSS times.
        
        Args:
            times: List of times in HHMMSS format
            
        Returns:
            Duration in hours as float
        """
        if not times or len(times) < 2:
            return 0.0
        
        start_time = QSOMetrics._time_to_minutes(times[0])
        end_time = QSOMetrics._time_to_minutes(times[-1])
        
        # Handle day rollover
        if end_time < start_time:
            end_time += 24 * 60  # Add 24 hours in minutes
        
        duration_minutes = end_time - start_time
        return duration_minutes / 60.0
    
    @staticmethod
    def _calculate_peak_rate(times: List[int]) -> float:
        """
        Calculate peak QSO rate per hour using sliding window.
        
        Args:
            times: List of times in HHMMSS format
            
        Returns:
            Peak rate per hour as float
        """
        if len(times) < 2:
            return 0.0
        
        times_minutes = [QSOMetrics._time_to_minutes(t) for t in times]
        times_minutes.sort()
        
        max_rate = 0.0
        
        # Use 60-minute sliding window
        for i in range(len(times_minutes)):
            window_start = times_minutes[i]
            window_end = window_start + 60  # 60 minutes
            
            # Count QSOs in this window
            qsos_in_window = sum(1 for t in times_minutes if window_start <= t <= window_end)
            
            if qsos_in_window > max_rate:
                max_rate = qsos_in_window
        
        return max_rate
    
    @staticmethod
    def _calculate_operator_sp_percentages(qsos: List[Dict[str, Any]], 
                                         operator_stats: Dict[str, Dict[str, float]]) -> None:
        """
        Calculate Run vs S&P percentages for each operator.
        
        Args:
            qsos: List of QSO records
            operator_stats: Dictionary to update with S&P percentages
        """
        # Group QSOs by operator
        operator_qsos = defaultdict(list)
        for qso in qsos:
            operator = qso.get('operator', 'UNKNOWN')
            operator_qsos[operator].append(qso)
        
        # Calculate S&P percentage for each operator
        for operator, op_qsos in operator_qsos.items():
            if len(op_qsos) < 2:
                continue
                
            s_and_p = 0
            total = 0
            prev = None
            
            # Sort operator's QSOs by time
            sorted_qsos = sorted(op_qsos, key=lambda x: x['time'] if x['time'] is not None else 0)
            
            for qso in sorted_qsos:
                if prev is not None:
                    # Check if same band
                    if qso['band'] == prev['band']:
                        freq_diff = abs(qso['freq'] - prev['freq'])
                        # Frequency change > 200 Hz indicates S&P
                        if freq_diff > 0.000200:
                            s_and_p += 1
                        total += 1
                prev = qso
            
            if total > 0:
                sp_percentage = 100.0 * s_and_p / total
                operator_stats[operator]['sp_percentage'] = sp_percentage
                operator_stats[operator]['run_percentage'] = 100.0 - sp_percentage
            else:
                operator_stats[operator]['sp_percentage'] = 0.0
                operator_stats[operator]['run_percentage'] = 100.0
    
    @staticmethod
    def _calculate_log_statistics(qsos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate overall log statistics including duration and gaps.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            Dictionary with log statistics
        """
        if not qsos:
            return {
                'total_hours': 0.0,
                'overall_rate': 0.0,
                'gaps': [],
                'hourly_rates': [],
                'operator_sessions': {}
            }
        
        # Get all times and sort them
        times = [qso['time'] for qso in qsos if qso['time'] is not None]
        if not times:
            return {
                'total_hours': 0.0,
                'overall_rate': 0.0,
                'gaps': [],
                'hourly_rates': [],
                'operator_sessions': {}
            }
        
        times.sort()
        start_time = times[0]
        end_time = times[-1]
        
        # Calculate total duration
        total_hours = QSOMetrics._calculate_duration_hours(times)
        
        # Calculate overall rate
        overall_rate = len(qsos) / total_hours if total_hours > 0 else 0.0
        
        # Find gaps > 15 minutes
        gaps = QSOMetrics._find_silent_periods(times)
        
        # Calculate hourly rates
        hourly_rates = QSOMetrics._calculate_hourly_rates(qsos)
        
        # Calculate operator sessions
        operator_sessions = QSOMetrics._calculate_operator_sessions(qsos)
        
        return {
            'total_hours': total_hours,
            'overall_rate': overall_rate,
            'gaps': gaps,
            'start_time': start_time,
            'end_time': end_time,
            'hourly_rates': hourly_rates,
            'operator_sessions': operator_sessions
        }
    
    @staticmethod
    def _calculate_hourly_rates(qsos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate QSO rates for each hour in the log.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            List of hourly rate dictionaries with hour and qso_count
        """
        if not qsos:
            return []
        
        # Group QSOs by hour
        hourly_counts = defaultdict(int)
        
        for qso in qsos:
            if qso['time'] is not None:
                time_str = f"{qso['time']:06d}"
                hour = int(time_str[:2])
                hourly_counts[hour] += 1
        
        # Convert to sorted list
        hourly_rates = []
        for hour in sorted(hourly_counts.keys()):
            hourly_rates.append({
                'hour': hour,
                'qso_count': hourly_counts[hour]
            })
        
        return hourly_rates

    @staticmethod
    def _calculate_operator_sessions(qsos: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate operator sessions including sign-in/sign-out times and accumulated time.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            Dictionary with operator session information
        """
        if not qsos:
            return {}
        
        # Sort QSOs by time
        sorted_qsos = sorted([qso for qso in qsos if qso['time'] is not None], 
                           key=lambda x: x['time'])
        
        operator_sessions = defaultdict(lambda: {
            'sessions': [],
            'total_minutes': 0,
            'first_qso': None,
            'last_qso': None,
            'session_count': 0
        })
        
        if not sorted_qsos:
            return {}
        
        # Track current session for each operator
        current_sessions = {}
        
        for i, qso in enumerate(sorted_qsos):
            operator = qso.get('operator', 'UNKNOWN')
            current_time = qso['time']
            
            # Initialize operator data if first time seeing them
            if operator_sessions[operator]['first_qso'] is None:
                operator_sessions[operator]['first_qso'] = current_time
            
            operator_sessions[operator]['last_qso'] = current_time
            
            # Check if this is a new session for this operator
            if operator not in current_sessions:
                # Start new session
                current_sessions[operator] = {
                    'start_time': current_time,
                    'last_qso_time': current_time
                }
            else:
                # Update existing session
                current_sessions[operator]['last_qso_time'] = current_time
            
            # Look ahead to see if there's a gap or operator change
            if i < len(sorted_qsos) - 1:
                next_qso = sorted_qsos[i + 1]
                next_operator = next_qso.get('operator', 'UNKNOWN')
                next_time = next_qso['time']
                
                # Calculate gap between current and next QSO
                gap_minutes = QSOMetrics._calculate_time_gap_minutes(current_time, next_time)
                
                # End session if gap > 30 minutes or operator changes
                if gap_minutes > 30 or next_operator != operator:
                    # End current session
                    session = current_sessions[operator]
                    session_duration = QSOMetrics._calculate_time_gap_minutes(
                        session['start_time'], session['last_qso_time'])
                    
                    operator_sessions[operator]['sessions'].append({
                        'start_time': session['start_time'],
                        'end_time': session['last_qso_time'],
                        'duration_minutes': session_duration
                    })
                    
                    operator_sessions[operator]['total_minutes'] += session_duration
                    operator_sessions[operator]['session_count'] += 1
                    
                    # Remove from current sessions
                    del current_sessions[operator]
            else:
                # This is the last QSO, end any remaining sessions
                for op, session in current_sessions.items():
                    session_duration = QSOMetrics._calculate_time_gap_minutes(
                        session['start_time'], session['last_qso_time'])
                    
                    operator_sessions[op]['sessions'].append({
                        'start_time': session['start_time'],
                        'end_time': session['last_qso_time'],
                        'duration_minutes': session_duration
                    })
                    
                    operator_sessions[op]['total_minutes'] += session_duration
                    operator_sessions[op]['session_count'] += 1
        
        return dict(operator_sessions)
    
    @staticmethod
    def _calculate_time_gap_minutes(time1: int, time2: int) -> int:
        """
        Calculate gap in minutes between two HHMMSS times.
        
        Args:
            time1: First time in HHMMSS format
            time2: Second time in HHMMSS format
            
        Returns:
            Gap in minutes (always positive)
        """
        minutes1 = QSOMetrics._time_to_minutes(time1)
        minutes2 = QSOMetrics._time_to_minutes(time2)
        
        # Handle day rollover
        if minutes2 < minutes1:
            minutes2 += 24 * 60
        
        return abs(minutes2 - minutes1)

    @staticmethod
    def _find_silent_periods(times: List[int], min_gap_minutes: int = 15) -> List[Dict[str, Any]]:
        """
        Find periods with no QSO activity longer than specified threshold.
        
        Args:
            times: List of times in HHMMSS format
            min_gap_minutes: Minimum gap in minutes to consider as silent period
            
        Returns:
            List of gap dictionaries with start, end, and duration information
        """
        gaps = []
        
        for i in range(len(times) - 1):
            current_time = QSOMetrics._time_to_minutes(times[i])
            next_time = QSOMetrics._time_to_minutes(times[i + 1])
            
            # Handle day rollover
            if next_time < current_time:
                next_time += 24 * 60
            
            gap_minutes = next_time - current_time
            
            if gap_minutes > min_gap_minutes:
                gaps.append({
                    'start': times[i],
                    'end': times[i + 1],
                    'duration_min': gap_minutes
                })
        
        return gaps
    
    @staticmethod
    def _format_time(time_hhmmss: int) -> str:
        """
        Format HHMMSS time for display.
        
        Args:
            time_hhmmss: Time in HHMMSS format
            
        Returns:
            Formatted time string (HH:MM)
        """
        time_str = f"{time_hhmmss:06d}"
        hours = time_str[:2]
        minutes = time_str[2:4]
        return f"{hours}:{minutes}"
    
    @staticmethod
    def _time_to_minutes(time_hhmmss: int) -> int:
        """
        Convert HHMMSS time to minutes since midnight.
        
        Args:
            time_hhmmss: Time in HHMMSS format
            
        Returns:
            Minutes since midnight
        """
        time_str = f"{time_hhmmss:06d}"
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])
        return hours * 60 + minutes
    
    @staticmethod
    def generate_summary_report(qsos: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive summary report.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            Formatted summary report as string
        """
        sp_percentage = QSOMetrics.calculate_sp_percentage(qsos)
        operator_stats = QSOMetrics.calculate_qso_rates(qsos)
        total_qsos = len(qsos)
        
        # Calculate overall log statistics
        log_stats = QSOMetrics._calculate_log_statistics(qsos)
        
        report = []
        report.append("=" * 60)
        report.append("QSO ANALYSIS SUMMARY REPORT")
        report.append("=" * 60)
        report.append(f"Total QSOs: {total_qsos}")
        report.append(f"S&P Percentage: {sp_percentage:.1f}%")
        report.append("")
        
        # Add overall log statistics
        report.append("LOG STATISTICS:")
        report.append("-" * 40)
        report.append(f"Total Log Duration: {log_stats['total_hours']:.1f} hours")
        report.append(f"Overall QSO Rate: {log_stats['overall_rate']:.1f} QSOs/hour")
        
        # Show all gaps
        if log_stats['gaps']:
            total_silent_minutes = sum(gap['duration_min'] for gap in log_stats['gaps'])
            total_silent_hours = total_silent_minutes / 60.0
            report.append(f"Silent Periods (>15 min): {len(log_stats['gaps'])} totaling {total_silent_hours:.1f} hours")
            for i, gap in enumerate(log_stats['gaps'], 1):
                report.append(f"  Gap {i}: {gap['duration_min']:.0f} minutes "
                            f"({QSOMetrics._format_time(gap['start'])} - {QSOMetrics._format_time(gap['end'])})")
        else:
            report.append("Silent Periods (>15 min): None")
        
        # Add hourly rates
        if log_stats['hourly_rates']:
            report.append("")
            report.append("HOURLY QSO RATES:")
            report.append("-" * 40)
            for hour_data in log_stats['hourly_rates']:
                hour = hour_data['hour']
                count = hour_data['qso_count']
                report.append(f"  {hour:02d}:00-{hour:02d}:59: {count} QSOs")
        
        # Add operator sessions
        if log_stats['operator_sessions']:
            report.append("")
            report.append("OPERATOR SESSIONS:")
            report.append("-" * 40)
            for operator, session_data in sorted(log_stats['operator_sessions'].items()):
                total_hours = session_data['total_minutes'] / 60.0
                report.append(f"Operator: {operator}")
                report.append(f"  Operating Time: {total_hours:.1f} hours ({session_data['session_count']} sessions)")
                report.append(f"  First QSO: {QSOMetrics._format_time(session_data['first_qso'])}")
                report.append(f"  Last QSO: {QSOMetrics._format_time(session_data['last_qso'])}")
                
                # Show individual sessions
                if session_data['sessions']:
                    report.append("  Sessions:")
                    for i, session in enumerate(session_data['sessions'], 1):
                        duration_hours = session['duration_minutes'] / 60.0
                        report.append(f"    {i}. {QSOMetrics._format_time(session['start_time'])} - "
                                    f"{QSOMetrics._format_time(session['end_time'])} "
                                    f"({duration_hours:.1f}h)")
                report.append("")
            
            # Add total operator time summary
            total_operator_minutes = sum(session_data['total_minutes'] 
                                       for session_data in log_stats['operator_sessions'].values())
            total_operator_hours = total_operator_minutes / 60.0
            total_sessions = sum(session_data['session_count'] 
                               for session_data in log_stats['operator_sessions'].values())
            
            report.append("SUMMARY:")
            report.append(f"  Total Operator Time: {total_operator_hours:.1f} hours across {total_sessions} sessions")
        
        report.append("")
        
        report.append("OPERATOR STATISTICS:")
        report.append("-" * 40)
        
        for operator, stats in sorted(operator_stats.items()):
            # Calculate contribution percentage
            contribution_pct = (stats['qso_count'] / total_qsos) * 100 if total_qsos > 0 else 0
            
            report.append(f"Operator: {operator}")
            report.append(f"  QSO Count: {stats['qso_count']} ({contribution_pct:.1f}% of total)")
            report.append(f"  Average Rate: {stats['avg_rate_per_hour']:.1f} QSOs/hour")
            report.append(f"  Peak Rate: {stats['peak_rate_per_hour']:.0f} QSOs/hour")
            report.append(f"  Run: {stats['run_percentage']:.1f}% | S&P: {stats['sp_percentage']:.1f}%")
            report.append("")
        
        return "\n".join(report)
