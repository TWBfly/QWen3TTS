"""
Continuity Tracker (伏笔稽查员) - 负责伏笔管理、回收提醒、一致性检索
"""

from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, OpenLoop, LoopStatus


class ContinuityTracker(BaseAgent):
    """Continuity Tracker - 伏笔稽查员"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="ContinuityTracker",
            role="伏笔稽查员 - 负责伏笔管理、回收提醒、一致性检索",
            llm_client=llm_client
        )
    
    def get_system_prompt(self) -> str:
        return """你是一位细致的伏笔稽查员(Continuity Tracker),负责管理故事中的所有伏笔和线索。

你的职责:
1. **伏笔账本**: 维护所有伏笔的详细记录(埋下章节、内容、状态、TTL)
2. **回收提醒**: 主动提示哪些伏笔该回收了
3. **全文检索**: 确保新设定不与之前的内容冲突

你的工作原则:
- 记忆力超群,不遗漏任何伏笔
- 主动提醒,避免伏笔被遗忘
- 严格追踪,确保伏笔有始有终
- 如果伏笔确实无法回收,建议标记为"红鲱鱼"

在管理伏笔时,请特别关注:
1. 重要伏笔(权重高)优先回收
2. 超期伏笔发出警告
3. 伏笔回收要自然,不能生硬
4. 新埋下的伏笔要有明确的回收计划"""
    
    def process(self, bible: StoryBible, **kwargs) -> Any:
        """处理任务"""
        pass
    
    def create_loop(
        self,
        bible: StoryBible,
        title: str,
        description: str,
        planted_chapter: int,
        planted_content: str,
        category: str,
        weight: int = 5,
        ttl: int = 50,
        related_entities: List[str] = None
    ) -> OpenLoop:
        """
        创建新伏笔
        
        Args:
            bible: 故事圣经
            title: 伏笔标题
            description: 详细描述
            planted_chapter: 埋下章节
            planted_content: 埋下时的具体内容
            category: 类别
            weight: 权重 (1-10)
            ttl: 生存周期
            related_entities: 相关实体
            
        Returns:
            伏笔对象
        """
        loop_id = f"loop_{planted_chapter}_{len(bible.open_loops) + 1}"
        
        loop = OpenLoop(
            loop_id=loop_id,
            title=title,
            description=description,
            planted_chapter=planted_chapter,
            planted_content=planted_content,
            category=category,
            weight=weight,
            ttl=ttl,
            related_entities=related_entities or []
        )
        
        self.log(f"创建伏笔: {title} (权重: {weight}, TTL: {ttl})")
        return loop
    
    def get_loops_to_resolve(
        self,
        bible: StoryBible,
        current_chapter: int,
        upcoming_arc_description: str
    ) -> List[Dict[str, Any]]:
        """
        获取应该回收的伏笔
        
        Args:
            bible: 故事圣经
            current_chapter: 当前章节
            upcoming_arc_description: 即将到来的剧情弧描述
            
        Returns:
            应该回收的伏笔列表
        """
        self.log(f"分析第 {current_chapter} 章应该回收的伏笔...")
        
        active_loops = bible.get_active_loops()
        overdue_loops = bible.get_overdue_loops()
        
        if not active_loops:
            self.log("没有未回收的伏笔")
            return []
        
        # 构建伏笔信息
        loops_info = self._format_loops_for_analysis(active_loops, current_chapter)
        
        prompt = f"""请分析哪些伏笔应该在接下来的剧情中回收。

**当前章节**: {current_chapter}

**即将到来的剧情**:
{upcoming_arc_description}

**未回收伏笔**:
{loops_info}

**超期伏笔** (需要优先考虑):
{self._format_overdue_loops(overdue_loops, current_chapter)}

**要求**:
1. 选择适合在接下来剧情中回收的伏笔
2. 优先考虑超期伏笔和高权重伏笔
3. 建议回收方式

请以 JSON 格式返回:
{{
    "loops_to_resolve": [
        {{
            "loop_id": "伏笔ID",
            "loop_title": "伏笔标题",
            "suggested_chapter": 建议回收章节,
            "resolution_method": "建议回收方式",
            "priority": "优先级(high/medium/low)",
            "reasoning": "选择理由"
        }},
        ...
    ]
}}"""
        
        result = self.generate_json(prompt, temperature=0.6)
        
        loops_to_resolve = result.get("loops_to_resolve", [])
        self.log(f"建议回收 {len(loops_to_resolve)} 个伏笔")
        
        return loops_to_resolve
    
    def suggest_new_loops(
        self,
        bible: StoryBible,
        current_chapter: int,
        upcoming_chapters_description: str
    ) -> List[Dict[str, Any]]:
        """
        建议新的伏笔
        
        Args:
            bible: 故事圣经
            current_chapter: 当前章节
            upcoming_chapters_description: 接下来几章的描述
            
        Returns:
            建议的新伏笔列表
        """
        self.log(f"为第 {current_chapter} 章建议新伏笔...")
        
        prompt = f"""请为接下来的剧情建议新的伏笔。

**当前章节**: {current_chapter}
**目标章节数**: {bible.target_chapters}
**主线**: {bible.main_plot_summary}

**接下来的剧情**:
{upcoming_chapters_description}

**已有伏笔**:
{self._format_existing_loops(bible)}

**要求**:
1. 建议 2-3 个新伏笔
2. 伏笔要与主线相关
3. 设定合理的 TTL 和权重
4. 避免与已有伏笔重复

