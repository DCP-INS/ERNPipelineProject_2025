# Read Me

## Running the EEG Preprocessing Pipeline

To run this pipeline successfully, you need to ensure that:

1. **A compatible version of ELAN** is installed on your system.
2. **All required Python libraries** are installed.

### Installing ELAN

* On Windows or MacOS you can use VirtualBox to create a Ubuntu 24-04-2 LTS virtual machine. 
  * download and install [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
  * download Ubuntu 24-04-2 LTS installation [ubuntu-24.04.2-desktop-amd64.iso](https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-desktop-amd64.iso)
  * create a new virtual machine 
* On Linux (Ubuntu 24-04-2 LTS) : 
  * install packages bzip2 gcc make perl git python3.12-venv liblapack3
  * download and uncompress [Elan_ref_Ubuntu-24-x86.tgz](https://sdrive.cnrs.fr/s/wdkneMpL9nAzwYM/download/Elan_ref_Ubuntu-24-x86_64.tgz)
  * configure your environment variables ELANPATH and PATH to point to Elan and Elan/bin directories  

```bash
wget https://sdrive.cnrs.fr/s/wdkneMpL9nAzwYM/download/Elan_ref_Ubuntu-24-x86_64.tgz
tar xvfz Elan_ref_Ubuntu-24-x86_64.tgz
export ELANPATH=${PWD}/Elan
export PATH=${PATH}:${ELANPATH}/bin
sudo apt install bzip2 gcc make perl git python3.12-venv liblapack3
```



### Installing Python Dependencies

It is recommended to use a virtual environment to avoid conflicts with existing packages:

```bash
python3 -m venv env
source env/bin/activate
```

Then install the necessary libraries using:

```bash
pip3 install -r requirements.txt
```

---

## Configuring the Pipeline

Before launching the pipeline, make sure to configure the paths in the `init_paths.sh` file:

* `path_data`: Set this to the root BIDS directory of your dataset.
* `PYTHON_EXECUTABLE`: This should point to your Python interpreter (e.g., `python3`). Adjust this if needed to match your environment.

---

## Launching the Pipeline

Once everything is set up, you can run the pipeline:

* For **specific subjects**:

  ```bash
  bash pipeline sub-AG04EN28 sub AG05EN28
  ```

* For **all subjects** in the dataset root directory:

  ```bash
  bash pipeline
  ```

---

## Step Descriptions

The pipeline processes subjects one by one.
If the final results file for a subject already exists, that subject will be skipped.

---

### Step 1: File Conversion

Before preprocessing, EEG data must be converted to a format compatible with ELAN (`.eeg`).

1. **Convert `.set` to `.edf`:**
   The script `python_scripts/convert_set2edf.py` converts `.set` files to `.edf` format (adding FCz). It also:

   * Creates a `.pos` file with event timings.
   * Records the number of samples in a `_desc-preprocessing_information.csv` files (global and per-subject).
   * Rejects trials with a response within a \[-500; 500] ms window around the cut marker (code 222 in the `.pos` file).

2. **Convert `.edf` to `.eeg`:**
   Using `edf2eeg`, the previously created `.edf` file is converted to `.eeg`. Since the `.edf` may contain added samples, `eegcut` is used to restore the signal to its original length.

---

### Step 2: Preprocessing

1. **High-pass filter at 0.1 Hz:**
   Using `eegfiltfilt`.

2. **Re-referencing:**

   * Reference to mastoids.
     Using `eegchref`.
   * Bipolar montage with Fp1.
     Using `eegchref`.

3. **50 Hz notch filtering:**
   Using `eegfiltfilt`.

4. **Low-pass filter at 40 Hz:**
   Using `eegfiltfilt`.

5. **Response artifact rejection on mastoids and subject exclusion:**

   * Rejection of trials with artifacts in a \[-500; 500] ms window around the responses using `eegavg` on the mastoids channels.
   * Subjects with more than 30% rejected trials are excluded using `python_scripts/exclude_sub_mast.py`.
   * Excluded subjects are skipped from further processing.

6. **Flanker artifact rejection on EOG channel and subject exclusion:**

   * Rejection of trials with artifacts in a \[-100; 400] ms window around the Flanker using `eegavg` on the EOG channel.
   * Subjects with more than 30% rejected trials are excluded using `python_scripts/exclude_sub_flanker.py`.
   * Excluded subjects are skipped from further processing.

7. **ICA correction:**

    **ICA Components:** Using `python_scripts/ica_eeg.py`:

    * **Bad channel detection:**
    Bad channels are detected using `mne.preprocessing.find_bad_channels_lof()` with a threshold of 3.

    * **ICA computation:**
    Independent Component Analysis is performed using `mne.preprocessing.ICA()`, with the number of components set to `n_channels - n_bad_channels`.

    * **Artifact component detection:**
    Blink and saccade-related components are automatically identified using `ica.find_bads_eog(raw)`.

    * **Transformation Matrix Extraction:** *
    The ICA transformation matrix is computed as `np.dot(ica.unmixing_matrix_, ica.pca_components_[:ica.n_components_])` and saved to an `.xml` file.

    * **Results saving:**
    Detected bad channels and ICA components are logged in each subject’s `_desc-preprocessing_information.csv`.

    **ICA Correction:**
    Identified artifact components are removed from the EEG data using `eegfiltica`.

8. **Artifact rejection on response events:**
    Using `eegavg`, trials with artifacts in the \[-500; 500] ms window around the response are rejected.

9. **Channel interpolation (if needed):**

   * Channels requiring interpolation are detected using `python_scripts/find_electrodes_to_interpolate_mean.py`.
   * The mean rejection rate of each channel is computed, and channels with outlier rejection rates superior to 10% are marked for interpolation.
   * Interpolated channels are saved in `desc-interpolated_channels.csv` (per subject).
   * Interpolation is performed using `eegspline`.
   * If interpolation is performed, Step 8 is re-run.

10. **Documentation of preprocessing outcomes:**

    * Final statistics are compiled with `python_scripts/preprocessing_information_file_over_all.py`.
    * Includes the number of retained events over the initial number of events and interpolated channels per subject.

---

### Step 3: Epoch Analysis

Once EEG data is preprocessed, the following analyses are performed:

1. **Single-trial epochs:**
   Saved in `sub-xx/ERP` using `python_scripts/save_single_trial_epo.py`.

2. **ERP and ERN computation:**
   Using `auto_ERN_eegavg`, which calls `eegavg`, `epavg`, and `epdiff`. The ERPs are baseline-corrected using the time window from -500 to -100 ms.

3. **ERN value extraction:**

   * Computed using `python_scripts/get_ERN_values.py`.
   * ERN was defined as the mean amplitude within a ±20 ms window centered on the minimum latency occurring between 50 and 150 ms post-response at FCz [1–4].
   * ERN is extracted only if:
     * ERN computation was performed only when there were a minimum of 30 trials for both correct and incorrect responses for the general ERN, and at least 8 trials per condition for congruency-specific analyses.
   * Results are saved in `desc-ERN_values.csv` (per subject).
   * In the `_desc-preprocessing_information.csv` files, information about the subject's inclusion or exclusion from each statistical analysis is added.
   * Only fast correct/incorrect trials are considered.

---

### Step 4: Statistical Analysis

After all subjects have been processed, group-level statistics are performed using `python_scripts/stats_analysis.py`.
Results are saved in `derivatives/stats_analysis`.

1. **Biweight midcorrelation correlation:**

   * Between ERN and PSWQ (fast incorrect vs. correct trials).
   * A scatterplot is generated.

2. **Effect of gender:**

   * Compare ERN values between gender (fast incorrect vs. correct trials).
   * Use unpaired t-test or Mann-Whitney based on normality.
   * A boxplot is generated.

3. **Effect of congruency:**

   * Compare ERN values between congruency levels (0 vs. 100).
   * Use paired t-test or Wilcoxon based on normality.
   * A boxplot is generated.

---

## Notes

A log file is generated for each Python script and saved in the subject's dedicated log directory.

### New Codes

During the epoch analysis, the codes were updated for easier identification.

Here is the description of the new codes:

* **IR** = Incorrect Response
* **CR** = Correct Response
* **0, 33, 66, 100** = Congruency percentage
* **Sl** = Slow
* **Fa** = Fast

## References

[1] Boen R, Quintana DS, Ladouceur CD, Tamnes CK. Age-related differences in the error-related negativity and error positivity in children and adolescents are moderated by sample and methodological characteristics: A meta-analysis. Psychophysiology. 2022 Jun;59(6):e14003. doi: 10.1111/psyp.14003. Epub 2022 Feb 6. PMID: 35128651; PMCID: PMC9285728.

[2] Lawler JM, Hruschak J, Aho K, Liu Y, Ip KI, Lajiness-O'Neill R, Rosenblum KL, Muzik M, Fitzgerald KD. The error-related negativity as a neuromarker of risk or resilience in young children. Brain Behav. 2021 Mar;11(3):e02008. doi: 10.1002/brb3.2008. Epub 2020 Dec 22. PMID: 33354942; PMCID: PMC7994696.

[3] Wang, L., Gu, Y., Zhao, G. et al. Error-related negativity and error awareness in a Go/No-go task. Sci Rep 10, 4026 (2020). <https://doi.org/10.1038/s41598-020-60693-0>

[4] McMahon CM, Henderson HA. Error-monitoring in response to social stimuli in individuals with higher-functioning Autism Spectrum Disorder. Dev Sci. 2015 May;18(3):389-403. doi: 10.1111/desc.12220. Epub 2014 Jul 28. PMID: 25066088; PMCID: PMC4309753.
