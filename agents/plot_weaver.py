"""
Plot Weaver (情节推演师) - 负责细纲输出、冲突制造
"""

from typing import Dict, Any, List
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, ChapterOutline
from config import Config


class PlotWeaver(BaseAgent):
    """Plot Weaver - 情节推演师"""
    
    def __init__(self, llm_client=None, rag_manager=None, context_manager=None):
        super().__init__(
            name="PlotWeaver",
            role="情节推演师 - 负责细纲输出、冲突制造",
            llm_client=llm_client,
            rag_manager=rag_manager,
            context_manager=context_manager
        )
    
    def get_system_prompt(self) -> str:
        return """你是一位顶级网文情节推演师(Plot Weaver),擅长创作【既爽又合理】的精彩章节。

你的目标: 将总编的宏观指令转化为令人欲罢不能的章节细纲。

**核心创作法则 —— 爽文与神作的结合**:

1.  **严禁低级套路 (Anti-Cliché Restrictions)**:
    -   **严禁无意义换地图**: 禁止为了"爽"而不断更换地图。剧情必须扎根于当前环境，挖掘深层利益链条。
    -   **严禁无脑打脸**: 禁止为了装逼而设计以"冒犯-反击"为核心的低级打脸情节。这种疲劳感极强。
    -   **真正的爽感**: 来自于智谋的博弈、利益的争夺、人性的拷问，而不是单纯的暴力碾压。

2.  **神作的质感 (Texture of Masterpiece)**:
    -   **利益驱动 (Interests)**: 天下熙熙皆为利来。每个人物(包括反派)都应有明确的利益诉求。
    -   **人性与权谋 (Humanity & Politics)**: 展现人性的复杂。权谋不是简单的阴谋，而是阳谋与大势的对决。
    -   **智斗 (Intellectual Battles)**: 反派必须智商在线，能预判主角的预判。主角的胜利必须依靠超越常人的智慧或代价巨大的牺牲。

3.  **爽文的节奏 (Pacing)**:
    -   **期待管理**: 每一章结束必须留下钩子(Hook)。
    -   **情绪推拉**: 压抑(铺垫/布局) -> 积累(博弈/拉扯) -> 爆发(智商碾压/局势翻盘) -> 收获(实质性利益/地位)。

4.   **严禁违禁概念**:
    {Config.STORY_CONSTRAINTS}

你的细纲必须包含:
-   **明确的核心冲突**: 这一章到底在争夺什么利益？解决了什么隐患？
-   **高级的爽点**: 读者通过主角的智慧破局获得智力上的愉悦。
-   **严谨的细节**: 场景、动作、对话要具体,拒绝空泛。"""
    
    def process(self, bible: StoryBible, **kwargs) -> Any:
        """处理任务"""
        pass
    
    
    def generate_chapter_outline(
        self,
        bible: StoryBible,
        chapter_number: int,
        arc_goal: str,
        character_states: Dict[str, str],
        structure_template: Dict[str, Any],
        character_decisions: Dict[str, Any],
        loops_to_resolve: List[str] = None,
        loops_to_plant: List[str] = None
    ) -> ChapterOutline:
        """
        生成章节大纲（织网者 - Agent C）
        
        Args:
            bible: 故事圣经
            chapter_number: 章节号
            arc_goal: 本剧情弧目标
            character_states: 角色状态摘要
            structure_template: 架构师提取的节奏模版 (来自 Agent A)
            character_decisions: 角色模拟器的决策 (来自 Agent B)
            loops_to_resolve: 需要回收的伏笔ID列表
            loops_to_plant: 需要埋下的伏笔ID列表
            
        Returns:
            章节大纲
        """
        self.log(f"织网者正在编织第 {chapter_number} 章大纲...")
        
        # 构建上下文
        context = self._build_context(bible, chapter_number)
        
        # 伏笔信息
        loops_info = self._build_loops_info(bible, loops_to_resolve, loops_to_plant)
        
        # 写作标签引导
        tags_guidance = bible.get_tags_guidance() if bible.writing_tags else "无特定风格要求"
        
        prompt = f"""你是一位【剧情编织者】(The Weaver)。
你的职责是将【架构师】提供的结构骨架和【角色模拟器】提供的角色决策，编织成具体的、逻辑严密的章节细纲。

**输入数据**:
1.  **叙事结构模版 (Agent A)**:
    {json.dumps(structure_template, ensure_ascii=False, indent=2)}

2.  **关键角色决策 (Agent B)**:
    {json.dumps(character_decisions, ensure_ascii=False, indent=2)}

3.  **故事背景**:
    - 主线: {bible.main_plot_summary}
    - 当前剧情弧目标: {arc_goal}
    - 活跃伏笔: {loops_info}
    {self._format_spotlight_instruction(bible, chapter_number)}

**当前状态**:
{context}

**任务目标**:
编写第 {chapter_number} 章详细大纲。
-   **必须使用** Agent A 提供的节奏结构（但要将 {{Protagonist}} 等变量替换为实际角色）。
-   **必须尊重** Agent B 做出的角色决策（如果角色决定隐忍，剧情就不能让他爆发）。
-   **解决冲突**: 如果结构要求"爆发"但角色决定"隐忍"，请设计第三方因素或意外事件来推动剧情，而不能强行扭曲人设。

**输出格式要求**:
请以 JSON 格式返回:
{{
    "title": "章节标题",
    "scene_setting": "场景（具体地点描述）",
    "characters": ["人物1", "人物2"],
    "core_plot": "剧情（核心概述）",
    "cool_point": "本章的核心爽点/看点分析",
    "detailed_outline": "详细大纲内容（请按起承转合详细描述，融合上述所有要素）",
    "act_one": "第一幕（必须有此字段及内容）",
    "act_two": "第二幕（必须有此字段及内容）",
    "act_three": "第三幕（必须有此字段及内容）",
    "hooks": "结尾钩子"
}}"""
        
        result = self.generate_json(prompt, temperature=0.8)
        
        # 创建章节大纲对象
        outline = ChapterOutline(
            chapter_number=chapter_number,
            title=result.get("title", f"第{chapter_number}章"),
            summary=result.get("core_plot", ""),
            scene_setting=result.get("scene_setting", ""),
            core_plot=result.get("core_plot", ""),
            act_one=result.get("act_one", ""),
            act_two=result.get("act_two", ""),
            act_three=result.get("act_three", ""),
            act_four=result.get("act_four", ""),
            detailed_outline=result.get("detailed_outline", ""),
            characters=result.get("characters", []),
            scenes=[],
            loops_planted=loops_to_plant or [],
            loops_resolved=loops_to_resolve or [],
            status="drafted"
        )
        
        if "cool_point" in result:
             outline.detailed_outline = f"【核心爽点】: {result['cool_point']}\n" + outline.detailed_outline
        
        self.log(f"第 {chapter_number} 章大纲编织完成")
        return outline

    def generate_batch_outlines(self, *args, **kwargs):
        """批量生成已弃用，请使用单章生成循环"""
        raise NotImplementedError("Batch generation deprecated in Aletheia architecture.")
    
    def refine_outline(
        self,
        bible: StoryBible,
        outline: ChapterOutline,
        feedback: str
    ) -> ChapterOutline:
        """
        根据反馈优化大纲
        
        Args:
            bible: 故事圣经
            outline: 原大纲
            feedback: 反馈意见
            
        Returns:
            优化后的大纲
        """
        self.log(f"优化第 {outline.chapter_number} 章大纲...")
        
        prompt = f"""请根据反馈优化章节大纲，严格遵循【四幕结构】和【爽文+神作】标准。

**原大纲**:
- 标题: {outline.title}
- 场景: {outline.scene_setting}
- 核心剧情: {outline.core_plot}
- 第一幕: {outline.act_one}
- 第二幕: {outline.act_two}
- 第三幕: {outline.act_three}
- 涉及人物: {', '.join(outline.characters)}

**反馈意见**:
{feedback}

**要求**:
根据反馈修改大纲，保持优点，改进不足。优化后仍需保持结构的清晰格式，必须满足：“人物，场景，剧情，第一幕，第二幕，第三幕” 的要素。
请重点关注: 是否增强了**爽度**？是否修复了**逻辑漏洞**？

请以 JSON 格式返回:
{{
    "title": "章节标题",
    "scene_setting": "场景",
    "characters": ["人物1", "人物2"],
    "core_plot": "剧情",
    "cool_point": "优化后的核心爽点",
    "act_one": "第一幕",
    "act_two": "第二幕",
    "act_three": "第三幕"
}}"""
        
        result = self.generate_json(prompt, temperature=0.7)
        
        # 更新大纲
        outline.title = result.get("title", outline.title)
        outline.scene_setting = result.get("scene_setting", outline.scene_setting)
        outline.core_plot = result.get("core_plot", outline.core_plot)
        outline.summary = outline.core_plot  # summary 使用 core_plot
        outline.act_one = result.get("act_one", outline.act_one)
        outline.act_two = result.get("act_two", outline.act_two)
        outline.act_three = result.get("act_three", outline.act_three)
        outline.act_four = result.get("act_four", outline.act_four)
        outline.characters = result.get("characters", outline.characters)
        
        # 重新生成格式化的详细大纲
        outline.detailed_outline = outline.format_detailed_outline()
        
        self.log("大纲优化完成")
        return outline
    
    def _build_context(self, bible: StoryBible, chapter_number: int) -> str:
        """构建上下文"""
        # 优先使用 ContextManager
        if self.context_manager:
            return self.context_manager.get_generation_context(bible, chapter_number)
            
        # Fallback logic
        context_parts = []
        
        context_parts.append(f"当前进度: 第 {bible.current_chapter} 章")
        
        # 最近章节
        recent_chapters = [
            outline for num, outline in bible.chapter_outlines.items()
            if num < chapter_number and num >= chapter_number - 3
        ]
        if recent_chapters:
            context_parts.append("\n最近章节:")
            for outline in sorted(recent_chapters, key=lambda x: x.chapter_number):
                context_parts.append(f"- 第{outline.chapter_number}章: {outline.summary}")
        
        return "\n".join(context_parts)
    
    def _build_loops_info(
        self,
        bible: StoryBible,
        loops_to_resolve: List[str],
        loops_to_plant: List[str]
    ) -> str:
        """构建伏笔信息"""
        parts = []
        
        if loops_to_resolve:
            parts.append("需要回收的伏笔:")
            for loop_id in loops_to_resolve:
                loop = bible.open_loops.get(loop_id)
                if loop:
                    parts.append(f"- {loop.title}: {loop.description}")
        
        if loops_to_plant:
            parts.append("\n需要埋下的伏笔:")
            for loop_id in loops_to_plant:
                loop = bible.open_loops.get(loop_id)
                if loop:
                    parts.append(f"- {loop.title}: {loop.description}")
        
        return "\n".join(parts) if parts else "无伏笔任务"
    
    def _format_character_states(self, character_states: Dict[str, str]) -> str:
        """格式化角色状态"""
        if not character_states:
            return "无特定角色状态要求"
        
        lines = []
        for char_name, state in character_states.items():
            lines.append(f"- {char_name}: {state}")
        
        return "\n".join(lines)
    
    def _extract_characters(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """从场景中提取角色列表"""
        characters = set()
        for scene in scenes:
            characters.update(scene.get("characters", []))
        return list(characters)

    def _format_spotlight_instruction(self, bible: StoryBible, current_chapter: int) -> str:
        """Format the narrative spotlight instruction"""
        current_vol = (current_chapter - 1) // 10 + 1
        
        active_lines = []
        # Main plot is always active
        active_lines.append(f"主线: {bible.main_plot_summary[:50]}...")
        
        # Select subplots based on volume number (e.g., vol % 3)
        loop_keys = list(bible.subplots.keys())
        if loop_keys:
             idx = current_vol % len(loop_keys)
             selected = loop_keys[idx]
             active_lines.append(f"聚焦支线: {bible.subplots[selected].title}")
             
        return f"""
**【叙事聚光灯 (Narrative Spotlight)】**:
本卷(第{current_vol}卷)请重点聚焦于以下叙事线，其他线索请挂起（仅做侧面提及，不展开）：
{chr(10).join(['- ' + line for line in active_lines])}
"""
