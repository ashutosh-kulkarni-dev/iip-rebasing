"""Stage 6d: figures for the sectoral-reliability analysis (drawn only from results/*.csv).

  charts/fig4_reliability.png   6-month change ratio R by unit, one panel per overlap, with the widest
                                95% joint stationary-bootstrap interval across mean blocks 12 and 6,
                                coloured by the per-overlap Holm-adjusted tier
                                (Pair 3: point estimates only)
  charts/fig5_episodes.png      use-based contributions in both bases, three episodes
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import RESULTS, CHARTS

CHARTS.mkdir(exist_ok=True)
NEW, OLD = '#2a78d6', '#eb6834'
INK, MUTED, GRID = '#222222', '#6b6b6b', '#e4e4e4'
plt.rcParams.update({'font.family': 'serif', 'font.size': 8, 'axes.edgecolor': MUTED,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.spines.top': False, 'axes.spines.right': False})

T = pd.read_csv(RESULTS / 'tests_h2_tiers.csv')
T = T[T['version'] == 'esankhyiki']
ORDER = ['General', 'Electricity', 'Mining', 'Manufacturing', 'Capital Goods', 'Intermediate Goods',
         'Consumer Durables', 'Consumer Non-durables']
GREY = '#8c8c8c'
# Colour by the per-overlap Holm-adjusted tier (paper v14 onwards); intervals are unadjusted.
# Pair 3 has only 13 dates, so only its point estimates are drawn.
fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.1), sharey=True)
titles = {'Pair 1': '1993-94 vs 2004-05', 'Pair 2': '2004-05 vs 2011-12', 'Pair 3': '2011-12 vs 2022-23 (24 months)'}
for ax, pair in zip(axes, ['Pair 1', 'Pair 2', 'Pair 3']):
    d = T[T['pair'] == pair].set_index('unit').reindex(ORDER)
    y = np.arange(len(ORDER))[::-1]
    ax.axvline(1, color=MUTED, lw=0.8, ls='--')
    for yi, (u, r) in zip(y, d.iterrows()):
        if pair == 'Pair 3':
            ax.plot(r['R'], yi, 'o', color='white', mec=GREY, mew=1.2, ms=5.5)
            continue
        c = {'readable': NEW, 'undetermined': GREY, 'unreadable': OLD}[r['tier'].split(' (')[0]]
        ax.plot([r['lo'], r['hi']], [yi, yi], color=c, lw=1.3, alpha=0.7, solid_capstyle='round')
        ax.plot(r['R'], yi, 'o', color=c, ms=5.5, mec='white', mew=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([u.replace('Consumer ', 'Cons. ') for u in ORDER])
    ax.set_xlim(0, 2.7)
    ax.set_title(titles[pair], fontsize=8, color=INK)
    ax.grid(axis='x', color=GRID, lw=0.5)
    ax.set_xlabel('disagreement ratio R')
H = [plt.Line2D([], [], marker='o', color=NEW, ms=5, label='Readable (Holm-adjusted)'),
     plt.Line2D([], [], marker='o', color=GREY, ms=5, label='Undetermined'),
     plt.Line2D([], [], marker='o', color='white', mec=GREY, mew=1.2, ls='', ms=5, label='Point estimate only')]
fig.legend(handles=H, loc='lower center', ncol=3, frameon=False, bbox_to_anchor=(0.55, -0.02))
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(CHARTS / 'fig4_reliability.png', dpi=300, bbox_inches='tight')
plt.close(fig)

E = pd.read_csv(RESULTS / 'diagnosis_episodes.csv')
E = E[E['family'] == 'use-based']
PANELS = [('GFC', '12 before / 12 after', 'GFC (Pair 1)\nchange: 12 months from Sep 2008\nvs 12 months before'),
          ('Demonetisation', '7 before / 5 after', 'Demonetisation (Pair 2)\nchange: Nov 2016-Mar 2017\nvs Apr-Oct 2016'),
          ('2012-14 slowdown', 'average of 2012-13 and 2013-14', '2012-14 slowdown (Pair 2)\nlevel: annual growth,\naverage of 2012-13 and 2013-14')]
UNITS = ['Capital Goods', 'Intermediate Goods', 'Consumer Durables', 'Consumer Non-durables', 'Other', 'General']
fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.4), sharey=True)
for ax, (ep, win, title) in zip(axes, PANELS):
    d = E[(E['episode'] == ep) & (E['window'] == win)].set_index('unit').reindex(UNITS)
    y = np.arange(len(UNITS))[::-1]
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.barh(y + 0.19, d['old'], height=0.36, color=OLD, label='Older base', edgecolor='white', linewidth=0.5)
    ax.barh(y - 0.19, d['new'], height=0.36, color=NEW, label='Newer base', edgecolor='white', linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(['Other (basic etc.)' if u == 'Other' else ('General (total)' if u == 'General' else u) for u in UNITS])
    ax.set_title(title, fontsize=7.5, color=INK)
    ax.grid(axis='x', color=GRID, lw=0.5)
    ax.set_xlabel('pp of General YoY growth')
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.55, -0.02))
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(CHARTS / 'fig5_episodes.png', dpi=300, bbox_inches='tight')
plt.close(fig)
print('fig4_reliability.png, fig5_episodes.png written')
