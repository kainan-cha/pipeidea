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
