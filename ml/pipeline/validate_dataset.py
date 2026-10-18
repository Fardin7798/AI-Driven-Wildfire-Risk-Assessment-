"""Automated dataset validation: null checks, range bounds, class balance, and leakage tests."""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPORT_OUTPUT_PATH = Path("ml/reports/dataset_report.md")


def validate_dataset(df: pd.DataFrame, report_path: Path) -> bool:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Dataset Validation & Integrity Report",
        f"Generated automatically across {len(df)} records.\n",
        "## 1. Structure & Temporal Coverage",
        f"- **Total Rows**: {len(df)}",
        f"- **Total Columns**: {len(df.columns)}",
    ]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        min_date, max_date = df["date"].min(), df["date"].max()
        lines.append(f"- **Date Range**: {min_date.date()} to {max_date.date()}")

    # Missing value audit
    null_counts = df.isnull().sum()
    nulls_present = null_counts[null_counts > 0]
    lines.extend([
        "\n## 2. Missing Value Audit",
        f"- Columns with missing values: {len(nulls_present)}",
    ])
    if len(nulls_present) > 0:
        for col, cnt in nulls_present.items():
            pct = (cnt / len(df)) * 100
            lines.append(f"  - `{col}`: {cnt} missing ({pct:.2f}%)")
    else:
        lines.append("- [PASS] Zero missing values detected across all features.")

    # Class balance audit
    lines.append("\n## 3. Target Distribution & Class Balance")
    if "label" in df.columns:
        pos_count = (df["label"] == 1).sum()
        neg_count = (df["label"] == 0).sum()
        pos_ratio = (pos_count / len(df)) * 100
        lines.extend([
            f"- **Negative Class (No Fire)**: {neg_count} ({(100 - pos_ratio):.2f}%)",
            f"- **Positive Class (Wildfire Event)**: {pos_count} ({pos_ratio:.2f}%)",
            f"- **Imbalance Ratio (Scale Pos Weight)**: {(neg_count / max(1, pos_count)):.2f}:1",
        ])

    # Temporal Leakage Validation
    lines.append("\n## 4. Zero-Lookahead Leakage Audit")
    leak_detected = False

    # Check temporal split isolation
    if "year" in df.columns and "date" in df.columns:
        train_rows = df[df["year"] <= 2023]
        val_rows = df[df["year"] == 2024]
        test_rows = df[df["year"] == 2025]

        train_max = train_rows["date"].max() if len(train_rows) > 0 else None
        val_min = val_rows["date"].min() if len(val_rows) > 0 else None
        val_max = val_rows["date"].max() if len(val_rows) > 0 else None
        test_min = test_rows["date"].min() if len(test_rows) > 0 else None

        if train_max and val_min and train_max >= val_min:
            lines.append("- [FAIL] Train/Validation overlap detected!")
            leak_detected = True
        else:
            lines.append("- [PASS] Clean temporal separation: Train (<=2023) strictly precedes Validation (2024).")

        if val_max and test_min and val_max >= test_min:
            lines.append("- [FAIL] Validation/Test overlap detected!")
            leak_detected = True
        else:
            lines.append("- [PASS] Clean temporal separation: Validation (2024) strictly precedes Test (2025).")

    # Range and physical bounds check
    lines.append("\n## 5. Physical Range Constraints")
    range_checks = [
        ("temp_max", -10.0, 55.0),
        ("rh_min", 0.0, 100.0),
        ("wind_max", 0.0, 150.0),
        ("precip_sum", 0.0, 800.0),
        ("fwi", 0.0, 200.0),
        ("ffmc", 0.0, 101.0),
    ]
    for col, min_val, max_val in range_checks:
        if col in df.columns:
            actual_min, actual_max = df[col].min(), df[col].max()
            if actual_min < min_val or actual_max > max_val:
                lines.append(f"- [WARN] `{col}` out of expected bounds: [{actual_min}, {actual_max}] vs [{min_val}, {max_val}]")
            else:
                lines.append(f"- [PASS] `{col}` within physical bounds [{actual_min:.1f}, {actual_max:.1f}]")

    report_content = "\n".join(lines) + "\n"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Dataset integrity report written to: {report_path}")
    return not leak_detected


def main():
    parser = argparse.ArgumentParser(description="Validate processed ML dataset and check for leakage")
    parser.add_argument("--input", type=Path, help="Path to input dataset parquet")
    parser.add_argument("--report", type=Path, default=REPORT_OUTPUT_PATH)
    args = parser.parse_args()

    if not args.input or not args.input.exists():
        print(f"Error: Dataset file not found: {args.input}. Please run the feature pipeline first.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(args.input)
    success = validate_dataset(df, args.report)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
