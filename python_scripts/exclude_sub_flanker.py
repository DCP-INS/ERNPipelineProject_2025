import os
import pandas as pd
import numpy as np
from pathlib import Path

from preprocessing_information_file_over_all import create_preprocessing_information_df

def exclude_sub_flanker(sub_list):
    """
    Evaluates whether each subject in the list should be excluded based on blink-related contamination
    during flanker trials.

    This function analyzes rejection flags from `.pos` files related to flanker trials and determines
    if a subject should be excluded based on the proportion of rejected flanker events. If more than 
    30% of flanker trials are marked as rejected, the subject is flagged for exclusio

    Parameters
    ----------
    sub_list : list of str
        A list of subject IDs to process (e.g., ['sub-AG05AS29']).

    Outputs
    -------
    - Prints whether each subject should be excluded based on flanker trial quality.
    - Updates or creates a consolidated CSV file (`preprocessing_information.csv`) that contains 
      inclusion/exclusion status for all processed subjects.
    - Saves an individual CSV file for each subject with preprocessing details.
    - Calls `rej_rest_trial()` to update rejection information in the `.pos` file as needed.

    """
    
    # Get the bids root dir
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")
    
    # Get the data directory
    derivatives_dir = bids_root / 'derivatives'
    # Define the different threshold
    rej_threshold = 0.3;  # e.g., 30% mean rejection mean the channel should be interpolate

    # Loop through subject to found the one to exludes based on flanker
    for sub in sub_list:
        print(f"Processing subject: {sub}")

        # Subject to exclude
        exclude = False

        # Get the subject directory and file
        sub_dir = derivatives_dir /  sub
        pos_filepath = sub_dir / 'pos' / f'{sub}_task-{task_name}_eeg_desc-eegavg_ERN_rej_flanker.pos'

        if not pos_filepath.exists():
            print(f"File not found: {pos_filepath}")
            continue
        else:
            with open(pos_filepath, 'r') as f:
                tokens = [line.strip().split() for line in f.readlines()]
            
            pos_data = pd.DataFrame(tokens, columns=['Sample', 'code_event', 'Rej_value'])
            pos_data[['code_event', 'Rej_value']] = pos_data[['code_event', 'Rej_value']].apply(pd.to_numeric, errors='coerce')

        # Open the file
        code_flanker = [100, 110, 120, 130]
        pos_data_flanker = pos_data[pos_data.iloc[:,1].isin(code_flanker)]
        total_nb_trial = len(pos_data_flanker)
        rej_trial = len(pos_data_flanker[pos_data_flanker.iloc[:,2] !=0])
        if (rej_trial/total_nb_trial) > rej_threshold:
            exclude = True

        rej_rest_trial(pos_data, pos_filepath)

        print(f'TO_EXCLUDE={exclude}')

        # Save preprocessing information (bad channels & ICA components used)
        global_file = derivatives_dir / 'preprocessing_information.csv'
        subject_file = sub_dir / f'{sub}_task-{task_name}_eeg_desc-preprocessing_information.csv'

        df_subj = create_preprocessing_information_df()
        df_subj.loc[0, 'participant_id'] = sub
        df_subj.loc[0, 'inclusion'] = 'inclus' if exclude == False else 'exclude'

        # Update global file
        if global_file.exists():
            df_all = pd.read_csv(global_file, sep=';')
            if sub in df_all['participant_id'].values:
                df_all.loc[df_all['participant_id'] == sub, 'inclusion'] = 'inclus' if exclude == False else 'exclude'
            else:
                df_all = pd.concat([df_all, df_subj], ignore_index=True)
        else:
            df_all = df_subj

        df_all.to_csv(global_file, sep=';', index=False)

        # Save individual subject file
        if subject_file.exists():
            df_subj_existing = pd.read_csv(subject_file, sep=';')
            df_subj_existing['inclusion'] = 'inclus' if exclude == False else 'exclude'
            df_subj = df_subj_existing

        df_subj.to_csv(subject_file, sep=';', index=False)


def rej_rest_trial(pos_data, pos_filepath):
    """
    Modifies a `.pos` file containing EEG event information by rejecting 
    the rest of the trial following any rejected flanker event.

    Specifically, it:
    - Identifies flanker events (codes 100, 110, 120, 130) that are marked as rejected (code 8).
    - Marks all subsequent events in that trial as rejected (value 8) until the next flanker event.
    - Saves the modified event list to a new `.pos` file, appending "_alltrial" to the original filename.

    Parameters:
    -----------
    pos_data : pandas.DataFrame
        DataFrame with 3 columns: onset (int), event code (int), and rejection code (int).

    pos_filepath : pathlib.Path
        Path to the original `.pos` file; used to determine where to save the updated file.
    """   
    list_flanker_code = [100, 110, 120, 130]
    i = 0
    while i < len(pos_data):
        if pos_data.iloc[i, 1] in list_flanker_code and pos_data.iloc[i, 2] == 8:
            i += 1
            while i < len(pos_data) and pos_data.iloc[i, 1] not in list_flanker_code:
                pos_data.iloc[i, 2] = 8
                i += 1
        else:
            i += 1
            
    # Save
    output_pos = os.path.join(pos_filepath.parent,
        f'{pos_filepath.stem}_alltrial.pos'
    )
    with open(output_pos, 'w') as f:
        for row in pos_data.itertuples(index=False):
            f.write(f'{row[0]:>11}{row[1]:>6}{row[2]:>6}\n')

if __name__ == "__main__":
 
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python exclude_sub_flanker.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]

    exclude_sub_flanker(sub_list)