#!/usr/bin/env python3
"""Build the review drafts. No measured product results are fabricated.

Run with Python + reportlab. Paths resolve relative to this file on any OS.
Fonts are redistributed under OFL (assets/OFL.txt).
"""
from pathlib import Path
from html import escape
import argparse
import json
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
META_PATH = REPO / 'web/public/data/meta.json'
CASE_PATH = REPO / 'web/public/data/cases.json'
MEASURED = json.loads(META_PATH.read_text()) if META_PATH.exists() else None
CASE_RESULTS = json.loads(CASE_PATH.read_text()) if CASE_PATH.exists() else None
PILOT_PATH = REPO / 'data/results/llm_pilot.json'
PILOT = json.loads(PILOT_PATH.read_text()) if PILOT_PATH.exists() else None
SCREENSHOT = ROOT / 'assets/screenshots/request-desktop.jpg'
W, H = 1280, 720
BG = '#0B1626'
PANEL = '#10233A'
LINE = '#274560'
TEXT = '#E6EEF7'
MUTED = '#9EB3C8'
CYAN = '#22D3EE'
AMBER = '#F5A524'
RED = '#FF7979'
GREEN = '#7ED9AD'


def slide(title, subtitle, kind='cards', **kw):
    return dict(title=title, subtitle=subtitle, kind=kind, **kw)


ROLES = [
    ('LLM', '측정', '신고 원문을 증상 라벨과\n상황 요약으로 정리합니다.', '원문 · 라벨 · 인용 연결', CYAN),
    ('STATISTICS', '판단', '차종별 증상 건수를\n자신의 과거 수준과 비교합니다.', '경보 규칙 · 기준선 공개', AMBER),
    ('HUMAN', '결정', '원문을 인용하거나 제외하고\n조사 착수·보류·기각을 정합니다.', '조사 요청서 · 결정 기록', GREEN),
]

PRELIM = [
    slide('신고를\n조사 요청서로.', '소비자 신고에서 조사해야 할 안전 신호를 더 일찍 찾는 도구', 'hero',
          kicker='EARLYSIGNAL  /  FINVIBE', tag='4분 예선 · 검토용 초안', time=15,
          bottom='LLM은 측정하고, 통계는 판단하고, 담당자는 결정합니다.', refs='E01 · E02'),
    slide('운전자의 신고를, 담당자의 다음 조치로.', '설명 상황 예: “주행 중 타는 냄새가 났어요.” → 자동차 회사에서 고객 안전을 살피는 담당자',
          cards=[('운전자의 신고', '타는 냄새, 연기, 과열처럼\n같은 현상도 서로 다르게\n표현됩니다.\n\n설명용 표현 예', '데이터 형식에서 출발', CYAN),
                 ('담당자의 검토', '어떤 차종에서 어떤 증상이\n평소보다 늘었는지 찾고\n실제 원문을 읽습니다.\n\n조사할 후보를 정리', '통계로 좁힐 문제', AMBER),
                 ('조사 요청', '“이 차종을 더 살펴봅시다.”\n\n조사할 이유, 근거 신고,\n아직 모르는 사항을\n문서로 남깁니다.', '제품으로 지원할 업무', GREEN)],
          takeaway='가치 가설: 고객 안전 담당자가 조사 후보와 근거를 정리하는 시간을 줄인다.', time=25, refs='E01 · E03 · E12', status='설명 상황 · 도입 가설'),
    slide('AI에게 맡기는 일의 경계를 정했습니다.', '신고 원문 → 증상 라벨 → 월간 집계 → 경보 → 담당자 결정', 'roles',
          takeaway='같은 차종의 평소 신고 수준과 비교합니다. 반복되는 증상을 확인하고 사람이 다음 조치를 정합니다.', time=25, refs='E02 · E04', status='채택한 설계'),
    slide('한 가지 업무를 끝까지 보여줍니다.', '실제 제품 캡처는 배포 후 교체합니다. 아래는 ADR-009의 시연 구성도입니다.', 'requestflow',
          takeaway='담당자가 원문을 제외하는 장면과 요청서 저장까지 시연합니다.', time=80, refs='E01 · E05 · E06', status='구현 · 캡처 대기'),
    slide('접수일 기준으로 과거를 재현합니다.', '이후 접수된 신고는 차단합니다. 당시 공개 파일의 수정 이력까지 복원한 것은 아닙니다.', 'boundary',
          takeaway='검증할 것: 기준일에서 잘라 재계산한 과거 경보가 전체 계산의 같은 구간과 일치하는가?', time=20, refs='E07 · E08', status='테스트 실행 대기'),
    slide('결과는 성공·실패·분모를 함께 공개합니다.', '사전 시제품 수치를 당일 구현의 성능으로 사용하지 않습니다.', 'results',
          takeaway='현재 상태: 당일 파이프라인 출력이 연결되기 전까지 결과 수치는 재현 대기입니다.', time=25, refs='E08 · E09', status='당일 재현 대기'),
    slide('다르게 읽었다고, 더 맞는 것은 아닙니다.', '단어 검색과 AI가 같은 증상으로 읽었는지, 사람이 검토한 정답에 맞는지는 따로 확인합니다.', 'compare',
          takeaway='발표 표현 수정: 방법 간 불일치를 키워드 오류로 단정하던 문장을 제거했습니다.', time=20, refs='E10 · E11', status='표현 수정 · 측정 대기'),
    slide('실제 업무에서 쓸 만한지 확인하겠습니다.', '첫 도입 후보: 자동차 회사의 고객 안전 담당자  |  구매 의사와 실제 사용 가치는 아직 가정', 'adoption',
          takeaway='검토 시간 · 월 경보량 · 요청서 활용률 · 신규 신고 처리 비용을 함께 측정합니다.', time=20, refs='E12 · E13', status='도입 가설'),
    slide('어떤 판단을 했는지 기록으로 남깁니다.', '사용자 선택과 Codex의 구현·독립 검수 결과를 코드·근거·결과로 연결합니다.', 'workflow',
          takeaway='다음: 실제 산출물로 숫자를 채우고, 직접 조작 또는 녹화로 요청서 저장을 보여줍니다.', time=10, refs='E14 · E15', status='기록 축적 중'),
]

