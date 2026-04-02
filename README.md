# mark2confluence

GitHub Action for converting markdown files into Confluence pages

This Action uses [mark](https://github.com/kovetskiy/mark) (v16.x) to accomplish this task.

## Diagram Support

Mark v16+ supports rendering diagrams directly in Confluence:

| Type | Support | How to enable |
|------|---------|---------------|
| **Mermaid** | Enabled by default | Use ` ```mermaid ` fenced code blocks |
| **D2** | Opt-in | Set `FEATURES: "d2"` or `FEATURES: "mermaid,d2"` |
| **Excalidraw** | Not supported | Not available in mark |

Scale rendering with `MERMAID_SCALE` and `D2_SCALE` inputs (default: 1).

## Inputs

### Required

`action` - `[publish, dry-run, verify]`

- `verify`  - Verify only the conversion from markdown to html
- `dry-run` - Verify in dry-run the conversion will success (connecting to confluence)
- `publish` - Use the given confluence account and push the generated pages

## Required Environment variables

```yaml
CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }} # Confluence base url must be set in GitHub Repo secrets
DOC_DIR: docs # Docs directory based on the git repo root
DOC_DIR_PATTERN: ".*" # Regexp to filter markdown files
MODIFIED_INTERVAL: "0" # Last modified files in minutes
CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }} # CONFLUENCE_USERNAME (Confluence username) must be set in GitHub Repo secrets
CONFLUENCE_PASSWORD: ${{ secrets.CONFLUENCE_PASSWORD }} # CONFLUENCE_PASSWORD (Confluence api key) must be set in GitHub Repo secrets
HEADER_TEMPLATE: "---\n\n**WARNING**: This page is automatically generated from [this source code]({{source_link}})\n\n---\n" # This is a jinja template used as header, source_link is automatically resolved as github source url of the current file
IMAGE_RENDER_SIZE: "900" # Image width in pixels for the Confluence ac:image macro
SOURCE_BRANCH: "main" # Branch name used in the source code link header (avoids broken links from deleted tags/branches)
```

## Optional environment variables

```yaml
FILES: "" # space separated list of file to upload (relative to the repo root directory).
          # if FILES is defined; DOC_DIR, DOC_DIR_PATTERN and MODIFIED_INTERVAL are ignored
FEATURES: "" # Comma-separated mark features: mermaid, d2, mention, mkdocsadmonitions (mermaid and mention are on by default)
MERMAID_SCALE: "" # Scale factor for mermaid diagram rendering
D2_SCALE: "" # Scale factor for d2 diagram rendering
```

## Debug locally

You can run mark2confluence directly using Docker to validate the flow before pushing to CI:

```bash
docker build -t mark2confluence .

docker run --rm \
  -v "$(pwd):/github/workspace" \
  -e INPUT_ACTION="dry-run" \
  -e INPUT_DOC_DIR="docs" \
  -e INPUT_DOC_DIR_PATTERN=".*" \
  -e INPUT_CONFLUENCE_BASE_URL="https://your-instance.atlassian.net/wiki" \
  -e INPUT_CONFLUENCE_USERNAME="your-email@example.com" \
  -e INPUT_CONFLUENCE_PASSWORD="your-api-token" \
  -e INPUT_SOURCE_BRANCH="main" \
  -e GITHUB_WORKSPACE="/github/workspace" \
  -e GITHUB_SERVER_URL="https://github.com" \
  -e GITHUB_REPOSITORY="your-org/your-repo" \
  mark2confluence
```

Use `INPUT_ACTION="verify"` to only validate markdown-to-html conversion without connecting to Confluence. Switch to `"publish"` once you're confident in the output.

To debug a single file:

```bash
docker run --rm \
  -v "$(pwd):/github/workspace" \
  -e INPUT_ACTION="dry-run" \
  -e INPUT_FILES="docs/my-page.md" \
  -e INPUT_CONFLUENCE_BASE_URL="https://your-instance.atlassian.net/wiki" \
  -e INPUT_CONFLUENCE_USERNAME="your-email@example.com" \
  -e INPUT_CONFLUENCE_PASSWORD="your-api-token" \
  -e GITHUB_WORKSPACE="/github/workspace" \
  -e GITHUB_SERVER_URL="https://github.com" \
  -e GITHUB_REPOSITORY="your-org/your-repo" \
  mark2confluence
```

## Example workflow


```yaml
name: Docs Test and Publish

on: pull_request

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Test docs generation
      uses: rarchk/infra-action-mark2confluence@main
      with:
        action: "dry-run"
        DOC_DIR_PATTERN: ".*"
        DOC_DIR: docs
        CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
        CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
        CONFLUENCE_PASSWORD: ${{ secrets.CONFLUENCE_PASSWORD }}

    - name: Publish docs
      uses: rarchk/infra-action-mark2confluence@main
      with:
        action: "publish"
        DOC_DIR_PATTERN: ".*"
        DOC_DIR: docs
        CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
        CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
        CONFLUENCE_PASSWORD: ${{ secrets.CONFLUENCE_PASSWORD }}
```

## Publish with d2 diagrams

```yaml
    - name: Publish with d2 support
      uses: rarchk/infra-action-mark2confluence@main
      with:
        action: "publish"
        DOC_DIR: docs
        FEATURES: "mermaid,d2"
        D2_SCALE: "2"
        CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
        CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
        CONFLUENCE_PASSWORD: ${{ secrets.CONFLUENCE_PASSWORD }}
```

## Verify and publish only changed files

```yaml
name: Docs verification and publish
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
  push:
    branches: main
jobs:
  documentation:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: ${{ github.event_name == 'pull_request' && 1 || 0 }}

    - uses: tj-actions/changed-files@v44
      id: changed-files

    - uses: rarchk/infra-action-mark2confluence@main
      with:
        action: "${{ github.event_name == 'push' && 'publish' || 'dry-run' }}"
        FILES: ${{ steps.changed-files.outputs.all_changed_files }}
        CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
        CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
        CONFLUENCE_PASSWORD: ${{ secrets.CONFLUENCE_PASSWORD }}
```
