#!/bin/bash

# ==============================================================================
# EEG Preprocessing Functions
# ------------------------------------------------------------------------------
# This script provides a set of reusable Bash functions to preprocess EEG data 
# files (.eeg). Each function applies a specific preprocessing step, including:
#   - Offset correction
#   - High-pass filtering (0.1 Hz cutoff)
#   - Rereferencing (bipolar then common reference)
#   - Notch filtering (50 Hz line noise removal)
#   - Low-pass filtering (40 Hz cutoff)
#
# The functions check if the processed output file already exists to avoid
# redundant processing, and return the full path to the output file.
#
# Dependencies:
#   - eegoffset
#   - eegfiltfilt
#   - eegchref
# ==============================================================================

apply_offset_correction() {
    # apply_offset_correction
    # -----------------------
    # Applies an offset correction to an EEG file if it hasn't been done already.
    #
    # Arguments:
    #   1. input_file : Path to the base EEG file
    #   2. output_dir : Directory where the offset-corrected output file should be saved
    #
    # Behavior:
    #   - Constructs the output filename by appending '_desc-offset' to the base name.
    #   - Checks if the output offset-corrected file already exists to avoid recomputation.
    #   - Returns the full path of the offset-corrected EEG file.
    local input_file=$1
    local output_dir=$2

    # Extract the base filename 
    local filename=$(basename "$input_file" .eeg)

    # Build the output filename with _desc-offset suffix
    local offset_filename="${filename}_desc-offset"
    local output_offset_path="$output_dir/$offset_filename.eeg"

    # Run offset correction only if output file doesn't already exist
    if [ ! -f "$output_offset_path" ]; then
        echo -e "\nOffset correction: $input_file -> $output_offset_path" >&2
        eegoffset "$input_file" -all "$output_offset_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            return 1
        fi
    fi

    # Return the output file path
    echo "$output_offset_path"
}

apply_highpass_filter() {
    # apply_highpass_filter
    # ---------------------
    # Applies a high-pass filter (cutoff at 0.1 Hz) to an EEG file if it hasn't been done already.
    #
    # Arguments:
    #   1. input_file : Path to the EEG file (.eeg)
    #   2. output_dir : Directory where the high-pass filtered output file should be saved
    #
    # Behavior:
    #   - Constructs the output filename by appending '_hp' to the base name.
    #   - Checks if the filtered file already exists to avoid redundant filtering.
    #   - Returns the full path of the high-pass filtered EEG file.
    local input_file=$1
    local output_dir=$2

    # Extract base filename without extension
    local filename
    filename=$(basename "$input_file" .eeg)

    # Build output filename with _hp suffix
    local hp_filename="${filename}_desc-hp"
    local output_hp_path="$output_dir/$hp_filename.eeg"

    # Run high-pass filter only if output file doesn't exist
    if [ ! -f "$output_hp_path" ]; then
        echo -e "\nHigh Pass 0.1Hz filtering: $input_file -> $output_hp_path" >&2
        eegfiltfilt "$input_file" "$PAR_FOLDER/eeg_filt_hp0.1.par" "$output_hp_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            return 1
        fi
    fi

    # Return the filtered file path
    echo "$output_hp_path"
}


