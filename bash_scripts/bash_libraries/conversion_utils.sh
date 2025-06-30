#!/bin/bash

convert_set_to_edf() {
    # Convert .set EEG files to .edf format for a given subject.
    #
    # Arguments:
    #   $1 - Subject identifier (e.g., "sub-01")
    #   $2 - Directory where the log file will be saved
    #
    # Description:
    #   This function calls the Python script `convert_set2edf.py` to convert 
    #   EEGLAB .set files to EDF format for the specified subject.
    #   Standard output and error are redirected to a log file named 
    #   'convert_set2edf.log' inside the given log directory.
    #
    # Requirements:
    #   - Environment variable $PYTHON_EXECUTABLE must point to a valid Python interpreter.
    #   - The script `convert_set2edf.py` must be in the same directory or accessible in PATH.
    subj=$1
    log_dir=$2
    echo "Converting .set to .edf for $subj..."
    set_to_edf_log="${log_dir}/convert_set2edf.log"

    # Run the script for .set to .edf conversion
    $PYTHON_EXECUTABLE $PYTHON_SCRIPTS/convert_set2edf.py "$subj" > "$set_to_edf_log" 2>&1 
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "\n    [.set to .edf] Conversion failed for $subj. Check the log: $set_to_edf_log" >&2
        return 1
    fi
}

convert_edf_to_eeg() {
    # convert_edf_to_eeg()
    # ---------------------
    # Converts a single .edf file to .eeg format for one subject.
    # The function uses a parameter file for conversion, then cuts the EEG
    # signal to the appropriate number of samples defined in a CSV file.
    #
    # Arguments:
    #   1. Path to the .edf file
    #   2. Directory to store the output .eeg file
    #   3. Subject's directory where the preprocessing CSV is located
    #
    # Output:
    #   Path to the .eeg file.
    local edf_file=$1
    local source_eeg_dir=$2
    local subj_dir=$3

    # Get filename and where to save it
    local filename
    filename=$(basename "$edf_file" .edf)
    local output_file="$source_eeg_dir/$filename"

    # Convert .edf to .eeg
    if [ ! -f "$output_file.eeg" ]; then
        echo -e "\nConverting: $edf_file -> $output_file.eeg"  >&2
        edf2eeg "$edf_file" "$PAR_FOLDER/EEG_ERN_convert.par" "$source_eeg_dir/temp" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [.edf to .eeg] edf2eeg failed." >&2
            return 1
        fi

        # Get the real number of samples
        local csv_file="$subj_dir/${filename}_desc-preprocessing_information.csv"
        local nb_samples=$(get_nb_samples "$csv_file")

        echo "Cutting EEG to $((nb_samples - 1)) samples"  >&2
        eegcut "$source_eeg_dir/temp.eeg" "$output_file.eeg" 0 $((nb_samples - 1)) >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [.edf to .eeg] eegcut failed." >&2
            return 1
        fi
        rm "$source_eeg_dir"/temp*
    fi

    echo "$output_file"  
}

select_and_convert_edf() {
    # select_and_convert_edf
    # -----------------------
    # Selects an EDF file (if present) from a list, and converts it to .eeg format.
    # - If no file is found, the subject is skipped.
    # - If one file is found, it is processed.
    # - If multiple files are found, only the first one is processed with a warning.
    #
    # Arguments:
    #   1. Subject ID
    #   2. Name of the array variable containing .edf files (passed by reference)
    #   3. EEG output directory for converted .eeg files
    #   4. Subject's directory (used to locate the preprocessing CSV)
    #
    # Output:
    #   Prints two space-separated values: the base filename and the .eeg output path.
    #   Returns non-zero status if no file was processed (to allow skipping in loops).
    local subj="$1"
    local edf_files=("${!2}")  # Array passed by reference
    local source_eeg_dir="$3"
    local subj_dir="$4"

    if (( ${#edf_files[@]} == 0 )); then
        echo "No EDF files found for subject $subj, pass the subject." >&2
        return 1

    elif (( ${#edf_files[@]} == 1 )); then
        edf_file="${edf_files[0]}"
        if [ -e "$edf_file" ]; then
            local output_file=$(convert_edf_to_eeg "$edf_file" "$source_eeg_dir" "$subj_dir") || return 1
        else
            echo "File $edf_file does not exist, pass subject $subj." >&2
            return 1
        fi

    else
        echo "Multiple EDF files found for subject $subj, only processing the first one."
        edf_file="${edf_files[0]}"
        if [ -e "$edf_file" ]; then
            local output_file=$(convert_edf_to_eeg "$edf_file" "$source_eeg_dir" "$subj_dir") || return 1
        else
            echo "File $edf_file does not exist, pass subject $subj." >&2
            return 1
        fi
    fi

    # Export filename and output_file so they can be used in the caller   
    echo "$output_file"
    return 0
}