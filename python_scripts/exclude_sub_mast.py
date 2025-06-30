import os
import pandas as pd
from pathlib import Path

from preprocessing_information_file_over_all import create_preprocessing_information_df

def exclude_sub_mast(sub_list):
    """
    Evaluates whether each subject in the list should be excluded based on mastoid channel quality,
    using a rejection threshold on response-related trials.

    This function reads `.pos` files containing rejection flags for EEG trials (typically due to 
    artéfacts such as bad mastoid channels), computes the proportion of rejected trials for each 
    subject, and determines whether the subject should be excluded based on a predefined threshold 
    (default: >30% of response trials rejected).
    
    Parameters
    ----------
    sub_list : list of str
        A list of subject IDs to process (e.g., ['sub-AG05AS29']).

    Outputs
    -------
    - Displays the names and numbers of the channels that need interpolation.
    - Saves the results in a CSV file for each subject.
    - Also creates or updates a consolidated CSV file containing results for all subjects.

    """
    
    # Get the bids root dir
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")
    
    # Get the data directory
    derivatives_dir = bids_root / 'derivatives'
    # Define the different threshold
    rej_threshold = 0.3;  # e.g., 30% mean rejection mean the channel should be interpolate

    # Loop through subject to found the one to excludes
    for sub in sub_list:
        print(f"Processing subject: {sub}")

        # Subject to exclude
        exclude = False

        # Get the subject directory and file
        sub_dir = derivatives_dir /  sub
        pos_filepath = sub_dir / 'pos' / f'{sub}_task-{task_name}_eeg_desc-eegavg_ERN_rej_mast.pos'

        if not pos_filepath.exists():
            print(f"File not found: {pos_filepath}")
            continue
        else:
            with open(pos_filepath, 'r') as f:
                tokens = [line.strip().split() for line in f.readlines()]
            
            pos_data = pd.DataFrame(tokens, columns=['Sample', 'code_event', 'Rej_value'])
            pos_data[['code_event', 'Rej_value']] = pos_data[['code_event', 'Rej_value']].apply(pd.to_numeric, errors='coerce')

        # Open the file
        code_fa_rep = [107, 117, 127, 137, 109, 119, 129, 139]
        pos_data_rep = pos_data[pos_data.iloc[:,1].isin(code_fa_rep)]
        total_nb_trial = len(pos_data_rep)
        rej_trial = len(pos_data_rep[pos_data_rep.iloc[:,2] !=0])
        if (rej_trial/total_nb_trial) > rej_threshold:
            exclude = True

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


if __name__ == "__main__":
 
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python exclude_sub_mast.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]

    exclude_sub_mast(sub_list)