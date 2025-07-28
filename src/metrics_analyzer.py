"""QSO metrics analyzer for contest statistics."""

from typing import List, Dict, Any
from collections import defaultdict


class QSOMetrics:
    @staticmethod
    def _format_section_table_side_by_side(sections: list) -> list:
        """
        Format the section table into three columns, side by side.
        Each section is a tuple: (section, count, percent)
        """
        # Split into three columns 
        n = len(sections)
        col_len = (n + 2) // 3
        col1 = sections[:col_len]
        col2 = sections[col_len:2*col_len]
        col3 = sections[2*col_len:]
        # Pad columns to equal length
        max_len = max(len(col1), len(col2), len(col3))
        if len(col1) < max_len:
            col1 += [("", "", "")] * (max_len - len(col1))
        if len(col2) < max_len:
            col2 += [("", "", "")] * (max_len - len(col2))
        if len(col3) < max_len:
            col3 += [("", "", "")] * (max_len - len(col3))
        # Prepare header and separator for three columns
        header = " Section   Total   % | Section   Total   % | Section   Total   %"
        sep    = " -------   ----- --- | -------   ----- --- | -------   ----- ---"
        lines = [header, sep]
        # Combine rows with fixed widths
        for (c1, c2, c3) in zip(col1, col2, col3):
            lstr = f" {c1[0]:<9} {c1[1]:>5} {c1[2]:>3}"
            mstr = f" {c2[0]:<9} {c2[1]:>5} {c2[2]:>3}" if c2[0] else ""
            rstr = f" {c3[0]:<9} {c3[1]:>5} {c3[2]:>3}" if c3[0] else ""
            lines.append(f"{lstr} |{mstr} |{rstr}")
        return lines
    @staticmethod
    def _find_silent_periods_by_computer(qsos: List[Dict[str, Any]], min_gap_minutes: int = 15) -> Dict[str, list]:
        """
        Find silent periods (gaps) for each computer in the log.
        Returns a dict: computer_name -> list of gap dicts
        """
        from collections import defaultdict
        computer_gaps = {}
        qsos_by_computer = defaultdict(list)
        for qso in qsos:
            computer = qso.get('station', 'UNKNOWN')  # Use 'station' as computer name
            if qso.get('time') is not None:
                qsos_by_computer[computer].append(qso)
        for computer, comp_qsos in qsos_by_computer.items():
            times = sorted(qso['time'] for qso in comp_qsos if qso.get('time') is not None)
            computer_gaps[computer] = QSOMetrics._find_silent_periods(times, min_gap_minutes)
        return computer_gaps

    @staticmethod
    def _generate_computer_gap_section(qsos: List[Dict[str, Any]], min_gap_minutes: int = 15) -> list:
        """
        Generate a report section listing silent periods for each computer.
        """
        section = []
        computer_gaps = QSOMetrics._find_silent_periods_by_computer(qsos, min_gap_minutes)
        section.append("")
        section.append(f"SILENT PERIODS BY COMPUTER (>{min_gap_minutes} min):")
        section.append("-" * 40)
        any_gaps = False
        for computer, gaps in sorted(computer_gaps.items()):
            section.append(f"Computer: {computer}")
            if not gaps:
                section.append("  No silent periods detected.")
                continue
            any_gaps = True
            for i, gap in enumerate(gaps, 1):
                start = gap['start']
                end = gap['end']
                duration = gap['duration_min']
                section.append(f"  Gap {i}: {duration:.0f} minutes ({QSOMetrics._format_time(start)} - {QSOMetrics._format_time(end)})")
            section.append("")
        if not any_gaps:
            section.append("No silent periods detected for any computer.")
        section.append("")
        return section

    
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
        
        # Band center frequencies for estimation when needed
        band_freq_map = {
            '160M': 1.900, '80M': 3.750, '60M': 5.330, '40M': 7.100, '30M': 10.125,
            '20M': 14.200, '17M': 18.100, '15M': 21.200, '12M': 24.900, '10M': 28.400,
            '6M': 50.100, '4M': 70.200, '2M': 144.200, '1.25M': 222.100, '70CM': 432.100
        }
        
        for qso in qsos:
            if prev is not None:
                # Check if same band
                if qso.get('band') == prev.get('band'):
                    # Get frequencies, estimating from band if missing
                    current_freq = qso.get('freq')
                    if current_freq is None and qso.get('band'):
                        current_freq = band_freq_map.get(qso.get('band', '').upper().strip(), 14.200)
                    
                    prev_freq = prev.get('freq')
                    if prev_freq is None and prev.get('band'):
                        prev_freq = band_freq_map.get(prev.get('band', '').upper().strip(), 14.200)
                    
                    # Only calculate if we have frequency data (actual or estimated)
                    if current_freq is not None and prev_freq is not None:
                        freq_diff = abs(current_freq - prev_freq)
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
            'sp_percentage': 0.0,
            'missing_freq_count': 0,
            'sp_analysis_reliable': True
        })
        
        # Group QSOs by operator and collect times
        for qso in qsos:
            operator = qso.get('operator', 'UNKNOWN')
            operator_stats[operator]['qso_count'] += 1
            if qso['time'] is not None:
                operator_stats[operator]['times'].append(qso['time'])
            # Track missing frequency data per operator
            if qso.get('freq') is None:
                operator_stats[operator]['missing_freq_count'] += 1
        
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
            elif len(times) == 1:
                # If only one QSO, set average rate to 1.0
                stats['avg_rate_per_hour'] = 1.0
                stats['peak_rate_per_hour'] = 1.0
        
        # Calculate Run vs S&P percentages for each operator
        QSOMetrics._calculate_operator_sp_percentages(qsos, operator_stats)
        
        # Update S&P analysis reliability per operator
        for operator, stats in operator_stats.items():
            if stats['missing_freq_count'] > 0:
                stats['sp_analysis_reliable'] = False
        
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
            if len(op_qsos) == 1:
                operator_stats[operator]['sp_percentage'] = 0.0
                operator_stats[operator]['run_percentage'] = 100.0
                continue

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
                    if qso.get('band') == prev.get('band'):
                        # Get frequencies, estimating from band if missing
                        band_freq_map = {
                            '160M': 1.900, '80M': 3.750, '60M': 5.330, '40M': 7.100, '30M': 10.125,
                            '20M': 14.200, '17M': 18.100, '15M': 21.200, '12M': 24.900, '10M': 28.400,
                            '6M': 50.100, '4M': 70.200, '2M': 144.200, '1.25M': 222.100, '70CM': 432.100
                        }

                        current_freq = qso.get('freq')
                        if current_freq is None and qso.get('band'):
                            current_freq = band_freq_map.get(qso.get('band', '').upper().strip(), 14.200)

                        prev_freq = prev.get('freq')
                        if prev_freq is None and prev.get('band'):
                            prev_freq = band_freq_map.get(prev.get('band', '').upper().strip(), 14.200)

                        # Only calculate if we have frequency data (actual or estimated)
                        if current_freq is not None and prev_freq is not None:
                            freq_diff = abs(current_freq - prev_freq)
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
                'operator_sessions': {},
                'time_accounting': QSOMetrics._calculate_accurate_time_accounting([])
            }
        
        # Get all times and sort them
        times = [qso['time'] for qso in qsos if qso['time'] is not None]
        if not times:
            return {
                'total_hours': 0.0,
                'overall_rate': 0.0,
                'gaps': [],
                'hourly_rates': [],
                'operator_sessions': {},
                'time_accounting': QSOMetrics._calculate_accurate_time_accounting([])
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
        
        # Calculate accurate time accounting
        time_accounting = QSOMetrics._calculate_accurate_time_accounting(qsos)
        
        return {
            'total_hours': total_hours,
            'overall_rate': overall_rate,
            'gaps': gaps,
            'start_time': start_time,
            'end_time': end_time,
            'hourly_rates': hourly_rates,
            'operator_sessions': operator_sessions,
            'time_accounting': time_accounting
        }
    
    @staticmethod
    def _calculate_accurate_time_accounting(qsos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate accurate time accounting with proper reconciliation.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            Dictionary with reconciled time statistics
        """
        if not qsos:
            return {
                'total_log_hours': 0.0,
                'active_operating_hours': 0.0,
                'all_gap_hours': 0.0,
                'long_gap_hours': 0.0,
                'short_gap_hours': 0.0,
                'reconciliation_check': True
            }
        
        # Get all times and sort them
        times = [qso['time'] for qso in qsos if qso['time'] is not None]
        if not times:
            return {
                'total_log_hours': 0.0,
                'active_operating_hours': 0.0,
                'all_gap_hours': 0.0,
                'long_gap_hours': 0.0,
                'short_gap_hours': 0.0,
                'reconciliation_check': True
            }
        
        times.sort()
        
        # Calculate total log duration (first QSO to last QSO)
        total_log_minutes = QSOMetrics._calculate_time_gap_minutes(times[0], times[-1])
        total_log_hours = total_log_minutes / 60.0
        
        # Get operator sessions and create timeline of active periods
        operator_sessions = QSOMetrics._calculate_operator_sessions(qsos)
        
        # Create timeline of all active periods (no overlaps since operators work on separate stations)
        active_periods = []
        for operator_station_key, session_data in operator_sessions.items():
            for session in session_data['sessions']:
                start_minutes = QSOMetrics._time_to_minutes(session['start_time'])
                end_minutes = QSOMetrics._time_to_minutes(session['end_time'])
                # Handle day rollover
                if end_minutes < start_minutes:
                    end_minutes += 24 * 60
                active_periods.append((start_minutes, end_minutes))
        
        # Sort active periods and calculate total active time
        active_periods.sort()
        total_active_minutes = sum(end - start for start, end in active_periods)
        total_active_hours = total_active_minutes / 60.0
        
        # Calculate all gap time
        all_gap_hours = total_log_hours - total_active_hours
        
        # Calculate long gaps (>15 minutes)
        gaps = QSOMetrics._find_silent_periods(times)
        long_gap_minutes = sum(gap['duration_min'] for gap in gaps)
        long_gap_hours = long_gap_minutes / 60.0
        
        # Calculate short gaps
        short_gap_hours = all_gap_hours - long_gap_hours
        
        # Reconciliation check (should be close to 0)
        reconciliation_diff = abs(total_log_hours - (total_active_hours + all_gap_hours))
        reconciliation_check = reconciliation_diff < 0.1  # Within 6 minutes tolerance
        
        return {
            'total_log_hours': total_log_hours,
            'active_operating_hours': total_active_hours,
            'all_gap_hours': all_gap_hours,
            'long_gap_hours': long_gap_hours,
            'short_gap_hours': short_gap_hours,
            'reconciliation_check': reconciliation_check,
            'reconciliation_diff': reconciliation_diff
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
        Sessions are grouped by operator + station combination. When an operator moves
        to a different station, their session on the original station ends.
        
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
        
        if not sorted_qsos:
            return {}
        
        # Group QSOs by operator + station combination
        operator_station_qsos = defaultdict(list)
        for qso in sorted_qsos:
            operator = qso.get('operator', 'UNKNOWN')
            station = qso.get('station', 'HAL 9000')
            # Create unique key for operator@station
            operator_station_key = f"{operator}@{station}"
            operator_station_qsos[operator_station_key].append(qso)
        
        operator_sessions = {}
        
        # Process each operator@station combination separately
        for operator_station_key, qsos_list in operator_station_qsos.items():
            # Extract operator and station from the key
            operator, station = operator_station_key.split('@', 1)
            
            # Sort this operator@station's QSOs by time
            qsos_list.sort(key=lambda x: x['time'])
            
            operator_sessions[operator_station_key] = {
                'operator': operator,
                'station': station,
                'sessions': [],
                'total_minutes': 0,
                'first_qso': qsos_list[0]['time'],
                'last_qso': qsos_list[-1]['time'],
                'session_count': 0
            }
            
            # Process sessions for this operator@station using 15-minute gap rule
            current_session_start = qsos_list[0]['time']
            current_session_end = qsos_list[0]['time']
            
            for i in range(1, len(qsos_list)):
                current_qso = qsos_list[i]
                prev_qso = qsos_list[i-1]
                
                # Calculate gap between consecutive QSOs for this operator@station
                gap_minutes = QSOMetrics._calculate_time_gap_minutes(
                    prev_qso['time'], current_qso['time'])
                
                if gap_minutes > 15:
                    # End current session and start new one
                    session_duration = QSOMetrics._calculate_time_gap_minutes(
                        current_session_start, current_session_end)
                    
                    # For multi-station operations: assign minimum 2-minute duration 
                    # to single QSO sessions (realistic time for QSO + logging)
                    if session_duration == 0:
                        session_duration = 2
                    
                    operator_sessions[operator_station_key]['sessions'].append({
                        'start_time': current_session_start,
                        'end_time': current_session_end,
                        'duration_minutes': session_duration
                    })
                    
                    operator_sessions[operator_station_key]['total_minutes'] += session_duration
                    operator_sessions[operator_station_key]['session_count'] += 1
                    
                    # Start new session
                    current_session_start = current_qso['time']
                    current_session_end = current_qso['time']
                else:
                    # Continue current session
                    current_session_end = current_qso['time']
            
            # Add the final session
            session_duration = QSOMetrics._calculate_time_gap_minutes(
                current_session_start, current_session_end)
            
            # For multi-station operations: assign minimum 2-minute duration 
            # to single QSO sessions (realistic time for QSO + logging)
            if session_duration == 0:
                session_duration = 2
            
            operator_sessions[operator_station_key]['sessions'].append({
                'start_time': current_session_start,
                'end_time': current_session_end,
                'duration_minutes': session_duration
            })
            
            operator_sessions[operator_station_key]['total_minutes'] += session_duration
            operator_sessions[operator_station_key]['session_count'] += 1
        
        return operator_sessions
    
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
    def _format_time(time_hhmmss: int, date: str = None) -> str:
        """
        Format HHMMSS time (optionally with date) for display.
        
        Args:
            time_hhmmss: Time in HHMMSS format
            date: Optional date string (YYYY-MM-DD)
        Returns:
            Formatted time string (YYYY-MM-DD HH:MM or HH:MM)
        """
        time_str = f"{time_hhmmss:06d}"
        hours = time_str[:2]
        minutes = time_str[2:4]
        if date:
            return f"{date} {hours}:{minutes}"
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
    def analyze_data_quality(qsos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze data quality and identify potential issues.
        
        Args:
            qsos: List of QSO records
            
        Returns:
            Dictionary with data quality metrics
        """
        if not qsos:
            return {
                'total_qsos': 0,
                'missing_frequency': 0,
                'missing_band': 0,
                'missing_time': 0,
                'freq_coverage': 0.0,
                'sp_analysis_reliable': False
            }
            
        total_qsos = len(qsos)
        missing_freq = sum(1 for qso in qsos if qso.get('freq') is None)
        missing_band = sum(1 for qso in qsos if qso.get('band') is None)
        missing_time = sum(1 for qso in qsos if qso.get('time') is None)
        
        # Check if frequencies are estimated (all frequencies are exact band center frequencies)
        estimated_freq_count = 0
        if missing_freq == 0:  # Only check if we have frequency data
            band_freq_map = {
                '160M': 1.900, '80M': 3.750, '60M': 5.330, '40M': 7.100, '30M': 10.125,
                '20M': 14.200, '17M': 18.100, '15M': 21.200, '12M': 24.900, '10M': 28.400,
                '6M': 50.100, '4M': 70.200, '2M': 144.200, '1.25M': 222.100, '70CM': 432.100
            }
            
            for qso in qsos:
                freq = qso.get('freq')
                band = qso.get('band', '').upper().strip()
                if freq is not None and band in band_freq_map:
                    if abs(freq - band_freq_map[band]) < 0.001:  # Within 1 kHz of band center
                        estimated_freq_count += 1
        
        freq_coverage = (total_qsos - missing_freq) / total_qsos * 100 if total_qsos > 0 else 0
        sp_analysis_reliable = missing_freq == 0 and estimated_freq_count < (total_qsos * 0.9)
        
        return {
            'total_qsos': total_qsos,
            'missing_frequency': missing_freq,
            'missing_band': missing_band,
            'missing_time': missing_time,
            'freq_coverage': freq_coverage,
            'estimated_frequencies': estimated_freq_count,
            'sp_analysis_reliable': sp_analysis_reliable,
            'frequencies_estimated': estimated_freq_count > (total_qsos * 0.5)
        }
    
    @staticmethod
    def generate_summary_report(qsos: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive summary report with date and time for all time fields.
        """
        sp_percentage = QSOMetrics.calculate_sp_percentage(qsos)
        operator_stats = QSOMetrics.calculate_qso_rates(qsos)
        total_qsos = len(qsos)
        data_quality = QSOMetrics.analyze_data_quality(qsos)
        log_stats = QSOMetrics._calculate_log_statistics(qsos)

        report = []
        report.append("=" * 60)
        report.append("QSO ANALYSIS SUMMARY REPORT")
        report.append("=" * 60)
        report.append(f"Total QSOs: {total_qsos}")

        report.extend(QSOMetrics._generate_data_quality_section(data_quality, sp_percentage))
        report.extend(QSOMetrics._generate_log_statistics_section(log_stats, qsos))
        report.extend(QSOMetrics._generate_band_mode_breakdown(qsos))
        report.extend(QSOMetrics._generate_section_table(qsos, total_qsos))
        report.extend(QSOMetrics._generate_country_table(qsos, total_qsos))
        report.extend(QSOMetrics._generate_operator_table(qsos, total_qsos))
        report.extend(QSOMetrics._generate_operator_sessions_section(log_stats.get('operator_sessions', {}), qsos))
        report.extend(QSOMetrics._generate_operator_statistics(operator_stats, total_qsos))
        report.extend(QSOMetrics._generate_computer_gap_section(qsos, min_gap_minutes=15))

        return "\n".join(report)
    @staticmethod
    def _generate_operator_table(qsos: List[Dict[str, Any]], total_qsos: int) -> list:
        section = []
        operator_counts = {}
        for qso in qsos:
            operator = qso.get('operator', 'UNKNOWN')
            if operator is None:
                operator = 'UNKNOWN'
            operator = str(operator).strip().upper()
            operator_counts[operator] = operator_counts.get(operator, 0) + 1
        if '' in operator_counts:
            operator_counts['UNKNOWN'] = operator_counts.get('UNKNOWN', 0) + operator_counts['']
            del operator_counts['']
        sorted_operators = sorted(operator_counts.items(), key=lambda x: (-x[1], x[0]))
        section.append("")
        section.append("Total Contacts by Operator:")
        section.append(" Operator       Total     %")
        section.append(" --------       -----   ---")
        for operator, count in sorted_operators:
            pct = int(round((count / total_qsos * 100))) if total_qsos > 0 else 0
            section.append(f" {operator:<12} {count:7d} {pct:5d}")
        total_contacts = sum(count for _, count in sorted_operators)
        section.append(f" Total = {total_contacts}\n")
        return section

    @staticmethod
    def _generate_operator_sessions_section(operator_sessions: Dict[str, Any], qsos: List[Dict[str, Any]]) -> list:
        section = []
        if not operator_sessions:
            return section
        section.append("")
        section.append("OPERATOR SESSIONS:")
        section.append("-" * 40)
        for operator_station_key, session_data in sorted(operator_sessions.items()):
            operator = session_data['operator']
            station = session_data['station']
            total_hours = session_data['total_minutes'] / 60.0
            total_qsos_for_station = sum(1 for qso in qsos if qso.get('operator', 'UNKNOWN') == operator and qso.get('station', 'HAL 9000') == station)
            section.append(f"Operator: {operator} @ Station: {station}")
            section.append(f"  Operating Time: {total_hours:.1f} hours ({session_data['session_count']} sessions, {total_qsos_for_station} QSOs)")
            section.append(f"  First QSO: {QSOMetrics._format_time(session_data['first_qso'])}")
            section.append(f"  Last QSO: {QSOMetrics._format_time(session_data['last_qso'])}")
            if session_data['sessions']:
                section.append("  Sessions:")
                for i, session in enumerate(session_data['sessions'], 1):
                    duration_hours = session['duration_minutes'] / 60.0
                    session_qso_count = sum(1 for qso in qsos if qso.get('operator', 'UNKNOWN') == operator and qso.get('station', 'HAL 9000') == station and session['start_time'] <= qso['time'] <= session['end_time'])
                    section.append(f"    {i}. {QSOMetrics._format_time(session['start_time'])} - "
                                   f"{QSOMetrics._format_time(session['end_time'])} "
                                   f"({duration_hours:.1f}h, {session_qso_count} QSOs)")
            section.append("")
        total_operator_minutes = sum(session_data['total_minutes'] for session_data in operator_sessions.values())
        total_operator_hours = total_operator_minutes / 60.0
        total_sessions = sum(session_data['session_count'] for session_data in operator_sessions.values())
        section.append("SUMMARY:")
        section.append(f"  Total Operator Time: {total_operator_hours:.1f} hours across {total_sessions} sessions")
        single_qso_sessions = 0
        for session_data in operator_sessions.values():
            for session in session_data['sessions']:
                if session['duration_minutes'] <= 2:
                    single_qso_sessions += 1
        if total_sessions > 0 and single_qso_sessions > total_sessions * 0.3:
            section.append("")
            section.append("MULTI-STATION OPERATION DETECTED:")
            section.append(f"  {single_qso_sessions} short sessions detected (likely single QSOs)")
            section.append("  This suggests a merged log from multiple logging computers.")
            section.append("  Session times represent minimum estimates for multi-station operations.")
        section.append("")
        return section

    @staticmethod
    def _generate_data_quality_section(data_quality: Dict[str, Any], sp_percentage: float) -> list:
        section = []
        if not data_quality['sp_analysis_reliable']:
            if data_quality['missing_frequency'] > 0:
                section.append("WARNING: Frequency data missing - S&P analysis unreliable")
                section.append(f"   Missing frequency in {data_quality['missing_frequency']} QSOs")
                section.append("   All QSOs classified as RUN mode due to lack of frequency data")
            elif data_quality['frequencies_estimated']:
                section.append("WARNING: Frequencies estimated from band data - S&P analysis may be unreliable")
                section.append(f"   {data_quality['estimated_frequencies']} frequencies estimated from band center")
        section.append(f"S&P Percentage: {sp_percentage:.1f}%")
        section.append("")
        section.append("DATA QUALITY:")
        section.append("-" * 40)
        section.append(f"Frequency Coverage: {data_quality['freq_coverage']:.1f}%")
        if data_quality['missing_frequency'] > 0:
            section.append(f"Missing Frequency: {data_quality['missing_frequency']} QSOs")
        if data_quality['estimated_frequencies'] > 0:
            section.append(f"Estimated Frequencies: {data_quality['estimated_frequencies']} QSOs")
        if data_quality['missing_band'] > 0:
            section.append(f"Missing Band: {data_quality['missing_band']} QSOs")
        if data_quality['missing_time'] > 0:
            section.append(f"Missing Time: {data_quality['missing_time']} QSOs")
        if data_quality['sp_analysis_reliable']:
            section.append("STATUS: S&P analysis reliable")
        else:
            section.append("STATUS: S&P analysis unreliable due to missing/estimated frequency data")
        section.append("")
        return section

    @staticmethod
    def _generate_log_statistics_section(log_stats: Dict[str, Any], qsos: List[Dict[str, Any]]) -> list:
        section = []
        def adif_date_to_iso(date_str):
            if date_str and len(date_str) == 8 and date_str.isdigit():
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            return date_str
        def get_qso_date(qso: Dict[str, Any]) -> str:
            for k in qso.keys():
                if k.lower() == 'qso_date':
                    return qso[k]
            return None
        def get_date_and_time_for_time(time: int, prefer_first: bool = False, prefer_last: bool = False):
            matches = [qso for qso in qsos if qso.get('time') == time and get_qso_date(qso)]
            if not matches:
                return (None, time)
            matches.sort(key=lambda q: (int(get_qso_date(q)), int(q['time']) if q.get('time') is not None else 0))
            if prefer_first:
                min_qso = matches[0]
                date = adif_date_to_iso(get_qso_date(min_qso))
                time_val = min_qso['time']
                return (date, time_val)
            if prefer_last:
                max_qso = matches[-1]
                date = adif_date_to_iso(get_qso_date(max_qso))
                time_val = max_qso['time']
                return (date, time_val)
            date = adif_date_to_iso(get_qso_date(matches[0]))
            return (date, matches[0]['time'])
        section.append("LOG STATISTICS:")
        section.append("-" * 40)
        section.append(f"Total Log Duration: {log_stats['total_hours']:.1f} hours")
        section.append(f"Overall QSO Rate: {log_stats['overall_rate']:.1f} QSOs/hour")
        if log_stats['gaps']:
            total_silent_minutes = sum(gap['duration_min'] for gap in log_stats['gaps'])
            total_silent_hours = total_silent_minutes / 60.0
            section.append(f"Full Log Silent Periods (>15 min): {len(log_stats['gaps'])} totaling {total_silent_hours:.1f} hours")
            for i, gap in enumerate(log_stats['gaps'], 1):
                start_date, start_time = get_date_and_time_for_time(gap['start'], prefer_first=True)
                end_date, end_time = get_date_and_time_for_time(gap['end'], prefer_last=True)
                section.append(f"  Gap {i}: {gap['duration_min']:.0f} minutes "
                              f"({QSOMetrics._format_time(start_time, start_date)} - {QSOMetrics._format_time(end_time, end_date)})")
        else:
            section.append("Silent Periods (>15 min): None")
        if 'time_accounting' in log_stats:
            time_acc = log_stats['time_accounting']
            section.append("")
            section.append("TIME BREAKDOWN:")
            section.append(f"  Total Log Duration: {time_acc['total_log_hours']:.1f} hours")
            qso_with_date_and_time = [
                (get_qso_date(qso), qso['time'])
                for qso in qsos
                if get_qso_date(qso) and qso.get('time') is not None
            ]
            if qso_with_date_and_time:
                qso_with_date_and_time.sort(key=lambda x: (int(x[0]), int(x[1])))
                first_date, first_time = qso_with_date_and_time[0]
                last_date, last_time = qso_with_date_and_time[-1]
                section.append(f"  First QSO: {QSOMetrics._format_time(int(first_time), adif_date_to_iso(first_date))}")
                section.append(f"  Last QSO: {QSOMetrics._format_time(int(last_time), adif_date_to_iso(last_date))}")
            section.append(f"  Active Operating Time: {time_acc['active_operating_hours']:.1f} hours")
            section.append(f"  Silent/Gap Time: {time_acc['all_gap_hours']:.1f} hours")
            section.append(f"    - Long gaps (>15 min): {time_acc['long_gap_hours']:.1f} hours")
            section.append(f"    - Short gaps (<15 min): {time_acc['short_gap_hours']:.1f} hours")
            total_check = time_acc['active_operating_hours'] + time_acc['all_gap_hours']
            section.append(f"  Reconciliation: {total_check:.1f} hours")
            if time_acc['reconciliation_check']:
                section.append("  STATUS: Time accounting reconciled")
            else:
                section.append(f"  WARNING: Time discrepancy: {time_acc['reconciliation_diff']:.1f} hours")
        section.append("")
        return section

    @staticmethod
    def _generate_band_mode_breakdown(qsos: List[Dict[str, Any]]) -> list:
        section = []
        band_mode_counts = {}
        band_set = set()
        mode_set = set()
        for qso in qsos:
            band = qso.get('band', 'UNKNOWN')
            mode = qso.get('mode', 'UNKNOWN')
            band_set.add(band)
            mode_set.add(mode)
            if band not in band_mode_counts:
                band_mode_counts[band] = {}
            band_mode_counts[band][mode] = band_mode_counts[band].get(mode, 0) + 1
        preferred_band_order = ['160M', '80M', '60M', '40M', '30M', '20M', '17M', '15M', '12M', '10M', '6M', '4M', '2M', '1.25M', '70CM']
        bands = [b for b in preferred_band_order if b in band_set]
        bands += sorted(b for b in band_set if b not in bands and b != 'UNKNOWN')
        if 'UNKNOWN' in band_set:
            bands.append('UNKNOWN')
        mode_display_map = {}
        for m in mode_set:
            m_upper = m.upper()
            if m_upper == 'CW':
                mode_display_map[m] = 'CW'
            elif m_upper in ['SSB', 'PHONE', 'FM', 'AM']:
                mode_display_map[m] = 'Phone'
            elif m_upper in ['FT8', 'FT4', 'PSK31', 'DIGITAL', 'DIG']:
                mode_display_map[m] = 'DIG'
            else:
                mode_display_map[m] = m
        display_modes = set(mode_display_map.values())
        modes = [m for m in ['CW', 'Phone', 'DIG'] if m in display_modes]
        modes += sorted(m for m in display_modes if m not in modes)
        band_mode_summary = {}
        for band in bands:
            band_mode_summary[band] = {}
            for mode in mode_set:
                display_mode = mode_display_map[mode]
                band_mode_summary[band][display_mode] = band_mode_summary[band].get(display_mode, 0) + band_mode_counts.get(band, {}).get(mode, 0)
        band_totals = {}
        mode_totals = {m: 0 for m in modes}
        grand_total = 0
        for band in bands:
            band_total = 0
            for mode in modes:
                count = band_mode_summary.get(band, {}).get(mode, 0)
                band_total += count
                mode_totals[mode] += count
            band_totals[band] = band_total
            grand_total += band_total
        section.append("")
        section.append("BAND/MODE BREAKDOWN:")
        section.append(" Band  |   CW  | Phone |  Dig  | Total |   %")
        section.append("-------|-------|-------|-------|-------|-----")
        for band in bands:
            cw = band_mode_summary[band].get('CW', 0)
            phone = band_mode_summary[band].get('Phone', 0)
            dig = band_mode_summary[band].get('DIG', 0)
            total = band_totals[band]
            pct = int(round((total / grand_total * 100))) if grand_total > 0 else 0
            line = f" {band:<5} | {cw:5d} | {phone:5d} | {dig:5d} | {total:5d} | {pct:3d}"
            section.append(line)
        section.append("-------|-------|-------|-------|-------|-----")
        total_row = f" Total | {mode_totals.get('CW', 0):5d} | {mode_totals.get('Phone', 0):5d} | {mode_totals.get('DIG', 0):5d} | {grand_total:5d} | 100"
        section.append(total_row)
        return section

    @staticmethod
    def _generate_section_table(qsos: List[Dict[str, Any]], total_qsos: int) -> list:
        arrl_sections = [
            'EMA', 'WMA', 'NH', 'VT', 'ME', 'RI', 'CT',
            'NNY', 'ENY', 'WNY', 'NLI',
            'SNJ', 'NNJ',
            'EPA', 'WPA',
            'DE', 'MD', 'DC', 'VA', 'WV',
            'NC', 'SC', 'GA', 'FL', 'PR', 'VI', 'AL', 'MS', 'TN', 'KY',
            'OH', 'MI', 'IN', 'WI',
            'IL', 'MO', 'AR', 'LA', 'OK', 'TX',
            'MN', 'IA', 'KS', 'NE', 'SD', 'ND',
            'CO', 'WY', 'MT', 'UT', 'ID',
            'AZ', 'NM',
            'OR', 'WA', 'EWA', 'WWA',
            'AK', 'NT',
            'MAR', 'NL', 'QC', 'ON', 'MB', 'SK', 'AB', 'BC', 'NU', 'YT', 'NWT', 'LB', 'PE', 'NS',
            'SB', 'SCV', 'SJV', 'LAX', 'ORG', 'SDG', 'SV', 'SF',
            'GTA', 'ONE', 'ONS'
        ]  # Official ARRL sections: 84
        assert len(arrl_sections) == 84, f"ARRL section list should have 84 entries, found {len(arrl_sections)}"

        section_counts: Dict[str, int] = {}
        for qso in qsos:
            sec = qso.get('section', 'UNKNOWN')
            if sec is None:
                sec = 'UNKNOWN'
            sec = str(sec).strip().upper()
            section_counts[sec] = section_counts.get(sec, 0) + 1
        # Always show all ARRL sections, even if not worked
        section_tuples = []
        for sec in arrl_sections:
            count = section_counts.get(sec, 0)
            pct = int(round((count / total_qsos * 100))) if total_qsos > 0 else 0
            section_tuples.append((sec, count, pct))
        # Sort by count descending, then section name ascending
        section_tuples_sorted = sorted(section_tuples, key=lambda x: (-x[1], x[0]))
        # Calculate worked_count independently
        worked_count = sum(1 for sec in arrl_sections if section_counts.get(sec, 0) > 0)
        lines = [""]
        lines.append("Total Contacts by Section (sorted):")
        lines += QSOMetrics._format_section_table_side_by_side(section_tuples_sorted)
        lines.append(f"Unique Sections Worked: {worked_count} of {len(arrl_sections)} ({(worked_count / len(arrl_sections) * 100):.1f}%)")
        return lines

    @staticmethod
    def _generate_country_table(qsos: List[Dict[str, Any]], total_qsos: int) -> list:
        section = []
        country_counts = {}
        for qso in qsos:
            country = qso.get('country', 'UNKNOWN')
            if country is None:
                country = 'UNKNOWN'
            country = str(country).strip().upper()
            country_counts[country] = country_counts.get(country, 0) + 1
        if '' in country_counts:
            country_counts['UNKNOWN'] = country_counts.get('UNKNOWN', 0) + country_counts['']
            del country_counts['']
        sorted_countries = sorted(country_counts.items(), key=lambda x: (-x[1], x[0]))
        section.append("")
        section.append("Total Contacts by Country:")
        section.append(" Country                        Total      %")
        section.append(" -------                        -----    ---")
        for country, count in sorted_countries:
            pct = int(round((count / total_qsos * 100))) if total_qsos > 0 else 0
            section.append(f" {country:<28} {count:7d} {pct:6d}")
        section.append(f" Total = {len(sorted_countries)}\n")
        return section

    @staticmethod
    def _generate_operator_statistics(operator_stats: Dict[str, Any], total_qsos: int) -> list:
        section = []
        section.append("")
        section.append("OPERATOR STATISTICS:")
        section.append("-" * 40)
        for operator, stats in sorted(operator_stats.items()):
            contribution_pct = (stats['qso_count'] / total_qsos) * 100 if total_qsos > 0 else 0
            section.append(f"Operator: {operator}")
            section.append(f"  QSO Count: {stats['qso_count']} ({contribution_pct:.1f}% of total)")
            section.append(f"  Average Rate: {stats['avg_rate_per_hour']:.1f} QSOs/hour")
            section.append(f"  Peak Rate: {stats['peak_rate_per_hour']:.0f} QSOs/hour")
            missing_count = stats.get('missing_freq_count', 0)
            qso_count = stats.get('qso_count', 0)
            if qso_count > 0:
                missing_pct = 100.0 * missing_count / qso_count
            else:
                missing_pct = 0.0
            if missing_count == 0:
                confidence = "(accurate - all QSOs have frequency data)"
            else:
                confidence = f"(unreliable - {missing_count} QSOs missing frequency, {missing_pct:.1f}% of QSOs)"
            section.append(f"  Run: {stats['run_percentage']:.1f}% | S&P: {stats['sp_percentage']:.1f}% {confidence}")
            section.append("")
        return section

