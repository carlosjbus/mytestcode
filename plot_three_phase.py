"""
Three-Phase Voltage and Current Plotter
Plots voltage and current waveforms with phase offsets for phases A, B, and C.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ── Simulation parameters ────────────────────────────────────────────────────
FREQUENCY = 60          # Hz
AMPLITUDE_V = 120       # Peak voltage  (V)
AMPLITUDE_I = 10        # Peak current  (A)
POWER_FACTOR_ANGLE = 30 # Degrees current lags voltage (power-factor angle)
CYCLES = 2              # Number of cycles to display
SAMPLES = 1000          # Points per plot


# ── Time axis ────────────────────────────────────────────────────────────────
T = 1 / FREQUENCY
t = np.linspace(0, CYCLES * T, SAMPLES)
omega = 2 * np.pi * FREQUENCY   # Angular frequency (rad/s)


# ── Phase offsets (degrees → radians) ───────────────────────────────���────────
phase_offsets_deg = {"A": 0, "B": -120, "C": -240}
phase_colors      = {"A": "#e74c3c",   # red
                     "B": "#2ecc71",   # green
                     "C": "#3498db"}   # blue
pf_rad = np.deg2rad(POWER_FACTOR_ANGLE)


def waveform(amplitude, offset_deg, extra_lag_rad=0.0):
    """Return a sinusoidal waveform array."""
    theta = np.deg2rad(offset_deg)
    return amplitude * np.sin(omega * t + theta - extra_lag_rad)


# ── Build waveforms ───────────────────────────────────────────────────────────
voltages  = {ph: waveform(AMPLITUDE_V, off)            for ph, off in phase_offsets_deg.items()}
currents  = {ph: waveform(AMPLITUDE_I, off, pf_rad)    for ph, off in phase_offsets_deg.items()}

t_ms = t * 1e3   # convert to milliseconds for the x-axis


# ── Plot ──────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 10))
fig.suptitle(
    f"Three-Phase Voltage & Current  |  "
    f"f = {FREQUENCY} Hz  |  "
    f"PF angle = {POWER_FACTOR_ANGLE}°  |  "
    f"Vp = {AMPLITUDE_V} V  |  Ip = {AMPLITUDE_I} A",
    fontsize=13, fontweight="bold"
)

gs = gridspec.GridSpec(3, 1, hspace=0.55)

for idx, phase in enumerate(("A", "B", "C")):
    ax = fig.add_subplot(gs[idx])
    color = phase_colors[phase]
    offset = phase_offsets_deg[phase]

    ax.plot(t_ms, voltages[phase],
            color=color, linewidth=2,
            label=f"Phase {phase} Voltage  (offset {offset}°)")
    ax.plot(t_ms, currents[phase],
            color=color, linewidth=2, linestyle="--",
            label=f"Phase {phase} Current  (lag {POWER_FACTOR_ANGLE}°)")

    # Shade the region between voltage and current
    ax.fill_between(t_ms, voltages[phase], currents[phase],
                    alpha=0.08, color=color)

    # Zero line
    ax.axhline(0, color="gray", linewidth=0.7, linestyle=":")

    ax.set_ylabel("Amplitude", fontsize=9)
    ax.set_title(f"Phase {phase}", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.35)

    # Dual y-axis labels
    ax_right = ax.twinx()
    ax_right.set_ylim(ax.get_ylim())
    ax_right.set_yticks([AMPLITUDE_V, -AMPLITUDE_V, AMPLITUDE_I, -AMPLITUDE_I])
    ax_right.set_yticklabels(
        [f"{AMPLITUDE_V} V", f"−{AMPLITUDE_V} V",
         f"{AMPLITUDE_I} A", f"−{AMPLITUDE_I} A"],
        fontsize=7
    )

ax.set_xlabel("Time (ms)", fontsize=10)   # label only on bottom subplot

plt.savefig("three_phase_plot.png", dpi=150, bbox_inches="tight")
print("Plot saved to three_phase_plot.png")
plt.show()