# PDF Translator v2 — LangGraph Multi-Agent Pipeline

A production-quality PDF translation agent built with LangGraph. Translates PDFs to any language while preserving layout, fonts, colors, and document structure. Uses a multi-node pipeline with an iterative quality gate that verifies translations before reconstructing the final document.

---

## The Problem

Translating a PDF with standard tools — Google Translate, ChatGPT, or copy-paste — destroys the document structure. Text gets extracted as a flat string, columns collapse, tables break, and the result is unreadable.

This agent solves that. It extracts every text element **span by span** with its exact position, font, size, and color. It translates the content using Claude Haiku. Then it reconstructs the PDF inserting each translated block back at the **exact original coordinates** — same columns, same headers, same layout. The output is a translated PDF that looks like it was designed that way from the start.

---

## Architecture

```
PDF Input
    │
    ▼
[Analyzer Node]        ← PyMuPDF extracts native text span by span
    │                    Claude Sonnet Vision detects text in images
    ▼
[Translator Node]      ← Claude Haiku translates in batches of 40
    │                    Preserves codes, prices, brand names
    ▼
[Quality Gate Node]    ← Verifies completeness, language, length ratio
    │                    Uses real PyMuPDF test page to verify font fit
    │◄─── retry ────────  Marks failures → re-translates (max 2×)
    ▼
[Language Classifier]  ← Unicode range heuristics: LATIN / ASIAN / CYRILLIC / ARABIC
    │                    No API call — instant classification
    ▼
[Image Strategy Node]  ← Decides per element: FULL_STYLE / REDUCED_SIZE / BEST_EFFORT / SKIP
    │                    Based on script, bbox size, translation length ratio
    ▼
[Image Patcher Node]   ← PDF_REDACT_IMAGE_PIXELS paints JPEG pixels
    │                    insert_text writes translation with correct contrast
    ▼
[Reconstructor Node]   ← fill=None redaction preserves original backgrounds
    │                    Span-level insertion maintains exact position
    ▼
Translated PDF
```

---

## Why LangGraph

LangGraph is justified here because the pipeline has genuine dynamic behavior that a linear script cannot handle cleanly:

- **Conditional retry loop** — the quality gate can send elements back to the translator. In a script this requires complex state management. In LangGraph it's a single conditional edge.
- **Shared state** — all nodes read and write the same `TranslationState` TypedDict. No global variables, no passing objects between functions.
- **Per-element decisions** — the strategy router assigns a different processing path to each image element based on runtime analysis.

---

## Key Technical Decisions

### Span-level extraction vs block-level
PyMuPDF groups text into blocks, but a block can contain multiple lines with different styles, sizes, and positions. Extracting span by span gives each piece of text its exact bbox — which means pixel-perfect reinsertion. Block-level extraction loses line structure and causes text to merge.

### Quality gate with real test page
Instead of estimating font fit with formulas (which accumulate rounding errors), the quality gate creates a temporary PyMuPDF page and calls `insert_textbox` with the exact dimensions the reconstructor will use. If it returns negative, the font is too large — we reduce and retry. The reconstructor receives a size that is guaranteed to fit.

### `PDF_REDACT_IMAGE_PIXELS` for image text
Vector shapes drawn with `shape.draw_rect` are composited behind raster images in PDF rendering — they don't cover the original text. `PDF_REDACT_IMAGE_PIXELS` modifies the actual JPEG pixel data, which is the only reliable way to paint over embedded image text.

### `fill=None` for native text redaction
When redacting native text, `fill=None` removes the text from the content stream without painting any color over it. The original background — whether solid color, gradient, or image — is preserved. This avoids the visible white rectangles that appear when using `fill=(1,1,1)`.

### Numeric filtering
Numbers, prices, measurements, and product codes are filtered at extraction time — they are never sent to the translator. This avoids wasting API calls and prevents the translator from mangling values like `999.-`, `1400 r.p.m.`, or `WW90T4042CE`.

