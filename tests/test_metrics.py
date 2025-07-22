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
