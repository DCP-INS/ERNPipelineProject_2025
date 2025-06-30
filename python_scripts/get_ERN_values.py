import os
from pathlib import Path
import pandas as pd
import numpy as np

# Local utilities
import libraries.elan.elan_utils as elan_func

def get_ERN_values(sub_list):
    """
    Extracts ERN-related values for a list of participants and saves results.

    This function processes EEG data in `.p` format for each subject in `sub_list`, 
    corresponding to ERN (Error-Related Negativity) conditions during a {task_name} task. 
    For each condition, it:

    - Loads averaged ERP epochs from ELAN `.p` files.
    - Applies electrode montage.
    - Extracts FCz signal between 50–150 ms post-onset.
    - Computes the mean of the smallest 10% of amplitudes within this window.
    - Saves the result in a condition-wise CSV file.
    - Plots and saves the ERP waveform (evoked response) per condition.

    Parameters
    ----------
    sub_list : list of str
        List of participant identifiers (e.g., ["sub-AG04EN28"]).

    Notes
    -----
    - This function assumes the presence of:
        - `channels.tsv` in the BIDS root folder for electrode positions.
        - Preprocessed metadata CSVs per subject.
        - Precomputed `.p` files containing averaged epochs in `derivatives/<sub>/ERN/`.
    - ERN conditions are derived from combinations of speed and congruency levels.
    - Only includes values if the number of CR trials > 15 and IR trials > 8.
    - Results are stored under each subject's derivatives directory.
    """

    # Configuration
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")
    montage_file = bids_root / 'channels.tsv'
    derivatives_dir = bids_root / 'derivatives'

    congru_list = ['', '0', '33', '66', '100']
    speed_list = ['Fa']

    all_ern_codes = {
        'FaCR0': ['107'], 'FaIR0': ['109'],
        'FaCR33': ['117'], 'FaIR33': ['119'],
        'FaCR66': ['127'], 'FaIR66': ['129'],
        'FaCR100': ['137'], 'FaIR100': ['139'],
        'FaCR': ['107', '117', '127', '137'],
        'FaIR': ['109', '119', '129', '139']
    }

    # Processing
    for sub in sub_list:
        print(f"Processing subject: {sub}\n")

        sub_dir = derivatives_dir / sub
        ERN_dir = sub_dir / 'ERN'

        # Preprocessing info
        preprocessing_path = sub_dir / f'{sub}_task-{task_name}_eeg_desc-preprocessing_information.csv'
        preprocessing_df = pd.read_csv(preprocessing_path, sep=';')

        # Results CSV path
        results_path = sub_dir / f'{sub}_task-{task_name}_eeg_desc-ERN_values.csv'
        results_df = pd.read_csv(results_path, sep=';') if results_path.exists() else pd.DataFrame(columns=['participant_id', 'ERN', 'mean_around_min'])

        for speed in speed_list:
            for congru in congru_list:
                ERN_cond = f'{speed}IR-CR{congru}'
                print(f' Running condition {ERN_cond}')
                p_file = ERN_dir / f'{sub}_desc-ERN_{ERN_cond}.p'

                if not p_file.exists():
                    print(f"Warning: file not found: {p_file}")

                    # Append or update results
                    mean_around_min = 'n/a'
                    new_entry = pd.DataFrame.from_records([{
                        'participant_id': sub,
                        'ERN': ERN_cond,
                        'mean_around_min': mean_around_min
                    }])

                else:

                    # Load epochs
                    epochs = elan_func.elan_p_to_epoch_mne(p_file, montage_file)
                    evoked = epochs.average()

                    # Plot evoked response
                    plot_path = ERN_dir / f'{sub}_task-{task_name}_eeg_desc-ERN_{ERN_cond}.png'
                    fig = evoked.plot(spatial_colors=True, show=False)
                    fig.savefig(plot_path)

                    # Trial count for validation
                    code_CR = all_ern_codes.get(f'{speed}CR{congru}', [])
                    code_IR = all_ern_codes.get(f'{speed}IR{congru}', [])

                    try:
                        nb_trials_CR = sum(int(preprocessing_df[code].iloc[0].split('|')[0]) for code in code_CR if code in preprocessing_df.columns)
                        nb_trials_IR = sum(int(preprocessing_df[code].iloc[0].split('|')[0]) for code in code_IR if code in preprocessing_df.columns)
                    except Exception as e:
                        print(f"Error processing trial counts for {ERN_cond}: {e}")
                        continue
                    
                    if ERN_cond == 'FaIR-CR':
                        min_trials = 30
                    else:
                        min_trials = 8
                    if nb_trials_CR > min_trials and nb_trials_IR > min_trials:
                        # Extract FCz data from 50 to 150 ms
                        try:
                            data = evoked.copy().pick('FCZ').data[0]  # (n_channels=1, n_times)
                            times = evoked.times * 1000  # convert to ms
                            mask = (times >= 50) & (times <= 150)
                            # Find index of minimum in that window
                            window_data = data[mask]
                            window_times = times[mask]
                            min_idx_in_window = np.argmin(window_data)
                            min_time = window_times[min_idx_in_window]

                            # Find global index of min sample
                            min_sample = np.where(times == min_time)[0][0]

                            # Define ±20 ms window around that index
                            window_range = 20  # in ms
                            sampling_interval = np.mean(np.diff(times))  # assume uniform spacing
                            samples_around = int(window_range / sampling_interval)

                            start_idx = max(min_sample - samples_around, 0)
                            end_idx   = min(min_sample + samples_around + 1, len(data))

                            # Compute mean in that window
                            mean_around_min = round(np.mean(data[start_idx:end_idx]), 3)
                            preprocessing_df.loc[0, f'{ERN_cond}_stats'] = 'inclus'
                        except Exception as e:
                            print(f"Error computing mean_around_min: {e}")
                            mean_around_min = 'n/a'
                            preprocessing_df.loc[0, f'{ERN_cond}_stats'] = 'exclude'
                    else:
                        mean_around_min = 'n/a'
                        preprocessing_df.loc[0, f'{ERN_cond}_stats'] = 'exclude'


                    # Append or update results
                    new_entry = pd.DataFrame.from_records([{
                        'participant_id': sub,
                        'ERN': ERN_cond,
                        'mean_around_min': mean_around_min
                    }])

                if ERN_cond in results_df['ERN'].values:
                    results_df.loc[results_df['ERN'] == ERN_cond, 'mean_around_min'] = mean_around_min
                else:
                    results_df = pd.concat([results_df, new_entry], ignore_index=True)

        # Save updated results
        results_df.to_csv(results_path, sep=';', index=False)
        preprocessing_df.to_csv(preprocessing_path, sep=';', index=False)

        # Save preprocessing information (exclusion of subject for the different conditions)
        global_file = derivatives_dir / 'preprocessing_information.csv'

        # Update global file
        if global_file.exists():
            df_all = pd.read_csv(global_file, sep=';')
            if sub in df_all['participant_id'].values:
                for speed in speed_list:
                    for congru in congru_list:
                        ERN_cond = f'{speed}IR-CR{congru}'
                        df_all.loc[df_all['participant_id'] == sub, f'{ERN_cond}_stats'] = preprocessing_df.loc[0, f'{ERN_cond}_stats']
            else:
                df_all = pd.concat([df_all, preprocessing_df], ignore_index=True)
        else:
            df_all = preprocessing_df

        df_all.to_csv(global_file, sep=';', index=False)

    

if __name__ == "__main__":
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python get_ERN_values.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]
    
    # Process subjects
    get_ERN_values(sub_list)