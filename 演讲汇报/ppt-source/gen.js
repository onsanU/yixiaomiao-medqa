// gen.js —— 基于 Qwen3.5-4B 的医疗专家大模型微调与部署 · 团队总 deck
// 内容来源：《汇报材料_医疗专家微调全流程.md》（全部为真实实测数据）
const pptxgen = require('pptxgenjs');
const H = require('./helpers.js');
const { C, FONT, MONO } = H;

const OUT_FILE = process.env.OUT_FILE || '/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa/演讲汇报/汇报PPT_医疗专家微调.pptx';

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';   // 10 x 5.625 in
pres.author = '医疗专家模型微调小组';
pres.title = '基于 Qwen3.5-4B 的医疗专家大模型微调与部署';

// ============ 01 封面 ============
{
  const s = pres.addSlide();
  H.cover(s, {
    kicker: '泰迪实训《基于 DeepSeek 大模型微调的医疗专家模型》· 课程汇报',
    title: '基于 Qwen3.5-4B 的医疗专家',
    title2: '大模型微调与部署',
    desc: '从环境准备、数据清洗、QLoRA 微调、显存调优，到 GGUF 量化、Ollama 部署，\n最终把微调成果真实上线到团队自研医疗问答应用「医小咪」',
    meta: '汇报小组：4 人    ｜    汇报时长：不少于 30 分钟    ｜    现场运行代码 + 展示运行结果',
    foot: '技术栈：Qwen3.5-4B · QLoRA · peft · bitsandbytes · llama.cpp · Ollama · FastAPI',
  });
}

// ============ 02 目录 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: 'CONTENTS', title: '汇报目录', page: 2,
    tagRight: '九大模块 + 附录',
  });
  const chapters = [
    ['01', '项目背景与目标', '行业痛点 · 项目定位'],
    ['02', '技术选型与整体方案', '模型 / 方法 / 流程'],
    ['03', '环境准备', '软件栈 · 模型下载'],
    ['04', '数据准备与处理', '切分 · 查重 · 格式转换'],
    ['05', 'QLoRA 微调实现', '原理 · 核心参数 · 防OOM'],
    ['06', '训练执行与调优', '真实数据 · 碎片化救场'],
    ['07', '效果验证', '三版本公平对比'],
    ['08', '部署上线', '合并 · 量化 · Ollama · 集成'],
    ['09', '总结与展望', '成果 · 后续方向'],
    ['A', '附录', '演示清单 · 问题记录'],
  ];
  const colW = 4.4, gapX = 0.2;
  chapters.forEach((ch, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col * (colW + gapX);
    const y = 1.3 + row * 0.72;
    H.card(s, { x, y, w: colW, h: 0.6, fill: C.CARD });
    H.tag(s, { x: x + 0.14, y: y + 0.15, w: 0.52, h: 0.3, text: ch[0], size: 11 });
    s.addText(ch[1], {
      x: x + 0.78, y: y + 0.06, w: colW - 0.9, h: 0.26,
      fontSize: 12, bold: true, color: C.TXT, fontFace: FONT,
    });
    s.addText(ch[2], {
      x: x + 0.78, y: y + 0.31, w: colW - 0.9, h: 0.24,
      fontSize: 9, color: C.SUB, fontFace: FONT,
    });
  });
}

// ============ 03 项目背景 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '01 · 项目背景与目标', title: '人工智能赋能医疗的迫切性', page: 3,
    tagRight: '数据来源：课程 PPT',
  });
  const sw = 2.9, gap = 0.15;
  H.statCard(s, { x: 0.5, y: 1.28, w: sw, h: 1.05, num: '40%', label: '基层医疗机构误诊率', accent: C.BAD });
  H.statCard(s, { x: 0.5 + (sw + gap), y: 1.28, w: sw, h: 1.05, num: '5%', label: '三甲医院误诊率', accent: C.OK });
  H.statCard(s, { x: 0.5 + 2 * (sw + gap), y: 1.28, w: sw, h: 1.05, num: '20,000 条', label: '课程提供医疗问答数据集', accent: C.ACCENT });

  H.table(s, {
    x: 0.5, y: 2.62, w: 9.0,
    headers: ['行业痛点', '具体表现'],
    colW: [2.5, 6.5],
    rowH: 0.55,
    rows: [
      ['医疗资源分布不均', '基层医疗机构误诊率高达 40%，而三甲医院仅 5%'],
      ['复杂病例分析效率低', '跨学科病例需多科室会诊，耗时长、成本高'],
      ['医学知识更新滞后', '一线医生的知识更新速度滞后于医学研究进展'],
    ],
    size: 11,
  });

  H.callout(s, {
    x: 0.5, y: 4.48, w: 9.0, h: 0.6,
    text: '结论：医疗场景需要更精准、更专业、能跟上知识更新的 AI 助手 —— 这正是本项目要解决的问题。',
    line: C.ACCENT, size: 11,
  });
}

