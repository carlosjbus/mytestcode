"""
Three-Phase Voltage and Current Plotter
Plots voltage and current waveforms with phase offsets for phases A, B, and C.

Gaussian white noise level is specified in decibels relative to the signal
RMS power (SNR in dB).  A higher SNR_DB means less noise.

  SNR (dB) = 10 * log10( P_signal / P_noise )
  => noise_std = signal_rms / 10^(SNR_dB / 20)

For a pure sine of amplitude A:  RMS = A / sqrt(2)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ── Simulation parameters ─────────────────────────────────────────────────────
FREQUENCY = 60          # Hz
AMPLITUDE_V = 4.1       # Peak voltage  (V)
AMPLITUDE_I = 3      # Peak current  (A)
POWER_FACTOR_ANGLE = 30 # Degrees current lags voltage (power-factor angle)
CYCLES = 1              # Number of cycles to display
SAMPLES = 1000         # Points per plot

NOISE_SEED = 42           # Random seed for reproducibility (set to None for random)

# ── Signal sets ───────────────────────────────────────────────────────────────
# Each entry is an independent trio of A / B / C waveforms with its own
# per-phase noise and harmonic configuration.  Add more dicts to create
# additional columns in the plot.
SIGNAL_SETS = [
    {
        "label": "Set 1",
        # Per-phase noise toggle and SNR (dB)
        "enable_noise": {"A": True,  "B": False, "C": False},
        "snr_db_v":     {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "snr_db_i":     {"A": 20.0,  "B": 20.0,  "C": 20.0},
        # Per-phase harmonic toggle and content
        # Each phase maps harmonic order n to (relative_amplitude, phase_deg)
        "enable_harmonics": {"A": True, "B": False, "C": False},
        "harmonics_v": {
            "A": {3: (0.05,  0), 5: (0.03,  0)},
            "B": {3: (0.05,  0), 5: (0.03,  0)},
            "C": {3: (0.05,  0), 5: (0.03,  0)},
        },
        "harmonics_i": {
            "A": {3: (0.15,  0), 5: (0.10, 30), 7: (0.05, 60)},
            "B": {3: (0.15,  0), 5: (0.10, 30), 7: (0.05, 60)},
            "C": {3: (0.15,  0), 5: (0.10, 30), 7: (0.05, 60)},
        },
    },
    {
        "label": "Set 2",
        "enable_noise": {"A": False,  "B": False, "C": False},
        "snr_db_v":     {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "snr_db_i":     {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "enable_harmonics": {"A": False, "B": False, "C": False},
        "harmonics_v": {
            "A": {3: (0.05,  0), 5: (0.03,  0)},
            "B": {3: (0.05,  0), 5: (0.03,  0)},
            "C": {3: (0.05,  0), 5: (0.03,  0)},
        },
        "harmonics_i": {
            "A": {3: (0.15,  0), 5: (0.10, 30), 7: (0.05, 60)},
            "B": {3: (0.15,  0), 5: (0.10, 30), 7: (0.05, 60)},
            "C": {3: (0.15,  0), 5: (0.10, 30), 7: (0.05, 60)},
        },
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def snr_db_to_noise_std(amplitude, snr_db):
    """
    Convert an SNR expressed in dB to a noise standard deviation.

    Parameters
    ----------
    amplitude : float
        Peak amplitude of the sinusoidal signal.
    snr_db : float
        Desired signal-to-noise ratio in dB.
            SNR_dB = 20 * log10(A_rms / sigma_noise)
        =>  sigma_noise = A_rms / 10^(SNR_DBL / 20)

    Returns
    -------
    float
        Standard deviation of the Gaussian noise to add.
    """
    signal_rms = amplitude / np.sqrt(2)          # RMS of a pure sine
    noise_std  = signal_rms / (10 ** (snr_db / 20.0))
    return noise_std


# ── Time axis
T = 1 / FREQUENCY
t = np.linspace(0, CYCLES * T, SAMPLES)
omega = 2 * np.pi * FREQUENCY   # Angular frequency (rad/s)

rng = np.random.default_rng(NOISE_SEED)


# ── Phase offsets ─────────────────────────────────────────────────────────────
phase_offsets_deg = {"A": 0, "B": -120, "C": -240}
phase_colors      = {"A": "#e74c3c",   # red
                     "B": "#2ecc71",   # green
                     "C": "#3498db"}   # blue
pf_rad = np.deg2rad(POWER_FACTOR_ANGLE)


def waveform(amplitude, offset_deg, extra_lag_rad=0.0, harmonics=None):
    """Return a sinusoidal waveform with optional harmonic content.

    Parameters
    ----------
    amplitude : float
        Peak amplitude of the fundamental.
    offset_deg : float
        Phase offset of the fundamental in degrees.
    extra_lag_rad : float
        Additional phase lag in radians (e.g. power-factor angle).
    harmonics : dict | None
        Mapping ``{n: (rel_amplitude, phase_deg)}`` for each harmonic order *n*.
    """
    theta = np.deg2rad(offset_deg)
    sig = amplitude * np.sin(omega * t + theta - extra_lag_rad)
    if harmonics:
        for n, (rel_amp, h_phase_deg) in harmonics.items():
            h_phase_rad = np.deg2rad(h_phase_deg)
            sig += amplitude * rel_amp * np.sin(
                n * omega * t + n * theta - n * extra_lag_rad + h_phase_rad
            )
    return sig


def add_noise(signal, std):
    """Add Gaussian white noise with the given standard deviation."""
    if std == 0.0:
        return signal.copy()
    return signal + rng.normal(loc=0.0, scale=std, size=signal.shape)

# ── Build waveforms (per set) ─────────────────────────────────────────────────
t_ms = t * 1e3   # convert to milliseconds for the x-axis

for s in SIGNAL_SETS:
    s["noise_std_v"] = {}
    s["noise_std_i"] = {}
    for ph in ("A", "B", "C"):
        if s["enable_noise"][ph]:
            s["noise_std_v"][ph] = snr_db_to_noise_std(AMPLITUDE_V, s["snr_db_v"][ph])
            s["noise_std_i"][ph] = snr_db_to_noise_std(AMPLITUDE_I, s["snr_db_i"][ph])
            print(f"{s['label']} Phase {ph}: "
                  f"SNR_V = {s['snr_db_v'][ph]} dB => σ_V = {s['noise_std_v'][ph]:.4f} V, "
                  f"SNR_I = {s['snr_db_i'][ph]} dB => σ_I = {s['noise_std_i'][ph]:.4f} A")
        else:
            s["noise_std_v"][ph] = 0.0
            s["noise_std_i"][ph] = 0.0
            print(f"{s['label']} Phase {ph}: noise disabled")

    harm_v = {ph: s["harmonics_v"][ph] if s["enable_harmonics"][ph] else None
              for ph in ("A", "B", "C")}
    harm_i = {ph: s["harmonics_i"][ph] if s["enable_harmonics"][ph] else None
              for ph in ("A", "B", "C")}

    s["voltages_clean"] = {ph: waveform(AMPLITUDE_V, off, harmonics=harm_v[ph])
                           for ph, off in phase_offsets_deg.items()}
    s["currents_clean"] = {ph: waveform(AMPLITUDE_I, off, pf_rad, harmonics=harm_i[ph])
                           for ph, off in phase_offsets_deg.items()}
    s["voltages"] = {ph: add_noise(s["voltages_clean"][ph], s["noise_std_v"][ph])
                     for ph in phase_offsets_deg}
    s["currents"] = {ph: add_noise(s["currents_clean"][ph], s["noise_std_i"][ph])
                     for ph in phase_offsets_deg}


# ── Plot ──────────────────────────────────────────────────────────────────────
n_sets = len(SIGNAL_SETS)
fig = plt.figure(figsize=(7 * n_sets, 10))
fig.suptitle(
    f"Three-Phase Voltage & Current  |  "
    f"f = {FREQUENCY} Hz  |  "
    f"PF angle = {POWER_FACTOR_ANGLE}°  |  "
    f"Vp = {AMPLITUDE_V} V  |  Ip = {AMPLITUDE_I} A",
    fontsize=11, fontweight="bold"
)

gs = gridspec.GridSpec(3, n_sets, hspace=0.55, wspace=0.35)

for col, s in enumerate(SIGNAL_SETS):
    for idx, phase in enumerate(("A", "B", "C")):
        ax = fig.add_subplot(gs[idx, col])
        color = phase_colors[phase]
        offset = phase_offsets_deg[phase]

        noise_v_tag = f"SNR {s['snr_db_v'][phase]} dB" if s["enable_noise"][phase] else "no noise"
        noise_i_tag = f"SNR {s['snr_db_i'][phase]} dB" if s["enable_noise"][phase] else "no noise"
        harm_v_tag  = (f"H{list(s['harmonics_v'][phase].keys())}"
                       if s["enable_harmonics"][phase] and s["harmonics_v"][phase] else "")
        harm_i_tag  = (f"H{list(s['harmonics_i'][phase].keys())}"
                       if s["enable_harmonics"][phase] and s["harmonics_i"][phase] else "")

        # Clean reference (faint) behind noisy waveform
        ax.plot(t_ms, s["voltages_clean"][phase],
                color=color, linewidth=1.0, alpha=0.25, zorder=1)
        ax.plot(t_ms, s["voltages"][phase],
                color=color, linewidth=1.5, zorder=2,
                label=f"Phase {phase} V  ({offset}°  {noise_v_tag}  {harm_v_tag})")

        ax.plot(t_ms, s["currents_clean"][phase],
                color=color, linewidth=1.0, alpha=0.25, linestyle="--", zorder=1)
        ax.plot(t_ms, s["currents"][phase],
                color=color, linewidth=1.5, linestyle="--", zorder=2,
                label=f"Phase {phase} I  (lag {POWER_FACTOR_ANGLE}°  {noise_i_tag}  {harm_i_tag})")

        # Shade between noisy voltage and current
        ax.fill_between(t_ms, s["voltages"][phase], s["currents"][phase],
                        alpha=0.08, color=color)

        ax.axhline(0, color="gray", linewidth=0.7, linestyle=":")
        ax.set_ylabel("Amplitude", fontsize=9)
        ax.set_title(f"{s['label']} — Phase {phase}", fontsize=10, fontweight="bold")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.35)

        ax_right = ax.twinx()
        ax_right.set_ylim(ax.get_ylim())
        ax_right.set_yticks([AMPLITUDE_V, -AMPLITUDE_V, AMPLITUDE_I, -AMPLITUDE_I])
        ax_right.set_yticklabels(
            [f"{AMPLITUDE_V} V", f"−{AMPLITUDE_V} V",
             f"{AMPLITUDE_I} A", f"−{AMPLITUDE_I} A"],
            fontsize=7
        )

        if idx == 2:
            ax.set_xlabel("Time (ms)", fontsize=10)

plt.savefig("three_phase_plot.png", dpi=150, bbox_inches="tight")
print("Plot saved to three_phase_plot.png")
plt.show()