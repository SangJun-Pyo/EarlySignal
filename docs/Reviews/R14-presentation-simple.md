# Independent review: EarlySignal preliminary simple deck

Final reviewed SHA-256: b5c1335b217f65ab285bda191f448a2c4e987185eedbec0deb77d128ab00958a

Initial review before label adjustment: 02905b1b5b30ea654d6562937c3572e8733c32baf87d58524322da4bf592910f

Result: final PDF PASS. The single chart-label overlap was corrected and independently re-rendered from the current PDF. No remaining actionable PDF visual defects.

## Review performed

- Rendered all 22 PDF pages at 1200px. Inspected all seven main pages individually and full-deck contact sheet, with source text and appendix comparisons.
- Main deck is 7 pages, appendix is 15 pages. Footers say 01/7 through 07/7; appendix numbering and Markdown table map appendix 1..15 to PDF 8..22.
- No out-of-page text on all 22 pages; Korean glyphs are intact. Main layout, concepts, title hierarchy, screenshot placement, name and closing are readable.
- Resolved finding: page 5 data labels for the two values 3 previously overlapped the yellow 4.92 baseline. Current PDF re-render /tmp/earlysignal-reference-review/simple/verified-fixed-05.png confirms both labels now sit clearly above the line. Final output hash matches the updated manifest.
- Independently recomputed directly from console.json HYUNDAI|SONATA fire_thermal monthly counts: prior 12 months [5,5,1,6,5,7,3,3,5,5,7,7] total 59, mean 59/12=4.916666666666667, current 17, ratio 3.4576271186440675. Shown 4.92 and 3.46 are correct rounding. Future months are not plotted.
- Meta holdout values are case 7/19 and control 1/17. Comparison population is 7,502. Main page 6 explicitly distinguishes cases/controls from complaints and says classification accuracy and early detection improvement require further assessment.
- Compared all 15 appendix pages against prior final PDF using mapped page pairs: old6->new8, old7->new9, old8->new10, old9->new11, old10..20->new12..22. Changes are titles, appendix/page numbers, line wrapping and re-layout of the business/Codex slide. All substantive numbers, failure cases, limitations, scope and issue35 model-year follow-up remain.
- Storyboard time allocation sums to 240 seconds; demo is exactly 60 seconds. Markdown script says allocation, not measured rehearsal. Spoken text and slide order agree. All appendix references in script match new page positions.
- Manifest output/script hashes match. Statistical input hashes for console.json, meta.json and data/backtest_kw.json match. Actual screenshot hashes and its console provenance match. Existing 3D art is reused without revision.

## Scope

Read-only repository review, with temporary renders in /tmp/earlysignal-reference-review/simple. No live product replay or rehearsal was performed. This is an artifact/design/data-preservation review, not a new validation of the detector or a claim that issue35 is complete.

## Final documentation check

- Current deck links and Markdown script link resolve; seven-stage sequence, 240-second total, 60-second demo and 15 appendix mappings agree with the PDF.
- Current source README/SPEC/STATUS documents point to the new 22-page preliminary deck and preserve the 23-page finals deck.
- Two small document-only inconsistencies were sent to the author: PRESENTATION.md demo sub-allocation still uses the old 10/20/20/10 seconds rather than the script 15/20/25; root README narrative should distinguish the detailed Poisson and business/Codex material now moved to appendix for the preliminary deck.
- qa-simple.json and R14 links target review records the author is creating; all other inspected local Markdown link targets exist.

## Current-pointer repairs

The author corrected the old demo split in PRESENTATION.md to15/20/25 seconds and clarified main-versus-appendix scope in README.md. qa-simple.json and this review are now present. Root final link and diff checks completed.