// ============ 04 通用模型瓶颈 + 项目目标 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '01 · 项目背景与目标', title: '通用大模型的医疗瓶颈 → 本项目目标', page: 4,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.0, text: '通用模型在医疗场景的三大短板' });
  H.bulletsHL(s, {
    x: 0.68, y: 1.82, w: 4.0, size: 11.5, spaceAfter: 9,
    items: [
      ['专业术语理解偏差', '“转移”在医学语境里 = 癌症扩散'],
      ['逻辑推理严谨性不足', '忽略过敏史等上下文 → 可能推荐禁忌药物'],
      ['知识更新滞后', '依赖过时的临床指南'],
    ],
  });

  H.card(s, { x: 5.15, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 5.33, y: 1.42, w: 4.0, text: '本项目目标' });
  s.addText('微调，是增强大模型原生能力的最佳方法。', {
    x: 5.33, y: 1.84, w: 4.0, h: 0.34,
    fontSize: 12, bold: true, color: C.ACCENT2, fontFace: FONT,
  });
  s.addText('用专业医疗数据对通用模型做专项提升，训练一个「医疗专家模型」，使其为医疗场景提供精准服务。', {
    x: 5.33, y: 2.22, w: 4.0, h: 0.9,
    fontSize: 11, color: C.BODY, fontFace: FONT, lineSpacing: 17, valign: 'top',
  });
  H.callout(s, {
    x: 5.33, y: 3.22, w: 4.0, h: 1.6, fill: '16305C', line: C.OK, size: 11,
    text: '我们不止于“训练完就结束”：\n把微调成果真实部署上线，升级团队自研的医疗问答应用「医小咪」，让微调模型直接服务真实用户。',
  });
}

// ============ 05 技术选型 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '02 · 技术选型与整体方案', title: '模型与方法选择（体现自主性）', page: 5,
    tagRight: '课程允许自选模型',
  });
  H.table(s, {
    x: 0.5, y: 1.28, w: 9.0,
    headers: ['项目', '选择', '理由'],
    colW: [1.3, 2.4, 5.3],
    rowH: 0.62, size: 10, headSize: 10.5,
    rows: [
      ['基座模型', 'Qwen3.5-4B', '课程推荐 DeepSeek-R1-Distill 但允许自选；选 Qwen 系可无缝部署回自研医小咪'],
      ['参数量', '4B', '8G 显存笔记本可训练；1.5B 效果有限，7B/8B 显存放不下'],
      ['微调方法', 'QLoRA', '4bit 量化省显存 + LoRA 只训少量参数，消费级显卡的标准方案'],
      ['训练数据', 'medical_cot_zh.jsonl', '课程提供 2W 条医疗问答，Question / Complex_CoT / Response 三字段'],
    ],
  });
  const sw = 2.9, gap = 0.15;
  H.statCard(s, { x: 0.5, y: 4.12, w: sw, h: 0.95, num: 'RTX 5070 · 8GB', label: 'GPU 显存（全项目最大挑战）', accent: C.WARN, numSize: 15 });
  H.statCard(s, { x: 0.5 + (sw + gap), y: 4.12, w: sw, h: 0.95, num: '16GB / WSL 12GB', label: '主机内存与 WSL 分配', accent: C.ACCENT, numSize: 15 });
  H.statCard(s, { x: 0.5 + 2 * (sw + gap), y: 4.12, w: sw, h: 0.95, num: 'Windows + WSL2', label: '运行环境（Ubuntu）', accent: C.ACCENT2, numSize: 15 });
}

