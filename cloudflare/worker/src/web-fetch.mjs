/**
 * Detect URLs in seeds, fetch their content, and extract readable text.
 */

const URL_RE = /https?:\/\/[^\s<>"']+/gi;
const MAX_CONTENT_CHARS = 2000;

const SKIP_TAGS = new Set([
  "script", "style", "noscript", "svg", "head", "meta", "link",
  "iframe", "object", "embed", "applet",
]);

/**
 * Minimal HTML→text extraction using regex (no DOM parser in CF workers).
 * Returns { title, text }.
 */
function htmlToText(html) {
  // Extract <title>.
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const title = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, "").trim() : "";

  // Remove skip tags and their content.
  let cleaned = html;
  for (const tag of SKIP_TAGS) {
    const re = new RegExp(`<${tag}[\\s>][\\s\\S]*?</${tag}>`, "gi");
    cleaned = cleaned.replace(re, "");
  }

  // Replace block-level closing tags with newlines.
  cleaned = cleaned.replace(/<\/(p|div|h[1-6]|li|tr|blockquote|section|article|header|footer|td|th)>/gi, "\n");
  cleaned = cleaned.replace(/<br\s*\/?>/gi, "\n");

  // Strip remaining tags.
  cleaned = cleaned.replace(/<[^>]+>/g, " ");

  // Decode common HTML entities.
  cleaned = cleaned
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");

  // Collapse whitespace.
  const lines = cleaned.split("\n").map(l => l.trim()).filter(Boolean);
  const text = lines.join("\n");

  return { title, text };
}

/**
 * Split seeds into [cleanSeeds, urls].
 */
export function extractUrls(seeds) {
  const urls = [];
  const clean = [];
  for (const seed of seeds) {
    const found = seed.match(URL_RE) || [];
    urls.push(...found);
    const remainder = seed.replace(URL_RE, "").trim();
    if (remainder) clean.push(remainder);
  }
  return [clean, urls];
}

/**
 * Fetch a URL and return extracted text, or null on failure.
 */
async function fetchUrlContent(url, { timeout = 10000 } = {}) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    const resp = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      },
      redirect: "follow",
    });
    clearTimeout(timer);

    if (!resp.ok) return null;

    const contentType = resp.headers.get("content-type") || "";
    if (!contentType.includes("text/html") && !contentType.includes("text/plain")) {
      return null;
    }

    const html = await resp.text();
    const { title, text: body } = htmlToText(html);
    if (!body) return null;

    // Truncate to budget.
    let truncated = body.slice(0, MAX_CONTENT_CHARS);
    if (body.length > MAX_CONTENT_CHARS) {
      // Cut at last sentence boundary (CJK or Latin period).
      let lastPeriod = truncated.lastIndexOf("\u3002"); // CJK period
      if (lastPeriod < 0) lastPeriod = truncated.lastIndexOf(".");
      if (lastPeriod > MAX_CONTENT_CHARS / 2) {
        truncated = truncated.slice(0, lastPeriod + 1);
      }
    }

    let header = `Source: ${url}`;
    if (title) header += `\nTitle: ${title}`;
    return `${header}\n\n${truncated}`;
  } catch {
    return null;
  }
}

/**
 * Process seeds: extract URLs, fetch their content.
 * Returns { effectiveSeeds, webStimuli }.
 */
export async function fetchSeedUrls(seeds) {
  const [cleanSeeds, urls] = extractUrls(seeds);
  if (urls.length === 0) return { effectiveSeeds: seeds, webStimuli: [] };

  // Fetch all URLs concurrently.
  const results = await Promise.all(urls.map(u => fetchUrlContent(u)));
  const webStimuli = results.filter(r => r !== null);

  let effectiveSeeds = cleanSeeds;

  // If removing URLs left no seeds, derive from first fetched title.
  if (effectiveSeeds.length === 0 && webStimuli.length > 0) {
    for (const stim of webStimuli) {
      for (const line of stim.split("\n")) {
        if (line.startsWith("Title:")) {
          const titleText = line.slice("Title:".length).trim();
          if (titleText) {
            effectiveSeeds = [titleText];
            break;
          }
        }
      }
      if (effectiveSeeds.length > 0) break;
    }
    // Fallback: use domain.
    if (effectiveSeeds.length === 0 && urls.length > 0) {
      try {
        effectiveSeeds = [new URL(urls[0]).hostname];
      } catch {
        effectiveSeeds = [urls[0]];
      }
    }
  }

  return { effectiveSeeds, webStimuli };
}
