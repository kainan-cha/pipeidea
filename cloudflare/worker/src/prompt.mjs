import { PROFILE_BUNDLE } from "./generated/profiles.mjs";

const SECTION_ORDER = [
  ["identity.md", "Identity"],
  ["taste.md", "Taste"],
  ["ambition.md", "Ambition"],
  ["knowledge.md", "Knowledge"],
  ["randomness.md", "Randomness"],
  ["techniques.md", "Techniques"],
  ["protocol.md", "Protocol"],
  ["dialogue.md", "Dialogue"],
  ["output.md", "Output"]
];

function resolveProfileName(name) {
  return name || PROFILE_BUNDLE.default_profile || "default";
}

function getExplicitProfile(name) {
  return PROFILE_BUNDLE.profiles[name] || null;
}

function resolveProfileFiles(name) {
  const resolvedName = resolveProfileName(name);
  const base = getExplicitProfile(PROFILE_BUNDLE.default_profile);
  const selected = getExplicitProfile(resolvedName);
  if (!selected) {
    throw new Error(`Profile '${resolvedName}' not found.`);
  }
  return {
    name: resolvedName,
    files: {
      ...(base ? base.files : {}),
      ...selected.files
    }
  };
}

export function listProfiles() {
  return Object.keys(PROFILE_BUNDLE.profiles).sort();
}

export function loadFullProfile(name) {
  return resolveProfileFiles(name);
}

export function composePrompt({ profile, mode, randomStimulus, runtimeGuidance }) {
  const snapshot = resolveProfileFiles(profile);
  const sections = [];

  for (const [key, title] of SECTION_ORDER) {
    const content = snapshot.files[key];
    if (content) {
      sections.push({ key, title, content });
    }
  }

  const modeKey = `modes/${mode}.md`;
  const modeContent = snapshot.files[modeKey];
  if (!modeContent) {
    throw new Error(`Mode '${mode}' is not available in profile '${snapshot.name}'.`);
  }
  sections.push({ key: modeKey, title: `Mode: ${mode}`, content: modeContent });

  if (randomStimulus) {
    sections.push({
      key: "runtime/random_stimulus",
      title: "Random Stimulus",
      content: [
        "# Random Stimulus",
        "",
        "A random element has been injected into your creative space. You did not ask for it.",
        "Use it, ignore it, or let it derail you if that makes the idea more alive.",
        "",
        `**Random stimulus:** ${randomStimulus}`
      ].join("\n")
    });
  }

  if (runtimeGuidance) {
    sections.push({
      key: "runtime/guidance",
      title: "Runtime Guidance",
      content: [
        "# Runtime Guidance",
        "",
        "Honor this situational instruction for the current prompt.",
        "",
        runtimeGuidance
      ].join("\n")
    });
  }

  return {
    profile: snapshot.name,
    sections,
    systemPrompt: sections.map((section) => section.content).join("\n\n---\n\n")
  };
}

const DIVERGE_PREAMBLE = `You are an idea mechanism generator. Your job is to produce three distinct, concrete mechanism sketches for a creative prompt. Do not write prose, titles, or metaphors. Write in plain operational language: who does what, by what rule or material or incentive, and what changes first.

Each candidate must:
- Describe a specific mechanism, not a mood or metaphor
- Stay visibly connected to the user's seed
- Be ambitious (level 7-10: the kind of idea that makes people nervous)
- Pass this test: if you remove all analogy and figurative language, is there still an operational mechanism left?

Kill on sight:
- Surface analogy ("X is like Y" without shared deep structure)
- Generic futurism ("AI-powered X", "blockchain-based Y")
- Wrapper ambition (calling something a platform/ecosystem/protocol without changing the underlying mechanism)
- Incremental improvement (a better version of an existing thing)

Output exactly this format, nothing else:

CANDIDATE 1:
Mechanism: [2-3 sentences. What happens? Who does what, by what rule/material/incentive/interface? What changes first?]
Seed connection: [1 sentence. How does this directly answer the user's prompt?]
Ambition: [1 sentence. What does the world look like if this wins?]

CANDIDATE 2:
Mechanism: [...]
Seed connection: [...]
Ambition: [...]

CANDIDATE 3:
Mechanism: [...]
Seed connection: [...]
Ambition: [...]`;

