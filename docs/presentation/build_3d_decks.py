#!/usr/bin/env python3
"""Decorate four narrative pages; copy all evidence pages from the reviewed PDFs.

Requires reportlab and pypdf. All paths are relative to this file or CLI arguments.
Existing final PDFs, storyboard and QA snapshots are never overwritten.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

import build_decks as d

ROOT = Path(__file__).resolve().parent
ART = ROOT / 'assets' / '3d'
CHANGED = (1, 2, 3, 9)


def background(c, name, x=0, y=0, width=1280, height=720):
    c.setFillColor(d.color(d.BG))
    c.rect(0, 0, d.W, d.H, fill=1, stroke=0)
    c.drawImage(ImageReader(str(ART / f'{name}.png')), x, d.H-y-height,
                width=width, height=height)


def footer(c, s, page, deck):
    d.line(c, 56, 665, 1224, 665, '#274560', .6)
    d.text(c, 'EARLYSIGNAL  /  FINVIBE', 56, 27, 17, d.CYAN, True)
    d.text(c, f'{deck}  |  발표자료 · 2026.10.09', 756, 29, 14, d.MUTED)
    d.text(c, f'발표자료 · {d.LABELER_NAME} 제품 · 38사례는 키워드 검증', 56, 685, 13, d.MUTED)
    d.text(c, f'근거 {s["refs"]}', 610, 685, 13, d.MUTED)
    d.text(c, f'{page:02d} / 9', 1151, 682, 17, d.TEXT, True)


def note(c, content, y=614, size=19):
    d.block(c, content, 56, y, 1168, size, d.TEXT, leading=25, max_height=50)


def cover(c, s):
    background(c, 'cover')
    d.text(c, s['tag'], 57, 93, 17, d.CYAN, True)
    d.block(c, '고객의 목소리를,', 52, 152, 680, 59, d.TEXT, True, leading=72)
    d.block(c, '조사의 근거로.', 52, 231, 680, 59, d.CYAN, True, leading=72)
    d.text(c, '2018년 미국, 현대·기아 차량의 비충돌 화재.', 57, 359, 24, d.TEXT, True)
    d.block(c, '신고가 쌓이며 조사 청원과 검토가 이어졌습니다.\n이 과거 사건으로, 조사 근거를 정리하는 도구를 만들었습니다.',
            57, 405, 650, 21, d.MUTED, leading=31, max_height=70)
    d.text(c, '공식 기록의 흐름', 57, 501, 17, d.MUTED, True)
    for x, date, label in ((57, '2018.06.11', 'CAS 조사 청원'),
                           (456, '2018.08.21', 'DP18-003 청원 검토'),
                           (854, '2019.03.29', '지정 예비조사(PE) 개시')):
        d.line(c, x, 529, x+360, 529, '#31566F', 1)
        d.text(c, date, x, 541, 25, d.CYAN, True)
        d.text(c, label, x, 576, 19, d.TEXT)
    note(c, '앞선 조사 이력을 함께 봅니다. 지정 PE보다 이른 날짜가 기관의 최초 인지·조사보다 앞섰다는 뜻은 아닙니다.', 622, 17)
    d.text(c, '3D 개념 이미지', 1093, 494, 12, d.MUTED)


def problem(c, s):
    background(c, 'evidence')
    d.block(c, s['title'], 52, 84, 1176, 37, bold=True, leading=46, max_height=92)
    d.block(c, s['subtitle'].replace(' → ', '\n→ '), 56, 153, 650, 19, d.MUTED, leading=27, max_height=81)
    d.text(c, s['status'], 56, 232, 15, d.AMBER, True)
    # Retain every original card paragraph, including the example disclosure.
    rows = [
        ('운전자의 신고', '타는 냄새, 연기, 과열처럼\n같은 현상도 서로 다르게 표현됩니다. · 설명용 표현 예', d.CYAN),
        ('담당자의 검토', '어떤 차종에서 어떤 증상이 평소보다 늘었는지 찾고\n실제 원문을 읽습니다. · 조사할 후보를 정리', d.AMBER),
        ('조사 요청', '“이 차종을 더 살펴봅시다.”\n조사할 이유, 근거 신고, 아직 모르는 사항을 문서로 남깁니다.', d.GREEN),
    ]
    for i, (title, body, accent) in enumerate(rows):
        y = 280 + i*108
        d.text(c, title, 57, y, 24, accent, True)
        d.block(c, body, 57, y+34, 540, 19, d.TEXT, leading=25, max_height=75)
    note(c, s['takeaway'], 624, 18)
    d.text(c, '3D 개념 이미지', 1093, 588, 12, d.MUTED)


def roles(c, s):
    background(c, 'roles', y=95, height=510)
    d.block(c, s['title'], 52, 84, 1176, 40, bold=True, leading=49, max_height=98)
    d.block(c, s['subtitle'], 56, 151, 1170, 21, d.MUTED, leading=29, max_height=60)
    d.text(c, s['status'], 56, 194, 15, d.AMBER, True)
    for i, (kicker, title, body, label, accent) in enumerate(d.ROLES):
        x = 56+i*400
        d.text(c, kicker, x, 418, 17, accent, True)
        d.text(c, title, x, 449, 38, d.TEXT, True)
        d.block(c, body, x, 502, 360, 23, d.TEXT, leading=31, max_height=93)
        d.text(c, label, x, 578, 17, d.MUTED)
    note(c, s['takeaway'], 622, 18)
    d.text(c, '3D 개념 이미지', 1093, 393, 12, d.MUTED)


def closing(c, s):
    background(c, 'closing')
    d.text(c, '고객의 목소리를,', 52, 92, 53, d.TEXT, True)
    d.text(c, '조사의 근거로.', 52, 159, 53, d.CYAN, True)
    d.text(c, s['title'], 57, 242, 28, d.TEXT, True)
    d.block(c, s['subtitle'], 57, 286, 690, 18, d.MUTED, leading=26, max_height=52)
    d.text(c, s['status'], 57, 345, 14, d.AMBER, True)
    d.text(c, '고객 안전 담당자', 57, 380, 23, d.CYAN, True)
    d.block(c, '원문 검토와 조사 요청서 준비\n도입 가설을 현장에서 확인\n검토 시간·요청서 활용 측정\n구매 의사·예방 효과는 미확인',
            57, 420, 340, 18, d.TEXT, leading=25, max_height=100)
    d.text(c, 'Codex와 개선', 445, 380, 23, d.GREEN, True)
    d.block(c, '이슈 → 작업트리 → PR\n구현과 독립 검수를 분리\n\n요약 과장 발견 → 공개 거부\n기존 AI 요약 인용으로 변경',
            445, 420, 300, 18, d.TEXT, leading=25, max_height=125)
    amount=float(d.BRIEF_AUDIT['costs']['combined_label_and_brief_experiments_estimated_usd'])
    d.text(c, '실제 실행과 비용', 57, 541, 18, d.AMBER, True)
    d.text(c, f"LLM {d.MEASURED['labels']['llm_labeled']:,}건 출력 검사 · 누적 실험 약 ${amount:.2f}", 57, 568, 19, d.TEXT, True)
    d.text(c, '실패·진단 포함 사용량 추정 · 청구액·검증된 단가와 구분', 57, 596, 16, d.MUTED)
    d.text(c, '감사합니다', 1018, 588, 28, d.TEXT, True)
    note(c, s['takeaway'], 629, 17)
    d.text(c, '3D 개념 이미지', 1093, 546, 12, d.MUTED)


DRAW = {1: cover, 2: problem, 3: roles, 9: closing}


def build(name, deck, slides, source_dir, output_dir):
    source = source_dir / f'{name}.pdf'
    output = output_dir / f'{name}-3d.pdf'
    if source.resolve() == output.resolve():
        raise ValueError('Decorated output must not overwrite original')
    original = PdfReader(source)
    if len(original.pages) != len(slides):
        raise ValueError('PDF and storyboard page counts disagree')
    writer = PdfWriter()
    for page, old in enumerate(original.pages, 1):
        if page not in DRAW:
            writer.add_page(old)
            continue
        stream = io.BytesIO()
        c = canvas.Canvas(stream, pagesize=(d.W, d.H), pageCompression=1)
        DRAW[page](c, slides[page-1])
        footer(c, slides[page-1], page, deck)
        c.showPage()
        c.save()
        stream.seek(0)
        writer.add_page(PdfReader(stream).pages[0])
    writer.add_metadata({'/Title': f'EarlySignal | {deck} | 3D 디자인',
                         '/Author': 'FinVibe · Codex 협업',
                         '/Subject': '3D 개념 이미지. 기존 통계·제품 캡처·부록 보존. 분류 정확도와 현업 효과 미측정.'})
    writer.write(output)
    return {'file': output.name, 'pages': len(slides), 'changed_pages': list(CHANGED),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'original_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', type=Path, default=ROOT/'output'/'pdf')
    ap.add_argument('--output-dir', type=Path, default=ROOT/'output'/'pdf')
    ap.add_argument('--font-dir', type=Path, default=ROOT/'assets')
    args = ap.parse_args()
    pdfmetrics.registerFont(TTFont('KR', str(args.font_dir/'IBMPlexSansKR-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('KR-Bold', str(args.font_dir/'IBMPlexSansKR-SemiBold.ttf')))
    story = json.loads((ROOT/'storyboard.json').read_text(encoding='utf-8'))
    assert sum(s['time'] for s in story['preliminary']) == 240
    assert sum(s['time'] for s in story['finals']) == 480
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [build('EarlySignal-preliminary-4min', '4분 예선', story['preliminary'], args.source_dir, args.output_dir),
               build('EarlySignal-finals-8min-qa2min', '결선 8분 + Q&A 2분', story['finals'], args.source_dir, args.output_dir)]
    manifest = {'outputs': outputs, 'assets': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(ART.glob('*.png'))],
                'generated_art_tool': 'built-in image_gen', 'prompt_file': 'assets/3d/prompts.json',
                'main_pages': 9, 'preliminary_seconds': 240, 'finals_seconds': 480, 'qa_seconds': 120,
                'timing_is_allocation_not_rehearsal': True}
    (args.output_dir/'3d-build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
