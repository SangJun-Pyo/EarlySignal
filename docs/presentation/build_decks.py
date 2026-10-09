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
PILOT_TOTAL = PILOT.get('cohort_size', PILOT.get('requested_limit', 50)) if PILOT else 50
PILOT_DONE = PILOT.get('cohort_completed', PILOT.get('completed', 0)) if PILOT else 0
SCREENSHOT = ROOT / 'assets/screenshots/request-public.jpg'
FIGURES = ROOT / 'figures'
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
    text(c, f'부록 {index-12}' if s.get('appendix') else f'{index:02d} / 12', 1140, 678, 17, TEXT, True)


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
    screenshot_region(c, SCREENSHOT, (110, 390, 1120, 470), (60, 286, 794, 264))
    box(c, 886, 278, 342, 280)
    text(c, '실제 저장된 요청서', 909, 300, 24, CYAN, True)
    block(c, '원문 인용·제외 → 판단 입력\n요청서와 결정 기록 저장', 909, 346, 296, 21, leading=31)
    screenshot_region(c, SCREENSHOT, (800, 1080, 430, 207), (902, 414, 310, 125))
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
                completed = PILOT_DONE
                selected = PILOT_TOTAL
                s.update(status='AI 시험 일부 완료 · 사람 검수 대기',takeaway=f'고정 시험 {selected}건 중 {completed}건 성공. 요청 한도로 시험 미완료이며, 사람 정답 기반 정확도는 미측정입니다.')
            elif s['kind']=='workflow':
                s.update(status='독립 검수·수정 기록 확인',takeaway='검수 지적 → 수정: 요청서 문서번호 충돌 · 잘못된 인용 · 제외한 신고의 AI 재인용 차단.')
            elif s['kind']=='roles':
                s.update(status='역할 분리 설계 · 현재 화면은 키워드 기준선')
            elif s['kind']=='requestflow' and SCREENSHOT.exists():
                s.update(kind='product', subtitle='공개 배포에서 직접 저장·다운로드한 실제 화면입니다. earlysignal.pages.dev · 키워드 기준선', status='실제 브라우저 저장 확인', takeaway='경보 선택 → 원문 인용·제외 → 담당자 판단 → 요청서 저장. 내려받은 문서까지 확인합니다.')
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


def figure_panel(c, s):
    path = FIGURES / s['figure']
    if not path.exists():
        raise FileNotFoundError(path)
    c.drawImage(ImageReader(str(path)), 52, H-282-284, width=820, height=284, preserveAspectRatio=True, anchor='c', mask='auto')
    box(c, 892, 278, 336, 286)
    for i, (label, value, note) in enumerate(s['metrics']):
        y = 295 + i*85
        text(c, label, 910, y, 17, MUTED)
        text(c, value, 910, y+25, 28, CYAN if i == 0 else TEXT, True)
        text(c, note, 910, y+61, 16, MUTED)
    takeaway(c, s['takeaway'])


def llm_flow(c, s):
    steps = [
        ('신고 원문', '식별정보 정제\n최대 1,500자 입력', CYAN),
        ('LLM 분류', '정해진 증상·위험 요소\n근거 인용·한국어 요약', AMBER),
        ('출력 검사', '스키마·인용·식별정보 검사\n실패 시 원문 구간 재선택', GREEN),
        ('집계에 연결', '캐시 완성 후 적용\n같은 범위의 키워드와 비교', CYAN),
    ]
    for i, (title, body, accent) in enumerate(steps):
        x = 52 + i*300
        box(c, x, 280, 276, 156)
        text(c, title, x+20, 303, 26, accent, True)
        block(c, body, x+20, 356, 238, 21, leading=30)
        if i < 3: arrow(c, x+280, 354, x+296)
    box(c, 52, 459, 1176, 100)
    text(c, 'API 출력 검사', 73, 480, 21, AMBER, True)
    completed = PILOT_DONE
    selected = PILOT_TOTAL
    text(c, f'고정 {selected}건 중 {completed}건 통과', 260, 479, 27, TEXT, True)
    text(c, '분류 정확도를 뜻하지 않음', 803, 483, 21, AMBER)
    text(c, '38개 조사 사례의 통계 백테스트와 별개입니다. 사람 정답 기반 분류 정확도는 미측정입니다.', 74, 522, 20, MUTED)
    takeaway(c, s['takeaway'])


