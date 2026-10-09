#!/usr/bin/env python3
"""Build a seven-slide, four-minute PDF and matching Markdown speaker script.

Uses approved 3D backgrounds and actual public captures; details stay in appendix.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from pypdf import PdfReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import build_decks as d
import build_3d_decks as art
import build_year_appendix as years

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def furniture(c, page, refs, concept=False):
    d.text(c, 'EARLYSIGNAL / FINVIBE', 56, 29, 17, d.CYAN, True)
    d.text(c, '4분 예선', 1119, 31, 15, d.MUTED)
    d.line(c, 56, 665, 1224, 665, d.LINE, .6)
    d.text(c, 'NHTSA 소비자 신고 · 접수일 기준', 56, 685, 13, d.MUTED)
    d.text(c, '근거 '+refs, 565, 685, 13, d.MUTED)
    d.text(c, f'{page:02d} / 7', 1150, 682, 17, d.TEXT, True)
    if concept:
        d.text(c, '3D 개념 이미지', 1093, 644, 12, d.MUTED)


def plain(c):
    c.setFillColor(d.color(d.BG))
    c.rect(0, 0, d.W, d.H, fill=1, stroke=0)


def cover(c, fact):
    art.background(c, 'cover')
    d.text(c, '소비자 신고를 분석하는 조사 준비 도구', 57, 111, 22, d.CYAN)
    d.block(c, '고객의 목소리를,', 52, 179, 690, 58, d.TEXT, True, leading=72)
    d.block(c, '조사의 근거로', 52, 256, 690, 58, d.CYAN, True, leading=72)
    d.text(c, 'EarlySignal', 57, 357, 30, d.TEXT, True)
    d.text(c, '발표자 표상준', 57, 403, 22, d.TEXT)
    d.block(c, '2018년 미국 현대·기아의 비충돌 화재 신고와\n조사 청원이라는 실제 과거 사건에서 출발했습니다.',
            57, 535, 1150, 23, d.TEXT, leading=33, max_height=76)


def problem(c, fact):
    art.background(c, 'evidence')
    d.block(c, '비슷한 문제도,\n신고는 다르게 쓰입니다', 52, 91, 1168, 44, bold=True, leading=55)
    d.text(c, '“타는 냄새”', 57, 251, 36, d.CYAN, True)
    d.text(c, '“연기가 났어요”', 57, 308, 36, d.CYAN, True)
    d.text(c, '“차가 과열됐어요”', 57, 365, 36, d.CYAN, True)
    d.text(c, '설명용 표현 예', 58, 421, 17, d.MUTED)
    d.text(c, '자동차 회사의 고객 안전 담당자', 57, 480, 24, d.MUTED)
    d.block(c, '키워드 검색은 다른 표현의 신고를 놓칠 수 있습니다.\n원문을 읽고 더 조사할 이유를 찾아야 합니다.', 57, 526, 1160, 27, d.TEXT, True, leading=40)


def roles(c, fact):
    art.background(c, 'roles', y=95, height=510)
    d.block(c, '신고를 정리하고 증가를 찾고\n사람이 검토합니다', 52, 88, 1170, 42, bold=True, leading=52)
    rows = [('LLM', '신고 정리', '소비자 신고 원문을 읽고\n증상을 분류합니다.', d.CYAN),
            ('통계', '증가 확인', '차종별 월간 신고 건수의\n이례적인 증가를 찾습니다.', d.AMBER),
            ('담당자', '조사 결정', '원문을 확인하고\n조사할지 결정합니다.', d.GREEN)]
    for i, (who, title, body, accent) in enumerate(rows):
        x = 56+i*400
        d.text(c, who, x, 418, 22, accent, True)
        d.text(c, title, x, 458, 36, d.TEXT, True)
        d.block(c, body, x, 515, 355, 25, d.TEXT, leading=35)
    d.text(c, '검토한 근거와 판단을 조사 요청서로 남깁니다.', 57, 610, 25, d.TEXT)


def demo(c, fact):
    plain(c)
    d.text(c, '신호에서 조사 요청서까지', 52, 91, 44, d.TEXT, True)
    d.text(c, '공개 웹사이트 실제 저장 화면', 56, 157, 21, d.MUTED)
    for x, label in [(56,'신호 선택'),(353,'원문 검토'),(650,'인용·제외'),(947,'요청서 저장')]:
        d.text(c, label, x, 211, 26, d.CYAN, True)
    d.screenshot_region(c, d.SCREENSHOT, (109,386,1267,535), (56,269,860,363))
    d.text(c, '저장된 요청서', 948, 288, 26, d.TEXT, True)
    d.block(c, '담당자의 판단과\n선택한 근거를 함께 저장', 949, 338, 275, 23, d.TEXT, leading=34)
    d.screenshot_region(c, d.DETAIL_SCREENSHOT, (889,106,488,197), (942,434,282,114))
    d.text(c, 'earlysignal.pages.dev', 947, 577, 19, d.CYAN)
    c.linkURL('https://earlysignal.pages.dev/', (944,107,1224,148), relative=0, thickness=0)


def signal(c, fact):
    plain(c)
    f = fact['example']
    d.block(c, f"평소 약 {round(f['baseline'])}건이던 신고가,\n이번 달 {f['observed']}건으로 늘었습니다", 52, 87, 1170, 43, bold=True, leading=54)
    d.text(c, '쏘나타 · 화재·과열 · 2018년 8월 접수분 · LLM 분류', 56, 213, 21, d.MUTED)
    rows = f['monthly_rows']; top, bottom = 284, 534
    left, right = 93, 879
    ymax = math.ceil(max(r['n'] for r in rows)/5)*5
    def y(value): return bottom-value/ymax*(bottom-top)
    for n in range(0, ymax+1, 5):
        d.line(c, left, y(n), right, y(n), d.LINE, .5)
        d.text(c, str(n), 57, y(n)-9, 17, d.MUTED)
    d.text(c, '고유 신고 수(건)', 56, 256, 18, d.MUTED)
    step=(right-left)/len(rows)
    for i, row in enumerate(rows):
        x=left+i*step+7; width=step-14
        c.setFillColor(d.color(d.CYAN if i==len(rows)-1 else '#41667F'))
        c.rect(x, d.H-bottom, width, bottom-y(row['n']), fill=1, stroke=0)
        d.text(c, str(row['n']), x+6, min(y(row['n'])-27, y(f['baseline'])-27) if row['n']==3 else y(row['n'])-27, 19, d.TEXT, i==len(rows)-1)
        if i in (0,5,12):
            d.text(c, row['month'][:7].replace('-','.'), x-13, 549, 17, d.MUTED)
    c.saveState();c.setDash(5,4)
    d.line(c,left,y(f['baseline']),right,y(f['baseline']),d.AMBER,1.5)
    c.restoreState()
    d.text(c, '직전 12개월 평균', 941, 280, 21, d.MUTED)
    d.text(c, f"{f['baseline']:.2f}건", 938, 320, 49, d.AMBER, True)
    d.text(c, '이번 달', 941, 400, 21, d.MUTED)
    d.text(c, f"{f['observed']}건", 938, 438, 65, d.CYAN, True)
    d.text(c, f"평소의 {f['ratio']:.2f}배", 941, 520, 23, d.TEXT, True)
    d.block(c, '평소 수준에서 이례적인 증가인지 계산해 경보를 냅니다.\n점선은 당월을 제외한 평균이며, 계산한 확률은 결함일 확률이 아닙니다.', 56, 598, 1168, 21, d.TEXT, leading=28)


def validation(c, fact):
    plain(c)
    d.text(c, '확인한 결과와, 남은 검증', 52, 91, 44, d.TEXT, True)
    d.text(c, '키워드의 과거 평가와 LLM의 데모 적용은 범위가 다릅니다.', 56, 162, 23, d.MUTED)
    case=d.MEASURED['validation']['holdout']['case']; control=d.MEASURED['validation']['holdout']['control']
    d.text(c, '키워드 기준선 평가', 56, 253, 29, d.CYAN, True)
    d.text(c, '등록 조사 사례 38개를 나눠 평가', 56, 297, 22, d.MUTED)
    d.text(c, f"{case['hits']} / {case['n']}", 53, 351, 58, d.TEXT, True)
    d.text(c, '검증용 사례의 조사 전 기간 내 경보', 57, 427, 23, d.TEXT)
    d.text(c, f"검증용 대조 {control['hits']} / {control['n']}", 57, 482, 27, d.AMBER, True)
    d.text(c, '해당 기간에 잡지 못한 사례도 많았습니다.', 57, 534, 21, d.MUTED)
    d.text(c, 'LLM 데모 적용', 690, 253, 29, d.GREEN, True)
    d.text(c, '별도 데모 범위의 소비자 신고', 690, 297, 22, d.MUTED)
    d.text(c, f"{d.COMPARISON['population']:,}건", 687, 351, 58, d.TEXT, True)
    d.text(c, '분류와 출력 검사 완료', 691, 427, 25, d.TEXT)
    d.block(c, '분류 정확도와 조기 탐지 성능 개선은\n전문가 검수·같은 조건의 추가 평가가 필요합니다.', 691, 482, 529, 23, d.MUTED, leading=34)
    d.text(c, '왼쪽은 사례·대조 대상 수, 오른쪽은 신고 수입니다. 같은 성능 지표로 비교하지 않습니다.', 57, 611, 20, d.TEXT)


def closing(c, fact):
    art.background(c, 'closing')
    d.block(c, '고객의 목소리를,\n조사의 근거로', 52, 98, 735, 53, d.TEXT, True, leading=68)
    d.block(c, '담당자가 조사할 근거를\n정리하도록 돕습니다', 57, 286, 700, 33, d.CYAN, True, leading=47)
    d.block(c, '신고를 모으고 원문을 확인하고\n근거와 판단이 연결된 요청서를 완성합니다.', 57, 404, 700, 25, d.TEXT, leading=36)
    d.text(c, '다음 단계', 57, 522, 21, d.GREEN, True)
    d.block(c, '전문가와 분류·탐지 검증\n현업 담당자와 검토 시간 측정', 57, 559, 680, 23, d.TEXT, leading=32)
    d.text(c, '감사합니다', 1018, 548, 30, d.TEXT, True)
    d.text(c, '발표자 표상준', 1018, 597, 20, d.TEXT)


DRAW={'cover':cover,'problem':problem,'roles':roles,'demo':demo,'signal':signal,'validation':validation,'closing':closing}


def appendices(old):
    moved = [deepcopy(old[i]) for i in (5,6,7,8)]
    names = ['포아송 모형으로 경보를 계산합니다','키워드 기준선의 38사례 평가','LLM 분류 비교와 대표 신고 요약','도입 계획·실행 비용·Codex 협업']
    for item,title in zip(moved,names):item['title']=title
    result=moved+deepcopy(old[9:])
    for n,item in enumerate(result,1):
        title=re.sub(r'^부록 \d+\.\s*','',item['title'])
        item.update(title=f'부록 {n}. {title}',appendix=True,time=0,appendix_number=n)
    return result


def write_script(story, appendix):
    md=['# EarlySignal 4분 발표 대본','',f"발표자 {story['presenter']}",'',
        f"발표자료: [본문7장·부록15장]({story['pdf']})",'',
        '240초는 발표·조작의 배분안입니다. 실제 타이머 리허설 기록은 아닙니다. 본문은 읽을 문장, 조작 메모는 읽지 않는 지시입니다.','']
    elapsed=0
    def stamp(n):return f'{n//60}:{n%60:02d}'
    for n,item in enumerate(story['main'],1):
        md.extend([f"## {n}. {item['title']}",'',f"{stamp(elapsed)}–{stamp(elapsed+item['seconds'])} · {item['seconds']}초 배분",'','**읽을 문장**',''])
        for para in item['spoken']:md.extend([para,''])
        md.extend(['**조작 메모 — 읽지 않음**','']+['- '+a for a in item['actions']]+[''])
        elapsed+=item['seconds']
    md.extend(['## 부록 찾아보기','', '| PDF 쪽 | 부록 | 내용 |','|---:|---:|---|'])
    for i, item in enumerate(appendix, 1):
        title = re.sub(r'^부록 \d+\.\s*', '', item['title'])
        md.append(f"| {7+i} | {i} | {title} |")
    md.extend(['','## 리허설 메모','',
        '- 시연60초를 포함해 전체4분을 타이머로 확인합니다. 웹 초기 상태·저장 이력·다운로드 위치를 발표 전에 준비합니다.',
        '- 키워드38사례 평가를 LLM의 성능으로 말하지 않습니다. 50.56%는 두 방식의 일치율이며 정확도가 아닙니다.',
        '- 지정PE 대비209·240일을 기관 최초 발견이나 예방 효과로 설명하지 않습니다. 키워드 볼트 놓침·LLM23일 늦음을 보존합니다.',
        '- 모델연도별 필터·독립 경보는 후속 계획입니다. [이슈#35](https://github.com/SangJun-Pyo/EarlySignal/issues/35).',
        '- 근거와 한계: [주장별 근거표](evidence-manifest.md), [현재 SPEC](../SPEC.md).',''])
    assert elapsed==240
    (ROOT/story['script']).write_text('\n'.join(md),encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--storyboard',type=Path,default=ROOT/'storyboard-humanized.json')
    ap.add_argument('--manifest',type=Path,default=ROOT/'humanized-build-manifest.json')
    ap.add_argument('--output-dir',type=Path,default=ROOT/'output/pdf')
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,file in [('KR','IBMPlexSansKR-Regular.ttf'),('KR-Bold','IBMPlexSansKR-SemiBold.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(ROOT/'assets'/file)))
    fact=json.loads((ROOT/'figures/source.json').read_text())
    for entry in fact['sources'][:3]:
        if digest(REPO/entry['path'])!=entry['sha256']:raise ValueError('Reviewed statistical input changed')
    f=fact['example']
    assert sum(r['n'] for r in f['monthly_rows'][:-1])==f['baseline_sum']
    assert math.isclose(f['baseline_sum']/12,f['baseline'])
    assert f['monthly_rows'][-1]['n']==f['observed']
    assert math.isclose(f['observed']/f['baseline'],f['ratio'])
    capture=d.CAPTURE_META
    if digest(REPO/'web/public/data/console.json')!=capture['console_sha256']:raise ValueError('Capture data changed')
    for field,hashfield in [('image','image_sha256'),('detail_image','detail_image_sha256')]:
        if digest(ROOT/capture[field])!=capture[hashfield]:raise ValueError('Actual capture changed')
    story=json.loads(args.storyboard.read_text())
    assert len(story['main'])==7 and sum(s['seconds'] for s in story['main'])==240 and story['main'][3]['seconds']==60
    old=json.loads((ROOT/'storyboard-final.json').read_text())['preliminary']
    appendix=appendices(old);assert len(appendix)==15
    d.RENDERERS.update(figure=d.figure_panel,validation_graph=d.validation_graph,llm_changes=d.llm_changes,
        adoption_codex=d.adoption_codex,llm_flow=d.llm_flow,technical_stats=d.technical_stats,
        comparison_stats=d.comparison_stats,investigation_context=d.investigation_context,
        llm_detail=d.llm_detail,brief_revision=d.brief_revision,rag_scope=d.rag_scope,
        proposal_scope=d.proposal_scope,hypotheses_design=d.hypotheses_design)
    output=args.output_dir/Path(story['pdf']).name
    c=canvas.Canvas(str(output),pagesize=(d.W,d.H),pageCompression=1)
    c.setTitle('EarlySignal | 4분 예선 | 본문7장');c.setAuthor(story['presenter'])
    c.setSubject('제품 시연 중심. 키워드 평가와 LLM 데모 범위 구분. 상세 근거·실패는 부록 보존.')
    for n,item in enumerate(story['main'],1):
        DRAW[item['kind']](c,fact)
        furniture(c,n,item['refs'],item['kind'] in {'cover','problem','roles','closing'})
        c.showPage()
    yearfact=years.extract_years()
    for n,item in enumerate(appendix,8):
        if item['kind'].startswith('model_year'):
            dist=item['kind']=='model_year_distribution'
            title=re.sub(r'^부록 \d+\.\s*','',item['title'])
            subtitle='실제 LLM 분류 근거 · HYUNDAI SONATA · 화재·과열 · 2018년 8월 접수분' if dist else '신고를 나누는 기준이 바뀌면 기준선·경보·요약·평가도 다시 확인해야 합니다.'
            years.frame(c,title,subtitle,item['appendix_number'],n,'4분 예선')
            (years.distribution if dist else years.roadmap)(c,yearfact)
        else:
            d.frame(c,item,n,22,'4분 예선',7)
            d.RENDERERS[item['kind']](c,item)
        c.showPage()
    c.save();write_script(story,appendix)
    story['appendices']=appendix
    args.manifest.write_text(json.dumps({
        'file':output.name,'sha256':digest(output),'pages':len(PdfReader(output).pages),'main_pages':7,'appendix_pages':15,
        'seconds':240,'demo_seconds':60,'presenter':story['presenter'],'actual_rehearsal_completed':False,
        'script_file':story['script'],'script_sha256':digest(ROOT/story['script']),
        'main':story['main'],'appendices':appendix,'model_year_fact':yearfact,
        'statistical_source':'figures/source.json','statistical_source_sha256':digest(ROOT/'figures/source.json'),
        'assets':[{ 'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sorted((ROOT/'assets/3d').glob('*.png'))],
        'capture_provenance':'assets/screenshots/request-public.json'
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Built {output.name}: 7 main + 15 appendix = 22 pages, 240 seconds; Markdown script only.')


if __name__=='__main__':main()
