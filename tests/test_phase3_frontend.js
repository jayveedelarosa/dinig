/**
 * Phase 3 frontend unit tests — plain Node.js, no packages required.
 *
 * Covers:
 *   3a  Heatmap blank-cell ordering: blanks (–) must be on the LEFT (oldest side),
 *       newest reading must always be the RIGHTMOST cell.
 *   3b  My Result font size: .story.result must override .story to a smaller size
 *       so the Next button stays on screen at 1366×768.
 *   3c  Pick Your Name tile grid: minmax must be ≤140px and tile min-height ≤80px
 *       so 40 pupils fit without scrolling.
 *
 * Run:
 *   node tests/test_phase3_frontend.js
 */

const fs   = require("fs");
const path = require("path");

// ── tiny test harness ─────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;

function ok(label, condition, detail = "") {
  if (condition) {
    console.log(`ok  ${label}`);
    passed++;
  } else {
    console.error(`FAIL  ${label}${detail ? `\n      ${detail}` : ""}`);
    failed++;
  }
}

function deepEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

// ── read source files ─────────────────────────────────────────────────────────

const appJs   = fs.readFileSync(path.join(__dirname, "../frontend/app.js"),    "utf8");
const css     = fs.readFileSync(path.join(__dirname, "../frontend/styles.css"), "utf8");

// ─────────────────────────────────────────────────────────────────────────────
// 3a — Heatmap blank-cell ordering
// ─────────────────────────────────────────────────────────────────────────────

// Extract the band() function from app.js and evaluate it in this context.
// band() maps accuracy → CSS class name.
const bandMatch = appJs.match(/function band\(accuracy\)\s*\{[\s\S]*?\n\}/);
ok("3a: band() function exists in app.js", !!bandMatch);

let band;
if (bandMatch) {
  // eslint-disable-next-line no-new-func
  band = new Function(`${bandMatch[0]}; return band;`)();
}

// ── band() correctness ────────────────────────────────────────────────────────
ok("3a: band(null) → 'none'",  band && band(null)      === "none");
ok("3a: band(undefined) → 'none'", band && band(undefined) === "none");
ok("3a: band(0.90) → 'good'",  band && band(0.90)      === "good");
ok("3a: band(0.95) → 'good'",  band && band(0.95)      === "good");
ok("3a: band(0.75) → 'almost'",band && band(0.75)      === "almost");
ok("3a: band(0.89) → 'almost'",band && band(0.89)      === "almost");
ok("3a: band(0.74) → 'help'",  band && band(0.74)      === "help");
ok("3a: band(0.50) → 'help'",  band && band(0.50)      === "help");

// ── left-pad logic ────────────────────────────────────────────────────────────
// This is the exact logic now in app.js:
function buildPadded(last5) {
  return Array(5 - last5.length).fill(undefined).concat(last5);
}

function renderCells(last5) {
  const padded = buildPadded(last5);
  return padded.map(acc => acc === undefined ? "–" : String(Math.round(acc * 100)));
}

// Pupil with 0 readings → all 5 blanks on the left
const cells0 = renderCells([]);
ok("3a: 0 readings → all 5 cells are '–'",
  deepEqual(cells0, ["–", "–", "–", "–", "–"]),
  `got ${JSON.stringify(cells0)}`
);

// Pupil with 1 reading (score 0.92) → blank blank blank blank score
const cells1 = renderCells([0.92]);
ok("3a: 1 reading → 4 blanks then the score on the right",
  deepEqual(cells1, ["–", "–", "–", "–", "92"]),
  `got ${JSON.stringify(cells1)}`
);

// Pupil with 2 readings → blank blank blank score1 score2
const cells2 = renderCells([0.80, 0.85]);
ok("3a: 2 readings → 3 blanks then oldest score then newest score",
  deepEqual(cells2, ["–", "–", "–", "80", "85"]),
  `got ${JSON.stringify(cells2)}`
);

