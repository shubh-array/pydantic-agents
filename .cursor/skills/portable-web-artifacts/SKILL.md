---
name: portable-web-artifacts
description: Build portable, self-contained HTML web artifacts using React, TypeScript, Vite, Tailwind CSS, shadcn/ui, and Parcel. Use for complex interactive web deliverables that need state management, routing, reusable UI components, or a single-file HTML output.
license: Apache-2.0. Complete terms in LICENSE.txt
compatibility: Requires Node.js 18+, shell access, network access for package installation, and an agent that can edit files and return, preview, host, or attach HTML output.
---

# Portable Web Artifacts

Create interactive web deliverables that can be previewed locally, returned as files, hosted as static HTML, or handed off as a single file.

## Workflow

1. Initialize the frontend project:
   ```bash
   bash scripts/init-artifact.sh <project-name>
   cd <project-name>
   ```
2. Build the artifact by editing the generated React code.
3. Bundle the app into one HTML file:
   ```bash
   bash ../scripts/bundle-artifact.sh
   ```
   If you copied the script into the project root, run `bash scripts/bundle-artifact.sh` instead.
4. Deliver `bundle.html` according to the host agent's capabilities.
5. Test only when requested or when the UI behavior is risky.

## Stack

React + TypeScript + Vite + Tailwind CSS 3.4.1 + shadcn/ui + Parcel bundling.

The initializer creates:
- React + TypeScript project via Vite
- Tailwind CSS with shadcn/ui theme variables
- `@/` path aliases
- shadcn/ui component files from `scripts/shadcn-components.tar.gz`
- Radix UI and common shadcn/ui dependencies

The bundler creates Parcel configuration when needed and produces a single-file HTML output.

## Host Agent Adaptation

- Claude-style hosts: present or attach `bundle.html` using the host's file or rendered-output mechanism.
- Cursor Agent: provide the path to `bundle.html`; optionally run a local preview server or browser check if requested.
- Codex or generic CLI agents: return the file path, copy it to the requested output directory, or serve it with a static file server.
- API-based agents: upload or return the single HTML file using the calling application's file mechanism.

Do not assume any specific provider UI. The portable deliverable is the generated `bundle.html`.

## Design Guidance

Avoid generic AI-looking defaults such as excessive centered layouts, purple gradients, uniform rounded corners, and overuse of Inter. Choose layout, typography, color, and interaction patterns that fit the user's actual request.

## Testing Guidance

For quick local checks, open `bundle.html` in a browser or serve the project directory with a static server. For automated checks, use Playwright or an equivalent browser automation tool.

## Reference

- shadcn/ui components: https://ui.shadcn.com/docs/components
