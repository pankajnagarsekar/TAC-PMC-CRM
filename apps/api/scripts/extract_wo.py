import os

import pandas as pd

try:
    file_path = r"d:\_repos\TAC-PMC-CRM\apps\web\memory\majorda templates.xlsx"
    df = pd.read_excel(file_path, sheet_name="WO", header=None)

    with open("extracted_wo_template.txt", "w", encoding="utf-8") as f:
        for index, row in df.iterrows():
            # Filter out NaNs and join with pipe for clear separation
            row_vals = [str(v).strip() for v in row if pd.notna(v)]
            if row_vals:
                f.write(" | ".join(row_vals) + "\n")
    print("Extraction complete. See extracted_wo_template.txt")
except Exception as e:
    print(f"Error: {e}")
