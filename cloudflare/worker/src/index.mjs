import { AVAILABLE_PROVIDERS, streamFromProvider } from "./providers.mjs";
import { parseCommand, helpText } from "./commands.mjs";
import { composePrompt, composeUserMessage, formatProfile, listProfiles } from "./prompt.mjs";
import { getRandomStimulus } from "./random-stimulus.mjs";
import { assessPromptSensitivity } from "./sensitivity.mjs";

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}

async function emit(writer, payload) {
  const encoded = new TextEncoder().encode(`${JSON.stringify(payload)}\n`);
  await writer.write(encoded);
}

async function handleStreamRequest(request, env, ctx) {
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ ok: false, output: "Invalid JSON payload." }, 400);
  }

  const commandText = String(body?.command || "").trim();
  if (!commandText) {
    return jsonResponse({ ok: false, output: "A prompt or command is required." }, 400);
  }

  let parsed;
  try {
    parsed = parseCommand(commandText);
  } catch (error) {
    return jsonResponse(
      {
        ok: false,
        output: `${error.message}\n\n${helpText(AVAILABLE_PROVIDERS)}`
      },
      400
    );
  }

  if (parsed.type === "help") {
    return streamSingleMessage({ type: "message", ok: true, output: helpText(AVAILABLE_PROVIDERS) });
  }
  if (parsed.type === "clear") {
    return streamImmediate([
      { type: "clear", ok: true, output: "" },
      { type: "done", ok: true, output: "", clear: true }
    ]);
  }
  if (parsed.type === "message") {
    return streamSingleMessage({ type: "message", ok: parsed.ok, output: parsed.output });
  }
  if (parsed.type === "profile_list") {
    const defaultProfile = env.PIPEIDEA_DEFAULT_PROFILE || "default";
    const output = listProfiles()
      .map((name) => `${name}${name === defaultProfile ? " (default)" : ""}`)
      .join("\n");
    return streamSingleMessage({ type: "message", ok: true, output });
  }
  if (parsed.type === "profile_show") {
    try {
      return streamSingleMessage({ type: "message", ok: true, output: formatProfile(parsed.name) });
    } catch (error) {
      return streamSingleMessage({ type: "error", ok: false, output: `Error: ${error.message}` });
    }
  }

  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();

  ctx.waitUntil((async () => {
    try {
      const profile = parsed.profile || env.PIPEIDEA_DEFAULT_PROFILE || "default";
      const randomStimulus = getRandomStimulus();
      const sensitivity = assessPromptSensitivity(parsed.seeds, parsed.mode);
      const prompt = composePrompt({
        profile,
        mode: parsed.mode,
        randomStimulus,
        runtimeGuidance: sensitivity.reason
      });
      const userMessage = composeUserMessage(parsed.seeds, parsed.mode);

      await emit(writer, { type: "start", ok: true, output: "Thinking..." });

      let fullOutput = "";
      for await (
        const chunk of streamFromProvider(
          env,
          parsed.provider,
          prompt.systemPrompt,
          userMessage,
          parsed.wild,
          sensitivity
        )
      ) {
        fullOutput += chunk;
        await emit(writer, { type: "chunk", delta: chunk });
      }

      await emit(writer, { type: "done", ok: true, output: fullOutput });
    } catch (error) {
      const message = `Error: ${error.message || String(error)}`;
      await emit(writer, { type: "error", ok: false, output: message });
      await emit(writer, { type: "done", ok: false, output: message });
    } finally {
      await writer.close();
    }
  })());

  return new Response(readable, {
    headers: {
      "content-type": "application/x-ndjson; charset=utf-8",
      "cache-control": "no-cache",
      "x-accel-buffering": "no"
    }
  });
}

function streamSingleMessage(message) {
  return streamImmediate([
    message,
    {
      type: "done",
      ok: message.ok ?? true,
      output: message.output || "",
      clear: message.type === "clear"
    }
  ]);
}

function streamImmediate(events) {
  const body = events.map((event) => JSON.stringify(event)).join("\n") + "\n";
  return new Response(body, {
    headers: {
      "content-type": "application/x-ndjson; charset=utf-8",
      "cache-control": "no-cache",
      "x-accel-buffering": "no"
    }
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/api/health") {
      return jsonResponse({ ok: true, service: "pipeidea-cloudflare" });
    }

    if (request.method === "POST" && url.pathname === "/api/command/stream") {
      return handleStreamRequest(request, env, ctx);
    }

    return env.ASSETS.fetch(request);
  }
};
