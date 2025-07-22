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
                'gaps': []
            }
        
        # Get all times and sort them
        times = [qso['time'] for qso in qsos if qso['time'] is not None]
        if not times:
            return {
                'total_hours': 0.0,
                'overall_rate': 0.0,
                'gaps': []
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
        
        return {
            'total_hours': total_hours,
            'overall_rate': overall_rate,
            'gaps': gaps,
            'start_time': start_time,
            'end_time': end_time
        }
    
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
        if log_stats['gaps']:
            report.append(f"Silent Periods (>15 min): {len(log_stats['gaps'])}")
            for i, gap in enumerate(log_stats['gaps'][:5], 1):  # Show first 5 gaps
                report.append(f"  Gap {i}: {gap['duration_min']:.0f} minutes "
                            f"({QSOMetrics._format_time(gap['start'])} - {QSOMetrics._format_time(gap['end'])})")
            if len(log_stats['gaps']) > 5:
                report.append(f"  ... and {len(log_stats['gaps']) - 5} more gaps")
        else:
            report.append("Silent Periods (>15 min): None")
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
