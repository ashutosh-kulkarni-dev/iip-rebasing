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
plt.rcParams.update({'font.family': 'serif', 'font.size': 8, 'xtick.labelsize': 8, 'ytick.labelsize': 8, 'hatch.linewidth': 0.8, 'axes.edgecolor': MUTED,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.spines.top': False, 'axes.spines.right': False})

T = pd.read_csv(RESULTS / 'tests_h2_tiers.csv')
T = T[T['version'] == 'esankhyiki']
ORDER = ['General', 'Electricity', 'Mining', 'Manufacturing', 'Capital Goods', 'Intermediate Goods',
         'Consumer Durables', 'Consumer Non-durables']
GREY = '#8c8c8c'
# Colour by the per-overlap Holm-adjusted tier (paper v14 onwards); intervals are unadjusted.
# Pair 3 has only 13 dates, so only its point estimates are drawn.
# Drawn at the LNCS text width (12.2 cm = 4.8 in) so that 8 pt text prints at 8 pt.
fig, axes = plt.subplots(1, 3, figsize=(4.8, 3.0), sharey=True)
titles = {'Pair 1': '1993-94 vs\n2004-05', 'Pair 2': '2004-05 vs\n2011-12', 'Pair 3': '2011-12 vs 2022-23\n(24 months)'}
for ax, pair in zip(axes, ['Pair 1', 'Pair 2', 'Pair 3']):
    d = T[T['pair'] == pair].set_index('unit').reindex(ORDER)
    y = np.arange(len(ORDER))[::-1]
    ax.axvline(1, color=MUTED, lw=0.8, ls='--')
    for yi, (u, r) in zip(y, d.iterrows()):
        if pair == 'Pair 3':
            ax.plot(r['R'], yi, 'o', color='white', mec=GREY, mew=1.2, ms=5.5)
            continue
        tier = r['tier'].split(' (')[0]
        c = {'readable': NEW, 'undetermined': GREY, 'unreadable': OLD}[tier]
        # Second encoding for greyscale print: readable = square marker and solid line,
        # undetermined = circle and dashed line.
        mk, ls = ('s', '-') if tier == 'readable' else ('o', (0, (3, 2)))
        ax.plot([r['lo'], r['hi']], [yi, yi], color=c, lw=1.3, alpha=0.8, ls=ls, solid_capstyle='round')
        ax.plot(r['R'], yi, mk, color=c, ms=5.5, mec='black' if tier == 'readable' else 'white', mew=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([u.replace('Consumer ', 'Cons. ') for u in ORDER])
    ax.set_xlim(0, 2.5)
    ax.set_title(titles[pair], fontsize=8, color=INK)
    ax.grid(axis='x', color=GRID, lw=0.5)
    ax.set_xlabel('ratio R')
H = [plt.Line2D([], [], marker='s', color=NEW, mec='black', mew=0.6, ms=5, ls='-', label='Readable (Holm-adjusted)'),
     plt.Line2D([], [], marker='o', color=GREY, ms=5, ls=(0, (3, 2)), label='Undetermined'),
     plt.Line2D([], [], marker='o', color='white', mec=GREY, mew=1.2, ls='', ms=5, label='Point estimate only')]
fig.legend(handles=H, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.03), fontsize=8)
fig.tight_layout(rect=(0, 0.13, 1, 1), w_pad=0.6)
fig.savefig(CHARTS / 'fig4_reliability.png', dpi=300, bbox_inches='tight')
plt.close(fig)

E = pd.read_csv(RESULTS / 'diagnosis_episodes.csv')
E = E[E['family'] == 'use-based']
PANELS = [('GFC', '12 before / 12 after', 'GFC (Pair 1):\nchange'),
          ('Demonetisation', '7 before / 5 after', 'Demonetisation\n(Pair 2): change'),
          ('2012-14 slowdown', 'average of 2012-13 and 2013-14', '2012-14 (Pair 2):\nannual growth')]
UNITS = ['Capital Goods', 'Intermediate Goods', 'Consumer Durables', 'Consumer Non-durables', 'Other', 'General']
fig, axes = plt.subplots(1, 3, figsize=(4.8, 3.2), sharey=True)
for ax, (ep, win, title) in zip(axes, PANELS):
    d = E[(E['episode'] == ep) & (E['window'] == win)].set_index('unit').reindex(UNITS)
    y = np.arange(len(UNITS))[::-1]
    ax.axvline(0, color=MUTED, lw=0.6)
    # Older base hatched so the two bases differ in greyscale print as well as in colour.
    ax.barh(y + 0.19, d['old'], height=0.36, color=OLD, label='Older base', edgecolor='black', linewidth=0.4, hatch='///')
    ax.barh(y - 0.19, d['new'], height=0.36, color=NEW, label='Newer base', edgecolor='black', linewidth=0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(['Other' if u == 'Other' else ('General' if u == 'General' else u.replace('Consumer ', 'Cons. ').replace('Intermediate', 'Interm.')) for u in UNITS])
    ax.set_title(title, fontsize=8, color=INK)
    ax.grid(axis='x', color=GRID, lw=0.5)
    ax.set_xlabel('pp')
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=8)
fig.tight_layout(rect=(0, 0.08, 1, 1), w_pad=0.6)
fig.savefig(CHARTS / 'fig5_episodes.png', dpi=300, bbox_inches='tight')
plt.close(fig)
print('fig4_reliability.png, fig5_episodes.png written')
