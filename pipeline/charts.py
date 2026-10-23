"""Stage 6: figures for the paper, drawn only from results/*.csv and the clean data.

  charts/fig1_overlaps.png      General-index YoY growth in both bases, one panel per pair
  charts/fig2_correlation.png   correlation between bases by series and pair (95% block-bootstrap CI)
  charts/fig3_splice.png        spliced General index under two splice rules
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from config import PAIRS, RESULTS, CHARTS, GFC_START, GFC_END
from common import true_yoy

CHARTS.mkdir(exist_ok=True)
NEW, OLD = '#2a78d6', '#eb6834'          # categorical slots 1 and 2 (validated default palette)
PAIR_C = ['#2a78d6', '#eb6834', '#1baf7a']
INK, MUTED, GRID = '#222222', '#6b6b6b', '#e4e4e4'
plt.rcParams.update({'font.family': 'serif', 'font.size': 8, 'axes.edgecolor': MUTED,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.spines.top': False, 'axes.spines.right': False, 'lines.linewidth': 1.4})

# Fig 1 -----------------------------------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(3.5, 5.8))
for ax, (pair, old, new, start, end) in zip(axes, PAIRS):
    s = pd.Timestamp(start) + pd.DateOffset(months=12)
    yo, yn = true_yoy(old)['General'].loc[s:end], true_yoy(new)['General'].loc[s:end]
    ax.axhline(0, color=MUTED, lw=0.6)
    if pair == 'Pair 1':
        ax.axvspan(pd.Timestamp(GFC_START), pd.Timestamp(GFC_END), color=GRID, lw=0)
        ax.text(pd.Timestamp('2009-06-01'), 20.5, 'GFC window', ha='center', va='top',
                fontsize=6.5, color=MUTED)
    ax.plot(yo.index, yo, color=OLD, ls='--', label=f'{old} base')
    ax.plot(yn.index, yn, color=NEW, label=f'{new} base')
    ax.set_title(f'{pair}: {old} vs {new}', fontsize=8, loc='left', color=INK)
    ax.set_ylabel('YoY growth, %')
    ax.grid(axis='y', color=GRID, lw=0.5)
    if pair == 'Pair 3':
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[4, 10]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    else:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
handles, _ = axes[0].get_legend_handles_labels()
fig.legend(handles, ['Older base', 'Newer base'], frameon=False, fontsize=7, ncol=2,
           loc='upper center', bbox_to_anchor=(0.55, 1.0))
fig.tight_layout(h_pad=0.8, rect=(0, 0, 1, 0.97))
fig.savefig(CHARTS / 'fig1_overlaps.png', dpi=300)
plt.close(fig)

# Fig 2 -----------------------------------------------------------------------------------
S = pd.read_csv(RESULTS / 'overlap_stats.csv')
S = S[(S['sample'] == 'true YoY (from month 13)') & (S['data_version'] == 'esankhyiki')]
order = ['General', 'Electricity', 'Mining', 'Manufacturing', 'Capital Goods', 'Intermediate Goods',
         'Consumer Durables', 'Consumer Non-durables']
fig, ax = plt.subplots(figsize=(3.5, 3.1))
markers = ['o', 's', '^']
for k, (pair, old, new, *_r) in enumerate(PAIRS):
    d = S[S['pair'] == pair].set_index('series').reindex(order)
    y = [i + (k - 1) * 0.24 for i in range(len(order))]
    ax.errorbar(d['corr'], y, xerr=[d['corr'] - d['corr_ci_lo'], d['corr_ci_hi'] - d['corr']],
                fmt=markers[k], color=PAIR_C[k], ms=4.5, elinewidth=0.8, capsize=0,
                label=f'{pair} ({old}/{new}, n={int(d["months"].iloc[0])})')
ax.axvline(0, color=MUTED, lw=0.6)
ax.set_yticks(range(len(order)))
ax.set_yticklabels(order)
ax.invert_yaxis()
ax.set_xlim(-0.5, 1.05)
ax.set_xlabel('Correlation of YoY growth between bases')
ax.grid(axis='x', color=GRID, lw=0.5)
ax.legend(frameon=False, fontsize=6, loc='lower left', bbox_to_anchor=(-0.45, -0.42), ncol=1)
fig.tight_layout()
fig.savefig(CHARTS / 'fig2_correlation.png', dpi=300, bbox_inches='tight')
plt.close(fig)

# Fig 3 -----------------------------------------------------------------------------------
SP = pd.read_csv(RESULTS / 'splice_series.csv', parse_dates=['date']).set_index('date')
fig, ax = plt.subplots(figsize=(3.5, 2.5))
w = SP.loc['2006-04-01':'2019-03-01']
ax.axhline(0, color=MUTED, lw=0.6)
ax.plot(w.index, w['old base last, base-year factor yoy'], color=MUTED, ls=':', lw=1.1,
        label='Old base kept, base-year factor')
ax.plot(w.index, w['old base last yoy'], color=OLD, ls='--', label='Old base kept, linked at switch')
ax.plot(w.index, w['new base first yoy'], color=NEW, label='New base from its start')
for t in ['2011-07-01', '2012-04-01', '2017-04-01']:
    ax.axvline(pd.Timestamp(t), color=GRID, lw=0.8)
ax.set_ylabel('Spliced YoY growth, %')
ax.grid(axis='y', color=GRID, lw=0.5)
ax.legend(frameon=False, fontsize=6, loc='upper center', bbox_to_anchor=(0.5, 1.32), ncol=1)
fig.tight_layout()
fig.savefig(CHARTS / 'fig3_splice.png', dpi=300)
plt.close(fig)
print('Figures written to', CHARTS)

# Fig E: the two overlaps that contain the episodes, with the episode windows shaded ----------
fig, axes = plt.subplots(2, 1, figsize=(3.5, 4.2))
for ax, (pair, old, new, start, end), shades in zip(
        axes, PAIRS[:2],
        [[('2008-09-01', '2010-03-01', 'GFC')],
         [('2012-04-01', '2014-03-01', '2012-14'), ('2016-11-01', '2017-03-01', 'Demon.')]]):
    s0 = pd.Timestamp(start) + pd.DateOffset(months=12)  # newer base: true YoY from its 13th month
    yo, yn = true_yoy(old)['General'].loc[start:end], true_yoy(new)['General'].loc[s0:end]
    ax.axhline(0, color=MUTED, lw=0.6)
    for a, b, lab in shades:
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=GRID, lw=0)
        ax.text(pd.Timestamp(a) + (pd.Timestamp(b) - pd.Timestamp(a)) / 2, 0.97, lab, transform=ax.get_xaxis_transform(),
                ha='center', va='top', fontsize=6.5, color=MUTED)
    ax.plot(yo.index, yo, color=OLD, ls='--')
    ax.plot(yn.index, yn, color=NEW)
    ax.set_title(f'{old} base (dashed) vs {new} base (solid)', fontsize=8, loc='left', color=INK)
    ax.set_ylabel('YoY growth, %')
    ax.grid(axis='y', color=GRID, lw=0.5)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
fig.tight_layout(h_pad=0.8)
fig.savefig(CHARTS / 'fig_episodes.png', dpi=300)
plt.close(fig)
