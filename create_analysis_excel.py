#!/usr/bin/env python3
"""
Create comprehensive Excel workbook for prediction tracking.
Stores: Actual ORFS data, Surrogate Predictions, Failure Predictions, Errors.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path
import json

# ─── Paths ───
PREDICTION_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/prediction_results")
OUTPUT_XLSX = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/prediction_analysis.xlsx")

# ─── Styles ───
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
ERROR_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
GOOD_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
WARN_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)
ALIGN_CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)

def style_header(ws, row=1):
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = THIN_BORDER

def style_cell(ws, row, col, fill=None):
    cell = ws.cell(row=row, column=col)
    cell.border = THIN_BORDER
    cell.alignment = ALIGN_CENTER if col > 2 else ALIGN_LEFT
    if fill:
        cell.fill = fill

def auto_width(ws):
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 2, 50)

# ─── Main ───
def main():
    wb = openpyxl.Workbook()

    # ─── Sheet 1: Summary Dashboard ───
    ws1 = wb.active
    ws1.title = "Dashboard"

    dashboard_headers = [
        "Run", "Design", "Platform", "Actual WNS (ns)", "Pred WNS (ns)", "WNS Error (ns)",
        "Actual TNS (ns)", "Pred TNS (ns)", "TNS Error (ns)",
        "Actual Area (μm²)", "Pred Area (μm²)", "Area Error (%)",
        "Actual Power (mW)", "Pred Power (mW)", "Power Error (%)",
        "Setup Violations", "Hold Violations", "DRC Clean",
        "Failure Risk %", "Failure Predicted", "Timing Closure Actual",
        "Surrogate WNS Error (ns)", "Surrogate TNS Error (ns)",
        "Area Error (%)", "Power Error (%)"
    ]

    for col, header in enumerate([  # Flattened for dashboard
        "Run", "Design", "Platform",
        "Actual WNS", "Pred WNS", "WNS Err",
        "Actual TNS", "Pred TNS", "TNS Err",
        "Area Act", "Pred Area", "Area Err%",
        "Power Act", "Pred Power", "Pwr Err%",
        "Setup Viol", "Hold Viol", "DRC Clean",
        "Fail Risk %", "Fail Pred", "Timing Close",
        "WNS Err", "TNS Err", "Area Err%", "Pwr Err%"
    ], 1):
        ws1.cell(row=1, column=col+1, value=col)
    style_header(ws1)

    # ─── Sheet 2: Actual ORFS Data ───
    ws2 = wb.create_sheet("Actual_ORFS_Data")
    actual_headers = [
        "Run", "Design", "Platform", "WNS (ns)", "TNS (ns)", "Area (μm²)",
        "Power (mW)", "Setup Violations", "Hold Violations",
        "DRC Violations", "Max Slew Violations", "Max Fanout Violations",
        "Max Cap Violations", "Timing Closure", "DRC Clean", "DRC Clean Flag"
    ]
    for col, h in enumerate(actual_headers, 1):
        ws2.cell(row=1, column=col, value=h)
    style_header(ws2)

    # ─── Sheet 3: Surrogate Predictions ───
    ws3 = wb.create_sheet("Surrogate_Predictions")
    pred_headers = [
        "Run", "Design", "Platform",
        "Pred WNS (ns)", "Pred TNS (ns)", "Pred Area (μm²)", "Pred Power (mW)",
        "Model Used", "Timestamp"
    ]
    for col, h in enumerate(pred_headers, 1):
        ws3.cell(row=1, column=col, value=h)
    style_header(ws3)

    # ─── Sheet 4: Failure Predictions ───
    ws4 = wb.create_sheet("Failure_Predictions")
    fail_headers = [
        "Run", "Design", "Platform",
        "Failure Risk %", "Overall Risk Level",
        "Timing Violation Risk %", "Timing Severity",
        "DRC Violation Risk %", "DRC Severity',
        "Congestion Risk %", "Congestion Severity",
        "Power Violation Risk %', 'Power Severity',
        "Area Overflow Risk %', 'Area Severity",
        "Recommended Mitigations"
    ]
    # Fix the headers
    fail_headers = [
        "Run", "Design", "Platform",
        "Failure Risk %", "Overall Risk Level",
        "Timing Violation Risk %", "Timing Severity",
        "DRC Violation Risk %", "DRC Severity",
        "Congestion Risk %", "Congestion Severity",
        "Power Violation Risk %", "Power Severity",
        "Area Overflow Risk %", "Area Severity",
        "Recommended Mitigations"
    ]
    for col, h in enumerate(fail_headers, 1):
        ws4.cell(row=1, column=col, value=h)
    style_header(ws4)

    # ─── Sheet 5: Error Analysis ───
    ws5 = wb.create_sheet("Error_Analysis")
    error_headers = [
        "Run", "Design", "Platform",
        "WNS Error (ns)", "WNS Error %", "WNS Direction",
        "TNS Error (ns)", "TNS Error %",
        "Area Error (μm²)", "Area Error (%)",
        "Power Error (mW)", "Power Error (%)',
        "Timing Prediction Accurate", "Failure Prediction Correct",
        "Notes"
    ]
    for col, h in enumerate([
        "Run", "Design", "Platform",
        "WNS Error (ns)", "WNS Error %", "WNS Direction",
        "TNS Error (ns)", "TNS Error %",
        "Area Error (μm²)", "Area Error (%)",
        "Power Error (mW)", "Power Error (%)",
        "Timing Prediction Accurate', "Failure Prediction Correct",
        "Notes"
    ], 1):
        ws5.cell(row=1, column=col, value=col)
    style_header(ws5)

    # ─── Sheet 6: Raw Data Import ───
    ws6 = wb.create_sheet("Raw_Data_Import")
    raw_headers = ["Run", "Source_File", "Key", "Value", "Unit", "Parsed_OK"]
    for col, h in enumerate(raw_headers, 1):
        ws6.cell(row=1, column=col, value=h)
    style_header(ws6)

    # ─── Process Runs ───
    pred_dir = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/prediction_results")
    runs = sorted([d for d in Path("/Users/mihirmithani/Downloads/OpenRoad GUI/prediction_results").iterdir() if d.is_dir() and d.name.startswith("run_")])

    row_dash = 2
    row_actual = 2
    row_pred = 2
    row_fail = 2
    row_err = 2
    row_raw = 2

    for run_dir in runs:
        run_name = run_dir.name
        print(f"Processing {run_name}...")

        # Parse files
        finish_rpt = run_dir / "6_finish.rpt"
        surrogate_txt = run_dir / "surrogate_prediction.txt"
        failure_txt = run_dir / "failure_prediction.txt"

        # Parse finish report
        actual_data = {}
        if finish_rpt.exists():
            content = finish_rpt.read_text()
            import re
            patterns = {
                'wns_ns': r"wns\s+max\s+([-\d.]+)",
                'tns_ns': r"tns\s+max\s+([-\d.]+)",
                'area_um2': r"Total\s+([\d.]+)\s+Watts",  # Will parse power separately
                'power_w': r"Total\s+([\d.]+)\s+Watts",
                'setup_violations': r"setup\s+violation\s+count\s+(\d+)",
                'hold_violations': r"hold\s+violation\s+count\s+(\d+)",
                'slew_violations': r"slew\s+violation\s+count\s+(\d+)",
                'fanout_violations': r"fanout\s+violation\s+count\s+(\d+)",
                'cap_violations': r"cap\s+violation\s+count\s+(\d+)",
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    actual_data[key] = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))

        # Parse power report for area
        power_match = re.search(r"Total\s+([\d.]+)\s+Watts", content)
        if power_match:
            power_w = float(power_match.group(1))
            actual_data['power_mw'] = power_w * 1000
            actual_data['power_w'] = power_w

        # Area from power report
        area_match = re.search(r"finish__design__instance__area\s+([\d.]+)", content)
        if area_match:
            actual_data['area_um2'] = float(area_match.group(1))

        # DRC clean
        total_violations = sum([
            actual_data.get('setup_violations', 0),
            actual_data.get('hold_violations', 0),
            actual_data.get('slew_violations', 0),
            actual_data.get('fanout_violations', 0),
            actual_data.get('cap_violations', 0)
        ])
        actual_data['drc_violations'] = total_violations
        actual_data['drc_clean'] = total_violations == 0
        actual_data['timing_closure'] = actual_data.get('wns_ns', 1) >= 0

        # Parse surrogate prediction
        pred_data = {}
        if (run_dir / "surrogate_prediction.txt").exists():
            pred_content = (run_dir / "surrogate_prediction.txt").read_text()
            import re
            pred_patterns = {
                'pred_wns': r"Predicted WNS:\s+([-\d.]+)\s+ns",
                'pred_tns': r"Predicted TNS:\s+([-\d.]+)\s+ns',
                'pred_area': r"Predicted Area:\s+([\d.]+)\s+um',
                'pred_power': r"Predicted Power:\s+([\d.]+)\s+mW',
            }
            for key, pattern in pred_patterns.items():
                match = re.search(pattern, pred_data)
                if match:
                    pred_data[key] = float(match.group(1))

        # Parse failure prediction
        failure_data = {}
        if (run_dir / "failure_prediction.txt").exists():
            fail_content = (run_dir / "failure_prediction.txt").read_text()
            # Parse failure prediction
            pass

        # Extract design/platform from run name
        run_name = run_dir.name
        # Assume format: run_1, run_2 etc. Need to map to design
        # For now, use run name
        design_name = "test_counter4"  # From run_1
        platform = "asap7"

        # This is a template - in reality you'd parse from the actual files
        # For now, create the structure

    # Save
    output_path = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/prediction_analysis.xlsx")
    wb.save(output_path)
    print(f"\n✅ Excel saved to {output_path}")

if __name__ == "__main__":
    main()
PYEOF