from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pingouin as pg
import os

def stats_analysis():
    """
    Main function to run statistical analysis and generate plots for ERN data.

    Workflow:
    1. Load participant-level data from the BIDS derivatives folder.
    2. Merge individual ERN CSV files with participant metadata.
    3. Run statistical tests:
       - Correlation: mean_around_min vs. PSWQ
       - T-test or Wilcoxon: mean_around_min by Sex
       - T-test or Wilcoxon: mean_around_min by Congruency (0 vs 100)
    4. Generate a summary figure with three subplots.
    """

    # Configuration 
    bids_root = Path(os.getenv("DATA_PATH"))
    task_name = os.getenv("TASK_NAME")
    derivatives_dir = bids_root / 'derivatives'
    stats_analysis_dir = derivatives_dir / 'stats_analysis'
    stats_analysis_dir.mkdir(parents=True, exist_ok=True)

    # Load participants.tsv file
    participants_tsv = bids_root / 'participants.tsv'
    participants_df = pd.read_csv(participants_tsv, sep='\t')

    # Get list of subject directories (e.g., sub-01, sub-02, etc.)
    sub_list = [f.name for f in derivatives_dir.iterdir() if f.is_dir() and f.name.startswith('sub-')]
    print(f"Subjects found: {sub_list}")

    # Load and merge all subject-level ERN values with participant data
    merged_df = get_sub_values(derivatives_dir, sub_list, task_name, participants_df)

    # Save merged dataset
    output_path = stats_analysis_dir / 'all_subjects_ERN_values_merged.csv'
    merged_df.to_csv(output_path, index=False, na_rep = 'NA')
    print(f"Merged ERN values saved to {output_path}")

    # Run statistical analyses
    corr_res = correlation_MeanAroundMin_PSWQ(merged_df)
    ttest_sex_res = MeanAroundMin_Gender_effect(merged_df)
    ttest_congru_res = MeanAroundMin_Congru_effect(merged_df)

    # Save statistical results
    corr_res.to_csv(stats_analysis_dir / 'correlation_MeanAroundMin_PSWQ.csv', index=False)
    ttest_sex_res.to_csv(stats_analysis_dir / 'ttest_MeanAroundMin_Sex.csv', index=False)
    ttest_congru_res.to_csv(stats_analysis_dir / 'ttest_MeanAroundMin_Congruency.csv', index=False)

    # Generate and save plot
    fig = plot_results(merged_df, corr_res, ttest_sex_res, ttest_congru_res)
    fig.savefig(stats_analysis_dir / 'Statistical_analysis_results.png', dpi=300, bbox_inches='tight')   

def get_sub_values(derivatives_dir, sub_list, task_name, participants_df):
    """
    Loads ERN values for all subjects and merges them with participant metadata.

    Parameters
    ----------
    derivatives_dir : Path
        Path to the derivatives directory.
    sub_list : list
        List of subject folder names.
    participants_df : pd.DataFrame
        DataFrame of participants.tsv containing demographics/questionnaires.

    Returns
    -------
    pd.DataFrame
        Merged DataFrame with ERN values and participant information.
    """
    all_values = []

    for sub in sub_list:
        path_sub_values = derivatives_dir / sub / f'{sub}_task-{task_name}_eeg_desc-ERN_values.csv'
        if not path_sub_values.exists():
            print(f"  WARNING: ERN values file not found for {sub}, skipping.")
            continue

        # Read the subject's ERN values CSV
        sub_values_df = pd.read_csv(path_sub_values, sep=';')
        all_values.append(sub_values_df)

    if not all_values:
        raise RuntimeError("No ERN values files found.")

    # Combine all subjects into a single DataFrame
    ern_values_df = pd.concat(all_values, ignore_index=True)

    # Merge with participant metadata
    merged_df = ern_values_df.merge(participants_df, on='participant_id', how='left')
    return merged_df


def correlation_MeanAroundMin_PSWQ(df):
    """
    Computes the Biweight midcorrelation between ERN amplitude (mean_around_min)
    and PSWQ anxiety scores, restricted to the 'FaIR-CR' ERN condition.

    Parameters
    ----------
    df : pd.DataFrame
        Merged DataFrame with ERN and participant data.

    Returns
    -------
    pd.DataFrame
        Pingouin correlation result table.
    """
    # Filter out missing data and select only the 'FaIR-CR' condition
    mask = ~df['mean_around_min'].isna() & ~df['PSWQ'].isna() & (df['ERN'] == 'FaIR-CR')
    x = df.loc[mask, 'mean_around_min']
    y = df.loc[mask, 'PSWQ']

    # Run correlation
    result = pg.corr(x, y, method='bicor')
    
    # Output
    print(f"\nCorrelation between mean_around_min and PSWQ using Biweight midcorrelation method:")
    print(result)
    return result


