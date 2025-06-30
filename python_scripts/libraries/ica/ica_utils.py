import mne

def get_good_eeg_indices(raw):
    """
    Return the 1-based indices of good EEG channels from an MNE Raw object
    as a list of integers.

    Parameters:
        raw (mne.io.Raw): The MNE Raw object containing EEG and bad channel info.

    Returns:
        list of int: 1-based indices of good EEG channels.
    """
    all_eeg = mne.pick_types(raw.info, eeg=True)
    bad = mne.pick_channels(raw.ch_names, include=raw.info['bads']) if raw.info['bads'] else []

    good = sorted(set(all_eeg) - set(bad))
    return [i + 1 for i in good]

def writeTmatrixXMLformat(nbtotchan, nbusedchan, nbsources, rankchanlist, matrix, filename):
    """
    Écrit un fichier XML au format Tmatrix.
    
    Args:
        nbtotchan (int): total number of channels including EOG, EMG etc.
        nbusedchan (int): number of used channels.
        nbsources (int): total number of sources.
        rankchanlist (list or array-like): rank list of used channels (ints) (pass the number 5 for exemple).
        matrix (2D array-like): matrix of shape (nbsources, nbusedchan).
        filename (str): chemin du fichier XML à écrire.
    """
    print('writeTmatrixXMLformat : V1.01 27-02-2008')

    with open(filename, 'w', encoding='ISO-8859-1') as fid:
        fid.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        fid.write('<Tmatrix>\n')

        fid.write(f'\t<nbtotchan>{nbtotchan}</nbtotchan>\n')
        fid.write(f'\t<nbusedchan>{nbusedchan}</nbusedchan>\n')
        fid.write(f'\t<nbsources>{nbsources}</nbsources>\n')

        # Écrire rankchanlist avec un ';' entre chaque élément
        rank_str = ';'.join(str(int(r)) for r in rankchanlist)
        fid.write(f'\t<rankchanlist>{rank_str};</rankchanlist>\n')

        fid.write('\t<matrix>')
        for i in range(nbsources):
            row_str = ';'.join(f'{float(val):.6f}' for val in matrix[i])
            fid.write(row_str + ';\n')
        fid.write('\t</matrix>\n')

        fid.write('</Tmatrix>\n')

    print('\nWriting xml file.\n')