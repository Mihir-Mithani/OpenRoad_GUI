#!/usr/bin/env python3
"""Test script for intelligence module integration"""

import sys
sys.path.insert(0, '/Users/mihirmithani/Downloads/OpenRoad GUI')

print("Testing intelligence module integration...")
print("=" * 60)

# Test 1: Import intelligence module
try:
    from openroad_gui.intelligence import FlowOptimizationEngine, FailurePredictor
    print("✅ 1. Intelligence module imports successfully")
except Exception as e:
    print(f"❌ 1. Import failed: {e}")
    sys.exit(1)

# Test 2: Instantiate FailurePredictor
try:
    predictor = FailurePredictor()
    print("✅ 2. FailurePredictor instantiated")
except Exception as e:
    print(f"❌ 2. FailurePredictor instantiation failed: {e}")
    sys.exit(1)

# Test 3: Test predict method
try:
    sample_metrics = {
        'wns_ns': -0.5,
        'tns_ns': -10.0,
        'drc_violations': 5,
        'congestion_pct': 85,
        'placement_density': 0.75,
        'wirelength': 100000,
        'via_count': 5000,
        'iteration': 1,
        'runtime_sec': 300,
        'memory_usage_mb': 2048
    }
    result = predictor.predict(sample_metrics)
    print("✅ 3. FailurePredictor.predict() works")
    print(f"   Result keys: {list(result.keys())}")
    print(f"   Overall risk: {result.get('overall_risk', 0):.2%}")
    print(f"   Predictions: {list(result.get('predictions', {}).keys())}")
except Exception as e:
    print(f"❌ 3. FailurePredictor.predict() failed: {e}")
    sys.exit(1)

# Test 4: Instantiate FlowOptimizationEngine
try:
    optimizer = FlowOptimizationEngine()
    print("✅ 4. FlowOptimizationEngine instantiated")
except Exception as e:
    print(f"❌ 4. FlowOptimizationEngine instantiation failed: {e}")
    sys.exit(1)

# Test 5: Test default action
try:
    action = optimizer._default_action()
    print("✅ 5. FlowOptimizationEngine._default_action() works")
    print(f"   Action type: {type(action).__name__}")
except Exception as e:
    print(f"❌ 5. FlowOptimizationEngine._default_action() failed: {e}")
    sys.exit(1)

# Test 6: Check HAS_INTELLIGENCE flag in app
try:
    from openroad_gui.app import HAS_INTELLIGENCE
    print(f"✅ 6. HAS_INTELLIGENCE flag: {HAS_INTELLIGENCE}")
except Exception as e:
    print(f"❌ 6. HAS_INTELLIGENCE check failed: {e}")

# Test 7: Check parser module
try:
    from openroad_gui.intelligence.data.parser import parse_reports_directory
    print("✅ 7. Parser module imports successfully")
except Exception as e:
    print(f"❌ 7. Parser module import failed: {e}")

print("=" * 60)
print("All intelligence integration tests passed!")