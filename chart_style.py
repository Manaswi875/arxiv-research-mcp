"""Shared matplotlib styling so every chart looks like part of the same dashboard
instead of matplotlib's defaults. White surfaces matching the dashboard's .card
background, DejaVu Sans (matplotlib's own bundled font - no new dependency),
top/right spines off, light gridlines below the bars."""

import matplotlib.pyplot as plt

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ACCENT = PALETTE[0]
OTHER_COLOR = "#898781"


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff", "savefig.facecolor": "#ffffff", "savefig.dpi": 150,
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b",
        "xtick.color": "#898781", "ytick.color": "#898781",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.8, "axes.axisbelow": True,
    })
