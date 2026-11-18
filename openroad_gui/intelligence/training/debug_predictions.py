#!/usr/bin/env python3
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['LIGHTGBM_NUM_THREADS'] = '1'

import joblib, torch, numpy as np, pandas as pd
from pathlib import Path
from sklearn.metrics import r2_score

MODEL_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved")

df = pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")
df = df[df['suitable_for_regression']].copy()
df = df.copy()
df['final_wns_ns'] = np.clip(df['final_wns_ns'], -500, 100)
df['final_tns_ns'] = np.clip(df['final_tns_ns'], -10000, 100)
df['final_area_um2_log'] = np.log1p(np.maximum(df['final_area_um2'], 0))
df['final_power_mw_log'] = np.log1p(np.maximum(df['final_power_mw'], 0))
df['log_instances'] = np.log1p(df['num_instances']) / 20
df['log_nets'] = np.log1p(df['num_nets']) / 20
df['seq_ratio'] = df['num_sequential'] / np.maximum(df['num_instances'], 1)
df['macro_ratio'] = df['num_macros'] / np.maximum(df['num_instances'], 1)
df['log_area'] = np.log1p(df['final_area_um2']) / 20
df['log_power'] = np.log1p(df['final_power_mw']) / 20
df['wns_normalized'] = np.clip(df['final_wns_ns'] / 10, -1, 1)
df['tns_normalized'] = np.clip(df['final_tns_ns'] / 1000, -1, 1)
df['sample_weight'] = 1.0

pre = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_preprocessor_v2.pkl")
X = pre.transform(df)

lgb_obj = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_lgb.pkl")
lgb_model = lgb_obj['model'] if isinstance(lgb_obj, dict) else lgb_obj

import torch
checkpoint = torch.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_mlp.pt", map_location='cpu')

class MLP(torch.nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(d,256), torch.nn.BatchNorm1d(256), torch.nn.ReLU(), torch.nn.Dropout(0.2),
            torch.nn.Linear(256,128), torch.nn.BatchNorm1d(128), torch.nn.ReLU(), torch.nn.Dropout(0.2),
            torch.nn.Linear(128,64), torch.nn.BatchNorm1d(64), torch.nn.ReLU(), torch.nn.Dropout(0.2),
            torch.nn.Linear(64,1)
        )
    def forward(self,x): return self.net(x).squeeze(-1)

mlp = MLP(18)
mlp.load_state_dict(torch.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_mlp.pt", map_location='cpu')['model_state'])
mlp.eval()

pre = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_preprocessor_v2.pkl")
X_all = df
X_processed = pre.transform(X_all)

lgb_obj = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_lgb.pkl")
lgb_model = lgb_obj['model'] if isinstance(lgb_obj, dict) else lgb_obj

mlp = MLP(18)
mlp.load_state_dict(torch.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_mlp.pt", map_location='cpu')['model_state'])
mlp.eval()

with torch.no_grad():
    y_mlp = mlp(torch.FloatTensor(torch.from_numpy(X_processed.astype('float32')))).numpy()

y_lgb = lgb_model.predict(X_processed)

print("LGB range:", y_lgb.min(), y_lgb.max())
print("MLP range:", y_mlp.min(), y_mlp.max())

y_ens = (y_lgb + y_mlp) / 2
print("Ensemble range:", y_ens.min(), y_ens.max())

df = pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")
df = df[df['suitable_for_regression']].copy()
y_true = np.clip(df['final_wns_ns'], -500, 100).values

print("True range:", y_true.min(), y_true.max())
print("True mean:", y_true.mean())

print("\nFirst 10 predictions vs true:")
for i in range(min(10, len(y_true))):
    print(f"  true={y_true[i]:.3f}, lgb={y_lgb[i]:.3f}, mlp={y_mlp[i]:.3f}, ens={y_ens[i]:.3f}")

print("\nR² (ensemble):", r2_score(y_true, y_ens))
print("R² (LGB only):", r2_score(y_true, y_lgb))
print("R² (MLP only):", r2_score(y_true, y_mlp))
print("R² (mean baseline):", r2_score(y_true, np.full_like(y_true, y_true.mean())))
