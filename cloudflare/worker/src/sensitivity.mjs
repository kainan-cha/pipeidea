const SENSITIVE_PATTERNS = [
  /\bgaza\b/i,
  /\bisrael\b/i,
  /\bpalestin(?:e|ian|ians)\b/i,
  /\bhamas\b/i,
  /\bceasefire\b/i,
  /\bwar\b/i,
  /\bconflict\b/i,
  /\bgenocide\b/i,
  /\bethnic cleansing\b/i,
  /\bterror(?:ism|ist|ists)?\b/i,
  /\bhostage(?:s)?\b/i,
  /\brefugee(?:s)?\b/i,
  /\bdisplacement\b/i,
  /\bfamine\b/i,
  /\bhumanitarian\b/i,
  /\batrocit(?:y|ies)\b/i,
  /\babuse\b/i,
  /\bsuicid(?:e|al)\b/i,
  /\bself-harm\b/i,
  /\boverdose\b/i,
  /\bepidemic\b/i,
  /\bpandemic\b/i,
  /\boutbreak\b/i,
  /\bmassacre\b/i,
  /\bshooting\b/i
];

export function assessPromptSensitivity(seeds, mode) {
  const haystack = String((seeds || []).join(" ")).trim();
  if (!haystack) {
    return { isSensitive: false, reason: null };
  }

  for (const pattern of SENSITIVE_PATTERNS) {
    const match = haystack.match(pattern);
    if (!match) {
      continue;
    }

    const trigger = String(match[0] || "").trim().toLowerCase();
    const base =
      `The user's prompt includes a live high-stakes topic (${trigger}). ` +
      "Respond with humane, concrete, non-decorative language.";
    const reason = mode === "collision"
      ? `${base} Keep the collision tightly anchored and avoid playful metaphor.`
      : `${base} Prefer direct mechanisms and grounded framing over bloom-style abstraction.`;
    return { isSensitive: true, reason };
  }

  return { isSensitive: false, reason: null };
}
