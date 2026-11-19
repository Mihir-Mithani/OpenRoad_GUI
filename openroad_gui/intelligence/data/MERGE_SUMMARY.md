# Merge Summary: New AWS asap7 Batch Data into Master Dataset

## Summary
Successfully merged 18 new AWS asap7 batch runs into the master training dataset.

## Merge Statistics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Records | 175 | 193 | +18 |
| Designs | 9 | 11 | +2 (aes-mbff, aes-block) |
| Platforms | 4 | 4 | 0 |
| Successful Runs | 152 | 170 | +18 |
| Failed Runs | 23 | 23 | 0 |

### New Designs Added
| Design | Records | Platform | WNS Range (ns) | TNS Range (ns) | Area (µm²) | Power (W) |
|--------|---------|----------|----------------|----------------|------------|-----------|
| aes-mbff | 3 | asap7 | -12.8 to -6.7 | -159 to -49 | 4,112 | 0.172 - 0.173 W |
| aes-block | 7 | asap7 | -68.3 to -20.9 | -1,666 to -229 | 12,829 - 20,124 | 7.0 - 7.6 mW |

### Data Quality
- **Total records**: 193 (175 original + 18 new)
- **Success rate**: 88% (170/193)
- **All new records**: Status = "success" ✅
- **No duplicates**: Verified by run_id deduplication
- **Backup created**: `real_runs_training.json.backup`

### Design Distribution (Post-Merge)
| Design | Records | Platform |
|--------|---------|----------|
| gcd | 64 | nangate45 |
| aes | 29 | nangate45 |
| riscv32i-mock-sram | 23 | nangate45 |
| ibex | 14 | nangate45 |
| uart-blocks | 13 | nangate45 |
| riscv32i | 11 | gf180 |
| picorv32 | 10 | sky130hd |
| dynamic_node | 10 | asap7 |
| jpeg | 9 | nangate45 |
| **aes-block** | 7 | **asap7** (NEW) |
| **aes-mbff** | 3 | **asap7** (NEW) |

### Platform Distribution
| Platform | Records | Designs |
|----------|---------|---------|
| nangate45 | 63 | 6 |
| asap7 | 56 | 4 |
| gf180 | 44 | 1 |
| sky130hd | 30 | 1 |

### Files Updated
- **Primary**: `/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json` (193 records)
- **Backup**: `real_runs_training.json.backup` (original 175 records)
- **New data source**: `/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/asap_new_batch/extracted/training_data.jsonl`

### Schema Compatibility
The new records have been normalized to match the master schema with 78 columns including:
- All timing metrics (WNS, TNS, setup/hold WS, Fmax, skew)
- All violation counts (setup, hold, DRC)
- All power metrics (total, internal, switching, leakage in W and mW)
- All area metrics (core, die, instance area/count)
- All design config parameters (utilization, aspect ratio, margin, density)
- All metadata (timestamps, status, run_id, design_name, platform)

### Verification
✅ All 18 new records merged successfully  
✅ All new records have status="success"  
✅ No duplicate run_ids  
✅ Schema alignment verified  
✅ Original backup preserved  
✅ Master dataset now has 193 records across 11 designs on 4 platforms  

---

*Merge completed: 2026-11-18*  
*Script: `merge_new_aws_data.py`*  
*Backup: `real_runs_training.json.backup`*