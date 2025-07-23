"""ADIF file parser for ham radio QSO data."""

import re
from typing import List, Dict, Optional, Any
from pathlib import Path


class QSORecord:
    """Represents a single QSO record."""
    
    def __init__(self, freq: Optional[float] = None, band: Optional[str] = None, 
                 time_on: Optional[int] = None, operator: Optional[str] = None,
                 call: Optional[str] = None, station: Optional[str] = None) -> None:
        """
        Initialize a QSO record.
        
        Args:
            freq: Frequency in MHz
            band: Amateur radio band
            time_on: Time in HHMMSS format
            operator: Call sign of the operator
            call: Call sign of the contacted station
            station: Station/computer name where QSO was logged
        """
        self.freq = freq
        self.band = band
        self.time_on = time_on
        self.operator = operator
        self.call = call
        self.station = station
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert QSO record to dictionary."""
        return {
            'freq': self.freq,
            'band': self.band,
            'time': self.time_on,
            'operator': self.operator,
            'call': self.call,
            'station': self.station
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
            # Try different encodings to handle various ADIF file formats
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(filename, 'r', encoding=encoding) as f:
                        content = f.read()
                    print(f"Successfully read file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise IOError("Could not read file with any supported encoding")
            
            # Split content by <eor> tags (end of record)
            records = re.split(r'<eor>', content, flags=re.IGNORECASE)
            
            for record in records:
                if record.strip():
                    qso = ADIFParser._parse_qso_record(record)
                    if qso:
                        qsos.append(qso.to_dict())
                        
        except FileNotFoundError:
            raise FileNotFoundError(f"ADIF file not found: {filename}")
        except IOError as e:
            raise IOError(f"Error reading ADIF file: {e}")
        
        # Filter out incomplete records and sort by time
        qsos = [q for q in qsos if q['freq'] is not None or q['band'] is not None]
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
        
        # If no frequency but we have band, estimate frequency from band
        if freq is None and band is not None:
            freq = ADIFParser._estimate_frequency_from_band(band)
        
        # Extract time_on (HHMMSS format)
        time_match = re.search(r'<time_on:(\d+)>(\d+)', buffer, re.IGNORECASE)
        time_on = int(time_match.group(2)) if time_match else None
        
        # Extract operator call sign
        operator_match = re.search(r'<operator:(\d+)>([^<]+)', buffer, re.IGNORECASE)
        operator = operator_match.group(2).strip() if operator_match else None
        
        # Use "Mr. Nobody" if operator is None or empty
        if not operator or operator == "":
            operator = "Mr. Nobody"
        
        # Extract station/computer name - try multiple field names
        station = None
        station_patterns = [
            r'<n3fjp_computername:(\d+)>([^<]+)',     # N3FJP logging software
            r'<app_n1mm_netbiosname:(\d+)>([^<]+)',   # N1MM+ logging software
        ]
        
        for pattern in station_patterns:
            station_match = re.search(pattern, buffer, re.IGNORECASE)
            if station_match:
                station = station_match.group(2).strip()
                break
        
        # Use "HAL 9000" if station is None or empty
        if not station or station == "":
            station = "HAL 9000"
        
        # Extract contacted station call sign - try multiple field names
        call = None
        call_patterns = [
            r'<call:(\d+)>([^<]+)',           # Standard call field
            r'<callsign:(\d+)>([^<]+)',       # Alternative field
        ]
        
        for pattern in call_patterns:
            call_match = re.search(pattern, buffer, re.IGNORECASE)
            if call_match:
                call = call_match.group(2).strip()
                break
        
        # Use "UNKNOWN" if no call sign found
        if not call:
            call = "UNKNOWN"
        
        return QSORecord(freq=freq, band=band, time_on=time_on, operator=operator, call=call, station=station)

    @staticmethod
    def _estimate_frequency_from_band(band: str) -> float:
        """
        Estimate frequency from band designation.
        
        Args:
            band: Amateur radio band (e.g., "20M", "40M", etc.)
            
        Returns:
            Estimated frequency in MHz
        """
        band_freq_map = {
            '160M': 1.900,
            '80M': 3.750,
            '60M': 5.330,
            '40M': 7.100,
            '30M': 10.125,
            '20M': 14.200,
            '17M': 18.100,
            '15M': 21.200,
            '12M': 24.900,
            '10M': 28.400,
            '6M': 50.100,
            '4M': 70.200,
            '2M': 144.200,
            '1.25M': 222.100,
            '70CM': 432.100,
            '33CM': 902.100,
            '23CM': 1296.100,
            '13CM': 2304.100,
            '9CM': 3456.100,
            '6CM': 5760.100,
            '3CM': 10368.100,
            '1.25CM': 24048.100,
        }
        
        # Normalize band string
        band_upper = band.upper().strip()
        return band_freq_map.get(band_upper, 14.200)  # Default to 20M if unknown