def validation_graph(c, s):
    # Counts originate in the current pipeline export, not illustrative chart data.
    vals = MEASURED['validation']
    x0, scale = 233, 34
    rows = [('dev','개발용 사례','case',CYAN), ('dev','개발용 대조','control',MUTED),
            ('holdout','검증용 사례','case',CYAN), ('holdout','검증용 대조','control',AMBER)]
    for i, (split, title, group, accent) in enumerate(rows):
        y = 292 + i*65
        value = vals[split][group]
        text(c, title, 61, y+7, 21, TEXT, True)
        box(c,x0,y,19*scale,35,fill='#152A3D',stroke='#152A3D',radius=4)
        if value['hits']:
            box(c,x0,y,value['hits']*scale,35,fill=accent,stroke=accent,radius=4)
        text(c,f"{value['hits']} / {value['n']}",x0+19*scale+15,y+6,24,accent,True)
    text(c,'정해진 조사 전 기간에 표적 증상 경보가 있었던 사례 수',60,563,18,MUTED)
    box(c,997,279,231,278)
    text(c,'검증의 순서',1016,301,22,CYAN,True)
    block(c,'개발 사례로\n규칙 선택\n↓\n규칙 고정\n↓\n검증·대조 평가',1016,350,190,20,leading=30)
    takeaway(c,s['takeaway'])


def technical_stats(c, s):
    cards(c,s | dict(cards=[
        ('월별 기준선','n = 그달 고유 신고 수\n평균 = 직전 12개월 평균\n\n당월 제외 · 0건 월 포함\n이력 6개월 이상부터 판단\n평균의 하한은 0.5','',CYAN),
        ('포아송 상위 꼬리','p = P(X ≥ n | 평균)\n계산: poisson.sf(n-1, 평균)\n\np < 0.001 이고 n ≥ 3\n두 조건 모두 만족하면 경보\n배수는 설명용 지표','',AMBER),
        ('검증하지 않은 가정','건수 독립·일정한 발생률\n평균과 분산이 같은 모형\n\n과산포·계절성·보도 영향\n판매·운행 노출 미반영\n다중 검정 보정 미적용','',GREEN),
    ]))


def comparison_stats(c,s):
    source=json.loads((FIGURES/'source.json').read_text())
    alt=source['example']['comparison_binomial']
    cards(c,s | dict(cards=[
        ('이항 비교 계산',f"전체 신고 중 증상 비율 비교\n과거 {alt['historical_category_sum']}/{alt['historical_total_sum']} → 이번 달 17/108\n\np = {alt['p_value']:.4f}\n코드에서 비교용으로 계산\n주 경보·평가에는 미사용",'',CYAN),
        ('검토 업무량 관측',f"차종·월당 경보 수\n사례 {MEASURED['burden']['case_alerts_per_group_month']:.3f} · 대조 {MEASURED['burden']['control_alerts_per_group_month']:.3f}\n\n등록 평가창의 관측치\n증상별 경보를 합산한 값\n현업 검토 시간은 미측정",'',AMBER),
        ('단일 차종 보조 분석','같은 단위로 좁혀 비교\n사례 8/20 · 대조 1/19\n\n기존 주 분석 결과는 보존\n결과를 보고 규칙 미조정\n차종 중복 등 한계는 유지','',GREEN),
    ]))


def hypotheses_design(c,s):
    steps=[('원문에 명시된 내용','원문에 명시된 증상·상황\n신고 ID와 근거 연결',CYAN),
           ('조사 질문·가설','근거와 추론을 구분\n다른 가능한 설명도 기록',AMBER),
           ('추가 확인 자료','정비 진단·고장 코드·검사\n작업·부품·생산 이력',AMBER),
           ('담당자 확인','지지·반박·보류를 기록\n확인 결과와 출처 보존',GREEN)]
    for i,(title,body,accent) in enumerate(steps):
        x=52+i*300
        box(c,x,290,276,193)
        text(c,title,x+18,316,25,accent,True)
        block(c,body,x+18,370,240,21,leading=31)
        text(c,'현재 근거' if i==0 else '후속 설계 · 미구현',x+18,452,17,MUTED)
        if i<3:arrow(c,x+280,386,x+296,AMBER)
    text(c,'자료 요구사항',57,512,20,CYAN,True)
    text(c,'위 정비·검사·생산 자료는 아직 연결하지 않았습니다. 실제 사례의 원인 가설을 생성한 결과도 없습니다.',234,512,19,TEXT)
    text(c,'근거가 부족하면 가설을 보류합니다. 유사한 증상만으로 같은 원인을 부여하거나 확률을 붙이지 않습니다.',57,551,20,MUTED)
    takeaway(c,s['takeaway'])


