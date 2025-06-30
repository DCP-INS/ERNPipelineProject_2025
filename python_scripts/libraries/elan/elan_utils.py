import neo
import mne
import pandas as pd
import numpy as np
from pathlib import Path
import os
import struct
from typing import Tuple, Dict, Any, Optional

def elan_eeg_to_mne(eeg_file, montage_file, ent_file = None, pos_file = None):
    """
    Convertit un fichier ELAN (.eeg) en objet Raw de MNE-Python.

    Cette fonction lit les données EEG enregistrées au format ELAN à l'aide de Neo, 
    crée un objet `RawArray` de MNE, et y associe un montage de capteur personnalisé 
    (fichier TSV).

    Paramètres
    ----------
    eeg_file : str ou Path
        Chemin vers le fichier .eeg (ELAN) contenant les données EEG brutes.
    montage_file : str ou Path
        Chemin vers un fichier .tsv décrivant les positions 3D des électrodes.
    ent_file : str ou Path, optionnel
        Fichier .ent associé, nécessaire si le chemin pour y accéder est différent du .eeg
    pos_file : str ou Path, optionnel
        Fichier .pos associé, nécessaire si le chemin pour y accéder est différent du .eeg

    Retour
    ------
    raw : mne.io.RawArray
        L'objet MNE Raw contenant les données EEG converties, avec le montage appliqué.
    """
    reader = neo.io.ElanIO(filename=str(eeg_file), entfile = ent_file, posfile=pos_file)
    block = reader.read_block()
    signal = block.segments[0].analogsignals[0]
    data = signal.magnitude.T  # (n_channels, n_times)
    sfreq = signal.sampling_rate.magnitude
    
    # Read only the header to get metadata
    header = reader.header
    channel_names = [ch['name'] for ch in header['signal_channels'][:-2]]
    n_channels = len(channel_names)
    clean_ch_names = [name.split('.')[0] for name in channel_names]

    ch_types = ['eeg']*n_channels

    info = mne.create_info(ch_names=clean_ch_names, sfreq=sfreq, ch_types=ch_types)
    raw = mne.io.RawArray(data, info)

    try:
        montage = mne.channels.read_custom_montage(fname=montage_file)    

        # Apply to montage
        montage.rename_channels({ch: fix_case_channel(ch) for ch in montage.ch_names})
        raw.set_montage(montage)
        raw.set_channel_types({'VOGbelow': 'eog', 'MASTl': 'bio', 'MASTr': 'bio'})
        # raw.set_channel_types({'VOGbelow': 'eog'})
    except Exception as e:
        print(f"Montage standard non trouvé : {e}")

    return(raw)

def add_FCz_montage(montage_file):
    """
    Adds the FCz electrode to a montage TSV file if it is missing.

    - Reads the montage file (tab-separated values).
    - Checks if an entry for 'FCZ' is present.
    - If absent, appends 'FCZ' with coordinates (0.388, 0.0, 0.922) to the file.
    - Saves the updated montage back to the same file.

    Parameters:
        montage_file (str): Path to the montage .tsv file.

    Returns:
        None
    """
    montage_df = pd.read_csv(montage_file, sep = '\t')
    if 'FCZ' not in list(montage_df['name']):
        FCz_df = pd.DataFrame({'name': ['FCZ'], 'x': [0.388], 'y': [0.0], 'z': [0.922]})
        montage_df = pd.concat([montage_df, FCz_df], ignore_index=True)
        # Save the updated DataFrame back to the TSV file
        montage_df.to_csv(montage_file, sep='\t', index=False)


def fix_case_channel(ch):
        """
        Standardizes EEG channel name capitalization for compatibility.

        - Preserves exact names for special channels (e.g., 'VOGbelow', 'MASTl', 'MASTr').
        - Ensures prefixes like 'AF', 'FT', 'FC', 'CP', 'TP', 'PO' stay uppercase.
        - Converts suffix 'Z' to lowercase 'z' (e.g., 'POZ' → 'POz').
        - Capitalizes other channels (e.g., 'fp1' → 'Fp1', 'oz' → 'Oz').

        Parameters:
            ch (str): The original channel name.

        Returns:
            str: The standardized channel name.
        """
        specials = ['VOGbelow', 'MASTl', 'MASTr']
        always_upper = ['AF', 'FT', 'FC', 'CP', 'TP', 'PO']  # Prefixes that stay uppercase
        
        if ch in specials:
            return ch
        if len(ch) <= 2:
            return ch.capitalize()
        for prefix in always_upper:
            if ch.startswith(prefix):
                rest = ch[len(prefix):]
                if rest == 'Z':  # e.g., POZ → POz
                    rest = 'z'
                return prefix + rest
        return ch[0].upper() + ch[1:].lower()


