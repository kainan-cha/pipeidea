/**
 * Detect the dominant language of user seeds via Unicode script analysis.
 */

function scriptOf(ch) {
  const code = ch.codePointAt(0);

  // CJK Unified Ideographs
  if (
    (code >= 0x4e00 && code <= 0x9fff) ||
    (code >= 0x3400 && code <= 0x4dbf) ||
    (code >= 0x20000 && code <= 0x2a6df) ||
    (code >= 0xf900 && code <= 0xfaff)
  ) {
    return "CJK";
  }

  // Hiragana
  if (code >= 0x3040 && code <= 0x309f) return "HIRAGANA";

  // Katakana
  if (
    (code >= 0x30a0 && code <= 0x30ff) ||
    (code >= 0x31f0 && code <= 0x31ff)
  ) {
    return "KATAKANA";
  }

  // Hangul
  if (
    (code >= 0xac00 && code <= 0xd7af) ||
    (code >= 0x1100 && code <= 0x11ff) ||
    (code >= 0x3130 && code <= 0x318f)
  ) {
    return "HANGUL";
  }

  // Cyrillic
  if (
    (code >= 0x0400 && code <= 0x04ff) ||
    (code >= 0x0500 && code <= 0x052f)
  ) {
    return "CYRILLIC";
  }

  // Arabic
  if (
    (code >= 0x0600 && code <= 0x06ff) ||
    (code >= 0x0750 && code <= 0x077f) ||
    (code >= 0x08a0 && code <= 0x08ff)
  ) {
    return "ARABIC";
  }

  // Thai
  if (code >= 0x0e00 && code <= 0x0e7f) return "THAI";

  // Devanagari
  if (code >= 0x0900 && code <= 0x097f) return "DEVANAGARI";

  return "OTHER";
}

export function detectSeedLanguage(seeds) {
  const combined = seeds.join(" ").trim();
  if (!combined) return null;

  const counts = {};
  let totalNonWs = 0;

  for (const ch of combined) {
    if (/\s/.test(ch)) continue;
    totalNonWs++;
    const script = scriptOf(ch);
    counts[script] = (counts[script] || 0) + 1;
  }

  if (totalNonWs === 0) return null;

  const threshold = 0.30;
  const kana = (counts.HIRAGANA || 0) + (counts.KATAKANA || 0);
  const cjk = counts.CJK || 0;
  const hangul = counts.HANGUL || 0;

  // Japanese: any Kana present + CJK
  if (kana > 0 && (kana + cjk) / totalNonWs >= threshold) return "Japanese";

  // Korean
  if (hangul / totalNonWs >= threshold) return "Korean";

  // Chinese: CJK without Kana or Hangul
  if (cjk / totalNonWs >= threshold && kana === 0 && hangul === 0) return "Chinese";

  // Other scripts
  const others = [
    ["CYRILLIC", "Russian"],
    ["ARABIC", "Arabic"],
    ["THAI", "Thai"],
    ["DEVANAGARI", "Hindi"]
  ];
  for (const [script, lang] of others) {
    if ((counts[script] || 0) / totalNonWs >= threshold) return lang;
  }

  return null;
}

export function languageGuidance(language) {
  return (
    `⚠️ LANGUAGE REQUIREMENT — NON-NEGOTIABLE ⚠️\n\n` +
    `The user wrote their prompt in ${language}. ` +
    `You MUST write your ENTIRE response in ${language}. ` +
    `Every word of output — title, mechanism, prose, trailing thread — ` +
    `must be in ${language}. Do NOT write in English. ` +
    `Only universally recognized proper nouns (brand names, place names) ` +
    `may remain in their original form. Everything else: ${language}.`
  );
}
