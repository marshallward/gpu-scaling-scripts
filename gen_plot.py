#!/usr/bin/env python3

import os
import sys

import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

CPU_cores = 96
#CPU_cores = 64
#CPU_cores = 0
force_origin = False
dark_bg = True
use_log_plot = True


# Standard modules
regions = [
    '(Ocean Coriolis & mom advection)',
    '(Ocean barotropic mode stepping)',
    '(Ocean continuity equation)',
    '(Ocean horizontal viscosity)',
    '(Ocean pressure force)',
    '(Ocean vertical viscosity)',
    #
    #'Ocean dynamics',
    #'Main loop',
    #'Ocean Other',
]

## MPI scaling
#regions = [
#    '(Ocean Coriolis & mom advection)',
#    '(Ocean BT stepping calcs only)',
#    '(Ocean continuity equation)',
#    '(Ocean message passing)',
#    '(Ocean pressure force)',
#    '(Ocean vertical viscosity)',
#]


# Custom ranges
plt_yrange = {
#    '(Ocean continuity equation)': [0.0, 100.],
#    '(Ocean barotropic mode stepping)': [0.0, 30.],
}


plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.tab10.colors)

# Create a square-like m x n pair
def square_pad(k):
    if k <= 0:
        raise ValueError("k must be positive")

    # ceil sqrt without using sqrt()
    n = 1
    while n * n < k:
        n += 1

    m = (k + n - 1) // n  # ceil(k/n)

    if m > n:
        m, n = n, m

    return m, n


def get_stats(platforms):
    stats = {}

    run_files = {
        expt: [
            os.path.join(expt, run)
            for run in os.listdir(expt)
            if run.endswith('.out') or run.endswith('.txt')
        ]
        for expt in platforms
    }

    for expt in platforms:
        data_files = run_files[expt]

        # NOTE: File is `(platform, resolution): region: timing`
        #   We invert to `platform: region: resolution: timing`
        #   But we may want `platform: region: timing: resolution`

        # NOTE: extension doesn't matter; `.out` or `.txt` are OK
        for runfile in data_files:
            resolution = runfile.rsplit('_', 1)[1].split('.')[0].lstrip('0')

            metrics = {}
            with open(runfile) as stats_file:
                for line in stats_file:
                    if not line.strip().startswith('hits'):
                        continue

                    keys = line.split()
                    break

                for line in stats_file:
                    # Skip blank lines
                    if not line.strip():
                        continue

                    # Skip any trailing output
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

    return stats


def plot_results(platforms, regions, stats, output, legend_labels):
    nplot = len(regions)
    nrow, ncol = square_pad(nplot)

    # Plot results
    fig, axes = plt.subplots(nrow, ncol, figsize=(12, 7), squeeze=False,
    #fig, axes = plt.subplots(nrow, ncol, figsize=(8, 4), squeeze=False,
            constrained_layout=True)

    if dark_bg:
        fig.patch.set_facecolor('none')
        ctxt = 'white'
    else:
        ctxt = 'black'

    fig.suptitle(f'Time per step (msec) from 32×32 to 1024×1024', color=ctxt)
    #fig.suptitle(f'Runtime per step (in msec) for MOM6 modules from 32×32 to 128×128')

    colors = plt.cm.tab10.colors[:len(platforms)]

    ## Denote the CPU core limit
    if CPU_cores > 0:
        for ax in axes.flat:
            ax.axvline(CPU_cores, linestyle="--", color=colors[0])
            #ax.axvline(2. * CPU_cores, linestyle="--", color=colors[1])
            #ax.axvline(96, linestyle="--", color=colors[1])

    for expt in platforms:
        for reg, ax in zip(regions, axes.flat):
            # Fetch metric keys
            nx_keys = stats[expt][reg].keys()
            nx = [int(k.rstrip('x')) for k in nx_keys]

            # Re-sort from 1x to max
            nx_keys = [x for _, x in sorted(zip(nx, nx_keys))]
            nx.sort()

            tmin = 1000. * np.array([stats[expt][reg][nx]['tmin'] for nx in nx_keys])
            tmax = 1000. * np.array([stats[expt][reg][nx]['tmax'] for nx in nx_keys])
            tavg = 1000. * np.array([stats[expt][reg][nx]['tavg'] for nx in nx_keys])

            # There are two clocks per dycore loop, but this could change.
            hits = np.array(
                    [stats[expt]['Ocean dynamics'][nx]['hits'] for nx in nx_keys]
            ) / 2.

            ax.set_title(reg, color=ctxt)

            # Explicit log ticks
            if (use_log_plot):
                ax.set_xscale('log')
                ax.xaxis.set_major_locator(mticker.FixedLocator(nx))
                ax.xaxis.set_minor_locator(mticker.NullLocator())
                ax.set_xticklabels([f"{nx}x" for nx in nx_keys], rotation=45)

                ax.set_yscale('log')
                ax.yaxis.set_major_formatter(
                    mticker.FuncFormatter(lambda v, pos: f"{v:g}")
                )
                ax.yaxis.set_major_locator(
                    #mticker.LogLocator(base=10, subs=(1.0, 2.0, 5.0))
                    mticker.LogLocator(base=2)
                )
                ax.yaxis.set_minor_locator(mticker.NullLocator())

            ax.tick_params(colors=ctxt)

            ax.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)

            if any(tavg != tmin) or any(tavg != tmax):
                ax.fill_between(nx, tmin / hits, tmax / hits,
                                alpha=0.15, linewidth=0)

            label = legend_labels[expt] if expt in legend_labels else expt

            line, = ax.plot(nx, tavg / hits, '-', label=label)

            col = line.get_color()

            ax.plot(nx, tavg / hits, 'o', color=col)

            #if reg in plt_yrange:
            #    ax.set_ylim(plt_yrange[reg])

    #axes[1,2].set_ylim([0.0, 0.008])

    # Force origin in plots
    # Per-plot?
    if force_origin:
        for ax in axes.flat:
            ax.set_ylim([0, None])

    axes[0, 0].legend()

    plt.show()
    #plt.savefig(output)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('platforms', nargs='+', help='Platform directories, e.g. a100 h100')
    p.add_argument('-o', '--output', default='out.svg', metavar='FILE', help='output filename')
    p.add_argument(
        '-l', '--label', default='', metavar='LABEL[,LABEL...]',
        help='comma-separated legend labels, matched to platform order'
    )
    args = p.parse_args()

    platforms = [os.path.basename(os.path.normpath(p)) for p in args.platforms]
    labels = next(csv.reader([args.label])) if args.label else []
    if len(labels) > len(platforms):
        p.error('more labels provided than platform directories')

    legend_labels = dict(zip(platforms, labels))

    stats = get_stats(platforms)
    plot_results(platforms, regions, stats, args.output, legend_labels)


if __name__ == '__main__':
    main()
