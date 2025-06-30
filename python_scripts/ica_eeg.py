import os
from pathlib import Path
import pandas as pd
import mne
from mne.preprocessing import ICA
import numpy as np

from preprocessing_information_file_over_all import create_preprocessing_information_df
import libraries.ica.ica_utils as ica_func
import libraries.elan.elan_utils as elan_func

def run_ica_eeg(sub_list):
    """
    Process EEG data for one subject: load, clean, ICA, save results and info.
    
    Parameters:
    -----------
    sub_list : list
        list of subject identifier, e.g. 'sub-AG04EN28'.
    """
    # Define root directories
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")

    # Define the derivatives directory
    derivatives_dir = bids_root / 'derivatives'
    
    for sub in sub_list:
        print(f"Do ICA for subject: {sub}\n")
        sub_dir = derivatives_dir / sub

        # Define file paths
        montage_file = bids_root / 'channels.tsv'
        eeg_file = sub_dir / 'eeg' / f"{sub}_task-{task_name}_eeg_desc-hp_ref_notch50_lp40.eeg"

        pos_file = bids_root / sub / 'eeg' / f"{sub}_task-{task_name}_eeg.pos"

        # Check that files exist
        for file_path in [eeg_file, pos_file, montage_file]:
            if not file_path.exists():
                raise FileNotFoundError(f"Missing file: {file_path}")

        # Add FCz to montage if needed
        elan_func.add_FCz_montage(montage_file)

        # Load raw data
        raw = elan_func.elan_eeg_to_mne(eeg_file, montage_file, ent_file=None, pos_file=pos_file)

        # Detect bad channels
        raw.info['bads'] = mne.preprocessing.find_bad_channels_lof(raw, picks='eeg', threshold=3)

        # Prepare ICA
        n_eeg = raw.get_channel_types().count('eeg')
        n_bad = len(raw.info['bads'])
        n_components = n_eeg - n_bad
        if n_components <= 0:
            raise ValueError(f"No good EEG channels left after marking bads for {sub}.")

        ica = ICA(n_components=n_components, method='infomax', random_state=97, max_iter=800)
        ica.fit(raw)

        # Find EOG-related ICA components
        eog_idx, _ = ica.find_bads_eog(raw, measure='correlation', threshold = 0.7)

        eog_idx_elan = [idx + 1 for idx in eog_idx]
        print('Ica component: ', eog_idx_elan)

        # Create output folder for ICA results
        output_ica_dir = sub_dir / 'ica'
        output_ica_dir.mkdir(exist_ok=True, parents=True)

        # Save ICA components topographies
        topo_figs = ica.plot_components(show=False)

        for i, fig in enumerate(topo_figs, start=1):
            topo_path = output_ica_dir / f'{sub}_task-{task_name}_eeg_desc-ica_components_topo_{i}.png'
            fig.savefig(topo_path)

        # Get good EEG channels indices (1-based)
        rankchanlist = ica_func.get_good_eeg_indices(raw)

        # Get the transformation matrix
        transf_matrix = np.dot(
                ica.unmixing_matrix_, ica.pca_components_[: ica.n_components_]
            )
        
        # Save ICA unmixing matrix in XML format
        xml_path = output_ica_dir / f'{sub}_task-{task_name}_eeg_desc-ica_transf_matrix.xml'
        ica_func.writeTmatrixXMLformat(
            nbtotchan=len(raw.ch_names),
            nbusedchan=n_components,
            nbsources=ica.n_components,
            rankchanlist=rankchanlist,
            matrix=transf_matrix,
            filename=xml_path
        )

        # Save preprocessing information (bad channels & ICA components used)
        global_file = derivatives_dir / 'preprocessing_information.csv'
        subject_file = sub_dir / f'{sub}_task-{task_name}_eeg_desc-preprocessing_information.csv'

        df_subj = create_preprocessing_information_df()
        df_subj.loc[0, 'participant_id'] = sub
        df_subj.loc[0, 'ch_removed_ICA'] = ', '.join(raw.info['bads'])
        df_subj.loc[0, 'ICA_components_used'] = ', '.join(map(str, eog_idx_elan))

        # Update global file
        if global_file.exists():
            df_all = pd.read_csv(global_file, sep=';')
            if sub in df_all['participant_id'].values:
                df_all.loc[df_all['participant_id'] == sub, 'ch_removed_ICA'] = ', '.join(raw.info['bads'])
                df_all.loc[df_all['participant_id'] == sub, 'ICA_components_used'] = ', '.join(map(str, eog_idx_elan))
            else:
                df_all = pd.concat([df_all, df_subj], ignore_index=True)
        else:
            df_all = df_subj

        df_all.to_csv(global_file, sep=';', index=False)

        # Save individual subject file
        if subject_file.exists():
            df_subj_existing = pd.read_csv(subject_file, sep=';')
            df_subj_existing['ch_removed_ICA'] = ', '.join(raw.info['bads'])
            df_subj_existing['ICA_components_used'] = ', '.join(map(str, eog_idx_elan))
            df_subj = df_subj_existing

        df_subj.to_csv(subject_file, sep=';', index=False)

        print(f"Processing for {sub} done.")

if __name__ == "__main__":
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python ica_eeg.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]
    run_ica_eeg(sub_list)