#!/bin/bash

artifact_rejection_mast(){
    # Runs EEG artifact rejection on mastoids
    # Arguments:
    #   1. Input EEG file path (.eeg)
    #   2. Subject ID
    #   3. Output .pos file path base (without extension)
    local input_file=$1
    local subj=$2
    local output_file_base=$3

    local filename
    filename=$(basename "$input_file" .eeg)
    local filename_base
    filename_base=$(basename "$output_file_base")

    # Generate output paths
    local rejpar_filename="${filename}_eegavg_ERN_rej_mast.par.res"
    local output_rejpar_path="$par_outdir/$rejpar_filename"

    local rejpos_filename="${filename_base}_desc-eegavg_ERN_rej_mast.pos"
    local output_rejpos_path="$pos_outdir/$rejpos_filename"

    # Run artifact rejection if output doesn't exist
    if [ ! -f "$output_rejpar_path" ]; then
        echo -e "\nArtifact rejection on the mastoid for $subj from $input_file:" >&2
        eegavg "$input_file" "${output_file_base}.pos" "$PAR_FOLDER/eegavg_ERN_rej_mast.par" "$output_rejpos_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [Mastoids Rejection] eegavg failed." >&2
            return 1
        fi
        mv "$PAR_FOLDER/eegavg_ERN_rej_mast.par.res" "$output_rejpar_path"
        rm tempo*
    fi

    # Check if subject should be excluded based on rejection
    is_subject_excluded "$subj" "mast"
    exclude_status=$?

    if [ $exclude_status -eq 0 ]; then
        echo -e "\n     [Mastoids Rejection] ${subj} is excluded after mastoid rejection. Skipping further steps." >&2
        return 3
    elif [ $exclude_status -eq 2 ]; then
        echo -e "\n     [Mastoids Rejection] Error occurred during exclusion." >&2
        return 1
    fi

    return 0
}

artifact_rejection_flanker() {
    # Runs EEG artifact rejection around Flanker window
    # Arguments:
    #   1. Input EEG file path (.eeg)
    #   2. Subject ID
    #   3. Output .pos file path base (without extension)

    local input_file=$1
    local subj=$2
    local output_file_base=$3

    local filename
    filename=$(basename "$input_file" .eeg)
    local filename_base
    filename_base=$(basename "$output_file_base")

    # Generate output paths
    local rejpar_filename="${filename}_eegavg_ERN_rej_flanker.par.res"
    local output_rejpar_path="$par_outdir/$rejpar_filename"

    local rejpos_filename="${filename_base}_desc-eegavg_ERN_rej_flanker.pos"
    local output_rejpos_path="$pos_outdir/$rejpos_filename"

    # Run artifact rejection if output doesn't exist
    if [ ! -f "$output_rejpar_path" ]; then
        echo -e "\nArtifact rejection around Flanker for $subj from $input_file:" >&2
        eegavg "$input_file" "${output_file_base}.pos" "$PAR_FOLDER/eegavg_ERN_rej_flanker.par" "$output_rejpos_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [Flanker Rejection] eegavg failed." >&2
            return 1
        fi
        mv "$PAR_FOLDER/eegavg_ERN_rej_flanker.par.res" "$output_rejpar_path"
        rm tempo*
    fi

    # Check if subject should be excluded based on rejection
    is_subject_excluded "$subj" "flanker"
    exclude_status=$?

    if [ $exclude_status -eq 0 ]; then
        echo -e "\n     [Flanker Rejection] ${subj} is excluded after flanker rejection. Skipping further steps." >&2
        return 3
    elif [ $exclude_status -eq 2 ]; then
        echo -e "\n     [Flanker Rejection] Error occurred during exclusion." >&2
        return 1
    fi


    echo $output_rejpos_path
    return 0
}


is_subject_excluded() {
    # Helper function to run exclusion python script and check log
    # Arguments:
    #   1. Subject ID
    #   2. Type of exclusion: should be either "mast" or "flanker"
    # Returns:
    #   0 if the subject is excluded (TO_EXCLUDE=True found in log)
    #   1 if the subject is NOT excluded
    #   2 if the check failed (e.g., Python script error)
    local subj=$1
    local type_func="$2"

    if [[ -z "$subj" || -z "$type_func" ]]; then
        echo "Usage: is_subject_excluded <subject_id> <type: mast|flanker>" >&2
        return 2
    fi

    local exclude_log_file="${log_dir}/exclude_sub_${type_func}.log"
    local exclude_script="$PYTHON_SCRIPTS/exclude_sub_${type_func}.py"

    if [[ ! -f "$exclude_script" ]]; then
        echo "[${type_func} Rejection] ERROR: Script not found: $exclude_script" >&2
        return 2
    fi

    $PYTHON_EXECUTABLE "$exclude_script" "$subj" > "$exclude_log_file" 2>&1
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "\n    [${type_func} Rejection] ERROR during exclusion for subject $subj. Check the log: $exclude_log_file" >&2
        return 2
    fi

    if grep -q "TO_EXCLUDE=True" "$exclude_log_file"; then
        return 0  # excluded
    else
        return 1  # not excluded
    fi
}


