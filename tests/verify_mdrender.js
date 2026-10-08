#!/usr/bin/env node
/* hermes-verify: 医小喵 index.html Markdown 渲染 — 针对「改后的真实文件」做独立验证
   验证目标：
   1. 从真实 index.html 里抠出 escapeHtml/mdToHtml，确保测的是线上代码而非副本
   2. 断言渲染行为正确（粗体/列表/标题/代码/引用/分隔线 + start 序号）
   3. 断言流式容错（未闭合语法不渲染、不崩）
   4. 断言 XSS 防护（模型输出的 HTML 被转义）
   5. 断言 4 处调用点已全部切换（无残留 textContent 直填回答）
*/
const fs = require('fs');
const FILE = '/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa/app/static/index.html';

let pass = 0, fail = 0;
const fails = [];
function eq(name, got, exp) {
  if (got === exp) { pass++; }
  else { fail++; fails.push(name + '\n     got: ' + JSON.stringify(got) + '\n     exp: ' + JSON.stringify(exp)); }
}
function ok(name, cond, detail) {
  if (cond) { pass++; } else { fail++; fails.push(name + (detail ? ' — ' + detail : '')); }
}

// ---------- 0. 抠函数（保证测的是真实文件内容）----------
const src = fs.readFileSync(FILE, 'utf8');
function grab(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('函数缺失: ' + name);
  let depth = 0, i = src.indexOf('{', start);
  for (let j = i; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') { depth--; if (depth === 0) return src.slice(start, j + 1); }
  }
  throw new Error('函数括号不闭合: ' + name);
}
eval(grab('escapeHtml') + '\n' + grab('mdToHtml'));

// ---------- 1. 基础渲染 ----------
eq('粗体去星号', mdToHtml('**寻求专业帮助**'), '<b>寻求专业帮助</b>');
eq('主人截图的真实句式', mdToHtml('6. **寻求专业帮助**：如果失眠问题持续存在'),
   '<ol class="md-ol" start="6"><li><b>寻求专业帮助</b>：如果失眠问题持续存在</li></ol>');
eq('斜体', mdToHtml('*注意*'), '<i>注意</i>');
eq('行内代码', mdToHtml('用 `ollama list` 查看'),
   '用 <code class="md-code">ollama list</code> 查看');

// ---------- 2. 块级元素 + start 序号修复 ----------
eq('h1', mdToHtml('# 标题'), '<div class="md-h md-h1">标题</div>');
eq('无序列表', mdToHtml('- 甲\n- 乙'), '<ul class="md-ul"><li>甲</li><li>乙</li></ul>');
eq('有序列表从1起不带start', mdToHtml('1. 甲'), '<ol class="md-ol"><li>甲</li></ol>');
eq('有序列表从6起带start（序号不丢）', mdToHtml('6. 己'), '<ol class="md-ol" start="6"><li>己</li></ol>');
eq('引用', mdToHtml('> 引用'), '<div class="md-quote">引用</div>');
eq('分隔线', mdToHtml('---'), '<hr class="md-hr">');
eq('列表内嵌粗体', mdToHtml('- **重点**：说明'), '<ul class="md-ul"><li><b>重点</b>：说明</li></ul>');

// ---------- 3. 流式容错（关键，防止打字抖动）----------
eq('未闭合粗体原样保留', mdToHtml('这是**重要'), '这是**重要');
eq('未闭合行内代码原样保留', mdToHtml('用 `ollama'), '用 `ollama');
eq('单个星号不当语法', mdToHtml('2*3=6'), '2*3=6');
eq('空输入不崩', mdToHtml(''), '');
eq('null 输入不崩', mdToHtml(null), '');

// ---------- 4. XSS 防护 ----------
eq('script 被转义', mdToHtml('<script>alert(1)</script>'), '&lt;script&gt;alert(1)&lt;/script&gt;');
eq('img onerror 被转义', mdToHtml('<img src=x onerror=alert(1)>'), '&lt;img src=x onerror=alert(1)&gt;');
ok('粗体包裹的注入不逃逸', mdToHtml('**<b>x</b>**') === '<b>&lt;b&gt;x&lt;/b&gt;</b>', mdToHtml('**<b>x</b>**'));

// ---------- 5. 接线检查（4 处调用点 + 样式）----------
ok('有 mdToHtml 定义', /function mdToHtml\s*\(/.test(src));
ok('流式回答走 mdToHtml', /full \+= data\.delta;[\s\S]{0,120}bubble\.innerHTML = mdToHtml\(full\)/.test(src));
ok('图片解读走 mdToHtml', /full = data\.answer[\s\S]{0,120}bubble\.innerHTML = mdToHtml\(full\)/.test(src));
ok('回答气泡无残留 textContent 直填', !/bubble\.textContent = full/.test(src));
ok('addMsg 对 bot 走 mdToHtml', /role === 'bot'\)\s*inner = mdToHtml\(text\)/.test(src));
ok('历史回放不再双重转义', /addMsg\('bot', h\.answer, h\.sources\)/.test(src) && !/addMsg\('bot', escapeHtml\(h\.answer\)/.test(src));
ok('用户提问由 addMsg 内部转义', !/addMsg\('user', escapeHtml\(question\)\)/.test(src));
ok('生成列表用 start 保留序号', /start="' \+ num \+ '"/.test(src));
ok('CSS 含 md-ol 样式', /\.md-ol li::marker/.test(src));
ok('CSS 含粗体样式', /\.msg \.bubble b[^{]*\{[^}]*font-weight: 700/.test(src));
ok('备份文件存在', fs.existsSync(FILE + '.bak-mdrender'));

// ---------- 汇总 ----------
console.log('===== 医小喵 Markdown 渲染 · 改后文件独立验证 =====');
console.log('目标文件: ' + FILE);
if (fails.length) { console.log('\n失败明细:'); fails.forEach(f => console.log('  ❌ ' + f)); }
console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
