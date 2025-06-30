import os
import pandas as pd
import numpy as np
from pathlib import Path

def create_preprocessing_information_df():
    """
    Crée un DataFrame vide contenant les colonnes nécessaires au suivi du prétraitement EEG.

    Colonnes :
    - participant_id : identifiant du participant
    - inclusion: inclus if the participant is included, else excluded
    - nb_samples: the number of samples in the eeg file
    - ch_removed_ICA : canaux EEG retirés avant ICA (souvent les mastoïdes, VOG, etc.)
    - ICA_components_used : composantes ICA utilisées pour corriger les clignements et les saccades
    - nb_interpoChan : nombre de canaux EEG interpolés après ICA
    - interpoChanNames : noms des canaux interpolés
    - {speed}IR-CR{congru}: inclus if the participant is included in the stats of this ERN, else excluded
    - Colonnes numériques : identifiants d’essais/conditions spécifiques (ex. : 6, 88, 100, ...)

    Returns:
        pd.DataFrame: DataFrame vide prêt à être rempli avec les données de prétraitement.
    """
    columns = [
        'participant_id',
        'inclusion',
        'nb_samples',
        'ch_removed_ICA',
        'ICA_components_used',
        'nb_interpoChan',
        'interpoChanNames',
        'FaIR-CR_stats',
        'FaIR-CR0_stats',
        'FaIR-CR33_stats',
        'FaIR-CR66_stats',
        'FaIR-CR100_stats',
    ]

    # Ajout des colonnes correspondant à des essais ou conditions
    trial_ids = [6, 88, 100, 104, 106, 107, 108, 109, 110, 114, 116, 117, 118, 119,
                 120, 124, 126, 127, 128, 129, 130, 134, 136, 137, 138, 139]

    columns.extend([str(tid) for tid in trial_ids])

    preprocessing_info_df = pd.DataFrame({
        **{col: pd.Series(dtype='object') for col in columns if col != 'nb_samples'},
        'nb_samples': pd.Series(dtype='Int64')  # nullable integer
    })

    return preprocessing_info_df