// ============ 06 整体流程 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '02 · 技术选型与整体方案', title: '整体流程落地（课程 PPT Slide 5 → 本项目 11 步）', page: 6,
  });
  s.addText('课程给出的核心流程', { x: 0.5, y: 1.24, w: 4.0, h: 0.26, fontSize: 10.5, bold: true, color: C.ACCENT, fontFace: FONT });
  H.flow(s, {
    x: 0.5, y: 1.55, w: 9.0, h: 0.42, size: 9,
    items: ['环境准备', '模型准备', '数据准备', '数据格式整理转换', '微调参数设置'],
  });
  s.addText('本项目的完整落地链路（多走 6 步一直到上线）', { x: 0.5, y: 2.18, w: 6.0, h: 0.26, fontSize: 10.5, bold: true, color: C.ACCENT2, fontFace: FONT });
  H.flow(s, {
    x: 0.5, y: 2.5, w: 9.0, h: 0.42, size: 9,
    items: ['模型下载(ModelScope)', '数据切分/查重/查重叠', 'R1 风格格式转换', 'QLoRA 微调', '效果验证'],
  });
  H.flow(s, {
    x: 0.5, y: 3.02, w: 9.0, h: 0.42, size: 9,
    items: ['LoRA CPU 合并', 'GGUF 转换', 'Q4_K_M 量化', 'Ollama 部署', '应用集成上线医小咪'],
  });
  H.callout(s, {
    x: 0.5, y: 3.68, w: 9.0, h: 1.36, fill: C.CARD, line: C.BORDER, size: 11,
    text: '三个「多走的一步」是本项目的加分项：\n① 数据卫生（查重 + 新旧数据零重叠比对）—— 保证训练数据干净\n② 效果验证的省显存公平对比 —— 同一份基座轮换适配器，结果可比\n③ 真实部署上线 —— 不停留在实验，直接服务真实用户',
  });
}

// ============ 07 模型下载 + 训练前铁律 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '03 · 环境准备', title: '模型下载 与 训练前铁律', page: 7,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.0, text: '模型下载：魔搭 ModelScope（国内快）' });
  H.code(s, {
    x: 0.68, y: 1.82, w: 4.0, h: 1.3, size: 9,
    text: 'from modelscope import snapshot_download\nsnapshot_download(\n  "Qwen/Qwen3.5-4B",\n  local_dir="Qwen3.5-4B-Instruct")',
  });
  H.bulletsHL(s, {
    x: 0.68, y: 3.2, w: 4.0, h: 1.7, size: 10.5, spaceAfter: 6,
    items: [
      ['实测 ~11 MB/s', '9.3GB 权重约 10-15 分钟'],
      ['踩坑：魔搭网页 200 是假象', 'SPA 页面永远返回 200，必须用\napi/v1/models/<repo> 探测真实性'],
    ],
  });

  H.card(s, { x: 5.15, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 5.33, y: 1.42, w: 4.0, text: '训练前两条铁律' });
  H.bulletsHL(s, {
    x: 5.33, y: 1.84, w: 4.0, size: 11, spaceAfter: 8,
    items: [
      ['微调前必须停掉 Ollama', 'Ollama 常驻会占约 6.3G 显存，\\n不释放根本训不动'],
      ['训练前显存必须为 0 MiB', 'nvidia-smi 确认无占用再启动训练'],
      ['8G 显存 = 全项目最大约束', '后续所有参数调优都是为它服务'],
    ],
  });
  H.callout(s, {
    x: 5.33, y: 3.9, w: 4.0, h: 0.95, fill: '16305C', line: C.BAD, size: 10,
    text: '⚠️ 微调期间医小咪问答会临时下线 —— 已在项目流程中提前告知使用者。',
  });
}

// ============ 08 数据准备 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '04 · 数据准备与处理', title: '源数据 与 数据切分策略', page: 8,
  });
  H.card(s, { x: 0.5, y: 1.26, w: 9.0, h: 1.24, fill: C.CARD });
  H.cardTitle(s, { x: 0.68, y: 1.36, w: 8.6, text: '源数据（课程提供）' });
  s.addText([
    { text: 'medical_cot_zh.jsonl', options: { fontSize: 11, bold: true, color: C.ACCENT2, fontFace: MONO } },
    { text: '    2 万条医疗问答 · 48MB · 字段：Question / Complex_CoT / Response', options: { fontSize: 10.5, color: C.BODY, fontFace: FONT } },
  ], { x: 0.68, y: 1.7, w: 8.6, h: 0.28 });
  s.addText('示例：Q「一个 1 岁小孩在夏季头皮上长了些小结节……」 → R「从中医角度看，症状符合“蝼蛄疖”……」', {
    x: 0.68, y: 2.02, w: 8.6, h: 0.34,
    fontSize: 10, color: C.SUB, fontFace: FONT, italic: true,
  });

  s.addText('小步快跑 → 增量续训（三档递进）', {
    x: 0.5, y: 2.68, w: 6.0, h: 0.28, fontSize: 11.5, bold: true, color: C.ACCENT2, fontFace: FONT,
  });
  H.table(s, {
    x: 0.5, y: 3.02, w: 9.0,
    headers: ['数据档', '用途', '实测训练时长'],
    colW: [2.2, 3.6, 3.2],
    rowH: 0.46, size: 10.5,
    rows: [
      ['60 条', '冒烟验证（先跑通全流程）', '2.6 分钟 / 4 步'],
      ['3000 条（去重后 2924）', '正式训练第 1 档', '约 2 小时 / 183 步'],
      ['2000 条（新增，与旧零重叠）', '增量续训第 2 档（共 5000 条知识）', '约 1.5–2.5 小时 / 123 步'],
    ],
  });
  H.callout(s, {
    x: 0.5, y: 4.62, w: 9.0, h: 0.5, size: 10.5,
    text: '策略价值：小档先验证流程，大档再正式跑；增量续训让模型在已有知识上继续学，不用从头重训。',
    line: C.ACCENT,
  });
}