apply_rereferencing() {
    # apply_rereferencing
    # ------------------
    # Applies rereferencing to a EEG file if not already done.
    # This process involves two sequential rereferencing steps using different parameter files.
    #
    # Arguments:
    #   1. input_file : Path to the high-pass filtered EEG file (.eeg)
    #   2. output_dir : Directory where the rereferenced EEG file will be saved
    #
    # Behavior:
    #   - Constructs the output filename by appending '_ref' to the input file’s base name.
    #   - Checks if the rereferenced file already exists to avoid recomputation.
    #   - Applies two rereferencing steps via 'eegchref':
    #       1. Bipolar rereferencing (using eeg_bipo.par)
    #       2. Common reference rereferencing (using eeg_ref.par)
    #   - Returns the full path of the rereferenced EEG file.
    local input_file=$1
    local output_dir=$2

    # Extract base filename without extension
    local filename
    filename=$(basename "$input_file" .eeg)

    # Build output filename with _ref suffix
    local reref_filename="${filename}_ref"
    local output_reref_path="$output_dir/$reref_filename.eeg"

    # Temporary intermediate file path
    local output_temp="$output_dir/temp.eeg"

    # Run rereferencing only if output file doesn't exist
    if [ ! -f "$output_reref_path" ]; then
        echo -e "\n[Rereferencing]  $input_file -> $output_reref_path" >&2

        # First rereferencing step: bipolar reref
        eegchref "$input_file" "$PAR_FOLDER/eeg_bipo.par" "$output_temp" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [Rereferencing] Bipolar referencing failed for $subj" >&2            
            return 1
        fi


        # Second rereferencing step: common reference reref
        eegchref "$output_temp" "$PAR_FOLDER/eeg_ref.par" "$output_reref_path" >&2
        exit_code=$? 
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n [Rereferencing] Mastoïde referencing failed for $subj" >&2           
            return 1
        fi

        # Clean up temporary file
        rm $output_dir/temp.*
    fi

    # Return the rereferenced file path
    echo "$output_reref_path"
}


apply_notch_filter() {
    # apply_notch_filter
    # -----------------
    # Applies a 50 Hz notch filter to remove line noise from an EEG file.
    #
    # Arguments:
    #   1. input_file : Path to the EEG file (.eeg)
    #   2. output_dir : Directory where the notch filtered EEG file will be saved
    #
    # Behavior:
    #   - Constructs the output filename by appending '_notch50' to the input file’s base name.
    #   - Checks if the notch filtered file already exists to avoid recomputation.
    #   - Applies notch filtering using 'eegfiltfilt' with the 50 Hz notch parameter file.
    #   - Returns the full path of the notch filtered EEG file.
    local input_file=$1
    local output_dir=$2

    # Extract base filename without extension
    local filename
    filename=$(basename "$input_file" .eeg)

    # Build output filename with _notch50 suffix
    local notchfilt_filename="${filename}_notch50"
    local output_notchfilt_path="$output_dir/$notchfilt_filename.eeg"

    # Run notch filtering only if output file doesn't exist
    if [ ! -f "$output_notchfilt_path" ]; then
        echo -e "\n50 Hz notch filtering: $input_file -> $output_notchfilt_path" >&2
        eegfiltfilt "$input_file" "$PAR_FOLDER/eeg_filt_notch50.par" "$output_notchfilt_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            return 1
        fi
    fi

    # Return the notch filtered file path
    echo "$output_notchfilt_path"
}


apply_lowpass_filter() {
    # apply_lowpass_filter
    # -------------------
    # Applies a 40 Hz low-pass filter to an EEG file.
    #
    # Arguments:
    #   1. input_file : Path to the EEG file (.eeg)
    #   2. output_dir : Directory where the low-pass filtered EEG file will be saved
    #
    # Behavior:
    #   - Constructs the output filename by appending '_lp40' to the input file’s base name.
    #   - Checks if the low-pass filtered file already exists to avoid recomputation.
    #   - Applies low-pass filtering using 'eegfiltfilt' with the 40 Hz low-pass parameter file.
    #   - Returns the full path of the low-pass filtered EEG file.
    local input_file=$1
    local output_dir=$2

    # Extract base filename without extension
    local filename
    filename=$(basename "$input_file" .eeg)

    # Build output filename with _lp40 suffix
    local lp40filt_filename="${filename}_lp40"
    local output_lp40filt_path="$output_dir/$lp40filt_filename.eeg"

    # Run low-pass filtering only if output file doesn't exist
    if [ ! -f "$output_lp40filt_path" ]; then
        echo -e "\n40 Hz low-pass filtering: $input_file -> $output_lp40filt_path" >&2
        eegfiltfilt "$input_file" "$PAR_FOLDER/eeg_filt_lp40.par" "$output_lp40filt_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            return 1
        fi
    fi

    # Return the low-pass filtered file path
    echo "$output_lp40filt_path"
}
