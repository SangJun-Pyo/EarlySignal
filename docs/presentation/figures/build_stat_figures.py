#!/usr/bin/env python3
"""Build source-backed figures; the console labeler and keyword validation stay distinct.

Requires matplotlib, numpy, scipy. Reads public/results JSON only; no API/DB access.
The Poisson PMF is an assumed model, not an empirical goodness-of-fit result.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse
import csv
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter, MaxNLocator, PercentFormatter
import numpy as np
from scipy.stats import poisson, binom

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ASSETS = HERE.parent / 'assets'
BG, GRID, TEXT, MUTED = '#0B1626', '#274560', '#E6EEF7', '#9EB3C8'
CYAN, AMBER = '#22D3EE', '#F5A524'
CATEGORY_NAMES = {'fire_thermal':'화재·과열', 'engine_failure':'엔진 파손',
                  'engine_stall':'엔진 꺼짐', 'loss_of_power':'동력 상실',
                  'electrical_failure':'전기 계통', 'lighting':'조명',
                  'airbag':'에어백', 'steering':'조향'}


def load(rel):
    return json.loads((REPO / rel).read_text(encoding='utf-8'))


def provenance(rel):
    return {'path':rel, 'sha256':hashlib.sha256((REPO/rel).read_bytes()).hexdigest()}


def month_index(month):
    d=datetime.strptime(month, '%Y-%m-%d')
    if d.day != 1:
        raise ValueError('Series must use calendar month starts')
    return d.year*12+d.month-1


def following_month(month):
    index=month_index(month)+1
    return f'{index//12:04d}-{index%12+1:02d}-01'


def extract_example(console, rule):
    """Select the configured demo and independently check its causal exported values."""
    labeler=console['labeler']
    if labeler not in ('keyword','llm'):
        raise ValueError('Unknown console labeler')
    demo=console['demo_signal']
    group,category,target=demo['grp'],demo['category'],demo['month']
    series=console['series'][group]
    months=series['months']
    if len(months)!=len(set(months)) or [month_index(m) for m in months] != list(range(month_index(months[0]),month_index(months[-1])+1)):
        raise ValueError('Series must contain consecutive, unique calendar months')
    index=months.index(target)
    if target not in console['asof_months']:
        raise ValueError('Demo month must be an operational as-of month')
    prior_start=max(0,index-rule['baseline_months'])
    history=months[prior_start:index]
    if len(history)<rule['min_history']:
        raise ValueError('Demo does not have enough history for a baseline')
    values=series['categories'][category]
    if any(len(series['total'])!=len(months) or len(values[key])!=len(months) for key in ('n','baseline','alert')):
        raise ValueError('Series arrays must align with months')
    rows=[{'month':months[i], 'n':int(values['n'][i]), 'total':int(series['total'][i])}
          for i in range(prior_start,index+1)]
    if any(r['n']<0 or r['total']<r['n'] for r in rows):
        raise ValueError('Counts must satisfy 0 <= category count <= total')
    baseline_sum=sum(r['n'] for r in rows[:-1])
    raw_mean=baseline_sum/len(history)
    baseline=max(raw_mean,rule['lambda_floor'])
    observed=rows[-1]['n']
    p=float(poisson.sf(observed-1,baseline))
    # Log-factorial summation avoids overflowing at larger observed counts.
    independent_stop=max(observed+100,int(poisson.ppf(1-1e-15,baseline))+1)
    independent=sum(math.exp(-baseline+j*math.log(baseline)-math.lgamma(j+1))
                    for j in range(observed,independent_stop+1))
    if not math.isclose(p,independent,rel_tol=1e-10,abs_tol=1e-14):
        raise ValueError('Poisson SF disagrees with independent summation')
    exported=values['baseline'][index]
    if exported is None or not math.isclose(baseline,exported,rel_tol=1e-12,abs_tol=1e-12):
        raise ValueError('Calculated baseline disagrees with console export')
    alert=p<rule['alpha'] and observed>=rule['min_count']
    if bool(values['alert'][index]) != alert:
        raise ValueError('Calculated alert disagrees with console export')
    historical_total=sum(r['total'] for r in rows[:-1])
    rate=baseline_sum/historical_total if historical_total else None
    binomial_p=float(binom.sf(observed-1,rows[-1]['total'],rate)) if rate is not None else None
    return {'group':group,'category':category,
            'display_name':group.replace('|',' ')+' · '+CATEGORY_NAMES.get(category,category),
            'labeler':labeler,'monthly_rows':rows,'baseline_period':[history[0],history[-1]],
            'target_month':target,'available':following_month(target),
            'baseline_sum':baseline_sum,'baseline_months':len(history),'raw_baseline':raw_mean,
            'baseline':baseline,'observed':observed,'ratio':observed/baseline,'p_value':p,
            'p_value_percent':100*p,'exported_baseline':exported,'alert':alert,
            'comparison_binomial':{'historical_category_sum':baseline_sum,'historical_total_sum':historical_total,
                'historical_rate':rate,'current_total':rows[-1]['total'],'p_value':binomial_p,
                'p_value_percent':100*binomial_p if binomial_p is not None else None,
                'alert':binomial_p<rule['alpha'] and observed>=rule['min_count'] if binomial_p is not None else None,
                'used_for_primary':False,'formula':'scipy.stats.binom.sf(observed-1,current_total,historical_rate)'},
            'formula':'P(X >= observed | X ~ Poisson(baseline)) = scipy.stats.poisson.sf(observed-1,baseline)',
            'verification':{'independent_sum':independent,'independent_stop':independent_stop,
                            'monthly_baseline_matches_export':True,'alert_matches_export':True}}


def configure_fonts():
    for name in ('IBMPlexSansKR-Regular.ttf','IBMPlexSansKR-SemiBold.ttf'):
        font_manager.fontManager.addfont(ASSETS/name)
    family=font_manager.FontProperties(fname=ASSETS/'IBMPlexSansKR-Regular.ttf').get_name()
    plt.rcParams.update({'font.family':family,'font.size':20,'text.color':TEXT,
        'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED,'axes.facecolor':BG,
        'figure.facecolor':BG,'axes.edgecolor':GRID,'axes.unicode_minus':False,'pdf.fonttype':42,'ps.fonttype':42})


def style(ax):
    ax.spines[['top','right']].set_visible(False)
    ax.spines[['left','bottom']].set_linewidth(1)
    ax.tick_params(axis='both',length=0,pad=9)
    ax.set_axisbelow(True)
    ax.grid(axis='y',color=GRID,linewidth=.8)


def save(fig,stem,output):
    fig.savefig(output/f'{stem}.png',dpi=180,facecolor=BG)
    fig.savefig(output/f'{stem}.pdf',facecolor=BG)
    plt.close(fig)


def draw_monthly(example,output):
    rows=example['monthly_rows'];baseline=example['baseline'];last=len(rows)-1
    fig,ax=plt.subplots(figsize=(12.3,4.5))
    fig.subplots_adjust(left=.085,right=.985,bottom=.17,top=.87)
    x=np.arange(len(rows))
    bars=ax.bar(x,[r['n'] for r in rows],width=.63,color=[CYAN]*last+[AMBER],zorder=3)
    bars[-1].set_hatch('//');bars[-1].set_edgecolor(TEXT);bars[-1].set_linewidth(.7)
    ceiling=max(3,max(r['n'] for r in rows)*1.22,baseline*1.15)
    ax.set_ylim(0,ceiling);ax.yaxis.set_major_locator(MaxNLocator(nbins=4,integer=True))
    ax.set_xlim(-.6,last+.65)
    labels=[r['month'][2:7].replace('-','.') if i==0 or i==last or r['month'][5:7]=='01' else r['month'][5:7]
            for i,r in enumerate(rows)]
    ax.set_xticks(x,labels)
    ax.axhline(baseline,color=TEXT,linestyle=(0,(5,4)),linewidth=1.4,zorder=2)
    fig.text(.12,.975,f"직전 {example['baseline_months']}개월 기준선: {baseline:.2f}건",fontsize=22,va='top')
    fig.text(.015,.91,'건',fontsize=20,color=MUTED)
    for i,r in enumerate(rows):
        ax.text(i,r['n']+ceiling*.02,str(r['n']),ha='center',va='bottom',fontsize=22,
                color=AMBER if i==last else TEXT,weight='semibold' if i==last else 'normal')
    style(ax);save(fig,'sonata-monthly-baseline',output)


def draw_poisson(example,output):
    baseline=example['baseline'];observed=example['observed']
    stop=max(10,observed+8,int(poisson.ppf(1-1e-7,baseline)))
    k=np.arange(stop+1);pmf=poisson.pmf(k,baseline)
    ymax=float(max(pmf))*1.22
    fig,ax=plt.subplots(figsize=(12.3,4.5))
    fig.subplots_adjust(left=.085,right=.985,bottom=.235,top=.88)
    ax.bar(k,pmf,width=.72,color=[CYAN if n<observed else AMBER for n in k],zorder=3)
    ax.set_xlim(-.7,stop+.5);ax.set_ylim(0,ymax)
    ticks=set(int(v) for v in MaxNLocator(nbins=6,integer=True).tick_values(0,stop) if 0<=v<=stop)
    ticks.add(observed);ax.set_xticks(sorted(ticks))
    ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    ax.set_xlabel('월 신고 건수',labelpad=10,fontsize=20)
    fig.text(.015,.975,'확률',ha='left',va='top',fontsize=20,color=MUTED)
    fig.text(.148,.972,f'월평균 {baseline:.2f}건을 가정한 분포',fontsize=20,va='top')
    ax.axvline(observed-.5,color=AMBER,linestyle=(0,(4,4)),linewidth=1.3)
    ax.text(observed,ymax*.07,f'{observed}건 이상 →',fontsize=22,color=AMBER,va='bottom')
    style(ax)
    tail=np.arange(observed,observed+7);tail_p=poisson.pmf(tail,baseline)
    tailmax=float(max(tail_p))*1.18
    if example['p_value']<.1 and tailmax>0:
        inset=ax.inset_axes([.58,.40,.40,.55])
        inset.bar(tail,tail_p,width=.65,color=AMBER,zorder=3)
        inset.set_xlim(observed-.6,observed+6.6);inset.set_ylim(0,tailmax)
        inset.set_xticks(tail[::2]);inset.yaxis.set_major_locator(MaxNLocator(nbins=2))
        inset.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'{100*v:.3g}%'))
        inset.tick_params(axis='both',length=0,pad=5,labelsize=20)
        inset.set_title('우측 꼬리 확대 · 별도 세로축',fontsize=20,pad=9)
        inset.spines[['top','right']].set_visible(False)
        inset.grid(axis='y',color=GRID,linewidth=.6);inset.set_axisbelow(True)
        example['tail_expansion']={'n_range':[observed,observed+6],'y_range_probability':[0,tailmax],
                                   'scale':'linear; separately labelled y axis'}
    else:
        example['tail_expansion']=None
    save(fig,'poisson-right-tail',output)
    example.update(pmf_rows=[{'n':int(n),'probability':float(prob)} for n,prob in zip(k,pmf)],
                   pmf_plotted_through=stop,probability_above_plotted_range=float(poisson.sf(stop,baseline)))


def keyword_validation(meta,backtest):
    validation=meta['validation']
    with (REPO/'data/results/backtest.csv').open(encoding='utf-8',newline='') as f:
        csv_rows=list(csv.DictReader(f))
    rows=[]
    for split in ('dev','holdout'):
        for arm in ('case','control'):
            v=validation[split][arm];plural='cases' if arm=='case' else 'controls'
            b=backtest['summary'][split][plural]
            sub=[r for r in csv_rows if r['split']==split and r['arm']==arm]
            if len(sub)!=v['n'] or sum(r['primary_hit']=='True' for r in sub)!=v['hits'] or (v['hits'],v['n'])!=(b['hits'],b['total']):
                raise ValueError('Keyword validation sources disagree')
            outcomes=Counter(r['result'] for r in backtest[plural] if r['split']==split)
            rows.append({'split':split,'arm':arm,**v,'results':dict(outcomes)})
    return rows


def draw_validation(rows,output):
    fig,ax=plt.subplots(figsize=(15.68,3.8))
    fig.subplots_adjust(left=.26,right=.90,bottom=.27,top=.93)
    positions=np.array([3.1,2.25,.9,.05]);maxn=max(r['n'] for r in rows)
    labels=['개발용 사례','개발용 대조군','평가용 사례','평가용 대조군']
    for pos,r in zip(positions,rows):
        accent=CYAN if r['arm']=='case' else AMBER
        ax.barh(pos,r['n'],height=.47,color=BG,edgecolor=GRID,linewidth=1.2,zorder=2)
        ax.barh(pos,r['hits'],height=.47,color=accent,edgecolor=TEXT,linewidth=.5,zorder=3)
        if not r['hits']:ax.plot(0,pos,'|',color=accent,markersize=20,markeredgewidth=2,zorder=3)
        ax.text(maxn*1.04,pos,f"{r['hits']}/{r['n']}",va='center',fontsize=25,color=accent,weight='semibold')
    ax.set_yticks(positions,labels,fontsize=24);ax.set_xlim(0,maxn*1.18)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5,integer=True))
    ax.set_xlabel('키워드 기준선 · 건수 · 채운 막대 = 사전 평가창 경보 있음',fontsize=20,labelpad=10)
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(length=0,pad=10)
    ax.set_axisbelow(True);ax.grid(axis='x',color=GRID,linewidth=.7)
    save(fig,'validation-counts',output)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=HERE)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    configure_fonts()
    console=load('web/public/data/console.json');meta=load('web/public/data/meta.json');backtest=load('data/backtest_kw.json')
    example=extract_example(console,meta['params']);validation=keyword_validation(meta,backtest)
    draw_monthly(example,args.output_dir);draw_poisson(example,args.output_dir);draw_validation(validation,args.output_dir)
    source={'generated_at':datetime.now(timezone.utc).isoformat(),
        'sources':[provenance(p) for p in ('web/public/data/console.json','web/public/data/meta.json','data/backtest_kw.json','data/results/backtest.csv','pipeline/es/detect.py','docs/ADR/ADR-011-retrospective-time-boundaries.md')],
        'labeler':console['labeler'],'example':example,'rule':meta['params'],'validation_labeler':'keyword','validation':validation,
        'validation_definition':{'primary_window':backtest['primary_window'],'window_basis':backtest['evaluation_window_basis'],
            'unit':'Selected investigation case bundles and matched single-model controls; counts with target-category alerts.',
            'limitations':['Not general accuracy or a false-positive rate.','Case bundles and controls have different units.',
                'Group overlap reduces dev/holdout independence.','Receipt-time retrospective analysis does not reconstruct historical file availability.']},
        'verification':{'scipy_poisson_sf_matches_independent_sum':True,**example['verification'],'validation_counts_match_backtest_csv':True},
        'model_assumptions':{'form':'Poisson count model; mean equals variance; independent counts assumption.',
            'tested_fit':False,'tested_independence':False,'note':'Backtest results do not establish Poisson goodness-of-fit or a defect probability.'},
        'figure_files':['sonata-monthly-baseline.png','sonata-monthly-baseline.pdf','poisson-right-tail.png','poisson-right-tail.pdf','validation-counts.png','validation-counts.pdf']}
    (args.output_dir/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'labeler':console['labeler'],'baseline':example['baseline'],'observed':example['observed'],
                      'p_value':example['p_value'],'validation_labeler':'keyword'},ensure_ascii=False))


if __name__=='__main__':main()