def preprocessing_information_file_over_all(sub_list):
    """
    Generates or updates a TSV file containing preprocessing information for a list of subjects.

    For each subject in `sub_list`, this function:
    1. Loads the number and names of interpolated EEG channels from a CSV file.
    2. Reads a corresponding POS file and counts the number of accepted events for specific event against their total number.
    3. Compiles this information into a pandas DataFrame.
    4. Appends the subject's preprocessing information to a global TSV file (`preprocessing_information.tsv`)
       in the 'derivatives' directory of the 'ERN' dataset. If the subject is already present in the file,
       their information is updated.

    Parameters:
    -----------
    sub_list : list of str
        List of subject IDs (e.g., ['sub-AG05AS29', 'sub-XY01']).

    Notes:
    ------
    - Requires the following files for each subject:
      - `<subject>_task-{task_name}_eeg_desc-interpolated_channels.csv`
      - `pos/<subject>_task-{task_name}_eeg_desc-eegavg_ERN_rej.pos`
    - The output file `preprocessing_information.tsv` will be created or updated in:
      `<project_root>/../ERN/data/derivatives/`
    - Event codes counted are: '6', '88', '100', ..., '139'.
    """
    for subj in sub_list:
        # Get the current working directory
        bids_root = Path(os.getenv("DATA_PATH"))
        task_name = os.getenv("TASK_NAME")

        # Get the data directory
        derivatives_dir = bids_root / 'derivatives'

        # Get the subject directory
        sub_dir = derivatives_dir / subj

        # Path to the interpolated channels CSV file
        interpolated_channels_sub = sub_dir / f'{subj}_task-{task_name}_eeg_desc-interpolated_channels.csv'

        # Check if the file exists
        if not interpolated_channels_sub.exists():
            print(f"File not found: {interpolated_channels_sub}")
        else:
            # Read the CSV file
            interpolated_channels_df = pd.read_csv(interpolated_channels_sub, sep=';')

            # Ensure 'ChannelNames' column exists
            if 'ChannelNames' in interpolated_channels_df.columns:
                # Drop NaN, convert to string, split by comma, and flatten the list
                interpoChanNames = [
                    chan.strip()
                    for entry in interpolated_channels_df['ChannelNames'].dropna().astype(str)
                    for chan in entry.split(',')
                    if chan.strip()
                ]

                nb_interpoChan = len(interpoChanNames)

                df_subj = create_preprocessing_information_df()
                
                df_subj.loc[0, 'participant_id'] = subj
                df_subj.loc[0, 'nb_interpoChan'] = int(nb_interpoChan)
                df_subj.loc[0, 'interpoChanNames'] = ', '.join(interpoChanNames) if interpoChanNames else 'n/a'

            else:
                print("'ChannelNames' column not found in the CSV file.")

        # Add event-related columns
        event_columns = ['6', '88', '100', '110', '120', '130', '104', '114', '124', '134',
                    '106', '116', '126', '136', '108', '118', '128', '138',
                    '107', '117', '127', '137', '109', '119', '129', '139']
        

        # Read POS file
        if nb_interpoChan == 0:
            pos_filename = sub_dir / 'pos' / f'{subj}_task-{task_name}_eeg_desc-eegavg_ERN_rej_flanker_alltrial_rej_rep.pos'
        else:
            pos_filename = sub_dir / 'pos' / f'{subj}_task-{task_name}_eeg_desc-eegavg_ERN_rej_flanker_alltrial_eegspline_rej_rep.pos'
        if not os.path.exists(pos_filename):
            print(f"File not found: {pos_filename}")
        else:
            with open(pos_filename, 'r') as f:
                tokens = [line.strip().split() for line in f.readlines()]
            
            df = pd.DataFrame(tokens, columns=['Sample', 'code_event', 'Rej_value'])
            df[['code_event', 'Rej_value']] = df[['code_event', 'Rej_value']].apply(pd.to_numeric, errors='coerce')
            
            for event in event_columns:
                mask = (df['code_event'] == int(event)) & (df['Rej_value'] == 0)
                nb_event = mask.sum()
            
                mask_all_trial = (df['code_event'] == int(event))
                nb_all_event = mask_all_trial.sum()

                # Add in df
                df_subj.loc[0, event] = f'{int(nb_event)}|{int(nb_all_event)}'

        # Save or update the output file
        global_file = derivatives_dir / 'preprocessing_information.csv'
        
        if global_file.exists():
            df_all = pd.read_csv(global_file, sep=';')
            if subj in df_all['participant_id'].values:
                df_all.loc[df_all['participant_id'] == subj, 'nb_interpoChan'] = int(nb_interpoChan)
                df_all.loc[df_all['participant_id'] == subj, 'interpoChanNames'] = ', '.join(interpoChanNames) if interpoChanNames else 'n/a'
                for i in event_columns:
                    df_all.loc[df_all['participant_id'] == subj,  i] = df_subj.loc[0, i]
            else:
                df_all = pd.concat([df_all, df_subj], ignore_index=True)
            
        else:
            df_all = df_subj

        df_all.to_csv(global_file, sep=';', index=False, na_rep='n/a')

        # Save one resume file per subject
        subject_file = derivatives_dir / subj / f'{subj}_task-{task_name}_eeg_desc-preprocessing_information.csv'

        # Save individual subject file
        if subject_file.exists():
            df_subj_existing = pd.read_csv(subject_file, sep=';')
            df_subj_existing.loc[0, 'nb_interpoChan'] = int(nb_interpoChan)
            df_subj_existing.loc[0, 'interpoChanNames'] = ', '.join(interpoChanNames) if interpoChanNames else 'n/a'
            for i in event_columns:
                df_subj_existing.loc[0, i] = df_subj.loc[0, i]

            df_subj = df_subj_existing

        df_subj.to_csv(subject_file, sep=';', index=False, na_rep='n/a')



if __name__ == "__main__":
 
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python preprocessing_information_file_over_all.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]

    preprocessing_information_file_over_all(sub_list)