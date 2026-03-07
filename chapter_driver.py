"""
Chapter Driver for IDE-Native Generation
Bridges the gap between the Story Bible state and the IDE Assistant for single chapter generation.
"""
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from storage import StorageManager
from models import StoryBible, ChapterOutline

class ChapterDriver:
    def __init__(self):
        self.storage = Config.get_storage_manager()
        self.bible_path = "story_bible_agent.json"

    def get_prompt_for_chapter(self, chapter_number: int):
        """Generate the comprehensive prompt for a single chapter."""
        bible = self.storage.load_story_bible(self.bible_path)
        if not bible:
            print("Error: Bible not found. Run init first.")
            return

        current_vol = (chapter_number - 1) // 10 + 1
        chapter_in_volume = (chapter_number - 1) % 10 + 1
        
        volume_plan = bible.volume_plans.get(str(current_vol)) or bible.volume_plans.get(current_vol)
        if not volume_plan:
            print(f"Error: Volume Plan for Volume {current_vol} not found. Generate volumes first.")
            return

        print(f"--- ALTIHEIA 5-STEP PROMPT FOR CHAPTER {chapter_number} ---")
        
        # 1. Extraction
        main_plot = bible.main_plot_summary
        vol_title = volume_plan.title if hasattr(volume_plan, 'title') else volume_plan.get('title')
        vol_conflict = volume_plan.main_conflict if hasattr(volume_plan, 'main_conflict') else volume_plan.get('main_conflict')
        
        # Key event for this specific chapter
        key_events = volume_plan.key_events if hasattr(volume_plan, 'key_events') else volume_plan.get('key_events', [])
        key_event = key_events[chapter_in_volume - 1] if chapter_in_volume <= len(key_events) else "自由发挥，衔接上下文"

        # Recent Chapters Context
        recent_chapters = []
        for i in range(max(1, chapter_number - 3), chapter_number):
            outline = bible.chapter_outlines.get(str(i)) or bible.chapter_outlines.get(i)
            if outline:
                recent_chapters.append(f"- 第{i}章: {outline.summary if hasattr(outline, 'summary') else outline.get('summary', '')}")

        # Active Characters in Volume
        vol_chars = volume_plan.key_characters if hasattr(volume_plan, 'key_characters') else volume_plan.get('key_characters', [])
        char_context = []
        for char_name in vol_chars:
            char = bible.characters.get(char_name)
            if char:
                char_context.append(f"- {char.name}: {char.psychological_state} (状态: {char.state.value if hasattr(char.state, 'value') else char.state})")

        # Active Loops
        loops_text = []
        active_loops = bible.get_active_loops() if hasattr(bible, 'get_active_loops') else []
        for loop in active_loops[:3]: # Top 3
            loops_text.append(f"- 伏笔 [{loop.title}]: {loop.description} (第{loop.planted_chapter}章埋下)")

        # 2. Prompt Assembly
        prompt = f"""
**Role**: 你是集【Architect(结构专家)】, 【Simulator(角色模拟器)】, 【Weaver(织网者)】, 【Verifier(逻辑卫士)】于一身的首席小说创作引擎。
**Task**: 为第 {chapter_number} 章生成逻辑严密、充满张力的四幕细纲。

**【宏观背景】**:
- 主线: {main_plot}
- 当前卷: 第 {current_vol} 卷《{vol_title}》
- 本卷核心冲突: {vol_conflict}
- **本章核心事件要求**: {key_event}

**【前文回顾】**:
{chr(10).join(recent_chapters) if recent_chapters else "无前文"}

**【本卷活跃角色状态】** (Deep Think依据):
{chr(10).join(char_context) if char_context else "无活跃角色信息"}

**【当前活跃伏笔】** (可选择触发):
{chr(10).join(loops_text) if loops_text else "无活跃伏笔"}

**【创作指令 (Aletheia 5-Step 融合)】**:
1. **结构(Architect)**: 采用起承转合的四幕结构，节奏必须一波三折。
2. **角色(Simulator)**: 严格遵守上述角色当前心理状态。如果角色在"隐忍"，遭遇挑衅绝对不能无脑打脸爆发，必须用符合人设的智谋化解。
3. **编织(Weaver)**: 将【本章核心事件】自然融入，不要生硬空降。制造一个"钩子(Hook)"作为结尾。
4. **风控(Verifier)**: 绝对禁止：{', '.join(Config.get_forbidden_concepts(bible.background_theme or '架空古代'))}。严禁机械降神，严禁逻辑漏洞。

请以严格的 JSON 格式返回第 {chapter_number} 章内容：
```json
{{
    "chapter_number": {chapter_number},
    "title": "震撼抓人的标题",
    "scene_setting": "主要场景描写(具体到时间、光线、氛围)",
    "characters": ["本章登场角色1", "本章登场角色2"],
    "core_plot": "一句话核心剧情总结",
    "cool_point": "本章提供给读者的核心【爽点/情报揭露/情绪价值】分析",
    "act_one": "第一幕(起): 引入变故",
    "act_two": "第二幕(承): 矛盾激化或调查深入",
    "act_three": "第三幕(转): 智斗高潮或意乱情迷的突破口",
    "act_four": "第四幕(合): 阶段性结果及留给下一章的巨大悬念钩子",
    "detailed_outline": "将核心爽点和四幕内容融合成一段300-500字连贯顺畅的大纲文本，必须包含具体的细节、动作和台词意图暗示。"
}}
```
"""
        print(prompt)
        print("---------------------------------------------------")


    def process_chapter_json(self, input_file: str):
        """Parse AI's JSON output for a chapter and save to Bible & Markdown."""
        bible = self.storage.load_story_bible(self.bible_path)
        if not bible:
            print("Error: Bible not found.")
            return

        print(f"Processing chapter input from {input_file}...")
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                    else:
                        raise ValueError("Could not parse JSON from file.")

            ch_num = data.get("chapter_number")
            if not ch_num:
                raise ValueError("JSON must contain 'chapter_number'")

            # Create ChapterOutline Object
            outline = ChapterOutline(
                chapter_number=ch_num,
                title=data.get("title", f"第{ch_num}章"),
                summary=data.get("core_plot", ""),
                scene_setting=data.get("scene_setting", ""),
                core_plot=data.get("core_plot", ""),
                act_one=data.get("act_one", ""),
                act_two=data.get("act_two", ""),
                act_three=data.get("act_three", ""),
                act_four=data.get("act_four", ""),
                detailed_outline=data.get("detailed_outline", ""),
                characters=data.get("characters", []),
                status="finalized"
            )

            # Optional: Add cool point if exists
            if data.get("cool_point"):
                 outline.detailed_outline = f"【核心看点】: {data.get('cool_point')}\n\n" + outline.detailed_outline

            # Save to Bible
            bible.add_chapter_outline(outline)
            bible.current_chapter = max(bible.current_chapter, ch_num)
            self.storage.save_story_bible(bible, self.bible_path)
            print(f"Processed Chapter {ch_num}: {outline.title}")

            # Append to Markdown Output
            output_file = f"/Users/tang/PycharmProjects/pythonProject/dagang/{bible.story_title}_chapters.md"
            self.append_to_markdown(outline, output_file)

        except Exception as e:
            print(f"Error processing input: {e}")
            import traceback
            traceback.print_exc()

    def append_to_markdown(self, outline: ChapterOutline, output_path: str):
        """Append the chapter outline to the markdown file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = 'a' if path.exists() else 'w'
        with open(path, mode, encoding='utf-8') as f:
            if mode == 'w':
                f.write(f"# 章节细纲内容\n\n---\n\n")
                
            f.write(f"## 第 {outline.chapter_number} 章：{outline.title}\n\n")
            f.write(f"**核心剧情**: {outline.core_plot}\n\n")
            f.write(f"**场景**: {outline.scene_setting}\n")
            f.write(f"**登场角色**: {', '.join(outline.characters)}\n\n")
            f.write(f"### 详细大纲\n{outline.detailed_outline}\n\n")
            
            f.write(f"#### 四幕拆解\n")
            f.write(f"- **起**: {outline.act_one}\n")
            f.write(f"- **承**: {outline.act_two}\n")
            f.write(f"- **转**: {outline.act_three}\n")
            f.write(f"- **合**: {outline.act_four}\n\n")
            f.write("---\n\n")
        
        print(f"Appended Chapter {outline.chapter_number} to {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["prompt", "process"], required=True)
    parser.add_argument("--chapter", type=int, help="Chapter number")
    parser.add_argument("--input", type=str, help="JSON input file for processing")
    
    args = parser.parse_args()
    driver = ChapterDriver()
    
    if args.step == "prompt":
        if not args.chapter:
            print("Error: --chapter required for prompt")
            return
        driver.get_prompt_for_chapter(args.chapter)
    elif args.step == "process":
        if not args.input:
            print("Error: --input required for process")
            return
        driver.process_chapter_json(args.input)

if __name__ == "__main__":
    main()