FINALS = [
    slide('신고를\n조사 요청서로.', '조사 후보를 발견하고, 원문을 검토하고, 다음 조치를 문서로 남깁니다.', 'hero',
          kicker='EARLYSIGNAL  /  FINVIBE', tag='10분 결선 · 검토용 초안', time=20,
          bottom='제품의 끝은 근거가 연결된 조사 요청서입니다.', refs='E01 · E02'),
    PRELIM[1] | dict(time=35),
    slide('공개 신고를 읽을 때 지켜야 할 기준.', '데이터 정의가 바뀌면 경보의 의미도 달라집니다.',
          cards=[('소비자 신고', '차량에 대한 소비자 신고만\n포함하는 규칙을 적용합니다.\n\nPROD_TYPE = V\nCMPL_TYPE 허용 목록', '필터 결과 검산 대기', CYAN),
                 ('고유 신고', '부품별 중복 행을\n신고 건수로 세지 않습니다.\n\nODINO 고유값으로 집계\n브랜드 + 모델, 연식 통합', '적재 출력 검산 대기', AMBER),
                 ('접수 시점', '그날 접수된 신고까지만\n탐지 입력으로 사용합니다.\n\nLDATE 기준\n조사 결과 필드는 평가용', '미래 정보 차단', GREEN)],
          takeaway='원본 행 수 · 필터 후 고유 신고 수 · 날짜 파싱 실패를 적재 로그에 남깁니다.', time=35, refs='E03 · E07 · E16', status='데이터 적재 검증 대기'),
    slide('정리 작업에 AI를 쓰는 이유.', '증상 표현과 문맥을 정해진 분류로 바꾸고, 근거를 검토할 수 있게 합니다.',
          cards=[('비교 기준선', '키워드 분류도 같은 범위에\n실행해 비교합니다.\n\n일치율만으로 어느 쪽이\n맞는지 판단하지 않습니다.', '키워드 기준선 유지', CYAN),
                 ('LLM 측정', '정해진 라벨·위험 요소·\n한국어 요약을 출력합니다.\n\n출력 스키마와 캐시로\n결과를 추적합니다.', '모델 · 프롬프트 기록', AMBER),
                 ('검토 가능성', '라벨이나 요약을 믿기 전에\n연결된 신고 원문을 읽습니다.\n\n맞지 않는 신고는 제외하고\n판단을 기록합니다.', '사람 검수 기준 필요', GREEN)],
          takeaway='효과 검증은 라벨 정확도, 탐지 결과, 검토 시간으로 나누어 진행합니다.', time=30, refs='E02 · E10 · E11', status='효과 측정 대기'),
    PRELIM[2] | dict(time=35, takeaway='설계 규칙: 직전 12개월 평균 대비 Poisson p < 0.001, 월 3건 이상.'),
    slide('측정과 판단 사이에 재현 가능한 경로.', '화면의 숫자가 어느 입력과 규칙에서 나왔는지 추적하는 구조입니다.', 'architecture',
          takeaway='파이프라인 출력 → 데이터 계약 → 정적 웹. 화면 수치는 출력 파일에서 가져옵니다.', time=35, refs='E05 · E16 · E17', status='채택한 설계'),
    PRELIM[3] | dict(time=100),
    slide('요청서는 근거와 미확인 사항을 함께 담습니다.', '아래는 문서 구조입니다. 실제 수치·신고 번호·담당자 판단은 제품에서 채웁니다.', 'requestdoc',
          takeaway='LLM 문장은 상황 요약 한 칸에만 사용합니다. 그 인용은 해당 경보 근거 안에 있어야 합니다.', time=40, refs='E01 · E05 · E06', status='실제 요청서 산출 대기'),
    PRELIM[4] | dict(time=40),
    slide('규칙을 정한 데이터와 평가 데이터를 나눕니다.', '사례 선정 · 분할 · 대조군 · 선행 기간의 정의를 결과와 함께 남깁니다.', 'validation',
          takeaway='holdout을 본 뒤 규칙을 바꾸면 변경 사실과 이유를 공개하고 기존 평가와 구분합니다.', time=45, refs='E08 · E09', status='평가 실행 대기'),
    PRELIM[5] | dict(time=45),
    PRELIM[6] | dict(time=35),
    slide('실패와 알려진 약점도 검증의 일부입니다.', '아래 항목은 사전 조사에서 발견한 한계와 당일 확인할 질문입니다.',
          cards=[('놓친 · 늦은 사례', '사전 조사에서 놓치거나\n늦게 경보한 사례를\n결과표에서 지우지 않습니다.\n\n볼트 EV 등 재현 확인', '사례별 원문과 결과 연결', RED),
                 ('대조군의 품질', '신고량이 적은 대조군은\n비교가 쉬워질 수 있습니다.\n\n주 분석을 보존하고\n별도 민감도 분석 제안', '분모 · 조건 변경 공개', AMBER),
                 ('평가 단위 차이', '여러 차종이 묶인 사례와\n단일 차종 대조군은\n완전히 같은 단위가 아닙니다.\n\n단일 차종 분석 제안', '사전 정의 후 확인', CYAN)],
          takeaway='이 초안의 변경은 주장과 근거의 연결입니다. 탐지 규칙 변경은 별도 ADR과 검증을 거칩니다.', time=30, refs='E09 · E18', status='재현 · 개선 검증 대기'),
    slide('Codex 지시도 결과 검수까지 연결합니다.', '작업 난이도에 맞게 구현과 검수를 배정하고, 총괄이 수정 결과를 통합합니다.', 'workflow',
          takeaway='ADR의 선택 이유 + 세션의 실행 결과 + 검수 지적 + 수정 커밋을 한 묶음으로 제시합니다.', time=35, refs='E14 · E15', status='실제 작업 기록 축적 중'),
    PRELIM[7] | dict(time=30),
    slide('확인한 것과 다음 질문을 구분합니다.', '시제품 설계가 당일 제품과 현업 가치로 이어지는지 단계별로 확인합니다.',
          cards=[('문서로 확인', '역할 분담 · 시간 기준\n요청서 구조 · 데이터 계약\n\n설계가 문서에 명시되어\n있는 것은 확인했습니다.', '구현 성능과 별개', CYAN),
                 ('당일 확인 대기', '파이프라인 재현 결과\n미래 정보 차단 테스트\n요청서 저장과 인용 검사\n모델 비용과 검수 정확도', '실행 근거로 교체', AMBER),
                 ('현장 검증 다음', '품질팀 검토 업무 적합성\n요청서 검토 시간과 활용\n보증·생산 이력 연동\n지속 사용 · 구매 의사', '파일럿에서 확인', GREEN)],
          takeaway='EarlySignal의 첫 목표: 담당자가 조사할 이유를 근거와 함께 남길 수 있도록 돕는 것.', time=10, refs='E01 · E12 · E13', status='검토용 초안'),
]


