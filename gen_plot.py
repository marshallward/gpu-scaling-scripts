#!/usr/bin/env python3

import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Read files

platforms = ('cpu', 'gpu',)
#platforms = ('gpu',)

regions = [
    '(Ocean Coriolis & mom advection)',
    '(Ocean pressure force)',
    '(Ocean vertical viscosity)',
    '(Ocean horizontal viscosity)',
    '(Ocean continuity equation)',
    '(Ocean barotropic mode stepping)',
]

plotcolor = {
    'gpu': 'orange',
    'cpu': 'blue',
}

run_files = {}
run_files['cpu'] = [run for run in os.listdir() if run.startswith('cpu_')]
run_files['gpu'] = [run for run in os.listdir() if run.startswith('gpu_')]

stats = {}

for expt in platforms:
    data_files = run_files[expt]

    # NOTE: File is `(platform, resolution): region: timing`
    #   We invert to `platform: region: resolution: timing`
    #   But we may want `platform: region: timing: resolution`

    for runfile in data_files:
        resolution = runfile.split('_')[1].split('.')[0].lstrip('0')

        metrics = {}
        with open(runfile) as stats_file:
            # Extract headers from first line
            # TODO: Allow full stdout as input
            header = stats_file.readline()
            keys = header.split()

            for line in stats_file:
                if line.strip().startswith('MPP_STACK high water mark'):
                    continue

                rec = line.rsplit(maxsplit=len(keys))

                clk = rec[0]
                try:
                    metrics[clk][resolution] = {}
                except KeyError:
                    metrics[clk] = {}
                    metrics[clk][resolution] = {}

                for stat, value in zip(keys, rec[1:]):
                    metrics[clk][resolution][stat] = float(value)

        # Poor man's deepupdate()
        # Assumes that all levels exist if `expt` exists.
        try:
            for reg in metrics:
                stats[expt][reg].update(metrics[reg])
        except KeyError:
            stats[expt] = metrics

# Plot results
fig, axes = plt.subplots(2, 3, figsize=(12,8))

fig.suptitle('Runtime per step for MOM6 modules')

# Denote the CPU core limit
for ax in axes.flat:
    ax.axvline(64, linestyle="--")

for expt in platforms:
    for reg, ax in zip(regions, axes.flat):

        nx_keys = stats[expt][reg].keys()
        nx = [int(k.rstrip('x')) for k in nx_keys]

        tmin = np.array([stats[expt][reg][nx]['tmin'] for nx in nx_keys])
        tmax = np.array([stats[expt][reg][nx]['tmax'] for nx in nx_keys])
        tavg = np.array([stats[expt][reg][nx]['tavg'] for nx in nx_keys])

        hits = np.array([stats[expt][reg][nx]['hits'] for nx in nx_keys])

        ax.set_title(reg)

        # Explicit log ticks
        ax.set_xscale('log')
        ax.xaxis.set_major_locator(mticker.FixedLocator(nx))
        ax.xaxis.set_minor_locator(mticker.NullLocator())

        ax.set_xticklabels(nx_keys)

        ax.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)

        ax.plot(nx, tavg / hits, '-', color=plotcolor[expt],
            label=expt.upper() + " tavg")
        ax.plot(nx, tmax / hits, '--', color=plotcolor[expt],
            label=expt.upper() + " tmax")
        ax.plot(nx, tmin / hits, ':', color=plotcolor[expt],
            label=expt.upper() + " tmin")

        ax.plot(nx, tavg / hits, 'o', color=plotcolor[expt])
        ax.plot(nx, tmax / hits, 'o', color=plotcolor[expt])
        ax.plot(nx, tmin / hits, 'o', color=plotcolor[expt])

        # Adjust ranges
        if reg == '(Ocean continuity equation)':
            ax.set_ylim([0.0, 0.06])
        if reg == '(Ocean barotropic mode stepping)':
            ax.set_ylim([0.0, 0.03])

axes[0,0].legend()

plt.show()
