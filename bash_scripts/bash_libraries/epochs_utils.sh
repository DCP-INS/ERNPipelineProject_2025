#!/bin/bash

save_single_trial_epochs() {
    # Save single-trial epochs for a given subject using Python.
    # Arguments:
    #   1. Subject ID
    #   2. Boolean or flag indicating whether interpolation was applied (to_interpol)
    local subj=$1
    local to_interpol=$2

    local python_script="$PYTHON_SCRIPTS/save_single_trial_epo.py"
    local log_file="${log_dir}/save_single_trial_epo.log"

    echo -e "\n     [Single Trials Epochs] Saving single-trial epochs for subject $subj (Interpolated: $to_interpol)..." >&2

    $PYTHON_EXECUTABLE "$python_script" "$subj" "$to_interpol" > "$log_file" 2>&1
    if [[ $? -ne 0 ]]; then
        echo -e "\n     [Single Trials Epochs] Error during execution of $python_script. Check log: $log_file" >&2
        return 1
    fi
}


average_per_condition() {
    # Compute averaged EEG epochs per condition for a subject.
    # Arguments:
    #   1. Subject ID
    #   2. Input EEG file path (e.g., filtered/interpolated EEG)
    #   3. Path to pos file
    local subj=$1
    local input_file=$2
    local rejposrep_file=$3

    echo -e "\n     [Epoch Computation] Processing subject ${subj}:" >&2

    local input_filename
    input_filename=$(basename "$input_file" .eeg)
    local rejposrep_filename
    rejposrep_filename=$(basename "$rejposrep_file" .pos)

    # Construct output filenames and paths
    local avg_pos_filename="${rejposrep_filename}_ERN"
    local output_pos_path="$pos_outdir/${avg_pos_filename}.pos"

    local avg_rej_filename="${input_filename}_eegavg_ERN"
    local output_avgrej_path="$par_outdir/${avg_rej_filename}.par.res"

    # Only proceed if the rejection position file exists
    if [ -f "$pos_outdir/${rejposrep_filename}.pos" ]; then
        bash $BASH_SCRIPTS/auto_ERN_eegavg "$input_file" "$pos_outdir/${rejposrep_filename}.pos" "$output_pos_path" "$subj" "$subj_dir" "$output_avgrej_path" >&2
        if [ $? -eq 1 ]; then
            echo -e "\n     [Epoch Computation] Error occurred while computing epoch averages." >&2
            return 1
        fi
    fi
}