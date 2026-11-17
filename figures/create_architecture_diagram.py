#!/usr/bin/env python3
"""
Create architecture layers diagram for OpenRoad-GUI paper
Uses matplotlib to generate PDF diagram
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up the figure
fig, ax = plt.subplots(1, 1, figsize=(12, 9))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Color scheme
colors = {
    'gui': '#2E86DE',      # Blue
    'flow': '#F39C12',     # Orange
    'intel': '#27AE60',    # Green
    'data': '#E74C3C',     # Red
    'text': '#2C3E50',     # Dark blue-gray
    'light': '#ECF0F1',    # Light gray
    'arrow': '#7F8C8D',    # Gray
    'feedback': '#E74C3C'  # Red for feedback
}

# Layer definitions: (y_position, height, color, title, components)
layers = [
    {
        'y': 7.5, 'height': 1.8, 'color': colors['gui'],
        'title': 'GUI Layer (Tkinter)',
        'components': ['Project Tree', 'Pipeline Row', 'Log Viewer', 'AI Panels']
    },
    {
        'y': 5.2, 'height': 1.5, 'color': colors['flow'],
        'title': 'Flow Execution Layer',
        'components': ['FlowRunner (subprocess) → ORFS make targets']
    },
    {
        'y': 2.8, 'height': 1.8, 'color': colors['intel'],
        'title': 'Intelligence Layer',
        'components': [
            'Surrogate Models\n(LightGBM + MLP Ensemble)',
            'Failure Predictor\n(Calibrated LightGBM)',
            'Flow Optimizer\n(PPO RL Agent)'
        ]
    },
    {
        'y': 0.3, 'height': 1.5, 'color': colors['data'],
        'title': 'Data Layer',
        'components': ['Real ORFS Runs', 'Feature Engineering', 'Training Pipeline']
    }
]

def draw_layer(ax, layer, x_start=0.5, width=9):
    """Draw a layer with title and components"""
    y = layer['y']
    h = layer['height']
    color = layer['color']

    # Main layer box
    box = FancyBboxPatch(
        (x_start, y - h/2), width, h,
        boxstyle="round,pad=0.1,rounding_size=0.15",
        linewidth=2.5,
        edgecolor=color,
        facecolor=color + '15',  # 10% opacity
        zorder=1
    )
    ax.add_patch(box)

    # Title
    ax.text(0.5, y + h/2 + 0.15, layer['title'],
            fontsize=14, fontweight='bold', color=color,
            ha='center', va='bottom', zorder=2)

    # Components
    n_comp = len(layer['components'])
    comp_width = width / n_comp
    for i, comp in enumerate(layer['components']):
        cx = x_start + comp_width * i + comp_width / 2
        cy = y

        comp_box = FancyBboxPatch(
            (cx - comp_width/2 + 0.1, cy - h/2 + 0.15),
            comp_width - 0.2, h - 0.5,
            boxstyle="round,pad=0.05,rounding_size=0.08",
            linewidth=1.5,
            edgecolor=color,
            facecolor=color + '25',  # 15% opacity
            zorder=2
        )
        ax.add_patch(comp_box)

        ax.text(cx, cy, comp,
                fontsize=10, color=color,
                ha='center', va='center',
                wrap=True, zorder=3)

# Draw all layers
for layer in layers:
    draw_layer(ax, layer)

# Arrows between layers
arrow_props = dict(arrowstyle='->', color=colors['arrow'], lw=2, mutation_scale=20)

for i in range(len(layers) - 1):
    y1 = layers[i]['y'] - layers[i]['height']/2
    y2 = layers[i+1]['y'] + layers[i+1]['height']/2
    mid_y = (y1 + y2) / 2

    # Vertical arrow
    arrow = FancyArrowPatch(
        (5, y1), (5, y2),
        arrowstyle='->', color=colors['arrow'], lw=2,
        mutation_scale=25, shrinkA=5, shrinkB=5,
        connectionstyle="arc3,rad=0"
    )
    ax.add_patch(arrow)

# Feedback arrow (Data -> Intelligence)
feedback_arrow = FancyArrowPatch(
    (9.5, layers[-1]['y']), (9.5, layers[2]['y']),
    arrowstyle='->', color=colors['feedback'], lw=2.5,
    mutation_scale=25, shrinkA=5, shrinkB=5,
    connectionstyle="arc3,rad=-0.4"
)
ax.add_patch(feedback_arrow)
ax.text(9.7, (layers[-1]['y'] + layers[2]['y'])/2, 'Feedback',
        fontsize=10, fontweight='bold', color=colors['feedback'],
        ha='left', va='center', rotation=90)

# Internal arrows in Intelligence Layer
intel_layer = layers[2]
comp_width = 9 / 3
for i in range(2):
    x1 = 0.5 + comp_width * (i + 1) - 0.1
    x2 = 0.5 + comp_width * (i + 1) + 0.1
    y = intel_layer['y']
    arrow = FancyArrowPatch(
        (x1, y), (x2, y),
        arrowstyle='->', color=colors['arrow'], lw=1.5,
        mutation_scale=15, shrinkA=2, shrinkB=2,
        linestyle='dashed'
    )
    ax.add_patch(arrow)

# Internal arrows in Data Layer
data_layer = layers[-1]
comp_width = 9 / 3
for i in range(2):
    x1 = 0.5 + comp_width * (i + 1) - 0.1
    x2 = 0.5 + comp_width * (i + 1) + 0.1
    y = data_layer['y']
    arrow = FancyArrowPatch(
        (x1, y), (x2, y),
        arrowstyle='->', color=colors['arrow'], lw=1.5,
        mutation_scale=15, shrinkA=2, shrinkB=2
    )
    ax.add_patch(arrow)

# Title
ax.text(5, 9.5, 'OpenRoad-GUI Four-Layer Architecture',
        fontsize=18, fontweight='bold', color=colors['text'],
        ha='center', va='top')

# Legend
legend_elements = [
    mpatches.Patch(facecolor=colors['gui']+'30', edgecolor=colors['gui'],
                   label='GUI Layer', linewidth=2),
    mpatches.Patch(facecolor=colors['flow']+'30', edgecolor=colors['flow'],
                   label='Flow Execution', linewidth=2),
    mpatches.Patch(facecolor=colors['intel']+'30', edgecolor=colors['intel'],
                   label='Intelligence', linewidth=2),
    mpatches.Patch(facecolor=colors['data']+'30', edgecolor=colors['data'],
                   label='Data Layer', linewidth=2),
]
ax.legend(handles=legend_elements, loc='lower center',
          bbox_to_anchor=(0.5, -0.02), ncol=4, fontsize=11,
          frameon=True, fancybox=True, shadow=True)

# Save
plt.tight_layout()
plt.savefig('/Users/mihirmithani/Downloads/OpenRoad GUI/figures/architecture_layers.pdf',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('/Users/mihirmithani/Downloads/OpenRoad GUI/figures/architecture_layers.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print("Architecture diagram saved to figures/architecture_layers.pdf and .png")