/**
 * 用 KaTeX 权威验证所有 .md 里的数学公式。
 *
 * 为什么要这个：GitHub README 用 KaTeX 渲染数学，但它只支持
 * LaTeX 的一个子集。我们踩过的坑：
 *   - \Big\{ / \big(  -> KaTeX 不认，必须 \left\{ / \left(
 *   - \tfrac / \dfrac -> 统一用 \frac
 *   - \left[ ... \right] -> KaTeX 把 \[ 当显示公式命令，改用字面 [ ]
 * 这些错误在编辑器里看不出来（本地 markdown 插件常能渲染），
 * 只有在 GitHub 上才炸。所以写这个脚本在提交前拦住它们。
 *
 * 用法（需要先 npm install katex，或指定 KATEX_PATH 环境变量）：
 *   node tools/check_math.js
 */
const katex = require(process.env.KATEX_PATH
  || 'E:/Ufolder/Current/ActionSys/Temp/md/node_modules/katex');
const fs = require('fs');
const path = require('path');

// 仓库根
const REPO = path.resolve(__dirname, '..');

function collectMd(dir, acc = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === '.git' || e.name === 'archive') continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) collectMd(full, acc);
    else if (e.name.endsWith('.md')) acc.push(full);
  }
  return acc;
}

function extractMath(src) {
  const lines = src.split('\n');
  const out = [];
  // display $$...$$
  let i = 0;
  while (i < lines.length) {
    if (lines[i].includes('$$')) {
      let buf = [lines[i]];
      while (!buf.slice(1).join('').includes('$$') && i + 1 < lines.length) {
        i++; buf.push(lines[i]);
      }
      const m = buf.join('').match(/\$\$(.+?)\$\$/s);
      if (m) out.push({ line: i + 1, display: true, tex: m[1].trim() });
    }
    i++;
  }
  // inline $...$ —— 跳过货币符号：要求 $ 两侧不是数字
  lines.forEach((ln, idx) => {
    if (ln.includes('$$')) return;
    const re = /(?<![$\d])\$([^$\n]+)\$(?![$\d])/g;
    let m;
    while ((m = re.exec(ln)) !== null) {
      // 看起来像数学的才验（含 LaTeX 命令或典型数学符号）
      if (/\\[a-zA-Z]+|[=<>^_]|\\frac|\\sum|\\max|\\min|\\in|\\sim|\\lambda|\\tau/.test(m[1])) {
        out.push({ line: idx + 1, display: false, tex: m[1] });
      }
    }
  });
  return out;
}

let total = 0, bad = 0;
const files = collectMd(REPO);
for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  const eqs = extractMath(src);
  if (!eqs.length) continue;
  const rel = path.relative(REPO, f).replace(/\\/g, '/');
  console.log('\n--- ' + rel + ' (' + eqs.length + ' formulas) ---');
  for (const e of eqs) {
    total++;
    try {
      katex.renderToString(e.tex, { throwOnError: true, displayMode: e.display });
      console.log('  L' + e.line + ' OK   ' + e.tex.slice(0, 70));
    } catch (err) {
      bad++;
      console.log('  L' + e.line + ' FAIL ' + err.message.slice(0, 80));
      console.log('       ' + e.tex.slice(0, 110));
    }
  }
}
console.log('\n========================================');
console.log('总计 ' + total + ' 条公式，失败 ' + bad + ' 条');
console.log(bad === 0 ? 'ALL PASS' : 'HAS FAILURES');
process.exit(bad === 0 ? 0 : 1);