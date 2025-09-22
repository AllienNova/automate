# AutoApply Agent

An extensible Python agent that discovers fresh job postings, ranks them against a candidate's resume, and drives a browser to submit applications automatically. The agent combines structured job search APIs, resume-aware scoring, and computer-vision assisted button detection to reliably automate repetitive application workflows.

## Features

- **Freshness-aware discovery** – query multiple job boards using rolling windows (past 24 hours, 3 days, etc.) while avoiding duplicates.
- **Resume intelligence** – extract resume text from PDF, compute keyword and skill overlap, and prioritise the most relevant roles.
- **Browser automation** – use Playwright to navigate postings, locate "Apply" buttons (with fallbacks that leverage template-based computer vision), upload resumes, and populate contact forms.
- **Configurable pipeline** – customise user profile, resume path, search preferences, and automation settings through a single configuration file.
- **Extensible sources** – add new job source integrations by implementing the `JobSource` protocol.

## Installation

Create a virtual environment and install the project with the testing extras:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[testing]
```

To enable browser automation you also need Playwright and its browser binaries:

```bash
pip install .[playwright]
playwright install chromium
```

## Usage

1. Create a configuration file similar to [`examples/config.sample.json`](examples/config.sample.json) and update the paths and personal information. Ensure the `resume.path` points to a local PDF file.
2. Run the agent from the command line:

   ```bash
   autoapply-agent path/to/config.json --limit 5
   ```

   The agent will query fresh jobs, rank them, and attempt applications using the configured automation settings.

## Extending job sources

Implement the `JobSource` protocol in `autoapply.job_sources.base` and register the class in the CLI's `create_sources` factory. See `RemotiveJobSource` for a fully working example that integrates with the Remotive public API.

## Running tests

```bash
pytest
```