def color(c):
    return HexColor(c)


def text(c, s, x, y, size=24, fill=TEXT, bold=False):
    c.setFillColor(color(fill))
    c.setFont('KR-Bold' if bold else 'KR', size)
    c.drawString(x, H - y - size * .80, s)


def wrapped_lines(s, width, size, bold=False):
    font = 'KR-Bold' if bold else 'KR'
    result = []
    for paragraph in s.split('\n'):
        if not paragraph:
            result.append('')
            continue
        current = ''
        for char in paragraph:
            if current and pdfmetrics.stringWidth(current + char, font, size) > width:
                result.append(current.rstrip())
                current = char.lstrip()
            else:
                current += char
        result.append(current.rstrip())
    return result


def block(c, s, x, y, width, size=24, fill=TEXT, bold=False, leading=None, max_height=None):
    leading = leading or size * 1.42
    lines = wrapped_lines(s, width, size, bold)
    h = len(lines) * leading
    if max_height is not None and h > max_height:
        raise ValueError(f'Text exceeds box ({h:.1f}>{max_height}): {s}')
    for i, line in enumerate(lines):
        text(c, line, x, y + i * leading, size, fill, bold)
    return h


def box(c, x, y, w, h, fill=PANEL, stroke=LINE, radius=16):
    c.setFillColor(color(fill))
    c.setStrokeColor(color(stroke))
    c.setLineWidth(1)
    c.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=1)


