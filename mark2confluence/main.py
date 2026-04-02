import os
import sys
import re
import subprocess
from datetime import datetime, timedelta
from typing import List, Tuple
import jinja2
from loguru import logger
from supermutes import dot
from pprint import pformat

ACTION_PUBLISH = "publish"
ACTION_DRY_RUN = "dry-run"
ACTION_VERIFY = "verify"

ENV_PREFIXES = {
  "inputs": "INPUT_",
  "github": "GITHUB_",
  "actions": "ACTIONS_",
  "runner": "RUNNER_",
}

# Precompiled regex patterns
SPACE_HEADER_RE = re.compile(r"<!--\s?[Ss]pace:.*-->")
IMAGE_LINK_RE = re.compile(r"!\[(?P<caption>.*?)\]\((?P<image>.*?)\)(?:\s*<!-- width=\d+ -->)?")
COMMENT_LINE_RE = re.compile(r"^<!--.*-->$")
OPENING_COMMENT_RE = re.compile(r"^<!--")
CLOSING_COMMENT_RE = re.compile(r"-->$")

# SANE DEFAULTS
DEFAULT_INPUTS = {
  "DOC_DIR": "",
  "DOC_DIR_PATTERN": ".*",
  "FILES": "",
  "ACTION": ACTION_DRY_RUN,
  "LOGURU_LEVEL": "INFO",
  "HEADER_TEMPLATE": "---\n\n**WARNING**: This page is automatically generated from [this source code]({{ source_link }})\n\n---\n<!-- Include: ac:toc -->\n<!-- Macro: \\!\\[.*\\]\\((.+)\\)\\<\\!\\-\\- width=(.*) \\-\\-\\>\nTemplate: ac:image\nAttachment: ${1}\nWidth: ${2} -->\n\n",
  "MODIFIED_INTERVAL": "0",
  "CONFLUENCE_PASSWORD": "",
  "CONFLUENCE_USERNAME": "",
  "CONFLUENCE_BASE_URL": "",
  "IMAGE_RENDER_SIZE": "900",
  "FEATURES": "",
  "MERMAID_SCALE": "",
  "D2_SCALE": "",
  "SOURCE_BRANCH": "main",
}

DEFAULT_GITHUB = {
  "SERVER_URL": "https://github.com",
  "REPOSITORY": "rarchk/infra-action-mark2confluence",
  "REF_NAME": "main",
  "WORKSPACE": ".",
}

cfg = dot.dotify({
  "inputs": DEFAULT_INPUTS,
  "github": DEFAULT_GITHUB,
  "actions": {},
  "runner": {},
})


def load_vars():
  global cfg
  cfg = dot.dotify(cfg)

  for k, _ in cfg.items():
    logger.info(f"Loading {k} vars from ENV")
    candidate = { key.replace(ENV_PREFIXES[k], ""): value for key, value in os.environ.items() if key.startswith(ENV_PREFIXES[k]) }
    for key, value in candidate.items():
      cfg[k][key] = value

  logger.debug(pformat(cfg))

  if os.getenv("LOGURU_LEVEL"):
    logger.remove()
    logger.add(sys.stderr, level=os.getenv("LOGURU_LEVEL"))


def publish(path: str) -> tuple:
  global cfg
  args = [
    "mark",
    "-u", cfg.inputs.CONFLUENCE_USERNAME,
    "-p", cfg.inputs.CONFLUENCE_PASSWORD,
    "-b", cfg.inputs.CONFLUENCE_BASE_URL,
  ]

  if cfg.inputs.ACTION == ACTION_DRY_RUN:
    args.append("--dry-run")
  elif cfg.inputs.ACTION == ACTION_VERIFY:
    args.append("--compile-only")

  if cfg.inputs.FEATURES:
    for feature in cfg.inputs.FEATURES.split(","):
      args.extend(["--features", feature.strip()])

  if cfg.inputs.MERMAID_SCALE:
    args.extend(["--mermaid-scale", cfg.inputs.MERMAID_SCALE])

  if cfg.inputs.D2_SCALE:
    args.extend(["--d2-scale", cfg.inputs.D2_SCALE])

  args.extend(["--color", "never", "--log-level", "trace", "-f", path])

  try:
    result = subprocess.run(args, capture_output=True, timeout=120)
  except subprocess.TimeoutExpired as e:
    logger.error(f"Exec timeout: {path}")
    return False, e.stderr or b"timeout"

  if result.returncode != 0:
    return False, result.stderr
  return True, None


