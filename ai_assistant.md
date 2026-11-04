# AI Assistant Integration Plan - OpenROAD Flow GUI

## Current Architecture (as of `app.py`)

### Three Integrated AI Components
| Component | Class | Type | Status | Purpose |
|-----------|-------|------|--------|---------|
| **FlowOptimizationEngine** | RL/PPO | `FlowOptimizationEngine` | Loaded at startup | Parameter optimization via PPO policy |
| **FailurePredictor** | LightGBM | `FailurePredictor` | Loaded at startup | Timing/DRC/power/congestion risk prediction |
| **SurrogateInference** | LightGBM + MLP | `SurrogateInference` | Loaded at startup | PPA prediction (WNS/TNS/Area/Power) |

### Initialization (in `OpenRoadGUI.__init__`, lines 76-88)
```python
if HAS_INTELLIGENCE:
    try:
        self.optimizer = FlowOptimizationEngine()
        self.failure_predictor = FailurePredictor()
        self.surrogate_inference = SurrogateInference(
            Path(__file__).parent / "intelligence" / "models" / "saved"
        )
    except Exception as e:
        print(f"Warning: Could not initialize intelligence modules: {e}")
```

### UI Integration (Right Rail - "AI Assistant" Panel)
- **Chat Interface** (`_build_ai_assistant`): Text-based chat with quick-action buttons
- **PPA Analysis** (`_build_ppa_analysis`): Predicted vs Actual vs Diff% table
- **Optimization Suggestions** (`_build_optimization_suggestions`): Parameter recommendations
- **Quick Actions**: "Suggest floorplan", "Predict PPA", "Recommend config", etc.

### Intelligence Menu
- **Predict Failure Risk** → `_predict_failure_risk()`
- **Suggest Optimal Parameters** → `_suggest_optimal_params()`
- **Show Surrogate Predictions** → `_show_surrogate_predictions()`
- **Open Intelligence Reports** → `_open_intelligence_reports()`

---

## Integration Phases

---

## Phase 1: Stabilize & Validate (Immediate - This Week)

### Objectives
- Ensure reliable model loading at startup
- Add graceful degradation when models unavailable
- Fix preprocessor path issue
- Add model health checks and version tracking

### Steps

#### 1.1 Fix Model Loading Robustness (`app.py` lines 76-88)
**File:** `openroad_gui/app.py`
**Location:** `OpenRoadGUI.__init__` method, lines 76-88

**Current Code:**
```python
if HAS_INTELLIGENCE:
    try:
        self.optimizer = FlowOptimizationEngine()
        self.failure_predictor = FailurePredictor()
        self.surrogate_inference = SurrogateInference(
            Path(__file__).parent / "intelligence" / "models" / "saved"
        )
    except Exception as e:
        print(f"Warning: Could not initialize intelligence modules: {e}")
```

**Replace with robust initialization:**
```python
def _init_intelligence(self):
    """Initialize AI modules with robust error handling and validation."""
    self.optimizer = None
    self.failure_predictor = None
    self.surrogate_inference = None
    
    if not HAS_INTELLIGENCE:
        self.log_viewer.log_warning("Intelligence modules not available (import failed)")
        return
    
    model_dir = Path(__file__).parent / "intelligence" / "models" / "saved"
    if not model_dir.exists():
        self.log_viewer.log_warning(f"Model directory not found: {model_dir}")
        return
    
    # Check for required model files
    required_files = [
        "surrogate_preprocessor.pkl",
        "surrogate_wns_lgb.pkl",
        "surrogate_tns_lgb.pkl", 
        "surrogate_area_lgb.pkl",
        "surrogate_power_lgb.pkl",
        "timing_closure_lgb.pkl",
        "drc_clean_lgb.pkl"
    ]
    missing = [f for f in required_files if not (model_dir / f).exists()]
    if missing:
        self.log_viewer.log_warning(f"Missing model files: {missing}")
        return
    
    try:
        self.surrogate_inference = SurrogateInference(model_dir)
        # Verify preprocessor loaded
        if self.surrogate_inference.preprocessor is None:
            raise ValueError("Preprocessor not loaded in SurrogateInference")
        
        self.failure_predictor = FailurePredictor()
        self.optimizer = FlowOptimizationEngine()
        
        self.log_viewer.log_info("✅ AI modules initialized successfully")
        self.log_viewer.log_info(f"   Models loaded from: {model_dir}")
        
    except Exception as e:
        self.log_viewer.log_warning(f"AI modules unavailable: {e}")
        self.optimizer = None
        self.failure_predictor = None
        self.surrogate_inference = None
```