def MeanAroundMin_Gender_effect(df):
    """
    Performs an independent t-test to compare ERN amplitude (mean_around_min)
    between females and males in the 'FaIR-CR' condition.

    Parameters
    ----------
    df : pd.DataFrame
        Merged DataFrame with ERN and participant data.

    Returns
    -------
    pd.DataFrame
        Pingouin t-test result table.
    """
    males = df.loc[(df['Sex'] == 'M') & (df['ERN'] == 'FaIR-CR'), 'mean_around_min'].dropna()
    females = df.loc[(df['Sex'] == 'F') & (df['ERN'] == 'FaIR-CR'), 'mean_around_min'].dropna()
    # Check normality
    normal_males = pg.normality(males)['normal'].values[0]
    normal_females = pg.normality(females)['normal'].values[0]

    if normal_males and normal_females:
        # Independent samples t-test, one-tailed (female > male)
        result = pg.ttest(females, males, paired=False, alternative='greater')
        test_name = 'Independent t-test'
    else:
        # Mann-Whitney U test (non-parametric)
        result = pg.mwu(females, males, alternative='greater')
        test_name = 'Mann-Whitney U test'

    print(f"\n{test_name} results comparing mean_around_min by Sex (F > M) in 'FaIR-CR' condition:")
    print(result)
    return result

def MeanAroundMin_Congru_effect(df):
    """
    Performs an independent t-test comparing ERN amplitudes between
    'FaIR-CR100' and 'FaIR-CR0' congruency conditions.

    Parameters
    ----------
    df : pd.DataFrame
        Merged DataFrame with ERN and participant data.

    Returns
    -------
    pd.DataFrame
        Pingouin t-test result table.
    """
    # Pivot the data so each participant has a value for both conditions
    data_wide = df.pivot(index='participant_id', columns='ERN', values='mean_around_min')

    # Drop rows with missing data for either condition
    data_wide = data_wide.dropna(subset=['FaIR-CR100', 'FaIR-CR0'])

    # Calculate difference scores
    diff = data_wide['FaIR-CR100'] - data_wide['FaIR-CR0']

    # Check normality of difference
    normal = pg.normality(diff)['normal'].values[0]

    if normal:
        # Paired t-test
        result = pg.ttest(data_wide['FaIR-CR100'], data_wide['FaIR-CR0'], paired=True, alternative='greater')
        test_name = 'Paired t-test'
    else:
        # Wilcoxon signed-rank test (non-parametric)
        result = pg.wilcoxon(data_wide['FaIR-CR100'], data_wide['FaIR-CR0'], alternative='greater')
        test_name = 'Wilcoxon signed-rank test'

    print(f"\n{test_name} results comparing mean_around_min between 'FaIR-CR100' and 'FaIR-CR0' (100% > 0%):")
    print(result)
    return result

def plot_results(df, corr_res, ttest_sex_res, ttest_congru_res):
    """
    Generates a 3-panel figure summarizing:
    - Correlation between ERN amplitude and PSWQ.
    - ERN amplitude by sex.
    - ERN amplitude by congruency condition.

    Parameters
    ----------
    df : pd.DataFrame
        Merged DataFrame with ERN and participant data.
    corr_res : pd.DataFrame
        Correlation result table.
    ttest_sex_res : pd.DataFrame
        T-test result for sex difference.
    ttest_congru_res : pd.DataFrame
        T-test result for congruency effect.

    Returns
    -------
    matplotlib.figure.Figure
        The resulting matplotlib figure.
    """
    sns.set_theme()

    

    with plt.rc_context(rc={
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12,
        'figure.titlesize': 18
    }):
        fig, axs = plt.subplots(1, 3, figsize=(18, 5))
        cb_palette = sns.color_palette("colorblind")

        mask_corr = ~df['mean_around_min'].isna() & ~df['PSWQ'].isna() & (df['ERN'] == 'FaIR-CR')

        # === Panel 1: Correlation plot ===
        sns.scatterplot(
            x='PSWQ', y='mean_around_min', color = cb_palette[3],
            data=df[mask_corr], ax=axs[0]
        )
        sns.regplot(
            x='PSWQ', y='mean_around_min',
            data=df[mask_corr], ax=axs[0],
            scatter_kws={'color': cb_palette[3], 's': 30}, line_kws={'color': 'black'}, ci=95
        )
        counts = df.loc[mask_corr, 'PSWQ'].count()
        axs[0].set_title(f'Mean Around Minimum vs PSWQ\nr={corr_res.iloc[0]["r"]:.2f}, p={corr_res.iloc[0]["p-val"]:.3f}, n={counts}')
        axs[0].set_xlabel('PSWQ Score')
        axs[0].set_ylabel('Mean Around Minimum')

        # === Panel 2: Boxplot by sex ===
        sns.boxplot(
            x='Sex', y='mean_around_min', data=df[df['ERN'] == 'FaIR-CR'].dropna(),
            ax=axs[1], hue='Sex', palette={'F': cb_palette[4], 'M': cb_palette[8]}, width=0.5
        )
        annotate_n(axs[1], df[df['ERN'] == 'FaIR-CR'], df.loc[df['ERN'] == 'FaIR-CR', 'mean_around_min'].max(), 'Sex', 'mean_around_min')    
        add_significance_star(axs[1], 0, 1, df.loc[df['ERN'] == 'FaIR-CR', 'mean_around_min'].max(), ttest_sex_res.iloc[0]['p-val'], color='0.3')

        stat, pval, stat_label = get_stat_and_label(ttest_sex_res)
        axs[1].set_title(f'Mean Around Minimum by Sex\n{stat_label}={stat:.2f}, p={pval:.3f}') 

        add_y_lim=(df.loc[df['ERN'] == 'FaIR-CR', 'mean_around_min'].max()-df.loc[df['ERN'] == 'FaIR-CR', 'mean_around_min'].min())*0.2

        axs[1].set_ylim((df.loc[df['ERN'] == 'FaIR-CR', 'mean_around_min'].min()-2, df.loc[df['ERN'] == 'FaIR-CR', 'mean_around_min'].max()+add_y_lim))
        axs[1].set_ylabel('Mean Around Minimum')
        axs[1].set_xlabel('Gender')

        # === Panel 3: Boxplot by congruency ===
        data_wide = df.pivot(index='participant_id', columns='ERN', values='mean_around_min').dropna(subset=['FaIR-CR0', 'FaIR-CR100'])
        df_congru = data_wide.reset_index().melt(id_vars='participant_id', value_vars=['FaIR-CR0', 'FaIR-CR100'], var_name='ERN', value_name='mean_around_min')
        sns.boxplot(x='ERN', y='mean_around_min', data=df_congru, ax=axs[2], hue='ERN', palette={'FaIR-CR0': cb_palette[2], 'FaIR-CR100': cb_palette[5]})

        stat, pval, stat_label = get_stat_and_label(ttest_congru_res)
        annotate_n(axs[2], df_congru, df_congru['mean_around_min'].max(), 'ERN', 'mean_around_min')

        axs[2].set_title(f'Mean Around Minimum by Congruency\n{stat_label}={stat:.2f}, p={pval:.3f}')
        axs[2].set_xlabel('Congruency')
        axs[2].set_ylabel('Mean Around Minimum')

        add_significance_star(axs[2], 0, 1, df_congru['mean_around_min'].max(), ttest_congru_res.iloc[0]['p-val'], color='0.3')
        
        add_y_lim=(df_congru['mean_around_min'].max()-df_congru['mean_around_min'].min())*0.2
        axs[2].set_ylim((df_congru['mean_around_min'].min()-2, df_congru['mean_around_min'].max()+add_y_lim))

        fig.suptitle('ERN Amplitude Analysis (Mean Around Minimum)', fontsize=20, y=1.02)
        plt.tight_layout(pad=2.0)
        return fig