def ep2mat(p_file_name: str, save: Optional[str] = None):
    """
    Reads a .p file and extracts header (ENTETE), experimental parameters (XE), and data (DONNEES).
    
    Parameters
    ----------
    p_file_name : str
        Full path to the input .p file.
    save : str, optional
        If specified, the data will be saved to a .mat file with this name.
    
    Returns
    -------
    ENTETE : dict
        Header metadata.
    XE : dict
        Experimental metadata.
    DONNEES : ndarray
        Data array (samples x channels).
    """
    
    # Open binary file in big-endian float32 mode
    try:
        with open(p_file_name, 'rb') as f:
            A = np.fromfile(f, dtype='>f4')  # big-endian float32
    except Exception as e:
        raise IOError(f"Problem with {p_file_name}: {e}")

    ENTETE = {
        "s_Version": int(A[1]),
        "s_Header_Size": int(A[2]),
        "s_Event_Code": int(A[3]),
        "v_reserved": A[4:9].tolist()
    }

    fin_entete = (ENTETE["s_Header_Size"] // 4) + 9

    XE = {
        "s_Nb_Channels": int(A[9]),
        "s_Nb_Sample_per_Channel": int(A[10]),
        "s_Time_Epoch": A[11],
        "s_Nb_Sample_PreStim": int(A[12]),
        "s_Sampling_Period": A[13],
        "s_Min_Sig_Value": A[17],
        "s_Max_Sig_Value": A[18],
    }

    ch = XE["s_Nb_Channels"]
    offset = 19
    XE["v_Elec"] = A[offset : offset + ch].tolist()
    XE["v_Triplets"] = A[offset + ch : offset + 4*ch].tolist()
    
    XE.update({
        "s_Nb_Event_Aver": int(A[offset + 4*ch]),
        "s_Nb_Samp_Inhib_Artef_Rej": int(A[offset + 4*ch + 1]),
        "s_Flag_Artef_Rej": int(A[offset + 4*ch + 2]),
        "s_Flag_Baseline_Correction": int(A[offset + 4*ch + 3]),
        "s_Amplifier_Gain": A[offset + 4*ch + 4],
        "s_Low_Cutfrequency": A[offset + 4*ch + 5],
        "s_High_Cutfrequency": A[offset + 4*ch + 6],
        "v_Baseline_Value_per_Chan": A[offset + 4*ch + 7 : offset + 5*ch + 7].tolist(),
        "reserved": A[offset + 5*ch + 7 : fin_entete].tolist()
    })

    # Load data
    nb_samples = XE["s_Nb_Sample_per_Channel"]
    DONNEES = np.zeros((nb_samples, ch), dtype=np.float32)
    
    for v in range(ch):
        deb = fin_entete + 1 + v * (nb_samples + 2)
        DONNEES[:, v] = A[deb + 1 : deb + 1 + nb_samples]

    # Optionally save to .mat
    if save:
        from scipy.io import savemat
        savemat(save, {"ENTETE": ENTETE, "XE": XE, "DONNEES": DONNEES})

    return ENTETE, XE, DONNEES


def elan_p_to_epoch_mne(p_file, montage_file):
    """
    Converts an ELAN `.p` file into an MNE-Python `EpochsArray` object.

    This function reads EEG data from a `.p` file formatted by ELAN, 
    constructs an `EpochsArray` using MNE-Python, and applies a custom 
    electrode montage provided in a `.tsv` file.

    Parameters
    ----------
    p_file : str or Path
        Path to the `.p` file containing the EEG data exported from ELAN.
    montage_file : str or Path
        Path to a `.tsv` file describing the 3D positions of the electrodes,
        compatible with `mne.channels.read_custom_montage`.

    Returns
    -------
    epochs : mne.EpochsArray
        MNE EpochsArray object containing the converted EEG data, with the montage 
        applied and channel types correctly set (EEG, EOG, BIO).

    Notes
    -----
    - Assumes the `.p` file contains one averaged epoch (i.e., a single trial).
    - Channel types are set manually for specific channels (e.g., EOG, BIO).
    - The channel names in the montage are normalized using `fix_case_channel`.
    """

    # Ensure paths are Path objects
    p_file = Path(p_file)
    montage_file = Path(montage_file)

    # Load data from .p file
    _, xe, data = ep2mat(p_file)

    # Extract shape info
    n_channels = xe["s_Nb_Channels"]
    n_times = xe["s_Nb_Sample_per_Channel"]
    sfreq = 1000.0 / xe["s_Sampling_Period"]  # Hz

    # ELAN .p is assumed to contain one averaged epoch
    data = data.T[np.newaxis, :, :]  # shape: (1, n_channels, n_times)

    # Load the montage
    montage = mne.channels.read_custom_montage(fname=montage_file)

    # Create channel info
    info = mne.create_info(
        ch_names=montage.ch_names,
        sfreq=sfreq,
        ch_types='eeg'
    )

    # Create the EpochsArray
    epochs = mne.EpochsArray(data, info, tmin=-0.5)
    epochs.set_montage(montage)

    # Manually define types for specific non-EEG channels (adjust as needed)
    special_types = {'VOGbelow': 'eog', 'MASTl': 'bio', 'MASTr': 'bio'}
    existing_specials = {ch: t for ch, t in special_types.items() if ch in epochs.ch_names}
    if existing_specials:
        epochs.set_channel_types(existing_specials)

    return epochs

