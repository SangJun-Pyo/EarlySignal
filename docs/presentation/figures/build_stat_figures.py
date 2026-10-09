#!/usr/bin/env python3
"""Reproduce static presentation figures from exported pipeline results.

Run: python docs/presentation/figures/build_stat_figures.py
Requires matplotlib, numpy, scipy. Uses repo-relative paths; no API/DB writes.
The Poisson PMF is an assumed model, not an empirical goodness-of-fit result.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import math
import csv
import json
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter
import numpy as np
from scipy.stats import poisson, binom

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ASSETS = HERE.parent / 'assets'
BG, GRID, TEXT, MUTED = '#0B1626', '#274560', '#E6EEF7', '#9EB3C8'
CYAN, AMBER = '#22D3EE', '#F5A524'
for name in ('IBMPlexSansKR-Regular.ttf', 'IBMPlexSansKR-SemiBold.ttf'):
    font_manager.fontManager.addfont(ASSETS / name)
FONT = font_manager.FontProperties(fname=ASSETS / 'IBMPlexSansKR-Regular.ttf').get_name()
plt.rcParams.update({'font.family': FONT, 'font.size': 20, 'text.color':TEXT,
                     'axes.labelcolor':MUTED, 'xtick.color':MUTED, 'ytick.color':MUTED,
                     'axes.facecolor':BG, 'figure.facecolor':BG, 'axes.edgecolor':GRID,
                     'axes.unicode_minus':False, 'pdf.fonttype':42, 'ps.fonttype':42})


def load(rel):
    path=REPO / rel
    return json.loads(path.read_text(encoding='utf-8'))


def provenance(rel):
    path=REPO / rel
    return {'path':rel, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def style(ax):
    ax.spines[['top','right']].set_visible(False)
    ax.spines[['left','bottom']].set_linewidth(1)
    ax.tick_params(axis='both', length=0, pad=9)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color=GRID, linewidth=.8)


def save(fig, stem):
    fig.savefig(HERE / f'{stem}.png', dpi=180, facecolor=BG)
    fig.savefig(HERE / f'{stem}.pdf', facecolor=BG)
    plt.close(fig)


console=load('web/public/data/console.json')
meta=load('web/public/data/meta.json')
backtest=load('data/backtest_kw.json')
series=console['series']['HYUNDAI|SONATA']
rows=[{'month':m,'n':int(series['categories']['fire_thermal']['n'][i]),'total':int(series['total'][i])}
      for i,m in enumerate(series['months']) if '2017-08-01'<=m<='2018-08-01']
assert len(rows)==13 and rows[-1]['month']=='2018-08-01'
baseline=sum(r['n'] for r in rows[:-1])/12
observed=rows[-1]['n']
p=float(poisson.sf(observed-1, baseline))
independent_p=sum(math.exp(-baseline)*baseline**j/math.factorial(j) for j in range(observed,101))
assert abs(p-independent_p)<1e-14
historical_total=sum(r['total'] for r in rows[:-1])
historical_rate=sum(r['n'] for r in rows[:-1])/historical_total
binomial_p=float(binom.sf(observed-1,rows[-1]['total'],historical_rate))
export_baseline=series['categories']['fire_thermal']['baseline'][series['months'].index('2018-08-01')]
assert abs(baseline-export_baseline)<1e-12
assert baseline==82/12 and observed==17
rule=meta['params']
assert rule['alpha']==.001 and rule['min_count']==3

# Figure 1: all thirteen actual months, no subsequent observations.
fig, ax=plt.subplots(figsize=(12.3,4.5))
fig.subplots_adjust(left=.085,right=.985,bottom=.17,top=.95)
x=np.arange(13)
bars=ax.bar(x,[r['n'] for r in rows],width=.63,color=[CYAN]*12+[AMBER],zorder=3)
bars[-1].set_hatch('//'); bars[-1].set_edgecolor(TEXT); bars[-1].set_linewidth(.7)
ax.set_ylim(0,20); ax.set_yticks([0,5,10,15,20],['0','5','10','15','20건']); ax.set_xlim(-.6,12.65)
ax.set_xticks(x, ['17.08','09','10','11','12','18.01','02','03','04','05','06','07','18.08'])
ax.axhline(baseline,color=TEXT,linestyle=(0,(5,4)),linewidth=1.4,zorder=2)
ax.text(.0,18.8,'직전 12개월: 월평균 6.83건',fontsize=22,color=TEXT,ha='left')
for i,r in enumerate(rows):
    ax.text(i,r['n']+.32,str(r['n']),ha='center',va='bottom',fontsize=22,
            color=AMBER if i==12 else TEXT,weight='semibold' if i==12 else 'normal')
style(ax); save(fig,'sonata-monthly-baseline')

# Figure 2: Poisson integer PMF, with a separately labelled small-tail scale.
k=np.arange(26); pmf=poisson.pmf(k,baseline)
fig, ax=plt.subplots(figsize=(12.3,4.5))
fig.subplots_adjust(left=.085,right=.985,bottom=.235,top=.94)
ax.bar(k,pmf,width=.72,color=[CYAN if n<17 else AMBER for n in k],zorder=3)
ax.set_xlim(-.7,25.5); ax.set_ylim(0,.175)
ax.set_xticks([0,5,10,15,17,20,25]); ax.set_yticks([0,.05,.10,.15])
ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
ax.set_xlabel('월 신고 건수',labelpad=10,fontsize=20)
fig.text(.015,.975,'확률',ha='left',va='top',fontsize=20,color=MUTED)
ax.axvline(16.5,color=AMBER,linestyle=(0,(4,4)),linewidth=1.3)
ax.text(17.0,.016,'17건 이상 →',fontsize=22,color=AMBER,ha='left',va='bottom')
fig.text(.148,.972,'월평균 6.83건을 가정한 분포',fontsize=20,color=TEXT,ha='left',va='top')
style(ax)
inset=ax.inset_axes([.58,.39,.40,.55])
tail_k=np.arange(17,24); tail_p=poisson.pmf(tail_k,baseline)
inset.bar(tail_k,tail_p,width=.65,color=AMBER,zorder=3)
inset.set_xlim(16.4,23.6); inset.set_ylim(0,.00055)
inset.set_xticks([17,19,21,23]); inset.set_yticks([0,.00025,.00050])
inset.yaxis.set_major_formatter(PercentFormatter(1,decimals=3))
inset.tick_params(axis='both',length=0,pad=5,labelsize=20)
inset.set_title('우측 꼬리 확대 · 별도 세로축',fontsize=20,color=TEXT,pad=9)
inset.spines[['top','right']].set_visible(False)
inset.grid(axis='y',color=GRID,linewidth=.6); inset.set_axisbelow(True)
save(fig,'poisson-right-tail')

# Figure 3: counts and denominators, rather than an unqualified accuracy metric.
validation=meta['validation']
with (REPO/'data/results/backtest.csv').open(encoding='utf-8',newline='') as f:
    csv_rows=list(csv.DictReader(f))
for split in ('dev','holdout'):
    for arm in ('case','control'):
        sub=[r for r in csv_rows if r['split']==split and r['arm']==arm]
        assert len(sub)==validation[split][arm]['n']
        assert sum(r['primary_hit']=='True' for r in sub)==validation[split][arm]['hits']
chart_rows=[]
for split in ('dev','holdout'):
    for arm in ('case','control'):
        v=validation[split][arm]
        b=backtest['summary'][split]['cases' if arm=='case' else 'controls']
        assert (v['hits'],v['n'])==(b['hits'],b['total'])
        results=Counter(r['result'] for r in backtest['cases' if arm=='case' else 'controls'] if r['split']==split)
        chart_rows.append({'split':split,'arm':arm,**v,'results':dict(results)})
fig, ax=plt.subplots(figsize=(15.68,3.8))
fig.subplots_adjust(left=.26,right=.90,bottom=.27,top=.93)
y=np.array([3.1,2.25,.9,.05])
labels=['개발용 사례','개발용 대조군','평가용 사례','평가용 대조군']
for pos,label,r in zip(y,labels,chart_rows):
    color=CYAN if r['arm']=='case' else AMBER
    ax.barh(pos,r['n'],height=.47,color=BG,edgecolor=GRID,linewidth=1.2,zorder=2)
    ax.barh(pos,r['hits'],height=.47,color=color,edgecolor=TEXT,linewidth=.5,zorder=3)
    if r['hits']==0:
        ax.plot(0,pos,'|',color=color,markersize=20,markeredgewidth=2,zorder=3)
    ax.text(19.7,pos,f"{r['hits']}/{r['n']}",va='center',fontsize=25,color=color,weight='semibold')
ax.set_yticks(y,labels,fontsize=24); ax.set_xlim(0,22.5)
ax.set_xticks([0,5,10,15,19],['0','5','10','15','19'])
ax.set_xlabel('건수 · 채운 막대 = 사전 평가창에서 경보가 있었음',fontsize=20,labelpad=10)
ax.spines[['top','right','left']].set_visible(False); ax.spines['bottom'].set_color(GRID)
ax.tick_params(length=0,pad=10); ax.set_axisbelow(True)
ax.grid(axis='x',color=GRID,linewidth=.7)
save(fig,'validation-counts')

source={'generated_at':datetime.now(timezone.utc).isoformat(),
 'sources':[provenance(p) for p in ('web/public/data/console.json','web/public/data/meta.json','data/backtest_kw.json','data/results/backtest.csv','pipeline/es/detect.py','docs/ADR/ADR-011-retrospective-time-boundaries.md')],
 'labeler':console['labeler'],
 'example':{'group':'HYUNDAI|SONATA','category':'fire_thermal','display_name':'SONATA · 화재·열 관련 신고',
            'monthly_rows':rows,'baseline_period':['2017-08-01','2018-07-01'],'target_month':'2018-08-01',
            'baseline_sum':sum(r['n'] for r in rows[:-1]),'baseline_months':12,'baseline':baseline,
            'observed':observed,'ratio':observed/baseline,'p_value':p,'p_value_percent':100*p,
            'comparison_binomial':{'historical_category_sum':sum(r['n'] for r in rows[:-1]),'historical_total_sum':historical_total,'historical_rate':historical_rate,'current_total':rows[-1]['total'],'p_value':binomial_p,'p_value_percent':100*binomial_p,'alert':binomial_p<rule['alpha'] and observed>=rule['min_count'],'used_for_primary':False,'formula':'scipy.stats.binom.sf(observed-1, current_total, historical_category_sum/historical_total_sum)'},
            'exported_baseline':export_baseline,'alert':p<rule['alpha'] and observed>=rule['min_count'],
            'formula':'P(X >= observed | X ~ Poisson(baseline)) = scipy.stats.poisson.sf(observed-1, baseline)',
            'pmf_rows':[{'n':int(n),'probability':float(prob)} for n,prob in zip(k,pmf)],
            'pmf_plotted_through':25,'probability_above_plotted_range':float(poisson.sf(25,baseline)),
            'tail_expansion':{'n_range':[17,23],'y_range_probability':[0,.00055],'scale':'linear; separately labelled y axis'}},
 'rule':rule,'validation':chart_rows,
 'validation_definition':{'primary_window':backtest['primary_window'],'window_basis':backtest['evaluation_window_basis'],
                          'unit':'Selected investigation case bundles and matched single-model controls; counts of units with a target-category alert in the specified window.',
                          'split':'38 selected investigation cases randomized dev/holdout, seed 42; controls 19 dev and 17 holdout.',
                          'limitations':['This is not general accuracy or a false-positive rate.','Case bundles and single-model controls have different units.','Group overlap between dev/holdout reduces independence.','Current file LDATE supports retrospective receipt-time analysis, not a historical file availability reconstruction.']},
 'verification':{'scipy_poisson_sf_matches_independent_sum':True,'independent_sum_17_to_100':independent_p,'monthly_baseline_matches_export':True,'validation_counts_match_backtest_csv':True},
 'model_assumptions':{'form':'Poisson count model; mean equals variance under model; independent counts assumption.',
                      'tested_fit':False,'tested_independence':False,
                      'note':'PMF is an assumed theoretical distribution. Backtest results assess alerts on selected cases; they do not establish Poisson goodness-of-fit, independence, or the probability of a defect.'},
 'figure_files':['sonata-monthly-baseline.png','sonata-monthly-baseline.pdf','poisson-right-tail.png','poisson-right-tail.pdf','validation-counts.png','validation-counts.pdf']}
(HERE/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'baseline':baseline,'observed':observed,'p_value':p,'p_percent':100*p,'validation':validation,'outputs':source['figure_files']},ensure_ascii=False))
