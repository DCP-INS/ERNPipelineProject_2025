#!/bin/bash

detect_interpolation_channels() {
    # Detect whether a subject has channels that require interpolation
    # Arguments:
    #   1. Subject ID
    # Output:
    #   "True" if interpolation is needed, otherwise "False"
    local subj=$1

    echo -e "\n     [Interpolation Detection] Checking for bad channels: subject ${subj}" >&2

    local log_file="${log_dir}/find_electrodes_to_interpolate.log"
    local python_script="$PYTHON_SCRIPTS/find_electrodes_to_interpolate_outlier_rej.py"

    $PYTHON_EXECUTABLE "$python_script" "$subj" > "$log_file" 2>&1
    exit_code=$? 
    if [ $exit_code -ne 0 ]; then
        echo -e "\n    [Interpolation Detection] Checking for bad channels for $subj failed. Check the log: $log_file" >&2
        return 1
    fi

    if grep -q "TO_INTERPOL=True" "$log_file"; then
        echo "True"
    else
        echo "False"
    fi
}

interpolate_and_reject() {
    # Interpolates bad EEG channels and performs artifact rejection on the interpolated data.
    # Arguments:
    #   1. Subject ID
    #   2. Input EEG file (path)
    #   3. Base EEG file (original filename, no .eeg extension to locate associated CSV)
    #   4. Path to .pos file used in artifact rejection
    local subj=$1
    local input_eeg=$2
    local base_eeg=$3
    local rejpos_path=$4

    local eeg_filename
    eeg_filename=$(basename "$input_eeg" .eeg)
    local base_filename
    base_filename=$(basename "$base_eeg")

    local interpolation_parfile="$par_outdir/${eeg_filename}_eegspline.par"
    local csv_file="$subj_dir/${base_filename}_desc-interpolated_channels.csv"

    local interpo_filename="${eeg_filename}_eegspline"
    local output_interp_path="$output_dir/$interpo_filename.eeg"

    if [ ! -f "$output_interp_path" ]; then
        echo -e "\n     [Interpolation] Creating interpolation parameter file: $interpolation_parfile" >&2
        bash "$BASH_SCRIPTS/create_interpo_par_sub" "$interpolation_parfile" "$csv_file" >&2

        echo -e "\n     [Interpolation] Running interpolation: $input_eeg.eeg → $output_interp_path" >&2
        eegspline "$input_eeg" "$interpolation_parfile" "$output_interp_path" >&2
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [Interpolation] eegspline failed." >&2
            return 1
        fi
    fi

    echo -e "\n     [Response Rejection Post Interpolation] Running post-ICA artifact rejection on interpolated data..." >&2
    local output_rej_paths
    output_rej_paths=$(artifact_rejection_post_interpo "$subj" "$output_interp_path" "$rejpos_path")
    if [ $? -eq 1 ]; then
        echo -e "\n     [Response Rejection Post Interpolation] Failed for $subj"
        return 1
    fi
    echo "$output_interp_path $output_rej_paths"
}


get_elecnumber_par() {
    # get_elecnumber_par
    # ------------------
    # Retrieves the line number and numeric identifier associated with a given electrode name
    # from the EEG parameter file (e.g., EEG_ERN_convert.par).
    #
    # Arguments:
    #   1. Electrode name (e.g., "Fz")
    #
    # Output:
    #   - Line number (0-based) and the electrode's numeric identifier, separated by a space.
    #
    # Usage:
    #   get_elecnumber_par "Fz"
    #
    local electrode_name=$1
    local elec_file="$PAR_FOLDER/EEG_ERN_convert.par"

    if [ -z "$electrode_name" ]; then
        echo "Usage: get_electrode_info <electrode_name>" >&2
        return 1
    fi

    if [ ! -f "$elec_file" ]; then
        echo "Error: Parameter file not found at $elec_file" >&2
        return 1
    fi

    # Search and extract info
    grep -n "^${electrode_name}\." "$elec_file" | while IFS=":" read -r line_number electrode_line; do
        local electrode_number
        electrode_number=$(echo "$electrode_line" | awk -F. '{print $2}')
        echo "$((line_number - 1)) $electrode_number"
    done
}