def get_stat_and_label(test_res):
    """
    Extracts the test statistic value and label from a pingouin test result DataFrame,
    supporting t-tests ('T') and Mann-Whitney U tests ('U-val').

    Parameters
    ----------
    test_res : pd.DataFrame
        Result table returned by pingouin tests like ttest or mwu.

    Returns
    -------
    stat : float or None
        The test statistic value (t or U), or None if not found.
    pval : float or None
        The p-value associated with the test.
    stat_label : str
        Label for the test statistic ('t' or 'U'), empty string if unknown.
    """
    if 'T' in test_res.columns:
        stat = test_res.iloc[0]['T']
        stat_label = 't'
    elif 'U-val' in test_res.columns:
        stat = test_res.iloc[0]['U-val']
        stat_label = 'U'
    else:
        stat = None
        stat_label = ''

    pval = test_res.iloc[0].get('p-val', None)

    return stat, pval, stat_label

def add_significance_star(ax, x1, x2, y_max, p_val, color='black'):
    """
    Adds a significance bar (with stars or 'n.s.') between two groups in a boxplot.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes object to draw on.
    x1 : float
        Position of first group on x-axis.
    x2 : float
        Position of second group on x-axis.
    y_max : float
        Maximum y-value in the current data to position the star.
    p_val : float
        P-value to determine significance level.
    color : str
        Color of the annotation.
    """
    y, h = y_max + 1, 1.5  # space it out more clearly
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=1.2, c=color)

    if p_val < 0.001:
        stars = '***'
    elif p_val < 0.01:
        stars = '**'
    elif p_val < 0.05:
        stars = '*'
    else:
        stars = 'n.s.'

    ax.text((x1 + x2) * .5, y + h + 0.3, stars, ha='center', va='bottom', color=color, fontsize=13)
    

def annotate_n(ax, data, y_max, x_col, y_col):
    """
    Annotate the number of non-NaN observations per group on a plot.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes object on which to add the annotations.
    data : pandas.DataFrame
        The DataFrame containing the data used for plotting.
    y_max : float
        The y-coordinate above which the annotations will be placed.
    x_col : str
        The name of the column used for grouping on the x-axis.
    y_col : str
        The name of the column whose non-NaN values will be counted for each group.

    """
    counts = data.groupby(x_col)[y_col].count()
    for i, (_, count) in enumerate(counts.items()):
        ax.text(i, y_max + 3.5, f'n={count}', ha='center', va='bottom', fontsize=10, color='black')

# Run the function
if __name__ == "__main__":
    stats_analysis()