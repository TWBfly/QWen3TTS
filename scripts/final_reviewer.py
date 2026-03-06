"""
Final Story Reviewer (终局大纲审查器)
在 100 卷 (1000章) 大纲生成完毕后，自动执行终局检测与大纲审视。
该脚本会生成供用户调用的 Prompt，或者直接通过 LLM API 进行打分、评估和修复建议。
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

def generate_review_prompt(novel_name: str, output_path: str) -> str:
    """生成最终审查的 Prompt"""
    
    prompt = f"""【任务目标】
你是一位经验丰富的故事结构分析师和创意写作顾问，擅长评估和优化小说大纲，帮助作者打造引人入胜的故事架构。
现在，请你对这份完成了100卷（1000章）的《{novel_name}》大纲进行终局评估和深度体检。

【审查纪律（不可逾越的红线）】
1. 必须保持背景风格统一，必须在一个世界观下，不可出现赛博朋克，不可出现星际科幻，不可出现作者维度。
2. 严格禁止“科幻”、“星际”、“AI”、“程序”、“物理宇宙”、“数据流”、“锚点”、“外星人”、“银河系”、“宇宙”、“时间旅行”、“平行世界”、“维度”、“位面”、“逻辑武器”、“科幻修仙”、“缸中之脑”、“直播”、“天道”、“奇点”、“元宇宙”、“虚拟现实”、“数字生命”等概念。
3. 严禁一直换地图打架升级！必须：写的人物与剧情极为细致，节奏放慢，必须让 1000 章（100 卷）的内容朝着神作方向深耕，草蛇灰线，伏笔千里，而不是流水线写作。
4. 除了主线，必须有支线，暗线，甚至是多线并进，极致刻画人物和其他配角，让读者对配角也产生共鸣，贯彻“三幕九线”写作手法。
5. 核心铁律：每个人物都是主角，每个人物都有自己的故事线，每个人物都有自己的高光时刻。

【你需要输出的评估报告结构】
请严格按照以下结构输出，只需严厉指出问题，不需要说客套话，不需要给出优点：

1. **综合打分**（满分10分）：给出最终得分，并用一句话说明扣分核心原因。
2. **大纲总体不足与剧情问题**：指出剧情脉络中的核心硬伤与毒点（尤其是是否触犯了上述禁忌红线）。
3. **逻辑断层检查**：尖锐指出章节与章节、卷与卷之间的逻辑断层、战力崩塌点、人物行为动机不连贯处。
4. **伏笔与呼应评估**：分析前文埋下的长线伏笔是否在后文巧妙回收，是否存在“挖坑不埋”或“强行回收（机器降神）”的拙劣手法。
5. **核心冲突与节奏递进**：判断全书的核心冲突（如：权力博弈、生存抗争等）是否贯穿始终？判断中后期冲突的规模与层次是否递进升级，是否出现了“倒V字崩塌”（比如前期毁天灭地，后期反而去和村长斗智斗勇）？
6. **具体可行的修复与优化建议**：提供精准到卷/章层面的修改策略，帮助作者将这部大纲拉高到真正的“神作”水准。

【待评估大纲片段/全文】
请读取以下大纲内容并开始你的无情审视：

(注意：由于大纲长达100卷，请通过 IDE 查阅上述文件内容) -> 路径: {output_path}
"""
    return prompt

def main():
    parser = argparse.ArgumentParser(description="终局大纲审查器")
    parser.add_argument("--novel-name", type=str, required=True, help="小说名称")
    parser.add_argument("--outline-path", type=str, required=True, help="大纲输出路径")
    parser.add_argument("--output-prompt", type=str, default=None, help=" Prompt的保存路径")
    
    args = parser.parse_args()
    
    prompt = generate_review_prompt(args.novel_name, args.outline_path)
    
    if args.output_prompt:
        out_path = Path(args.output_prompt)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"\n✅ 终局审查 Prompt 已生成并保存至:\n   {args.output_prompt}")
        print("\n👉 请直接在 IDE 中读取该文件，并让 AI 开始执行最终的大纲修复评估任务。")
    else:
        print("\n" + "="*80)
        print("以下是终局审查的 Prompt 内容：\n")
        print(prompt)
        print("="*80)

if __name__ == "__main__":
    main()
