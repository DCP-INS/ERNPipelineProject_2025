import os
from pathlib import Path
import mne
import mne_bids
import pandas as pd
from preprocessing_information_file_over_all import create_preprocessing_information_df

mne.set_log_level('error')

def convert_set_to_edf(set_file, bids_root, subject, eeg_sub_dir, evt_dict):
    """
    Convert an EEGLAB .set file to .edf format and create a corresponding .pos file.
    
    Parameters:
    set_file (Path): Path to the .set file.
    subject (str): Subject name
    eeg_sub_dir (Path): Directory where the .edf file will be saved.
    evt_dict (dict): Dictionary mapping event codes.
    """
    edf_file = eeg_sub_dir / f'{set_file.stem}.edf'
    if not edf_file.exists():
        raw = mne.io.read_raw_eeglab(set_file, preload=True)
        sampling_rate = raw.info['sfreq']
        raw = mne.add_reference_channels(raw, ref_channels=['FCz'])
        raw.export(edf_file, fmt='edf', overwrite=True)
        print(set_file, '->', f'{set_file.stem}.edf', '(', raw.info['nchan'], 'chan')
        
        # Create .pos file
        evts, _ = mne.events_from_annotations(raw, evt_dict, verbose='error')
        pos_file = eeg_sub_dir / f'{set_file.stem}.pos'
        pos_data = pd.DataFrame({'sample': evts[:, 0], 'code_evt': evts[:, 2], 'code_rej': 0})
        pos_data = rej_cut_trials(pos_data, sampling_rate)
        pos_data.to_csv(pos_file, sep=' ', header=False, index=False)
        print('   and', pos_data.shape[0], 'evts ->', pos_file)

        # Save number of samples
        save_nb_samples(subject, bids_root, raw.n_times)
    else:
        print(f'The edf files {edf_file} already exists, pass')

def process_subjects(bids_root, Sujlist, evt_dict):
    """
    Process multiple subjects by converting their .set files to .edf and generating .pos files.
    
    Parameters:
    bids_root (Path): Root directory of the BIDS dataset.
    Sujlist (list): List of subject IDs to process.
    evt_dict (dict): Dictionary mapping event codes.
    """
    for subject in Sujlist:
        eeg_sub_dir = bids_root / f'{subject}' / 'eeg'
        set_files = list(eeg_sub_dir.glob("*.set"))
        for set_file in set_files:
            convert_set_to_edf(set_file, bids_root, subject, eeg_sub_dir, evt_dict)

def rej_cut_trials(pos_data, fs):
    """
    pos_data: pandas DataFrame where
      - col 0 = sample number (int)
      - col 1 = code (int)
      - col 2 = rej vamue (int)
    fs: sampling frequency in Hz
    """
    bad_code = [88, 222]
    code_rep = [106, 116, 126, 136, 108, 118, 128, 138,
                107, 117, 127, 137, 109, 119, 129, 139]
    code_flanker = [100, 110, 120, 130]

    half_window_samples = int(0.5 * fs)  # 500 ms before and after = 0.5 s * fs

    # Iterate over DataFrame rows
    for i, row in pos_data.iterrows():
        sample = row.iloc[0]
        code = row.iloc[1]

        if code in code_rep:
            # Define window range around this sample
            start_sample = sample - half_window_samples
            end_sample = sample + half_window_samples

            # Find rows within this window
            window_rows = pos_data[(pos_data.iloc[:,0] >= start_sample) & (pos_data.iloc[:,0] <= end_sample)]

            # Check if any code in window is in bad_code
            if any(window_rows.iloc[:,1].isin(bad_code)):
                pos_data.at[i, pos_data.columns[2]] = 9

                # Now find the last flanker event before this rep
                # Filter all rows before current sample
                previous_rows = pos_data[pos_data.iloc[:,0] < sample]

                # Among those, find rows with flanker codes
                flanker_rows = previous_rows[previous_rows.iloc[:,1].isin(code_flanker)]

                if not flanker_rows.empty:
                    # Get the sample of the last flanker before the rep
                    last_flanker_sample = flanker_rows.iloc[-1, 0]

                    # Find all rows between last flanker and current rep sample (inclusive)
                    to_mark = pos_data[(pos_data.iloc[:,0] >= last_flanker_sample) & (pos_data.iloc[:,0] <= sample)]

                    # Set their rej value to 9
                    pos_data.loc[to_mark.index, pos_data.columns[2]] = 9

    return pos_data

def save_nb_samples(sub, bids_root, nb_samples):
    """
    Save the number of EEG samples for a subject in both the global and individual preprocessing info files.
    """
    # Create the different directory and path
    derivatives_dir = bids_root / 'derivatives'
    derivatives_dir.mkdir(parents=True, exist_ok=True)
    global_file = derivatives_dir / 'preprocessing_information.csv'
    subject_dir = derivatives_dir / sub
    subject_dir.mkdir(exist_ok=True)
    subject_file = subject_dir / f'{sub}_task-Flanker_eeg_desc-preprocessing_information.csv'

    # Base info for current subject
    df_subj = create_preprocessing_information_df()
    df_subj.loc[0, 'participant_id'] = sub
    df_subj.loc[0, 'nb_samples'] = nb_samples

    # Update global file
    if global_file.exists():
        df_all = pd.read_csv(global_file, sep=';')
        if sub in df_all['participant_id'].values:
            df_all.loc[df_all['participant_id'] == sub, 'nb_samples'] = nb_samples
        else:
            df_all = pd.concat([df_all, df_subj], ignore_index=True)
    else:
        df_all = df_subj

    df_all.to_csv(global_file, sep=';', index=False)

    # Save individual subject file
    if subject_file.exists():
        df_subj_existing = pd.read_csv(subject_file, sep=';')
        df_subj_existing['nb_samples'] = nb_samples
        df_subj = df_subj_existing
    
    df_subj.to_csv(subject_file, sep=';', index=False)
    

def main():

    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python convert_set2edf.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    Sujlist = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(Sujlist) == 1:
        Sujlist = [Sujlist[0]]

    # Define BIDS root directory
    bids_root = Path(os.getenv("DATA_PATH"))
    
    # Get subject list
    print(f'The subject list:', Sujlist)
    
    # Dictionary of events
    evt_dict = {str(i): i for i in range(6, 140)}
    evt_dict.update({'boundary': 222})
    
    # Process subjects
    process_subjects(bids_root, Sujlist, evt_dict)

if __name__ == "__main__":
    main()
