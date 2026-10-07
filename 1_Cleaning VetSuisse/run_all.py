"""Run all cleaning notebooks in order."""

import subprocess
import sys
from pathlib import Path

CLEANING_NOTEBOOKS = [

    # Individual dataset cleaning
    "1_0_combine_individual_dataset.ipynb",
    "1_1_check_unique_values.ipynb",
    "1_2_clean_unique_values.ipynb",
    "1_3_clean_certification.ipynb",
    "1_4_clean_calculator.ipynb",
    "1_5_anonymize_individual_data.ipynb",

    # Panel dataset cleaning
    "2_0_combine_panel_dataset.ipynb",
    "2_1_check_unique_values.ipynb",
    "2_2_clean_unique_values.ipynb",
    "2_3_clean_calculations.ipynb",
    "2_4_merge_calculator.ipynb",
    "2_5_energy_use_formulas.ipynb",
    
    # Merging individual and panel datasets
    "3_1_merge_individual_panel.ipynb",
]

here = Path(__file__).parent

for nb in CLEANING_NOTEBOOKS:
    print(f"Running {nb} ...", flush=True)
    result = subprocess.run(
        [
            "/Users/drutna/miniconda3/envs/labrct/bin/jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            "--inplace",
            "--ExecutePreprocessor.timeout=600",
            str(here / nb),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"\nFAILED: {nb}")
        print(result.stderr)
        sys.exit(1)
    print(f"  done.")

print("\nAll notebooks completed successfully.")