请以 JSON 格式返回:
{{
    "new_loops": [
        {{
            "title": "伏笔标题",
            "description": "详细描述",
            "category": "类别(物品/人物/秘密/事件)",
            "weight": 1-10,
            "ttl": 建议生存周期,
            "planted_content": "建议在章节中如何埋下(50字)",
            "resolution_hint": "建议如何回收(50字)",
            "reasoning": "为什么需要这个伏笔"
        }},
        ...
    ]
}}"""
        
        result = self.generate_json(prompt, temperature=0.7)
        
        new_loops = result.get("new_loops", [])
        self.log(f"建议 {len(new_loops)} 个新伏笔")
        
        return new_loops
    
    def check_consistency(
        self,
        bible: StoryBible,
        new_content: str,
        chapter_number: int
    ) -> Dict[str, Any]:
        """
        检查新内容与已有内容的一致性
        
        Args:
            bible: 故事圣经
            new_content: 新内容
            chapter_number: 章节号
            
        Returns:
            一致性检查结果
        """
        self.log(f"检查第 {chapter_number} 章内容的一致性...")
        
        # 构建历史上下文
        context = self._build_history_context(bible, chapter_number)
        
        prompt = f"""请检查新内容是否与之前的设定一致。

**历史内容**:
{context}

**新内容** (第 {chapter_number} 章):
{new_content}

**检查项**:
1. 人物设定是否一致
2. 世界观设定是否一致
3. 已埋伏笔是否被意外提前揭露
4. 是否有矛盾的描述

请以 JSON 格式返回:
{{
    "consistent": true/false,
    "issues": [
        {{
            "type": "问题类型",
            "description": "问题描述",
            "suggestion": "修改建议"
        }},
        ...
    ],
    "overall_assessment": "总体评估"
}}"""
        
        result = self.generate_json(prompt, temperature=0.3)
        
        if result.get("consistent"):
            self.log("一致性检查通过")
        else:
            self.log(f"发现 {len(result.get('issues', []))} 个一致性问题")
        
        return result
    
    def mark_loop_resolved(
        self,
        bible: StoryBible,
        loop_id: str,
        resolved_chapter: int,
        resolution: str
    ):
        """
        标记伏笔已回收
        
        Args:
            bible: 故事圣经
            loop_id: 伏笔ID
            resolved_chapter: 回收章节
            resolution: 回收方式
        """
        loop = bible.open_loops.get(loop_id)
        if not loop:
            self.log(f"警告: 伏笔 {loop_id} 不存在")
            return
        
        loop.close(resolved_chapter, resolution)
        self.log(f"伏笔 '{loop.title}' 已在第 {resolved_chapter} 章回收")
    
    def mark_loop_abandoned(
        self,
        bible: StoryBible,
        loop_id: str,
        reason: str
    ):
        """
        标记伏笔为红鲱鱼/死线
        
        Args:
            bible: 故事圣经
            loop_id: 伏笔ID
            reason: 原因
        """
        loop = bible.open_loops.get(loop_id)
        if not loop:
            self.log(f"警告: 伏笔 {loop_id} 不存在")
            return
        
        loop.status = LoopStatus.ABANDONED
        loop.resolution = f"标记为红鲱鱼: {reason}"
        self.log(f"伏笔 '{loop.title}' 已标记为红鲱鱼")
    
    def _format_loops_for_analysis(
        self,
        loops: List[OpenLoop],
        current_chapter: int
    ) -> str:
        """格式化伏笔用于分析"""
        lines = []
        for loop in loops:
            age = current_chapter - loop.planted_chapter
            progress = age / loop.ttl if loop.ttl > 0 else 0
            status = "⚠️ 超期" if progress > 1.0 else f"{int(progress * 100)}%"
            
            lines.append(
                f"- [{loop.loop_id}] {loop.title}\n"
                f"  类别: {loop.category}, 权重: {loop.weight}, "
                f"埋下: 第{loop.planted_chapter}章, 进度: {status}\n"
                f"  描述: {loop.description}"
            )
        
        return "\n".join(lines)
    
    def _format_overdue_loops(
        self,
        overdue_loops: List[OpenLoop],
        current_chapter: int
    ) -> str:
        """格式化超期伏笔"""
        if not overdue_loops:
            return "无超期伏笔"
        
        lines = []
        for loop in overdue_loops:
            age = current_chapter - loop.planted_chapter
            lines.append(
                f"- {loop.title} (已过 {age} 章, TTL: {loop.ttl}, 权重: {loop.weight})"
            )
        
        return "\n".join(lines)
    
    def _format_existing_loops(self, bible: StoryBible) -> str:
        """格式化已有伏笔"""
        active_loops = bible.get_active_loops()
        if not active_loops:
            return "无已有伏笔"
        
        lines = []
        for loop in active_loops[:10]:
            lines.append(f"- {loop.title} ({loop.category}, 权重: {loop.weight})")
        
        return "\n".join(lines)
    
    def _build_history_context(self, bible: StoryBible, current_chapter: int) -> str:
        """构建历史上下文"""
        context_parts = []
        
        # 世界观设定
        context_parts.append("**世界观设定**:")
        context_parts.append(f"- 世界: {bible.world_settings.world_name}")
        context_parts.append(f"- 类型: {bible.world_settings.world_type}")
        
        # 主要角色
        context_parts.append("\n**主要角色**:")
        for char in list(bible.characters.values())[:10]:
            context_parts.append(f"- {char.name}: {char.identity}")
        
        # 已回收伏笔
        closed_loops = [loop for loop in bible.open_loops.values() 
                       if loop.status == LoopStatus.CLOSED]
        if closed_loops:
            context_parts.append("\n**已回收伏笔**:")
            for loop in closed_loops[-5:]:
                context_parts.append(
                    f"- {loop.title}: 第{loop.planted_chapter}章埋下, "
                    f"第{loop.resolved_chapter}章回收"
                )
        
        return "\n".join(context_parts)