def line(c, x1, y1, x2, y2, fill=LINE, width=2):
    c.setStrokeColor(color(fill))
    c.setLineWidth(width)
    c.line(x1, H-y1, x2, H-y2)


def arrow(c, x1, y, x2, fill=CYAN):
    line(c, x1, y, x2-10, y, fill, 3)
    p = c.beginPath()
    p.moveTo(x2, H-y)
    p.lineTo(x2-12, H-y+7)
    p.lineTo(x2-12, H-y-7)
    p.close()
    c.setFillColor(color(fill))
    c.drawPath(p, fill=1, stroke=0)


def pill(c, s, x, y, fill=AMBER, size=14):
    w = pdfmetrics.stringWidth(s, 'KR-Bold', size) + 24
    box(c, x, y, w, 30, fill=fill, stroke=fill, radius=15)
    text(c, s, x+12, y+8, size, BG, True)
    return w


def frame(c, s, index, total, deck):
    c.setFillColor(color(BG))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, 'EARLYSIGNAL', 52, 28, 18, CYAN, True)
    text(c, f'{deck}  |  검토본 · 2026.10.09', 730, 31, 15, MUTED)
    if s['kind'] != 'hero':
        block(c, s['title'], 52, 85, 1180, 40, bold=True, leading=49, max_height=98)
        block(c, s['subtitle'], 54, 156, 1140, 21, MUTED, leading=29, max_height=60)
        pill(c, s.get('status', '검토용 초안'), 54, 224)
    line(c, 52, 661, 1228, 661)
    text(c, 'DRAFT · 키워드 제품 실측 · AI 검증 진행 중' if MEASURED else 'DRAFT · 결과 수치 및 제품 캡처 재현 대기', 54, 681, 14, MUTED)
    text(c, f'근거 {s["refs"]}', 640, 681, 14, MUTED)
    text(c, f'부록 {index-12}' if s.get('appendix') else f'{index:02d} / {12 if deck.startswith("결선") else total:02d}', 1140, 678, 17, TEXT, True)


def takeaway(c, s):
    box(c, 52, 587, 1176, 56, '#122B3D', '#285266', 12)
    block(c, s, 72, 600, 1136, 20, TEXT, leading=25, max_height=50)


def cards(c, s):
    y, w, h, gap = 278, 376, 280, 24
    for i, (title, body, label, accent) in enumerate(s['cards']):
        x = 52 + i*(w+gap)
        box(c, x, y, w, h)
        line(c, x+24, y+25, x+78, y+25, accent, 4)
        text(c, title, x+24, y+42, 29, TEXT, True)
        block(c, body, x+24, y+95, w-48, 23, leading=30, max_height=180)
        # The label is carried in notes rather than adding a second dense footer.
    takeaway(c, s['takeaway'])


def roles(c, s):
    for i, (kicker, title, body, label, accent) in enumerate(ROLES):
        x = 52 + i*400
        box(c, x, 278, 376, 280)
        text(c, kicker, x+26, 301, 18, accent, True)
        text(c, title, x+26, 346, 45, TEXT, True)
        block(c, body, x+26, 417, 324, 24, leading=33, max_height=100)
        text(c, label, x+26, 522, 17, MUTED)
    takeaway(c, s['takeaway'])


def hero(c, s):
    pill(c, s['tag'], 54, 91, CYAN, 16)
    text(c, s['kicker'], 56, 158, 22, MUTED, True)
    block(c, s['title'], 52, 218, 810, 72, bold=True, leading=90)
    block(c, s['subtitle'], 56, 440, 790, 25, MUTED, leading=36)
    box(c, 939, 222, 265, 292, '#123149', '#285266', 20)
    text(c, '조사 요청서', 967, 255, 29, TEXT, True)
    for i, label in enumerate(['대상 · 기준일', '증가와 경보 근거', '인용한 신고', '미확인 사항', '담당자 판단']):
        line(c, 966, 316+i*34, 1178, 316+i*34)
        text(c, label, 969, 325+i*34, 17, MUTED)
    block(c, s['bottom'], 56, 589, 1160, 23, CYAN, bold=True, max_height=50)


