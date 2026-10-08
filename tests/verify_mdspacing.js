#!/usr/bin/env node
/* hermes-verify: 医小喵 Markdown 段落间距优化 验证（2026-09-10 第二次迭代）
   目标：确认列表项之间不再出现「大空隙」，间距收敛为一行字高度
   方法：从真实 index.html 抠 mdToHtml，用历史库里主人的真实回答原文测
*/
const fs = require('fs');
const FILE = '/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa/app/static/index.html';
const src = fs.readFileSync(FILE, 'utf8');

function grab(name) {
  const start = src.indexOf('function ' + name + '(');
  let depth = 0, i = src.indexOf('{', start);
  for (let j = i; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') { depth--; if (depth === 0) return src.slice(start, j + 1); }
  }
}
eval(grab('escapeHtml') + '\n' + grab('mdToHtml'));

let pass = 0, fail = 0; const fails = [];
function ok(name, cond, detail) { cond ? pass++ : (fail++, fails.push(name + (detail ? '\n     ' + detail : ''))); }
function eq(name, got, exp) { got === exp ? pass++ : (fail++, fails.push(name + '\n     got: ' + JSON.stringify(got) + '\n     exp: ' + JSON.stringify(exp))); }

// ---------- 1. 主人截图里的真实回答原文（从 data/chat_history.db 取的实际格式）----------
const REAL = '根据资料，针对失眠问题需要注意以下几点：\n' +
  '\n' +
  '1.  **饮食调整**：避免摄入妨碍睡眠的食物，如咖啡、茶和酒。\n' +
  '2.  **改善环境**：注意卧室的光线、噪音、温度（过冷或过热）等因素，减少外界干扰。\n' +
  '3.  **关注情绪与作息**：资料提到七情（情绪）所伤是重要原因，若因身体疾病（如心脏病、高血压等）或生理变化导致失眠，需针对原发病处理。\n' +
  '4.  **用药建议**：在医生指导下适当服用催眠药可能是解决失眠的有效方法之一。\n' +
  '\n' +
  '*温馨提示：失眠成因复杂，涉及气、血、痰、瘀等多种病理因素。若症状严重或持续，请及时就医咨询专业医生。*';

const html = mdToHtml(REAL);
console.log('=== 渲染结果（\\n 显式化）===');
console.log(html.replace(/\n/g, '\\n\n'));
console.log();

// ---------- 2. 核心断言：<li> 之间不能有换行符（否则 pre-wrap 撑大间距）----------
ok('li 之间无换行符（间距不再被撑大）', !/<\/li>\n<li>/.test(html),
   '发现 </li>\\n<li> —— 会产生多余空行');
ok('ol 开标签后无换行', !/<ol[^>]*>\n/.test(html));
ok('ul 开标签后无换行', !/<ul[^>]*>\n/.test(html));
ok('块级标签前无换行', !/\n<(?:(?:ul|ol|li|di|hr))/i.test(html));
eq('列表项数正确（4项）', (html.match(/<li>/g) || []).length, 4);
ok('序号 start 保留', /<ol class="md-ol" start="1">/.test(html) || /<ol class="md-ol">/.test(html));

// ---------- 3. 段落语义仍保留（不把该有的间距也吃掉）----------
ok('缩进列表整体结构完整', /<ol class="md-ol"[^>]*>[\s\S]*<\/ol>/.test(html));
ok('斜体小提示仍渲染', /<i>温馨提示/.test(html));
ok('粗体仍渲染', /<b>饮食调整<\/b>/.test(html));
ok('段落文字仍保留', html.includes('根据资料，针对失眠问题需要注意以下几点：'));

// ---------- 4. 无空块残留 ----------
ok('没有空 <li></li>', !/<li><\/li>/.test(html));
ok('没有连续空标签', !/<\/li>\s*<\/li>/.test(html));

// ---------- 5. 回归：上一轮的渲染能力没被破坏 ----------
eq('粗体', mdToHtml('**重点**'), '<b>重点</b>');
eq('无序列表紧凑', mdToHtml('- 甲\n- 乙'), '<ul class="md-ul"><li>甲</li><li>乙</li></ul>');
eq('流式容错未闭合', mdToHtml('这是**重要'), '这是**重要');
eq('XSS 转义', mdToHtml('<script>x</script>'), '&lt;script&gt;x&lt;/script&gt;');
eq('纯文本单行', mdToHtml('你好喵'), '你好喵');
eq('空输入', mdToHtml(''), '');

console.log('===== 段落间距优化 · 改后文件验证 =====');
if (fails.length) { console.log('失败明细:'); fails.forEach(f => console.log('  ❌ ' + f)); }
console.log('\n通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
