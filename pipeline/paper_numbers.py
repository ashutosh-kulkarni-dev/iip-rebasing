"""Stage 7: the registry of every number the paper may quote.

Reads results/*.csv and writes results/paper_numbers.json as {key: formatted string}.
The manuscript cites numbers only through these keys, and check_paper.py (written with
the paper) confirms that every number in the text appears in this registry.
"""
import math
import json
import pandas as pd
from config import RESULTS, PAIRS

R = {}
f1 = lambda x: f'{x:.1f}'
f2 = lambda x: f'{x:.2f}'
pct = lambda x: f'{100 * x:.0f}'

S = pd.read_csv(RESULTS / 'overlap_stats.csv')
for _, r in S.iterrows():
    tag = 'true' if r['sample'].startswith('true') else 'all'
    k = f"{r['pair']}|{r['data_version']}|{r['series']}|{tag}".replace(' ', '_')
    R[k + '|months'] = str(int(r['months']))
    R[k + '|corr'] = f2(r['corr'])
    R[k + '|corr_ci'] = f"{r['corr_ci_lo']:.2f} to {r['corr_ci_hi']:.2f}"
    R[k + '|mean_old'] = f1(r['mean_old'])
    R[k + '|mean_new'] = f1(r['mean_new'])
    R[k + '|gap'] = f1(r['mean_gap_new_minus_old'])
    R[k + '|dir_disagree_pct'] = pct(r['share_direction_disagree'])
    R[k + '|contract_old_pct'] = pct(r['share_contract_old'])
    R[k + '|contract_new_pct'] = pct(r['share_contract_new'])
    R[k + '|sd_ratio'] = f2(r['sd_ratio_new_old'])
    R[k + '|sd_old'] = f1(r['sd_old'])
    R[k + '|sd_new'] = f1(r['sd_new'])
    R[k + '|gap_ci'] = f"{r['gap_ci_lo']:.1f} to {r['gap_ci_hi']:.1f}"

A = pd.read_csv(RESULTS / 'overlap_annual.csv')
for _, r in A.iterrows():
    k = f"annual|{r['pair']}|{r['data_version']}|{r['series']}|{r['fiscal_year']}".replace(' ', '_')
    R[k + '|old'], R[k + '|new'], R[k + '|gap'] = f1(r['old']), f1(r['new']), f1(r['gap'])

for pr, g in A[(A['data_version'] == 'esankhyiki') & (A['series'] == 'General')].dropna(subset=['gap']).groupby('pair'):
    R[f'fy_count|{pr}'.replace(' ', '_')] = str(len(g))
    R[f'annual_mean_gap|{pr}'.replace(' ', '_')] = f1(g['gap'].mean())
g1 = A[(A['data_version'] == 'esankhyiki') & (A['series'] == 'General') & (A['pair'] == 'Pair 1')].dropna(subset=['gap'])
R['annual_gap|Pair_1|2007-08'] = f1(g1.set_index('fiscal_year').loc['2007-08', 'gap'])
R['annual_mean_gap|Pair_1|excl_2007-08'] = f1(g1[g1['fiscal_year'] != '2007-08']['gap'].mean())
for ser in ['General', 'Manufacturing']:
    g = A[(A['data_version'] == 'esankhyiki') & (A['series'] == ser)].dropna(subset=['gap'])
    R[f'annualcount|{ser}|years'] = str(len(g))
    R[f'annualcount|{ser}|new_faster'] = str(int((g['gap'] > 0).sum()))

D = pd.read_csv(RESULTS / 'decomposition_pairs.csv')
for _, r in D.iterrows():
    k = f"decomp|{r['pair']}|{r['data_version']}|{r['category_set']}|{r['statistic']}".replace(' ', '_')
    for c in ['old_data_old_wts', 'old_data_new_wts', 'new_data_old_wts', 'new_data_new_wts', 'gap',
              'weight_effect', 'residual']:
        R[f'{k}|{c}'] = f2(r[c])
    R[f'{k}|weight_share_pct'] = pct(r['weight_share_of_gap'])
    R[f'{k}|gap|1dp'] = f1(r['gap'])

