"""
Agent Driver for QWen3TTS
Designed for Agent-as-LLM execution.
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from storage import StorageManager
from models import StoryBible, VolumePlan, CharacterCard, CharacterState, OpenLoop, LoopStatus
import re
import hashlib

class AgentDriver:
    def __init__(self, story_name: str = "default_story"):
        self.storage = Config.get_storage_manager(story_name)
        self.bible_path = "story_bible_agent.json" # Use a separate bible for this task
        
    def init_story(self, title: str, protagonist_name: str, protagonist_desc: str):
        """Initialize the story"""
        print("Initializing Story Bible...")
        
        # Initialize World Settings
        world_settings = self._create_world_settings()
        
        bible = StoryBible(
            story_title=title,
            genre="架空古代/群像",
            target_chapters=1000,
            background_theme="架空古代",
            writing_tags=["群像", "剧情向", "神作要求", "伏笔千里"],
            world_settings=world_settings
        )
        
        # Initialize Protagonist
        protagonist = CharacterCard(
            name=protagonist_name,
            identity="主角",
            current_location="未知",
            state=CharacterState.ALIVE,
            power_level=10, 
            special_abilities=[],
            personality_keywords=[],
            biography=protagonist_desc,
            first_appearance_chapter=1
        )
        bible.characters[protagonist.name] = protagonist 
        
        # Main Plot Summary
        bible.main_plot_summary = (
            f"关于 {protagonist_name} 的故事。"
        )
        
        self.storage.save_story_bible(bible, self.bible_path)
        print(f"Story initialized and saved to {self.bible_path}")

    def _create_world_settings(self):
        from models import WorldSettings
        ws = WorldSettings(
            world_name="大宁王朝",
            world_type="架空古代王朝",
            background_theme="架空古代",
            power_system={
                "description": "纯粹的中医医术与传统的古代武功（低武），无玄幻法术。",
                "stages": ["三流", "二流", "一流", "宗师"],
                "rules": ["医武不分家", "内力辅助针灸"]
            }
        )
        return ws

    def get_prompt_for_volumes(self, start_vol, end_vol):
        """Generate the prompt for the Agent to use"""
        bible = self.storage.load_story_bible(self.bible_path)
        if not bible:
            print("Error: Bible not found. Run init first.")
            return

        print(f"--- PROMPT FOR VOLUMES {start_vol} TO {end_vol} ---")
        
        protagonist_name = "陆清源"
        protagonist = bible.characters.get(protagonist_name)
        protagonist_info = protagonist.biography if protagonist else "Unknown"

        print(f"**Story Bible Summary**:")
        print(f"- Title: {bible.story_title}")
        print(f"- Main Plot: {bible.main_plot_summary}")
        print(f"- Protagonist: {protagonist_name} - {protagonist_info}")

        context = f"""
**Role**: You are the "MainAgent" (Showrunner).
**Task**: Generate the detailed outline for Volumes {start_vol}-{end_vol} (Chapters {(start_vol-1)*10+1}-{end_vol*10}).
**Constraints**: 
{Config.STORY_CONSTRAINTS}

