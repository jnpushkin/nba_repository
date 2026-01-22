"""
Excel workbook generator for NBA statistics.
"""

import os
from typing import Dict, Any
import pandas as pd

from ..utils.constants import EXCEL_COLORS


def generate_excel_workbook(data: Dict[str, pd.DataFrame], output_path: str) -> None:
    """
    Generate an Excel workbook from processed NBA data.

    Args:
        data: Dictionary of DataFrames to write
        output_path: Path for output Excel file
    """
    try:
        import xlsxwriter
    except ImportError:
        # Fallback to openpyxl if xlsxwriter not available
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet_name, df in data.items():
                if not df.empty:
                    clean_name = sheet_name.replace('_', ' ').title()[:31]
                    df.to_excel(writer, sheet_name=clean_name, index=False)
        return

    # Use xlsxwriter for better formatting
    workbook = xlsxwriter.Workbook(output_path)

    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': EXCEL_COLORS['header_blue'],
        'font_color': EXCEL_COLORS['white'],
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
    })

    number_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
    })

    decimal_format = workbook.add_format({
        'num_format': '0.0',
        'align': 'center',
        'valign': 'vcenter',
    })

    pct_format = workbook.add_format({
        'num_format': '0.000',
        'align': 'center',
        'valign': 'vcenter',
    })

    # Sheet name mapping
    sheet_names = {
        'players': 'Player Stats',
        'player_games': 'Game Log',
        'starters_vs_bench': 'Starters vs Bench',
        'season_highs': 'Season Highs',
        'triple_doubles': 'Triple-Doubles',
        'double_doubles': 'Double-Doubles',
    }

    for key, df in data.items():
        if df.empty:
            continue

        sheet_name = sheet_names.get(key, key.replace('_', ' ').title())[:31]
        worksheet = workbook.add_worksheet(sheet_name)

        # Write headers
        for col_num, column in enumerate(df.columns):
            worksheet.write(0, col_num, column, header_format)

        # Write data
        for row_num, row in enumerate(df.values, start=1):
            for col_num, value in enumerate(row):
                col_name = df.columns[col_num]

                # Choose format based on column
                if col_name in ['FG%', '3P%', 'FT%', 'TS%', 'eFG%']:
                    worksheet.write(row_num, col_num, value, pct_format)
                elif col_name in ['PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TOPG', 'MPG', 'Game Score']:
                    worksheet.write(row_num, col_num, value, decimal_format)
                else:
                    worksheet.write(row_num, col_num, value, number_format)

        # Auto-fit columns
        for col_num, column in enumerate(df.columns):
            max_len = max(
                len(str(column)),
                df[column].astype(str).str.len().max() if len(df) > 0 else 0
            )
            worksheet.set_column(col_num, col_num, min(max_len + 2, 30))

        # Freeze header row
        worksheet.freeze_panes(1, 0)

    workbook.close()