def proposal_scope(c,s):
    columns=[(52,194,'제출 기획'),(258,342,'현재 구현'),(612,290,'차이·이유'),(914,314,'다음 검증')]
    for x,w,title in columns:
        box(c,x,278,w,46,fill='#18314A')
        text(c,title,x+13,292,22,CYAN,True)
    rows=[
        ('신호 추출','고정 16개 증상 코드로 분류\n위험 요소·인용 출력 검사','별도 부품 추출 미구현\n자유 군집화·벡터 검색 없음','같은 표본의 사람 정답 대조\n검수 예시는 평가와 분리'),
        ('변화 탐지','월별 집계·포아송 경보\n현재 제품은 키워드 기준선','LLM 50건 출력 검사 완료\nAI 연결 전 임시 기준선','전체 라벨·요약 실행 후\n출력·근거·사람 정답 검증'),
        ('신호 브리프','원문·추세·인용·제외 제공\n담당자 판단을 요청서로 저장','AI 상황 요약 실사용 전\n유사 과거 사례 검색 미구현','원래 기획의 검색 기능 보완\n근거·인용·시점 검증'),
        ('과거 재현','접수일 기준으로 잘라 계산\n공식 조사 대비 선행일 측정','당시 공개 파일 수정 이력은\n복원하지 못한 한계','공개 가능 시점·자료 변경\n민감도 분석 필요'),
    ]
    for r,values in enumerate(rows):
        y=333+r*57
        for (x,w,_),value in zip(columns,values):
            block(c,value,x+11,y,w-18,18,leading=24,max_height=50)
        line(c,52,y+51,1228,y+51,LINE,1)
    takeaway(c,s['takeaway'])


def rag_scope(c, s):
    box(c,52,278,1176,82)
    text(c,'현재 구현',73,295,19,CYAN,True)
    text(c,'신고 한 건 → 정제 → 직접 LLM 분류 → 출력 검사 → 집계',260,306,25,TEXT,True)
    text(c,'벡터 검색 없음',74,328,17,MUTED)
    items=[('자료 정제·임베딩','유사 과거 신고·수리 자료'),('pgvector 검색','기준일·권한 필터'),('RAG 근거 요약','출처 ID·인용 연결'),('담당자 원문 대조','채택·제외·요청서 근거')]
    for i,(title,sub) in enumerate(items):
        x=52+i*300
        box(c,x,385,276,110)
        text(c,title,x+17,407,22,AMBER,True)
        text(c,sub,x+17,451,18,TEXT)
        if i<3: arrow(c,x+280,440,x+296,AMBER)
    text(c,'확장안 · 현재 미구현',57,515,19,AMBER,True)
    text(c,'검증 계획: 검색 Recall@k · 인용 정확성 · 기준일/권한 누출 · 검토 시간',288,515,20,TEXT)
    text(c,'검색 결과는 담당자의 근거 검토를 돕고, 현재 신고의 자동 라벨에는 다른 신고의 사실을 섞지 않습니다.',57,551,19,MUTED)
    takeaway(c,s['takeaway'])


def llm_detail(c,s):
    cards(c,s | dict(cards=[
        ('신고 분류 출력','주 증상 1개·보조 최대 2개\n위험 요소 6개·심각도 1~3\n\n원문에 있는 인용 200자 이내\n한국어 요약 40자 이내\n모델·프롬프트·원문 해시 저장','',CYAN),
        ('상황 요약 경로','완성된 LLM 근거만 입력\n해당 칸 최대 10건 고정 선택\n\n수치 문장은 코드가 작성\nLLM 상황 문장마다 #신고번호\n다른 칸 인용은 폐기','',AMBER),
        ('현재 확인한 범위',f"API 출력 검사: {PILOT_DONE}/{PILOT_TOTAL}건 통과\n초기 인용 실패 14건은 수정\n\n제품은 키워드 기준선\n사람 정답 정확도는 미측정\n전체 7,502건 결과 대기",'',GREEN),
    ]))


