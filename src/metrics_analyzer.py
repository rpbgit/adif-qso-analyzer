
"""QSO metrics analyzer for contest statistics."""

from typing import List, Dict, Any
from collections import defaultdict


class QSOMetrics:
    @staticmethod
    def _generate_data_quality_section(data_quality: Dict[str, Any], sp_percentage: float) -> list:
        """
        Generate a section of the report summarizing data quality metrics.
        Args:
            data_quality: Dictionary with data quality metrics
            sp_percentage: Overall Search & Pounce percentage
        Returns:
            List of strings for the report section
        """
        section = []
        section.append("")
        section.append("DATA QUALITY ANALYSIS:")
        section.append("-" * 40)
        total_qsos = data_quality.get('total_qsos', 0)
        missing_freq = data_quality.get('missing_frequency', 0)
        missing_band = data_quality.get('missing_band', 0)
        missing_time = data_quality.get('missing_time', 0)
        freq_coverage = data_quality.get('freq_coverage', 0.0)
        estimated_freqs = data_quality.get('estimated_frequencies', 0)
        sp_reliable = data_quality.get('sp_analysis_reliable', False)
        freqs_estimated = data_quality.get('frequencies_estimated', False)
        section.append(f"QSOs analyzed: {total_qsos}")
        section.append(f"QSOs missing frequency: {missing_freq}")
        section.append(f"QSOs missing band: {missing_band}")
        section.append(f"QSOs missing time: {missing_time}")
        section.append(f"Frequency coverage: {freq_coverage:.1f}% of QSOs have frequency data")
        section.append(f"QSOs with estimated (band center) frequencies: {estimated_freqs}")
        section.append(f"Search & Pounce (S&P) percentage: {sp_percentage:.1f}%")
        if not sp_reliable:
            section.append("WARNING: S&P analysis may be unreliable due to missing or estimated frequency data.")
        elif freqs_estimated:
            section.append("NOTE: Many frequencies are estimated from band center; S&P analysis may be less accurate.")
        else:
            section.append("S&P analysis is considered reliable.")
        section.append("")
        return section
    @staticmethod
    def calculate_sp_percentage(qsos: List[Dict[str, Any]]) -> float:
        """
        Calculate the Search & Pounce (S&P) percentage for the log.
        S&P is estimated by counting frequency jumps > 200 Hz between consecutive QSOs on the same band.
        Returns the S&P percentage as a float (0-100).
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
                if qso.get('BAND') == prev.get('BAND'):
                    # Get frequencies, estimating from band if missing
                    current_freq = qso.get('FREQ')
                    if (current_freq == '' or current_freq is None) and qso.get('BAND'):
                        current_freq = band_freq_map.get(qso.get('BAND', '').upper().strip(), 14.200)
                    prev_freq = prev.get('FREQ')
                    if (prev_freq == '' or prev_freq is None) and prev.get('BAND'):
                        prev_freq = band_freq_map.get(prev.get('BAND', '').upper().strip(), 14.200)
                    # Convert frequency values to float if possible
                    try:
                        if current_freq is not None:
                            current_freq = float(current_freq)
                        if prev_freq is not None:
                            prev_freq = float(prev_freq)
                    except (ValueError, TypeError):
                        current_freq = None
                        prev_freq = None
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
            computer = qso.get('STATION', 'UNKNOWN')  # Use 'station' as computer name
            if qso.get('TIME_ON') is not None:
                qsos_by_computer[computer].append(qso)
        for computer, comp_qsos in qsos_by_computer.items():
            times = sorted(qso['TIME_ON'] for qso in comp_qsos if qso.get('TIME_ON') is not None)
            computer_gaps[computer] = QSOMetrics._find_silent_periods(times, min_gap_minutes)
        return computer_gaps

    @staticmethod
    def _generate_computer_gap_section(qsos: List[Dict[str, Any]], min_gap_minutes: int = 15) -> list:
        """
        Generate a report section listing silent periods for each computer.
        """
        section = []
        computer_gaps = QSOMetrics._find_silent_periods_by_computer(qsos, min_gap_minutes)
        if not computer_gaps or all(len(gaps) == 0 for gaps in computer_gaps.values()):
            section.append("")
            section.append("SILENT PERIODS BY COMPUTER: None detected (no gaps > {} min)".format(min_gap_minutes))
            return section

        section.append("")
        section.append(f"SILENT PERIODS BY COMPUTER (>{min_gap_minutes} min):")
        section.append("-" * 40)
        for computer, gaps in sorted(computer_gaps.items()):
            if not gaps:
                continue
            section.append(f"Computer/Station: {computer}")
            for i, gap in enumerate(gaps, 1):
                start = QSOMetrics._format_time(gap['start'])
                end = QSOMetrics._format_time(gap['end'])
                duration = gap['duration_min']
                section.append(f"  Gap {i}: {duration:.0f} minutes ({start} - {end})")
            section.append("")
        return section
    
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
            operator = qso.get('OPERATOR', 'UNKNOWN')
            # Only use 'TIME_ON' (uppercase) as the canonical time field
            if 'TIME_ON' not in qso or qso['TIME_ON'] is None:
                raise ValueError(f"QSO record is missing required 'TIME_ON' field: {qso}")
            operator_stats[operator]['qso_count'] += 1
            operator_stats[operator]['times'].append(qso['TIME_ON'])
            # Track missing frequency data per operator (treat None or '' as missing)
            freq_val = qso.get('FREQ')
            if freq_val is None or freq_val == '':
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
            operator = qso.get('OPERATOR', 'UNKNOWN')
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

            # Sort operator's QSOs by canonical time field
            sorted_qsos = sorted(op_qsos, key=lambda x: x.get('TIME_ON') if x.get('TIME_ON') is not None else 0)

            for qso in sorted_qsos:
                if prev is not None:
                    # Check if same band
                    if qso.get('BAND') == prev.get('BAND'):
                        # Get frequencies, estimating from band if missing
                        band_freq_map = {
                            '160M': 1.900, '80M': 3.750, '60M': 5.330, '40M': 7.100, '30M': 10.125,
                            '20M': 14.200, '17M': 18.100, '15M': 21.200, '12M': 24.900, '10M': 28.400,
                            '6M': 50.100, '4M': 70.200, '2M': 144.200, '1.25M': 222.100, '70CM': 432.100
                        }

                        current_freq = qso.get('FREQ')
                        if current_freq == '' and qso.get('BAND'):
                            current_freq = band_freq_map.get(qso.get('BAND', '').upper().strip(), 14.200)

                        prev_freq = prev.get('FREQ')
                        if prev_freq == '' and prev.get('BAND'):
                            prev_freq = band_freq_map.get(prev.get('BAND', '').upper().strip(), 14.200)

                        # Only calculate if we have frequency data (actual or estimated)
                        try:
                            if current_freq is not None:
                                current_freq = float(current_freq)
                            if prev_freq is not None:
                                prev_freq = float(prev_freq)
                        except (ValueError, TypeError):
                            current_freq = None
                            prev_freq = None
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
        times = [qso['TIME_ON'] for qso in qsos if qso.get('TIME_ON') is not None]
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
        times = [qso['TIME_ON'] for qso in qsos if qso.get('TIME_ON') is not None]
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
            time_on = qso.get('TIME_ON')
            if time_on is not None:
                # Ensure time_on is int for formatting
                try:
                    time_on_int = int(time_on)
                except Exception:
                    continue
                time_str = f"{time_on_int:06d}"
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
        
        # Sort QSOs by canonical time field
        sorted_qsos = sorted([qso for qso in qsos if qso.get('TIME_ON') is not None], 
                           key=lambda x: x['TIME_ON'])
        
        if not sorted_qsos:
            return {}
        
        # Group QSOs by operator + station combination
        operator_station_qsos = defaultdict(list)
        for qso in sorted_qsos:
            operator = qso.get('OPERATOR', 'UNKNOWN')
            if operator is None:
                operator = 'UNKNOWN'
            operator = str(operator).strip().upper()
            station = qso.get('STATION', 'HAL 9000')
            # Create unique key for operator@station
            operator_station_key = f"{operator}@{station}"
            operator_station_qsos[operator_station_key].append(qso)
        
        operator_sessions = {}
        
        # Process each operator@station combination separately
        for operator_station_key, qsos_list in operator_station_qsos.items():
            # Extract operator and station from the key
            operator, station = operator_station_key.split('@', 1)
            
            # Sort this operator@station's QSOs by canonical time field
            qsos_list.sort(key=lambda x: x['TIME_ON'])
            
            operator_sessions[operator_station_key] = {
                'operator': operator,  # already uppercased above
                'station': station,
                'sessions': [],
                'total_minutes': 0,
                'first_qso': qsos_list[0]['TIME_ON'],
                'last_qso': qsos_list[-1]['TIME_ON'],
                'session_count': 0
            }
            
            # Process sessions for this operator@station using 15-minute gap rule
            current_session_start = qsos_list[0]['TIME_ON']
            current_session_end = qsos_list[0]['TIME_ON']
            
            for i in range(1, len(qsos_list)):
                current_qso = qsos_list[i]
                prev_qso = qsos_list[i-1]
                # Calculate gap between consecutive QSOs for this operator@station
                gap_minutes = QSOMetrics._calculate_time_gap_minutes(
                    prev_qso['TIME_ON'], current_qso['TIME_ON'])

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
                    current_session_start = current_qso['TIME_ON']
                    current_session_end = current_qso['TIME_ON']
                else:
                    # Continue current session
                    current_session_end = current_qso['TIME_ON']
            
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
        try:
            time_int = int(time_hhmmss)
        except Exception:
            return str(time_hhmmss) if not date else f"{date} {str(time_hhmmss)}"
        time_str = f"{time_int:06d}"
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
        # Accept both string and int for HHMMSS, always convert to string then int
        time_str = str(time_hhmmss).zfill(6)
        try:
            hours = int(time_str[:2])
            minutes = int(time_str[2:4])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid HHMMSS time value: {time_hhmmss}")
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
        missing_band = sum(1 for qso in qsos if qso.get('BAND') is None)
        missing_time = sum(1 for qso in qsos if qso.get('TIME_ON') is None)

        band_freq_map = {
            '160M': 1.900, '80M': 3.750, '60M': 5.330, '40M': 7.100, '30M': 10.125,
            '20M': 14.200, '17M': 18.100, '15M': 21.200, '12M': 24.900, '10M': 28.400,
            '6M': 50.100, '4M': 70.200, '2M': 144.200, '1.25M': 222.100, '70CM': 432.100
        }

        missing_freq = 0
        estimated_freq_count = 0
        freq_coverage_count = 0
        for qso in qsos:
            freq = qso.get('FREQ')
            band = qso.get('BAND', '').upper().strip()
            is_missing = freq in (None, '')
            # If missing, estimate for estimated count, but do not count for coverage
            if is_missing:
                missing_freq += 1
                if band in band_freq_map:
                    freq_est = band_freq_map[band]
                    estimated_freq_count += 1
                continue
            try:
                freq_val = float(freq)
            except (ValueError, TypeError):
                missing_freq += 1
                continue
            # If freq matches band center, count as estimated
            if band in band_freq_map and abs(freq_val - band_freq_map[band]) < 0.001:
                estimated_freq_count += 1
            else:
                freq_coverage_count += 1

        freq_coverage = (freq_coverage_count / total_qsos * 100) if total_qsos > 0 else 0
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

        # Calculate duplicate contacts (same callsign on same band/mode)
        from collections import defaultdict
        dupe_times: dict = defaultdict(list)
        for qso in qsos:
            call = str(qso.get('CALL', '')).strip().upper()
            band = str(qso.get('BAND', '')).strip().upper()
            mode = str(qso.get('MODE', '')).strip().upper()
            key = (call, band, mode)
            time_on = qso.get('TIME_ON')
            dupe_times[key].append(time_on)

        # Only consider as dupe if more than one QSO for (call, band, mode)
        dupe_list = [key for key, times in dupe_times.items() if len(times) > 1]

        report = []
        report.append("=" * 60)
        report.append("QSO ANALYSIS SUMMARY REPORT")
        report.append("=" * 60)
        report.append(f"Total QSOs: {total_qsos}")

        if dupe_list:
            report.append("")
            report.append("Duplicate contact list (CALLSIGN on BAND/MODE):")
            for call, band, mode in sorted(dupe_list):
                times = dupe_times[(call, band, mode)]
                # Format times as HHMMSS, sorted
                times_fmt = ', '.join(str(t).zfill(6) for t in sorted(times) if t is not None)
                report.append(f"  {call} on {band} {mode} at times: {times_fmt}")
        report.append(f"Duplicate contacts (same callsign on same band/mode): {len(dupe_list)}")

        # --- New Stat: Calls worked on multiple modes per band (corrected logic) ---
        # Build: call -> band -> set(modes)
        all_calls_in_log = set()
        call_band_modes = defaultdict(lambda: defaultdict(set))
        for qso in qsos:
            call = str(qso.get('CALL', '')).strip().upper()
            band = str(qso.get('BAND', '')).strip().upper()
            mode = str(qso.get('MODE', '')).strip().upper()
            # Assert that no callsign is 'UNKNOWN' or 'NONE'
            assert call not in {'UNKNOWN', 'NONE'}, f"Invalid callsign found in log: {qso}"
            if call:
                all_calls_in_log.add(call)
            if call and band and mode:
                call_band_modes[call][band].add(mode)


        # For each call, if it was worked on multiple modes on any band, count it once
        band_multi_mode_counts = defaultdict(int)
        band_total_calls = defaultdict(int)
        calls_multi_mode_any_band = set()
        all_unique_calls = set(call_band_modes.keys())
        for call, band_modes in call_band_modes.items():
            multi_mode_this_call = False
            for band, modes in band_modes.items():
                band_total_calls[band] += 1
                if len(modes) > 1:
                    band_multi_mode_counts[band] += 1
                    multi_mode_this_call = True
            if multi_mode_this_call:
                calls_multi_mode_any_band.add(call)

        total_unique = len(all_calls_in_log)
        total_multi_mode = len(calls_multi_mode_any_band)
        pct_total_multi = (100.0 * total_multi_mode / total_unique) if total_unique > 0 else 0.0

        # --- New Stat: Number of unique callsigns in the entire log ---
        report.append("")
        report.append(f"Number of unique callsigns in the entire log: {total_unique}")

        report.append("")
        report.append("Calls worked on multiple modes per band:")
        for band in sorted(band_total_calls.keys()):
            count_multi = band_multi_mode_counts[band]
            count_total = band_total_calls[band]
            pct = (100.0 * count_multi / count_total) if count_total > 0 else 0.0
            report.append(f"  {band}: {count_multi} of {count_total} calls ({pct:.1f}%)")
        report.append(f"Total calls worked on multiple modes (any band): {total_multi_mode} of {total_unique} unique calls ({pct_total_multi:.1f}%)")

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
    # (method removed, logic restored to generate_summary_report)
    @staticmethod
    def _generate_operator_table(qsos: List[Dict[str, Any]], total_qsos: int) -> list:
        section = []
        operator_counts = {}
        for qso in qsos:
            operator = qso.get('OPERATOR', 'Mr. Nobody')
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
            # Use uppercase for operator to match _generate_operator_table
            operator = session_data.get('operator', 'UNKNOWN')
            if operator is None:
                operator = 'UNKNOWN'
            operator = str(operator).strip().upper()
            station = session_data['station']
            total_hours = session_data['total_minutes'] / 60.0
            total_qsos_for_station = sum(
                1 for qso in qsos
                if str(qso.get('OPERATOR', 'UNKNOWN')).strip().upper() == operator and qso.get('STATION', 'HAL 9000') == station
            )
            section.append(f"Operator: {operator} @ Station: {station}")
            section.append(f"  Operating Time: {total_hours:.1f} hours ({session_data['session_count']} sessions, {total_qsos_for_station} QSOs)")
            section.append(f"  First QSO: {QSOMetrics._format_time(session_data['first_qso'])}")
            section.append(f"  Last QSO: {QSOMetrics._format_time(session_data['last_qso'])}")
            if session_data['sessions']:
                section.append("  Sessions:")
                for i, session in enumerate(session_data['sessions'], 1):
                    duration_hours = session['duration_minutes'] / 60.0
                    session_qso_count = sum(
                        1 for qso in qsos
                        if str(qso.get('OPERATOR', 'UNKNOWN')).strip().upper() == operator
                        and qso.get('STATION', 'HAL 9000') == station
                        and session['start_time'] <= qso.get('TIME_ON', -1) <= session['end_time']
                    )
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
    def _generate_log_statistics_section(log_stats: Dict[str, Any], qsos: List[Dict[str, Any]]) -> list:
        """
        Generate the log statistics section for the report.
        """
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
            matches = [qso for qso in qsos if qso.get('TIME_ON') == time and get_qso_date(qso)]
            if not matches:
                return (None, time)
            matches.sort(key=lambda q: (int(get_qso_date(q)), int(q['TIME_ON']) if q.get('TIME_ON') is not None else 0))
            if prefer_first:
                min_qso = matches[0]
                date = adif_date_to_iso(get_qso_date(min_qso))
                time_val = min_qso['TIME_ON']
                return (date, time_val)
            if prefer_last:
                max_qso = matches[-1]
                date = adif_date_to_iso(get_qso_date(max_qso))
                time_val = max_qso['TIME_ON']
                return (date, time_val)
            date = adif_date_to_iso(get_qso_date(matches[0]))
            return (date, matches[0]['TIME_ON'])

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
                (get_qso_date(qso), qso['TIME_ON'])
                for qso in qsos
                if get_qso_date(qso) and qso.get('TIME_ON') is not None
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
            band = qso.get('BAND', 'UNKNOWN')
            mode = qso.get('MODE', 'UNKNOWN')
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
        section.append(" Band  |   CW  |  SSB  |  Dig  | Total |  %")
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
        # User-provided ARRL section abbreviations list (count: 63)
      
        arrl_sections = [
            # Area 0: Central and Northern Plains States
            "CO", "IA", "KS", "MN", "MO", "ND", "NE", "SD",
            # Area 1: New England and Eastern Massachusetts
            "CT", "EMA", "ME", "NH", "RI", "VT", "WMA",
            # Area 2: New York and Northern New Jersey
            "ENY", "NLI", "NNJ", "NNY", "SNJ", "WNY",
            # Area 3: Delaware, Eastern & Western Pennsylvania, Maryland, DC
            "DE", "EPA", "MDC", "WPA",
            # Area 4: Southeast US including Puerto Rico and U.S. Virgin Islands
            "AL", "GA", "KY", "NC", "NFL", "PR", "SC", "SFL", "TN", "VA", "VI", "WCF",
            # Area 5: South Central US (Arkansas, Louisiana, Mississippi, New Mexico, Texas sections)
            "AR", "LA", "MS", "NM", "NTX", "OK", "STX", "WTX",
            # Area 6: California and Pacific sections
            "EB", "LAX", "ORG", "PAC", "SB", "SCV", "SDG", "SF", "SJV", "SV",
            # Area 7: Northwestern US including Alaska, Arizona, Hawaii, Washington, Oregon, Idaho, Montana, Wyoming, Utah, Nevada
            "AK", "AZ", "EWA", "HI", "ID", "MT", "NV", "OR", "UT", "WWA", "WY",
            # Area 8: Michigan, Ohio, West Virginia
            "MI", "OH", "WV",
            # Area 9: Illinois, Indiana, Wisconsin
            "IL", "IN", "WI",
            # Canada: Canadian RAC Sections and Territories
            "AB", "BC", "GH", "MB", "NB", "NL", "NS", "ONE", "ONN", "ONS", "PE", "QC", "SK", "TER",
            # any DX non ARRL section
            "DX"
        ]
        assert len(arrl_sections) == 87, f"ARRL section list should have 87 entries, found {len(arrl_sections)}"

        section_counts: Dict[str, int] = {}
        unmatched_sections = set()
        unmatched_qsos = []
        for qso in qsos:
            sec = qso.get('ARRL_SECT', 'UNKNOWN')
            if sec is None:
                sec = 'UNKNOWN'
            sec = str(sec).strip().upper()
            section_counts[sec] = section_counts.get(sec, 0) + 1
            if sec not in arrl_sections:
                unmatched_sections.add(sec)
                unmatched_qsos.append(qso)
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
        if unmatched_sections:
            lines.append("")
            lines.append("WARNING: The following ARRL_SECT values in the log do not match the official ARRL section list:")
            for sec in sorted(unmatched_sections):
                lines.append(f"  Unmatched section: '{sec}'")
            # Print details for each unmatched QSO
            for qso in unmatched_qsos:
                call = qso.get('CALL', 'UNKNOWN')
                sec = qso.get('ARRL_SECT', 'UNKNOWN')
                band = qso.get('BAND', 'UNKNOWN')
                mode = qso.get('MODE', 'UNKNOWN')
                time_on = qso.get('TIME_ON', 'UNKNOWN')
                operator = qso.get('OPERATOR', 'UNKNOWN')
                computer = qso.get('N3FJP_COMPUTERNAME', 'UNKNOWN')
                lines.append(
                    f"    QSO: CALL={call}, ARRL_SECT={sec}, BAND={band}, MODE={mode}, TIME_ON={time_on}, OPERATOR={operator}, COMPUTER={computer}"
                )
        else:
            lines.append("")
            lines.append("All ARRL_SECT values in the log match the official ARRL section list.")
        return lines

    @staticmethod
    def _generate_country_table(qsos: List[Dict[str, Any]], total_qsos: int) -> list:
        section = []
        country_counts = {}
        for qso in qsos:
            country = qso.get('COUNTRY', 'Elbonia')
            if country is None:
                country = 'Elbonia'
            country = str(country).strip().upper()
            country_counts[country] = country_counts.get(country, 0) + 1
        if '' in country_counts:
            country_counts['Elbonia'] = country_counts.get('Elbonia', 0) + country_counts['']
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
            # If all QSOs are missing frequency, mark as unreliable
            if missing_count == 0:
                confidence = "(accurate - all QSOs have frequency data)"
            elif missing_count == qso_count:
                confidence = "(unreliable - all QSOs missing frequency data)"
            else:
                confidence = f"(unreliable - {missing_count} QSOs missing frequency, {missing_pct:.1f}% of QSOs)"
            section.append(f"  Run: {stats['run_percentage']:.1f}% | S&P: {stats['sp_percentage']:.1f}% {confidence}")
            section.append("")
        # Add total number of unique operators
        total_operators = len(operator_stats)
        section.append(f"Total number of operators: {total_operators}")
        return section