// ============ 09 QLoRA 原理 + 核心参数 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '05 · QLoRA 微调实现', title: '为什么用 QLoRA（原理）', page: 9,
  });
  const cw = 2.9, gap = 0.15;
  const cards = [
    ['LoRA', '冻结原模型，只训练注入的低秩矩阵 A×B', '可训参数 4B → 42M', C.ACCENT],
    ['4bit NF4 量化', '把模型权重压缩到 4bit，8G 显存才装得下 4B 模型', '显存节省约 75%', C.OK],
    ['QLoRA', '4bit 量化 + LoRA 的组合，消费级显卡微调大模型的标准方案', '本项目采用的方案', C.ACCENT2],
  ];
  cards.forEach((c, i) => {
    const x = 0.5 + i * (cw + gap);
    H.card(s, { x, y: 1.26, w: cw, h: 1.72 });
    H.cardTitle(s, { x: x + 0.18, y: 1.4, w: cw - 0.36, text: c[0], size: 14 });
    s.addText(c[1], {
      x: x + 0.18, y: 1.78, w: cw - 0.36, h: 0.72,
      fontSize: 10.5, color: C.BODY, fontFace: FONT, lineSpacing: 16, valign: 'top',
    });
    H.tag(s, { x: x + 0.18, y: 2.56, w: Math.min(cw - 0.36, 2.1), h: 0.28, text: c[2], size: 9, fill: c[3] });
  });

  H.code(s, {
    x: 0.5, y: 3.14, w: 9.0, h: 1.44, size: 9.5,
    text: '# 核心参数（8G 显存实测调优结果）\nMAX_LEN = 704          # 8G 显存上限附近；超长样本直接过滤不截断（截断会教坏模型）\nEPOCHS = 1   BATCH = 1   GRAD_ACCUM = 16    # 等效 batch 16\nLR = 2e-4（首训）/ 1e-4（续训精修）    LORA_R = 32    LORA_ALPHA = 64\nOPTIM = "paged_adamw_8bit"   # 8bit 分页优化器省显存',
  });
  H.callout(s, {
    x: 0.5, y: 4.68, w: 9.0, h: 0.46, size: 10.5,
    text: '一句话总结：QLoRA 让 8G 显存的笔记本也能微调 4B 参数的大模型。',
    line: C.ACCENT,
  });
}

// ============ 10 防 OOM 三板斧 + 脚本结构 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '05 · QLoRA 微调实现', title: '8G 显存防 OOM 三板斧 + 训练脚本结构', page: 10,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.4, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.05, text: '防 OOM 三板斧（缺一不可）' });
  H.bulletsHL(s, {
    x: 0.68, y: 1.84, w: 4.05, size: 10.5, spaceAfter: 7,
    items: [
      ['① 先量化数据真实长度再定 MAX_LEN', '统计 token 分位数（实测均值 505 / P95 712 / max 1189），MAX_LEN=768 只丢 2.1% 超长样本'],
      ['② 超长样本过滤，不截断', 'batch=1 时显存峰值由批内最长样本决定；截断 = 答案不完整，会教坏模型'],
      ['③ 梯度检查点 + 8bit 分页优化器', '前向重算换显存，缺一不可'],
    ],
  });
  H.callout(s, {
    x: 0.68, y: 3.94, w: 4.05, h: 0.94, fill: '16305C', line: C.WARN, size: 10,
    text: '血泪收敛过程：MAX_LEN = 2048 / 1536 / 1024 全部 OOM 崩过，768 才稳定，续训版留余量降到 704。',
  });

  H.code(s, {
    x: 5.1, y: 1.28, w: 4.4, h: 3.72, size: 9,
    text: 'finetune_qwen35_medical.py 结构\n\n① 读数据 → build_text() 拼 R1 格式\n② 加载 4bit 基座\n   (BitsAndBytesConfig NF4)\n③ 挂 LoRA\n   (get_peft_model /\n    PeftModel.from_pretrained)\n④ 并行 tokenize（超长过滤）\n⑤ Trainer 训练\n   存档策略：每 8 步一档，留 3 档\n   → 断电可从最近档续上\n⑥ save_pretrained 保存 adapter\n\n增量续训脚本额外关键点：\nPeftModel.from_pretrained(\n  base, 旧LoRA, is_trainable=True)\n⚠️ 必须 is_trainable=True —— adapter\n配置里存的是推理态，不显式解冻会\n得到「可训参数 0.0M」→ 训练白跑',
  });
}

