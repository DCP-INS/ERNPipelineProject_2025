#!/bin/bash
print_banner() {
    local term_width=$(tput cols)             # get terminal width
    local text="$1"
    local text_len=${#text}
    local padding=$(( (term_width - text_len) / 2 ))

    # print top border
    printf '=%.0s' $(seq 1 $term_width)
    echo

    # print centered text with padding spaces before it
    printf '%*s%s\n' $padding '' "$text"

    # print bottom border
    printf '=%.0s' $(seq 1 $term_width)
    echo
}
init_subject_dirs() {
    # Initializes directory structure and path variables for a given subject.
    #
    # Arguments:
    #   subj - Subject identifier (e.g., sub-01)
    #
    # Creates necessary output folders under the derivatives directory:
    #   - derivatives/subj/
    #   - derivatives/subj/eeg/
    #   - derivatives/subj/pos/
    #   - derivatives/subj/par/
    #   - derivatives/subj/log/
    #   - derivatives/subj/ica/
    #
    # Also defines and exports the following path variables for downstream use:
    #   source_eeg_dir  - Path to the raw EEG data folder of the subject
    #   subj_dir        - Base derivatives directory for the subject
    #   output_dir      - Directory for processed EEG data
    #   pos_outdir      - Directory for position-related outputs
    #   par_outdir      - Directory for parameter files or similar outputs
    #   log_dir         - Directory for logs
    #   ica_dir         - Directory for ICA results
    subj=$1
    source_eeg_dir="$DATA_PATH/$subj/eeg"
    
    subj_dir="$DATA_PATH/derivatives/$subj"
    mkdir -p "$subj_dir"
    
    output_dir="$subj_dir/eeg"
    mkdir -p "$output_dir"
    
    pos_outdir="$subj_dir/pos"
    mkdir -p "$pos_outdir"
    
    par_outdir="$subj_dir/par"
    mkdir -p "$par_outdir"
    
    log_dir="$subj_dir/log"
    mkdir -p "$log_dir"
    
    ica_dir="$subj_dir/ica"
    mkdir -p "$ica_dir"

    general_log="$DATA_PATH/derivatives/log"
    mkdir -p "$general_log"
    
    # Export variables to be used outside the function
    export source_eeg_dir
    export subj_dir
    export output_dir
    export pos_outdir
    export par_outdir
    export log_dir
    export ica_dir
    export general_log
}


get_nb_samples() {
    # get_nb_samples
    # --------------
    # Extracts the value of the 'nb_samples' column from the second line of a CSV file.
    # The CSV file is expected to have a semicolon (;) delimiter and a header line.
    #
    # Arguments:
    #   1. Path to the CSV file
    #
    # Behavior:
    #   - Checks if the CSV file exists; exits with error if not found
    #   - Finds the column index of the header named 'nb_samples'
    #   - If the 'nb_samples' column is missing, exits with error
    #   - Prints the value from the 'nb_samples' column of the second line (first data row)
    #
    # Usage:
    #   nb_samples=$(get_nb_samples path/to/file.csv)
    #
    local csv_file=$1

    if [[ ! -f "$csv_file" ]]; then
        echo "Error: File not found: $csv_file" >&2
        return 1
    fi

    local col_index
    col_index=$(head -1 "$csv_file" | tr ';' '\n' | grep -n '^nb_samples$' | cut -d: -f1)

    if [[ -z "$col_index" ]]; then
        echo "Error: 'nb_samples' column not found in $csv_file" >&2
        return 1
    fi

    local nb_samples
    nb_samples=$(awk -F';' -v col="$col_index" 'NR==2 {print $col}' "$csv_file")

    echo "$nb_samples"
}
