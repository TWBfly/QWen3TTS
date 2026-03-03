"""
Main Agent (总编/Showrunner) - 负责宏观控盘、任务分发、决策仲裁
"""

from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, PlotArc, VolumePlan
from config import Config


class MainAgent(BaseAgent):
    """Main Agent - 总编"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="MainAgent",
            role="总编/Showrunner - 负责宏观控盘、任务分发、决策仲裁",
            llm_client=llm_client
        )
    
    def get_system_prompt(self) -> str:
        return """你是一位兼具顶级商业畅销书作家与文学大师水准的网文总编(Showrunner)。
你的目标是打造一部【爽文与神作完美结合】的巅峰之作。

你的职责:
1. **宏观控盘**: 维护 1000 章（100卷）的总体大纲,将故事拆分为卷(Volume) -> 剧情弧(Arc) -> 章节(Chapter)
2. **任务分发**: 向各个专业 Agent 发布明确的指令
3. **决策仲裁**: 在"逻辑严谨性"与"极致爽感"之间寻找完美的平衡点
4. **状态管理**: 决定何时更新 Story Bible

你的核心创作理念:
- **爽文的皮**: 节奏明快、期待感拉满、装逼打脸、极致的压抑与爆发、直观的利益反馈。
- **神作的骨**: 
    - 逻辑严谨: 世界观自洽,战力不崩,智商在线。
    - 人物深度: 拒绝脸谱化,配角也有血有肉,主角有深刻的成长弧光。
    - 沉浸感: 细节丰富,草蛇灰线,伏笔千里。

在做决策时,请务必确保:
1. 每一个剧情单元都有明确的"爽点"或"期待值"。
2. 所有的"爽"都必须建立在合乎逻辑的铺垫之上,拒绝无脑爽。"""
    
    def process(self, bible: StoryBible, **kwargs) -> Any:
        """处理任务 - 由具体方法调用"""
        pass
    
    def create_main_plot_skeleton(
        self,
        genre: str,
        target_chapters: int,
        protagonist_info: str,
        world_type: str,
        ending_type: str = "开放式"
    ) -> Dict[str, Any]:
        """
        创建主线骨架
        
        Args:
            genre: 类型 (修仙、玄幻、都市等)
            target_chapters: 目标章节数
            protagonist_info: 主角信息
            world_type: 世界观类型
            ending_type: 结局类型
            
        Returns:
            包含主线概要、结局、转折点的字典
        """
        self.log(f"创建 {target_chapters} 章的主线骨架 (要求: 爽文+神作)...")
        
        prompt = f"""请为一部 {genre} 类型的网文创建主线骨架。
这是一部追求【极致爽感】与【神作逻辑】完美结合的小说。

**基本信息**:
- 目标章节数: {target_chapters} 章
- 主角信息: {protagonist_info}
- 世界观: {world_type}
- 结局类型: {ending_type}

**核心要求**:
1. **主线故事**: 必须具备极强的目标感和期待感,主角的上升通道要清晰。
2. **爽点设计**: 规划宏大的"压抑-爆发"循环,确保故事高潮迭起。
3. **逻辑与深度**: 在追求爽快的同时,确保世界观严谨,伏笔深远,避免后期战力崩坏。
4. **结局**: 意料之外,情理之中,升华主题。
5. **节奏控制**: 必须在最后一卷(Volume)才进入大结局,绝对禁止提前进入结局篇章。
6. {Config.STORY_CONSTRAINTS}

请以 JSON 格式返回:
{{
    "story_title": "故事标题 (要有爆款潜质,同时不失格调)",
    "main_plot_summary": "主线概要(300-500字, 强调主角的成长与征服之路)",
    "ending": "结局描述(100字)",
    "major_turning_points": [
        {{"chapter": 章节号, "description": "转折点描述 (必须是重大冲突或命运转折)"}},
        ...
    ],
    "volumes": [
        {{"volume_id": "vol_1", "title": "卷标题", "start_chapter": 1, "end_chapter": 10, "summary": "卷概要 (本卷的核心爽点与冲突)"}},
        ...
    ]
}}"""
        
        result = self.generate_json(prompt, temperature=0.8)
        self.log("主线骨架创建完成")
        return result
    
    def generate_ten_narrative_lines(self, bible: StoryBible) -> str:
        """强制生成1条主线+9条支线/暗线的全景规划"""
        self.log("正在生成全书【三幕九线】顶层总约束框架...")
        
        prompt = f"""小说已经立项，为了彻底杜绝后续生成中出现跑偏、乱加设定、降维打击等崩盘现象，
