# AI-Assisted EDA: Layout Diagram

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  (#) AI-Assisted EDA                                                                      [ Light ]  [ Help ]│
│      OpenROAD GUI for RTL-to-GDSII Flow                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌─ Project ──────────────┐ ┌─ Design Flow (RTL -> GDSII) ─────────────────┐ ┌─ AI Assistant ───────────────────┐
│             [ Refresh ]│ │ Design: alu_4bit   Platform: asap7           │ │ How can I help you with          │
│ ┌─ File Tree ────────┐ │ │ Config: ./designs/asap7/alu_4bit/config.mk   │ │ your design today?               │
│ │v flow              │ │ │ [ Stop ]   Ready          [ Run Full Flow ]  │ │                                  │
│ │ v results (asap7)/ │ │ │                                              │ │ [ Suggest optimal floorplan ]    │
│ │  v base/           │ │ │  (o)---(o)---(o)---(o)---(o)---(o)           │ │ [ Predict PPA for design    ]    │
│ │   1_2_yosys.sdc    │ │ │ Synth Floor Place  CTS  Route GDSII          │ │ [ Recommend better config   ]    │
│ │   1_2_yosys.v      │ │ └──────────────────────────────────────────────┘ │ [ Explain STA violations    ]    │
│ │   1_synth.odb      │ │ ┌─ Layout Viewer ──────────────────────────────┐ │ [ Help fix routing congest. ]    │
│ │   1_synth.sdc      │ │ │ File Preview                                 │ │ [ Generate TCL script       ]    │
│ │   2_x_floorplan... │ │ │ [ Text ] [ Layout ]                          │ │                                  │
│ │   3_x_place...     │ │ │ ┌──────────────────────────────────────────┐ │ │ [Type your question...][Send>]   │
│ │   ...              │ │ │ │                                          │ │ │ [ Clear Chat ]                   │
│ └────────────────────┘ │ │ │                                          │ │ └──────────────────────────────────┘
│     [ New Design ]     │ │ │                                          │ │ ┌─ PPA Analysis (AI Prediction) ───┐
│    [ Open Folder ]     │ │ │                                          │ │ │ Metric     Pred.  Actual Diff(%) │
│ ┌─ (empty area) ─────┐ │ │ └──────────────────────────────────────────┘ │ │ Power       --     --     --     │
│ │                    │ │ └──────────────────────────────────────────────┘ │ Perf (WNS)  --     --     --     │
│ │                    │ │ ┌─ Terminal / Flow Log ────────────────────────┐ │ Area        --     --     --     │
│ │                    │ │ │ Flow Log         [ Export Log... ] [ Clear ] │ └──────────────────────────────────┘
│ │                    │ │ │ [ Flow Log ] [ Terminal ]                    │ ┌─ Optimization Suggestions ───────┐
│ │                    │ │ │ ┌──────────────────────────────────────────┐ │ │ No suggestions yet.              │
│ │                    │ │ │ │ Ready - ORFS: /Users/.../OpenROAD-flow...│ │ │          [ Apply Suggestion ]    │
│ └────────────────────┘ │ │ │ Active design: asap7/alu_4bit            │ │ └──────────────────────────────────┘
└────────────────────────┘ │ │ GDS: 6_final.gds (found)                 │ │ ┌─ Reports ────────────────────────┐
                           │ └──────────────────────────────────────────┘ │ │ [Timing]  [Power]   [Area]       │
                           └──────────────────────────────────────────────┘ │ [ DRC ]   [ LVS ]   [Gen GDSII]  │
                           ┌─ Flow Progress ──────┐┌─ Quick Metrics ──────┐ └──────────────────────────────────┘
                           │ Ready                ││ WNS  TNS  Area Power │                                     
                           │ [##                ] ││  --   --   --    --  │                                     
                           │ 0%                   ││  ns   ns  um^2  mW   │                                     
                           └──────────────────────┘│ DRC: --              │                                     
                                                   └──────────────────────┘                                     
```
