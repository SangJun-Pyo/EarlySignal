#!/usr/bin/env python3
"""Append evidence-backed model-year slides to the preserved 3D PDFs."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import build_decks as d

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def extract_years():
    path = REPO/'web/public/data/console.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    demo = data['demo_signal']
    key = f"{demo['grp']}:{demo['category']}:{demo['month']}"
    evidence = data['evidence'][key]
    ids = evidence['ids']
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate evidence IDs')
    years = Counter()
    for item_id in ids:
        row = data['complaints'][item_id]
        if row['grp'] != demo['grp'] or row['month'] != demo['month'] or demo['category'] not in row['categories']:
            raise ValueError('Complaint does not belong to selected signal')
        if not row['ldate'].startswith(demo['month'][:7]):
            raise ValueError('Receipt month mismatch')
        year = str(row.get('year') or '')
        years['미상' if year in ('', '0', '9999') else year] += 1
    if dict(years) != dict(evidence['years']) or sum(years.values()) != evidence['n']:
        raise ValueError('Recomputed model years disagree with public evidence')
    return {'labeler':data['labeler'], 'evidence_key':key,'count':len(ids),
            'years':sorted(years.items()),'unknown':years.get('미상',0),'duplicate_ids':0,
            'source':'web/public/data/console.json','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def frame(c, title, subtitle, appendix, page, deck):
    c.setFillColor(d.color(d.BG));c.rect(0,0,d.W,d.H,fill=1,stroke=0)
    d.text(c,'EARLYSIGNAL',56,28,18,d.CYAN,True)
    d.text(c,f'{deck}  |  후속 분석 · 이슈 #35',815,30,15,d.MUTED)
    d.block(c,f'부록 {appendix}. {title}',52,86,1176,37,bold=True,leading=46,max_height=92)
    d.block(c,subtitle,56,149,1170,21,d.MUTED,leading=29,max_height=60)
    d.line(c,56,662,1224,662,d.LINE,1)
    d.text(c,'출처: console.json · 코드 · ADR-001 · 이슈 #35',56,681,14,d.MUTED)
    d.text(c,'근거 E30 · E31  |  본문 발표 시간 외',687,681,14,d.MUTED)
    d.text(c,f'{page:02d}',1185,679,18,d.TEXT,True)
    c.linkURL('https://github.com/SangJun-Pyo/EarlySignal/issues/35',(56,15,660,47),relative=0,thickness=0)


def distribution(c, fact):
    d.text(c,'현재 감시: 차종 × 증상 × 접수월, 연식 통합',56,207,21,d.AMBER,True)
    d.text(c,'모델연도별 고유 신고 수',56,265,24,d.TEXT,True)
    for i,(year,count) in enumerate(fact['years']):
        y=320+i*59
        d.text(c,f'{year}년식',57,y,23,d.TEXT)
        c.setFillColor(d.color(d.CYAN))
        c.rect(204,d.H-y-27,count/max(n for _,n in fact['years'])*363,27,fill=1,stroke=0)
        d.text(c,f'{count}건',590,y,25,d.TEXT,True)
    d.text(c,f"미상 연식 {fact['unknown']}건 · ID 중복 {fact['duplicate_ids']}건",56,558,18,d.MUTED)
    d.line(c,698,266,698,579,d.LINE,1)
    d.text(c,f"{fact['count']}건",757,260,76,d.CYAN,True)
    d.text(c,'2018년 8월 접수된 근거 신고',759,349,23,d.TEXT,True)
    d.block(c,'연식은 차량의 모델연도입니다.\n접수연도·제작연도·등록연도와 다릅니다.',759,396,458,21,d.MUTED,leading=31,max_height=93)
    d.block(c,'현재 화면은 연식 분포 상위 4개를 표시합니다.\n연식별 경보와 클릭 필터는 아직 없습니다.',759,493,458,21,d.TEXT,leading=31,max_height=93)
    d.block(c,'신고 건수는 위험률이 아닙니다. 운행대수·주행거리와 차량 나이의 차이를 반영하지 않았으며,\n이 분포만으로 같은 세대·엔진·공통 원인이라고 판단할 수 없습니다.',56,605,1168,19,d.TEXT,leading=25,max_height=50)


def roadmap(c, fact):
    d.text(c,'이번 제출은 현행 차종 감시 유지 · 아래는 후속 계획',56,207,21,d.AMBER,True)
    cols=[
      (56,'분포와 원문 검토','전체 연식 분포·미상 연식 표시\n연식별 원문 필터 검토\n\n필터 후 신고·경보·기준선·요약이\n어떤 모집단인지 명확히 표시'),
      (456,'별도 탐지 실험','연식·확인된 세대·엔진별 비교\n희소 신고·결측·최소 이력 검토\n\n다중 비교·차령·운행대수·\n주행거리 차이를 고려'),
      (856,'새 자료로 검증','개발 자료로 범위·규칙 사전 정의\n새 미관측 기간·차종에서 평가\n\n사후 조사 대상 연식으로\n감시 집단을 선택하지 않음'),
    ]
    for x,title,body in cols:
        d.line(c,x,273,x+350,273,d.CYAN,2)
        d.text(c,title,x,299,28,d.TEXT,True)
        d.block(c,body,x,351,353,22,d.TEXT,leading=32,max_height=192)
    d.text(c,'재사용의 범위',56,544,21,d.CYAN,True)
    d.block(c,'같은 신고·정제 원문·모델·분류 프롬프트라면 기존 라벨은 재사용할 수 있습니다.\n새 연식별 경보에 기존 차종 전체의 대표 요약 캐시를 그대로 붙이지 않습니다.',246,542,969,19,d.MUTED,leading=27,max_height=54)
    d.block(c,'기존 38사례 평가와 209·240일은 현행 차종 감시 결과입니다. 연식별 탐지 성능으로 재사용하지 않습니다.\n풀체인지 이전 차량의 위험이 같다는 가정도 검증하지 않았습니다.',56,605,1168,19,d.TEXT,leading=25,max_height=50)


def build(source, output, deck, fact):
    original=PdfReader(source);before=len(original.pages)
    stream=io.BytesIO();c=canvas.Canvas(stream,pagesize=(d.W,d.H),pageCompression=1)
    frame(c,'연식별 신고 분포와 현재 감시 범위','실제 LLM 분류 근거 | HYUNDAI SONATA · 화재·과열 · 2018년 8월 접수분',before-8,before+1,deck)
    distribution(c,fact);c.showPage()
    frame(c,'연식·세대별 분석은 별도 검증으로 진행합니다','신고를 나누는 기준이 바뀌면 기준선·경보·요약·평가도 다시 확인해야 합니다.',before-7,before+2,deck)
    roadmap(c,fact);c.showPage();c.save();stream.seek(0)
    writer=PdfWriter()
    for p in original.pages:writer.add_page(p)
    for p in PdfReader(stream).pages:writer.add_page(p)
    writer.add_metadata({'/Title':f'EarlySignal | {deck} | 모델연도 부록 추가', '/Author':'FinVibe · Codex 협업', '/Subject':'현행 감시와 후속 모델연도 분석 구분. 이슈 #35. 본문 발표 시간 유지.'})
    writer.write(output)
    return {'file':output.name,'pages':before+2,'preserved_pages':before,'added_pages':[before+1,before+2],
            'source_file':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',type=Path,default=ROOT/'output/pdf')
    ap.add_argument('--source-dir',type=Path,default=ROOT/'output/pdf')
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('KR',str(ROOT/'assets/IBMPlexSansKR-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('KR-Bold',str(ROOT/'assets/IBMPlexSansKR-SemiBold.ttf')))
    fact=extract_years()
    expected=json.loads((ROOT/'qa-3d.json').read_text())['outputs']
    outputs=[]
    for prefix,deck in [('EarlySignal-preliminary-4min','4분 예선'),('EarlySignal-finals-8min-qa2min','결선 8분 + Q&A 2분')]:
        source=args.source_dir/f'{prefix}-3d.pdf'
        check=next(x for x in expected if x['file']==source.name)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=check['sha256']:
            raise ValueError('Input 3D deck differs from reviewed source')
        outputs.append(build(source,args.output_dir/f'{prefix}-3d-v2.pdf',deck,fact))
    result={'fact':fact,'outputs':outputs,'issue':'https://github.com/SangJun-Pyo/EarlySignal/issues/35',
            'issue_state_at_read':'OPEN','product_year_features_implemented':False,'preliminary_seconds':240,'finals_seconds':480,'qa_seconds':120}
    (ROOT/'year-appendix-source.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    story=json.loads((ROOT/'storyboard.json').read_text(encoding='utf-8'))
    story['version']='3d-v2';story['speaker_script']='speaker-script.md'
    for key,entry in zip(('preliminary','finals'),outputs):
        story[key].extend([
          {'title':'연식별 신고 분포와 현재 감시 범위','kind':'model_year_distribution','appendix':True,'time':0,'refs':'E30 · E31'},
          {'title':'연식·세대별 분석은 별도 검증으로 진행합니다','kind':'model_year_plan','appendix':True,'time':0,'refs':'E30 · E31'},
        ])
        story[key+'_pdf']='output/pdf/'+entry['file']
    (ROOT/'storyboard-v2.json').write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
