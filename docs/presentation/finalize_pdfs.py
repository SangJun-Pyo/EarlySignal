#!/usr/bin/env python3
"""Add a confirmed presenter and correct the validation chart in reviewed PDFs.

The v2 PDFs, original script, and historical QA snapshots remain unchanged.
"""
import argparse
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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def single_page(width, height, draw):
    stream = io.BytesIO()
    c = canvas.Canvas(stream, pagesize=(width, height), pageCompression=1)
    draw(c)
    c.showPage()
    c.save()
    stream.seek(0)
    return PdfReader(stream).pages[0]


def finalize(entry, source_dir, output_dir, presenter, deck=None, slides=None):
    source = source_dir / entry['file']
    if digest(source) != entry['sha256']:
        raise ValueError(f'Reviewed input changed: {source.name}')
    output = output_dir / (source.name.replace('-3d-v2.pdf', '-final.pdf')
                           if deck else source.name.replace('.pdf', '-final.pdf'))
    reader = PdfReader(source)
    if len(reader.pages) != entry['pages']:
        raise ValueError('Reviewed page count changed')
    writer = PdfWriter()
    for number, page in enumerate(reader.pages, 1):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if deck and number == 7:
            def draw_chart(c):
                d.frame(c, slides[6], 7, len(slides), deck, 9)
                d.validation_graph(c, slides[6])
            corrected = single_page(width, height, draw_chart)
            if ''.join(corrected.extract_text().split()) != ''.join(page.extract_text().split()):
                raise ValueError('Current chart data or copy differs from the reviewed PDF')
            page = corrected
        elif deck and number in (1, 9):
            def draw_name(c):
                if number == 1:
                    d.text(c, f'발표자 {presenter}', 57, 314, 20, d.TEXT)
                else:
                    d.text(c, f'발표자 {presenter}', 1018, 631, 17, d.TEXT)
            page.merge_page(single_page(width, height, draw_name))
        elif not deck and number == 1:
            def draw_script_name(c):
                c.setFillColor(d.color('#55677B'))
                c.setFont('KR', 12)
                c.drawRightString(width - 44, height - 63, f'발표자 {presenter}')
            page.merge_page(single_page(width, height, draw_script_name))
        writer.add_page(page)
    writer.add_metadata({
        '/Title': f'EarlySignal | {deck or "발표 대본"} | {presenter}',
        '/Author': presenter,
        '/Subject': str(reader.metadata.get('/Subject', 'EarlySignal 발표 대본')),
    })
    writer.write(output)
    return {'file': output.name, 'pages': len(reader.pages), 'sha256': digest(output),
            'source_file': source.name, 'source_sha256': digest(source),
            'changed_pages': [1, 7, 9] if deck else [1], 'presenter': presenter}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', type=Path, default=ROOT/'output/pdf')
    ap.add_argument('--output-dir', type=Path, default=ROOT/'output/pdf')
    args = ap.parse_args()
    config = json.loads((ROOT/'finalization.json').read_text(encoding='utf-8'))
    qa = json.loads((ROOT/config['source_qa']).read_text(encoding='utf-8'))
    story = json.loads((ROOT/'storyboard-v2.json').read_text(encoding='utf-8'))
    presenter = config['presenter']
    for name, filename in [('KR', 'IBMPlexSansKR-Regular.ttf'), ('KR-Bold', 'IBMPlexSansKR-SemiBold.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(ROOT/'assets'/filename)))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for key, deck, entry in zip(('preliminary', 'finals'), ('4분 예선', '결선 8분 + Q&A 2분'), qa['decks']):
        outputs.append(finalize(entry, args.source_dir, args.output_dir, presenter, deck, story[key]))
        story[key+'_pdf'] = 'output/pdf/' + outputs[-1]['file']
    outputs.append(finalize(qa['script'], args.source_dir, args.output_dir, presenter))
    markdown = (ROOT/'speaker-script.md').read_text(encoding='utf-8')
    markdown = markdown.replace('# EarlySignal 발표 대본\n', f'# EarlySignal 발표 대본\n\n발표자 {presenter}\n', 1)
    for entry in outputs[:2]:
        markdown = markdown.replace(entry['source_file'], entry['file'])
    (ROOT/'speaker-script-final.md').write_text(markdown, encoding='utf-8')
    story.update(version='final', presenter=presenter, speaker_script='speaker-script-final.md')
    (ROOT/'storyboard-final.json').write_text(json.dumps(story, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    manifest = {'outputs': outputs, 'presenter': presenter, 'issue': config['issue'],
                'preliminary_seconds': 240, 'finals_seconds': 480, 'qa_seconds': 120,
                'actual_rehearsal_completed': False}
    (ROOT/'final-build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
