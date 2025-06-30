import numpy as np
import mne
import os
from pathlib import Path

import libraries.elan.elan_utils as elan_func

def save_single_trial_epo(sub, interpol = False):
    """
    Extracts and saves clean single-trial EEG epochs for the ERN (Error-Related Negativity) analysis 
    from ELAN-formatted `.eeg` and `.pos` files for a subject.

    Parameters
    ----------
    sub_list : str
        Subject identifiers (e.g., 'sub-01').
    interpol: bool, default=False
        To know if some electrode of the subject have been interpoled

    Functionality
    -------------
    - Loads preprocessed EEG data and corresponding event marker files.
    - Applies a predefined montage (ensuring FCz is included).
    - Converts ELAN EEG data to MNE-Python format using custom utilities.
    - Extracts epochs time-locked to specific response codes.
    - Filters out trials marked for rejection.
    - Saves the cleaned single-trial epochs in `.fif` format under the subject's `ERN` directory.

    Assumptions
    -----------
    - The EEG file is named: {sub}_task-{task_name}_eeg_desc-hp_ref_notch50_lp40_icacor.eeg
    - The event file is named: {sub}_task-{task_name}_eeg_desc-eegavg_ERN_rej_flanker_alltrial_rej_rep.pos
    - A valid `channels.tsv` file with channel locations is located at ../ERN/data/.

    Raises
    ------
    FileNotFoundError
        If any of the expected EEG, POS, or montage files are missing.

    Output
    ------
    Saves cleaned epochs for each response code to:
        {subject_dir}/ERN/{sub}_task-{task_name}_eeg_desc-single_trial-epo.fif
    """
    
    # Define root directories
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")
    derivatives_dir = bids_root / 'derivatives'
    montage_file = bids_root / 'channels.tsv'
    sub_dir = derivatives_dir / sub

    # Define file paths
    if interpol == True:
        eeg_file = sub_dir / 'eeg' / f"{sub}_task-{task_name}_eeg_desc-hp_ref_notch50_lp40_icacor_eegspline.eeg"
    else:
        eeg_file = sub_dir / 'eeg' / f"{sub}_task-{task_name}_eeg_desc-hp_ref_notch50_lp40_icacor.eeg"
    pos_file = sub_dir / 'pos' / f"{sub}_task-{task_name}_eeg_desc-eegavg_ERN_rej_flanker_alltrial_rej_rep.pos"

    # Check that files exist
    for file_path in [eeg_file, pos_file, montage_file]:
        if not file_path.exists():
            raise FileNotFoundError(f"Missing file: {file_path}")

    # Add FCz to montage if needed
    elan_func.add_FCz_montage(montage_file)

    # Load raw data
    raw = elan_func.elan_eeg_to_mne(eeg_file, montage_file, ent_file=None, pos_file=pos_file)

    # Get the events and format them
    events = mne.read_events(pos_file)
    reject_event = events[:, 2]  # rejection flags
    mne_events = np.column_stack((events[:, 0], np.zeros(len(events), dtype=int), events[:, 1]))

    # Create epochs
    epochs = mne.Epochs(raw, events=mne_events, event_repeated='drop', event_id=None, tmin=-0.5, tmax=0.5, baseline=None)

    ERP_dir = sub_dir / 'ERP'
    ERP_dir.mkdir(parents=True, exist_ok=True)

    fast_rep_code = {'107': 'FaCR0',
                     '117': 'FaCR33', 
                     '127': 'FaCR66', 
                     '137': 'FaCR100', 
                     '109': 'FaIR0', 
                     '119': 'FaIR33', 
                     '129': 'FaIR66', 
                     '139': 'FaIR100',
                     '106': 'SlCR0',
                     '116': 'SlCR33', 
                     '126': 'SlCR66', 
                     '136': 'SlCR100', 
                     '108': 'SlIR0', 
                     '118': 'SlIR33', 
                     '128': 'SlIR66', 
                     '138': 'SlIR100'}

    for rep_code, rep_id in fast_rep_code.items():
        # Define path to save
        all_trial_epoch_path = ERP_dir / f"{sub}_task-{task_name}_eeg_desc-event-ERP_{rep_id}_SingleTrial-epo.fif"

        if not all_trial_epoch_path.exists():
            if int(rep_code) in np.unique(events[:, 1]):
                print(f'\nSaving single trials for code: {rep_code}')
                
                # Get target epochs
                target_epochs = epochs[rep_code]

                # Find indices in original events
                target_indices = epochs.selection[epochs.events[:, 2] == epochs.event_id[rep_code]]

                # Get reject flags for selected trials
                reject_flags_for_target = reject_event[target_indices]

                # Keep only trials with reject flag == 0
                
                clean_target_epochs = target_epochs[reject_flags_for_target == 0]
                print(clean_target_epochs)

                # Save               
                if len(clean_target_epochs.events) > 0:
                    clean_target_epochs.save(all_trial_epoch_path, overwrite=True)
                    print(f'Single trials epoch of subject {sub} saved at {all_trial_epoch_path}.')
                else:
                    print(f"No valid epochs to save for {all_trial_epoch_path}")


if __name__ == "__main__":
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 3:
        print("Usage: python save_single_trial_epo.py sub-01 to_interpol")
        sys.exit(1)

    # Get the subject from the command-line arguments
    sub = sys.argv[1]
    interpol = sys.argv[2]

    save_single_trial_epo(sub, interpol)