import os
import pandas as pd
import numpy as np
from pathlib import Path


def find_electrodes_to_interpolate_outlier_rej(sub_list):
    """
    Processes EEG rejection files (.par.res) for a given list of subjects.
    Identifies EEG channels that should be interpolated based on their rejection rates.

    Specifically, the function computes the mean rejection rate per channel and flags channels 
    as candidates for interpolation if their rejection rate is statistically identified as 
    an outlier compared to the rest and superior to min_rej_outlier_elec (e.g., using IQR methods).

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
    
    # Get the current working directory
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")

    # Get the data directory
    data_dir = os.path.join(bids_root, 'derivatives')

    consolidated_results = []

    # For an outlier electrode to be interpolated, it should have at least 10% reject
    min_rej_outlier_elec = 10

    # Loop through subject to found the electrodes to interpolate
    for sub in sub_list:
        print(f"Processing subject: {sub}")

        # Get the subject directory and file
        sub_dir = os.path.join(data_dir, sub)
        par_filename = os.path.join(
            sub_dir, 'par',
            f'{sub}_task-{task_name}_eeg_desc-hp_ref_notch50_lp40_icacor_eegavg_ERN_rej_rep.par.res'
        )

        if not os.path.exists(par_filename):
            print(f"File not found: {par_filename}")
            continue

        # Read all lines
        with open(par_filename, 'r') as f:
            all_lines = f.readlines()

        # Find indices
        start_idx = next(i for i, line in enumerate(all_lines) if '        chan' in line)
        end_idx = next(i for i, line in enumerate(all_lines) if line.startswith('---------------------------------------'))

        # Extract and process the lines
        extract_lines = all_lines[start_idx:end_idx - 1]
        tokens = [line.strip().split() for line in extract_lines]

        # Add artificial 'index' column and build DataFrame
        headers = ['index'] + tokens[0]
        df = pd.DataFrame(tokens[1:], columns=headers)
        # print(df)

        # Replace '----' with NaN and convert columns to float when possible
        df.replace('----', np.nan, inplace=True)
        
        for col in df.columns[2:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        interpchanNames = []
        interpchanNumbers = []
        print(df)
        # Keep only the fast correct and incorrect codes
        columns_of_interest = ['107', '117', '127', '137', '109', '119', '129', '139']
        existing_columns = [col for col in columns_of_interest if col in df.columns]

        # Compute mean rejection per electrode
        mean_rej_elec = {}
        for _, row in df.iterrows():
            chan_name = row['chan']
            values = row[existing_columns].astype(float)
            mean_rej_elec[chan_name] = np.nanmean(values)

        # Found if their is electrode with an outlier rejection 
        outliers = find_outlier_electrodes_iqr(mean_rej_elec)
        
        # If outliers, this electrode need to be interpolated
        if outliers:
            for chan_info in outliers:
                if mean_rej_elec[chan_info] > min_rej_outlier_elec:
                    if '.' in chan_info:
                        name, number = chan_info.split('.')
                        interpchanNames.append(name) # Name before the dot
                        interpchanNumbers.append(int(number)) # Number after the dot

        # Print results
        print("Channels to interpolate (Names):", interpchanNames)
        print("Channels to interpolate (Numbers):", interpchanNumbers)

        # Combine the Channel Names and Channel Numbers into strings
        channels_str = ', '.join(interpchanNames)  # Join the names with a separator (e.g., comma)
        numbers_str = ', '.join(map(str, interpchanNumbers))  # Convert the numbers to strings and join them
        
        # Create result DataFrame with one row for the subject
        result_df = pd.DataFrame({
            'participant_id': [sub],  # Only one row for sub
            'ChannelNames': [channels_str],  # Join all channel names into one string
            'ChannelNumbers': [numbers_str]  # Join all channel numbers into one string
        })

        # Save to subject-specific CSV
        output_file_sub = os.path.join(
            sub_dir, f'{sub}_task-{task_name}_eeg_desc-interpolated_channels.csv'
        )
        print(output_file_sub)
        result_df.to_csv(output_file_sub, index=False, sep = ';')

        # Add to consolidated list
        consolidated_results.append(result_df)

        if not interpchanNames:
            print('TO_INTERPOL=False')
        else:
            print('TO_INTERPOL=True')

def find_outlier_electrodes_iqr(mean_rej_elec):
    """
    Identifies outlier EEG electrodes based on mean rejection rates using the IQR method.

    This function takes a dictionary of mean rejection rates per electrode and detects 
    channels with unusually high rejection rates. An electrode is considered an outlier 
    if its rejection rate is greater than the upper bound defined by:

        upper_bound = Q3 + 1.5 * IQR

    where Q3 is the 75th percentile and IQR is the interquartile range (Q3 - Q1).

    Args:
        mean_rej_elec (dict): A dictionary mapping electrode names (str) to their mean rejection rates (float).

    Returns:
        list: A list of electrode names (str) that are considered outliers.
    """
    values = np.array(list(mean_rej_elec.values()))
    chans = list(mean_rej_elec.keys())

    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1

    upper_bound = q3 + 1.5 * iqr

    outliers = [chans[i] for i, val in enumerate(values) if val > upper_bound]

    return outliers

if __name__ == "__main__":
 
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python find_electrodes_to_interpolate_outlier_rej.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]

    find_electrodes_to_interpolate_outlier_rej(sub_list)