def requestflow(c, s):
    labels = [('01', '경보 선택', '증상 증가와\n기준선을 확인'),
              ('02', '근거 검토', '원문을 읽고\n인용 · 제외'),
              ('03', '요청서 작성', '반복 상황과\n미확인 사항 정리'),
              ('04', '확정 · 저장', '담당자 판단과\n다음 조치를 남김')]
    for i,(n,title,body) in enumerate(labels):
        x = 52+i*300
        box(c, x, 282, 276, 229)
        text(c, n, x+22, 303, 19, CYAN, True)
        text(c, title, x+22, 345, 28, TEXT, True)
        block(c, body, x+22, 401, 232, 22, MUTED, leading=31)
        if i < 3:
            arrow(c, x+280, 391, x+295)
    text(c, '시연 포인트', 56, 538, 18, CYAN, True)
    text(c, '증상별로 묶인 신고를 담당자가 검토하고, 저장된 문서를 실제로 엽니다.', 211, 536, 22, TEXT)
    takeaway(c, s['takeaway'])


def boundary(c, s):
    box(c, 52, 285, 722, 166)
    box(c, 802, 285, 426, 166, '#25243A', '#524856')
    text(c, '탐지에 사용', 80, 309, 21, CYAN, True)
    block(c, '기준일까지 접수된 신고\n원문 · 증상 라벨 · 과거 건수', 80, 355, 670, 28, leading=41)
    text(c, '평가에서만 확인', 830, 309, 21, AMBER, True)
    block(c, '이후 실제 신고\n공식 조사 개시와 결과', 830, 355, 370, 26, leading=41)
    line(c, 80, 505, 1197, 505, MUTED, 3)
    for x in [120,280,440,600]:
        line(c,x,498,x,512,CYAN,3)
    line(c, 773, 274, 773, 547, AMBER, 3)
    text(c, '과거', 81, 526, 20, MUTED)
    text(c, '분석 기준일', 679, 526, 20, AMBER, True)
    text(c, '사후 확인', 1041, 526, 20, MUTED)
    takeaway(c, s['takeaway'])


def results(c, s):
    if MEASURED and CASE_RESULTS:
        values=MEASURED['validation']
        for i,(split,label) in enumerate([('dev','개발용'),('holdout','검증용')]):
            y=281+i*91
            box(c,52,y,1176,77)
            text(c,label,76,y+23,25,CYAN,True)
            a,b=values[split]['case'],values[split]['control']
            text(c,f"조사 사례 {a['hits']}/{a['n']}",330,y+23,27,TEXT,True)
            text(c,f"비교 차종 {b['hits']}/{b['n']}",720,y+23,27,AMBER,True)
        box(c,52,463,1176,77)
        text(c,'대표 · 실패',76,486,25,CYAN,True)
        cases={case['case_id']:case for case in CASE_RESULTS['cases']}
        text(c,f"현대 {cases['PE19003']['lead_days']}일 · 기아 {cases['PE19004']['lead_days']}일",330,486,25,TEXT,True)
        text(c,'볼트 EV 놓침',860,486,25,AMBER,True)
        text(c,'키워드 기준선 · 일수는 공식 조사 개시보다 선행 · 현재 파일의 접수일 기준 재현',56,555,20,MUTED)
        takeaway(c,'선정된 사례의 경보 발생 비율입니다. 일반 정확도·오탐률이나 실제 사고 예방 효과가 아닙니다.')
        return
    rows = [('개발용', '조사 사례 / 비교 차종', '규칙 선택에 사용'),
            ('검증용', '조사 사례 / 비교 차종', '규칙 고정 후 평가'),
            ('대표 · 실패', '선행 / 늦음 / 놓침', '사례별 근거 연결')]
    for i,(k,v,note) in enumerate(rows):
        y=281+i*91
        box(c,52,y,1176,77)
        text(c,k,76,y+23,25,CYAN,True)
        text(c,v,330,y+26,22,TEXT)
        text(c,'당일 재현 대기',680,y+22,26,AMBER,True)
        text(c,note,991,y+28,17,MUTED)
    text(c,'결과를 채울 파일',56,556,16,MUTED,True)
    text(c,'meta.json · cases.json · 세션 실행 로그',226,554,20,TEXT)
    takeaway(c,s['takeaway'])


def compare(c,s):
    box(c,52,282,571,273)
    box(c,651,282,577,273)
    text(c,'단어 검색과 AI 비교',80,307,21,CYAN,True)
    text(c,'같은 증상으로 읽었나?',80,355,33,TEXT,True)
    block(c,'동일한 신고의 대표 증상 비교\n둘의 답이 같았던 비율\n\n다른 답은 사람이 검토할 후보입니다.',80,412,515,23,leading=31)
    text(c,'사람이 검토한 정답과 비교',679,307,21,AMBER,True)
    text(c,'맞는 증상으로 읽었나?',679,355,33,TEXT,True)
    block(c,'사람이 원문을 읽고 정답 확인\n단어 검색·AI 각각의 정확도\n\n사람의 검토 없이 단정하지 않습니다.',679,412,520,23,leading=31)
    takeaway(c,s['takeaway'])