// ============ 11 训练执行 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '06 · 训练执行与调优', title: '训练过程（真实数据）', page: 11,
  });
  H.table(s, {
    x: 0.5, y: 1.28, w: 9.0,
    headers: ['数据档', '步数', '实测时长', '最终 loss'],
    colW: [2.4, 1.5, 2.7, 2.4],
    rowH: 0.5, size: 10.5,
    rows: [
      ['60 条冒烟验证', '4 步', '2.6 分钟', '2.41'],
      ['3000 条件正式训练', '183 步', '约 2 小时', '1.9 ~ 2.0 区间'],
      ['续训 2000 条（共 5000）', '123 步', '约 1.5–2.5 小时（含救场）', '2.02 ~ 2.16 波动下降'],
    ],
  });
  H.code(s, {
    x: 0.5, y: 2.92, w: 9.0, h: 1.28, size: 9.5,
    text: '# 启动训练\ncd ~/medical-ft\n~/shixun-venv/bin/python finetune_qwen35_medical_cont2000.py\n\n# 断电 / 中断后：从断点续训（进度零丢失）\nRESUME_CKPT=~/medical-ft/ckpt-5000/checkpoint-XX ~/shixun-venv/bin/python finetune_qwen35_medical_cont2000.py',
  });
  H.callout(s, {
    x: 0.5, y: 4.36, w: 9.0, h: 0.74, size: 10.5,
    text: '工程化设计：正式训练开存档（每 20 分钟一档，保留 3 档），配合断点续训 —— 2000 条续训档全程中断 4 次，进度一次没丢、从未从头重跑。',
    line: C.OK,
  });
}

// ============ 12 碎片化救场 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '06 · 训练执行与调优', title: '8G 显存碎片化救场（本项目最硬核经验）', page: 12,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.0, text: '现象 与 诊断铁证' });
  s.addText('步速从正常的 40s/步 突然恶化到 100 ~ 300s/步，而 GPU 功耗只有约 35W —— 显卡在「空转整理碎片」。', {
    x: 0.68, y: 1.8, w: 4.0, h: 0.62, fontSize: 10.5, color: C.BODY, fontFace: FONT, lineSpacing: 16, valign: 'top',
  });
  H.code(s, {
    x: 0.68, y: 2.5, w: 4.0, h: 1.46, size: 9,
    text: '显存 7874 / 8151 MiB（96.6% 顶满）\nSM 利用率 98% 但功耗仅 ~40W\n  → GPU 在「等」（碎片整理）\npclk 锁 1500MHz\nmclk 满血 9001MHz\n  → 不是省电模式，就是碎片化',
  });
  H.callout(s, {
    x: 0.68, y: 4.08, w: 4.0, h: 0.8, fill: '16305C', line: C.WARN, size: 9.5,
    text: '排查还要先排除干扰项：Windows 电源计划、Defender 定时扫描都已确认不是元凶。',
  });

  H.card(s, { x: 5.15, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 5.33, y: 1.42, w: 4.0, text: '解法（进度零丢失）' });
  H.flow(s, {
    x: 5.33, y: 1.82, w: 4.0, h: 0.4, size: 9,
    items: ['kill 进程', 'resume 最近档', '显存池清空', '恢复 40s/步'],
  });
  H.bullets(s, {
    x: 5.33, y: 2.36, w: 4.0, size: 10.5, spaceAfter: 8, lineSpacing: 16,
    items: [
      '实战救场 4 次，123 步完整训完，从未从头重跑',
      'resume 失败时退一档 checkpoint 再试（checkpoint-72 比 -80 更干净）',
      '判断真实步速只看 checkpoint 落盘时间戳 —— tqdm 显示会骗人',
    ],
  });
  H.callout(s, {
    x: 5.33, y: 4.08, w: 4.0, h: 0.8, fill: '16305C', line: C.OK, size: 9.5,
    text: '这条经验的价值：8G 显卡训 4B 模型，「中途变慢 / OOM」是常态而非异常，checkpoint + resume 就是为它设计的。',
  });
}

