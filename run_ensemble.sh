#!/bin/bash

MOM6_EXEC=../build_arm/MOM6

# This is needed for some environments
first=$(cat /proc/self/status | grep Cpus_allowed_list | cut -f 2 | cut -d'-' -f 1)

JOBSIZES="1 2 4 8 16 32 64 128"
#JOBSIZES="1 2 4 8 16 32 64 96 128"
#JOBSIZES="1 2 4 8 16 32 64 128 256 512"

# TODO: can I get this from lscpu or `/sys` ?
CPU_PER_NODE=96

# Set to cpu or gpu
PLATFORM=gpu
NGPUS=1

#---

#cpuid_max=$(( ${CPU_PER_NODE} - 1 ))

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
    if [ "$PLATFORM" = "gpu" ]; then
	   get_layout "${NGPUS}"
    else
        nranks=$(( i > CPU_PER_NODE ? CPU_PER_NODE : i ))

	   get_layout "${nranks}"
    fi
	lx=${m}
	ly=${n}


	get_layout "${i}"

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
ENERGYSAVEDAYS = 50
#override DAYMAX = 150
EOF
    # File label index
    printf -v i0 "%03d" "$i"

    if [ "${PLATFORM}" == "gpu" ]; then
        # TODO: Flags must be built based on config!
        ## GPU parallel (two per node)
        #mpirun -np ${NGPUS} \
        #    --map-by ppr:2:node \
        #    --bind-to core \
        #    bash -lc "
        #        export CUDA_VISIBLE_DEVICES=\$OMPI_COMM_WORLD_LOCAL_RANK
        #        exec ${MOM6_EXEC}
        #    " \
        #    | tee ${PLATFORM}_${i0}.out 2> ${PLATFORM}_${i0}.err

        # GPU parallel (one per node)
        mpirun -np ${NGPUS} --cpu-set ${first} \
            --bind-to core \
            bash -lc "
                export CUDA_VISIBLE_DEVICES=\$OMPI_COMM_WORLD_LOCAL_RANK
                exec ${MOM6_EXEC}
            " \
            | tee ${PLATFORM}_${i0}.out 2> ${PLATFORM}_${i0}.err
    else
        nranks=$(( i > CPU_PER_NODE ? CPU_PER_NODE : i ))

        mpirun -np ${nranks} \
            --bind-to core \
            ${MOM6_EXEC} \
            | tee ${PLATFORM}_${i0}.out 2> ${PLATFORM}_${i0}.err
        #mpirun -np ${nranks} \
        #    --map-to socket \
        #    --bind-to core \
        #    ${MOM6_EXEC} \
        #    | tee ${PLATFORM}_${i0}.out 2> ${PLATFORM}_${i0}.err
    fi

    ## GPU parallel
    #mpirun -np ${NGPUS} --cpu-set ${first} \
    #    bash -lc "
    #        export CUDA_VISIBLE_DEVICES=\$OMPI_COMM_WORLD_LOCAL_RANK
    #        exec ${MOM6_EXEC}
    #    " \
    #    | tee ${PLATFORM}_${i0}.out 2> ${PLATFORM}_${i0}.err
done
