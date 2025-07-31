
"""Tests for ADIF parser functionality."""

import pytest
import tempfile
import os
from pathlib import Path
import sys
from adif_parser import ADIFParser, QSORecord

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestQSORecord:
    """Test QSORecord class."""
    
    def test_qso_record_creation(self) -> None:
        """Test QSO record creation."""
        qso = QSORecord(freq=14.205, band="20M", time_on=123456, operator="K1ABC")
        assert qso.freq == 14.205
        assert qso.band == "20M"
        assert qso.time_on == 123456
        assert qso.operator == "K1ABC"
    
    def test_qso_record_to_dict(self) -> None:
        """Test QSO record dictionary conversion."""
        qso = QSORecord(freq=14.205, band="20M", time_on=123456, operator="K1ABC")
        result = qso.to_dict()
        expected = {
            'freq': 14.205,
            'band': "20M", 
            'time': 123456,
            'operator': "K1ABC"
        }
        assert result == expected


class TestADIFParser:
    """Test ADIF parser functionality."""
    
    def test_parse_valid_adif(self) -> None:
        """Test parsing valid ADIF content."""
        adif_content = """
<FREQ:6>14.205<BAND:3>20M<TIME_ON:6>123456<OPERATOR:5>K1ABC<EOR>
<FREQ:6>21.300<BAND:3>15M<TIME_ON:6>124500<OPERATOR:5>K2DEF<EOR>
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.adi') as f:
            f.write(adif_content)
            temp_file = f.name
        
        try:
            qsos = ADIFParser.parse_adi(temp_file)
            assert len(qsos) == 2
            assert qsos[0]['freq'] == 14.205
            assert qsos[0]['band'] == "20M"
            assert qsos[0]['operator'] == "K1ABC"
        finally:
            os.unlink(temp_file)
    
    def test_file_not_found(self) -> None:
        """Test file not found error."""
        with pytest.raises(FileNotFoundError):
            ADIFParser.parse_adi("nonexistent_file.adi")
    
    def test_parse_empty_file(self) -> None:
        """Test parsing empty ADIF file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.adi') as f:
            f.write("")
            temp_file = f.name
        
        try:
            qsos = ADIFParser.parse_adi(temp_file)
            assert len(qsos) == 0
        finally:
            os.unlink(temp_file)