artifact_rejection_post_ica() {
    # Perform artifact rejection around response using EEGAVG
    # Arguments:
    #   1. Subject ID
    #   2. EEG file (e.g., *_desc-*.eeg)
    #   3. Input .pos file (e.g., *_desc-*.pos)
    local subj=$1
    local input_eeg=$2
    local input_pos=$3

    local eeg_filename
    eeg_filename=$(basename "$input_eeg" .eeg)
    local pos_filename
    pos_filename=$(basename "$input_pos" .pos)

    local rej_parres_file="${eeg_filename}_eegavg_ERN_rej_rep.par.res"
    local rej_parres_path="$par_outdir/$rej_parres_file"

    local alltrial_pos_file="${pos_filename}.pos"
    local alltrial_pos_path="$pos_outdir/$alltrial_pos_file"

    local rej_pos_file="${pos_filename}_rej_rep.pos"
    local rej_pos_path="$pos_outdir/$rej_pos_file"

    if [ ! -f "$rej_parres_path" ]; then
        echo -e "\n     [Response Rejection] Running EEGAVG on $input_eeg..." >&2
        eegavg "$input_eeg" "$alltrial_pos_path" "$PAR_FOLDER/eegavg_ERN_rej_rep.par" "$rej_pos_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [Response Rejection] eegavg failed." >&2
            return 1
        fi
        mv par/eegavg_ERN_rej_rep.par.res "$rej_parres_path"
        rm -f tempo*
    fi

    # Return the two generated file paths
    echo "$rej_pos_path"
}

artifact_rejection_post_interpo() {
    # Perform artifact rejection around response using EEGAVG
    # Arguments:
    #   1. Subject ID
    #   2. EEG file (e.g., *_desc-*.eeg)
    #   3. Input .pos file (e.g., *_desc-*.pos)
    local subj=$1
    local input_eeg=$2
    local input_pos=$3

    local eeg_filename
    eeg_filename=$(basename "$input_eeg" .eeg)
    local pos_filename
    pos_filename=$(basename "$input_pos" .pos)

    local rej_parres_file="${eeg_filename}_eegavg_ERN_rej_rep.par.res"
    local rej_parres_path="$par_outdir/$rej_parres_file"

    local alltrial_pos_file="${pos_filename}.pos"
    local alltrial_pos_path="$pos_outdir/$alltrial_pos_file"

    local rej_pos_file="${pos_filename}_eegspline_rej_rep.pos"
    local rej_pos_path="$pos_outdir/$rej_pos_file"

    if [ ! -f "$rej_parres_path" ]; then
        echo -e "\n     [Response Rejection] Running EEGAVG on $input_eeg..." >&2
        eegavg "$input_eeg" "$alltrial_pos_path" "$PAR_FOLDER/eegavg_ERN_rej_rep.par" "$rej_pos_path" >&2
        exit_code=$?
        if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
            echo -e "\n     [Response Rejection] eegavg failed." >&2
            return 1
        fi
        mv par/eegavg_ERN_rej_rep.par.res "$rej_parres_path"
        rm -f tempo*
    fi

    # Return the two generated file paths
    echo "$rej_pos_path"
}


document_rejection_and_interpolation() {
    # Document rejection and interpolation for a given subject.
    # Arguments:
    #   1. Subject ID
    local subj=$1

    echo -e "\n     [Documentation] Rejection and interpolation for subject ${subj}:" >&2

    local python_script="$PYTHON_SCRIPTS/preprocessing_information_file_over_all.py"
    local log_file="${log_dir}/preprocessing_information_file_over_all.log"

    $PYTHON_EXECUTABLE "$python_script" "$subj" > "$log_file" 2>&1

    if [[ $? -ne 0 ]]; then
        echo -e "\n     [Documentation] Error while documenting subject $subj. Check log: $log_file" >&2
        return 1
    fi
}