// Pupil with 3 readings (improving) → blank blank score1 score2 score3
const cells3 = renderCells([0.60, 0.70, 0.80]);
ok("3a: 3 readings → 2 blanks then oldest to newest left-to-right",
  deepEqual(cells3, ["–", "–", "60", "70", "80"]),
  `got ${JSON.stringify(cells3)}`
);

// Pupil with 5 readings → no blanks, oldest first
const cells5 = renderCells([0.55, 0.65, 0.72, 0.80, 0.91]);
ok("3a: 5 readings → no blanks, oldest left newest right",
  deepEqual(cells5, ["55", "65", "72", "80", "91"]),
  `got ${JSON.stringify(cells5)}`
);

// Newest reading is always position 4 (index 4) when readings exist
ok("3a: newest reading is always the last (rightmost) cell",
  cells1[4] === "92" && cells2[4] === "85" && cells3[4] === "80" && cells5[4] === "91"
);

// Blanks are always on the left side
ok("3a: blanks are always left-aligned (older side)",
  cells1.indexOf("–") === 0 &&
  cells2.indexOf("–") === 0 &&
  cells3.indexOf("–") === 0
);

// ── app.js contains the padded array construction ─────────────────────────────
ok("3a: app.js uses Array().fill(undefined).concat(p.last5) for left-padding",
  /Array\(5\s*-\s*p\.last5\.length\)\.fill\(undefined\)\.concat\(p\.last5\)/.test(appJs)
);

ok("3a: app.js iterates over `padded[i]` not `p.last5[i]` in the heat loop",
  /padded\[i\]/.test(appJs) && !/const acc = p\.last5\[i\]/.test(appJs)
);

// ─────────────────────────────────────────────────────────────────────────────
// 3b — My Result font size (.story.result override)
// ─────────────────────────────────────────────────────────────────────────────

// Parse a CSS property value from a given selector.
// Anchors the selector with \s*{ so ".story" does not accidentally match ".story.result".
function getCSSProp(css, selector, prop) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Use (?![.\w]) after the selector so ".story" won't match ".story.result"
  const re = new RegExp(escaped + "(?![.\\w\\-])\\s*\\{([^}]*)\\}");
  const m = css.match(re);
  if (!m) return null;
  const block = m[1];
  const propRe = new RegExp(prop.replace("-", "\\-") + "\\s*:\\s*([^;]+)");
  const pm = block.match(propRe);
  return pm ? pm[1].trim() : null;
}

const storyFontSize   = getCSSProp(css, ".story",        "font-size");
const storyLineHeight = getCSSProp(css, ".story",        "line-height");
const resultFontSize  = getCSSProp(css, ".story.result", "font-size");
const resultLineHeight= getCSSProp(css, ".story.result", "line-height");
const resultPadding   = getCSSProp(css, ".story.result", "padding");

ok("3b: .story base font-size is 36px",
  storyFontSize === "36px",
  `got '${storyFontSize}'`
);

ok("3b: .story.result rule exists in styles.css",
  css.includes(".story.result")
);

ok("3b: .story.result font-size is smaller than .story (≤28px)",
  !!resultFontSize && parseInt(resultFontSize) <= 28,
  `got '${resultFontSize}'`
);

ok("3b: .story.result line-height is set (reduces vertical space)",
  !!resultLineHeight,
  `got '${resultLineHeight}'`
);

ok("3b: .story.result line-height ≤ .story line-height (1.8)",
  !!resultLineHeight && parseFloat(resultLineHeight) <= 1.8,
  `got '${resultLineHeight}'`
);

ok("3b: .story.result padding is set (tighter than .story's 24px 32px)",
  !!resultPadding,
  `got '${resultPadding}'`
);