def adoption(c,s):
    cols=[('누가 쓰나','자동차 회사의 고객 안전 담당자\n원문 검토와 조사 요청서 작성\n\n구매 의사 · 가격은 미확인',CYAN),
          ('어떤 가치가 있나','검토 전후에 걸린 시간 비교\n월 경보 수와 제외 이유 기록\n\n감당할 수 있는 업무량 확인',AMBER),
          ('어떻게 운영하나','새 신고만 AI가 읽고 결과 저장\n처리 비용과 재시도 비용 기록\n\n수리 기록 · 생산 기록은 다음',GREEN)]
    s=s|dict(cards=[(title,body,'',accent) for title,body,accent in cols])
    cards(c,s)


def workflow(c,s):
    labels=[('총괄 계획','Step · 완료 기준\nADR · 데이터 계약'),
            ('구현 배정','난이도와 범위에\n맞는 에이전트'),
            ('독립 검수','근거 · 테스트\n실패 · 주장 검토'),
            ('수정 · 통합','검수 지적 반영\n세션 · 커밋 연결')]
    for i,(title,body) in enumerate(labels):
        x=52+i*300
        box(c,x,282,276,215)
        text(c,title,x+22,309,28,TEXT,True)
        block(c,body,x+22,370,232,22,MUTED,leading=33)
        if i<3: arrow(c,x+279,390,x+295)
    text(c,'검수 기록에 남길 것',56,529,18,CYAN,True)
    text(c,'작업 지시 → 실제 결과 → 지적 사항 → 수정 → 재검증 → 통합',266,527,22,TEXT)
    takeaway(c,s['takeaway'])


def architecture(c,s):
    items=[('접수 신고','LDATE · ODINO'),('라벨링','키워드 / LLM'),('집계 · 탐지','월별 · Poisson'),('JSON 출력','계약 · 근거'),('정적 웹','검토 · 요청서')]
    for i,(title,sub) in enumerate(items):
        x=52+i*239
        box(c,x,316,219,146)
        text(c,title,x+18,345,25,TEXT,True)
        text(c,sub,x+18,407,17,MUTED)
        if i<4: arrow(c,x+222,389,x+235)
    text(c,'입력과 출력의 경계',56,513,19,CYAN,True)
    block(c,'탐지 코드는 조사 결과를 읽지 않습니다.\n웹은 export 값과 사용자의 검토·판단으로 문서를 만듭니다.',300,502,906,22,leading=32)
    takeaway(c,s['takeaway'])


def requestdoc(c,s):
    box(c,52,278,725,280)
    text(c,'조사 요청서 · 문서 구조',80,300,22,CYAN,True)
    rows=['대상 · 기준일','증가와 경보 근거','상황 요약 · 인용 신고','미확인 사항 · 내부 확인 항목','담당자 판단 · 다음 조치']
    for i,label in enumerate(rows):
        y=347+i*39
        line(c,80,y-5,750,y-5)
        text(c,label,81,y,22,TEXT)
    box(c,803,278,425,280)
    text(c,'문서의 신뢰 조건',831,302,25,TEXT,True)
    block(c,'수치 → 파이프라인 값\n인용 → 해당 근거 신고\n제외 → 인용 목록에서 제거\n판단 → 담당자 입력',831,359,365,23,leading=40)
    takeaway(c,s['takeaway'])


def validation(c,s):
    cards(c,s|dict(cards=[
        ('선정 · 분할','선정 기준에 맞는 사례\n사전 목록을 사용합니다.\n\n개발용 dev\n규칙 고정 후 holdout','',CYAN),
        ('동일 규칙 비교','같은 제조사의 대조군과\n동일한 경보 규칙을 적용.\n\n사례 수 · 차종 수 · 관측월\n분모를 함께 공개합니다.','',AMBER),
        ('선행 정의','공식 조사 전후 정해진\n기간 안 첫 경보를 평가.\n\n확인 가능일은\n경보 월 다음 달 첫날.','',GREEN),
    ]))


RENDERERS={'hero':hero,'cards':cards,'roles':roles,'requestflow':requestflow,
           'boundary':boundary,'results':results,'compare':compare,'adoption':adoption,
           'workflow':workflow,'architecture':architecture,'requestdoc':requestdoc,
           'validation':validation}


