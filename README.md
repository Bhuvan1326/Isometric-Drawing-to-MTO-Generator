# IsoMTO — Isometric Drawing to Automated MTO Generator

Upload a piping isometric drawing (PNG / JPG / PDF) and get back a structured
Material Take-Off: a bill of every pipe, fitting, flange, valve, gasket, and
bolt set on the drawing. A vision LLM reads the drawing; a validation layer
normalizes units and re-derives gaskets + bolt sets from flange counts.

## Architecture

```
┌────────────────┐     upload (PNG/JPG/PDF)      ┌──────────────────────────┐
│  Next.js UI    │ ───────────────────────────> │  FastAPI backend         │
│  (frontend/)   │ <──── JSON MTO + status ──── │  (backend/app)           │
│                │ <──── CSV download ───────── │                          │
│  - dropzone    │                              │  routes/  upload, mto,   │
│  - results     │                              │           health         │
│  - CSV export  │                              │  services/ file, jobs    │
└────────────────┘                              │  pipeline/ mock|gemini   │
                                                │  prompts/  prompt + JSON │
                                                │             schema       │
                                                │  models/  Pydantic MTO   │
                                                └─────────────┬────────────┘
                                                              │
                                            ┌─────────────────┴──────────────┐
                                            │                                  │
                                       no API key                          API key set
                                            │                                  │
                                  ┌─────────┴────────┐             ┌─────────┴─────────┐
                                  │  MockPipeline    │             │  GeminiPipeline   │
                                  │  (sample MTO)    │             │  (vision LLM +    │
                                  └──────────────────┘             │   structured JSON)│
                                                                   └───────────────────┘
```

**Pipeline choice — LLM-only, not hybrid OCR/CV.** A hybrid pipeline
(OCR + symbol detection + rules) would be more deterministic but requires a
labeled symbol library and weeks of tuning; isometric symbols vary wildly
across companies and drawing styles. A vision LLM trades deterministic
precision for massive coverage with zero training data. We mitigate the
LLM's tendency to miscount with a strict JSON schema, a deterministic
post-processing layer that re-derives gaskets/bolts from flange counts, and
per-row confidence scores. A hybrid CV pre-pass (deskew, denoise, symbol
detection) is the right next step for production — see "What I'd improve"
below.

## Setup

### Requirements

- **Node.js** 18.18+ (the project uses Next.js 13.5 / App Router)
- **Python** 3.10+ (3.11 or 3.12 recommended)
- **poppler** (optional, for higher-quality PDF rendering) — on Ubuntu:
  `sudo apt install poppler-utils`; on macOS: `brew install poppler`. If
  poppler isn't installed, the backend falls back to PyMuPDF automatically.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit .env to add GEMINI_API_KEY
                                   # (leave blank to run in mock mode)

python run.py                      # starts uvicorn on http://localhost:8000
```

The API docs are at `http://localhost:8000/docs` (Swagger) and
`http://localhost:8000/redoc`.

### Frontend

```bash
# from the project root (the Next.js app lives at the repo root)
cp .env.example .env.local         # adjust NEXT_PUBLIC_API_URL if needed
npm install
npm run dev                        # starts on http://localhost:3000
```

Open `http://localhost:3000`, upload a drawing, and the MTO appears once
extraction completes.

### Tests (backend)

```bash
cd backend
source .venv/bin/activate
pytest -v
```

The test suite forces the mock provider, so it runs without an API key.

## Environment variables

### Backend (`backend/.env`, see `backend/.env.example`)

| Variable | Default | Description |
|---|---|---|
| `VISION_PROVIDER` | `gemini` | `gemini` or `mock`. If `gemini` is set but `GEMINI_API_KEY` is empty, the app automatically falls back to `mock`. |
| `GEMINI_API_KEY` | (empty) | Google AI Studio API key. Get one at https://aistudio.google.com/apikey. Leave blank to run in mock mode. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model. `gemini-2.5-flash` is fast and cheap; `gemini-2.5-pro` is more accurate. |
| `MAX_FILE_SIZE_MB` | `20` | Server-side upload limit. The client checks the same limit. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed origins for the Next.js dev server. |
| `UPLOAD_DIR` | `./_uploads` | Temp storage for uploaded files. Files are deleted after extraction. |

### Frontend (`.env.local`, see `.env.example`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL of the FastAPI backend. |

## How the AI pipeline works

### 1. Pre-process (`app/services/file_service.py`)

- Validate content-type, extension, and magic bytes server-side. Reject
  files > 20MB.