**Integration:** Call `self._init_intelligence()` in `__init__` after `self.log_viewer` is created (around line 88).

---

#### 1.2 Fix Preprocessor Path Issue
**Problem:** `SurrogateInference` expects `surrogate_preprocessor.pkl` in `models/saved/` but it may not be copied during training.

**Fix in `train_surrogate.py`:**
```python
# In train_surrogate.py main(), after saving models:
# Copy preprocessor to model directory for inference
preprocessor_src = MODEL_DIR / "surrogate_preprocessor.pkl"
if preprocessor_src.exists():
    # Ensure it's in the right place for inference
    pass  # Already in correct location
else:
    # Save preprocessor from the last trained model
    joblib.dump(preprocessor, MODEL_DIR / "surrogate_preprocessor.pkl")
    print(f"Saved preprocessor to {MODEL_DIR / 'surrogate_preprocessor.pkl'}")
```

**Also fix in `onnx_export.py`:**
```python
# In SurrogateInference.__init__, add fallback:
preprocessor_path = self.model_dir / "surrogate_preprocessor.pkl"
if preprocessor_path.exists():
    self.preprocessor = joblib.load(preprocessor_path)
else:
    # Try loading from model files that embed preprocessor
    for model_file in self.model_dir.glob("surrogate_*_lgb.pkl"):
        model_data = joblib.load(model_file)
        if isinstance(model_data, dict) and 'preprocessor' in model_data:
            self.preprocessor = model_data['preprocessor']
            break
```

---

#### 1.3 Add Model Health Check & Version Tracking
**Add to `app.py`:**
```python
def _check_model_health(self):
    """Verify AI models are healthy and log versions."""
    if not self.surrogate_inference:
        return False
    
    try:
        # Test inference with dummy data
        test_features = {
            "platform": "nangate45",
            "core_utilization": 30.0,
            "core_aspect_ratio": 1.0,
            "core_margin": 5.0,
            "num_instances": 10000,
            "num_nets": 12000,
            "num_sequential": 2000,
            "num_macros": 0,
            "macro_area_ratio": 0.0,
            "log_instances": np.log1p(10000)/20,
            "log_nets": np.log1p(12000)/20,
            "seq_ratio": 0.2,
            "macro_ratio": 0.0,
        }
        pred = self.surrogate_inference.predict_ensemble(test_features)
        self.log_viewer.log_info(f"✅ Model health check passed - Sample prediction: {pred}")
        return True
    except Exception as e:
        self.log_viewer.log_error(f"Model health check failed: {e}")
        return False
```

---

#### 1.4 Add Model Version Display in AI Panel
**In `_build_ai_assistant()` method:**
```python
def _build_ai_assistant(self):
    # ... existing code ...
    
    # Add model version footer
    version_frame = ttk.Frame(self.ai_frame)
    version_frame.pack(fill="x", padx=8, pady=(4, 8))
    
    model_dir = Path(__file__).parent / "intelligence" / "models" / "saved"
    if model_dir.exists():
        # Get latest model timestamp
        model_files = list(model_dir.glob("surrogate_*_lgb.pkl"))
        if model_files:
            latest = max(model_files, key=lambda f: f.stat().st_mtime)
            version_text = f"Models: {latest.stem} | {datetime.fromtimestamp(latest.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}"
        else:
            version_text = "Models: Not loaded"
    else:
        version_text = "Models: Directory not found"
    
    ttk.Label(version_frame, text=version_text, 
              style="Secondary.TLabel", font=("TkDefaultFont", 7)).pack(anchor="w")
```

---

## Phase 2: Enhance AI Assistant UX (Next 2 Weeks)

### Objectives
- Streaming chat responses
- Context-aware suggestions (design config + recent logs)
- Actionable "Apply Suggestion" button
- Chat history persistence

---

### Steps

