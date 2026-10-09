# EarlySignal humanized preliminary deck independent review

Result: PASS. No actionable defects.

Reviewed PDF: EarlySignal-preliminary-4min-humanized.pdf
SHA-256: 991cf65af1d8299d1e8daf08b6c6cc2759b6d1ef55fba0af80be45e5e96a3a32
Script: speaker-script-4min.md
SHA-256: c0b61957cfb00bdcc78a0652984c40f59684e652a4ba84ac1a8360844e83468e

- Directly rendered pages 2, 3 and 7 from the current PDF at 1200px and visually inspected them. The supplied 1400px page 2/3 renders were also inspected. No text overlap, clipping or missing Korean glyphs. PDF character-coordinate inspection on all three changed pages found zero out-of-page characters.
- Page 2 names the automotive customer safety role and states that fixed keyword searches can miss reports using other expressions. The wording is a potential limitation and does not assert proven LLM superiority. The three phrases remain marked as explanatory examples.
- Page 3 clearly separates consumer report text input, LLM symptom classification, statistical monthly-count increase detection, and the human investigation decision. It ends with the evidence-linked investigation request.
- Exactly pages 2, 3 and 7 differ in extracted PDF text from the reviewed simple deck. The other 19 pages, including all 15 appendices, are text-identical. Rebuilt PDF content streams are not byte-identical because font/subset references can change; no content-stream identity claim is made.
- Seven main pages + 15 appendices = 22 total pages. Storyboard still sums to 240 seconds and demo remains 60 seconds. The script matches this order and timing, links to the humanized PDF, and retains appendix mappings 1..15 to PDF8..22.
- Main page 6 and script retain the distinction between keyword case/control evaluation and the 7,502-report LLM demo. Classification accuracy, LLM early detection improvement and real-world effectiveness remain unverified; failures and limits are retained in unchanged appendix text.
- PDF/script hashes match humanized-build-manifest.json. No repository files edited by reviewer.

Temporary evidence: /tmp/earlysignal-reference-review/humanized-02.png, humanized-03.png, humanized-07.png.
Scope: artifact wording/layout and preservation review, not live demo replay, timing rehearsal or new statistical validation.
