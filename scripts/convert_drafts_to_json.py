#!/usr/bin/env python3
"""
将大王饶命_仿写的 batch_*_draft.md 批量大纲
逆向解析为 agent_driver.py 可消费的标准 input_v*.json 格式。
"""

import re
import json
import sys
from pathlib import Path


def parse_volume_block(text: str) -> dict:
    """解析单卷的 markdown 块为结构化字典"""
    vol = {}

    # 卷号与标题
    m = re.search(r'## 第(\d+)卷[：:](.+)', text)
    if m:
        vol['volume_number'] = int(m.group(1))
        vol['title'] = m.group(2).strip()
    else:
        return None

    # 阶段
    m = re.search(r'\*\*【阶段】\*\*[：:]\s*(.+)', text)
    vol['phase'] = m.group(1).strip() if m else ""

    # 本卷提要 → summary
    m = re.search(r'\*\*【本卷提要】\*\*[：:]\s*(.+)', text)
    vol['summary'] = m.group(1).strip() if m else ""

    # 核心冲突
    m = re.search(r'\*\*【核心冲突】\*\*[：:]\s*(.+)', text)
    vol['main_conflict'] = m.group(1).strip() if m else ""

    # 主角成长
    m = re.search(r'\*\*【主角成长】\*\*[：:]\s*(.+)', text)
    vol['protagonist_growth'] = m.group(1).strip() if m else ""

    # 关键人物 → key_characters
    m = re.search(r'\*\*【关键人物】\*\*[：:]\s*(.+)', text)
    if m:
        raw = m.group(1).strip()
        vol['key_characters'] = [c.strip() for c in re.split(r'[、，,]', raw) if c.strip()]
    else:
        vol['key_characters'] = []

    # 新登场人物 → new_characters（列表项）
    new_chars = []
    m = re.search(r'\*\*【新登场人物】\*\*[：:]\s*(.*?)(?=\n\*\*【|\n\n\*\*【大纲逻辑】)', text, re.DOTALL)
    if m:
        block = m.group(1)
        for line in block.strip().splitlines():
            line = line.strip()
            if line.startswith('-'):
                item = line.lstrip('-').strip()
                if item and item != '无' and not item.startswith('无新'):
                    new_chars.append(item)
    vol['new_characters'] = new_chars

    # 伏笔种植 → loops_to_plant
    loops_plant = []
    m = re.search(r'\*\*【伏笔种植】\*\*[：:]\s*(.+?)(?=\n\*\*【)', text, re.DOTALL)
    if m:
        raw = m.group(1).strip()
        if raw and raw != '无' and '无悬念' not in raw and '没有悬念' not in raw:
            # 按分号或句号分隔
            parts = re.split(r'[；;。]', raw)
            for p in parts:
                p = p.strip()
                if p and p != '无':
                    loops_plant.append(p)
    vol['loops_to_plant'] = loops_plant

    # 伏笔回收 → loops_to_resolve
    loops_resolve = []
    m = re.search(r'\*\*【伏笔回收】\*\*[：:]\s*(.+?)(?=\n\n|\n\*\*【)', text, re.DOTALL)
    if m:
        raw = m.group(1).strip()
        if raw and raw != '无' and raw != '无。':
            parts = re.split(r'[；;。]', raw)
            for p in parts:
                p = p.strip()
                if p and p != '无':
                    loops_resolve.append(p)
    vol['loops_to_resolve'] = loops_resolve

    # 十章细目 → key_events
    events = []
    m = re.search(r'\*\*【十章细目】\*\*[：:]?\s*\n(.*?)(?=\n\n## |\Z)', text, re.DOTALL)
    if m:
        block = m.group(1)
        for line in block.strip().splitlines():
            line = line.strip()
            if line.startswith('-'):
                event_text = line.lstrip('-').strip()
                if event_text:
                    events.append(event_text)
    vol['key_events'] = events

    return vol


def parse_batch_file(filepath: str) -> list:
    """解析一个 batch_*_draft.md 文件，返回卷列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按 "## 第X卷" 拆分
    vol_blocks = re.split(r'(?=## 第\d+卷)', content)
    volumes = []
    for block in vol_blocks:
        block = block.strip()
        if not block or not block.startswith('## 第'):
            continue
        vol = parse_volume_block(block)
        if vol:
            volumes.append(vol)
    return volumes


def main():
    novel_name = "大王饶命_仿写"
    data_dir = Path(__file__).parent.parent / "novel_data" / novel_name
    plans_dir = data_dir / "volume_plans"
    output_dir = Path(__file__).parent.parent  # JSON files go directly into the root dir for agent_driver

    if not plans_dir.exists():
        print(f"❌ 目录不存在: {plans_dir}")
        sys.exit(1)

    # 找到所有 batch draft 文件
    batch_files = sorted(plans_dir.glob("batch_*_draft.md"))
    if not batch_files:
        print(f"❌ 未找到 batch_*_draft.md 文件")
        sys.exit(1)

    print(f"找到 {len(batch_files)} 个 batch 文件")

    all_volumes = []
    for bf in batch_files:
        vols = parse_batch_file(str(bf))
        print(f"  📄 {bf.name}: {len(vols)} 卷 (卷{vols[0]['volume_number']}~{vols[-1]['volume_number']})" if vols else f"  ⚠️ {bf.name}: 0 卷")
        all_volumes.extend(vols)

    print(f"\n总计解析: {len(all_volumes)} 卷")

    # 按 10 卷一组输出 JSON
    for batch_idx in range(10):
        start_vol = batch_idx * 10 + 1
        end_vol = start_vol + 9
        batch_vols = [v for v in all_volumes if start_vol <= v['volume_number'] <= end_vol]

        if not batch_vols:
            print(f"  ⚠️ 批次 {batch_idx+1} (卷{start_vol}~{end_vol}): 无数据")
            continue

        output_data = {"volumes": batch_vols}
        output_file = output_dir / f"input_v{start_vol}-{end_vol}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"  ✅ 已生成: {output_file.name} ({len(batch_vols)} 卷)")

    # 验证
    total_chars = set()
    total_loops_plant = 0
    total_loops_resolve = 0
    total_events = 0
    for v in all_volumes:
        for c in v.get('key_characters', []):
            total_chars.add(c)
        for c in v.get('new_characters', []):
            # 提取名字部分
            name = re.split(r'[（(]', c)[0].strip()
            total_chars.add(name)
        total_loops_plant += len(v.get('loops_to_plant', []))
        total_loops_resolve += len(v.get('loops_to_resolve', []))
        total_events += len(v.get('key_events', []))

    print(f"\n{'='*60}")
    print(f"📊 解析统计:")
    print(f"   总卷数: {len(all_volumes)}")
    print(f"   独立角色名: {len(total_chars)} 个")
    print(f"   伏笔种植: {total_loops_plant} 条")
    print(f"   伏笔回收: {total_loops_resolve} 条")
    print(f"   章节事件: {total_events} 条")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