#### 2.1 Streaming Chat Responses
**Replace blocking `_append_ai_chat` with async streaming:**
```python
async def _send_ai_message_async(self):
    """Send message and stream response."""
    msg = self.ai_input.get()
    if not msg:
        return
    
    self._append_ai_chat(f"You: {msg}")
    self.ai_input.delete(0, tk.END)
    
    # Show typing indicator
    self._append_ai_chat("AI: ", tag="typing")
    
    # Run inference in thread
    def run_inference():
        # Build context with current design state
        context = self._build_ai_context()
        # Run inference (blocking)
        response = self._get_ai_response(context + "\nUser: " + msg)
        # Update UI from main thread
        self.after(0, lambda: self._finish_ai_response(response))
    
    threading.Thread(target=run_inference, daemon=True).start()

def _build_ai_context(self) -> str:
    """Build context string with current design state."""
    ctx = []
    if self.app_config.design_config:
        ctx.append(f"Active Design: {self.app_config.platform}/{self.app_config.design_name}")
        ctx.append(f"Config: {self.app_config.design_config}")
    # Add recent logs (last 50 lines)
    log_text = self.log_viewer.get_text()
    recent_logs = "\n".join(log_text.strip().split("\n")[-50:])
    ctx.append(f"Recent Logs:\n{recent_logs}")
    return "\n".join(ctx)

def _finish_ai_response(self, response: str):
    """Replace typing indicator with actual response."""
    # Remove last "AI: " typing line
    content = self.ai_chat.get("1.0", tk.END)
    lines = content.strip().split("\n")
    if lines and lines[-1].startswith("AI: "):
        self.ai_chat.config(state=tk.NORMAL)
        self.ai_chat.delete("end-2l", "end-1l")
        self.ai_chat.insert(tk.END, "AI: " + response + "\n")
        self.ai_chat.config(state=tk.DISABLED)
        self.ai_chat.see(tk.END)
```

---

#### 2.2 Context-Aware Suggestions
**Enhance quick-action buttons to use current design state:**
```python
def _ai_suggest_floorplan(self):
    """Suggest floorplan parameters based on current design."""
    if not self.app_config.design_config:
        self._append_ai_chat("AI: No active design. Set a config.mk first.")
        return
    
    # Read current config
    config_path = self.app_config.flow_dir / self.app_config.design_config.lstrip("./")
    if config_path.exists():
        content = config_path.read_text()
        # Extract current params
        util = re.search(r'CORE_UTILIZATION\s*=\s*(\d+)', content)
        aspect = re.search(r'CORE_ASPECT_RATIO\s*=\s*([\d.]+)', content)
        margin = re.search(r'CORE_MARGIN\s*=\s*(\d+)', content)
        
        current = f"Current: Util={util.group(1) if util else '?'}, AR={aspect.group(1) if aspect else '?'}, Margin={margin.group(1) if margin else '?'}"
    else:
        current = "Could not read config"
    
    self._append_ai_chat(f"AI: Analyzing floorplan for {self.app_config.design_name}...\n{current}")
    
    # Run surrogate prediction for multiple configs
    suggestions = self._predict_best_floorplan()
    if suggestions:
        self._append_ai_chat(f"AI: Recommended configs:\n{suggestions}")
```

---

#### 2.3 Actionable "Apply Suggestion" Button
**Make suggestions directly modify config.mk:**
```python
def _apply_suggestion(self, suggestion_text: str):
    """Parse suggestion and apply to config.mk."""
    if not self.app_config.design_config:
        messagebox.showwarning("No Design", "No active design config.mk")
        return
    
    config_path = self.app_config.flow_dir / self.app_config.design_config.lstrip("./")
    if not config_path.exists():
        messagebox.showerror("Error", f"Config not found: {config_path}")
        return
    
    # Parse suggestion for parameter changes
    # Format: "Set CORE_UTILIZATION=40, CORE_MARGIN=6"
    import re
    params = {}
    for match in re.finditer(r'(\w+)\s*=\s*([\d.]+)', suggestion_text):
        params[match.group(1)] = match.group(2)
    
    if not params:
        messagebox.showinfo("No Params", "Could not parse parameters from suggestion")
        return
    
    # Backup and update config.mk
    content = config_path.read_text()
    new_content = content
    for key, value in params.items():
        pattern = rf'(export\s+{key}\s*=\s*)[\d.]+'
        replacement = f'export {key} = {value}'
        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, new_content)
        else:
            new_content += f'\n{replacement}'
    
    # Write backup
    backup_path = config_path.with_suffix('.mk.backup')
    config_path.write_text(content)  # This was backup
    config_path.write_text(new_content)
    
    self.log_viewer.log_info(f"Applied suggestion: {params}")
    self._append_ai_chat(f"AI: Updated config.mk with {params}")
    messagebox.showinfo("Applied", f"Updated config.mk:\n" + "\n".join(f"{k}={v}" for k,v in params.items()))
```

---