**Previous Volumes Context (CRITICAL)**:
"""
        # Add summaries of previous volumes (Logic from MainAgent)
        if start_vol > 1:
            for v in range(1, start_vol):
                vol_plan = bible.volume_plans.get(v) # Note: Keys are ints
                # Handle string keys if JSON loaded
                if not vol_plan and str(v) in bible.volume_plans:
                    vol_plan = bible.volume_plans[str(v)]
                
                if vol_plan:
                    # Logic to handle object or dict (depending on serialization)
                    title = vol_plan.title if hasattr(vol_plan, 'title') else vol_plan.get('title')
                    summary = vol_plan.summary if hasattr(vol_plan, 'summary') else vol_plan.get('summary')
                    context += f"- Volume {v}: {title}\n  Summary: {summary}\n"
        else:
            context += "(First batch, no previous context)\n"

        print(context)
        print("\n**INSTRUCTION**: Generate the content for these volumes in the format specified by `MainAgent.generate_all_volumes_plan`.")
        print("Ensure strict adherence to the 'Ancient/Ensemble' theme. No Sci-Fi terms.")
        print("---------------------------------------------------")

    def _ensure_bible(self):
        """加载或自动创建 Story Bible"""
        bible = self.storage.load_story_bible(self.bible_path)
        if not bible:
            print("Story Bible 不存在，自动创建...")
            self.init_story(
                title="大王饶命_仿写",
                protagonist_name="陆长安",
                protagonist_desc="底层出身的说书人，凭借坚韧在乱世中崛起"
            )
            bible = self.storage.load_story_bible(self.bible_path)
        return bible

    def _parse_name_annotation(self, raw_name: str):
        """解析 '名字（注释）' 格式"""
        raw_name = raw_name.strip()
        for opener, closer in [('（', '）'), ('(', ')')]:
            if opener in raw_name:
                idx = raw_name.index(opener)
                name = raw_name[:idx].strip()
                end_idx = raw_name.index(closer) if closer in raw_name else len(raw_name)
                annotation = raw_name[idx+1:end_idx].strip()
                return name, annotation
        return raw_name, ""

    def _auto_create_characters(self, bible, vol_data, vol_num):
        """Fix #8: 自动从 input JSON 提取并创建 CharacterCard"""
        all_chars = vol_data.get('key_characters', []) + vol_data.get('new_characters', [])
        for raw_name in all_chars:
            name, annotation = self._parse_name_annotation(raw_name)
            if not name:
                continue
            
            if name not in bible.characters:
                card = CharacterCard(
                    name=name,
                    identity=annotation,
                    personality_keywords=[],
                    first_appearance_chapter=(vol_num - 1) * 10 + 1,
                )
                bible.characters[name] = card
            else:
                card = bible.characters[name]
                # 更新身份（取更详细的）
                if annotation and len(annotation) > len(card.identity):
                    card.identity = annotation

    def _register_loops(self, bible, vol_data, vol_num):
        """Fix #3: 将伏笔注册到 bible.open_loops (带唯一ID)"""
        for loop_text in vol_data.get('loops_to_plant', []):
            # 生成稳定的 ID
            loop_id = f"loop_v{vol_num}_{hashlib.md5(loop_text.encode()).hexdigest()[:8]}"
            if loop_id not in bible.open_loops:
                loop = OpenLoop(
                    loop_id=loop_id,
                    title=loop_text[:30],
                    description=loop_text,
                    planted_chapter=(vol_num - 1) * 10 + 1,
                    planted_content=loop_text,
                    status=LoopStatus.OPEN,
                )
                bible.open_loops[loop_id] = loop
        
        for loop_text in vol_data.get('loops_to_resolve', []):
            # 尝试匹配已有伏笔并关闭
            for lid, loop in bible.open_loops.items():
                if loop.description and loop_text[:15] in loop.description:
                    loop.status = LoopStatus.CLOSED
                    loop.resolved_chapter = vol_num * 10
                    break

    def process_input(self, input_file):
        """Process the agent's generated JSON/Text input"""
        bible = self._ensure_bible()
        if not bible:
            print("Error: Bible could not be created.")
            return

        print(f"Processing input from {input_file}...")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                # Attempt to parse json from markdown block if needed
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
            
            # The input should be compliant with VolumePlan structure
            volumes_data = data.get("volumes", [])
            
            for vol_data in volumes_data:
                vol_num = vol_data.get("volume_number")
                
                # Create VolumePlan object
                plan = VolumePlan(
                    volume_number=vol_num,
                    title=vol_data.get("title", f"第{vol_num}卷"),
                    summary=vol_data.get("summary", ""),
                    main_conflict=vol_data.get("main_conflict", ""),
                    protagonist_growth=vol_data.get("protagonist_growth", ""),
                    key_events=vol_data.get("key_events", []),
                    key_characters=vol_data.get("key_characters", []),
                    new_characters=vol_data.get("new_characters", []),
                    loops_to_plant=vol_data.get("loops_to_plant", []),
                    loops_to_resolve=vol_data.get("loops_to_resolve", []),
                    phase=vol_data.get("phase", "")
                )
                
                bible.volume_plans[vol_num] = plan
                
                # Fix #8: Auto-create CharacterCards from input data
                self._auto_create_characters(bible, vol_data, vol_num)
                
                # Fix #3: Register loops with IDs
                self._register_loops(bible, vol_data, vol_num)
                
                print(f"Processed Volume {vol_num}: {plan.title}")

            # Save Bible
            self.storage.save_story_bible(bible, self.bible_path)
            
            # Append to Markdown Output
            output_file = getattr(self, '_output_override', None) or getattr(getattr(self, 'args', None), 'output', None)
            if not output_file:
                output_file = f"/Users/tang/PycharmProjects/pythonProject/dagang/{bible.story_title}.md"
            self.export_to_markdown(bible, output_file)
            
        except Exception as e:
            print(f"Error processing input: {e}")
            import traceback
            traceback.print_exc()

    def export_to_markdown(self, bible, output_path):
        """Append/Overwrite the markdown file"""
        # Ensure directory exists
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# {bible.story_title}\n\n")
            f.write(f"**类型**: {bible.genre}\n")
            f.write(f"**主线**: {bible.main_plot_summary}\n\n")
            f.write("---\n\n")
            
            # Sort volumes
            sorted_vols = sorted(bible.volume_plans.items(), key=lambda x: int(x[0]))
            
            for vol_num, plan in sorted_vols:
                f.write(f"## 第{vol_num}卷：{plan.title}\n\n")
                f.write(f"**阶段**: {plan.phase}\n")
                f.write(f"**核心冲突**: {plan.main_conflict}\n")
                f.write(f"**主角成长**: {plan.protagonist_growth}\n\n")
                f.write(f"### 剧情概要\n{plan.summary}\n\n")
                f.write("### 关键事件 (10章)\n")
                for event in plan.key_events:
                    f.write(f"- {event}\n")
                f.write("\n")
                f.write("### 涉及人物\n")
                f.write(f"- 核心: {', '.join(plan.key_characters)}\n")
                if plan.new_characters:
                    f.write(f"- 新登场: {', '.join(plan.new_characters)}\n")
                f.write("\n---\n\n")
        
        print(f"Exported to {output_path}")

    def process_all_inputs(self, output_file=None):
        """
        依次处理所有 input_v*.json 文件，从卷1到卷100。
        每个文件处理后累积到同一个 Story Bible 中，最终全量导出。
        """
        import glob
        input_dir = Path(__file__).parent
        input_files = sorted(input_dir.glob("input_v*.json"))
        
        if not input_files:
            print("Error: No input_v*.json files found in project directory.")
            return
        
        print(f"\n{'='*60}")
        print(f"📚 找到 {len(input_files)} 个输入文件，开始批量导入...")
        print(f"{'='*60}")
        
        # Set output override if provided
        if output_file:
            self._output_override = output_file
        
        for i, f in enumerate(input_files, 1):
            print(f"\n{'─'*40}")
            print(f"[{i}/{len(input_files)}] 处理: {f.name}")
            print(f"{'─'*40}")
            self.process_input(str(f))
        
        # Clean up override
        if hasattr(self, '_output_override'):
            del self._output_override
        
        # Final verification
        bible = self.storage.load_story_bible(self.bible_path)
        if bible:
            total_vols = len(bible.volume_plans)
            vol_nums = sorted(bible.volume_plans.keys())
            print(f"\n{'='*60}")
            print(f"✅ 全部 {len(input_files)} 个文件处理完毕!")
            print(f"   Story Bible 中共有 {total_vols} 卷规划")
            if vol_nums:
                print(f"   卷号范围: 第{vol_nums[0]}卷 ~ 第{vol_nums[-1]}卷")
            print(f"{'='*60}")
        else:
            print("\n⚠️ 处理完成，但无法加载 Story Bible 进行验证。")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=[
        "init", "prompt", "process", "process-all",
        "generate-profiles", "scan-poison", "check-continuity"
    ], required=True)
    parser.add_argument("--start", type=int, help="Start volume (for prompt)")
    parser.add_argument("--end", type=int, help="End volume (for prompt)")
    parser.add_argument("--input", type=str, help="JSON input file (for process)")
    parser.add_argument("--output", type=str, help="Output markdown file path (for process)")
    parser.add_argument("--title", type=str, help="Story title (for init)", default="未命名神作")
    parser.add_argument("--protagonist", type=str, help="Protagonist name (for init)", default="主角")
    parser.add_argument("--desc", type=str, help="Protagonist description (for init)", default="暂无描述")
    parser.add_argument("--story", type=str, help="Story name for isolation", default="default_story")
    
    args = parser.parse_args()
    
    driver = AgentDriver(story_name=args.story)
    
    # Store args on driver for use in process_input if needed
    driver.args = args

    if args.step == "init":
        driver.init_story(title=args.title, protagonist_name=args.protagonist, protagonist_desc=args.desc)
    elif args.step == "prompt":
        if not args.start or not args.end:
            print("Error: --start and --end required for prompt")
            return
        driver.get_prompt_for_volumes(args.start, args.end)
    elif args.step == "process":
        if not args.input:
            print("Error: --input required for process")
            return
        driver.process_input(args.input)
    elif args.step == "process-all":
        driver.process_all_inputs(output_file=args.output)
    elif args.step == "generate-profiles":
        _run_generate_profiles(driver, args)
    elif args.step == "scan-poison":
        _run_scan_poison(driver, args)
    elif args.step == "check-continuity":
        _run_check_continuity(driver, args)


