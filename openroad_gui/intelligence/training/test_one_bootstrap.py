#!/usr/bin/env python3
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['LIGHTGBM_NUM_THREADS'] = '1'
"""Quick test: one bootstrap resample for WNS"""
import joblib
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import r2_score

MODEL_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved")
DATA_PATH = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")

# Load & preprocess
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

# Load WNS models
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

mlp = MLP(18)  # X.shape[1] after preprocessing
mlp.load_state_dict(torch.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_mlp.pt", map_location='cpu')['model_state'])
mlp.eval()

with torch.no_grad():
    y_mlp = mlp(torch.FloatTensor(torch.from_numpy(pre.transform(pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")).astype('float32')))).numpy()

lgb_obj = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_wns_lgb.pkl")
lgb_model = lgb_obj['model'] if isinstance(lgb_obj, dict) else lgb_obj
y_lgb = lgb_model.predict(pre.transform(pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")))

y_ens = (y_lgb + y_mlp) / 2

df = pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")
df = df[df['suitable_for_regression']].copy()
y_true = np.clip(df['final_wns_ns'], -500, 100).values

from sklearn.metrics import r2_score
idx = np.random.choice(len(y_true), len(y_true), replace=True)
print("Single bootstrap R²:", r2_score(y_true[idx], y_ens[idx]))