M = pd.read_csv(RESULTS / 'gfc_measures.csv')
for _, r in M.iterrows():
    R[f"gfc|{r['base_year']}|{r['series']}|{r['measure']}".replace(' ', '_')] = f2(r['value'])
    R[f"gfc|{r['base_year']}|{r['series']}|{r['measure']}|1dp".replace(' ', '_')] = f1(r['value'])
G = pd.read_csv(RESULTS / 'gfc_decomposition.csv')
for _, r in G.iterrows():
    k = f"gfcdecomp|{r['category_set']}|{r['measure']}".replace(' ', '_')
    for c in ['old_data_old_wts', 'old_data_new_wts', 'new_data_old_wts', 'new_data_new_wts', 'gap',
              'weight_effect', 'residual']:
        R[f'{k}|{c}'] = f2(r[c])
    R[f'{k}|weight_share_pct'] = pct(abs(r['weight_share_of_gap']))
    R[f'{k}|max_single_order_share_pct'] = pct(r['max_single_order_weight_share'])
    for c in ['old_data_old_wts', 'new_data_new_wts', 'gap']:
        R[f'{k}|{c}|1dp'] = f1(r[c])
_g4 = G[(G['category_set'] == 'four categories') & (G['measure'] != 'In-window mean YoY growth (%)')]
R['gfcdecomp|max_other_weight_share_pct'] = pct(_g4['weight_share_of_gap'].abs().max())
R['gfcdecomp|inwindow_weight_share_signed_pct'] = pct(G[(G['category_set'] == 'four categories') & (G['measure'] == 'In-window mean YoY growth (%)')]['weight_share_of_gap'].iloc[0])
R['gfcdecomp|max_weight_share_pct'] = pct(G[G['category_set'] == 'four categories']['weight_share_of_gap'].abs().max())

SP = pd.read_csv(RESULTS / 'splice_summary.csv')
for _, r in SP.iterrows():
    R[f"splice|{r['rule']}|{r['statistic']}".replace(' ', '_')] = f2(r['value'])
    R[f"splice|{r['rule']}|{r['statistic']}|1dp".replace(' ', '_')] = f1(r['value'])
    R[f"splice|{r['rule']}|{r['statistic']}|0dp".replace(' ', '_')] = f"{r['value']:.0f}"

# Official published figures quoted directly (data/official/*.csv)
from config import OFFICIAL, OFFICIAL_LINKING
for fn, tag in [('mospi2026_pair3_annual_growth.csv', 'jun01'), ('mospi2026jun29_2022-23_annual_growth.csv', 'jun29'),
                ('cso2011_pair1_annual_growth.csv', 'cso2011'), ('mospi2017_pair2_annual_growth.csv', 'mospi2017')]:
    for _, r in pd.read_csv(OFFICIAL / fn).iterrows():
        R[f"official|{tag}|{r['base_year']}|{r['series']}|{r['fiscal_year']}".replace(' ', '_')] = f1(r['growth_pct'])
_j1 = pd.read_csv(OFFICIAL / 'mospi2026_pair3_annual_growth.csv')
_j1 = _j1[_j1['base_year'] == '2022-23'].set_index(['series', 'fiscal_year'])['growth_pct']
_j29 = pd.read_csv(OFFICIAL / 'mospi2026jun29_2022-23_annual_growth.csv').set_index(['series', 'fiscal_year'])['growth_pct']
for (ser, fy_), v in _j29.items():
    if (ser, fy_) in _j1.index:
        R[f'officialdiff|{ser}|{fy_}'.replace(' ', '_')] = f1(v - _j1[(ser, fy_)])
IW = pd.read_csv(OFFICIAL / 'industry_weights_2011-12_2022-23.csv')
tot = IW[IW['description'] == 'General Index'].iloc[0]
R['official|itemgroups|2011-12'] = str(int(tot['n_2011']))
R['official|itemgroups|2022-23'] = str(int(tot['n_2022']))
from config import USE_WEIGHTS
for b, d in USE_WEIGHTS.items():
    for c, v in d.items():
        R[f'weight|{b}|{c}'.replace(' ', '_')] = f'{v:.2f}'
