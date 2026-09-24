# ProfileKit

ProfileKit is a privacy-conscious conversational agent for turning user-approved
information into editable, single-page profile materials. It supports
resume-style profiles, personal posters, business cards, researcher profiles,
project highlight sheets, and bilingual single-page introductions.

The implementation has two layers:

- A deterministic workflow controller that prevents approval stages from being
  skipped.
- One OpenAI Agents SDK agent that performs source review, writing, format
  recommendations, and draft review within that workflow.

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

Pass sources explicitly with repeatable `--source` options:

```bash
profilekit --source resume.pdf --source project-notes.docx
```

Supported inputs are plain text, Markdown, JSON, YAML, CSV/TSV, PDF, DOCX, and
common image filenames. Image bytes are not interpreted in this first local
version; the image is registered as requiring authorization and the agent offers
a text-only or placeholder route. A supplied file is approved for inspection,
not automatically for public display.

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

The local ProfileKit runtime currently uses the OpenAI Agents SDK. DeepSeek and
Gemini are checked independently; their presence in `.env` does not silently
route ProfileKit conversations to those services.