- For PDFs, render the first page to a 200-DPI PNG using `pdf2image`
  (poppler) with a fallback to PyMuPDF. PNG/JPG bytes pass through.

### 2. Extract (`app/pipeline/gemini.py`)

- Send the image to Gemini (`gemini-2.5-flash` by default) with the prompt
  from `app/pipeline/prompts/extraction_prompt.txt` and the JSON schema from
  `app/pipeline/prompts/mto_schema.json` as `response_schema`. This is the
  provider's structured-output mode — the model is constrained to emit JSON
  matching the schema, so we never hand-parse free text.
- Temperature 0.1 for extraction fidelity. 60s timeout (enforced with a
  worker thread because the SDK doesn't expose a clean per-request timeout).

### 3. Validate (`app/pipeline/validate.py`)

- Parse the LLM JSON into Pydantic models (`app/models/mto.py`). Malformed
  output raises a typed `PipelineError`.
- **Re-derive gaskets and bolt sets deterministically.** One flanged joint =
  one gasket + one bolt set, and a joint is a *pair* of flanges. We count
  flange items, integer-divide by 2, and emit that many gaskets and bolt
  sets — replacing any GASKET/BOLT rows the LLM returned. This catches LLM
  miscounts on dense drawings.
- **Recompute the summary block** from the items, never trusting the LLM's
  own summary.
- Renumber items sequentially starting at 1.

### 4. Serve

- The validated MTO is stored in the in-memory job store. The frontend polls
  `GET /api/mto/{job_id}` until `state == "done"`, then renders the table,
  summary cards, and metadata block. CSV is available at
  `GET /api/mto/{job_id}/csv`.

### Prompt strategy

The prompt (in `app/pipeline/prompts/extraction_prompt.txt`) is engineered to:

- State the domain conventions explicitly (pipe by length, everything else by
  count, one gasket + one bolt set per flanged joint).
- Specify the exact standards vocabulary to use (ASME B16.9 / B16.5 / B16.11
  / B16.20, ASTM A106 / A234 / A105 / A312 / A182).
- List the component families to recognize (elbows, tees, reducers, caps,
  couplings, unions, olets, flanges by type, valves drawn as bowties).
- Define a confidence rubric (0.9-1.0 clearly drawn, 0.6-0.9 drawn but not
  dimensioned, 0.3-0.6 inferred, below 0.3 don't report).
- Tell the model to return null rather than invent values, and to derive
  gaskets/bolts even when not drawn.

### Mock fallback

When `GEMINI_API_KEY` is not set, `app/config.py` forces `VISION_PROVIDER=mock`.
The `MockPipeline` (`app/pipeline/mock.py`) returns a realistic 6" carbon-steel
cooling-water line MTO. The mock data flows through the same
`parse_and_validate` code path as the real pipeline, so the derived gaskets,
bolt sets, and summary are computed by the real validator — the mock
exercises the same code. The returned MTO has `source: "mock"` and every item
is tagged `MOCK SAMPLE` in remarks; the frontend shows a banner explaining
mock mode.

### Provider is swappable

Adding a new vision provider is a one-file change:

1. Implement the `Pipeline` protocol (in `app/pipeline/base.py`) in a new
   module, e.g. `app/pipeline/openai.py`.
2. Register it in `app/pipeline/__init__.py`'s `_PROVIDERS` dict.
3. Set `VISION_PROVIDER=openai` in `.env`.

No other code changes needed — the routes and services talk to the pipeline
through the protocol.

## Assumptions and known limitations

- **Single-page extraction.** For multi-page PDFs, only the first page is
  rendered and sent to the LLM. Real isometrics are usually one sheet, but a
  multi-sheet line would need page aggregation.
- **Flange-pair heuristic.** We derive gaskets/bolts as `flange_count // 2`.
  This assumes flanges come in pairs (joints). A blind flange at a line end
  is one flange with no pair — it would be undercounted by this integer
  division. A more accurate model would look at whether each flange is
  paired with another flange, a valve, or equipment, but the LLM doesn't
  reliably give us that structure.
- **Field-weld counting is a heuristic.** We count items whose remarks or
  description contain "FW" or "field weld". The spec calls field welds a
  bonus output; a production system would parse weld symbols from the drawing
  with CV.
- **In-memory job store.** Jobs are lost on restart and don't survive
  horizontal scaling. The spec allows in-memory or SQLite; in-memory keeps
  the dependency list short. Swap `JobStore` for SQLite + a lock if needed.
- **No auth.** The spec didn't ask for auth, so there's none. Anyone who can
  reach the backend can upload and run the pipeline.
- **PDF rendering depends on poppler or PyMuPDF.** If neither is installed,
  PDF uploads fail with a typed `BAD_FILE` error. PNG/JPG always work.
- **Confidence scores are model self-reports.** Gemini's confidence is its
  own estimate, not a calibrated probability. Treat it as a rough guide.
- **No Excel export.** CSV is implemented; Excel (.xlsx) is noted as a bonus
  in the spec and not implemented. CSV opens cleanly in Excel.

## What I'd improve with more time

1. **Hybrid CV pre-pass.** Deskew, denoise, and detect the title block and
   symbol regions with OpenCV before sending to the LLM. This would let us
   crop the title block for a focused metadata-extraction call and crop
   symbol regions for higher-confidence component identification. It would
   also let us count weld symbols deterministically.
2. **Multi-page PDF support.** Render all pages, send each to the LLM, and
   merge the MTOs (deduping by item_no and summing pipe lengths).
3. **Flange-pairing logic.** Ask the LLM to return each flange with a
   `paired_with` field (another flange, a valve, equipment), then derive
   gaskets/bolts from the actual pair structure instead of `// 2`.
4. **Excel export.** Add a `/api/mto/{job_id}/xlsx` endpoint with openpyxl,
   with formatted header rows and a separate summary sheet.
5. **Persistence.** Swap the in-memory `JobStore` for SQLite so jobs survive
   restarts. Add a `GET /api/jobs` list endpoint.
6. **Auth.** Supabase email/password auth with per-user job ownership.
7. **Drawing diff.** Upload two revisions of the same isometric and get a
   diff MTO (added/removed/changed items). This is a real workflow for
   revision control on piping projects.
8. **Calibrated confidence.** Run the same drawing through the pipeline 3
   times at temperature 0.7 and use the agreement across runs as a
   pseudo-calibrated confidence. Items that appear in all 3 runs are high
   confidence; items in 1 of 3 are low.
9. **Streaming progress.** The current fake progress bar eases forward on
   each poll. A WebSocket or SSE stream from the backend would give real
   stage-by-stage progress.
10. **Symbol library + few-shot.** Build a small library of cropped isometric
    symbols (elbows, valves, flanges) and include a few as few-shot image
    examples in the prompt. This would help the LLM on unusual drawing styles.

## Where to put sample drawings and screenshots

- `backend/samples/` — sample isometric drawings (PNG/JPG/PDF) for testing
  the pipeline. Drop a few real isometrics here.
- `docs/screenshots/` — screenshots of the running app for the README. Add
  these after you've run the app and captured the upload + results screens.

## Project structure

```
.
├── README.md                   (this file)
├── .env.example                (frontend env vars)
├── app/                        (Next.js App Router — frontend)
│   ├── layout.tsx
│   ├── page.tsx                (upload + results orchestration)
│   └── globals.css
├── components/
│   ├── upload-dropzone.tsx
│   ├── results-panel.tsx
│   ├── processing-state.tsx
│   ├── drawing-preview.tsx
│   ├── metadata-block.tsx
│   ├── summary-cards.tsx
│   ├── mto-table.tsx
│   └── ui/                     (shadcn/ui components)
├── lib/
│   ├── api.ts                  (typed API client)
│   └── utils.ts
├── backend/
│   ├── app/
│   │   ├── main.py             (FastAPI app + CORS + error handlers)
│   │   ├── config.py           (settings, provider selection)
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── upload.py
│   │   │   └── mto.py
│   │   ├── models/
│   │   │   ├── mto.py          (MTOItem, MTO, DrawingMeta, Summary, enums)
│   │   │   └── api.py          (JobStatus, UploadResponse, ErrorResponse)
│   │   ├── services/
│   │   │   ├── job_store.py    (in-memory job storage)
│   │   │   └── file_service.py (validation, PDF rendering)
│   │   └── pipeline/
│   │       ├── base.py         (Pipeline protocol)
│   │       ├── mock.py         (mock fallback)
│   │       ├── gemini.py       (Gemini vision pipeline)
│   │       ├── validate.py     (Pydantic parse + derive + summary)
│   │       └── prompts/
│   │           ├── extraction_prompt.txt
│   │           └── mto_schema.json
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_models.py
│   │   ├── test_validate.py
│   │   └── test_routes.py
│   ├── requirements.txt
│   ├── run.py
│   ├── .env.example
│   └── samples/                (drop sample drawings here)
└── package.json
```
