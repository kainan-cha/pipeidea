const form = document.getElementById("idea-form");
const input = document.getElementById("command");
const pages = document.getElementById("pages");

function escapeHtml(value) {
  return String(value)
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

function addMetaEntry(text) {
  return createEntry("Note", `<div class="rendered">${escapeHtml(text)}</div>`, "meta-card");
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

function applyStreamEvent(event, entry) {
  if (event.type === "clear") {
    entry.remove();
    pages.innerHTML = "";
    addMetaEntry("Page cleared.");
    return;
  }

  if (event.type === "message") {
    setEntryLabel(entry, event.ok ? "Pipeidea" : "Error");
    setEntryState(entry, event.ok ? "" : "error-card");
    setEntryText(entry, event.output || "");
    return;
  }

  if (event.type === "error") {
    setEntryLabel(entry, "Error");
    setEntryState(entry, "error-card");
    setEntryText(entry, event.output || "Something went wrong.");
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
    body: JSON.stringify({ command })
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
