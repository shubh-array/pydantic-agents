---
name: portable-webapp-testing
description: Test and debug local web applications with Python Playwright scripts. Use for verifying frontend behavior, inspecting rendered DOM, capturing screenshots, collecting browser console logs, and running browser automation against static HTML or local dev servers.
license: Apache-2.0. Complete terms in LICENSE.txt
compatibility: Requires Python 3.9+, Playwright with browser binaries installed, shell access, and access to local files or localhost ports for the app under test.
---

# Portable Webapp Testing

Use native Python Playwright scripts to inspect, test, and debug local web applications. Keep server lifecycle separate from browser automation by using `scripts/with_server.py` when the app is not already running.

## Quick Start

Always run helper scripts with `--help` before use:

```bash
python scripts/with_server.py --help
```

Use bundled scripts as black boxes first. Read or modify them only when the task needs a custom behavior that the script does not expose.

## Decision Tree

```text
User task -> Is it static HTML?
  Yes -> Read HTML file directly to identify selectors
    Success -> Write Playwright script using selectors
    Fails or incomplete -> Treat as dynamic

  No -> Is the server already running?
    No -> Run scripts/with_server.py --help, then use the helper
    Yes -> Reconnaissance, then action
```

For dynamic apps:
1. Navigate and wait for `networkidle`.
2. Capture a screenshot or inspect rendered DOM.
3. Identify selectors from rendered state.
4. Execute actions with discovered selectors.

## Server Helper

Single server:

```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

Multiple servers:

```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

Set `OUTPUT_DIR` to control logs and screenshots:

```bash
OUTPUT_DIR=./test-results python your_automation.py
```

## Playwright Pattern

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5173")
    page.wait_for_load_state("networkidle")
    # inspect, interact, assert, or capture screenshots
    browser.close()
```

## Best Practices

- Use `sync_playwright()` for short, task-focused automation scripts.
- Always close the browser, preferably in the same script that opened it.
- Prefer descriptive selectors such as `text=`, `role=`, stable CSS selectors, or IDs.
- Add explicit waits with `page.wait_for_selector()` or short `page.wait_for_timeout()` calls when UI state changes after an action.
- Save screenshots, logs, and reports under `OUTPUT_DIR` or `./test-results`.

## Host Agent Adaptation

- Claude-style hosts: attach screenshots, logs, or reports using the host's file or rendered-output mechanism.
- Cursor Agent: write results under `./test-results` or the requested output path, then summarize key failures and file paths.
- Codex or generic CLI agents: print concise results to stdout and save screenshots/logs under `OUTPUT_DIR` or `./test-results`.
- CI or API runners: return process exit codes and machine-readable logs where possible.

Do not assume hosted paths such as `/mnt/user-data/outputs`. Prefer `OUTPUT_DIR`, `./test-results`, or `/tmp`.

## Common Pitfall

Do not inspect the DOM before waiting for `networkidle` on dynamic apps. Wait for `page.wait_for_load_state("networkidle")` before inspection unless the app intentionally keeps network activity open.

## Reference Files

- `examples/element_discovery.py` - discover buttons, links, and inputs.
- `examples/static_html_automation.py` - automate local HTML with `file://` URLs.
- `examples/console_logging.py` - capture browser console logs.