def build(deck, slides, output):
    c=canvas.Canvas(str(output),pagesize=(W,H),pageCompression=1)
    c.setTitle(f'EarlySignal | {deck} | 검토용 초안')
    c.setAuthor('FinVibe · Codex 협업')
    c.setSubject('키워드 기준선 실측과 실제 요청서 저장 화면. AI 검증은 진행 중.')
    for i,s in enumerate(slides,1):
        frame(c,s,i,len(slides),deck)
        RENDERERS[s['kind']](c,s)
        c.showPage()
    c.save()


def screenshot_region(c, path, source_box, target_box):
    """Place an unmodified real screenshot through a PDF clipping viewport."""
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    sx, sy, sw, sh = source_box
    tx, ty, tw, th = target_box
    scale = min(tw / sw, th / sh)
    dx, dy = tx + (tw-sw*scale)/2, ty + (th-sh*scale)/2
    c.saveState()
    clip = c.beginPath()
    clip.rect(dx, H-dy-sh*scale, sw*scale, sh*scale)
    c.clipPath(clip, stroke=0)
    c.drawImage(image, dx-sx*scale, H-(dy+(ih-sy)*scale), width=iw*scale, height=ih*scale)
    c.restoreState()


def product(c, s):
    box(c, 52, 278, 810, 280)
    screenshot_region(c, SCREENSHOT, (108, 390, 1295, 450), (60, 286, 794, 264))
    box(c, 886, 278, 342, 280)
    text(c, '실제 저장된 요청서', 909, 300, 24, CYAN, True)
    block(c, '원문 인용·제외 → 판단 입력\n요청서와 결정 기록 저장', 909, 346, 296, 21, leading=31)
    screenshot_region(c, SCREENSHOT, (905, 1085, 500, 201), (902, 414, 310, 125))
    takeaway(c, s['takeaway'])