def _run_generate_profiles(driver, args):
    """生成人物小传"""
    bible = driver._ensure_bible()
    if not bible:
        print("Error: Bible not found.")
        return
    
    from scripts.generate_profiles import ProfileGenerator
    generator = ProfileGenerator()
    
    story_name = args.story
    output_dir = args.output or str(Config.STORAGE_DIR / story_name / f"{story_name}_人物小传")
    
    files = generator.generate_all_profiles(bible, output_dir)
    index = generator.generate_index(bible, output_dir)
    
    print(f"\n{'='*60}")
    print(f"✅ 人物小传生成完毕!")
    print(f"   生成角色数: {len(files)}")
    print(f"   输出目录: {output_dir}")
    print(f"   索引文件: {index}")
    print(f"{'='*60}")


def _run_scan_poison(driver, args):
    """毒点扫描"""
    bible = driver._ensure_bible()
    if not bible:
        print("Error: Bible not found.")
        return
    
    from mechanisms.poison_detector import PoisonDetector
    detector = PoisonDetector()
    report = detector.scan_all_volumes(bible)
    md = detector.generate_report_markdown(report)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"毒点报告已保存到 {args.output}")
    else:
        print(md)


def _run_check_continuity(driver, args):
    """连续性检查"""
    bible = driver._ensure_bible()
    if not bible:
        print("Error: Bible not found.")
        return
    
    from mechanisms.continuity_tracker import ContinuityTracker
    tracker = ContinuityTracker()
    md = tracker.generate_continuity_report(bible)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"连续性报告已保存到 {args.output}")
    else:
        print(md)


if __name__ == "__main__":
    main()