const SELECT_PREAMBLE = `You are a taste judge for creative ideas. You will receive three mechanism candidates and the original seed. Pick the single best one.

Selection criteria (in order):
1. Strongest mechanism — can you explain what happens in plain language?
2. Most ambitious — does it change a category, not just improve a product?
3. Closest to seed — is the user's prompt still visibly load-bearing?
4. Passes the "remove the metaphor" test — is anything left without analogy?

Output exactly this format, nothing else:

WINNER: [1, 2, or 3]
REASON: [1 sentence explaining why this candidate beats the others]`;

export function composeDivergePrompt({ profile, mode, randomStimulus, runtimeGuidance }) {
  const snapshot = resolveProfileFiles(profile);
  const sections = [{ key: "diverge_preamble", title: "Diverge Preamble", content: DIVERGE_PREAMBLE }];

  const modeKey = `modes/${mode}.md`;
  const modeContent = snapshot.files[modeKey];
  if (modeContent) {
    sections.push({ key: modeKey, title: `Mode: ${mode}`, content: modeContent });
  }

  if (randomStimulus) {
    sections.push({
      key: "runtime/random_stimulus",
      title: "Random Stimulus",
      content: `A random element for creative perturbation. Use it only if it strengthens a mechanism. Discard it if it weakens topic discipline.\n\n**Random stimulus:** ${randomStimulus}`
    });
  }

  if (runtimeGuidance) {
    sections.push({ key: "runtime/guidance", title: "Runtime Guidance", content: runtimeGuidance });
  }

  return {
    profile: snapshot.name,
    sections,
    systemPrompt: sections.map((s) => s.content).join("\n\n---\n\n")
  };
}

export function composeSelectPrompt() {
  return SELECT_PREAMBLE;
}

export function composeDivergeUserMessage(seeds, mode) {
  const base = composeUserMessage(seeds, mode);
  return `${base}\n\nGenerate three mechanism candidates. No prose, no titles, no metaphors.`;
}

export function composeSelectUserMessage(seeds, mode, candidates) {
  const seedText = seeds.join(" + ");
  return `Original seed: ${seedText}\nMode: ${mode}\n\nCandidates:\n\n${candidates}\n\nPick the best candidate.`;
}

export function composeRenderUserMessage(seeds, mode, mechanismSpec) {
  const base = composeUserMessage(seeds, mode);
  return [
    base,
    "",
    "You have already extracted the core mechanism. Here it is:",
    "",
    "---",
    mechanismSpec,
    "---",
    "",
    "Render this mechanism into your final output. The mechanism is your ",
    "foundation — preserve it faithfully. Your job now is voice, vividness, ",
    "and format. Do not invent a new mechanism; deepen and render the one above."
  ].join("\n");
}

export function composeUserMessage(seeds, mode) {
  if (mode === "collision") {
    return [
      "Collide these:",
      "",
      `**Input 1:** ${seeds[0]}`,
      "",
      `**Input 2:** ${seeds[1]}`
    ].join("\n");
  }
  if (mode === "forage") {
    return seeds[0]
      ? `Forage around this topic and bring back collisions: ${seeds[0]}`
      : "Forage freely. Find something interesting in the world and build ideas from it.";
  }
  return `Seed: ${seeds[0]}`;
}

export function formatProfile(name) {
  const snapshot = resolveProfileFiles(name);
  const parts = [`profile: ${snapshot.name}`];
  for (const key of PROFILE_BUNDLE.file_order) {
    if (snapshot.files[key]) {
      parts.push(`\n[${key}]\n${snapshot.files[key].trim()}`);
    }
  }
  return parts.join("\n").trim();
}
