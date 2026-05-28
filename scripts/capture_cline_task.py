#!/usr/bin/env python3
"""Capture the Cline task folder corresponding to a trial.

After a Cline run for a trial completes, copy Cline's per-task storage folder
(api_conversation_history.json, ui_messages.json, ...) into the trial
directory under `cline_task/`, and additionally emit two human-readable
derivatives:

  - cline_task/transcript.md  — chronological agent actions
  - cline_task/terminal.log   — concatenated commands and their output

By default the script matches the Cline task to the trial by looking inside
each task's `ui_messages.json` for the working-directory line in its first
api_req_started envelope. Newest matching task wins. You can also force a
particular task id with `--task-id`.

Does not modify Cline's storage. Safe to run while Cline is idle.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "trials"

DEFAULT_CLINE_STORAGE = Path.home() / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "tasks"


def find_cline_task_for_trial(trial_dir: Path, storage: Path, explicit_id: str | None) -> Path:
    """Locate the Cline task folder whose first message references `trial_dir`."""
    if explicit_id:
        candidate = storage / explicit_id
        if not candidate.is_dir():
            raise SystemExit(f"No Cline task folder at {candidate}")
        return candidate

    if not storage.is_dir():
        raise SystemExit(f"Cline storage not found: {storage}")

    trial_str = str(trial_dir.resolve())
    matches: list[tuple[int, Path]] = []
    for task_dir in storage.iterdir():
        if not task_dir.is_dir():
            continue
        ui = task_dir / "ui_messages.json"
        if not ui.is_file():
            continue
        try:
            head = ui.read_text(encoding="utf-8", errors="ignore")[:20000]
        except Exception:
            continue
        if trial_str in head:
            try:
                ts = int(task_dir.name)
            except ValueError:
                ts = int(ui.stat().st_mtime * 1000)
            matches.append((ts, task_dir))

    if not matches:
        raise SystemExit(
            f"No Cline task references {trial_str}. "
            f"Pass --task-id <id> to override (folders under {storage})."
        )
    matches.sort(reverse=True)
    return matches[0][1]


def _safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def render_transcript(ui_messages: list[dict]) -> str:
    """Render ui_messages.json into a readable Markdown transcript."""
    lines: list[str] = ["# Cline transcript", ""]
    for m in ui_messages:
        ts = m.get("ts")
        when = datetime.fromtimestamp(ts / 1000).strftime("%H:%M:%S") if ts else "??:??:??"
        kind = m.get("say") or m.get("ask") or m.get("type")

        if m.get("say") == "task":
            lines.append(f"## [{when}] USER TASK")
            lines.append("")
            lines.append("```text")
            lines.append(m.get("text", ""))
            lines.append("```")
            lines.append("")
        elif m.get("say") == "text":
            text = m.get("text", "").strip()
            if text:
                lines.append(f"### [{when}] assistant")
                lines.append("")
                lines.append(text)
                lines.append("")
        elif m.get("say") == "tool":
            d = _safe_json_load(m.get("text", "")) or {}
            tool = d.get("tool", "?")
            path = d.get("path") or d.get("filePath") or ""
            lines.append(f"- [{when}] tool **{tool}** {path}".rstrip())
        elif m.get("say") == "command" or m.get("ask") == "command":
            cmd = (m.get("text") or "").replace("REQ_APP", "").strip()
            lines.append(f"- [{when}] $ `{cmd}`")
        elif m.get("ask") == "command_output":
            out = (m.get("text") or "").strip()
            if out:
                snippet = out if len(out) < 1500 else out[:1500] + "\n... (truncated)"
                lines.append(f"  <details><summary>[{when}] command output</summary>\n\n```\n{snippet}\n```\n\n</details>")
        elif m.get("say") == "task_progress":
            lines.append(f"  - [{when}] progress update")
        elif m.get("say") == "api_req_started":
            d = _safe_json_load(m.get("text", "")) or {}
            tin, tout = d.get("tokensIn"), d.get("tokensOut")
            if tin or tout:
                lines.append(f"  - [{when}] api req (tokens in={tin}, out={tout})")
        elif m.get("say") == "checkpoint_created":
            continue
        else:
            lines.append(f"- [{when}] {kind}")
    return "\n".join(lines) + "\n"


def render_terminal_log(ui_messages: list[dict]) -> str:
    """Extract command+output pairs into a plain text log."""
    out: list[str] = []
    pending_cmd: str | None = None
    for m in ui_messages:
        ts = m.get("ts")
        when = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
        if m.get("say") == "command" or m.get("ask") == "command":
            pending_cmd = (m.get("text") or "").replace("REQ_APP", "").strip()
            out.append(f"\n# [{when}] $ {pending_cmd}")
        elif m.get("ask") == "command_output":
            body = (m.get("text") or "").rstrip()
            if body:
                out.append(body)
    return "\n".join(out) + "\n"


def compute_metrics(ui_messages: list[dict]) -> dict:
    """Lightweight dynamic metrics extracted from the Cline task."""
    tool_counts: dict[str, int] = {}
    files_created: set[str] = set()
    files_edited: set[str] = set()
    files_read: set[str] = set()
    commands: list[str] = []
    tokens_in = tokens_out = 0
    api_calls = 0
    ts_first: int | None = None
    ts_last: int | None = None

    for m in ui_messages:
        ts = m.get("ts")
        if ts:
            ts_first = ts if ts_first is None else min(ts_first, ts)
            ts_last = ts if ts_last is None else max(ts_last, ts)

        if m.get("say") == "tool":
            d = _safe_json_load(m.get("text", "")) or {}
            tool = d.get("tool", "?")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
            path = d.get("path") or d.get("filePath") or ""
            if tool == "newFileCreated" and path:
                files_created.add(path)
            elif tool == "editedExistingFile" and path:
                files_edited.add(path)
            elif tool in ("readFile", "readFileTool") and path:
                files_read.add(path)
        elif m.get("say") == "command" or m.get("ask") == "command":
            cmd = (m.get("text") or "").replace("REQ_APP", "").strip()
            if cmd:
                commands.append(cmd)
        elif m.get("say") == "api_req_started":
            d = _safe_json_load(m.get("text", "")) or {}
            api_calls += 1
            tokens_in += int(d.get("tokensIn") or 0)
            tokens_out += int(d.get("tokensOut") or 0)

    # Did the agent read any of the treatment resources?
    resource_reads = sorted(
        p for p in files_read
        if re.search(r"(?i)(agents\.md|claude\.md|gemini\.md|\.clinerules|copilot-instructions|skills/)", p)
    )

    duration_s = ((ts_last - ts_first) / 1000.0) if (ts_first and ts_last) else None

    return {
        "api_calls": api_calls,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "duration_seconds": round(duration_s, 1) if duration_s is not None else None,
        "tool_counts": tool_counts,
        "commands_run": len(commands),
        "commands": commands,
        "files_created": sorted(files_created),
        "files_edited": sorted(files_edited),
        "files_read": sorted(files_read),
        "resource_files_read": resource_reads,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trial-id", required=True, help="Trial folder name under trials/, e.g. A001")
    ap.add_argument("--task-id", default=None, help="Force a specific Cline task id")
    ap.add_argument("--storage", default=str(DEFAULT_CLINE_STORAGE),
                    help=f"Cline tasks storage directory (default: {DEFAULT_CLINE_STORAGE})")
    ap.add_argument("--force", action="store_true", help="Overwrite existing cline_task/ in the trial")
    args = ap.parse_args()

    trial_dir = TRIALS / args.trial_id
    if not trial_dir.is_dir():
        raise SystemExit(f"Trial not found: {trial_dir}")

    storage = Path(os.path.expanduser(args.storage))
    src = find_cline_task_for_trial(trial_dir, storage, args.task_id)
    dest = trial_dir / "cline_task"
    # A pre-created empty stub (no ui_messages.json) is not treated as a conflict;
    # only error when actual captured data is already present.
    has_data = dest.is_dir() and (dest / "ui_messages.json").is_file()
    if has_data and not args.force:
        raise SystemExit(f"{dest} already has captured data. Use --force to overwrite.")
    if dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    # Always write derivatives + a small provenance file
    ui_path = dest / "ui_messages.json"
    if ui_path.is_file():
        ui_messages = json.loads(ui_path.read_text(encoding="utf-8"))
        (dest / "transcript.md").write_text(render_transcript(ui_messages), encoding="utf-8")
        (dest / "terminal.log").write_text(render_terminal_log(ui_messages), encoding="utf-8")
        metrics = compute_metrics(ui_messages)
        (dest / "cline_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    provenance = {
        "source_task_dir": str(src),
        "source_task_id": src.name,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "trial_id": args.trial_id,
    }
    (dest / "capture_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    print(f"Captured Cline task {src.name} -> {dest}")
    print(f"  transcript:  {dest / 'transcript.md'}")
    print(f"  terminal:    {dest / 'terminal.log'}")
    print(f"  metrics:     {dest / 'cline_metrics.json'}")


if __name__ == "__main__":
    main()
