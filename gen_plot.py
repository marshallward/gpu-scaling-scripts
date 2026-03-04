#!/usr/bin/env python3

import os
import sys

import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

CPU_cores = 96
#CPU_cores = 0
force_origin = False
dark_bg = True


# Standard modules
regions = [
    '(Ocean Coriolis & mom advection)',
    '(Ocean barotropic mode stepping)',
    '(Ocean continuity equation)',
    '(Ocean horizontal viscosity)',
    '(Ocean pressure force)',
    '(Ocean vertical viscosity)',
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


# TODO: Better as command line inputs?
legend_labels = {
    'h100': 'H100',
    'a100': 'A100',
    'gh200': 'GH200',

    'cpu_m': 'CPU (MW)',
    'cpu_u': 'CPU (UW)',
    'cpu_0': 'CPU (ref)',
    'bbl_cpu': 'CPU (BBL PR)',
    'bbl_gpu': 'GPU (BBL PR)',
    #'mpi_pe1': '1 GPU',
    #'mpi_pe2': '2 GPU',
    #'mpi_pe4': '4 GPU',
    #'mpi_pe8': '8 GPU',
    #'pe1_new': 'GPU (H100)',
    #'pe1_new': 'GPU (serial k)',
    'pe1_new': 'xH100',
    'pe2_new': 'xH100 ×2',
    'pe4_new': 'xH100 ×4',
    'pe8_new': 'xH100 ×8',
    'pe1_v2': 'GPU (H100)',
    'pe2_v2': 'H100 ×2',
    'pe4_v2': 'H100 ×4',
    'pe8_v2': 'H100 ×8',
    #
    'pe1_vvlim': 'H100 + vvlim',
    #'h100': 'nvhpc 25.11',
    'nv26p1': 'nvhpc 26.1',
    #'cor_k': 'CorAdCalc v2',
    'cor_k': 'GPU (k teams)',
    'gaea_2s': 'CPU (Milan 64c x2)',
    'gaea_1s': 'CPU (Milan 64c)',
    'ursa_1s': 'CPU (Genoa 96c)',
    'ursa_2s': 'CPU (Genoa 96c x2)',
}


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


def plot_results(platforms, regions, stats, output):
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
            ax.set_xscale('log')
            ax.xaxis.set_major_locator(mticker.FixedLocator(nx))
            ax.xaxis.set_minor_locator(mticker.NullLocator())
            ax.set_xticklabels([f"{nx}x" for nx in nx_keys], rotation=45)

            ax.set_yscale('log')
            ax.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda v, pos: f"{v:g}")
            )
            ax.yaxis.set_major_locator(
                mticker.LogLocator(base=10, subs=(1.0, 2.0, 5.0))
            )
            ax.yaxis.set_minor_locator(mticker.NullLocator())

            ax.tick_params(colors=ctxt)

            ax.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)

            if any(tavg != tmin) or any(tavg != tmax):
                ax.fill_between(nx, tmin / hits, tmax / hits,
                                alpha=0.15, linewidth=0)

            line, = ax.plot(nx, tavg / hits, '-',
                            label=legend_labels[expt])

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

    #plt.show()
    plt.savefig(output)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('platforms', nargs='+', help='Platform directories, e.g. a100 h100')
    p.add_argument('-o', '--output', default='out.svg', metavar='FILE', help='output filename')
    args = p.parse_args()

    platforms = [os.path.basename(os.path.normpath(p)) for p in args.platforms]

    stats = get_stats(platforms)
    plot_results(platforms, regions, stats, args.output)


if __name__ == '__main__':
    main()
