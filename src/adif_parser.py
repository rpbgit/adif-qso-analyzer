"""ADIF file parser for ham radio QSO data."""

import re
from typing import List, Dict, Optional, Any
from pathlib import Path


class QSORecord:
    """Represents a single QSO record."""
    
    def __init__(self, freq: Optional[float] = None, band: Optional[str] = None, 
                 time_on: Optional[int] = None, operator: Optional[str] = None,
                 call: Optional[str] = None, station: Optional[str] = None,
                 qso_date: Optional[str] = None, mode: Optional[str] = None,
                 section: Optional[str] = None, country: Optional[str] = None) -> None:
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
        self.qso_date = qso_date
        self.mode = mode
        self.section = section
        self.country = country
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert QSO record to dictionary."""
        return {
            'freq': self.freq,
            'band': self.band,
            'time': self.time_on,
            'operator': self.operator,
            'call': self.call,
            'station': self.station,
            'qso_date': self.qso_date,
            'mode': self.mode,
            'section': self.section,
            'country': self.country
        }





class ADIFParser:
    """Parser for ADIF (Amateur Data Interchange Format) files using adif-io."""

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
            import adif_io
            print(f"Trying to open {filename} with encoding: utf-8")
            adif_data, _ = adif_io.read_from_file(filename)
            print(f"Successfully read {filename} with encoding: utf-8")
        except ImportError:
            raise ImportError("adif-io package is not installed. Please install it via requirements.txt.")
        except Exception as e:
            raise IOError(f"Failed to read {filename} with encoding utf-8: {e}")

        for qso in adif_data:
            qso_norm = {k.lower(): v for k, v in qso.items()}
            freq = None
            if 'freq' in qso_norm:
                try:
                    freq = float(qso_norm['freq'])
                except Exception:
                    freq = None
            band = str(qso_norm.get('band', 'UNKNOWN')).strip().upper() if qso_norm.get('band') else 'UNKNOWN'
            qso_date = str(qso_norm.get('qso_date', None)) if qso_norm.get('qso_date') else None
            mode = str(qso_norm.get('mode', 'UNKNOWN')).strip().upper() if qso_norm.get('mode') else 'UNKNOWN'
            section = None
            for field in ['arrl_sect', 'n3fjp_spcnum', 'section']:
                if field in qso_norm and qso_norm[field]:
                    section = str(qso_norm[field]).strip().upper()
                    break
            if not section:
                section = 'UNKNOWN'
            time_on = None
            if 'time_on' in qso_norm and qso_norm['time_on']:
                try:
                    time_on = int(qso_norm['time_on'])
                except Exception:
                    time_on = None
            elif 'time' in qso_norm and qso_norm['time']:
                try:
                    time_on = int(qso_norm['time'])
                except Exception:
                    time_on = None
            operator = str(qso_norm.get('operator', None)).strip().upper() if qso_norm.get('operator') else None
            if not operator:
                operator = "MR. NOBODY"
            station = None
            for field in ['n3fjp_computername', 'app_n1mm_netbiosname']:
                if field in qso_norm and qso_norm[field]:
                    station = str(qso_norm[field]).strip()
                    break
            if not station:
                station = "HAL 9000"
            call = None
            for field in ['call', 'callsign']:
                if field in qso_norm and qso_norm[field]:
                    call = str(qso_norm[field]).strip().upper()
                    break
            if not call:
                call = "UNKNOWN"
            country = str(qso_norm.get('country', None)).strip().upper() if qso_norm.get('country') else None
            if not country:
                country = ADIFParser._infer_country_from_call(call)
            qso_dict = {
                'freq': freq,
                'band': band,
                'time': time_on,
                'operator': operator,
                'call': call,
                'station': station,
                'qso_date': qso_date,
                'mode': mode,
                'section': section,
                'country': country
            }
            qsos.append(qso_dict)
        qsos = [q for q in qsos if q['freq'] is not None or q['band'] is not None]
        def qso_sort_key(q: Dict[str, Any]):
            date = q.get('qso_date')
            date_str = str(date) if date and str(date).isdigit() and len(str(date)) == 8 else '00000000'
            time_val = q.get('time')
            if time_val is None:
                time_str = '000000'
            else:
                time_str = f"{int(time_val):06d}"
            return (date_str, time_str)
        qsos = sorted(qsos, key=qso_sort_key)
        return qsos

    @staticmethod
    def _infer_country_from_call(call: str) -> str:
        """
        Infer country from callsign prefix (very basic, not exhaustive).
        """
        if not call or call == "UNKNOWN":
            return "UNKNOWN"
        call = call.upper()
        if call.startswith(('K', 'W', 'N')) and len(call) > 1 and call[1].isdigit():
            return "UNITED STATES"
        if call.startswith('VE') or call.startswith('VA'):
            return "CANADA"
        if call.startswith('XE'):
            return "MEXICO"
        if call.startswith('JA'):
            return "JAPAN"
        if call.startswith('DL'):
            return "GERMANY"
        if call.startswith(('G', 'M')) and len(call) > 1 and call[1].isdigit():
            return "ENGLAND"
        if call.startswith('VK'):
            return "AUSTRALIA"
        if call.startswith('ZL'):
            return "NEW ZEALAND"
        if call.startswith('I') and len(call) > 1 and call[1].isdigit():
            return "ITALY"
        if call.startswith('F') and len(call) > 1 and call[1].isdigit():
            return "FRANCE"
        if call.startswith('EA'):
            return "SPAIN"
        return "UNKNOWN"

    @staticmethod
    def _estimate_frequency_from_band(band: str) -> float:
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
        band_upper = band.upper().strip()