---

## Stack

| Component | Technology |
|-----------|-----------|
| Pipeline orchestration | LangGraph 0.2+ |
| PDF parsing & reconstruction | PyMuPDF (fitz) |
| Translation | Claude Haiku (batched) |
| Vision / image analysis | Claude Sonnet |
| API | FastAPI |
| Language | Python 3.12 |

---

## Pipeline Nodes

### `analyzer_node.py`
Extracts every text span from the PDF with its exact bbox, font size, color, and flags. For pages with embedded images, renders the full page at 144 DPI and sends it to Claude Sonnet Vision to detect translatable text regions. Deduplicates Vision detections that overlap with native text to prevent double-processing.

### `translator_node.py`
Translates all elements in batches of 40 using Claude Haiku. Uses assistant prefill (`{"role": "assistant", "content": "{"}`) to guarantee JSON output without markdown wrappers. Falls back to original text on parse failure so the pipeline never crashes on a bad API response.

### `quality_gate_node.py`
Checks each translated element for: empty translation, excessive length ratio (>4× original), CJK characters in Latin-target translations, and font fit using a real PyMuPDF test page. Elements that fail are marked `RETRY` and sent back to the translator. After `max_quality_iterations` the element is accepted as-is with status `ACCEPTED`.

### `language_classifier_node.py`
Classifies the script of each image text element using Unicode range counting. If >30% of characters fall in CJK ranges → `ASIAN`. Cyrillic ranges → `CYRILLIC`. Arabic ranges → `ARABIC`. Otherwise → `LATIN`. No API call required.

### `image_strategy_node.py`
Assigns a processing strategy per element based on script and geometry. Latin text that fits at 100% → `FULL_STYLE`. Fits at 80% → `REDUCED_SIZE`. Smaller → `BEST_EFFORT`. Asian text with bbox height < 10pt → `SKIP`. Numeric/code elements → `SKIP`.

### `image_patcher_node.py`
Applies translations to image regions. Samples background color from the rendered page (for complex backgrounds) or uses the Vision-detected color (for solid backgrounds). Applies `PDF_REDACT_IMAGE_PIXELS` to paint over original text pixels. Inserts translated text with contrast-adjusted color.

### `reconstructor_node.py`
Opens the PDF already patched by the image patcher. Applies `fill=None` redactions to remove native text without altering backgrounds. Inserts translated text at the exact span baseline position (`rect.y1`). Handles the save-to-same-file constraint with a temp file.

---

## Limitations

- **Image-based PDFs with complex layouts** (photos, gradients, rotated text) — Vision coordinate precision is ~2-3%, which causes visible misalignment on dense layouts like retail catalogs.
- **CJK → Latin translation** — CJK characters are ~3× more compact than Latin at the same font size. The translated text always occupies more horizontal space than the original bbox, requiring font reduction.
- **Right-to-left scripts** — Arabic and Hebrew are classified and detected but PyMuPDF's `insert_text` does not support RTL rendering. These elements are processed as best-effort with LTR layout.

---

## Setup

```bash
pip install pymupdf anthropic langchain-core langgraph fastapi uvicorn python-multipart python-dotenv pillow

# .env
ANTHROPIC_API_KEY=your_key_here
```

```bash
uvicorn backend.main:app --reload
# UI at http://localhost:8000/pdf-translator-v2/
```

---

## API

```
POST /pdf-translator-v2/translate
  file: PDF (multipart)
  target_language: "spanish" | "english" | "french" | "german" | ...
  source_language: "auto" (default)
  max_quality_iterations: 1 | 2 | 3 (default: 2)

Response: PDF file
Headers:
  X-Pages: number of pages processed
  X-Blocks-Translated: number of elements translated
  X-Time-Seconds: total processing time
  X-Quality-Iterations: quality gate iterations used
```

---

## Supported Languages

Spanish, English, French, German, Italian, Portuguese, Dutch, Polish, Russian, Chinese, Japanese, Catalan