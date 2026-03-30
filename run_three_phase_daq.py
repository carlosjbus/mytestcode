"""
Three-Phase DAQ Integration
===========================
Generates three-phase V/I waveforms with ThreePhaseSimulator and writes
them to NI-DAQ hardware via DAQmx.

Flow
----
1. ThreePhaseSimulator.build_waveforms()  →  per-phase voltage/current arrays
2. waveforms_to_datanp()                  →  flat channel-grouped float64 array
3. daq.datanp = <computed array>          →  inject into DAQmx before configure()
4. daq.configure()                        →  write to hardware

Channel order (GroupByChannel layout)
--------------------------------------
For each signal set in order:  V_A, V_B, V_C, I_A, I_B, I_C
Two signal sets → 12 channels total.
"""

import numpy as np

from plot_three_phase import ThreePhaseSimulator
from DAQC_python3_AI_modified import DAQmx


# ── DAQ hardware parameters ───────────────────────────────────────────────────

PHYS_CHAN      = "cDAQ5Mod1/ao0:2,cDAQ5Mod2/ao0:2,cDAQ5Mod4/ao0:5"
SAMP_RATE      = 64800.0    # samples / second
SAMPS_PER_CHAN = 1080       # samples per channel (one 60 Hz cycle)
N_CHANNELS     = 12         # 2 signal sets × (3V + 3I) channels

# ── Simulator parameters ──────────────────────────────────────────────────────

SIM_FREQUENCY  = 60
SIM_PF_ANGLE   = 30
SIM_CYCLES     = 1
SIM_NOISE_SEED = 42


# ── Signal-set configurations ────────────────────────────────────────────────

SIGNAL_SETS = [
    {
        "label": "Set 1",
        "amplitude_v": {"A": 4.1, "B": 4.1, "C": 4.1},
        "amplitude_i": {"A": 3,   "B": 3,   "C": 3},
        "enable_noise_v":     {"A": True,  "B": False, "C": False},
        "enable_noise_i":     {"A": False, "B": False, "C": False},
        "snr_db_v":           {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "snr_db_i":           {"A": 20.0,  "B": 20.0,  "C": 20.0},
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
        "offset_v":          {"A": 0.0, "B": 0.0, "C": 0.0},
        "offset_i":          {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_v":  {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_i":  {"A": 0.0, "B": 0.0, "C": 0.0},
    },
    {
        "label": "Set 2",
        "amplitude_v": {"A": 4.1, "B": 4.1, "C": 4.1},
        "amplitude_i": {"A": 3,   "B": 3,   "C": 3},
        "enable_noise_v":     {"A": False, "B": False, "C": False},
        "enable_noise_i":     {"A": False, "B": False, "C": False},
        "snr_db_v":           {"A": 20.0,  "B": 20.0,  "C": 20.0},
        "snr_db_i":           {"A": 20.0,  "B": 20.0,  "C": 20.0},
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
        "offset_v":          {"A": 0.0, "B": 0.0, "C": 0.0},
        "offset_i":          {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_v":  {"A": 0.0, "B": 0.0, "C": 0.0},
        "angular_offset_i":  {"A": 0.0, "B": 0.0, "C": 0.0},
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def waveforms_to_datanp(signal_sets):
    """Flatten build_waveforms() output into a channel-grouped 1-D float64 array.

    Channel order per signal set: V_A, V_B, V_C, I_A, I_B, I_C.
    Multiple signal sets are appended in list order.

    Parameters
    ----------
    signal_sets : list[dict]
        Return value of ThreePhaseSimulator.build_waveforms().

    Returns
    -------
    numpy.ndarray, dtype=float64
        Flat array of shape (n_sets * 6 * samps_per_chan,) ready for
        DAQmxWriteAnalogF64 with DAQmx_Val_GroupByChannel layout.
    """
    channels = []
    for s in signal_sets:
        for ph in ("A", "B", "C"):
            channels.append(s["voltages"][ph])
        for ph in ("A", "B", "C"):
            channels.append(s["currents"][ph])
    return np.concatenate(channels).astype(np.float64, copy=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Initialize ThreePhaseSimulator and build waveforms ─────────────────
    sim = ThreePhaseSimulator(
        frequency=SIM_FREQUENCY,
        power_factor_angle=SIM_PF_ANGLE,
        cycles=SIM_CYCLES,
        samples=SAMPS_PER_CHAN,
        noise_seed=SIM_NOISE_SEED,
        signal_sets=SIGNAL_SETS,
    )
    waveform_data = sim.build_waveforms()
    sim.plot(waveform_data)

    # ── 2. Initialize DAQmx with sampPerChan and sampleRate ───────────────────
    daq = DAQmx(samp_per_chan=SAMPS_PER_CHAN, sample_rate=SAMP_RATE)

    # ── 3. Configure DAQ channel / timing parameters ──────────────────────────
    #    Amplitude/phase/offset lists are placeholders — waveform data comes
    #    from build_waveforms() and is injected in step 4.
    placeholder = [0.0] * N_CHANNELS
    daq.setup_daq_parameters(
        physChan=PHYS_CHAN,
        nchannels=N_CHANNELS,
        sampleRate=SAMP_RATE,
        numSampsPerChannel=SAMPS_PER_CHAN,
        amplitudes=placeholder,
        phaseOffsets=placeholder,
        dcOffsets=placeholder,
        harmonicAmplitudes=placeholder,
        harmonicComponents=placeholder,
        system_freq=SIM_FREQUENCY,
    )

    # ── 4. Replace self.datanp with computed waveforms and write to hardware ──
    daq.datanp = waveforms_to_datanp(waveform_data)
    print(f"\nwaveforms_to_datanp: shape={daq.datanp.shape}, dtype={daq.datanp.dtype}")
    daq.configure()


if __name__ == "__main__":
    main()
