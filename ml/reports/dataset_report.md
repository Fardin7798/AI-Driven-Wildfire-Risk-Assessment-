# Dataset Validation & Integrity Report
Generated automatically across 365 records.

## 1. Structure & Temporal Coverage
- **Total Rows**: 365
- **Total Columns**: 10
- **Date Range**: 2023-01-01 to 2023-12-31

## 2. Missing Value Audit
- Columns with missing values: 0
- [PASS] Zero missing values detected across all features.

## 3. Target Distribution & Class Balance
- **Negative Class (No Fire)**: 338 (92.60%)
- **Positive Class (Wildfire Event)**: 27 (7.40%)
- **Imbalance Ratio (Scale Pos Weight)**: 12.52:1

## 4. Zero-Lookahead Leakage Audit
- [PASS] Clean temporal separation: Train (<=2023) strictly precedes Validation (2024).
- [PASS] Clean temporal separation: Validation (2024) strictly precedes Test (2025).

## 5. Physical Range Constraints
- [PASS] `temp_max` within physical bounds [15.0, 41.8]
- [PASS] `rh_min` within physical bounds [10.4, 85.0]
- [PASS] `wind_max` within physical bounds [5.0, 44.8]
- [PASS] `precip_sum` within physical bounds [0.0, 7.8]
- [PASS] `fwi` within physical bounds [2.2, 45.0]
- [PASS] `ffmc` within physical bounds [60.1, 94.8]
