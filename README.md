# ADIF QSO Analyzer

A Python tool for analyzing ADIF (Amateur Data Interchange Format) files from ham radio contests.

## Features

- **S&P Percentage Calculation**: Determines Search & Pounce vs. CQ operations
- **QSO Rate Metrics**: Calculate average and peak QSO rates per operator
- **Operator Statistics**: QSO counts and performance metrics per operator
- **Run vs S&P Analysis**: Individual operator percentages for Run vs Search & Pounce
- **Contribution Analysis**: Each operator's percentage contribution to total QSO count
- **Comprehensive Reports**: Detailed analysis output with exportable results

## Project Structure

```
python_proj1/
├── main.py              # Main entry point
├── requirements.txt     # Project dependencies
├── src/                 # Source code directory
│   ├── __init__.py      # Package initialization
│   ├── adif_parser.py   # ADIF file parsing
│   └── metrics_analyzer.py  # QSO metrics calculation
├── tests/               # Test files
│   ├── __init__.py      # Test package initialization
│   ├── test_main.py     # ADIF parser tests
│   └── test_metrics.py  # Metrics analyzer tests
├── data/                # Sample data files
├── .vscode/             # VS Code configuration
│   └── tasks.json       # Build and run tasks
├── .github/             # GitHub configuration
│   └── copilot-instructions.md  # Copilot customization
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Python 3.7 or higher
- VS Code with Python extension

### Installation

1. Clone or download this project
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Project

#### Basic Usage
```bash
python main.py [path_to_adif_file]
```

#### Examples
```bash
# Use default file location
python main.py

# Specify custom file
python main.py contest_log.adi

# With full path
python main.py "C:\Logs\FieldDay2025.adi"
```

### Output
The tool generates:
- Console output with summary statistics
- Text file report saved as `[filename]_analysis.txt`

### Sample Output

```
QSO ANALYSIS SUMMARY REPORT
============================================================
Total QSOs: 713
S&P Percentage: 43.7%

OPERATOR STATISTICS:
----------------------------------------
Operator: 9ZV
  QSO Count: 278 (39.0% of total)
  Average Rate: 16.2 QSOs/hour
  Peak Rate: 62 QSOs/hour
  Run: 45.3% | S&P: 54.7%

Operator: UGX
  QSO Count: 289 (40.5% of total)
  Average Rate: 12.6 QSOs/hour
  Peak Rate: 52 QSOs/hour
  Run: 78.7% | S&P: 21.3%

Operator: VGO
  QSO Count: 146 (20.5% of total)
  Average Rate: 27.0 QSOs/hour
  Peak Rate: 40 QSOs/hour
  Run: 34.5% | S&P: 65.5%
```

### Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

### Building Executable

Create standalone executable:
```bash
pyinstaller --onefile --name "ADIF_SP_Calculator" main.py
```

## Contributing

1. Fork the project
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
