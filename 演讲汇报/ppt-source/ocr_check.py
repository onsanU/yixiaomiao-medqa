# -*- coding: utf-8 -*-
"""OCR 抽查 PPT 预览图渲染质量：整行糊/乱码/低置信 = 渲染层问题
用法: PYTHONPATH=$HOME/.local/lib/python3.12/site-packages python3 ocr_check.py [预览目录]
退出码: 0=全通过, 1=有低置信行
"""
import os, sys, datetime
from rapidocr_onnxruntime import RapidOCR

D = sys.argv[1] if len(sys.argv) > 1 else '/mnt/d/tmp/meow-ppt'
SAMPLES = ['deck1-slide01.png', 'deck1-slide05.png', 'deck1-slide10.png',
           'deck1-slide16.png', 'deck1-slide22.png', 'deck1-slide23.png']
THRESHOLD = 0.55

ocr = RapidOCR()
bad = 0
for name in SAMPLES:
    p = os.path.join(D, name)
    if not os.path.exists(p):
        print(f'❌ {name} 不存在（预览未导出？）')
        bad += 1
        continue
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M')
    res, _ = ocr(p)
    lines = [(t, c) for _, t, c in res] if res else []
    low = [f'{t}({c:.2f})' for t, c in lines if c < THRESHOLD]
    status = '⚠️ 低置信' if low else '✅'
    print(f'{status} {name}  时间={ts}  行数={len(lines)}  抽样: {" | ".join(t for t, _ in lines[:2])}')
    if low:
        bad += 1
        print('     低置信行: ' + ' / '.join(low[:6]))

print()
if bad:
    print(f'❌ 视觉层检查失败：{bad} 个采样页异常')
    sys.exit(1)
print('✅ 视觉层检查通过：所有采样页无低置信行（无叠影/乱码）')