def prepare_slides():
    """Tie current evidence to both decks without changing evaluation outputs."""
    if MEASURED:
        lookahead=json.loads((REPO/'data/results/lookahead_kw.json').read_text())
        for s in PRELIM+FINALS:
            if s['kind']=='results':
                s.update(subtitle='실행한 키워드 기준선의 결과입니다. 실패와 비교 집단의 한계를 함께 봅니다.', status='실데이터 · 독립 검수 완료',takeaway='선정된 사례의 경보 발생 비율입니다. 일반 정확도·오탐률이나 실제 사고 예방 효과가 아닙니다.')
            elif s['kind']=='boundary':
                s.update(status='미래 접수 차단 확인',takeaway=f"{lookahead['complete_month_cutoffs']}개 조사 사례의 기준일에서 잘라 재계산한 완료월 경보가 전체 계산과 일치했습니다.")
            elif s['kind']=='validation':
                s.update(status='등록된 평가 완료',takeaway='사례·대조군의 규모 차이와 분할 간 차종 중복이 있습니다. 일반화 성능은 추가 검증이 필요합니다.')
            elif s['kind']=='compare':
                completed = PILOT.get('completed', 0) if PILOT else 0
                selected = PILOT.get('selected', 50) if PILOT else 50
                s.update(status='AI 시험 일부 완료 · 사람 검수 대기',takeaway=f'고정 시험 {selected}건 중 {completed}건 성공. 요청 한도로 시험 미완료이며, 사람 정답 기반 정확도는 미측정입니다.')
            elif s['kind']=='workflow':
                s.update(status='독립 검수·수정 기록 확인',takeaway='검수 지적 → 수정: 요청서 문서번호 충돌 · 잘못된 인용 · 제외한 신고의 AI 재인용 차단.')
            elif s['kind']=='roles':
                s.update(status='역할 분리 설계 · 현재 화면은 키워드 기준선')
            elif s['kind']=='requestflow' and SCREENSHOT.exists():
                s.update(kind='product', subtitle='로컬 정적 제품에서 직접 저장한 실제 화면입니다. 분류 출처는 키워드 기준선입니다.', status='실제 브라우저 저장 확인', takeaway='경보 선택 → 원문 인용·제외 → 담당자 판단 → 요청서 저장. 내려받은 문서까지 확인합니다.')
            elif s['kind']=='requestdoc':
                s.update(subtitle='실제 저장 문서는 수치·원문 인용·미확인 사항·담당자 판단을 함께 남깁니다.', status='실제 요청서 저장 확인', takeaway='현재 상황 요약은 비워 둡니다. 검증된 AI 요약이 없을 때 문장을 만들어 채우지 않습니다.')
        FINALS[2].update(status='실데이터 적재 검산 완료',takeaway='원본 1,301,663행 → 소비자 고유 신고 932,821건. 원본 스트리밍 집계와 DB 결과를 독립 대조했습니다.')
        FINALS[2]['cards'][0]=('소비자 신고','차량에 대한 소비자 신고만\n포함하는 규칙을 적용합니다.\n\n차량 제품으로 한정\n허용 신고 유형을 고정','필터 결과 검산 완료',CYAN)
        FINALS[2]['cards'][1]=('고유 신고','부품별 중복 행을\n신고 건수로 세지 않습니다.\n\n고유 신고 번호로 집계\n브랜드 + 모델, 연식 통합','적재 출력 검산 완료',AMBER)
        FINALS[12].update(status='실패·민감도 분석 확인',subtitle='볼트 EV 놓침을 공개하고, 단일 차종 비교를 주 분석과 분리했습니다.',takeaway='단일 차종 보조 분석: 사례 8/20 · 대조 1/19. 주 분석을 덮어쓰거나 규칙을 다시 맞추지 않았습니다.')
        FINALS[12]['cards']=[('놓친 사례','볼트 EV는 현재 키워드\n기준선에서 놓쳤습니다.\n\n사전 시제품의 늦은 경보와\n다른 결과도 그대로 공개.','실패 공개',RED),('대조군의 품질','신고량이 적은 대조군은\n비교가 쉬워질 수 있습니다.\n\n주 분석을 보존하고\n차종 단위 결과를 별도 확인.','분모와 조건 공개',AMBER),('평가의 한계','여러 차종을 묶은 사례와\n단일 대조의 단위가 다릅니다.\n\n개발·검증 분할 사이에\n겹치는 차종도 있습니다.','새 차종 일반화 미검증',CYAN)]
        FINALS[-1]['cards']=[('직접 확인','공개 신고 적재·키워드 경보\n등록 사례와 대조군 평가\n미래 접수 차단 재계산\n원문 검토와 요청서 저장','산출물과 테스트 연결',CYAN),('아직 미확인','AI 라벨 정확도·전체 비용\n사람 검수 정답\n현업 검토 시간 감소\n당시 공개 파일 수정 이력','실행·사용자 검증 필요',AMBER),('다음 현장 검증','고객 안전 담당자 파일럿\n검토 시간과 요청서 활용\n수리·생산 기록 연결\n구매 의사와 지속 사용','도입 가설 검증',GREEN)]
        FINALS[-1].update(subtitle='확인한 결과, 미검증 가정, 다음 검증을 구분합니다. 여기서 발표를 마치고 질의응답을 진행합니다.',takeaway='8분 발표·데모 종료 → 2분 질의응답. 자세한 데이터·평가·실패 자료는 부록에 준비했습니다.',status='본문 마지막 · 질의응답 2분')
    # Twelve presentation pages total exactly eight minutes; four appendices are opened only for questions.
    order=[0,1,4,3,6,7,8,10,11,13,14,15]
    times=[20,30,35,30,100,35,35,45,30,40,45,35]
    main=[FINALS[i] | dict(time=t) for i,t in zip(order,times)]
    main[0]['tag']='결선 · 8분 발표 + 2분 질의응답'
    appendices=[]
    for n,i in enumerate([2,5,9,12],1):
        item=FINALS[i] | dict(time=0,appendix=True)
        item['title']=f'부록 {n}. '+item['title']
        appendices.append(item)
    return PRELIM, main+appendices


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',type=Path,default=ROOT/'output'/'pdf')
    ap.add_argument('--font-dir',type=Path,default=ROOT/'assets')
    args=ap.parse_args()
    pdfmetrics.registerFont(TTFont('KR',str(args.font_dir/'IBMPlexSansKR-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('KR-Bold',str(args.font_dir/'IBMPlexSansKR-SemiBold.ttf')))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    prelim,finals=prepare_slides()
    RENDERERS['product']=product
    assert sum(s['time'] for s in prelim)==240
    assert sum(s['time'] for s in finals)==480
    assert sum(not s.get('appendix', False) for s in finals)==12
    build('4분 예선',prelim,args.output_dir/'EarlySignal-preliminary-4min-DRAFT.pdf')
    build('결선 8분 + Q&A 2분',finals,args.output_dir/'EarlySignal-finals-10min-DRAFT.pdf')
    source={'draft':True,'measured_product_results_included':bool(MEASURED),'product_capture':str(SCREENSHOT.relative_to(ROOT)) if SCREENSHOT.exists() else None,'finals_presentation_seconds':480,'finals_qa_seconds':120,'appendix_seconds':0,'preliminary':prelim,'finals':finals}
    (ROOT/'storyboard.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built 9-slide / 240-second preliminary and 12-slide / 480-second finals + 120-second Q&A + 4 appendices.')


if __name__=='__main__':
    main()
