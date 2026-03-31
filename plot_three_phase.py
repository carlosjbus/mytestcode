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


class ThreePhaseSimulator:
    """Simulate and plot three-phase voltage/current waveforms.

    Parameters
    ----------
    frequency : float
        System frequency in Hz.
    power_factor_angle : float
        Degrees that current lags voltage.
    duration : float
        Duration of the waveform in seconds.
    sample_rate : float
        Sample rate in samples per second.
    noise_seed : int | None
        Random seed for reproducibility (``None`` for random).
    signal_sets : list[dict]
        Per-set noise, harmonic, offset, angular-offset, and per-phase
        amplitude configuration.  Each dict **must** contain
        ``"amplitude_v"`` and ``"amplitude_i"`` keys with per-phase dicts
        ``{"A": float, "B": float, "C": float}``.
    """

    PHASE_OFFSETS_DEG = {"A": 0, "B": -120, "C": -240}
    PHASE_COLORS      = {"A": "#e74c3c", "B": "#2ecc71", "C": "#3498db"}

    def __init__(self, frequency=60, power_factor_angle=30, duration=1.0,
                 sample_rate=64800.0, noise_seed=42, signal_sets=None):
        self.frequency = frequency
        self.power_factor_angle = power_factor_angle
        self.duration = duration
        self.sample_rate = sample_rate
        self.signal_sets = signal_sets or []

        # Derived quantities
        self.t = np.arange(0, self.duration, 1 / self.sample_rate, dtype=np.float64)
        self.t_ms = self.t * 1e3
        self.omega = np.float64(2 * np.pi * self.frequency)
        self.pf_rad = np.float64(np.deg2rad(self.power_factor_angle))
        self.rng = np.random.default_rng(noise_seed)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def snr_db_to_noise_std(amplitude, snr_db):
        """Convert an SNR in dB to a noise standard deviation.

        Parameters
        ----------
        amplitude : float
            Peak amplitude of the sinusoidal signal.
        snr_db : float
            Desired signal-to-noise ratio in dB.

        Returns
        -------
        numpy.float64
            Standard deviation of the Gaussian noise to add.
        """
        signal_rms = amplitude / np.sqrt(2)
        return np.float64(signal_rms / (10 ** (snr_db / 20.0)))

    def waveform(self, amplitude, offset_deg, extra_lag_rad=0.0,
                 harmonics=None, dc_offset=0.0, extra_offset_deg=0.0):
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
            Mapping ``{n: (rel_amplitude, phase_deg)}`` for each harmonic
            order *n*.
        dc_offset : float
            DC offset added to the waveform.
        extra_offset_deg : float
            Additional angular offset in degrees added on top of *offset_deg*.
        """
        theta = np.float64(np.deg2rad(offset_deg) + np.deg2rad(extra_offset_deg))
        amp = np.float64(amplitude)
        lag = np.float64(extra_lag_rad)
        sig = amp * np.sin(self.omega * self.t + theta - lag) + np.float64(dc_offset)
        if harmonics:
            for n, (rel_amp, h_phase_deg) in harmonics.items():
                h_phase_rad = np.deg2rad(h_phase_deg)
                sig += amp * np.float64(rel_amp) * np.sin(
                    n * self.omega * self.t + n * theta - n * lag + h_phase_rad
                )
        return sig.astype(np.float64, copy=False)

    def add_noise(self, signal, std):
        """Add Gaussian white noise with the given standard deviation."""
        if std == 0.0:
            return signal.astype(np.float64, copy=True)
        return (signal + self.rng.normal(loc=0.0, scale=std, size=signal.shape)).astype(
            np.float64, copy=False)

    # ── Waveform generation ───────────────────────────────────────────────────

    def build_waveforms(self):
        """Compute clean and noisy voltage/current waveforms for every signal set.

        Returns
        -------
        list[dict]
            One dict per signal set with the original config keys plus computed
            ``noise_std_v``, ``noise_std_i``, ``voltages``, and ``currents``.
        """
        results = []
        for s in self.signal_sets:
            result = dict(s)

            # Per-phase amplitudes (required in each signal set)
            amp_v = {ph: np.float64(result["amplitude_v"][ph])
                     for ph in ("A", "B", "C")}
            amp_i = {ph: np.float64(result["amplitude_i"][ph])
                     for ph in ("A", "B", "C")}

            result["noise_std_v"] = {}
            result["noise_std_i"] = {}
            for ph in ("A", "B", "C"):
                if result["enable_noise_v"][ph]:
                    result["noise_std_v"][ph] = self.snr_db_to_noise_std(
                        amp_v[ph], result["snr_db_v"][ph])
                    print(f"{result['label']} Phase {ph}: "
                          f"SNR_V = {result['snr_db_v'][ph]} dB "
                          f"=> σ_V = {result['noise_std_v'][ph]:.4f} V")
                else:
                    result["noise_std_v"][ph] = 0.0
                    print(f"{result['label']} Phase {ph}: voltage noise disabled")

                if result["enable_noise_i"][ph]:
                    result["noise_std_i"][ph] = self.snr_db_to_noise_std(
                        amp_i[ph], result["snr_db_i"][ph])
                    print(f"{result['label']} Phase {ph}: "
                          f"SNR_I = {result['snr_db_i'][ph]} dB "
                          f"=> σ_I = {result['noise_std_i'][ph]:.4f} A")
                else:
                    result["noise_std_i"][ph] = 0.0
                    print(f"{result['label']} Phase {ph}: current noise disabled")

            harm_v = {ph: result["harmonics_v"][ph]
                      if result["enable_harmonics_v"][ph] else None
                      for ph in ("A", "B", "C")}
            harm_i = {ph: result["harmonics_i"][ph]
                      if result["enable_harmonics_i"][ph] else None
                      for ph in ("A", "B", "C")}

            result["voltages"] = {
                ph: self.add_noise(
                    self.waveform(amp_v[ph], off,
                                  harmonics=harm_v[ph],
                                  dc_offset=result["offset_v"][ph],
                                  extra_offset_deg=result["angular_offset_v"][ph]),
                    result["noise_std_v"][ph],
                )
                for ph, off in self.PHASE_OFFSETS_DEG.items()
            }
            result["currents"] = {
                ph: self.add_noise(
                    self.waveform(amp_i[ph], off, self.pf_rad,
                                  harmonics=harm_i[ph],
                                  dc_offset=result["offset_i"][ph],
                                  extra_offset_deg=result["angular_offset_i"][ph]),
                    result["noise_std_i"][ph],
                )
                for ph, off in self.PHASE_OFFSETS_DEG.items()
            }
            results.append(result)

        return results

    # ── Plotting ──────────────────────────────────────────────────────────────

    def plot(self, signal_sets):
        """Create a multi-panel figure of three-phase voltage and current waveforms.

        Parameters
        ----------
        signal_sets : list[dict]
            Waveform data returned by :meth:`build_waveforms`.
        """
        n_sets = len(signal_sets)
        fig = plt.figure(figsize=(7 * n_sets, 10))
        fig.suptitle(
            f"Three-Phase Voltage & Current  |  "
            f"f = {self.frequency} Hz  |  "
            f"PF angle = {self.power_factor_angle}°",
            fontsize=11, fontweight="bold"
        )

        gs = gridspec.GridSpec(3, n_sets, hspace=0.55, wspace=0.35)

        for col, s in enumerate(signal_sets):
            # Per-phase amplitudes (required in each signal set)
            amp_v = {ph: s["amplitude_v"][ph] for ph in ("A", "B", "C")}
            amp_i = {ph: s["amplitude_i"][ph] for ph in ("A", "B", "C")}

            for idx, phase in enumerate(("A", "B", "C")):
                ax = fig.add_subplot(gs[idx, col])
                color = self.PHASE_COLORS[phase]
                offset = self.PHASE_OFFSETS_DEG[phase]
                vp = amp_v[phase]
                ip = amp_i[phase]

                noise_v_tag = (f"SNR {s['snr_db_v'][phase]} dB"
                               if s["enable_noise_v"][phase] else "no noise")
                noise_i_tag = (f"SNR {s['snr_db_i'][phase]} dB"
                               if s["enable_noise_i"][phase] else "no noise")
                harm_v_tag = (f"H{list(s['harmonics_v'][phase].keys())}"
                              if s["enable_harmonics_v"][phase]
                              and s["harmonics_v"][phase] else "")
                harm_i_tag = (f"H{list(s['harmonics_i'][phase].keys())}"
                              if s["enable_harmonics_i"][phase]
                              and s["harmonics_i"][phase] else "")

                ax.plot(self.t_ms, s["voltages"][phase],
                        color=color, linewidth=1.5, zorder=2,
                        label=f"Phase {phase} V  ({offset}°  {noise_v_tag}  {harm_v_tag})")

                ax.plot(self.t_ms, s["currents"][phase],
                        color=color, linewidth=1.5, linestyle="--", zorder=2,
                        label=(f"Phase {phase} I  (lag {self.power_factor_angle}°"
                               f"  {noise_i_tag}  {harm_i_tag})"))

                ax.fill_between(self.t_ms, s["voltages"][phase],
                                s["currents"][phase], alpha=0.08, color=color)

                ax.axhline(0, color="gray", linewidth=0.7, linestyle=":")
                ax.set_ylabel("Amplitude", fontsize=9)
                ax.set_title(f"{s['label']} — Phase {phase}  "
                             f"(Vp={vp} V, Ip={ip} A)",
                             fontsize=10, fontweight="bold")
                ax.legend(loc="upper right", fontsize=8)
                ax.grid(True, alpha=0.35)
                ax.set_xlim(0, 1000 / self.frequency)

                ax_right = ax.twinx()
                ax_right.set_ylim(ax.get_ylim())
                ax_right.set_yticks([vp, -vp, ip, -ip])
                ax_right.set_yticklabels(
                    [f"{vp} V", f"−{vp} V",
                     f"{ip} A", f"−{ip} A"],
                    fontsize=7
                )

                if idx == 2:
                    ax.set_xlabel("Time (ms)", fontsize=10)

        plt.savefig("three_phase_plot.png", dpi=150, bbox_inches="tight")
        print("Plot saved to three_phase_plot.png")
        plt.show()

    def run(self):
        """Build waveforms and plot them."""
        waveform_data = self.build_waveforms()
        self.plot(waveform_data)


# ── Default signal-set configurations ─────────────────────────────────────────

DEFAULT_SIGNAL_SETS = [
    {
        "label": "Set 1",
        "amplitude_v": {"A": 4.1, "B": 4.1, "C": 4.1},
        "amplitude_i": {"A": 3,   "B": 3,   "C": 3},
        "enable_noise_v": {"A": True,  "B": False, "C": False},
        "enable_noise_i": {"A": False, "B": False, "C": False},
        "snr_db_v":       {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "snr_db_i":       {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "enable_harmonics_v": {"A": True,  "B": False, "C": False},
        "enable_harmonics_i": {"A": False, "B": False, "C": False},
        "harmonics_v": {
            "A": {3: (0.05, 0), 5: (0.03, 0)},
            "B": {3: (0.05, 0), 5: (0.03, 0)},
            "C": {3: (0.05, 0), 5: (0.03, 0)},
        },
        "harmonics_i": {
            "A": {3: (0.15, 0), 5: (0.10, 30), 7: (0.05, 60)},
            "B": {3: (0.15, 0), 5: (0.10, 30), 7: (0.05, 60)},
            "C": {3: (0.15, 0), 5: (0.10, 30), 7: (0.05, 60)},
        },
        "offset_v": {"A": 0.0, "B": 0.0, "C": 0.0},
        "offset_i": {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_v": {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_i": {"A": 0.0, "B": 0.0, "C": 0.0},
    },
    {
        "label": "Set 2",
        "amplitude_v": {"A": 4.1, "B": 4.1, "C": 4.1},
        "amplitude_i": {"A": 3,   "B": 3,   "C": 3},
        "enable_noise_v": {"A": False, "B": False, "C": False},
        "enable_noise_i": {"A": False, "B": False, "C": False},
        "snr_db_v":       {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "snr_db_i":       {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "enable_harmonics_v": {"A": False, "B": False, "C": False},
        "enable_harmonics_i": {"A": False, "B": False, "C": False},
        "harmonics_v": {
            "A": {3: (0.05, 0), 5: (0.03, 0)},
            "B": {3: (0.05, 0), 5: (0.03, 0)},
            "C": {3: (0.05, 0), 5: (0.03, 0)},
        },
        "harmonics_i": {
            "A": {3: (0.15, 0), 5: (0.10, 30), 7: (0.05, 60)},
            "B": {3: (0.15, 0), 5: (0.10, 30), 7: (0.05, 60)},
            "C": {3: (0.15, 0), 5: (0.10, 30), 7: (0.05, 60)},
        },
        "offset_v": {"A": 0.0, "B": 0.0, "C": 0.0},
        "offset_i": {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_v": {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_i": {"A": 0.0, "B": 0.0, "C": 0.0},
    },
]


if __name__ == "__main__":
    sim = ThreePhaseSimulator(
        frequency=60,
        power_factor_angle=30,
        duration=1.0,
        sample_rate=64800.0,
        noise_seed=42,
        signal_sets=DEFAULT_SIGNAL_SETS,
    )
    sim.run()