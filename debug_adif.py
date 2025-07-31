
#!/usr/bin/env python3
"""Debug script to examine ADIF file contents."""

import sys
from pathlib import Path


def examine_adif_file(filename: str) -> None:
    """Examine the structure of an ADIF file."""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        content = None
        encoding_used = None
        
        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding) as file:
                    content = file.read()
                encoding_used = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print("❌ Could not read file with any supported encoding")
            return
            
        print(f"✅ Successfully read file with {encoding_used} encoding")
        print(f"📄 File size: {len(content)} characters")
        print(f"📄 File lines: {content.count(chr(10)) + 1}")
        
        print("\n" + "="*60)
        print("FIRST 500 CHARACTERS:")
        print("="*60)
        print(content[:500])
        print("="*60)
        
        # Look for QSO records
        eor_count = content.upper().count('<EOR>')
        eor_with_slash = content.upper().count('</EOR>')
        print(f"\n📊 Found {eor_count} <EOR> tags (end of record markers)")
        if eor_with_slash > 0:
            print(f"📊 Found {eor_with_slash} </EOR> tags (XML-style end markers)")
        
        # Look for common ADIF fields
        common_fields = ['CALL', 'FREQ', 'BAND', 'MODE', 'TIME_ON', 'QSO_DATE', 'OPERATOR', 'STATION_CALLSIGN']
        print("\n📋 ADIF FIELDS FOUND:")
        print("-" * 40)
        for field in common_fields:
            count = content.upper().count(f'<{field}:')
            if count > 0:
                print(f"  <{field}:...> : {count} occurrences")
            else:
                print(f"  <{field}:...> : ❌ NOT FOUND")
        
        # Look for ADIF header
        header_match = content.upper().find('<ADIF_VER:')
        if header_match >= 0:
            print(f"\n📋 ADIF header found at position {header_match}")
        else:
            print(f"\n⚠️  No ADIF header found")
        
        # Show a sample QSO record if any
        eor_pos = content.upper().find('<EOR>')
        if eor_pos > 0:
            # Find the start of this record (look backwards for previous <EOR> or start of file)
            prev_eor = content.upper().rfind('<EOR>', 0, eor_pos)
            start_pos = prev_eor + 5 if prev_eor >= 0 else 0
            
            # Skip any header content before first QSO
            first_field = content.find('<', start_pos)
            if first_field > start_pos:
                start_pos = first_field
            
            sample_record = content[start_pos:eor_pos + 5]
            print(f"\n" + "="*60)
            print("SAMPLE QSO RECORD:")
            print("="*60)
            display_length = min(500, len(sample_record))
            print(sample_record[:display_length])
            if len(sample_record) > display_length:
                print(f"... (truncated, full record is {len(sample_record)} characters)")
            print("="*60)
        else:
            print(f"\n❌ No QSO records found (no <EOR> tags)")
            
        # Check for potential issues
        print(f"\n🔍 POTENTIAL ISSUES:")
        print("-" * 40)
        
        if eor_count == 0:
            print("❌ No <EOR> tags found - file may not be valid ADIF")
        
        if content.upper().count('<FREQ:') == 0:
            print("❌ No frequency fields found")
            
        if content.upper().count('<BAND:') == 0:
            print("❌ No band fields found")
            
        if content.upper().count('<TIME_ON:') == 0:
            print("❌ No time_on fields found")
            
        if content.upper().count('<CALL:') == 0:
            print("❌ No call sign fields found")
            
        # Look for non-ASCII characters that might cause issues
        non_ascii_chars = [c for c in content if ord(c) > 127]
        if non_ascii_chars:
            unique_chars = set(non_ascii_chars)
            print(f"⚠️  Found {len(non_ascii_chars)} non-ASCII characters ({len(unique_chars)} unique)")
            if len(unique_chars) <= 10:
                print(f"   Characters: {', '.join(repr(c) for c in sorted(unique_chars))}")
        
        # Check line endings
        crlf_count = content.count('\r\n')
        lf_count = content.count('\n') - crlf_count
        cr_count = content.count('\r') - crlf_count
        
        print(f"\n📄 LINE ENDINGS:")
        print(f"   CRLF (\\r\\n): {crlf_count}")
        print(f"   LF (\\n): {lf_count}")
        print(f"   CR (\\r): {cr_count}")
        
        print(f"\n✅ Analysis complete!")
        
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
    except Exception as e:
        print(f"❌ Error examining file: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = input("Enter ADIF file path: ")
    
    print(f"🔍 Examining ADIF file: {filename}")
    print("=" * 80)
    examine_adif_file(filename)
