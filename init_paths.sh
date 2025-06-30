#!/bin/bash

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define the dataset path relative to current directory
path_data="$SCRIPT_DIR/../ERN/data" # TO UPDATE
export DATA_PATH="$path_data"

# Define path to the 'par' folder (parameters or config)
par_folder="$SCRIPT_DIR/par"
export PAR_FOLDER="$par_folder"

# Define the task name
task_name='Flanker'
export TASK_NAME=$task_name

# Detect available Python executable (prefer python3 if available) TO UPDATE IF NEEDED
if command -v python3 &> /dev/null; then
    export PYTHON_EXECUTABLE=$(command -v python3)
elif command -v python &> /dev/null; then
    export PYTHON_EXECUTABLE=$(command -v python)
else
    echo "Error: Python is not installed or not in PATH."
    exit 1
fi

export PYTHON_SCRIPTS="$SCRIPT_DIR/python_scripts"
export BASH_SCRIPTS="$SCRIPT_DIR/bash_scripts"
export BASH_LIBRARIES="$BASH_SCRIPTS/bash_libraries"