def revise_stat_story(prelim, finals):
    source = json.loads((FIGURES / 'source.json').read_text())
    # Figure source is produced independently from current public JSON and detector math.
    demo = source['example']
    demo['ratio'] = demo['observed'] / demo['baseline']
    monthly = slide('이번 달 신고를, 지난 12개월과 비교합니다.',
        '실제 키워드 집계 | HYUNDAI SONATA · 화재·과열 · 2018년 8월', 'figure',
        figure='sonata-monthly-baseline.png',
        metrics=[('이번 달', f"{demo['observed']}건", '고유 신고 번호로 집계'),
                 ('직전 12개월 평균', f"{demo['baseline']:.2f}건", '이번 달은 평균에서 제외'),
                 ('평소 대비', f"{demo['ratio']:.2f}배", '2018-09-01부터 확인 가능')],
        status='실제 신고 건수 · 키워드 기준선',
        takeaway='접수일로 월을 나눕니다. 0건인 달도 포함하고, 선택한 기준일 뒤의 신고는 보지 않습니다.',
        refs='E04 · E07 · E19',time=25)
    poisson=slide('평소에도 이만큼 나올 수 있는지 묻습니다.',
        '포아송 모형: 평소 평균이 같은 상태에서 이번 달 건수 이상이 나올 확률을 계산합니다.', 'figure',
        figure='poisson-right-tail.png',
        metrics=[('관측 건수 이상 확률', f"p = {demo['p_value']:.6f}", '포아송 모형 아래의 확률'),
                 ('경보 조건', 'p < 0.001', '그리고 월 3건 이상'),
                 ('이번 사례', '두 조건 충족', '원문을 검토할 후보로 표시')],
        status='통계의 역할 · 경보 후보 판단',
        takeaway='p값은 결함일 확률이 아닙니다. 배수가 커도 확률과 최소 건수 조건을 함께 통과해야 합니다.',
        refs='E04 · E19',time=25)
    llm=slide('LLM은 문장을 정해진 항목으로 바꿉니다.',
        '직접 분류 → 출력 검사 → 캐시 → 월별 집계. 현재 제품의 통계는 키워드 기준선입니다.', 'llm_flow',
        status='고정 50건 API 출력 검사 완료 · 분류 정확도 미측정',time=25,refs='E02 · E10 · E11 · E21',
        takeaway='같은 신고의 키워드·LLM 분류를 비교하고, 사람이 확인한 정답으로 정확도를 따로 검증합니다.')
    val=slide('경보 규칙과, 그 규칙의 검증을 나눕니다.',
        '규칙 선택에 쓴 개발용(dev)과 고정 규칙으로 평가한 검증용(holdout)을 분리했습니다.', 'validation_graph',
        status='등록 사례·대조군 · 키워드 백테스트',time=25,refs='E08 · E09 · E20',
        takeaway='선정 사례의 경보 발생 비율입니다. 포아송 분포의 적합성이나 일반 정확도를 검증한 값은 아닙니다.')
    stats=slide('부록. 경보 계산과 모형 가정의 범위.',
        '독립 계산 확인 · 과거 사례 평가 · 확률모형의 적합성은 서로 다른 검사입니다.', 'technical_stats',
        status='규칙은 고정 · 모형 적합성 추가 검증 필요',time=0,appendix=True,refs='E04 · E07 · E19 · E20',
        takeaway='작은 p값만으로 전체 오류율을 보장하지 않습니다. 작은 대조군·신고 쏠림·노출량 차이도 남아 있습니다.')
    rag=slide('부록. pgvector·RAG는 확장안으로 구분합니다.',
        '원래 기획의 ‘유사 과거 사례’는 아직 미구현입니다. pgvector/RAG는 이를 보완하기 위한 설계입니다.', 'rag_scope',
        status='사용자 승인 확장 설계 · 현재 미구현',time=0,appendix=True,refs='E02 · E21 · E22',
        takeaway='분류 검증을 먼저 완료합니다. RAG는 근거 검색 확장으로 설계하며, 효과 지표는 아직 측정하지 않았습니다.')
    detail=slide('부록. 분류와 상황 요약은 서로 다른 호출입니다.',
        '라벨 분류는 개별 신고를, 상황 요약은 같은 경보 칸의 선택된 근거만 다룹니다.', 'llm_detail',
        status='현재 코드·캐시의 실제 범위',time=0,appendix=True,refs='E02 · E06 · E10 · E21',
        takeaway='인용 실패 14건은 원문 후보 번호를 재선택해 통과했습니다. 전체 7,502건과 데모 요약의 추가 실행은 승인됐으며 결과를 기다립니다.')
    # Compact core story preserves the two statistical chart pages in the timed body.
    main=[prelim[0]|dict(time=15),prelim[1]|dict(time=15),prelim[2]|dict(time=10),llm,
          monthly,poisson,val,prelim[4]|dict(time=15,subtitle='38회 과거 경보 재계산 · 독립 계산 64칸 대조. 당시 파일의 공개·수정 이력은 복원하지 못했습니다.'),prelim[5]|dict(time=15),
          prelim[3]|dict(time=50),prelim[7]|dict(time=10),prelim[8]|dict(time=10)]
    appendix_eval=finals[14] | dict(title='부록. 등록 평가와 선행 일수의 정의.',appendix=True,time=0)
    extra=[stats,slide('부록. 비교 통계와 업무량도 범위를 밝힙니다.', '이항 계산은 비교용이며, 포아송이 현재 주 경보 규칙입니다. 업무량은 현업 투입 시간이 아닙니다.', 'comparison_stats',status='실제 계산 · 주 분석과 보조 분석 분리',time=0,appendix=True,refs='E04 · E13 · E18 · E19 · E23',takeaway='서로 다른 지표를 하나의 정확도로 합치지 않습니다. 발생 비율·경보량·모형 적합성·분류 정답은 별개입니다.'),appendix_eval,detail,rag,slide('부록. 제출 기획과 현재 구현의 차이를 남깁니다.', '요청서는 원래 기획의 담당자 결정을 구체화했습니다. AI·유사 사례 검색의 미완료를 완료로 표시하지 않습니다.', 'proposal_scope',status='제출 기획 보존 · 미완료·보완 이유 공개',time=0,appendix=True,refs='E01 · E02 · E22 · E24',takeaway='유사 사례는 원래 기획의 미구현 기능입니다. 직접 분류 검증을 먼저 하고, 근거 검색으로 보완합니다.'),slide('부록. 증상 다음에는 조사 질문과 확인 자료가 필요합니다.', '현재 제품 완성을 우선합니다. 가설과 확인 절차는 후속 설계이며 실제 원인 추정 기능은 아닙니다.', 'hypotheses_design',status='설계·발표만 · 자료 연결·가설 생성 미구현',time=0,appendix=True,refs='E01 · E22 · E24 · E25',takeaway='현재는 조사 요청서를 완성합니다. 이후의 가설·추가 자료·담당자 확인은 출처와 상태를 나누어 검증합니다.')]
    fm=[s | dict(time=t) for s,t in zip(main,[15,25,25,40,45,45,50,35,40,100,35,25])]
    fm[0]['tag']='결선 · 8분 발표 + 2분 질의응답'
    fm[-1]=fm[-1] | dict(takeaway='8분 발표·데모 종료 → 2분 질의응답. 근거 계산과 미사용 기술의 범위는 부록에서 확인합니다.')
    prelim_result=main+[dict(s) for s in extra]
    finals_result=fm+[dict(s) for s in extra]+[s | dict(appendix=True,time=0) for s in [finals[12],finals[13],finals[15]]]
    for deck in (prelim_result,finals_result):
        for i,item in enumerate(deck[12:],1):
            item['title']=item['title'].replace('부록. ', '').replace('부록 1. ', '').replace('부록 2. ', '').replace('부록 4. ', '')
            item['title']=f'부록 {i}. '+item['title']
    return prelim_result,finals_result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',type=Path,default=ROOT/'output'/'pdf')
    ap.add_argument('--font-dir',type=Path,default=ROOT/'assets')
    args=ap.parse_args()
    pdfmetrics.registerFont(TTFont('KR',str(args.font_dir/'IBMPlexSansKR-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('KR-Bold',str(args.font_dir/'IBMPlexSansKR-SemiBold.ttf')))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    prelim,finals=prepare_slides()
    prelim,finals=revise_stat_story(prelim,finals)
    RENDERERS.update(product=product,figure=figure_panel,llm_flow=llm_flow,validation_graph=validation_graph,technical_stats=technical_stats,rag_scope=rag_scope,llm_detail=llm_detail,comparison_stats=comparison_stats,proposal_scope=proposal_scope,hypotheses_design=hypotheses_design)
    assert sum(s['time'] for s in prelim)==240
    assert sum(s['time'] for s in finals)==480
    assert sum(not s.get('appendix', False) for s in finals)==12
    build('4분 예선',prelim,args.output_dir/'EarlySignal-preliminary-4min-DRAFT.pdf')
    build('결선 8분 + Q&A 2분',finals,args.output_dir/'EarlySignal-finals-10min-DRAFT.pdf')
    source={'draft':True,'measured_product_results_included':bool(MEASURED),'product_capture':str(SCREENSHOT.relative_to(ROOT)) if SCREENSHOT.exists() else None,'finals_presentation_seconds':480,'finals_qa_seconds':120,'appendix_seconds':0,'preliminary':prelim,'finals':finals}
    (ROOT/'storyboard.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built preliminary 12 + 7 appendix pages / 240 seconds; finals 12 + 10 appendix pages / 480 seconds + 120 seconds Q&A.')


if __name__=='__main__':
    main()
