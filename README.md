# ProfileKit

ProfileKit is a privacy-conscious conversational agent for turning user-approved
information into editable, single-page profile materials. It supports
resume-style profiles, personal posters, business cards, researcher profiles,
project highlight sheets, and bilingual single-page introductions.

The implementation has two layers:

- A deterministic workflow controller that prevents approval stages from being
  skipped.
- One OpenAI Agents SDK agent that performs source review, writing, format
  recommendations, and draft review within that workflow. The SDK can route the
  run to DeepSeek's OpenAI-compatible API or to OpenAI.

It does not publish, host, connect accounts, verify personal claims, or decide
what a user should disclose.

## Files

- `profilekit/agent.py` — OpenAI Agents SDK agent definition and turn runner.
- `profilekit/models.py` — typed profile record and turn output.
- `profilekit/workflow.py` — allowed state transitions and approval gates.
- `profilekit/cli.py` — local interactive CLI with JSON session persistence.
- `config/system_prompt.md` — the agent's main instruction.
- `evals/` — acceptance rubric and adversarial test cases.

## Run locally

Python 3.11+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export OPENAI_API_KEY="your-key"
export PROFILEKIT_MODEL="gpt-6-astra"
profilekit
```

Alternatively, place the variables in the ignored local `.env` file. ProfileKit
loads it automatically and does not override values already exported in your
terminal.

ProfileKit defaults to `deepseek-flash` for lower-cost classroom use. The web
app can switch each local session among DeepSeek Flash, DeepSeek V4 Pro, OpenAI
GPT-6 Luna, Sol, and Astra. OpenAI Luna is the recommended low-cost OpenAI
fallback. A selection is available only when its provider key is configured.

Pass sources explicitly with repeatable `--source` options:

```bash
profilekit --source resume.pdf --source project-notes.docx
```

Supported inputs are plain text, Markdown, JSON, YAML, CSV/TSV, PDF, DOCX, and
common image filenames. Image bytes are not interpreted in this first local
version; the image is registered as requiring authorization and the agent offers
a text-only or placeholder route. A supplied file is approved for inspection,
not automatically for public display.

## Run the classroom web app

The visual workspace is the recommended way to demonstrate ProfileKit:

```bash
source .venv/bin/activate
profilekit-web
```

Before class, run the offline safety check:

```bash
python -m profilekit.preflight
```

It checks the local configuration, provider readiness, web assets, one-page PDF
generation, and privacy filtering without displaying any API key.

It opens `http://127.0.0.1:8765` and provides:

- an 11-stage workflow visualization;
- an English-first interface and model selector;
- conversational intake and source review;
- drag-and-drop source uploads;
- direct extraction from resume or profile DOCX files;
- immediate setup from `default_config.json` without an API call;
- a live Personal Profile Record with item-level privacy decisions;
- a matching one-page preview with six themes: Academic, Modern, Minimal,
  Sunrise, Studio, and Editorial;
- a customization panel for core profile content, audience, purpose, tone, color,
  typography, density, and privacy restrictions;
- a single-page PDF export that omits restricted and unconfirmed sensitive items;
- three fictional classroom demonstrations (research, student developer,
  and student designer) selected beside **Load demo**; and
- local JSON export for inspecting the agent state.

Use `profilekit-web --no-browser` when you do not want it to open a browser
automatically. The web session is stored locally in
`.profilekit/web-session.json`, ignored by Git, and written with user-only file
permissions. API keys remain on the server and are never sent to the page.
Extracted upload text is sent to the selected model provider when the user asks
the agent to review it, but it is hidden from the visible browser transcript.
The private source context stays only in server memory for the current run so
later agent turns can refine the record; Reset, Load demo, or restarting the
server clears it.

For a quick style comparison, load any fictional example, choose a template in
the preview, then use **Customize** to tune its accent color, typography, and
density. Template changes set a readable default accent; a later manual color
choice overrides it. The preview and PDF now use the same one-column content
plan. For long material, ProfileKit first adjusts spacing and type size within
a readable range and shortens unusually long individual entries, then omits
trailing entries only if needed. It reports the number omitted and any shortened
entries, header, or introduction in the preview and
marks shortened output in the PDF footer. The complete text remains in the
editable Personal Profile Record.

Run `python -m profilekit.preflight` to check every example against all six
PDF themes without an API call. Run `python scripts/build_demo_gallery.py` to
regenerate the three fictional sample PDFs in `output/pdf/`.

The template direction was informed by [Reactive Resume's content-first design
notes](https://github.com/reactive-resume/reactive-resume/blob/main/DESIGN.md),
[JSON Resume's separation of data and themes](https://github.com/jsonresume/resume-cli/blob/master/README.md),
and [CMU's viewer-friendly poster guidance](https://www.cmu.edu/student-success/other-resources/handouts/comm-supp-pdfs/designing-viewer-friendly-poster.pdf).
ProfileKit's layouts and implementation are original; no third-party template
assets are bundled.

You can configure a profile in three complementary ways:

1. Upload a resume or personal-information DOCX/PDF, then ask the agent to review it.
2. Describe the content, audience, and preferences in the conversation.
3. Edit `default_config.json` and upload that exact filename for deterministic setup,
   then use the agent to refine the imported wording.

Session data is saved locally to `.profilekit/session.json` by default. Do not
commit that file; it can contain personal information. Choose a different path
with `profilekit --session /path/to/session.json`.

## Test without an API key

```bash
python -m unittest discover -s tests -v
```

## Privacy notes

- Phone numbers are excluded until explicitly approved; home addresses are
  always excluded.
- Images, logos, links, third-party references, and confidential or unpublished
  work each require separate approval.
- Removing an item never requires restarting the workflow.
- Generated output remains a draft until the final approval stage.

This tool supports organization and drafting. It does not provide legal,
employment, immigration, medical, financial, or formal accessibility advice.

## Upload to GitHub yourself

No GitHub credentials or connection are required by this project. When you are
ready, initialize and push it from this directory:

```bash
git init -b main
git add .
git commit -m "Initial ProfileKit agent"
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

Review `git status` before committing. `.venv`, `.env`, and `.profilekit` are
ignored so dependencies, secrets, and local profile sessions are not uploaded.

## Test API credentials safely

`.env` is ignored by Git. `.env.example` contains variable names only and is
safe to commit. The diagnostic script never prints keys or generated content:

```bash
# Authentication and model-list checks only
python scripts/test_api_keys.py

# Also send one minimal generation request to each provider
python scripts/test_api_keys.py --generate
```

The local ProfileKit runtime uses the OpenAI Agents SDK with either OpenAI or
DeepSeek's OpenAI-compatible API. Gemini remains an independent credential
check and is not yet a ProfileKit conversation provider.