def has_mark_headers(path: str) -> bool:
  with open(path, 'r') as f:
    for line in f:
      if SPACE_HEADER_RE.search(line):
        return True
  return False

class MultilineCommentIsOpenException(Exception):
    pass

def inject_header_before_first_line_of_content(path: str, header: str) -> Tuple[List[str], int]:
  with open(path, 'r') as f:
    file_lines = f.readlines()

  beginning_of_content_index = 0
  is_inside_multiline_comment = False
  for line in file_lines:
      stripped = line.strip()
      is_single_comment = bool(COMMENT_LINE_RE.match(stripped))
      if not is_single_comment and OPENING_COMMENT_RE.match(stripped):
        is_inside_multiline_comment = True
      elif not is_single_comment and CLOSING_COMMENT_RE.match(stripped):
        is_inside_multiline_comment = False
      elif stripped != "" and not is_inside_multiline_comment and not is_single_comment:
        break
      beginning_of_content_index += 1

  if is_inside_multiline_comment:
    raise MultilineCommentIsOpenException(f"The file {path} has multiline comments in it that are not closed.")

  file_lines.insert(beginning_of_content_index, header)
  with open(path, "w") as f:
    f.writelines(file_lines)
  return (file_lines, beginning_of_content_index)


def get_files_by_doc_dir_pattern() -> list:
  global cfg

  try:
    pattern = re.compile(cfg.inputs.DOC_DIR_PATTERN)
  except re.error as e:
    logger.error(f"Setup error, DOC_DIR_PATTERN: {e}")
    exit(1)

  topdir = os.path.join(cfg.github.WORKSPACE, cfg.inputs.DOC_DIR)
  logger.info(f"Searching into {topdir}")

  modified_interval = int(cfg.inputs.MODIFIED_INTERVAL)
  filtered_files = []
  for root, dirs, files in os.walk(topdir, topdown=True, followlinks=False):
    for file in files:
      path = os.path.join(root, file)
      if pattern.match(path) is None:
        logger.info(f"Doesn't match DOC_DIR_PATTERN, skipping {path}")
      elif modified_interval > 0:
        mtime = datetime.fromtimestamp(os.stat(path).st_mtime)
        cutoff = datetime.now() - timedelta(minutes=modified_interval)
        if mtime < cutoff:
          logger.info(f"Is too old, skipping ({mtime}) {path}")
        else:
          filtered_files.append(path)
      else:
        filtered_files.append(path)

  return filtered_files

def check_header_template(header_template: str):
  try:
    return jinja2.Template(header_template)
  except jinja2.exceptions.TemplateError as e:
    logger.error(f"Setup error, HEADER_TEMPLATE: {e}")
    exit(1)

def update_image_link(path: str, size: str) -> int:
    with open(path, 'r') as fd:
      content = fd.read()
    replacement = rf"![\g<caption>](\g<image>)<!-- width={size} -->"
    result = IMAGE_LINK_RE.sub(replacement, content)
    with open(path, 'w') as fd:
      fd.write(result)
    return 0


def main() -> int:
  global cfg
  load_vars()

  tpl = check_header_template(cfg.inputs.HEADER_TEMPLATE)

  files = []
  if cfg.inputs.FILES:
    files = list(map(
      lambda file: f"{cfg.github.WORKSPACE}/{file}",
      cfg.inputs.FILES.split(" ")
    ))
  else:
    files = get_files_by_doc_dir_pattern()

  logger.info(f"Files to be processed: {', '.join(files)}")

  source_branch = cfg.inputs.SOURCE_BRANCH if cfg.inputs.SOURCE_BRANCH else "main"

  status = {}
  for path in files:
    if path.endswith('.md') and has_mark_headers(path):
      logger.info(f"Processing file {path}")
      relative_path = path.replace(cfg.github.WORKSPACE, '').lstrip('/')
      source_link = f"{cfg.github.SERVER_URL}/{cfg.github.REPOSITORY}/blob/{source_branch}/{relative_path}"
      header = tpl.render(source_link=source_link)

      inject_header_before_first_line_of_content(path, header)
      update_image_link(path, cfg.inputs.IMAGE_RENDER_SIZE)
      status[path] = publish(path)
    else:
      logger.info(f"Skipping headerless or non md file {path}")

  rc = 0
  for k, v in status.items():
    if not v[0]:
      rc += 1
      logger.error(f"{k} {v[1]}")
  logger.info(f"Success: {len(status)-rc} | Failures: {rc} | Total: {len(status)}")
  return rc

if __name__ == "__main__":
  exit(main())
