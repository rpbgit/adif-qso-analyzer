#!/usr/bin/env python3
"""
Main entry point for the ADIF QSO analyzer.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import adif_io

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adif_parser import ADIFParser
from src.metrics_analyzer import QSOMetrics


def normalize_qso_fields(qso: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize QSO fields for compatibility with N3FJP ADIF format.
    Handles mapping of N1MM and N3FJP-specific tags.
    """
    # Normalize all keys and string values to upper case
    qso_norm = {}
    for k, v in qso.items():
        key_upper = k.upper()
        if isinstance(v, str):
            qso_norm[key_upper] = v.strip().upper()
        else:
            qso_norm[key_upper] = v
    # Map N1MM Class tag to N3FJP, set empty if neither present
    if not qso_norm.get('CLASS'):
        if 'APP_N1MM_EXCHANGE1' in qso_norm and qso_norm['APP_N1MM_EXCHANGE1']:
            qso_norm['CLASS'] = qso_norm['APP_N1MM_EXCHANGE1']
        else:
            qso_norm['CLASS'] = ''
    # Map N1MM computer name to N3FJP
    if not qso_norm.get('N3FJP_COMPUTERNAME'):
        if 'APP_N1MM_NETBIOSNAME' in qso_norm and qso_norm['APP_N1MM_NETBIOSNAME']:
            qso_norm['N3FJP_COMPUTERNAME'] = qso_norm['APP_N1MM_NETBIOSNAME']
        else:
            qso_norm['N3FJP_COMPUTERNAME'] = ''
    # Ensure ARRL_SECT is upper case (already handled above, but for safety)
    if 'ARRL_SECT' in qso_norm and isinstance(qso_norm['ARRL_SECT'], str):
        qso_norm['ARRL_SECT'] = qso_norm['ARRL_SECT'].strip().upper()

    # Ensure OPERATOR is set to 'Mr. Nobody' if missing or empty
    if not qso_norm.get('OPERATOR') or (isinstance(qso_norm.get('OPERATOR'), str) and qso_norm.get('OPERATOR').strip() == ''):
        qso_norm['OPERATOR'] = 'Mr. Nobody'
    return qso_norm


def write_adif_file(qsos: List[Dict[str, Any]], output_file: str, header: str = "") -> None:
    """
    Write QSO records to an ADIF file in N3FJP-compatible format.
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Define standard N3FJP Field Day ADIF fields
    n3fjp_fields = [
        'CALL', 'QSO_DATE', 'TIME_ON', 'BAND', 'FREQ', 'MODE', 'RST_SENT', 'RST_RCVD',
        'ARRL_SECT', 'CLASS', 'OPERATOR', 'STATION', 'N3FJP_COMPUTERNAME'
    ]
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            if header:
                f.write(f"{header}\n")
            f.write("<EOH>\n")
            for qso in qsos:
                record = ""
                for field in n3fjp_fields:
                    v = qso.get(field, '')
                    if v is not None and v != "":
                        record += f"<{field}:{len(str(v))}>{v} "
                    elif field == 'CLASS':
                        record += f"<CLASS:0> "
                record += "<EOR>\n"
                f.write(record)
    except Exception as e:
        print(f"Error writing ADIF file '{output_file}': {e}")
        raise


def concatenate_adif_files(input_files: List[str], output_file: str) -> None:
    """
    Concatenate QSO records from multiple ADIF files and write to a new ADI file.
    Normalizes fields for N3FJP compatibility.
    """
    all_qsos = []
    import adif_io
    read_messages = []
    print("")
    for file in input_files:
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                file_content = f.read()
            adif_data, _ = adif_io.read_from_string(file_content)
            msg = f"Read {len(adif_data)} QSO records from '{file}'"
            print(msg)
            read_messages.append(msg)
        except Exception as e:
            print(f"Error reading ADIF file '{file}': {e}")
            continue
        for qso in adif_data:
            norm_qso = normalize_qso_fields(qso)
            # Uppercase all string values for output as well
            for k in norm_qso:
                if isinstance(norm_qso[k], str):
                    norm_qso[k] = norm_qso[k].upper()
            n3fjp_fields = [
                'CALL', 'QSO_DATE', 'TIME_ON', 'BAND', 'FREQ', 'MODE', 'CLASS', 'ARRL_SECT', 
                'OPERATOR', 'STATION', 'N3FJP_COMPUTERNAME', 'APP_N1MM_NETBIOSNAME'
            ]
            filtered_qso = {field: norm_qso.get(field, '') for field in n3fjp_fields}
            # Ensure all output values are upper case strings
            for k in filtered_qso:
                if isinstance(filtered_qso[k], str):
                    filtered_qso[k] = filtered_qso[k].upper()
            all_qsos.append(filtered_qso)
    try:
        write_adif_file(all_qsos, output_file, header="Exported by ADIF QSO Analyzer")
    except Exception as e:
        print(f"Error writing concatenated ADIF file '{output_file}': {e}")
    return all_qsos, read_messages


def main() -> None:
    """Main function for ADIF analysis."""
    # Example usage: python main.py file1.adi file2.adi file3.adi
    import glob
    input_files = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if '*' in arg or '?' in arg:
                input_files.extend(glob.glob(arg))
            else:
                input_files.append(arg)
    else:
        input_files = ["data/FieldDay.adi"]

    if not input_files:
        print("No files matched the provided pattern(s).")
        sys.exit(1)
    output_file = "data/composite.adi"
    print(f"Concatenating ADIF files: {input_files}")
    qsos, read_messages = concatenate_adif_files(input_files, output_file)
    filename = output_file  # Only used for naming the report file, not for reparsing

    if not qsos:
        print("No valid QSO records found in the file.")
        return
    try:
        from datetime import datetime
        report = QSOMetrics.generate_summary_report(qsos)
        # Prepend header with current date and time
        header = ('+' * 80) + '\n'
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header += f"Report generated: {now_str}\n"
        report_with_reads = header + "\n" + "\n".join(read_messages) + "\n\n" + report
        print(report_with_reads)
        output_report = f"{Path(filename).stem}_analysis.txt"
        with open(output_report, 'w', encoding='utf-8') as f:
            f.write(report_with_reads)
        print(f"Report saved to: {output_report}")
    except (FileNotFoundError, IOError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
