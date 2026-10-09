#!/usr/bin/env python3
"""Create a printable Korean speaker script and editable Markdown from JSON."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, HRFlowable

ROOT=Path(__file__).resolve().parent
INK='#14263B';TEAL='#087C90';GRAY='#55677B'


def page_footer(c,doc):
    c.setStrokeColor(HexColor('#D6DFE8'));c.line(44,39,A4[0]-44,39)
    c.setFont('KR',9);c.setFillColor(HexColor(GRAY))
    c.drawString(44,25,'EARLYSIGNAL  |  발표 대본 · 본문 9장 · 부록은 질의응답용')
    c.drawRightString(A4[0]-44,25,str(doc.page))


def make_styles():
    return {
      'title':ParagraphStyle('title',fontName='KR-Bold',fontSize=26,leading=35,textColor=HexColor(INK),spaceAfter=15,wordWrap='CJK'),
      'section':ParagraphStyle('section',fontName='KR-Bold',fontSize=21,leading=29,textColor=HexColor(TEAL),spaceAfter=13,spaceBefore=8,wordWrap='CJK'),
      'heading':ParagraphStyle('heading',fontName='KR-Bold',fontSize=15,leading=22,textColor=HexColor(INK),spaceBefore=13,spaceAfter=8,keepWithNext=True,wordWrap='CJK'),
      'time':ParagraphStyle('time',fontName='KR-Bold',fontSize=10.5,leading=16,textColor=HexColor(TEAL),spaceAfter=9,keepWithNext=True,wordWrap='CJK'),
      'body':ParagraphStyle('body',fontName='KR',fontSize=12.5,leading=20.5,textColor=HexColor(INK),spaceAfter=8,wordWrap='CJK'),
      'note':ParagraphStyle('note',fontName='KR',fontSize=10,leading=16,textColor=HexColor(GRAY),spaceAfter=6,wordWrap='CJK'),
    }


def build(source,output,markdown):
    data=json.loads(source.read_text(encoding='utf-8'))
    style=make_styles();flow=[];md=['# EarlySignal 발표 대본','',data['status'],'']
    def p(text,kind='body'):
        return Paragraph(escape(text).replace('\n','<br/>'),style[kind])
    flow.append(p('EarlySignal 발표 대본','title'))
    for n in data['usage_notes']:
        flow.append(p(n,'note'));md.extend([n,''])
    md.extend(['대상 발표자료:','',f"- [예선 4분]({data['deck_files']['preliminary']})",f"- [결선 8분 + Q&A 2분]({data['deck_files']['finals']})",''])
    for k,label,seconds in [('preliminary','예선 4분',240),('finals','결선 8분',480)]:
        if k=='finals':flow.append(PageBreak())
        flow.append(p(label,'section'));md.extend(['## '+label,''])
        assert len(data[k])==9 and sum(s['seconds'] for s in data[k])==seconds
        for slide in data[k]:
            heading=f"{slide['slide']:02d}. {slide['title']}"
            time=f"{slide['start']}–{slide['end']}  |  {slide['seconds']}초 배분"
            items=[p(heading,'heading'),p(time,'time')]
            items.extend(p(t) for t in slide['spoken'])
            items.append(Spacer(1,3))
            items.extend(p('조작 메모 · '+t,'note') for t in slide['actions'])
            items.append(Spacer(1,6))
            # Each slide is a coherent rehearsal unit; long demos may fill one page.
            flow.append(KeepTogether(items))
            md.extend(['### '+heading,'',time,'','**읽을 문장**',''])
            for t in slide['spoken']:md.extend([t,''])
            md.extend(['**조작 메모 — 읽지 않음**',''])
            md.extend('- '+t for t in slide['actions']);md.append('')
    rehearsal_items=[Spacer(1,12),p('리허설 메모','heading')];md.extend(['## 리허설 메모',''])
    for text in data['rehearsal']:
        rehearsal_items.append(p(text,'note'));md.extend(['- '+text,''])
    rehearsal_items.append(p('연식 후속 계획: https://github.com/SangJun-Pyo/EarlySignal/issues/35','note'))
    flow.append(KeepTogether(rehearsal_items))
    flow.extend([PageBreak(),p('질의응답 2분 준비','section')]);md.extend(['## 질의응답 2분 준비',''])
    for text in data['qa_strategy']:
        flow.append(p(text,'note'));md.extend([text,''])
    for question in data['qa']:
        loc=question['appendix']
        location='연결 슬라이드 · 예선 '+', '.join(map(str,loc['preliminary']))+'쪽 / 결선 '+', '.join(map(str,loc['finals']))+'쪽'
        flow.append(KeepTogether([p(question['question'],'heading'),p(f"{question['seconds']}초 답변 배분  |  {location}",'time')]+[p(t) for t in question['spoken']]))
        md.extend(['### '+question['question'],'',location,''])
        for t in question['spoken']:md.extend([t,''])
    md.extend(['근거: [이슈 #35](https://github.com/SangJun-Pyo/EarlySignal/issues/35), [근거표](evidence-manifest.md), [기존 발표자 노트](speaker-notes.md).',''])
    pdf=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=55,
                          title='EarlySignal | 예선·결선 발표 대본',author='FinVibe · Codex 협업')
    pdf.build(flow,onFirstPage=page_footer,onLaterPages=page_footer)
    markdown.write_text('\n'.join(md),encoding='utf-8')
    return {'file':output.name,'pages':len(PdfReader(output).pages),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'spoken_nonspace_characters':{k:sum(len(''.join(''.join(s['spoken']).split())) for s in data[k]) for k in ('preliminary','finals')},
            'preliminary_seconds':240,'finals_seconds':480,'qa_seconds':120,'actual_rehearsal_completed':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=ROOT/'speaker-script.json')
    ap.add_argument('--output-dir',type=Path,default=ROOT/'output/pdf')
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('KR',str(ROOT/'assets/IBMPlexSansKR-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('KR-Bold',str(ROOT/'assets/IBMPlexSansKR-SemiBold.ttf')))
    result=build(args.source,args.output_dir/'EarlySignal-presentation-script.pdf',ROOT/'speaker-script.md')
    (ROOT/'speaker-script-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
