"""
Generation Loop (增量生成循环) - 核心生成流程
实现 Aletheia 5-Step 循环 + 累计回顾 + 配角 Deep Think + 卷总结
"""

import sys
import os
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StoryBible, ChapterOutline
from agents.main_agent import MainAgent
from agents.the_architect import TheArchitect
from agents.character_simulator import CharacterSimulator
from agents.plot_weaver import PlotWeaver
from agents.logic_verifier import LogicVerifier
from agents.stylist import TheStylist
from agents.character_architect import CharacterArchitect
from agents.world_keeper import WorldKeeper
from agents.continuity_tracker import ContinuityTracker
from mechanisms.shadow_registry import ShadowRegistry
from mechanisms.event_sourcing import EventSourcingEngine
from mechanisms.trajectory_analysis import TrajectoryAnalyzer
from mechanisms.chekhov_gun import ChekhovGunScheduler
from mechanisms.context_manager import ContextManager
from mechanisms.rag_manager import RAGManager
from mechanisms.poison_detector import PoisonDetector  # Fix #2
from storage import StorageManager
from config import Config


class GenerationLoop:
    """增量生成循环 (Aletheia Architecture)"""
    
    def __init__(self, storage_manager: StorageManager):
        """
        初始化生成循环
        
        Args:
            storage_manager: 存储管理器
        """
        self.storage = storage_manager
        
        # Fix #13: Shared LLM client for all agents
        from utils.llm_client import get_default_client
        shared_client = get_default_client()
        
        # Managers
        self.context_manager = ContextManager(storage_manager)
        self.rag_manager = RAGManager(str(storage_manager.storage_dir))
        
        # Agents (Aletheia Architecture) — 共享 LLM 客户端
        self.main_agent = MainAgent(llm_client=shared_client)
        self.architect = TheArchitect(llm_client=shared_client)
        self.character_sim = CharacterSimulator(llm_client=shared_client)
        self.weaver = PlotWeaver(
            llm_client=shared_client,
            context_manager=self.context_manager,
            rag_manager=self.rag_manager
        )
        self.verifier = LogicVerifier(
            llm_client=shared_client,
            rag_manager=self.rag_manager
        )
        self.stylist = TheStylist(llm_client=shared_client)
        self.world_agent = WorldKeeper(llm_client=shared_client)
        self.continuity_agent = ContinuityTracker(llm_client=shared_client)
        self.character_architect = CharacterArchitect(llm_client=shared_client)
        
        # Mechanisms
        self.shadow_registry = ShadowRegistry()
        self.event_sourcing = EventSourcingEngine()
        self.trajectory_analyzer = TrajectoryAnalyzer()
        self.chekhov_scheduler = ChekhovGunScheduler()
        self.poison_detector = PoisonDetector()  # Fix #2: 内联毒点检测

    # =========================================================================
    # Fix #4: 实现 generate_chapters 方法
    # =========================================================================
    def generate_chapters(
        self,
        bible: StoryBible,
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None
    ) -> List[ChapterOutline]:
        """
        批量生成章节大纲
        
        Args:
            bible: 故事圣经
            start_chapter: 起始章节（默认从当前进度的下一章开始）
            end_chapter: 结束章节（默认到目标章节数）
            
        Returns:
            生成的章节大纲列表
        """
        start = start_chapter or (bible.current_chapter + 1)
        end = end_chapter or bible.target_chapters
        
        print(f"\n{'='*60}")
        print(f"📖 开始批量生成: 第 {start} 章 → 第 {end} 章")
        print(f"{'='*60}")
        
        generated_outlines = []
        
        for chapter_num in range(start, end + 1):
            current_volume = (chapter_num - 1) // 10 + 1
            chapter_in_volume = (chapter_num - 1) % 10 + 1
            
            # 每卷开始前执行累计回顾 (Fix #5 + #9)
            if chapter_in_volume == 1:
                self._perform_volume_start_actions(bible, current_volume)
            
            # 动态获取对应卷的原文作为上下文 (Fix for extracting volume content)
            volume_text = self._extract_volume_text_from_markdown(current_volume)
            if volume_text:
                arc_description = f"{arc_description}\n\n==== 原文原著第 {current_volume} 卷内容参考 ====\n{volume_text}"

            try:
                outline = self.generate_single_chapter(
                    bible=bible,
                    chapter_number=chapter_num,
                    arc_description=arc_description
                )
                generated_outlines.append(outline)
                
                # 每卷结束后执行总结 (Fix #9)
                if chapter_in_volume == 10:
                    self._perform_volume_end_actions(bible, current_volume)
                
                # 每章生成后保存
                self.storage.save_story_bible(bible)
                
                # Fix #14: 保存机制状态 (断点恢复)
                try:
                    self.rag_manager._save_corpus()
                    self.rag_manager.save_graph()
                except Exception:
                    pass
                
                print(f"\n✅ 第 {chapter_num} 章生成并保存完毕\n")
                
            except Exception as e:
                print(f"\n❌ 第 {chapter_num} 章生成失败: {e}")
                print(f"   已保存到第 {bible.current_chapter} 章，可从此处恢复")
                self.storage.save_story_bible(bible)
                # Fix #14: 失败时也保存状态
                try:
                    self.rag_manager._save_corpus()
                    self.rag_manager.save_graph()
                except Exception:
                    pass
                break
        
        print(f"\n{'='*60}")
        print(f"📊 本次生成完成: 共 {len(generated_outlines)} 章")
        print(f"{'='*60}")
        
        return generated_outlines

    # =========================================================================
    # Fix #5: 累计回顾机制集成
    # =========================================================================
    def _perform_volume_start_actions(self, bible: StoryBible, volume_number: int):
        """
        每卷开始前的操作：
        1. 累计回顾前文
        2. 检查待铺垫角色
        """
        print(f"\n{'─'*40}")
        print(f"📚 第 {volume_number} 卷开始前置准备...")
        print(f"{'─'*40}")
        
        # 累计回顾 (Fix #5)
        if volume_number > 1:
            print(f"\n[回顾] 正在回顾前 {volume_number - 1} 卷内容...")
            try:
                review = self.main_agent.perform_cumulative_review(
                    bible=bible,
                    current_volume=volume_number
                )
                bible.cumulative_review = review
                print(f"  ✓ 累计回顾完成")
                
                # 打印关键信息
                if isinstance(review, dict):
                    key_points = review.get("key_continuity_points", [])
                    if key_points:
                        print(f"  📌 关键连续性要点:")
                        for point in key_points[:3]:
                            print(f"     - {point}")
            except Exception as e:
                print(f"  ⚠️ 累计回顾出错（继续生成）: {e}")
        
        # 检查待铺垫角色
        start_chapter = (volume_number - 1) * 10 + 1
        pending_chars = self.shadow_registry.get_pending_characters(
            start_chapter, lookahead_chapters=10
        )
        if pending_chars:
            print(f"\n[铺垫] {len(pending_chars)} 个角色需要在本卷铺垫:")
            for char in pending_chars:
                print(f"  - {char['character_name']} "
                      f"(还差 {char['required_mentions'] - char['current_mentions']} 次提及)")

    # =========================================================================
    # Fix #9: 卷总结自动写入
    # =========================================================================
    def _perform_volume_end_actions(self, bible: StoryBible, volume_number: int):
        """
        每卷结束后的操作：
        1. 生成卷总结
        2. 更新RAG知识库
        """
        print(f"\n{'─'*40}")
        print(f"📝 第 {volume_number} 卷结束，执行收尾...")
        print(f"{'─'*40}")
        
        # 生成卷总结 (Fix #9)
        try:
            print(f"\n[总结] 正在生成第 {volume_number} 卷总结...")
            summary = self.main_agent.summarize_volume(
                bible=bible,
                volume_number=volume_number
            )
            bible.volume_summaries[volume_number] = summary
            print(f"  ✓ 卷总结已写入")
            
            # 将关键事实写入RAG知识库
            if isinstance(summary, str) and summary:
                # Fix #10: 细粒度RAG索引 (不止200字)
                self.rag_manager.index_volume_summary(volume_number, summary)
                
                # 索引角色事件
                try:
                    plan = bible.volume_plans.get(volume_number)
                    if plan:
                        for event in (plan.key_events if hasattr(plan, 'key_events') else []):
                            self.rag_manager.add_to_vector_store(
                                event, {"type": "key_event", "volume": volume_number}
                            )
                        for char_name in (plan.key_characters if hasattr(plan, 'key_characters') else []):
                            self.rag_manager.add_to_vector_store(
                                f"第{volume_number}卷关键角色: {char_name}",
                                {"type": "character", "volume": volume_number}
                            )
                except Exception:
                    pass
                print(f"  ✓ 关键事实已写入知识库")
                
        except Exception as e:
            print(f"  ⚠️ 卷总结生成出错: {e}")

    # =========================================================================
    # Aletheia 5-Step 单章生成
    # =========================================================================
    def generate_single_chapter(
        self,
        bible: StoryBible,
        chapter_number: int,
        arc_description: str = "",
        reference_text: str = ""
    ) -> ChapterOutline:
        """
        生成单章大纲 (Aletheia 5-Step 循环)
        
        Step 1 (Architect): 提取参考文本的叙事结构
        Step 2 (Simulator): 所有关键角色深度模拟与决策 (Fix #7)
        Step 3 (Weaver): 编织剧情 (Structure + Decision -> Plot)
        Step 4 (Verifier): 逻辑验证 + 禁词过滤
        Step 5 (Stylist): 风格润色
        """
        print(f"\n⚡️ [Aletheia Engine] 启动第 {chapter_number} 章生成流程...")
        
        # 0. Context Loading
        context = self._load_context(bible, chapter_number)
        
        # Step 1: Architect (结构解析)
        print(f"\n[Step 1/5] Agent A (Architect): 解析叙事结构...")
        if reference_text:
            structure_template = self.architect.analyze_reference(reference_text)
        else:
            structure_template = {
                "structure_name": "Standard Pacing", 
                "pacing_beats": []
            }
        print(f"  ✓ 结构模版已就绪: {structure_template.get('structure_name', 'Generic')}")

        # Step 2: Character Simulator — 所有关键角色 Deep Think (Fix #7)
        print(f"\n[Step 2/5] Agent B (Simulator): 全角色深度思考 (Deep Think)...")
        character_decisions = self._deep_think_all_characters(
            bible, chapter_number, context
        )

        # Step 3: Weaver (剧情编织)
        print(f"\n[Step 3/5] Agent C (Weaver): 编织剧情细纲...")
        
        # 获取应回收和应埋设的伏笔
        loops_to_resolve = self._get_loops_to_resolve(bible, chapter_number, arc_description)
        loops_to_plant = self._get_loops_to_plant(bible, chapter_number, arc_description)
        
        outline = self.weaver.generate_chapter_outline(
            bible=bible,
            chapter_number=chapter_number,
            arc_goal=arc_description,
            character_states={name: char.psychological_state 
                            for name, char in bible.characters.items()},
            structure_template=structure_template,
            character_decisions=character_decisions,
            loops_to_resolve=loops_to_resolve,
            loops_to_plant=loops_to_plant
        )
        print(f"  ✓ 初稿完成: {outline.title}")

        # Step 4: Verifier (逻辑验证 + 禁词硬过滤)
        print(f"\n[Step 4/5] Agent D (Verifier): 逻辑风控审查...")
        verification = self.verifier.verify_outline(bible, outline)
        
        # 硬编码禁词过滤 (Fix #12 bonus)
        forbidden_hits = self._check_forbidden_words(outline, bible)
        if forbidden_hits:
            print(f"  ⛔️ 禁词检测命中: {forbidden_hits}")
            verification["status"] = "REJECT"
            verification["forbidden_words"] = forbidden_hits
        
        if verification.get("status") == "REJECT":
            print(f"  ⛔️ 逻辑审查未通过! 尝试重新生成...")
            # Fix #9: 验证-修改-重试循环 (最多2次)
            for retry in range(2):
                outline = self.weaver.refine_outline(
                    bible=bible,
                    outline=outline,
                    feedback=str(verification.get('review_summary', verification.get('forbidden_words', '')))
                )
                # 重新验证
                re_verify = self.verifier.verify_outline(bible, outline)
                if re_verify.get('status') != 'REJECT':
                    print(f"  ✓ 第{retry+1}次修改后通过")
                    break
            else:
                print(f"  ⚠️ 2次重试后仍未通过，使用最新版本")
            print(f"  ✓ 重新生成完成: {outline.title}")
        else:
            print(f"  ✓ 逻辑审查通过 (Status: {verification.get('status', 'PASS')})")

        # Fix #2: 内联毒点检测
        print(f"\n[Step 4b/5] Poison Detector: 毒点扫描...")
        poison_text = f"{outline.title} {outline.summary} {outline.detailed_outline}"
        poison_hits = self.poison_detector.scan_text(poison_text, f"第{chapter_number}章")
        fatal_poisons = [h for h in poison_hits if h.severity.value == "致命"]
        if fatal_poisons:
            print(f"  ⛔️ 检测到 {len(fatal_poisons)} 个致命毒点!")
            for h in fatal_poisons[:3]:
                print(f"     [{h.poison_type.value}] '{h.keyword}' → {h.suggestion[:50]}")
            # 尝试修复
            poison_feedback = "\n".join([f"致命毒点: '{h.keyword}'→{h.suggestion}" for h in fatal_poisons])
            outline = self.weaver.refine_outline(bible, outline, f"必须修复以下毒点：\n{poison_feedback}")
            print(f"  ✓ 毒点修复尝试完成")
        elif poison_hits:
            print(f"  ⚠️ 检测到 {len(poison_hits)} 个非致命毒点（允许通过）")
        else:
            print(f"  ✓ 无毒点")

        # Step 5: Stylist (风格润色)
        print(f"\n[Step 5/5] Agent E (Stylist): 风格修辞润色...")
        polished_text = self.stylist.polish_outline(outline.detailed_outline, bible)
        outline.detailed_outline = polished_text
        print(f"  ✓ 润色完成")

        # Commit
        self._commit_and_update(bible, outline, chapter_number)
        
        # Fix #17: 轨迹分析 (在提交后, 检查OOC)
        try:
            for char_name in outline.characters:
                char = bible.get_character(char_name) if hasattr(bible, 'get_character') else bible.characters.get(char_name)
                if char:
                    ooc = self.trajectory_analyzer.check_ooc(
                        character=char,
                        current_chapter=chapter_number,
                        action_description=outline.summary
                    )
                    if ooc and ooc.get('is_ooc', False):
                        print(f"  ⚠️ OOC警告: {char_name} - {ooc.get('reason', '未知')}")
        except Exception:
            pass  # 轨迹分析是辅助功能
        
        return outline

    # =========================================================================
    # Fix #7: 配角 Deep Think
    # =========================================================================
    def _deep_think_all_characters(
        self,
        bible: StoryBible,
        chapter_number: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        对所有本章关键角色执行 Deep Think (不仅限于主角)
        
        策略：
        1. 从卷规划中获取本卷关键角色
        2. 如果没有卷规划，从当前活跃角色中选择
        3. 每个角色独立做 Deep Think，得到各自的决策
        """
        character_decisions = {}
        
        # 确定本章关键角色
        key_character_names = self._identify_chapter_characters(bible, chapter_number)
        
        if not key_character_names:
            print(f"  ⚠️ 未找到关键角色，跳过 Deep Think")
            return character_decisions
        
        print(f"  🎭 本章关键角色: {', '.join(key_character_names)}")
        
        # 获取卷规划的context
        volume_plan = context.get("volume_plan")
        situation_desc = ""
        if volume_plan:
            situation_desc = f"本卷核心冲突: {volume_plan.main_conflict}"
            key_event = context.get("key_event_for_chapter", "")
            if key_event:
                situation_desc += f"\n本章关键事件: {key_event}"
        
        for char_name in key_character_names:
            char = bible.get_character(char_name)
            if not char:
                continue
            
            # 获取该角色和其他角色的互动信息
            other_actions = []
            for other_name in key_character_names:
                if other_name != char_name:
                    other_char = bible.get_character(other_name)
                    if other_char:
                        other_actions.append(
                            f"{other_name}: 当前状态 - {other_char.psychological_state}"
                        )
            
            try:
                decision = self.character_sim.deep_think(
                    character=char,
                    current_situation=f"第 {chapter_number} 章\n{situation_desc}",
                    other_characters_actions=other_actions
                )
                character_decisions[char_name] = decision
                print(f"  ✓ [{char_name}] 决策: {decision.get('decision', 'N/A')[:60]}")
            except Exception as e:
                print(f"  ⚠️ [{char_name}] Deep Think 失败: {e}")
        
        return character_decisions
    
    def _identify_chapter_characters(
        self, bible: StoryBible, chapter_number: int
    ) -> List[str]:
        """确定本章需要做 Deep Think 的角色列表"""
        characters = []
        
        # 1. 从卷规划的 key_characters 获取
        current_volume = (chapter_number - 1) // 10 + 1
        volume_plan = bible.volume_plans.get(current_volume)
        if volume_plan and volume_plan.key_characters:
            characters.extend(volume_plan.key_characters)
        
        # 2. 如果没有，取所有活跃角色（最多5个最重要的）
        if not characters:
            active_chars = [
                char for char in bible.characters.values()
                if char.state.value == "alive"
                and char.first_appearance_chapter is not None
                and char.first_appearance_chapter <= chapter_number
            ]
            # 按战力/重要性排序取前5
            active_chars.sort(key=lambda c: c.power_level, reverse=True)
            characters = [c.name for c in active_chars[:5]]
        
        # 去重
        return list(dict.fromkeys(characters))

    # =========================================================================
    # 辅助方法
    # =========================================================================
    def _load_context(self, bible: StoryBible, chapter_number: int) -> Dict[str, Any]:
        """上下文装载"""
        context = {
            "current_chapter": chapter_number,
            "current_progress": bible.current_chapter,
            "target_chapters": bible.target_chapters
        }
        
        # 获取当前卷规划
        current_volume = (chapter_number - 1) // 10 + 1
        volume_plan = bible.volume_plans.get(current_volume)
        if not volume_plan:
            raise ValueError(
                f"❌ 第 {current_volume} 卷规划不存在！\n"
                f"   请先运行 'python main.py init' 或 'python main.py plan-volumes' 生成卷规划。\n"
                f"   在生成章节大纲之前，必须先完成全部 100 卷的宏观规划。"
            )
        context["volume_plan"] = volume_plan
        print(f"  📚 当前卷: 第{current_volume}卷《{volume_plan.title}》")
        print(f"     核心冲突: {volume_plan.main_conflict}")
        
        # 获取当前章在卷内的位置 (1-10)
        chapter_in_volume = (chapter_number - 1) % 10 + 1
        key_event = volume_plan.get_event_for_chapter(chapter_in_volume)
        if key_event:
            context["key_event_for_chapter"] = key_event
            print(f"     本章关键事件: {key_event}")
        
        # 获取活跃伏笔
        active_loops = bible.get_active_loops()
        context["active_loops"] = active_loops
        print(f"  活跃伏笔: {len(active_loops)} 个")
        
        # 获取超期伏笔
        overdue_loops = self.chekhov_scheduler.get_overdue_loops(bible, chapter_number)
        context["overdue_loops"] = overdue_loops
        if overdue_loops:
            print(f"  ⚠️ 超期伏笔: {len(overdue_loops)} 个")
        
        # 获取待铺垫角色
        pending_chars = self.shadow_registry.get_pending_characters(chapter_number)
        context["pending_characters"] = pending_chars
        if pending_chars:
            print(f"  待铺垫角色: {len(pending_chars)} 个")
            
        # 注入累计回顾
        if hasattr(bible, 'cumulative_review') and bible.cumulative_review:
            context["cumulative_review"] = bible.cumulative_review
            print("  ✓ 已注入剧情连贯性审查报告")
        
        return context
    
    def _extract_volume_text_from_markdown(self, volume_number: int) -> str:
        """Fix #11: 从大纲 Markdown 提取卷内容（动态路径）"""
        # 尝试从 bible 的 storage 目录查找
        import glob
        search_dirs = [
            "/Users/tang/PycharmProjects/pythonProject/dagang/",
            str(self.storage.storage_dir) + "/",
        ]
        
        for search_dir in search_dirs:
            md_files = glob.glob(f"{search_dir}*章节细纲*.md") + glob.glob(f"{search_dir}*.md")
            for md_path in md_files:
                try:
                    import re as re_mod
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    parts = re_mod.split(r'(?=\n## 第\d+卷)', content)
                    target_header = f"## 第{volume_number}卷"
                    for part in parts:
                        if target_header in part:
                            # 限制长度 4000 字符
                            return part.strip()[:4000]
                except Exception:
                    continue
        
        return ""
    
    def _get_loops_to_resolve(
        self, bible: StoryBible, chapter_number: int, arc_description: str
    ) -> List[str]:
        """获取应该回收的伏笔"""
        try:
            loops = self.continuity_agent.get_loops_to_resolve(
                bible=bible,
                current_chapter=chapter_number,
                upcoming_arc_description=arc_description
            )
            result = [loop["loop_id"] for loop in loops[:2]]
            if result:
                print(f"  📌 计划回收伏笔: {len(result)} 个")
            return result
        except Exception:
            return []
    
    def _get_loops_to_plant(
        self, bible: StoryBible, chapter_number: int, arc_description: str
    ) -> List[str]:
        """获取建议埋设的新伏笔"""
        try:
            loops = self.continuity_agent.suggest_new_loops(
                bible=bible,
                current_chapter=chapter_number,
                upcoming_chapters_description=arc_description
            )
            result = loops[:1]
            if result:
                print(f"  🌱 计划埋设伏笔: {len(result)} 个")
            return result
        except Exception:
            return []
    
    def _check_forbidden_words(self, outline: ChapterOutline, bible: StoryBible = None) -> List[str]:
        """硬编码禁词过滤 — 不依赖 LLM 自检"""
        text = f"{outline.title} {outline.summary} {outline.detailed_outline}"
        setting = "架空古代"
        if bible and hasattr(bible, 'background_theme') and bible.background_theme:
            setting = bible.background_theme
        hits = []
        for word in Config.get_forbidden_concepts(setting):
            if word in text:
                hits.append(word)
        return hits
    
    def _commit_and_update(
        self, bible: StoryBible, outline: ChapterOutline, chapter_number: int
    ):
        """提交与状态更新"""
        # 更新 Story Bible
        bible.add_chapter_outline(outline)
        
        # 记录事件到 EventSourcing (Fix #10)
        try:
            self.event_sourcing.record_event(
                bible=bible,
                event_id=f"chapter_{chapter_number}_generated",
                chapter=chapter_number,
                event_type="chapter_generated",
                description=f"第{chapter_number}章《{outline.title}》生成完毕",
                facts={"title": outline.title, "summary": outline.summary},
                affected_characters=outline.characters
            )
        except Exception:
            pass  # EventSourcing 是辅助，不阻塞主流程
        
        # 更新版本号
        bible.increment_version()
        
        print(f"  ✓ 状态已更新")
        print(f"    当前进度: 第 {bible.current_chapter} 章")
        print(f"    版本: v{bible.version}")
