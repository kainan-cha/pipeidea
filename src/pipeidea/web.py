"""Minimal browser UI for the creative Pipeidea flow."""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from textwrap import dedent

from pipeidea.config import load_config
from pipeidea.core import run_creative
from pipeidea.providers.registry import AVAILABLE_PROVIDERS
from pipeidea.soul.profiles import create_profile, ensure_defaults, list_profiles, load_full_profile


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pipeidea</title>
  <style>
    :root {
      --paper: #f7f0e3;
      --paper-deep: #efe3cf;
      --ink: #2f241c;
      --muted: #786556;
      --line: rgba(80, 57, 39, 0.14);
      --accent: #8e3b2d;
      --accent-soft: rgba(142, 59, 45, 0.08);
      --danger: #9d2f24;
      --shadow: 0 20px 70px rgba(85, 61, 36, 0.16);
    }

    * { box-sizing: border-box; }

    html, body { height: 100%; }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top, rgba(186, 151, 111, 0.18), transparent 28rem),
        linear-gradient(180deg, #f3eadb, #eadcc4);
      color: var(--ink);
      font-family: "Times New Roman", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      display: flex;
      justify-content: center;
      padding: 28px 16px;
    }

    .book {
      width: min(100%, 1040px);
      min-height: calc(100vh - 56px);
      background:
        linear-gradient(90deg, rgba(117, 83, 56, 0.08), transparent 18px),
        linear-gradient(180deg, rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0.12)),
        var(--paper);
      border: 1px solid rgba(91, 68, 48, 0.16);
      border-radius: 28px;
      box-shadow: var(--shadow);
      display: grid;
      grid-template-rows: 1fr auto;
      overflow: hidden;
      position: relative;
    }

    .book::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image: linear-gradient(rgba(122, 96, 71, 0.08) 1px, transparent 1px);
      background-size: 100% 2rem;
      opacity: 0.35;
      pointer-events: none;
    }

    .composer, #pages {
      position: relative;
      z-index: 1;
    }

    #pages {
      overflow: auto;
      padding: 26px 34px;
    }

    .entry {
      margin: 0 auto 26px;
      max-width: 46rem;
      animation: fadeUp 180ms ease-out;
    }

    .entry-label {
      margin-bottom: 8px;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .entry-card {
      background: rgba(255, 252, 246, 0.9);
      border: 1px solid rgba(91, 68, 48, 0.12);
      border-radius: 18px;
      padding: 18px 20px;
      box-shadow: 0 8px 24px rgba(101, 71, 45, 0.05);
    }

    .entry-card.prompt-card {
      background: rgba(142, 59, 45, 0.05);
      border-color: rgba(142, 59, 45, 0.12);
    }

    .entry-card.meta-card {
      background: transparent;
      border-style: dashed;
      color: var(--muted);
      font-style: italic;
    }

    .entry-card.error-card {
      background: rgba(157, 47, 36, 0.06);
      border-color: rgba(157, 47, 36, 0.16);
      color: var(--danger);
    }

    .entry-card.loading-card {
      color: var(--muted);
      font-style: italic;
    }

    .user-line {
      font-size: 1.12rem;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .rendered {
      font-size: 1.1rem;
      line-height: 1.7;
      word-break: break-word;
    }

    .rendered > :first-child { margin-top: 0; }
    .rendered > :last-child { margin-bottom: 0; }

    .rendered h1,
    .rendered h2,
    .rendered h3,
    .rendered h4 {
      line-height: 1.15;
      margin: 1.15em 0 0.45em;
      font-weight: 600;
    }

    .rendered h1 { font-size: 2rem; }
    .rendered h2 { font-size: 1.55rem; }
    .rendered h3 { font-size: 1.25rem; }
    .rendered h4 { font-size: 1.08rem; }

    .rendered p { margin: 0.8em 0; }

    .rendered ul,
    .rendered ol {
      margin: 0.8em 0 0.8em 1.3em;
      padding: 0;
    }

    .rendered li { margin: 0.35em 0; }

    .rendered blockquote {
      margin: 1em 0;
      padding: 0.1em 0 0.1em 1.1em;
      border-left: 3px solid rgba(142, 59, 45, 0.3);
      color: var(--muted);
      font-style: italic;
    }

    .rendered hr {
      border: 0;
      border-top: 1px solid rgba(91, 68, 48, 0.14);
      margin: 1.3em 0;
    }

    .rendered code {
      font-family: "Courier New", "SFMono-Regular", monospace;
      font-size: 0.9em;
      background: rgba(111, 79, 48, 0.08);
      padding: 0.08em 0.3em;
      border-radius: 5px;
    }

    .rendered pre {
      overflow: auto;
      padding: 14px 16px;
      border-radius: 12px;
      background: #f0e2cb;
      border: 1px solid rgba(91, 68, 48, 0.1);
      line-height: 1.45;
      margin: 1em 0;
    }

    .rendered pre code {
      background: transparent;
      padding: 0;
      border-radius: 0;
    }

    .rendered a {
      color: var(--accent);
      text-decoration-thickness: 1px;
      text-underline-offset: 2px;
    }

    .composer {
      padding: 18px 34px 28px;
      border-top: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(247, 240, 227, 0.7), rgba(239, 227, 207, 0.95));
    }

    .composer-label {
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 0.98rem;
    }

    .input-shell {
      display: block;
      padding: 16px 18px;
      border: 1px solid rgba(91, 68, 48, 0.16);
      border-radius: 18px;
      background: rgba(255, 252, 246, 0.84);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
    }

    .input-shell:focus-within {
      border-color: rgba(142, 59, 45, 0.34);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.75),
        0 0 0 4px rgba(142, 59, 45, 0.08);
    }

    #command {
      width: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--ink);
      font: inherit;
      font-size: 1.14rem;
      line-height: 1.5;
    }

    #command::placeholder {
      color: #9a8878;
    }

    .hint {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.94rem;
    }

    @keyframes fadeUp {
      from {
        opacity: 0;
        transform: translateY(6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @media (max-width: 700px) {
      body { padding: 12px; }
      .book {
        min-height: calc(100vh - 24px);
        border-radius: 20px;
      }
      .composer, #pages {
        padding-left: 18px;
        padding-right: 18px;
      }
      #pages { padding-top: 22px; }
    }
  </style>
</head>
<body>
  <main class="book">
    <section id="pages" aria-live="polite"></section>
    <footer class="composer">
      <form id="idea-form">
        <div class="composer-label">Start with a seed, or type <strong>help</strong> to see commands.</div>
        <label class="input-shell" for="command">
          <input id="command" autocomplete="off" placeholder='Try "public libraries" or "collide &quot;jazz&quot; &quot;tax policy&quot;"' />
        </label>
      </form>
      <div class="hint">Enter submits. <code>clear</code> resets the page.</div>
    </footer>
  </main>

  <script>
    const form = document.getElementById("idea-form");
    const input = document.getElementById("command");
    const pages = document.getElementById("pages");

    function escapeHtml(value) {
      return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function renderInlineMarkdown(value) {
      const codeSpans = [];
      let text = escapeHtml(value);

      text = text.replace(/`([^`]+)`/g, (_, code) => {
        const token = `@@INLINECODE${codeSpans.length}@@`;
        codeSpans.push(`<code>${code}</code>`);
        return token;
      });

      text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_match, label, url) => {
        return `<a href="${url}" target="_blank" rel="noreferrer">${label}</a>`;
      });
      text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      text = text.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");

      for (let index = 0; index < codeSpans.length; index += 1) {
        text = text.replace(`@@INLINECODE${index}@@`, codeSpans[index]);
      }

      return text;
    }

    function renderMarkdown(value) {
      const normalized = String(value || "").replace(/\r\n?/g, "\n");
      const codeBlocks = [];
      let text = normalized.replace(/```([\w-]*)\n?([\s\S]*?)```/g, (_match, language, code) => {
        const token = `@@CODEBLOCK${codeBlocks.length}@@`;
        const languageAttr = language ? ` data-lang="${escapeHtml(language)}"` : "";
        codeBlocks.push(`<pre><code${languageAttr}>${escapeHtml(code.replace(/\n$/, ""))}</code></pre>`);
        return token;
      });

      const blocks = text.split(/\n{2,}/);
      const renderedBlocks = blocks.map((block) => {
        const trimmed = block.trim();
        if (!trimmed) {
          return "";
        }

        if (/^@@CODEBLOCK\d+@@$/.test(trimmed)) {
          return trimmed;
        }

        if (/^(?:-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
          return "<hr>";
        }

        const heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
        if (heading) {
          const level = heading[1].length;
          return `<h${level}>${renderInlineMarkdown(heading[2].trim())}</h${level}>`;
        }

        const blockquoteLines = trimmed.split("\n");
        if (blockquoteLines.every((line) => line.trim().startsWith(">"))) {
          const quote = blockquoteLines
            .map((line) => line.replace(/^\s*>\s?/, ""))
            .join("\n");
          return `<blockquote>${renderMarkdown(quote)}</blockquote>`;
        }

        const unorderedLines = trimmed.split("\n");
        if (unorderedLines.every((line) => /^\s*[-*]\s+/.test(line))) {
          const items = unorderedLines
            .map((line) => line.replace(/^\s*[-*]\s+/, ""))
            .map((line) => `<li>${renderInlineMarkdown(line)}</li>`)
            .join("");
          return `<ul>${items}</ul>`;
        }

        const orderedLines = trimmed.split("\n");
        if (orderedLines.every((line) => /^\s*\d+\.\s+/.test(line))) {
          const items = orderedLines
            .map((line) => line.replace(/^\s*\d+\.\s+/, ""))
            .map((line) => `<li>${renderInlineMarkdown(line)}</li>`)
            .join("");
          return `<ol>${items}</ol>`;
        }

        const paragraph = trimmed
          .split("\n")
          .map((line) => renderInlineMarkdown(line))
          .join("<br>");
        return `<p>${paragraph}</p>`;
      });

      let html = renderedBlocks.filter(Boolean).join("\n");
      for (let index = 0; index < codeBlocks.length; index += 1) {
        html = html.replace(`@@CODEBLOCK${index}@@`, codeBlocks[index]);
      }
      return html || "<p></p>";
    }

    function createEntry(label, innerHtml, cardClass) {
      const entry = document.createElement("article");
      entry.className = "entry";
      entry.innerHTML = `
        <div class="entry-label">${escapeHtml(label)}</div>
        <div class="entry-card ${cardClass}">${innerHtml}</div>
      `;
      pages.appendChild(entry);
      pages.scrollTop = pages.scrollHeight;
      return entry;
    }

    function addUserEntry(text) {
      return createEntry("Prompt", `<div class="user-line">${escapeHtml(text)}</div>`, "prompt-card");
    }

    function addAssistantPlaceholder() {
      return createEntry("Pipeidea", `<div class="rendered">Thinking...</div>`, "loading-card");
    }

    function setEntryLabel(entry, label) {
      entry.querySelector(".entry-label").textContent = label;
    }

    function setEntryState(entry, cardClass) {
      const card = entry.querySelector(".entry-card");
      card.className = "entry-card";
      if (cardClass) {
        card.classList.add(cardClass);
      }
    }

    function setEntryText(entry, text) {
      const node = entry.querySelector(".rendered");
      node.dataset.rawText = text;
      node.innerHTML = renderMarkdown(text);
      pages.scrollTop = pages.scrollHeight;
    }

    function appendEntryText(entry, text) {
      const node = entry.querySelector(".rendered");
      let rawText = node.dataset.rawText || "";
      if (rawText === "Thinking...") {
        rawText = "";
      }
      rawText += text;
      node.dataset.rawText = rawText;
      node.innerHTML = renderMarkdown(rawText);
      pages.scrollTop = pages.scrollHeight;
    }

    function addMetaEntry(text) {
      return createEntry("Note", `<div class="rendered">${escapeHtml(text)}</div>`, "meta-card");
    }

    function applyStreamEvent(event, entry) {
      if (event.type === "clear") {
        entry.remove();
        pages.innerHTML = "";
        addMetaEntry("Page cleared.");
        return;
      }

      if (event.type === "meta") {
        setEntryLabel(entry, "Note");
        setEntryState(entry, "meta-card");
        setEntryText(entry, event.output || "");
        return;
      }

      if (event.type === "error") {
        setEntryLabel(entry, "Error");
        setEntryState(entry, "error-card");
        setEntryText(entry, event.output || "Something went wrong.");
        return;
      }

      if (event.type === "message") {
        setEntryLabel(entry, event.ok ? "Pipeidea" : "Error");
        setEntryState(entry, event.ok ? "" : "error-card");
        setEntryText(entry, event.output || "");
        return;
      }

      if (event.type === "start") {
        setEntryLabel(entry, "Pipeidea");
        setEntryState(entry, "loading-card");
        setEntryText(entry, event.output || "Thinking...");
        return;
      }

      if (event.type === "chunk") {
        setEntryLabel(entry, "Pipeidea");
        setEntryState(entry, "");
        appendEntryText(entry, event.delta || "");
        return;
      }

      if (event.type === "done") {
        setEntryLabel(entry, event.ok ? "Pipeidea" : "Error");
        setEntryState(entry, event.ok ? "" : "error-card");
        if (event.output && !entry.querySelector(".rendered").textContent.trim()) {
          setEntryText(entry, event.output);
        }
      }
    }

    async function streamCommand(command, entry) {
      const response = await fetch("/api/command/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.output || payload.error || "Request failed.");
      }

      if (!response.body) {
        throw new Error("Streaming response body missing.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        let lineBreak = buffer.indexOf("\n");
        while (lineBreak >= 0) {
          const line = buffer.slice(0, lineBreak).trim();
          buffer = buffer.slice(lineBreak + 1);
          if (line) {
            applyStreamEvent(JSON.parse(line), entry);
          }
          lineBreak = buffer.indexOf("\n");
        }

        if (done) {
          break;
        }
      }

      if (buffer.trim()) {
        applyStreamEvent(JSON.parse(buffer), entry);
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const command = input.value.trim();
      if (!command) {
        return;
      }

      addUserEntry(command);
      input.value = "";
      input.disabled = true;
      const assistantEntry = addAssistantPlaceholder();

      try {
        await streamCommand(command, assistantEntry);
      } catch (error) {
        setEntryLabel(assistantEntry, "Error");
        setEntryState(assistantEntry, "error-card");
        setEntryText(assistantEntry, error.message || "Something went wrong.");
      } finally {
        input.disabled = false;
        input.focus();
      }
    });

    input.focus();
  </script>
</body>
</html>
"""


@dataclass(frozen=True)
class CommandResponse:
    """Response payload returned to the browser."""

    ok: bool
    output: str
    clear: bool = False


class CommandParser(argparse.ArgumentParser):
    """Parser that raises ValueError instead of exiting the process."""

    def error(self, message: str) -> None:
        raise ValueError(message)


def _build_parser() -> CommandParser:
    parser = CommandParser(prog="pipeidea", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    bloom = subparsers.add_parser("bloom", add_help=False)
    bloom.add_argument("seed", nargs="+")
    bloom.add_argument("-P", "--profile", default=None)
    bloom.add_argument("-p", "--provider")
    bloom.add_argument("-w", "--wild", action="store_true")
    bloom.add_argument("--forage", action="store_true")

    collide = subparsers.add_parser("collide", add_help=False)
    collide.add_argument("seed1")
    collide.add_argument("seed2")
    collide.add_argument("-P", "--profile", default=None)
    collide.add_argument("-p", "--provider")
    collide.add_argument("-w", "--wild", action="store_true")

    profile = subparsers.add_parser("profile", add_help=False)
    profile_subparsers = profile.add_subparsers(dest="profile_command")
    profile_subparsers.add_parser("list", add_help=False)

    profile_create = profile_subparsers.add_parser("create", add_help=False)
    profile_create.add_argument("name")

    profile_show = profile_subparsers.add_parser("show", add_help=False)
    profile_show.add_argument("name")

    return parser


def _help_text() -> str:
    providers = ", ".join(AVAILABLE_PROVIDERS)
    return dedent(
        f"""\
        pipeidea idea book

        Write a plain sentence to bloom it into an idea draft, or use a command.

        Commands
          bloom "seed text" [--forage] [-w] [-P PROFILE] [-p PROVIDER]
          collide "first input" "second input" [-w] [-P PROFILE] [-p PROVIDER]
          profile list
          profile create NAME
          profile show NAME
          clear
          help

        Notes
          If you just type a phrase with no command, it will be treated like bloom.
          Quote multi-word inputs when you want strict command parsing.
          Available providers: {providers}
        """
    ).strip()


def _format_profile(profile_name: str, files: dict[str, str]) -> str:
    parts = [f"profile: {profile_name}"]
    for filename, content in sorted(files.items()):
        parts.append(f"\n[{filename}]\n{content.strip()}")
    return "\n".join(parts).strip()


def _parse_command_text(command_text: str) -> tuple[argparse.Namespace | None, CommandResponse | None]:
    """Parse browser command text into argparse namespace or an immediate response."""
    command_text = command_text.strip()
    if not command_text:
        return None, CommandResponse(ok=True, output="")

    if command_text in {"help", "--help", "-h"}:
        return None, CommandResponse(ok=True, output=_help_text())

    if command_text == "clear":
        return None, CommandResponse(ok=True, output="", clear=True)

    parser = _build_parser()

    try:
        argv = shlex.split(command_text)
    except ValueError:
        argv = ["bloom", command_text]

    try:
        args = parser.parse_args(argv)
    except ValueError as exc:
        first_word = command_text.split(maxsplit=1)[0].lower() if command_text.split() else ""
        known_commands = {"bloom", "collide", "profile", "help", "clear", "--help", "-h"}
        if first_word and first_word not in known_commands:
            try:
                args = parser.parse_args(["bloom", command_text])
            except ValueError:
                return None, CommandResponse(ok=False, output=f"{exc}\n\n{_help_text()}")
        else:
            return None, CommandResponse(ok=False, output=f"{exc}\n\n{_help_text()}")

    if not getattr(args, "command", None):
        return None, CommandResponse(ok=False, output=_help_text())

    return args, None


async def _execute_parsed_command(
    args: argparse.Namespace,
    cfg,
    on_chunk: Callable[[str], None] | None = None,
) -> CommandResponse:
    """Execute a parsed command."""
    if args.command == "bloom":
        mode = "forage" if args.forage else "bloom"
        output = await run_creative(
            seeds=[" ".join(args.seed)],
            mode=mode,
            profile=args.profile or cfg.default_profile,
            provider_name=args.provider,
            wild=args.wild,
            on_chunk=on_chunk,
        )
        return CommandResponse(ok=True, output=output.strip())

    if args.command == "collide":
        output = await run_creative(
            seeds=[args.seed1, args.seed2],
            mode="collision",
            profile=args.profile or cfg.default_profile,
            provider_name=args.provider,
            wild=args.wild,
            on_chunk=on_chunk,
        )
        return CommandResponse(ok=True, output=output.strip())

    if args.command == "profile":
        if args.profile_command == "list":
            profiles = list_profiles(cfg)
            default = cfg.default_profile
            lines = [f"{name}{' (default)' if name == default else ''}" for name in profiles]
            return CommandResponse(ok=True, output="\n".join(lines) or "No profiles found.")

        if args.profile_command == "create":
            path = create_profile(cfg, args.name)
            return CommandResponse(
                ok=True,
                output=(
                    f"Created profile '{args.name}' at {path}\n"
                    "Edit markdown files to override default behavior."
                ),
            )

        if args.profile_command == "show":
            files = load_full_profile(cfg, args.name)
            if not files:
                return CommandResponse(ok=False, output=f"Profile '{args.name}' not found.")
            return CommandResponse(ok=True, output=_format_profile(args.name, files))

    return CommandResponse(ok=False, output=_help_text())


async def execute_command(command_text: str) -> CommandResponse:
    """Execute a browser command and return text output."""
    args, immediate = _parse_command_text(command_text)
    if immediate is not None:
        return immediate

    cfg = load_config()
    ensure_defaults(cfg)

    try:
        return await _execute_parsed_command(args, cfg)
    except Exception as exc:
        return CommandResponse(ok=False, output=f"Error: {exc}")


async def stream_command_events(
    command_text: str,
    emit: Callable[[dict[str, object]], None],
) -> None:
    """Execute a browser command while emitting incremental events."""
    args, immediate = _parse_command_text(command_text)
    if immediate is not None:
        if immediate.clear:
            emit({"type": "clear", "ok": True, "output": ""})
        else:
            emit({"type": "message", "ok": immediate.ok, "output": immediate.output})
        emit(
            {
                "type": "done",
                "ok": immediate.ok,
                "output": immediate.output,
                "clear": immediate.clear,
            }
        )
        return

    cfg = load_config()
    ensure_defaults(cfg)

    try:
        if args.command in {"bloom", "collide"}:
            emit({"type": "start", "ok": True, "output": "Thinking..."})
            chunks: list[str] = []

            def on_chunk(chunk: str) -> None:
                chunks.append(chunk)
                emit({"type": "chunk", "delta": chunk})

            response = await _execute_parsed_command(args, cfg, on_chunk=on_chunk)
            emit({"type": "done", "ok": response.ok, "output": "".join(chunks) or response.output})
            return

        response = await _execute_parsed_command(args, cfg)
        emit({"type": "message", "ok": response.ok, "output": response.output})
        emit({"type": "done", "ok": response.ok, "output": response.output})
    except Exception as exc:
        error_text = f"Error: {exc}"
        emit({"type": "error", "ok": False, "output": error_text})
        emit({"type": "done", "ok": False, "output": error_text})


class PipeideaWebHandler(BaseHTTPRequestHandler):
    """HTTP handler serving the browser idea book."""

    server_version = "pipeidea-web/0.3"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if self.path.rstrip("/") in {"", "/"}:
            self._send_html(INDEX_HTML)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if self.path == "/api/command":
            self._handle_command()
            return
        if self.path == "/api/command/stream":
            self._handle_command_stream()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _handle_command(self) -> None:
        data = self._read_json_body()
        if data is None:
            return

        command_text = str(data.get("command", "")).strip()
        if not command_text:
            self._send_json(
                {"ok": False, "output": "A prompt or command is required."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            response = asyncio.run(execute_command(command_text))
        except Exception as exc:
            self._send_json(
                {"ok": False, "output": f"Error: {exc}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        status = HTTPStatus.OK if response.ok else HTTPStatus.BAD_REQUEST
        self._send_json(
            {"ok": response.ok, "output": response.output, "clear": response.clear},
            status,
        )

    def _handle_command_stream(self) -> None:
        data = self._read_json_body()
        if data is None:
            return

        command_text = str(data.get("command", "")).strip()
        if not command_text:
            self._send_json(
                {"ok": False, "output": "A prompt or command is required."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

        def emit(payload: dict[str, object]) -> None:
            encoded = (json.dumps(payload, ensure_ascii=True) + "\n").encode("utf-8")
            self.wfile.write(encoded)
            self.wfile.flush()

        try:
            asyncio.run(stream_command_events(command_text, emit))
        except BrokenPipeError:
            return
        except ConnectionResetError:
            return
        except Exception as exc:
            try:
                emit({"type": "error", "ok": False, "output": f"Error: {exc}"})
                emit({"type": "done", "ok": False, "output": f"Error: {exc}"})
            except Exception:
                return

    def _read_json_body(self) -> dict[str, object] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length)

        try:
            return json.loads(payload.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "output": "Invalid JSON payload."}, HTTPStatus.BAD_REQUEST)
            return None

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def serve_web_ui(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the keyboard-driven web UI server."""
    server = ThreadingHTTPServer((host, port), PipeideaWebHandler)
    address = f"http://{host}:{port}"
    print(f"pipeidea web ui running at {address}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
