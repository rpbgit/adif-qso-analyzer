"""ADIF file parser for ham radio QSO data."""

import re
from typing import List, Dict, Optional, Any


class QSORecord:
    """Represents a single QSO record."""
    
    def __init__(self, freq: Optional[float] = None, band: Optional[str] = None, 
                 time_on: Optional[int] = None, operator: Optional[str] = None) -> None:
        """
        Initialize a QSO record.
        
        Args:
            freq: Frequency in MHz
            band: Amateur radio band
            time_on: Time in HHMMSS format
            operator: Call sign of the operator
        """
        self.freq = freq
        self.band = band
        self.time_on = time_on
        self.operator = operator
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert QSO record to dictionary."""
        return {
            'freq': self.freq,
            'band': self.band,
            'time': self.time_on,
            'operator': self.operator
        }


class ADIFParser:
    """Parser for ADIF (Amateur Data Interchange Format) files."""
    
    @staticmethod
    def parse_adi(filename: str) -> List[Dict[str, Any]]:
        """
        Parse an ADIF file and extract QSO records.
        
        Args:
            filename: Path to the ADIF file
            
        Returns:
            List of QSO dictionaries sorted by time
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        qsos = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                buffer = ''
                for line in f:
                    if '<eor>' in line.lower():
                        buffer += line
                        qso = ADIFParser._parse_qso_record(buffer)
                        if qso:
                            qsos.append(qso.to_dict())
                        buffer = ''
                    else:
                        buffer += line
        except FileNotFoundError:
            raise FileNotFoundError(f"ADIF file not found: {filename}")
        except IOError as e:
            raise IOError(f"Error reading ADIF file: {e}")
        
        # Filter out incomplete records and sort by time
        qsos = [q for q in qsos if q['freq'] is not None and q['band'] is not None]
        qsos = sorted(qsos, key=lambda x: x['time'] if x['time'] is not None else 0)
        
        return qsos
    
    @staticmethod
    def _parse_qso_record(buffer: str) -> Optional[QSORecord]:
        """
        Parse a single QSO record from ADIF buffer.
        
        Args:
            buffer: ADIF record buffer
            
        Returns:
            QSORecord object or None if parsing fails
        """
        # Extract frequency (MHz float)
        freq_match = re.search(r'<freq:(\d+)>([\d\.]+)', buffer, re.IGNORECASE)
        freq = float(freq_match.group(2)) if freq_match else None
        
        # Extract band (string)
        band_match = re.search(r'<band:(\d+)>([^<]+)', buffer, re.IGNORECASE)
        band = band_match.group(2) if band_match else None
        
        # Extract time_on (HHMMSS format)
        time_match = re.search(r'<time_on:(\d+)>(\d+)', buffer, re.IGNORECASE)
        time_on = int(time_match.group(2)) if time_match else None
        
        # Extract operator call sign
        operator_match = re.search(r'<operator:(\d+)>([^<]+)', buffer, re.IGNORECASE)
        operator = operator_match.group(2) if operator_match else None
        
        # If no operator field, try station_callsign
        if not operator:
            station_match = re.search(r'<station_callsign:(\d+)>([^<]+)', buffer, re.IGNORECASE)
            operator = station_match.group(2) if station_match else "UNKNOWN"
        
        return QSORecord(freq=freq, band=band, time_on=time_on, operator=operator)
