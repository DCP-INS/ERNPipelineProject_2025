#!/bin/bash

perform_ica() {
    # Perform ICA decomposition and artifact correction on EEG data
    # Arguments:
    #   1. Subject ID
    #   2. Base EEG path (used to build ICA XML path)
    #   3. Input EEG file (already filtered)
    local subj=$1
    local base_eeg_path=$2
    local input_eeg=$3

    local base_filename
    base_filename=$(basename "$base_eeg_path" .edf)

    # Path to ICA transformation matrix
    local ica_xml_path="$ica_dir/${base_filename}_desc-ica_transf_matrix.xml"

    # Run ICA matrix generation if not done
    if [ ! -f "$ica_xml_path" ]; then
        echo -e "\n     [ICA] Performing ICA decomposition for subject $subj..." >&2
        $PYTHON_EXECUTABLE "$PYTHON_SCRIPTS/ica_eeg.py" "$subj" > "$log_dir/ica_eeg.log" 2>&1
        if [[ $? -ne 0 ]]; then
            echo -e "\n     ICA] Error while Performing ICA decomposition for subject $subj. Check log: $log_dir/ica_eeg.log" >&2
            return 1
        fi
    fi

    # Prepare filename for ICA-corrected EEG
    local input_filename
    input_filename=$(basename "$input_eeg" .eeg)

    local icacor_filename="${input_filename}_icacor"
    local output_icacor_path="$output_dir/$icacor_filename"

    # Run component rejection if not already done
    if [ ! -f "${output_icacor_path}.eeg" ]; then
        echo -e "\n     [ICA] Correcting blinks and saccades for $subj..." >&2

        local preprocessing_csv="$subj_dir/${base_filename}_desc-preprocessing_information.csv"
        
        # Read component numbers from helper
        components_output=$(get_component_ica "$preprocessing_csv")
        if [ $? -eq 1 ]; then
            echo -e "\n     [ICA] Error: Failed to get ICA components from $preprocessing_csv" >&2
            return 1
        fi

        # Then parse it into variables
        read -r comp1 comp2 comp3 <<< "$components_output"

        if [ -n "$comp1" ]; then
        
            # Run the ICA correction
            eegfiltica $input_eeg $ica_xml_path $output_icacor_path $comp1 $comp2 $comp3 >&2
            exit_code=$?
            if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
                echo -e "\n     [ICA] eegfiltica failed." >&2
                return 1
            fi
        else
            cp "$input_eeg" "$output_icacor_path.eeg"
            cp "$input_eeg.ent" "$output_icacor_path.eeg.ent"
        fi
    fi
    # Return the ICA-corrected output path
    echo "$output_icacor_path"
}

get_component_ica() {
    # Extract up to three ICA components from a CSV file for artifact correction
    #
    # Usage:
    #   get_component_ica <csv_file>
    #
    # Description:
    #   This function reads a semicolon-separated CSV file (usually generated during preprocessing)
    #   and extracts up to the first three ICA components listed under the "ICA_components_used" column.
    #   These components are typically used for blink or saccade correction in EEG preprocessing pipelines.
    #
    # Arguments:
    #   <csv_file> - Path to the CSV file containing preprocessing metadata.
    #
    # Output:
    #   Prints up to three ICA component indices separated by spaces.
    #   These can be captured by a calling script using `read comp1 comp2 comp3 < <(get_component_ica ...)`
    local csv_file=$1
    local col_index components_string
    local comp1 comp2 comp3

    # Check if the file exists
    if [[ ! -f "$csv_file" ]]; then
        echo "Error: File not found: $csv_file" >&2
        return 1
    fi

    # Get column index of 'ICA_components_used'
    col_index=$(head -1 "$csv_file" | tr ';' '\n' | grep -n '^ICA_components_used$' | cut -d: -f1)

    if [[ -z "$col_index" ]]; then
        echo "Error: 'ICA_components_used' column not found in $csv_file" >&2
        return 1
    fi

    # Extract the value in that column (2nd line of the CSV)
    components_string=$(awk -F';' -v col="$col_index" 'NR==2 {print $col}' "$csv_file")

    # Split the components (comma or comma + space), get the first three max
    IFS=',' read -ra components_array <<< "$components_string"


    comp1=$(echo "${components_array[0]:-}" | xargs)
    comp2=$(echo "${components_array[1]:-}" | xargs)
    comp3=$(echo "${components_array[2]:-}" | xargs)

    echo "$comp1 $comp2 $comp3"
}