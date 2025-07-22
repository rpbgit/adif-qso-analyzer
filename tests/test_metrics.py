"""Tests for metrics analyzer functionality."""

import pytest
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from metrics_analyzer import QSOMetrics


class TestQSOMetrics:
    """Test QSO metrics calculations."""
    
    def test_calculate_sp_percentage_no_band_changes(self) -> None:
        """Test S&P calculation with no band changes."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 123000, 'operator': 'K1ABC'},
            {'freq': 14.201, 'band': '20M', 'time': 123100, 'operator': 'K1ABC'},
            {'freq': 14.202, 'band': '20M', 'time': 123200, 'operator': 'K1ABC'}
        ]
        result = QSOMetrics.calculate_sp_percentage(qsos)
        assert result == 100.0  # All frequency changes > 200 Hz
    
    def test_calculate_sp_percentage_mixed(self) -> None:
        """Test S&P calculation with mixed operations."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 123000, 'operator': 'K1ABC'},
            {'freq': 14.200, 'band': '20M', 'time': 123100, 'operator': 'K1ABC'},  # CQ
            {'freq': 14.205, 'band': '20M', 'time': 123200, 'operator': 'K1ABC'}   # S&P
        ]
        result = QSOMetrics.calculate_sp_percentage(qsos)
        assert result == 50.0
    
    def test_calculate_qso_rates_single_operator(self) -> None:
        """Test QSO rate calculation for single operator."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},
            {'freq': 14.201, 'band': '20M', 'time': 121500, 'operator': 'K1ABC'},
            {'freq': 14.202, 'band': '20M', 'time': 123000, 'operator': 'K1ABC'}
        ]
        result = QSOMetrics.calculate_qso_rates(qsos)
        
        assert 'K1ABC' in result
        assert result['K1ABC']['qso_count'] == 3
        assert result['K1ABC']['avg_rate_per_hour'] > 0
        assert 'run_percentage' in result['K1ABC']
        assert 'sp_percentage' in result['K1ABC']
    
    def test_calculate_operator_sp_percentages(self) -> None:
        """Test Run vs S&P percentage calculation per operator."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},
            {'freq': 14.200, 'band': '20M', 'time': 121000, 'operator': 'K1ABC'},  # Run
            {'freq': 14.205, 'band': '20M', 'time': 122000, 'operator': 'K1ABC'},  # S&P
            {'freq': 21.200, 'band': '15M', 'time': 123000, 'operator': 'K2DEF'},
            {'freq': 21.210, 'band': '15M', 'time': 124000, 'operator': 'K2DEF'}   # S&P
        ]
        result = QSOMetrics.calculate_qso_rates(qsos)
        
        # K1ABC should have 50% Run, 50% S&P (1 run, 1 s&p out of 2 transitions)
        assert result['K1ABC']['run_percentage'] == 50.0
        assert result['K1ABC']['sp_percentage'] == 50.0
        
        # K2DEF should have 0% Run, 100% S&P (1 s&p out of 1 transition)
        assert result['K2DEF']['run_percentage'] == 0.0
        assert result['K2DEF']['sp_percentage'] == 100.0
    
    def test_calculate_log_statistics(self) -> None:
        """Test overall log statistics calculation."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},  # 12:00
            {'freq': 14.201, 'band': '20M', 'time': 120500, 'operator': 'K1ABC'},  # 12:05
            {'freq': 14.202, 'band': '20M', 'time': 122000, 'operator': 'K1ABC'},  # 12:20 (15 min gap)
            {'freq': 14.203, 'band': '20M', 'time': 140000, 'operator': 'K1ABC'}   # 14:00 (100 min gap)
        ]
        
        log_stats = QSOMetrics._calculate_log_statistics(qsos)
        
        assert log_stats['total_hours'] == 2.0  # 12:00 to 14:00 = 2 hours
        assert log_stats['overall_rate'] == 2.0  # 4 QSOs / 2 hours
        assert len(log_stats['gaps']) == 1  # Only one gap > 15 minutes (100 min gap)
        assert log_stats['gaps'][0]['duration_min'] == 100
    
    def test_find_silent_periods(self) -> None:
        """Test silent period detection."""
        times = [120000, 120500, 122000, 140000]  # 12:00, 12:05, 12:20, 14:00
        
        gaps = QSOMetrics._find_silent_periods(times, min_gap_minutes=15)
        
        assert len(gaps) == 1  # Only the 100-minute gap should be detected
        assert gaps[0]['start'] == 122000
        assert gaps[0]['end'] == 140000
        assert gaps[0]['duration_min'] == 100
    
    def test_format_time(self) -> None:
        """Test time formatting utility."""
        assert QSOMetrics._format_time(123456) == "12:34"
        assert QSOMetrics._format_time(0) == "00:00"
        assert QSOMetrics._format_time(235959) == "23:59"
    
    def test_time_to_minutes_conversion(self) -> None:
        """Test time conversion utility."""
        assert QSOMetrics._time_to_minutes(123456) == 12 * 60 + 34
        assert QSOMetrics._time_to_minutes(235959) == 23 * 60 + 59
        assert QSOMetrics._time_to_minutes(0) == 0
    
    def test_generate_summary_report(self) -> None:
        """Test summary report generation."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},
            {'freq': 14.205, 'band': '20M', 'time': 121500, 'operator': 'K2DEF'}
        ]
        report = QSOMetrics.generate_summary_report(qsos)
        
        assert "QSO ANALYSIS SUMMARY REPORT" in report
        assert "Total QSOs: 2" in report
        assert "K1ABC" in report
        assert "K2DEF" in report
        assert "Run:" in report
        assert "S&P:" in report
        assert "% of total)" in report  # Check for contribution percentage
    
    def test_calculate_hourly_rates(self) -> None:
        """Test hourly QSO rate calculation."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},  # 12:00
            {'freq': 14.201, 'band': '20M', 'time': 121500, 'operator': 'K1ABC'},  # 12:15
            {'freq': 14.202, 'band': '20M', 'time': 130000, 'operator': 'K2DEF'},  # 13:00
            {'freq': 14.203, 'band': '20M', 'time': 130500, 'operator': 'K2DEF'}   # 13:05
        ]
        result = QSOMetrics._calculate_hourly_rates(qsos)
        
        # Should have 2 hours with data
        assert len(result) == 2
        
        # Hour 12 should have 2 QSOs
        hour_12 = next((h for h in result if h['hour'] == 12), None)
        assert hour_12 is not None
        assert hour_12['qso_count'] == 2
        
        # Hour 13 should have 2 QSOs
        hour_13 = next((h for h in result if h['hour'] == 13), None)
        assert hour_13 is not None
        assert hour_13['qso_count'] == 2
    
    def test_calculate_operator_sessions(self) -> None:
        """Test operator session calculation."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},  # 12:00
            {'freq': 14.201, 'band': '20M', 'time': 120500, 'operator': 'K1ABC'},  # 12:05
            {'freq': 14.202, 'band': '20M', 'time': 130000, 'operator': 'K2DEF'},  # 13:00 (different op)
            {'freq': 14.203, 'band': '20M', 'time': 140000, 'operator': 'K1ABC'},  # 14:00 (K1ABC returns after gap)
        ]
        result = QSOMetrics._calculate_operator_sessions(qsos)
        
        # Should have both operators
        assert 'K1ABC' in result
        assert 'K2DEF' in result
        
        # K1ABC should have 2 sessions due to the gap
        assert result['K1ABC']['session_count'] == 2
        assert result['K1ABC']['first_qso'] == 120000
        assert result['K1ABC']['last_qso'] == 140000
        
        # K2DEF should have 1 session
        assert result['K2DEF']['session_count'] == 1
        assert result['K2DEF']['first_qso'] == 130000
        assert result['K2DEF']['last_qso'] == 130000
    
    def test_calculate_accurate_time_accounting(self) -> None:
        """Test accurate time accounting with reconciliation."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},  # 12:00
            {'freq': 14.201, 'band': '20M', 'time': 120500, 'operator': 'K1ABC'},  # 12:05
            {'freq': 14.202, 'band': '20M', 'time': 130000, 'operator': 'K2DEF'},  # 13:00 (55 min gap)
            {'freq': 14.203, 'band': '20M', 'time': 131000, 'operator': 'K2DEF'},  # 13:10
        ]
        result = QSOMetrics._calculate_accurate_time_accounting(qsos)
        
        # Should have proper time breakdown
        assert 'total_log_hours' in result
        assert 'active_operating_hours' in result
        assert 'all_gap_hours' in result
        assert 'long_gap_hours' in result
        assert 'short_gap_hours' in result
        assert 'reconciliation_check' in result
        
        # Time accounting should reconcile
        total = result['active_operating_hours'] + result['all_gap_hours']
        assert abs(total - result['total_log_hours']) < 0.1
        assert result['reconciliation_check'] is True
        
        # Gap of 55 minutes should be counted as long gap
        assert result['long_gap_hours'] > 0
    
    def test_time_accounting_with_no_gaps(self) -> None:
        """Test time accounting with continuous operation."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},  # 12:00
            {'freq': 14.201, 'band': '20M', 'time': 120100, 'operator': 'K1ABC'},  # 12:01
            {'freq': 14.202, 'band': '20M', 'time': 120200, 'operator': 'K1ABC'},  # 12:02
        ]
        result = QSOMetrics._calculate_accurate_time_accounting(qsos)
        
        # Should have minimal gap time for continuous operation
        assert result['long_gap_hours'] == 0.0
        assert result['short_gap_hours'] >= 0.0  # May have small gaps between QSOs
        assert result['reconciliation_check'] is True
    
    def test_time_accounting_empty_data(self) -> None:
        """Test time accounting with empty data."""
        result = QSOMetrics._calculate_accurate_time_accounting([])
        
        assert result['total_log_hours'] == 0.0
        assert result['active_operating_hours'] == 0.0
        assert result['all_gap_hours'] == 0.0
        assert result['reconciliation_check'] is True
    
    def test_log_statistics_includes_time_accounting(self) -> None:
        """Test that log statistics includes time accounting data."""
        qsos = [
            {'freq': 14.200, 'band': '20M', 'time': 120000, 'operator': 'K1ABC'},
            {'freq': 14.201, 'band': '20M', 'time': 130000, 'operator': 'K2DEF'},  # 1 hour gap
        ]
        result = QSOMetrics._calculate_log_statistics(qsos)
        
        assert 'time_accounting' in result
        assert 'total_log_hours' in result['time_accounting']
        assert 'active_operating_hours' in result['time_accounting']
        assert 'reconciliation_check' in result['time_accounting']