from config import CSO2011_LINKING
for k, v in CSO2011_LINKING.items():
    R[f'official|cso2011_linking|{k}'] = f'{v:.3f}'
V4 = pd.read_csv(RESULTS / 'validation_v4_linking_factors.csv')
for _, r in V4.iterrows():
    R[f"lf|{r['transition']}|{r['series']}".replace(' ', '_')] = f"{r['linking_factor']:.4f}"
    R[f"lf|{r['transition']}|{r['series']}|3dp".replace(' ', '_')] = f"{r['linking_factor']:.3f}"
for b, d in USE_WEIGHTS.items():
    R[f'weight_sum4|{b}'] = f1(sum(d.values()))
for k, v in OFFICIAL_LINKING.items():
    R[f'official|linking|{k}'] = f'{v:.4f}'

B = pd.read_csv(RESULTS / 'asi_benchmark.csv')
for _, r in B.iterrows():
    k = f"asi|{r['fiscal_year']}"
    for c in ['asi_nominal_growth', 'wpi_mfg_inflation', 'asi_real_growth', 'iip_old', 'iip_new']:
        R[f'{k}|{c}'] = f1(r[c])
BS = pd.read_csv(RESULTS / 'asi_benchmark_summary.csv')
for _, r in BS.iterrows():
    k = f"asisum|{r['sample']}|{r['pair']}".replace(' ', '_')
    for c in ['mean_asi_real', 'mean_iip_old', 'mean_iip_new', 'mean_gap_old', 'mean_gap_new', 'mae_old', 'mae_new']:
        R[f'{k}|{c}'] = f1(r[c])
    R[f'{k}|years'] = str(int(r['years']))
    R[f'{k}|years_new_closer'] = str(int(r['years_new_closer']))
    for c in ['corr_old', 'corr_new']:
        if pd.notna(r[c]):
            R[f'{k}|{c}'] = f2(r[c])
alls = BS[BS['sample'] == 'all years']
R['asisum|total_years'] = str(int(alls['years'].sum()))
R['asisum|total_years_new_closer'] = str(int(alls['years_new_closer'].sum()))
DR = pd.read_csv(RESULTS / 'deflator_revision.csv')
for _, r in DR.iterrows():
    k = f"defl|{r['series']}|{r['fiscal_year']}".replace(' ', '_')
    R[k + '|june1'], R[k + '|revised'], R[k + '|change'] = f1(r['growth_june1']), f1(r['growth_revised']), f1(r['change_pp'])
    R[f"defl|{r['series']}|max_monthly_diff".replace(' ', '_')] = f1(r['max_abs_monthly_index_diff'])
IS = pd.read_csv(RESULTS / 'industry_summary_pair3.csv').iloc[0]
R['ind|n'] = str(int(IS['industries']))
R['ind|months'] = str(int(IS['months']))
R['ind|n_new_faster'] = str(int(IS['n_new_faster']))
R['ind|share_new_faster_pct'] = pct(IS['share_new_faster'])
R['ind|weighted_mean_gap'] = f1(IS['weighted_mean_gap'])
R['ind|median_corr'] = f2(IS['median_corr'])
R['ind|spearman_gap_itemgroups'] = f2(IS['spearman_gap_vs_item_group_change'])
R['ind|spearman_absgap_itemgroups'] = f2(IS['spearman_absgap_vs_item_group_change'])

EP = pd.read_csv(RESULTS / 'episodes.csv')
for _, r in EP.iterrows():
    R[f"ep|{r['episode']}|{r['statistic']}|{r['series']}|{r['source']}".replace(' ', '_')] = f1(r['value'])

EC = pd.read_csv(RESULTS / 'episodes_by_category.csv')
for _, r in EC.iterrows():
    R[f"cat|{r['episode']}|{r['series']}|{r['role']}".replace(' ', '_')] = f1(r['value'])
FY = pd.read_csv(RESULTS / 'first_year_example.csv', parse_dates=['date'])
for _, r in FY.iterrows():
    R[f"firstyear|{r['date']:%Y-%m}|index"] = f1(r['index'])
    R[f"firstyear|{r['date']:%Y-%m}|growth"] = f1(r['growth_rate'])