#### 2.4 Chat History Persistence
```python
def _load_ai_chat_history(self):
    """Load chat history from disk."""
    history_path = Path.home() / ".config" / "openroad-gui" / "ai_chat_history.json"
    if history_path.exists():
        try:
            with open(history_path) as f:
                history = json.load(f)
            self.ai_chat.config(state=tk.NORMAL)
            for entry in history:
                self.ai_chat.insert(tk.END, entry + "\n")
            self.ai_chat.config(state=tk.DISABLED)
        except Exception:
            pass

def _save_ai_chat_history(self):
    """Save chat history to disk."""
    history_path = Path.home() / ".config" / "openroad-gui" / "ai_chat_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        content = self.ai_chat.get("1.0", tk.END).strip().split("\n")
        with open(history_path, "w") as f:
            json.dump(content, f, indent=2)
    except Exception:
        pass

def _on_close(self):
    # ... existing code ...
    self._save_ai_chat_history()
    self.destroy()
```

---

## Phase 3: Advanced AI Integration (Medium Term - Next Month)

### Objectives
- RL-guided flow parameter optimization
- Failure early-warning system
- Surrogate-guided config sweeps
- Natural language config interface

---

### Steps

#### 3.1 RL-Guided Flow Optimization
**Integrate `FlowOptimizationEngine` with flow execution:**
```python
def _run_stage_with_rl(self, stage: FlowStage):
    """Run stage with RL-suggested parameters."""
    if not self.optimizer:
        self._run_stage(stage)  # Fallback
        return
    
    # Get current design state
    state = self._get_current_flow_state()
    
    # Get RL action
    action = self.optimizer.predict_action(state)
    
    # Apply action to config
    self._apply_rl_action(action)
    
    # Run stage
    self._run_stage(stage)
    
    # After completion, compute reward and train
    new_state = self._get_current_flow_state()
    reward = self.optimizer.compute_reward(state, new_state, action, runtime)
    self.optimizer.train_step(state, action, reward, new_state)
```

---

#### 3.2 Failure Early-Warning System
**Background monitor after each stage:**
```python
def _post_stage_failure_check(self, stage: FlowStage):
    """Run failure predictor after stage completion."""
    if not self.failure_predictor:
        return
    
    metrics = self._fetch_design_metrics()
    if not metrics:
        return
    
    prediction = self.failure_predictor.predict(metrics)
    
    # Show warning if high risk
    if prediction.get("overall_risk", 0) > 0.7:
        self._show_failure_warning(stage, prediction)
    
    # Log for tracking
    self.log_viewer.log_info(f"Failure risk after {stage.label}: {prediction.get('overall_risk', 0):.1%}")
```

---

#### 3.3 Surrogate-Guided Config Sweeps
**Use surrogate to predict best configs before running:**
```python
def _predict_best_configs(self, design: str, platform: str, n_candidates: int = 20) -> List[Dict]:
    """Use surrogate to predict best configs before running ORFS."""
    if not self.surrogate_inference:
        return []
    
    # Get design features
    features = self._get_design_features(design, platform)
    
    # Generate candidate configs
    candidates = self._generate_candidate_configs(platform, n_candidates)
    
    # Predict PPA for each
    results = []
    for config in candidates:
        config_features = {**features, **config}
        pred = self.surrogate_inference.predict_ensemble(config_features)
        
        # Score: prioritize timing closure, then area, then power
        wns = pred.get("wns", -999)
        tns = pred.get("tns", -999)
        area = pred.get("area", 1e9)
        power = pred.get("power", 1e9)
        
        # Closure probability estimate
        closure_prob = 1.0 / (1.0 + np.exp(wns * 2)) if wns < 0 else 0.95
        
        score = closure_prob * 100 - area * 1e-6 - power * 1e-6
        
        results.append({
            "config": config,
            "predicted_wns": wns,
            "predicted_tns": tns,
            "predicted_area": area,
            "predicted_power": power,
            "closure_probability": closure_prob,
            "score": score
        })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]  # Top 5
```

---

