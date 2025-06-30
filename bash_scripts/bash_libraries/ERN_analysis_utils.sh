#!/bin/bash

extract_ern_values() {
    # extract_ern_values
    # ------------------
    # Runs a Python script to extract ERN (Error-Related Negativity) values for a given subject.
    #
    # Arguments:
    #   1. Subject identifier (e.g., subject ID)
    #
    # Behavior:
    #   - Calls the Python script 'get_ERN_values.py' located in the current directory,
    #     passing the subject ID as an argument.
    #   - Logs output and errors to a dedicated log file in the log directory.
    #   - Prints status messages to stderr indicating success or failure.
    #
    # Usage example:
    #   extract_ern_values "sub-01"

    local subj=$1

    local python_extract_ern_values_script="$PYTHON_SCRIPTS/get_ERN_values.py"
    local extract_ern_values_log="${log_dir}/get_ERN_values.log"

    echo -e "\n     [ERN Extraction] Extracting ERN values for subject ${subj}..." >&2
    $PYTHON_EXECUTABLE "$python_extract_ern_values_script" "${subj}" > "$extract_ern_values_log" 2>&1
    exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo -e "\n     [ERN Extraction] Error during ERN extraction, check log: $extract_ern_values_log" >&2
        return 1
    fi

}

run_stats_analysis() {
    # run_stats_analysis
    # ------------------
    # Executes the statistical analysis Python script and logs the output.
    #
    # Behavior:
    #   - Runs the Python script located at $PYTHON_SCRIPTS/stats_analysis.py
    #   - Redirects stdout and stderr to a log file $general_log/stats_analysis.log
    local python_stats_analysis_script="$PYTHON_SCRIPTS/stats_analysis.py"
    local stats_analysis_log_file="${general_log}/stats_analysis.log"

    echo "[Stats Analysis] Running statistical analysis..." >&2
    $PYTHON_EXECUTABLE "$python_stats_analysis_script" > "$stats_analysis_log_file" 2>&1
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "\n     [Stats Analysis] Error during statistical analysis. Check log: $stats_analysis_log_file" >&2
        return 1
    fi

}