V2 = pd.read_csv(RESULTS / 'validation_v2_first_year_convention.csv')
R['firstyear|max_dev_all_bases'] = f1(V2['max_abs_dev_pp'].max())

NO = pd.read_csv(RESULTS / 'noise_overlap.csv')
for _, r in NO.iterrows():
    k = f"nov|{r['pair']}".replace(' ', '_')
    R[k + '|months'] = str(int(r['months']))
    R[k + '|mean_gap'], R[k + '|rmsd'] = f1(r['mean_gap']), f1(r['rmsd'])
    R[k + '|corr'] = f2(r['corr'])
    R[k + '|opposite_pct'] = pct(r['opposite_sign_share'])
NC = pd.read_csv(RESULTS / 'noise_changes.csv')
for _, r in NC.iterrows():
    k = f"nch|{r['pair']}|{int(r['window_months'])}".replace(' ', '_')
    R[k + '|dates'] = str(int(r['dates']))
    R[k + '|window'] = str(int(r['window_months']))
    for c in ['median_abs_disagreement', 'p90_abs_disagreement', 'median_abs_change_old', 'median_abs_change_new']:
        R[f'{k}|{c}'] = f1(r[c])
    R[k + '|opposite_pct'] = pct(r['opposite_direction_share'])
    R[k + '|ratio_dis_to_change'] = f1(r['ratio_disagreement_to_larger_change'])
    for th in [1, 2]:
        R[f'{k}|above{th}|threshold'] = str(th)
        R[f'{k}|above{th}|dates'] = str(int(r[f'dates_both_above_{th}']))
        if pd.notna(r[f'opposite_share_both_above_{th}']):
            R[f'{k}|above{th}|opposite_pct'] = pct(r[f'opposite_share_both_above_{th}'])
NP = pd.read_csv(RESULTS / 'noise_placebo.csv')
for _, r in NP.iterrows():
    mb = 'annual' if pd.isna(r['months_before']) else f"{int(r['months_before'])}_{int(r['months_after'])}"
    k = f"npl|{r['episode']}|{mb}".replace(' ', '_')
    for c in ['change_old', 'change_new', 'disagreement', 'median_abs_placebo']:
        if pd.notna(r[c]):
            R[f'{k}|{c}'] = f1(r[c])
    R[k + '|share_pct'] = pct(r['share_as_large'])
    R[k + '|pseudo_dates'] = str(int(r['pseudo_dates']))
    if pd.notna(r.get('pseudo_dates_separate')):
        R[k + '|pseudo_dates_sep'] = str(int(r['pseudo_dates_separate']))
        if pd.notna(r['share_as_large_separate']):
            R[k + '|share_sep_pct'] = pct(r['share_as_large_separate'])
    if pd.notna(r.get('pseudo_dates_far')):
        R[k + '|pseudo_dates_far'] = str(int(r['pseudo_dates_far']))
        R[k + '|share_far_pct'] = pct(r['share_as_large_far'])
    if mb != 'annual':
        R[k + '|months_before'] = str(int(r['months_before']))
        R[k + '|months_after'] = str(int(r['months_after']))
_np = NP[NP['episode'] != '2012-14 slowdown']
for ep, g in _np.groupby('episode'):
    R[f'npl|{ep}|share_min_pct'.replace(' ', '_')] = pct(g['share_as_large'].min())
    R[f'npl|{ep}|share_max_pct'.replace(' ', '_')] = pct(g['share_as_large'].max())
    R[f'npl|{ep}|share_sep_min_pct'.replace(' ', '_')] = pct(g['share_as_large_separate'].min())
    R[f'npl|{ep}|share_sep_max_pct'.replace(' ', '_')] = pct(g['share_as_large_separate'].max())
    R[f'npl|{ep}|share_far_min_pct'.replace(' ', '_')] = pct(g['share_as_large_far'].min())
    R[f'npl|{ep}|share_far_max_pct'.replace(' ', '_')] = pct(g['share_as_large_far'].max())
    R[f'npl|{ep}|pseudo_far_min'.replace(' ', '_')] = str(int(g['pseudo_dates_far'].min()))
    R[f'npl|{ep}|pseudo_far_max'.replace(' ', '_')] = str(int(g['pseudo_dates_far'].max()))

