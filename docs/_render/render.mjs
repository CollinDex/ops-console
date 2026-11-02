// Renders docs/system-design.md into docs/system-design.html (the published review page).
// Usage: node docs/_render/render.mjs docs docs/system-design.html
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { Marked } from "marked";

const [docsDir, outFile] = process.argv.slice(2);

const slug = (s) =>
  s.toLowerCase().replace(/<[^>]+>/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function makeMarked(prefix, toc) {
  const m = new Marked();
  m.use({
    renderer: {
      heading(text, depth) {
        const adrId = text.match(/^ADR-(\d{3})/);
        const id = adrId ? `adr-${adrId[1]}` : prefix + slug(text);
        if (toc && depth === 2) toc.push({ id, text: text.replace(/<[^>]+>/g, "") });
        return `<h${depth} id="${id}">${text}</h${depth}>\n`;
      },
      code(code, lang) {
        if (lang === "mermaid") return `<div class="diagram"><pre class="mermaid">${code.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</pre></div>\n`;
        const esc = code.replace(/&/g, "&amp;").replace(/</g, "&lt;");
        return `<pre class="code"><code>${esc}</code></pre>\n`;
      },
      table(header, body) {
        return `<div class="table-wrap"><table><thead>${header}</thead><tbody>${body}</tbody></table></div>\n`;
      },
      link(href, title, text) {
        const adr = href.match(/adr\/(\d{3})-/);
        if (adr) return `<a href="#adr-${adr[1]}">${text}</a>`;
        if (href === "./adr") return `<a href="#appendix-architecture-decision-records">${text}</a>`;
        return `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;
      },
    },
  });
  return m;
}

const toc = [];
let design = readFileSync(join(docsDir, "system-design.md"), "utf8");
// Title + metadata table are rendered by the page header instead.
design = design.replace(/^# .*\n/, "").replace(/^\s*\|[\s\S]*?\n---\n/, "");
const designHtml = makeMarked("", toc).parse(design);


const tocHtml = toc.map((t) => `<li><a href="#${t.id}">${t.text}</a></li>`).join("");

const page = `<title>CrediSure Ops Console Design</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: sticky contents rail + single reading column; tables/diagrams scroll inside their own frames. */
:root {
  --bg: #f6f7f9; --surface: #ffffff; --fg: #1a2233; --muted: #5a6478; --line: #dde2ea;
  --navy: #1f3a68; --accent: #2457b3; --code-bg: #eef1f6; --ok: #1d7a4a; --warn: #a56a00;
  --f-display: "IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif;
  --f-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f141d; --surface: #161d29; --fg: #e3e8f1; --muted: #9aa5b8; --line: #2a3445;
  --navy: #9fbcf0; --accent: #7ea6f2; --code-bg: #1d2636; --ok: #5cc68e; --warn: #e2a640; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0f141d; --surface: #161d29; --fg: #e3e8f1; --muted: #9aa5b8; --line: #2a3445;
  --navy: #9fbcf0; --accent: #7ea6f2; --code-bg: #1d2636; --ok: #5cc68e; --warn: #e2a640; color-scheme: dark; }
body { background: var(--bg); color: var(--fg); font: 15.5px/1.65 var(--f-body); }
.shell { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 48px; max-width: 1180px; margin: 0 auto;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 40px 80px; }
nav.toc { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 24px); align-self: start; max-height: calc(100vh - 48px); overflow: auto; }
nav.toc .label { font: 600 11px/1 var(--f-display); letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
nav.toc ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
nav.toc a { display: block; padding: 5px 10px; border-left: 2px solid var(--line); color: var(--muted); text-decoration: none; font-size: 13.5px; line-height: 1.35; }
nav.toc a:hover, nav.toc a:focus-visible { color: var(--fg); border-left-color: var(--accent); outline: none; }
main { min-width: 0; max-width: 820px; }
header.doc { border-bottom: 1px solid var(--line); padding-bottom: 24px; margin-bottom: 8px; }
.eyebrow { font: 600 12px/1 var(--f-display); letter-spacing: .14em; text-transform: uppercase; color: var(--accent); }
h1 { font: 600 clamp(30px, 5vw, 42px)/1.1 var(--f-display); color: var(--navy); margin: 10px 0 14px; text-wrap: balance; }
.meta { display: flex; flex-wrap: wrap; gap: 8px 20px; color: var(--muted); font-size: 13.5px; }
.pill { display: inline-flex; align-items: center; gap: 6px; font: 500 12px/1 var(--f-mono); padding: 5px 9px; border-radius: 999px; border: 1px solid var(--warn); color: var(--warn); }
.pill.ok { border-color: var(--ok); color: var(--ok); }
.pill::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
h2 { font: 600 26px/1.2 var(--f-display); color: var(--navy); margin: 56px 0 12px; padding-top: 8px; text-wrap: balance; scroll-margin-top: 16px; }
h3 { font: 600 18px/1.3 var(--f-display); margin: 32px 0 8px; scroll-margin-top: 16px; }
p, li { max-width: 68ch; }
a { color: var(--accent); }
code { font: 0.86em var(--f-mono); background: var(--code-bg); padding: 1px 5px; border-radius: 4px; }
pre.code { background: var(--code-bg); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; overflow-x: auto; font: 13px/1.55 var(--f-mono); }
pre.code code { background: none; padding: 0; font-size: inherit; }
.table-wrap { overflow-x: auto; margin: 14px 0 20px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 14px; font-variant-numeric: tabular-nums; }
th { text-align: left; font: 600 12.5px/1.3 var(--f-display); letter-spacing: .03em; color: var(--muted); background: var(--code-bg); }
th, td { padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
tbody tr:last-child td { border-bottom: 0; }
td code { white-space: nowrap; }
.diagram { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px; margin: 14px 0 20px; }
.diagram pre.mermaid { margin: 0; background: none; text-align: center; }
hr { border: 0; border-top: 1px solid var(--line); margin: 40px 0; }
.adr { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 4px 22px 14px; margin: 18px 0; }
.adr h3 { color: var(--navy); font-size: 19px; }
.adr h2 { font-size: 13px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin: 20px 0 4px; padding: 0; }
@media (max-width: 960px) {
  .shell { grid-template-columns: minmax(0, 1fr); gap: 0; padding-block: 24px 64px; }
  nav.toc { position: static; max-height: none; border: 1px solid var(--line); border-radius: 8px; padding: 14px; margin-bottom: 24px; background: var(--surface); }
  nav.toc ol { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
}
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
</style>
<div class="shell">
  <nav class="toc" aria-label="Contents"><div class="label">Contents</div><ol>${tocHtml}</ol></nav>
  <main>
    <header class="doc">
      <div class="eyebrow">CrediSure engineering assessment · System design</div>
      <h1>CrediSure Ops Console: System Design</h1>
      <div class="meta"><span class="pill ok">Approved</span><span>Chibuikem Collins Obetta</span><span>2 November 2026</span><span>Source: Ops Console PRD</span></div>
    </header>
    ${designHtml}
  </main>
</div>
`;
writeFileSync(outFile, page);
console.log(`wrote ${outFile} (${page.length} bytes, ${toc.length} toc entries)`);