// Rough height estimate: verify a 60-word story at result font size fits in 768px
// Available height: 768px total - 68px header - 40px score-row - 40px legend
//   - 96px Next button+margin - 48px screen padding = ~476px for the story block
// At 22px font, 1.6 line-height: line-height = 35.2px. 60 words on a 1366px screen
// wrap to ~4 lines at 22px. 4 × 35.2 + 32px padding = ~173px → fits.
const resFontPx = resultFontSize ? parseInt(resultFontSize) : 36;
const resLH     = resultLineHeight ? parseFloat(resultLineHeight) : 1.8;
const lineHeightPx = resFontPx * resLH;
// 60 words at 22px averages ~100px per line on 1366px viewport → ~4 lines
const estimatedStoryHeight = 4 * lineHeightPx + 32; // +32 padding
const availableHeight = 768 - 68 - 40 - 40 - 96 - 48; // ~476
ok(
  `3b: estimated story block height (${Math.round(estimatedStoryHeight)}px) fits available viewport (${availableHeight}px)`,
  estimatedStoryHeight <= availableHeight,
  `story block ~${Math.round(estimatedStoryHeight)}px, available ~${availableHeight}px`
);

// ─────────────────────────────────────────────────────────────────────────────
// 3c — Tile grid size (40 pupils fit without scrolling at 1366×768)
// ─────────────────────────────────────────────────────────────────────────────

// Extract minmax value from .tiles grid-template-columns
const tilesRule = css.match(/\.tiles\s*\{([^}]+)\}/);
const tilesBlock = tilesRule ? tilesRule[1] : "";

const minmaxMatch = tilesBlock.match(/minmax\((\d+)px/);
const tilesMinPx  = minmaxMatch ? parseInt(minmaxMatch[1]) : null;

const tileRule  = css.match(/\.tile\s*\{([^}]+)\}/);
const tileBlock = tileRule ? tileRule[1] : "";

const minHeightMatch = tileBlock.match(/min-height\s*:\s*(\d+)px/);
const tileMinHeightPx = minHeightMatch ? parseInt(minHeightMatch[1]) : null;

const gapMatch = tilesBlock.match(/gap\s*:\s*(\d+)px/);
const gapPx    = gapMatch ? parseInt(gapMatch[1]) : 20;

ok("3c: .tiles minmax is set to ≤140px",
  tilesMinPx !== null && tilesMinPx <= 140,
  `got minmax(${tilesMinPx}px, ...)`
);

ok("3c: .tile min-height is set to ≤80px",
  tileMinHeightPx !== null && tileMinHeightPx <= 80,
  `got min-height: ${tileMinHeightPx}px`
);

// Verify 40 pupils fit on a 1366×768 screen without scrolling
// Available width: 1366 - 2×32px screen padding = 1302px
// Tiles per row: floor((1302 + gap) / (minmax + gap))
// Available height: 768 - 68px header - 24px top padding = ~676px
// Rows needed: ceil(40 / tilesPerRow)
// Total tile height: rows × (minHeight + gap) - gap (no trailing gap)
const availWidth   = 1366 - 2 * 32;
const tilesPerRow  = Math.floor((availWidth + gapPx) / (tilesMinPx + gapPx));
const rowsNeeded   = Math.ceil(40 / tilesPerRow);
const totalHeight  = rowsNeeded * (tileMinHeightPx + gapPx) - gapPx;
const availTileHeight = 768 - 68 - 24; // header + top padding

ok(
  `3c: ${tilesPerRow} tiles/row → ${rowsNeeded} rows for 40 pupils`,
  tilesPerRow >= 8,
  `got ${tilesPerRow} tiles per row`
);

ok(
  `3c: 40 tiles total height (${totalHeight}px) fits viewport height (${availTileHeight}px)`,
  totalHeight <= availTileHeight,
  `total tile height ~${totalHeight}px, available ~${availTileHeight}px`
);

// ─────────────────────────────────────────────────────────────────────────────
// Summary
// ─────────────────────────────────────────────────────────────────────────────

console.log();
const total = passed + failed;
if (failed === 0) {
  console.log(`All ${total} Phase 3 frontend tests passed. ✓`);
  process.exit(0);
} else {
  console.log(`${passed} of ${total} Phase 3 frontend tests passed.  ${failed} FAILED.`);
  process.exit(1);
}