你必须在这里提前规划好贯穿全书 {bible.target_chapters//10} 卷的【核心10条叙事线】（1条主线+9条支线/暗线群体线）。

**基本信息**:
- 标题: {bible.story_title}
- 核心设定: {bible.main_plot_summary}
- 世界观背景: {bible.world_settings.background_theme}
- 强约束: {Config.STORY_CONSTRAINTS}

**任务要求**:
必须要列出明确的 10 条线，每一条线必须包含：
1. **线索名称**与**类型**（主线/支线/暗线）
2. **核心绑定人物**（包括主角或多面反派、立体配角）
3. **三幕分布**（第一幕起：1-30卷，第二幕承转：31-70卷，第三幕合：71-100卷。说明各幕的剧情使命）

请直接以一段结构清晰、信息量极大的 Markdown 纯文本（非 json）返回这10条线的详细梳理。
此梳理将被作为“至高宪法”透传给所有后续大纲生成环节，任何偏离这10条线的新增发散都将被审查官击毙。"""
        
        result = self.generate(prompt, temperature=0.7)
        self.log("【三幕九线】总约束框架生成完成！")
        return result

    def generate_all_volumes_plan(
        self,
        bible: StoryBible,
        total_volumes: int = 100,
        start_volume: int = 1,
        end_volume: int = 100,
        verifier = None
    ) -> List[VolumePlan]:
        """
        一次性生成全部卷的宏观规划。
        这是整本书的顶层设计，必须在生成任何章节大纲前完成。
        
        Args:
            bible: 故事圣经
            total_volumes: 总卷数 (默认100卷)
            start_volume: 起始卷
            end_volume: 结束卷
            verifier: LogicVerifier 实例
            
        Returns:
            VolumePlan 列表
        """
        self.log(f"开始生成第 {start_volume} 到 {end_volume} 卷的宏观规划...")
        
        if not bible.ten_narrative_lines_summary:
            bible.ten_narrative_lines_summary = self.generate_ten_narrative_lines(bible)
            
        all_volume_plans = []
        
        # 分批次生成 (每次1卷，避免模型上下文过长导致JSON截断)
        batch_size = 1
        for batch_start in range(start_volume, end_volume + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_volume)
            self.log(f"  生成第 {batch_start}-{batch_end} 卷规划...")
            
            # 获取已生成的卷规划作为上下文
            previous_volumes_summary = self._summarize_previous_volumes(all_volume_plans)
            
            max_retries = 3
            current_try = 0
            feedback_history = ""
            
            while current_try < max_retries:
                current_try += 1
                prompt = f"""请为小说生成第 {batch_start}-{batch_end} 卷的详细规划（每卷10章）。

**故事基本信息**:
- 标题: {bible.story_title}
- 类型: {bible.genre}
- 主线概要: {bible.main_plot_summary}
- 结局: {bible.ending}
- 总卷数: {total_volumes} 卷
- 总章节数: {total_volumes * 10} 章

**重大转折点**:
{self._format_turning_points(bible.major_turning_points)}

**已规划的前序卷概要**:
{previous_volumes_summary}

**【至高宪法：本卷只允许推进下列三幕九线框架内的剧情，严禁脱离该框架引入新地图、新物种设定！】**
{bible.ten_narrative_lines_summary}

**全书节奏分布** (必须严格遵守“龙头、猪肚、豹尾”的极高张力要求，拒绝平淡):
- 第1-30卷: 【破局求生期】- 面临生存危机与局部势力压迫，重点在于悬念铺设与主角从无到有的爽感。
- 第31-80卷: 【体系颠覆期】- 危机必须从个人恩怨跃迁为恐怖的阵营对抗或世界法则解密。多线交汇，群像高潮爆发，SS级伏笔开始连环引爆。反派是庞大旧体系的代言人。
- 第81-100卷: 【信仰坍塌与重构决战期】- 绝对禁止大圆满后的游历养老。外部明面强敌崩溃后，必须立刻转入内部分崩离析（路线之争、新旧势力利益反扑、甚至是深渊拷问）。这20卷必须是不见硝烟的思想绞肉机与最惨烈的终极清算，配角在此阶段必须有壮烈的牺牲闭环！

**核心要求**:
1. 每卷必须有**明确的核心冲突**和**主角成长目标**
2. 每卷必须设计**10个关键事件**（对应10章的主要剧情）
3. 必须标注本卷**新登场的重要角色**(必须是从【三幕九线框架】中衍生出来的，不能凭空机械降神)
4. 必须规划本卷需要**埋下或回收的伏笔**
5. **严禁在第100卷之前进入最终结局**
6. **必须包含第一幕、第二幕、第三幕的三幕结构叙述，以及核心人物细节刻画和逻辑闭环分析，严禁概括式流水账**
7. 绝对禁止违禁元素（科幻、星际、物理宇宙、工业革命、甚至现代概念）。
8. {Config.STORY_CONSTRAINTS}
{feedback_history}
请以 JSON 格式返回:
{{
    "volumes": [
        {{
            "volume_number": 卷号,
            "title": "卷标题（要有冲击力）",
            "phase": "铺垫期/发展期/高潮期/收尾期",
            "summary": "本卷内容概要（300-500字，必须详细到能支撑10章创作）",
            "main_conflict": "本卷核心冲突",
            "protagonist_growth": "主角在本卷的成长目标/收获",
            "act_one": "第一幕(起): 开场与危机引入（必须详尽）",
            "act_two": "第二幕(承/转): 调查/发展/冲突升级（必须详尽）",
            "act_three": "第三幕(合): 高潮爆发与结果（必须详尽）",
            "character_details": "核心人物刻画与逻辑闭环说明（解释人物动机与草蛇灰线）",
            "key_events": [
                "第1章: 事件描述",
                "第2章: 事件描述",
                ... (共10项，对应10章)
            ],
            "key_characters": ["主要角色1", "主要角色2"],
            "new_characters": ["本卷新登场角色"],
            "loops_to_plant": ["本卷埋下的伏笔"],
            "loops_to_resolve": ["本卷回收的伏笔"]
        }},
        ...
    ]
}}"""
                result = self.generate_json(prompt, temperature=0.7)
                
                # 开始交由 verifier 审核
                if verifier is not None:
                    print(f"\n[Agent 协作] LogicVerifier 正在审查第 {batch_start}-{batch_end} 卷的大纲草案...")
                    verifier_prompt = f"""请审查以下由 MainAgent 生成的卷大纲草案：
{result}

**十条核心叙事线限制（必须只在此范围内发展，严禁偏离）**：
{bible.ten_narrative_lines_summary}

**世界观规则**:
{bible.world_settings.physics_rules}
{Config.STORY_CONSTRAINTS}

**违禁词检测**: 检查是否有科幻、星际、降维打击、外星人、物理宇宙、维度等违禁词和违禁设定！

请严格按照以上宪法进行评判，如果出现违禁设定、违背10条核心线，直接 REJECT。
请以 JSON 格式返回审查结果：
{{
    "status": "PASS" | "REJECT",
    "issues": ["问题1", "问题2"],
    "review_summary": "总体评价与重写建议"
}}
"""
                    verify_res = verifier.generate_json(verifier_prompt, temperature=0.1)
                    if verify_res.get("status") == "REJECT":
                        print(f"❌ LogicVerifier 驳回大纲草案！原因：{verify_res.get('review_summary')}")
                        for issue in verify_res.get("issues", []):
                            print(f"  - 漏洞：{issue}")
                        if current_try < max_retries:
                            print(f"🔄 MainAgent 将根据审查意见进行第 {current_try+1} 次重写...")
                            feedback_history = f"\n\n**LogicVerifier的驳回意见(请必须修正)**:\n{verify_res.get('review_summary')}\n问题细节:\n" + "\n".join(verify_res.get("issues", []))
                            continue
                        else:
                            print("⚠️ 达到最大重试次数，强行通过草案。")
                            break
                    else:
                        print("✅ LogicVerifier 审查通过：逻辑自洽且未触发违禁设定。")
                        break
                else:
                    break
            
            # 解析结果并创建 VolumePlan 对象
            for vol_data in result.get("volumes", []):
                volume_plan = VolumePlan(
                    volume_number=vol_data.get("volume_number", batch_start),
                    title=vol_data.get("title", f"第{vol_data.get('volume_number', batch_start)}卷"),
                    summary=vol_data.get("summary", ""),
                    main_conflict=vol_data.get("main_conflict", ""),
                    protagonist_growth=vol_data.get("protagonist_growth", ""),
                    act_one=vol_data.get("act_one", ""),
                    act_two=vol_data.get("act_two", ""),
                    act_three=vol_data.get("act_three", ""),
                    character_details=vol_data.get("character_details", ""),
                    key_events=vol_data.get("key_events", []),
                    key_characters=vol_data.get("key_characters", []),
                    new_characters=vol_data.get("new_characters", []),
                    loops_to_plant=vol_data.get("loops_to_plant", []),
                    loops_to_resolve=vol_data.get("loops_to_resolve", []),
                    phase=vol_data.get("phase", "")
                )
                all_volume_plans.append(volume_plan)
                bible.volume_plans[volume_plan.volume_number] = volume_plan
            
            self.log(f"  ✓ 第 {batch_start}-{batch_end} 卷规划完成")
        
        self.log(f"全部 {len(all_volume_plans)} 卷规划生成完成")
        return all_volume_plans
    
    def _summarize_previous_volumes(self, volume_plans: List[VolumePlan]) -> str:
        """总结已生成的卷规划"""
        if not volume_plans:
            return "（首批规划，无前序内容）"
        
        # 为了防止上下文爆炸，对前序卷的总结进行压缩与提取
        lines = []
        # 1. 最近的3卷提供详细冲突
        recent_plans = volume_plans[-3:]
        lines.append("【最近三卷详细核心冲突】:")
        for plan in recent_plans:
            lines.append(f"- 第{plan.volume_number}卷《{plan.title}》: {plan.main_conflict}")
            
        # 2. 从更早的卷中提取未闭合的重大伏笔和人物状态 (简化版)
        older_plans = volume_plans[:-3]
        if older_plans:
            lines.append("\n【前序宏观脉络概述】:")
            older_summary = [f"第{p.volume_number}卷({p.title})" for p in older_plans[::5]] # 每5卷抽样一个进度
            lines.append(f"剧情已推进过: {', '.join(older_summary)} 等阶段。")
            
        return "\n".join(lines)
    
    def _format_turning_points(self, turning_points: List[Dict[str, Any]]) -> str:
        """格式化转折点"""
        if not turning_points:
            return "（无预设转折点）"
        lines = []
        for tp in turning_points:
            lines.append(f"- 第{tp.get('chapter', '?')}章: {tp.get('description', '')}")
        return "\n".join(lines)
    
    def plan_next_arc(
        self,
        bible: StoryBible,
        start_chapter: int,
        end_chapter: int
    ) -> Dict[str, Any]:
        """
        规划下一个剧情弧
        
        Args:
            bible: 故事圣经
            start_chapter: 起始章节
            end_chapter: 结束章节
            
        Returns:
            剧情弧规划
        """
        self.log(f"规划第 {start_chapter}-{end_chapter} 章的剧情弧...")
        
        # 获取上下文
        context = self._build_context(bible, start_chapter)
        
        prompt = f"""基于当前故事进度,规划第 {start_chapter}-{end_chapter} 章的剧情弧。

**当前进度**:
- 已完成章节: {bible.current_chapter}
- 主线概要: {bible.main_plot_summary}

**当前状态**:
{context}

**未回收伏笔**:
{self._format_open_loops(bible)}

**要求**:
1. 设计本剧情弧的主要冲突
2. 确定高潮章节
3. 涉及的主要角色
4. 主角的目标和预期结果
5. 考虑回收哪些伏笔,埋下哪些新伏笔
6. {Config.STORY_CONSTRAINTS}

**节奏控制**:
- 假如当前不是最后一卷（距离大结局还有10章以上），绝对禁止进入结局篇章。
- 假如是最后一卷，必须开始收束剧情进入大结局。

请以 JSON 格式返回剧情弧规划。"""
        
        result = self.generate_json(prompt, temperature=0.7)
        self.log("剧情弧规划完成")
        return result
    
    def make_decision(
        self,
        bible: StoryBible,
        conflict_description: str,
        options: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        做出决策(当有冲突时)
        
        Args:
            bible: 故事圣经
            conflict_description: 冲突描述
            options: 选项列表,每个选项包含 {"option": "选项描述", "pros": "优点", "cons": "缺点"}
            
        Returns:
            决策结果
        """
        self.log("进行决策仲裁...")
        
        options_text = "\n\n".join([
            f"**选项 {i+1}**: {opt['option']}\n优点: {opt['pros']}\n缺点: {opt['cons']}"
            for i, opt in enumerate(options)
        ])
        
        prompt = f"""作为总编,请对以下冲突做出决策。
目标: 确保小说既有【极致的爽感】，又有【神作的逻辑】。

**冲突描述**:
{conflict_description}

**可选方案**:
{options_text}

**当前故事状态**:
- 当前章节: {bible.current_chapter}
- 主线: {bible.main_plot_summary}

请综合评估以下维度:
1. **爽度(Cool Factor)**: 是否能带来强烈的情绪释放或期待满足？
2. **逻辑性(Logic)**: 是否符合世界观和人物性格？(拒绝降智光环)
3. **长期收益**: 是否有利于长线铺垫和人物成长？

请以 JSON 格式返回决策:
{{
    "chosen_option": 选项编号(1, 2, ...),
    "reasoning": "决策理由 (请解释为什么这个选项能在保证逻辑的前提下带来最大的爽感)",
    "modifications": "对选中方案的修改建议(如果有,如何微调以增加爽度或修补逻辑漏洞)"
}}"""
        
        result = self.generate_json(prompt, temperature=0.6)
        self.log(f"决策完成: 选择选项 {result['chosen_option']}")
        return result
    
    def _build_context(self, bible: StoryBible, current_chapter: int) -> str:
        """构建上下文摘要"""
        context_parts = []
        
        # 主要角色状态
        main_chars = [char for char in bible.characters.values() 
                     if char.first_appearance_chapter and char.first_appearance_chapter <= current_chapter]
        if main_chars:
            context_parts.append("**主要角色**:")
            for char in main_chars[:5]:  # 只显示前 5 个
                context_parts.append(f"- {char.name}: {char.identity}, 位于 {char.current_location}, "
                                   f"战力 {char.power_level}, 状态 {char.state.value}")
        
        # 最近事件
        recent_events = bible.get_recent_events(5)
        if recent_events:
            context_parts.append("\n**最近事件**:")
            for event in recent_events:
                context_parts.append(f"- 第{event.chapter}章: {event.description}")
        
        return "\n".join(context_parts)
    
    def _format_open_loops(self, bible: StoryBible) -> str:
        """格式化未回收伏笔"""
        active_loops = bible.get_active_loops()
        if not active_loops:
            return "无未回收伏笔"
        
        lines = []
        for loop in active_loops[:10]:  # 只显示前 10 个
            overdue = "⚠️ 超期" if loop.is_overdue(bible.current_chapter) else ""
            lines.append(f"- [{loop.category}] {loop.title} (第{loop.planted_chapter}章埋下, "
                        f"权重{loop.weight}) {overdue}")
        
        return "\n".join(lines)

    def summarize_volume(self, bible: StoryBible, volume_number: int) -> str:
        """
        总结某一卷的内容
        """
        start_chapter = (volume_number - 1) * 10 + 1
        end_chapter = volume_number * 10
        self.log(f"正在总结第 {volume_number} 卷 ({start_chapter}-{end_chapter}章)...")
        
        # 收集本卷大纲
        chapters_text = []
        for i in range(start_chapter, end_chapter + 1):
            outline = bible.chapter_outlines.get(i)
            if outline:
                chapters_text.append(f"第{i}章: {outline.summary}")
        
        chapters_content = "\n".join(chapters_text)
        
        prompt = f"""作为总编，请对第 {volume_number} 卷进行精炼总结。
        
**本卷内容 ({start_chapter}-{end_chapter}章)**:
{chapters_content}

**要求**:
1. 概括本卷的核心剧情走向。
2. 记录主角的关键成长与获得的收益(爽点)。
3. 记录重要的人物关系变化。
4. 记录未解决的重大伏笔。

请返回一段 300-500 字的总结文本。"""

        summary = self.generate(prompt, temperature=0.7)
        self.log(f"第 {volume_number} 卷总结完成")
        return summary

    def perform_cumulative_review(self, bible: StoryBible, current_volume_number: int) -> str:
        """
        执行累计回顾 (在开始新一卷之前)
        """
        self.log(f"正在进行第 {current_volume_number} 卷前的全书累计回顾...")
        
        # 收集之前的卷总结
        summaries_text = []
        for v in range(1, current_volume_number):
            summary = bible.volume_summaries.get(v, "")
            if summary:
                summaries_text.append(f"== 第 {v} 卷总结 ==\n{summary}")
        
        if not summaries_text:
            return "无前文记录 (首卷)"
            
        previous_content = "\n\n".join(summaries_text)
        
        prompt = f"""作为总编，在开始创作第 {current_volume_number} 卷之前，必须对前 {current_volume_number-1} 卷进行深度回顾，确保剧情连贯。

**前文综述**:
{previous_content}

**当前状态**:
- 主线目标: {bible.main_plot_summary}
- 活跃伏笔: {len(bible.get_active_loops())} 个

**要求**:
请生成一份【剧情连贯性审查报告】，包含：
1. **前情提要**: 用一句话概括主角目前的处境。
2. **逻辑连续性**: 指出必须在下一卷延续的剧情线索（逻辑不可断层）。
3. **人物一致性**: 提醒核心角色的性格底色和当前心理状态。
4. **期待管理**: 读者现在最期待解决的问题是什么？

这份报告将作为第 {current_volume_number} 卷创作的核心指导。"""

        review = self.generate(prompt, temperature=0.7)
        self.log("累计回顾完成")
        return review