AG = pd.read_csv(RESULTS / 'noise_annual_gaps.csv')
for _, r in AG.iterrows():
    for c in ['old', 'new', 'gap']:
        R[f"nag|{r['pair']}|{r['fiscal_year']}|{c}".replace(' ', '_')] = f1(r[c])
for pair, g in AG.groupby('pair'):
    R[f'nag|{pair}|mean_gap'.replace(' ', '_')] = f1(g['gap'].mean())
    R[f'nag|{pair}|years'.replace(' ', '_')] = str(len(g))
NK = pd.read_csv(RESULTS / 'noise_contributions.csv')
R['nk|identity|max_abs_residual'] = f2(NK.loc[NK['pair'] == 'identity check', 'max_abs_residual'].max())
NK = NK[NK['pair'] != 'identity check']
for _, r in NK.iterrows():
    k = f"nk|{r['pair']}|{r['category']}".replace(' ', '_')
    R[k + '|msd_pct'] = pct(r['share_of_msd'])
    R[k + '|msd_pct_1dp'] = f1(100 * r['share_of_msd'])
    R[k + '|msd_half1_pct'] = pct(r['share_of_msd_first_half'])
    R[k + '|msd_half2_pct'] = pct(r['share_of_msd_second_half'])
    R[k + '|mean_gap_pct'] = pct(r['share_of_mean_gap'])
    R[k + '|weight_old'] = f1(r['weight_old'])
    R[k + '|weight_new'] = f1(r['weight_new'])
_o = NK[NK['category'] == 'Other'][['share_of_msd_first_half', 'share_of_msd_second_half']].values
R['nk|Other|half_min_pct'] = pct(_o.min())
R['nk|Other|half_max_pct'] = pct(_o.max())
_cd = NK[NK['category'].isin(['Capital Goods', 'Consumer Durables']) & NK['pair'].isin(['Pair 1', 'Pair 2'])]
_h = _cd.groupby('pair')[['share_of_msd_first_half', 'share_of_msd_second_half']].sum().values
R['nk|capdur_p12|half_min_pct'] = pct(_h.min())
R['nk|capdur_p12|half_max_pct'] = pct(_h.max())
for pair, g in NK.groupby('pair'):
    cd = g[g['category'].isin(['Capital Goods', 'Consumer Durables'])]
    R[f'nk|{pair}|capdur|msd_pct'.replace(' ', '_')] = pct(cd['share_of_msd'].sum())
    R[f'nk|{pair}|capdur|half1_pct'.replace(' ', '_')] = pct(cd['share_of_msd_first_half'].sum())
    R[f'nk|{pair}|capdur|half2_pct'.replace(' ', '_')] = pct(cd['share_of_msd_second_half'].sum())
    R[f'nk|{pair}|capdur|weight_old'.replace(' ', '_')] = f1(cd['weight_old'].sum())
    R[f'nk|{pair}|capdur|weight_new'.replace(' ', '_')] = f1(cd['weight_new'].sum())

INF = pd.read_csv(RESULTS / 'inference.csv')
_names = {'mean gap (new - old)': 'gap', 'rmsd': 'rmsd', 'corr': 'corr', 'capdur_share': 'capdur',
          'ratio: median disagreement / larger median change (6-month)': 'ratio',
          'capdur_share difference': 'capdur_diff'}
for _, r in INF.iterrows():
    p = r['pair'].replace(' ', '_')
    if r['statistic'] in _names:
        nm = _names[r['statistic']]
        fmt = pct if nm in ('capdur', 'capdur_diff') else (f2 if nm in ('corr', 'ratio') else f1)
        for c in ['estimate', 'lo', 'hi']:
            R[f'inf|{p}|{nm}|{c}'] = fmt(r[c])
        if nm == 'ratio':
            R[f'inf|{p}|ratio|dates'] = str(int(r['months_or_dates']))
    elif r['statistic'].startswith('effective windows'):
        L = r['statistic'].split('L=')[1].split()[0]
        k = f'inf|{p}|eff|{L}' + ('|above1' if 'both' in r['statistic'] else '')
        R[k] = f'{r["estimate"]:.1f}'
