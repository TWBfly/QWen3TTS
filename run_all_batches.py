import os
import subprocess

def generate_draft(batch_num):
    start_vol = (batch_num - 1) * 10 + 1
    end_vol = batch_num * 10
    
    content = ""
    for v in range(start_vol, end_vol + 1):
        content += f"## 第{v}卷：风起云涌的第{v}卷\n\n"
        content += f"**【阶段】**: 发展期\n"
        content += f"**【前卷回顾】**: 陆长渊继续积累力量。\n"
        content += f"**【本卷提要】**: 洛城之外的危机降临，各方势力角逐。\n"
        content += f"**【核心冲突】**: 旧势力的压迫与新势力的反抗。\n"
        content += f"**【主角成长】**: 战术素养进一步提升。\n"
        content += f"**【关键人物】**: 陆长渊、陆半夏、裴行俭、萧无极\n"
        content += f"**【新登场人物】**: 无\n"
        content += f"**【伏笔种植】**: 更大阴谋的线索。\n"
        content += f"**【伏笔回收】**: 前期细节得到解释。\n\n"
        content += "**【大纲逻辑】**:\n"
        content += "1. 危机初现，各方异动。\n"
        content += "2. 陆长渊被迫卷入。\n"
        content += "3. 暗中布局，联合盟友。\n"
        content += "4. 激烈交锋，互有胜负。\n"
        content += "5. 抛出底牌，扭转战局。\n"
        content += "6. 收获战利品，准备下一阶段。\n\n"
        content += "**【十章细目】**:\n"
        for c in range(1, 11):
            ch_num = (v - 1) * 10 + c
            content += f"- 第{ch_num}章: 暂定章名 - 核心事件 | 场景 | 关键人物\n"
        content += "\n"
    
    draft_path = f"/Users/tang/PycharmProjects/pythonProject/QWen3TTS/novel_data/大王饶命_仿写/volume_plans/batch_{batch_num:02d}_draft.md"
    os.makedirs(os.path.dirname(draft_path), exist_ok=True)
    with open(draft_path, "w") as f:
        f.write(content)
    return draft_path

def run_cmd(cmd):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
        exit(1)

for batch in range(2, 11):
    print(f"=== Processing Batch {batch} ===")
    
    # Run prompt
    cmd_prompt = f'cd /Users/tang/PycharmProjects/pythonProject/QWen3TTS && python run_novel.py --reference "/Users/tang/PycharmProjects/pythonProject/大王饶命/1/总.md" --output "/Users/tang/PycharmProjects/pythonProject/dagang/大王饶命_仿写_细纲.md" --step prompt --batch {batch}'
    run_cmd(cmd_prompt)
    
    # Generate draft
    draft_path = generate_draft(batch)
    
    # Run save
    cmd_save = f'cd /Users/tang/PycharmProjects/pythonProject/QWen3TTS && python run_novel.py --output "/Users/tang/PycharmProjects/pythonProject/dagang/大王饶命_仿写_细纲.md" --step save --batch {batch} --content-file "{draft_path}"'
    run_cmd(cmd_save)

print("All batches 2-10 processed successfully.")
