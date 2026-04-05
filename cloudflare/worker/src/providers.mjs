function toNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function providerConfig(env, requestedProvider) {
  const name = requestedProvider || env.PIPEIDEA_DEFAULT_PROVIDER || "deepseek";
  const temperature = toNumber(env.PIPEIDEA_TEMPERATURE, 0.9);

  if (name === "deepseek") {
    if (!env.DEEPSEEK_API_KEY) {
      throw new Error("DEEPSEEK_API_KEY is not configured.");
    }
    return {
      name,
      model: env.PIPEIDEA_DEFAULT_MODEL || "deepseek-chat",
      temperature,
      kind: "openai_compat",
      apiKey: env.DEEPSEEK_API_KEY,
      baseUrl: env.DEEPSEEK_BASE_URL || "https://api.deepseek.com/v1"
    };
  }

  if (name === "openai") {
    if (!env.OPENAI_API_KEY) {
      throw new Error("OPENAI_API_KEY is not configured.");
    }
    return {
      name,
      model: env.OPENAI_MODEL || "gpt-4o-mini",
      temperature,
      kind: "openai_compat",
      apiKey: env.OPENAI_API_KEY,
      baseUrl: env.OPENAI_BASE_URL || "https://api.openai.com/v1"
    };
  }

  if (name === "claude") {
    if (!env.ANTHROPIC_API_KEY) {
      throw new Error("ANTHROPIC_API_KEY is not configured.");
    }
    return {
      name,
      model: env.ANTHROPIC_MODEL || "claude-sonnet-4-20250514",
      temperature,
      kind: "anthropic",
      apiKey: env.ANTHROPIC_API_KEY,
      baseUrl: env.ANTHROPIC_BASE_URL || "https://api.anthropic.com/v1"
    };
  }

  throw new Error(`Unknown provider: ${name}`);
}

async function* parseOpenAICompatSSE(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let separator = buffer.indexOf("\n\n");
    while (separator >= 0) {
      const eventBlock = buffer.slice(0, separator).trim();
      buffer = buffer.slice(separator + 2);

      if (eventBlock) {
        const lines = eventBlock.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data:")) {
            continue;
          }
          const payload = line.slice(5).trim();
          if (!payload || payload === "[DONE]") {
            continue;
          }
          const parsed = JSON.parse(payload);
          const delta = parsed.choices?.[0]?.delta?.content;
          if (delta) {
            yield delta;
          }
        }
      }

      separator = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }
}

async function* parseAnthropicSSE(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let separator = buffer.indexOf("\n\n");
    while (separator >= 0) {
      const eventBlock = buffer.slice(0, separator).trim();
      buffer = buffer.slice(separator + 2);

      if (eventBlock) {
        const lines = eventBlock.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data:")) {
            continue;
          }
          const payload = line.slice(5).trim();
          if (!payload || payload === "[DONE]") {
            continue;
          }
          const parsed = JSON.parse(payload);
          if (parsed.type === "content_block_delta" && parsed.delta?.text) {
            yield parsed.delta.text;
          }
        }
      }

      separator = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }
}

async function* streamOpenAICompat(config, systemPrompt, userMessage) {
  const response = await fetch(`${config.baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${config.apiKey}`
    },
    body: JSON.stringify({
      model: config.model,
      temperature: config.temperature,
      max_tokens: 4096,
      stream: true,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage }
      ]
    })
  });

  if (!response.ok) {
    throw new Error(`Provider error (${config.name}): ${await response.text()}`);
  }

  if (!response.body) {
    throw new Error(`Provider error (${config.name}): empty response body.`);
  }

  yield* parseOpenAICompatSSE(response.body);
}

async function* streamAnthropic(config, systemPrompt, userMessage) {
  const response = await fetch(`${config.baseUrl}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": config.apiKey,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({
      model: config.model,
      temperature: config.temperature,
      max_tokens: 4096,
      stream: true,
      system: systemPrompt,
      messages: [
        { role: "user", content: userMessage }
      ]
    })
  });

  if (!response.ok) {
    throw new Error(`Provider error (${config.name}): ${await response.text()}`);
  }

  if (!response.body) {
    throw new Error(`Provider error (${config.name}): empty response body.`);
  }

  yield* parseAnthropicSSE(response.body);
}

export const AVAILABLE_PROVIDERS = ["claude", "openai", "deepseek"];

export async function* streamFromProvider(env, requestedProvider, systemPrompt, userMessage, wild = false) {
  const config = providerConfig(env, requestedProvider);
  const effectiveConfig = {
    ...config,
    temperature: wild ? Math.min(config.temperature + 0.3, 1.5) : config.temperature
  };

  if (effectiveConfig.kind === "openai_compat") {
    yield* streamOpenAICompat(effectiveConfig, systemPrompt, userMessage);
    return;
  }

  yield* streamAnthropic(effectiveConfig, systemPrompt, userMessage);
}