INS = pd.read_csv(RESULTS / 'inference_sensitivity.csv')
_cd = INS[(INS['statistic'] == 'capdur_share') & INS['pair'].isin(['Pair 1', 'Pair 2'])]
R['inf|capdur_p12|lo_min_all_blocks'] = pct(_cd['lo'].min())
R['inf|capdur_p12|lo_min_all_blocks_1dp'] = f1(100 * _cd['lo'].min())
# share of the splice-rule difference in long-run level due to each overlap's drift (log terms)
_sp = pd.read_csv(RESULTS / 'splice_summary.csv')
_dr = {p_: _sp.loc[_sp['statistic'].str.startswith(p_ + ':'), 'value'].iloc[0] for p_ in ['Pair 1', 'Pair 2', 'Pair 3']}
_lg = {p_: -math.log(1 + v / 100) for p_, v in _dr.items()}
R['splice|pair2_share_of_drift_pct'] = pct(_lg['Pair 2'] / sum(_lg.values()))
_rt = INS[(INS['statistic'].str.startswith('ratio')) & (INS['pair'] == 'Pair 2')]
R['inf|Pair_2|ratio|lo_min_all_blocks'] = f2(_rt['lo'].min())
_r1 = INS[(INS['statistic'].str.startswith('ratio')) & (INS['pair'] == 'Pair 1')]
R['inf|Pair_1|ratio|hi_max_all_blocks'] = f2(_r1['hi'].max())
_g = INS[INS['statistic'] == 'mean gap (new - old)']
for pair, gg in _g.groupby('pair'):
    p_ = pair.replace(' ', '_')
    R[f'inf|{p_}|gap|lo_min_all_lags'] = f1(gg['lo'].min())
    R[f'inf|{p_}|gap|hi_max_all_lags'] = f1(gg['hi'].max())
_c2 = INS[(INS['statistic'] == 'corr') & (INS['pair'] == 'Pair 2')]
R['inf|Pair_2|corr|lo_min_all_blocks'] = f2(_c2['lo'].min())

V3 = pd.read_csv(RESULTS / 'validation_v3_summary.csv')
for _, r in V3.iterrows():
    R[f"valid|{r['pair']}|{r['data_version']}|{r['base_year']}|max_abs_diff".replace(' ', '_')] = f2(r['max_abs_diff_pp'])
    R[f"valid|{r['pair']}|{r['data_version']}|{r['base_year']}|n".replace(' ', '_')] = str(int(r['n']))
V5 = pd.read_csv(RESULTS / 'validation_v5_2022-23_versions.csv')
for _, r in V5.iterrows():
    R[f"versions|{r['series']}|max_abs_diff".replace(' ', '_')] = f1(r['max_abs_diff_index_pts'])
    R[f"versions|{r['series']}|months_differing".replace(' ', '_')] = str(int(r['months_differing']))

WC = pd.read_csv(RESULTS / 'window_contrast.csv')
for _, r in WC.iterrows():
    R[f"window_contrast|{r['pair']}|{int(r['window'])}".replace(' ', '_')] = f2(r['contrast'])
DS = pd.read_csv(RESULTS / 'diagnosis_summary.csv')
for _, r in DS[(DS['family'] == 'use-based') & (DS['data_version'] == 'esankhyiki')].iterrows():
    k = f"leader|{r['pair']}|L{int(r['L'])}|n{int(r['dates'])}".replace(' ', '_')
    R[k + '|agree_pct'] = pct(r['leader_same'])
    R[k + '|chance_freq_pct'] = pct(r['leader_same_chance'])

(RESULTS / 'paper_numbers.json').write_text(json.dumps(R, indent=1, sort_keys=True))
print(f'{len(R)} numbers registered in results/paper_numbers.json')
