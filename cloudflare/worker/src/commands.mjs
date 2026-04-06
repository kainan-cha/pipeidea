function tokenizeCommand(input) {
  const tokens = [];
  let current = "";
  let quote = null;
  let escape = false;

  for (const char of input) {
    if (escape) {
      current += char;
      escape = false;
      continue;
    }
    if (char === "\\") {
      escape = true;
      continue;
    }
    if (quote) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
      continue;
    }
    if (char === "'" || char === "\"") {
      quote = char;
      continue;
    }
    if (/\s/.test(char)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }
    current += char;
  }

  if (escape || quote) {
    throw new Error("Unterminated quote or escape in command.");
  }

  if (current) {
    tokens.push(current);
  }
  return tokens;
}

function parseFlags(tokens) {
  const result = {
    profile: null,
    provider: null,
    wild: false,
    forage: false,
    rest: []
  };

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token === "-w" || token === "--wild") {
      result.wild = true;
      continue;
    }
    if (token === "--forage") {
      result.forage = true;
      continue;
    }
    if (token === "-P" || token === "--profile") {
      const value = tokens[index + 1];
      if (!value) {
        throw new Error("Missing profile name after --profile.");
      }
      result.profile = value;
      index += 1;
      continue;
    }
    if (token === "-p" || token === "--provider") {
      const value = tokens[index + 1];
      if (!value) {
        throw new Error("Missing provider name after --provider.");
      }
      result.provider = value;
      index += 1;
      continue;
    }
    result.rest.push(token);
  }

  return result;
}

function normalizeCommandToken(token) {
  const normalized = String(token || "").toLowerCase();
  if (!normalized.startsWith("/")) {
    return token;
  }

  const bare = normalized.slice(1);
  if (["bloom", "collide", "profile", "help", "commands", "clear"].includes(bare)) {
    return bare;
  }
  return token;
}

export function helpText(availableProviders) {
  return [
    "# pipeidea",
    "",
    "Plain text blooms by default. Use `/commands` or `/help` to see browser commands.",
    "",
    "## Commands",
    "- `/bloom \"seed text\" [--forage] [-w] [-P PROFILE] [-p PROVIDER]`",
    "- `/collide \"first input\" \"second input\" [-w] [-P PROFILE] [-p PROVIDER]`",
    "- `/profile list`",
    "- `/profile show NAME`",
    "- `/clear`",
    "- `/help`",
    "",
    "## Notes",
    `- Available providers: ${availableProviders.join(", ")}`
  ].join("\n");
}

export function parseCommand(commandText) {
  const trimmed = String(commandText || "").trim();
  if (!trimmed) {
    return { type: "message", ok: true, output: "" };
  }
  if (trimmed === "help" || trimmed === "/help" || trimmed === "/commands" || trimmed === "--help" || trimmed === "-h") {
    return { type: "help" };
  }
  if (trimmed === "clear" || trimmed === "/clear") {
    return { type: "clear" };
  }

  let tokens;
  try {
    tokens = tokenizeCommand(trimmed);
  } catch {
    return {
      type: "creative",
      command: "bloom",
      seeds: [trimmed],
      profile: null,
      provider: null,
      wild: false,
      mode: "bloom"
    };
  }

  if (tokens.length === 0) {
    return { type: "message", ok: true, output: "" };
  }

  const command = normalizeCommandToken(tokens[0]);
  if (command === "bloom") {
    const parsed = parseFlags(tokens.slice(1));
    if (parsed.rest.length === 0) {
      throw new Error("Bloom needs a seed.");
    }
    return {
      type: "creative",
      command: "bloom",
      seeds: [parsed.rest.join(" ")],
      profile: parsed.profile,
      provider: parsed.provider,
      wild: parsed.wild,
      mode: parsed.forage ? "forage" : "bloom"
    };
  }

  if (command === "collide") {
    const parsed = parseFlags(tokens.slice(1));
    if (parsed.rest.length !== 2) {
      throw new Error("Collide needs exactly two quoted inputs.");
    }
    return {
      type: "creative",
      command: "collide",
      seeds: [parsed.rest[0], parsed.rest[1]],
      profile: parsed.profile,
      provider: parsed.provider,
      wild: parsed.wild,
      mode: "collision"
    };
  }

  if (command === "profile") {
    const subcommand = tokens[1];
    if (subcommand === "list") {
      return { type: "profile_list" };
    }
    if (subcommand === "show") {
      const name = tokens[2];
      if (!name) {
        throw new Error("Profile show needs a profile name.");
      }
      return { type: "profile_show", name };
    }
    if (subcommand === "create") {
      return {
        type: "message",
        ok: false,
        output: "Profile creation is disabled in the Cloudflare deployment."
      };
    }
    throw new Error("Unknown profile command.");
  }

  return {
    type: "creative",
    command: "bloom",
    seeds: [trimmed],
    profile: null,
    provider: null,
    wild: false,
    mode: "bloom"
  };
}