// ============ 13 实测对比结果 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '07 · 效果验证', title: '实测对比结果（原版 vs 3000 档 vs 5000 档）', page: 13,
  });
  H.table(s, {
    x: 0.5, y: 1.28, w: 9.0,
    headers: ['测试题目', '原版 qwen3.5:4b', '3000 档', '5000 档（续训）'],
    colW: [3.0, 2.1, 1.9, 2.0],
    rowH: 0.62, size: 10, markBad: true,
    rows: [
      ['① 中医：小孩头皮疮疡流脓', 'x卡英文 think 想不出结果', '!空 think 直接辨证论治', '!更快更稳'],
      ['② 西医考点：胸水性质检查', 'x卡英文 think', 'x同样卡英文 think', '!答出「胸水 ADA 活性测定」'],
      ['③ 失眠建议', 'x中文 think 啰嗦半截', 'x卡英文 think', '!分点专业回答'],
    ],
  });
  H.callout(s, {
    x: 0.5, y: 3.6, w: 9.0, h: 1.42, fill: C.CARD, line: C.OK, size: 11,
    text: '结论：微调让模型学会「医疗问答直接作答」，不再卡在英文思考里自说自话；\n知识量从 3000 → 5000 条后，西医考点题也能答对（胸水 ADA 是结核性胸膜炎的标准考点）。\n→ 知识灌注 + 行为对齐，双重生效。',
  });
}

// ============ 14 部署链路总览 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '08 · 部署上线', title: '部署链路总览（微调模型 → Ollama → 医小咪）', page: 14,
  });
  H.flow(s, {
    x: 0.5, y: 1.4, w: 9.0, h: 0.5, size: 8.5,
    items: ['LoRA\n182M', 'CPU 合并\nbf16 8.1G', 'convert\nGGUF f16 8.65G', 'quantize\nQ4_K_M 2.6G', 'ollama create\n2.8G', '医小咪\n上线'],
  });
  const sw = 2.17, gap = 0.1;
  H.statCard(s, { x: 0.5, y: 2.2, w: sw, h: 1.0, num: '108 s', label: 'CPU 合并 LoRA', accent: C.ACCENT, numSize: 17 });
  H.statCard(s, { x: 0.5 + (sw + gap), y: 2.2, w: sw, h: 1.0, num: '32 s', label: 'convert 转 GGUF', accent: C.ACCENT2, numSize: 17 });
  H.statCard(s, { x: 0.5 + 2 * (sw + gap), y: 2.2, w: sw, h: 1.0, num: '25 s', label: 'llama-quantize 量化', accent: C.ACCENT2, numSize: 17 });
  H.statCard(s, { x: 0.5 + 3 * (sw + gap), y: 2.2, w: sw, h: 1.0, num: '2.8 G', label: 'Ollama 最终体积', accent: C.OK, numSize: 17 });

  H.card(s, { x: 0.5, y: 3.4, w: 9.0, h: 1.6 });
  H.cardTitle(s, { x: 0.68, y: 3.52, w: 8.6, text: '关键决策：为什么走 CPU 合并' });
  H.bullets(s, {
    x: 0.68, y: 3.88, w: 8.6, size: 10.5, spaceAfter: 6, lineSpacing: 16,
    items: [
      '8G 显存放不下 bf16 全量模型（4B ≈ 8.8G）→ LoRA 合并改走 CPU（内存 11G，实测 108 秒完成）',
      '合并必须保留原版权重，「Qwen3.5-4B-Instruct/」目录不能删 —— 删了以后无法再合并',
      '先量化成 Q4_K_M（与原版同级精度），再用 ollama create 建新名字 —— 原版永远保留，随时可回滚',
    ],
  });
}

