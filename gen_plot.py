#!/usr/bin/env python3

import os
import matplotlib.pyplot as plt

# Read files

platforms = ('cpu', 'gpu',)

regions = [
    '(Ocean Coriolis & mom advection)',
    '(Ocean pressure force)',
    '(Ocean vertical viscosity)',
    '(Ocean horizontal viscosity)',
    '(Ocean continuity equation)',
    '(Ocean barotropic mode stepping)',
]

run_files = {}
run_files['cpu'] = [run for run in os.listdir() if run.startswith('cpu_')]
run_files['gpu'] = [run for run in os.listdir() if run.startswith('gpu_')]

stats = {}

for expt in platforms:
    data_files = run_files[expt]

    # NOTE: File is (platform, resolution): region: timing
    #   We want to invert to platform: region: timing: resolution
    runs = {}
    for runfile in data_files:
        clocks = {}
        with open(runfile) as timings_file:
            header = timings_file.readline()
            keys = header.split()

            for line in timings_file:
                rec = line.rsplit(maxsplit=len(keys))

                clk = rec[0]
                clocks[clk] = {}
                for key, value in zip(keys, rec[1:]):
                    clocks[clk][key] = value

        run_label = runfile.split('_')[1].split('.')[0].lstrip('0')

        runs[run_label] = clocks

    stats[expt] = runs


# Plot results
fig, axes = plt.subplots(2, 3)

for expt in platforms:
    # Generate x-axis
    # TODO: Maybe keep as dict?
    #run_labels = [int(k.rstrip('x')) for k in stats[expt].keys()]

    # Get run keys
    run_keys = sorted(stats[expt], key=lambda k: int(k.rstrip('x')))
    print(run_keys)

    for reg, ax in zip(regions, axes.flat):
        #tmin = stats[expt][reg]['tmin']
        #tavg = stats[expt][reg]['tavg']
        #tmax = stats[expt][reg]['tmax']

        ax.set_title(reg)
        ax.set_xscale('log')
