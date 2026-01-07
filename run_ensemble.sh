#!/bin/bash

JOBSIZES="1 2 4 8 16 32 64 128"
#JOBSIZES="1 2 4 8 16 32 64 96 128"
#JOBSIZES="1 2 4 8 16 32 64 128 256 512"

# TODO: can I get this from lscpu or `/sys` ?
CPU_PER_NODE=96

# Set to cpu or gpu
PLATFORM=gpu

#---

cpuid_max=$(( ${CPU_PER_NODE} - 1 ))

# Construct a square-like layout m x n for i ranks
get_layout() {
 	local i=$1
  	m=1

	# Find the smallest m such that m**2 > i
  	while (( (m+1)*(m+1) <= i )); do
    	((m++))
  	done

	# Then decrement m until it exactly divides i
  	while (( i % m != 0 )); do
  	  ((m--))
  	done

	# Finally, set n such that m*n == i
  	n=$(( i / m ))

	# Force m >= n
  	if (( m < n )); then
  	  	local t=$m
  	  	m=$n
  	  	n=$t
  	fi
}

for i in ${JOBSIZES}; do
    k=0
    t=$i
    while (( t > 1 )); do
        ((k++))
        t=$((t >> 1))
    done

	get_layout "$i"

    if [ "$PLATFORM" = "gpu" ]; then
        lx=1
        ly=1
    else
	    lx=${m}
	    ly=${n}
    fi
	ni=$(( 32 * ${m} ))
	nj=$(( 32 * ${n} ))

    dt=$(( 1200 / ${m} ))
    dt_therm=$(( 2400 / ${m} ))

    cat <<EOF > MOM_override
#override COORD_CONFIG = "linear"
DENSITY_RANGE = 2.0
#override NK = 100
#override NIGLOBAL = ${ni}
#override NJGLOBAL = ${nj}
LAYOUT = ${lx},${ly}
#override DT = ${dt}
#override DT_THERM = ${dt_therm}
#override DT_FORCING = ${dt_therm}
TIMEUNIT = ${dt}
ENERGYSAVEDAYS = 75
#override DAYMAX = 150
EOF
    if [ "${PLATFORM}" == "gpu" ]; then
        # TODO: GPU parallelization
        nranks=1
    else
        nranks=${i}
    fi

    printf -v i0 "%03d" "$i"
    mpirun -np ${nranks} ../build_omp/MOM6 \
        | tee ${PLATFORM}_${i0}.out 2> ${PLATFORM}_${i0}.err

    # TODO: what is the MPI GPU command?
    #mpiexec -n 1 -x CUDA_VISIBLE_DEVICES=0 ../build_omp/MOM6 \
    #    : -n 1 -x CUDA_VISIBLE_DEVICES=1 ../build_omp/MOM6 \
    #| tee gpu_${i0}.out 2> gpu_${i0}.err
done
