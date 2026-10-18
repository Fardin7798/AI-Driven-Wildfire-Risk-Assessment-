import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.unit.test_domain import (
    test_cpcb_naqi_breakpoints,
    test_derive_wildfire_label,
    test_fwi_calculation_bounds_and_propagation,
    test_fwi_rain_damping,
    test_risk_probability_classification,
    test_zero_lookahead_leakage_assertion,
)
from tests.unit.test_providers import (
    test_firms_csv_parser,
    test_open_meteo_weather_parser,
    test_provider_registry_country_config,
)

test_functions = [
    test_fwi_calculation_bounds_and_propagation,
    test_fwi_rain_damping,
    test_cpcb_naqi_breakpoints,
    test_risk_probability_classification,
    test_zero_lookahead_leakage_assertion,
    test_derive_wildfire_label,
    test_firms_csv_parser,
    test_open_meteo_weather_parser,
    test_provider_registry_country_config,
]

failed = 0
passed = 0

print("🚀 Running Unit Test Suite (Domain & Providers)...")
for tf in test_functions:
    try:
        tf()
        print(f"  ✅ PASS: {tf.__name__}")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ FAIL: {tf.__name__} - {e}")
        failed += 1
    except Exception as e:
        print(f"  💥 ERROR: {tf.__name__} - {e}")
        failed += 1

print(f"\nResults: {passed} passed, {failed} failed.")
if failed > 0:
    sys.exit(1)
sys.exit(0)