#### 3.4 Natural Language Config Interface
```python
def _parse_natural_language_config(self, text: str) -> Dict[str, float]:
    """Parse natural language into config parameters."""
    # Simple pattern matching (can be enhanced with spaCy/LLM)
    params = {}
    
    # Utilization
    util_match = re.search(r'util(?:ization)?\s*(?:to|=|at)\s*(\d+)', text, re.I)
    if util_match:
        params["CORE_UTILIZATION"] = float(util_match.group(1))
    
    # Aspect ratio
    ar_match = re.search(r'aspect\s*(?:ratio)?\s*(?:to|=|at)\s*([\d.]+)', text, re.I)
    if ar_match:
        params["CORE_ASPECT_RATIO"] = float(ar_match.group(1))
    
    # Margin
    margin_match = re.search(r'margin\s*(?:to|=|at)\s*(\d+)', text, re.I)
    if margin_match:
        params["CORE_MARGIN"] = float(margin_match.group(1))
    
    # Density
    density_match = re.search(r'dens(?:ity)?\s*(?:to|=|at)\s*([\d.]+)', text, re.I)
    if density_match:
        params["PLACEMENT_DENSITY"] = float(density_match.group(1))
    
    return params

def _apply_natural_language_config(self, text: str):
    """Apply natural language config changes."""
    params = self._parse_natural_language_config(text)
    if params:
        self._apply_suggestion(params)
        self._append_ai_chat(f"AI: Applied: {params}")
    else:
        self._append_ai_chat("AI: Could not parse parameters. Try: 'Set utilization to 40, margin to 6'")
```

---

## Implementation Checklist

### Phase 1: Stabilize (This Week)
- [ ] 1.1 Replace model loading with robust `_init_intelligence()`
- [ ] 1.2 Fix preprocessor copy in training pipeline
- [ ] 1.3 Add model health check at startup
- [ ] 1.4 Add model version display in AI panel

### Phase 2: Enhance UX (Week 2)
- [ ] 2.1 Implement streaming chat with threading
- [ ] 2.2 Add context-aware quick actions
- [ ] 2.3 Make "Apply Suggestion" modify config.mk
- [ ] 2.4 Add chat history persistence

### Phase 3: Advanced Integration (Month 1)
- [ ] 3.1 Integrate RL optimizer with flow execution
- [ ] 3.2 Add failure early-warning after each stage
- [ ] 3.3 Build surrogate-guided config sweep runner
- [ ] 3.4 Add natural language config parser

---

## File Locations for Changes

| Change | File | Location |
|--------|------|----------|
| Model loading | `openroad_gui/app.py` | `OpenRoadGUI.__init__` → `_init_intelligence()` |
| Preprocessor fix | `train_surrogate.py` | `main()` after model saving |
| Preprocessor fix | `onnx_export.py` | `SurrogateInference.__init__` |
| Health check | `openroad_gui/app.py` | New method `_check_model_health()` |
| Version display | `openroad_gui/app.py` | `_build_ai_assistant()` |
| Streaming chat | `openroad_gui/app.py` | New methods `_send_ai_message_async()`, `_finish_ai_response()` |
| Context actions | `openroad_gui/app.py` | `_ai_suggest_floorplan()`, `_apply_suggestion()` |
| Chat persistence | `openroad_gui/app.py` | `_load_ai_chat_history()`, `_save_ai_chat_history()` |
| RL integration | `openroad_gui/app.py` | `_run_stage_with_rl()`, `_get_current_flow_state()` |
| Failure monitor | `openroad_gui/app.py` | `_post_stage_failure_check()` |
| Surrogate sweep | `openroad_gui/app.py` | `_predict_best_configs()`, `_generate_candidate_configs()` |
| NL config | `openroad_gui/app.py` | `_parse_natural_language_config()`, `_apply_natural_language_config()` |

---

## Dependencies to Verify

```bash
# Required for Phase 2-3
pip install scikit-learn==1.9.1  # Match training version
pip install lightgbm
pip install torch
pip install onnx onnxruntime
pip install stable-baselines3[extra] gymnasium  # For RL
```

---

## Testing Checklist

### Phase 1 Validation
- [ ] Models load without errors at startup
- [ ] Preprocessor found and loads correctly
- [ ] Health check passes with dummy prediction
- [ ] Model version displays in AI panel
- [ ] Graceful degradation when model files missing

### Phase 2 Validation
- [ ] Streaming chat shows typing indicator
- [ ] Quick actions use current design context
- [ ] "Apply Suggestion" modifies config.mk correctly
- [ ] Chat history persists across restarts

### Phase 3 Validation
- [ ] RL optimizer suggests parameters for a stage
- [ ] Failure predictor runs after stage completion
- [ ] Surrogate predicts top 5 configs for a design
- [ ] Natural language parser handles common phrases

---

## Notes

- **Model files must exist** in `openroad_gui/intelligence/models/saved/` before testing
- **Run `train_surrogate.py` and `train_failure_predictor.py`** first if models missing
- **Preprocessor must be copied** to model directory during training
- **sklearn version must match** (1.9.1) between training and inference
- **All changes in `app.py`** - single file modification for Phases 1-2

---

*Generated: 2025-11-04 | For integration into OpenROAD Flow GUI*