// ============ 15 mtp 大坑 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '08 · 部署上线', title: 'Qwen3.5 多模态架构大坑（本项目最深教训）', page: 15,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.0, text: '现象：转换后的模型加载报错' });
  H.code(s, {
    x: 0.68, y: 1.84, w: 4.0, h: 1.0, size: 9,
    text: "tensor 'blk.32.attn_norm.weight'\nnot found\n\n（llama.cpp 与 Ollama 同报）",
  });
  s.addText('根因', { x: 0.68, y: 2.98, w: 4.0, h: 0.26, fontSize: 11.5, bold: true, color: C.ACCENT2, fontFace: FONT });
  s.addText('魔搭的 Qwen/Qwen3.5-4B 是多模态完整版，共 738 个张量 = text 主干 426 + mtp 15 + vision 297。LoRA 合并只导出 text 主干，config 里却还声明着 mtp 层 → 写完 block_count=33 却没有对应权重。', {
    x: 0.68, y: 3.24, w: 4.0, h: 1.6, fontSize: 10, color: C.BODY, fontFace: FONT, lineSpacing: 15, valign: 'top',
  });

  H.card(s, { x: 5.15, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 5.33, y: 1.42, w: 4.0, text: '正解：从原版权重补回 mtp 张量' });
  H.bullets(s, {
    x: 5.33, y: 1.86, w: 4.0, size: 10.5, spaceAfter: 8, lineSpacing: 16,
    items: [
      '从原版 safetensors 补回 15 个 mtp.* 张量，生成独立的 model.mtp.safetensors + index.json',
      '补齐后共 441 个张量，再 convert 一次成功',
      'vision 张量不需要补 —— 文本应用不会加载视觉分支',
      '踩过的弯路：把 mtp 声明改成 0 会触发 convert 断言崩溃，qwen35 转换强制要求带 mtp',
    ],
  });
  H.callout(s, {
    x: 5.33, y: 4.06, w: 4.0, h: 0.82, fill: '16305C', line: C.OK, size: 10,
    text: 'python patch_mtp_5000.py\n→ 补齐 15 个 mtp 张量，index.json 441 个张量',
  });
}

// ============ 16 Ollama 部署 + 换脑 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '08 · 部署上线', title: 'Ollama 部署 与 医小咪换脑', page: 16,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.0, text: '① Ollama 部署（新名字，可回滚）' });
  H.code(s, {
    x: 0.68, y: 1.84, w: 4.0, h: 1.5, size: 9,
    text: '# Modelfile-med3.txt\nFROM .../qwen35-med3-q4_k_m.gguf\nPARAMETER temperature 1\nPARAMETER top_k 20\nPARAMETER top_p 0.95\nPARAMETER presence_penalty 1.5',
  });
  H.code(s, {
    x: 0.68, y: 3.46, w: 4.0, h: 1.36, size: 9,
    text: '# 先本地 llama-server 验证再入库\nllama-server -m qwen35-med3-q4_k_m.gguf\n  -c 2048 --port 8099   # 看 "model loaded"\n\nollama create qwen3.5:4b-med3 -f Modelfile-med3.txt\nollama list   # 三版本并存，原版永远保留',
  });

  H.card(s, { x: 5.15, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 5.33, y: 1.42, w: 4.0, text: '② 应用集成（医小咪换脑）' });
  s.addText('模型名常量只有两处，不在 main.py 硬编码：', {
    x: 5.33, y: 1.8, w: 4.0, h: 0.28, fontSize: 10.5, color: C.BODY, fontFace: FONT,
  });
  H.code(s, {
    x: 5.33, y: 2.1, w: 4.0, h: 1.1, size: 9,
    text: '# app/rag.py（问答/护理计划/宠物/俳句）\nLLM_MODEL = "qwen3.5:4b-med3"\n\n# app/vision.py（看图 OCR 解读）\nTEXT_MODEL = "qwen3.5:4b-med3"',
  });
  H.bullets(s, {
    x: 5.33, y: 3.3, w: 4.0, size: 10, spaceAfter: 6, lineSpacing: 15,
    items: [
      '改前 cp 备份 → 改后 AST 静态验证（不 import，避免拉起 Chroma 副作用）',
      '重跑幂等 bash start.sh 重启 API，新模型生效',
      '设计上三版本并存：原版 4b / 3000 档 med / 5000 档 med3',
    ],
  });
  H.callout(s, {
    x: 5.33, y: 4.42, w: 4.0, h: 0.46, size: 10, line: C.OK,
    text: '换脑成功：医小咪主脑 = qwen3.5:4b-med3',
  });
}

