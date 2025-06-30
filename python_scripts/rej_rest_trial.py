import os
import pandas as pd

def rej_rest_trial(sub_list):
    """
    For each subject in the provided list, this function modifies a `.pos` file 
    containing EEG event information by rejecting the whole trial if the flanker is rejected.

    Specifically, it:
    - Loads the subject's rejection file from the EEG flanker task.
    - Identifies events that follow a flanker event (codes 100, 110, 120, 130) 
      and marks them with a rejection code (value 8).
    - Saves the updated data in a new `.pos` file with the add of the suffix "_alltrial" in the filename.

    Parameters:
    -----------
    sub_list : list of str
        List of subject identifiers (e.g., ["sub-AL08AS02"]).
    """
    # Get the current working directory
    bids_root = os.getenv("DATA_PATH")
    task_name = os.getenv("TASK_NAME")

    # Get the data directory
    data_dir = os.path.join(bids_root, 'derivatives')

    # Loop through subject to found the electrodes to interpolate
    for sub in sub_list:
        print(f"Processing subject: {sub}")

        # Get the subject directory and file
        sub_dir = os.path.join(data_dir, sub)
        pos_filename = os.path.join(
            sub_dir, 'pos',
            f'{sub}_task-{task_name}_eeg_desc-eegavg_ERN_rej.pos'
        )

        if not os.path.exists(pos_filename):
            print(f"File not found: {pos_filename}")
            continue
        
        list_flanker_code = [100, 110, 120, 130]
        df = pd.read_csv(pos_filename, sep=r'\s+', header=None)
        print(df)
        i = 0
        while i < len(df):
            if df.iloc[i, 1] in list_flanker_code and df.iloc[i, 2] == 8:
                i += 1
                while i < len(df) and df.iloc[i, 1] not in list_flanker_code:
                    df.iloc[i, 2] = 8
                    i += 1
            else:
                i += 1
                
        # Save
        output_pos = os.path.join(
            sub_dir, 'pos',
            f'{sub}_task-{task_name}_eeg_desc-eegavg_ERN_rej_alltrial.pos'
        )
        with open(output_pos, 'w') as f:
            for row in df.itertuples(index=False):
                f.write(f'{row[0]:>11}{row[1]:>6}{row[2]:>6}\n')

def main():
       
    import sys

    # Check if there are command-line arguments passed
    if len(sys.argv) < 2:
        print("Usage: python rej_rest_trial.py sub-01 sub-02 ...")
        sys.exit(1)

    # Get the subject(s) from the command-line arguments
    sub_list = sys.argv[1:]

    # If only one subject is passed, pass it as a list
    if len(sub_list) == 1:
        sub_list = [sub_list[0]]
    
    # Process subjects
    rej_rest_trial(sub_list)

if __name__ == "__main__":
    main()
        