// ============ 17 总结与展望 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '09 · 总结与展望', title: '成果与后续方向', page: 17,
  });
  H.card(s, { x: 0.5, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 0.68, y: 1.42, w: 4.0, text: '项目成果', color: C.OK });
  H.bulletsHL(s, {
    x: 0.68, y: 1.86, w: 4.0, size: 10.5, spaceAfter: 8, hlColor: C.OK,
    items: [
      ['全链路跑通', '环境 → 数据 → QLoRA 微调 → 验证 → 部署 → 应用集成'],
      ['数据规模达标', '3000 + 2000 条增量续训，共 5000 条医疗知识'],
      ['成果真实上线', '微调模型已服务医小咪用户，版本可回滚'],
      ['沉淀硬核经验', '8G 显存碎片化救场、Qwen3.5 mtp 补丁'],
    ],
  });

  H.card(s, { x: 5.15, y: 1.28, w: 4.35, h: 3.72 });
  H.cardTitle(s, { x: 5.33, y: 1.42, w: 4.0, text: '未来展望', color: C.ACCENT2 });
  H.bulletsHL(s, {
    x: 5.33, y: 1.86, w: 4.0, size: 10.5, spaceAfter: 9, hlColor: C.ACCENT2,
    items: [
      ['全量数据训练', '2W 条全量约需 15-20 小时挂机',
        '进一步提升知识覆盖度'],
      ['更多医疗场景评测', '方剂推荐准确率、病历结构化',
        '从问答走向实际业务'],
      ['数据质量清洗', '合成数据含噪声，人工校验子集',
        '数据干净 = 效果上限更高'],
    ],
  });
}

// ============ 18 附录：演示清单 ============
{
  const s = pres.addSlide();
  H.titleBar(s, {
    kicker: '附录 A', title: '现场演示脚本清单（8 个演示点）', page: 18,
  });
  H.table(s, {
    x: 0.5, y: 1.24, w: 9.0,
    headers: ['#', '演示内容', '预期结果', '耗时'],
    colW: [0.5, 3.3, 3.6, 1.6],
    rowH: 0.375, size: 9.5, headSize: 10, headH: 0.34,
    rows: [
      ['1', '环境展示（torch / cuda）', '2.11.0+cu128  True', '5 s'],
      ['2', '数据格式展示', '三字段 + R1 模板', '5 s'],
      ['3', '训练脚本讲解（QLoRA 参数）', '展示防 OOM 配置', '静态'],
      ['4', '现场小训练（60 条小档）', 'loss 下降 + adapter 保存', '约 3 分钟'],
      ['5', '效果对比推理 compare_4way.py', '5000 档直接中文作答', '约 4 分 20 秒'],
      ['6', '部署产物 ollama list', '三模型并存', '5 s'],
      ['7', '现场问答（医小咪页面）', '专业医疗回答', '10 s'],
      ['8', '自动化验证脚本', '15/15 断言通过', '30 s'],
    ],
  });
  H.callout(s, {
    x: 0.5, y: 4.7, w: 9.0, h: 0.44, size: 10,
    text: '原则：提前把脚本放好，按顺序跑；除演示点 4、5 外，其余演示点均在 30 秒内出结果。',
    line: C.ACCENT,
  });
}

// ============ 19 致谢 ============
{
  const s = pres.addSlide();
  H.bg(s);
  H.dotGrid(s, 0.55, 4.4, 5, 12, 0.16, C.BORDER, 0.03);
  H.decoRings(s, 8.15, 0.5, 1.55);
  s.addShape('rect', { x: 0.62, y: 1.9, w: 0.075, h: 1.3, fill: { color: C.ACCENT } });
  s.addText('谢谢聆听', {
    x: 0.85, y: 1.85, w: 8.0, h: 0.72, fontSize: 34, bold: true, color: C.TXT, fontFace: FONT,
  });
  s.addText('欢迎提问与交流', {
    x: 0.85, y: 2.6, w: 8.0, h: 0.44, fontSize: 16, color: C.ACCENT2, fontFace: FONT,
  });
  s.addShape('rect', { x: 0.85, y: 3.3, w: 8.3, h: 0.02, fill: { color: C.BORDER } });
  s.addText([
    { text: '演示环境 · ', options: { fontSize: 11, color: C.SUB, fontFace: FONT } },
    { text: 'http://localhost:8000', options: { fontSize: 11, color: C.ACCENT, fontFace: MONO } },
    { text: '   ｜   公网 · ', options: { fontSize: 11, color: C.SUB, fontFace: FONT } },
    { text: 'https://yixiaomiao.osanu.dpdns.org', options: { fontSize: 11, color: C.ACCENT, fontFace: MONO } },
  ], { x: 0.85, y: 3.45, w: 8.3, h: 0.3 });
  s.addText('小组：4 人    ｜    课程：泰迪《基于 DeepSeek 大模型微调的医疗专家模型》    ｜    2026 年 9 月', {
    x: 0.85, y: 3.85, w: 8.3, h: 0.3, fontSize: 10.5, color: C.SUB, fontFace: FONT,
  });
}

// ---------- 输出 ----------
pres.writeFile({ fileName: OUT_FILE }).then(f => {
  console.log('✅ 生成成功: ' + f);
  console.log('总页数: ' + pres.slides.length);
}).catch(e => {
  console.error('❌ 生成失败: ' + e);
  process.exit(1);
});
