#!/usr/bin/env python3
"""
QWen3TTS 一键小说大纲生成器 (run_novel.py)
============================================

用法:
  python run_novel.py \\
    --reference /path/to/参考小说/1/总.md \\
    --setting "架空古代" \\
    --tags "群像" \\
    --output /path/to/dagang/大王饶命_仿写_细纲.md

功能:
  1. 解析参考小说 → 提取结构、人物、剧情模式
  2. 在 novel_data/ 下创建小说数据文件夹
  3. 初始化 Story Bible + 约束体系
  4. 生成完整的 IDE Agent 工作流配置
  5. 按批次 (10卷/批) 生成 100 卷大纲

注意:
  本脚本不依赖 LLM API。它生成结构化的工作流，
  由 IDE 中的 AI Agent 执行实际的内容生成。
"""

import sys
import os
import json
import re
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from storage import StorageManager
from models import StoryBible, VolumePlan, CharacterCard, CharacterState, OpenLoop, LoopStatus


# ==========================================================================
# 参考小说分析器
# ==========================================================================
class ReferenceAnalyzer:
    """分析参考小说，提取可仿写的内核结构"""
    
    def __init__(self, reference_path: str):
        self.reference_path = reference_path
        self.content = ""
        self.chapters = []
        self.characters = {}
        self.plot_structure = {}
        self.themes = []
        
    def analyze(self) -> dict:
        """完整分析参考小说"""
        print(f"\n📖 分析参考小说: {self.reference_path}")
        
        # 读取内容
        with open(self.reference_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        
        total_lines = len(self.content.split('\n'))
        print(f"   总行数: {total_lines}")
        
        # 提取章节
        self.chapters = self._extract_chapters()
        print(f"   章节数: {len(self.chapters)}")
        
        # 提取人物
        self.characters = self._extract_characters()
        print(f"   人物数: {len(self.characters)}")
        
        # 分析结构
        self.plot_structure = self._analyze_structure()
        print(f"   剧情阶段: {len(self.plot_structure.get('phases', []))}")
        
        # 提取主题
        self.themes = self._extract_themes()
        print(f"   核心主题: {', '.join(self.themes[:5])}")
        
        return {
            "total_chapters": len(self.chapters),
            "total_characters": len(self.characters),
            "characters": self.characters,
            "plot_structure": self.plot_structure,
            "themes": self.themes,
            "chapter_samples": self.chapters[:3],  # 前3章样本
        }
    
    def _extract_chapters(self) -> list:
        """提取章节结构"""
        chapters = []
        parts = re.split(r'(?=\n# 第\d+章)', self.content)
        
        for part in parts:
            match = re.match(r'\s*# (第\d+章.*?)[\n\r]', part)
            if match:
                title = match.group(1).strip()
                
                # 提取场景
                scene_match = re.search(r'##\s*场景\s*\n(.*?)(?=\n##|\Z)', part, re.DOTALL)
                scene = scene_match.group(1).strip() if scene_match else ""
                
                # 提取人物列表
                char_match = re.search(r'##\s*人物\s*\n(.*?)(?=\n##|\Z)', part, re.DOTALL)
                chars_text = char_match.group(1).strip() if char_match else ""
                
                # 提取剧情概要
                plot_match = re.search(r'##\s*剧情概要\s*\n(.*?)(?=\n##|\Z)', part, re.DOTALL)
                plot = plot_match.group(1).strip() if plot_match else ""
                
                chapters.append({
                    "title": title,
                    "scene": scene[:200],
                    "characters": chars_text[:300],
                    "plot": plot[:300],
                })
        
        return chapters
    
    def _extract_characters(self) -> dict:
        """提取人物信息"""
        characters = {}
        # 匹配 **名字**：描述 或 - **名字**：描述
        pattern = r'\*\*([^*]+)\*\*[：:]\s*(.+?)(?=\n|$)'
        
        for match in re.finditer(pattern, self.content):
            name = match.group(1).strip()
            desc = match.group(2).strip()
            
            if name and len(name) <= 10 and name not in characters:
                characters[name] = desc[:100]
        
        return characters
    
    def _analyze_structure(self) -> dict:
        """分析剧情结构"""
        total = len(self.chapters)
        if total == 0:
            return {"phases": []}
        
        # 按10章一卷估算阶段
        phases = []
        chapters_per_phase = max(total // 10, 1)
        
        for i in range(0, total, chapters_per_phase):
            batch = self.chapters[i:i+chapters_per_phase]
            if batch:
                phase_plots = [ch.get('plot', '') for ch in batch]
                phases.append({
                    "range": f"第{i+1}~{min(i+chapters_per_phase, total)}章",
                    "sample_plot": phase_plots[0][:150] if phase_plots else ""
                })
        
        return {"phases": phases[:10]}  # 最多10个阶段
    
    def _extract_themes(self) -> list:
        """提取核心主题"""
        theme_keywords = {
            "成长": ["成长", "蜕变", "觉醒", "领悟"],
            "权谋": ["阴谋", "算计", "布局", "棋局", "权力"],
            "友情": ["兄弟", "朋友", "伙伴", "战友"],
            "爱情": ["心动", "倾心", "守护", "爱"],
            "家国": ["天下", "苍生", "百姓", "国家"],
            "复仇": ["仇恨", "报仇", "血债", "冤屈"],
            "江湖": ["江湖", "武林", "门派", "宗门"],
            "战争": ["大军", "攻城", "战场", "兵马"],
            "悬疑": ["真相", "秘密", "谜团", "隐秘"],
            "热血": ["热血", "燃烧", "拼命", "搏杀"],
        }
        
        found = []
        for theme, keywords in theme_keywords.items():
            count = sum(1 for kw in keywords if kw in self.content)
            if count >= 2:
                found.append(theme)
        
        return found if found else ["成长", "热血"]
    
    def get_analysis_summary(self) -> str:
        """生成分析摘要 (用于 prompt 注入)"""
        char_list = "\n".join([f"- {name}: {desc}" for name, desc in list(self.characters.items())[:20]])
        
        return f"""【参考小说分析摘要】
总章节数: {len(self.chapters)}
核心人物数: {len(self.characters)}
核心主题: {', '.join(self.themes)}

主要人物:
{char_list}

剧情结构: {len(self.plot_structure.get('phases', []))} 个阶段
"""


# ==========================================================================
# 小说项目初始化器
# ==========================================================================
class NovelProjectSetup:
    """创建小说数据文件夹和初始配置"""
    
    def __init__(self, novel_name: str, setting: str, tags: list, output_path: str):
        self.novel_name = novel_name
        self.setting = setting
        self.tags = tags
        self.output_path = output_path
        self.data_dir = Path(__file__).parent / "novel_data" / f"{novel_name}_仿写"
        
    def setup(self) -> dict:
        """创建完整的项目结构"""
        print(f"\n📁 创建小说数据文件夹: {self.data_dir}")
        
        # 创建目录结构
        dirs = [
            self.data_dir,
            self.data_dir / "bibles",
            self.data_dir / "volume_plans",
            self.data_dir / "character_profiles",
            self.data_dir / "quality_reports",
            self.data_dir / "backups",
        ]
        
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            
        print(f"   ✅ 目录结构已创建")
        
        # 创建项目配置
        project_config = {
            "novel_name": self.novel_name,
            "setting": self.setting,
            "tags": self.tags,
            "output_path": self.output_path,
            "created_at": datetime.now().isoformat(),
            "total_volumes": 100,
            "chapters_per_volume": 10,
            "total_chapters": 1000,
            "status": "initialized",
            "current_batch": 0,
        }
        
        config_path = self.data_dir / "project_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(project_config, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ 项目配置已保存: {config_path}")
        
        # 初始化输出文件
        output = Path(self.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        if not output.exists():
            with open(output, 'w', encoding='utf-8') as f:
                f.write(f"# {self.novel_name}（仿写）\n\n")
                f.write(f"**背景**: {self.setting}\n")
                f.write(f"**标签**: {', '.join(self.tags)}\n")
                f.write(f"**总卷数**: 100卷（1000章）\n\n")
                f.write("---\n\n")
            print(f"   ✅ 输出文件已初始化: {self.output_path}")
        else:
            print(f"   ℹ️ 输出文件已存在，将追加内容")
        
        return project_config


# ==========================================================================
# 批次生成管理器
# ==========================================================================
class BatchGenerationManager:
    """管理 100 批 × 1 卷/批 的分批生成"""
    
    BATCH_SIZE = 1  # 每批1卷
    TOTAL_BATCHES = 100  # 共100批 = 100卷
    
    def __init__(self, data_dir: Path, output_path: str, analysis: dict, novel_name: str):
        self.data_dir = data_dir
        self.output_path = output_path
        self.analysis = analysis
        self.novel_name = novel_name
        self.state_file = data_dir / "generation_state.json"
        
    def get_current_state(self) -> dict:
        """获取当前生成进度"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"completed_batches": [], "current_batch": 0}
    
    def save_state(self, state: dict):
        """保存生成进度"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def get_batch_prompt(self, batch_num: int) -> str:
        """生成第 N 批的完整 prompt（含进化系统注入）"""
        start_vol = (batch_num - 1) * self.BATCH_SIZE + 1
        end_vol = batch_num * self.BATCH_SIZE
        
        # 读取已生成的内容作为回顾
        lookback = self._get_lookback(batch_num)
        
        # 构建约束
        constraints = self._build_constraints()
        
        # 加载核心人物设定库
        character_bible = self._load_character_bible(batch_num)
        
        # === 进化系统注入 ===
        evolution_sections = self._build_evolution_sections(batch_num)
        
        prompt = f"""你是一名经验丰富的小说作家，严格以人物为核心，必须以人物推动剧情。

【任务】生成第 {start_vol}~{end_vol} 卷（第 {(start_vol-1)*10+1}~{end_vol*10} 章）的详细大纲。

【参考小说内核分析】
{self.analysis.get('themes', [])} 
核心人物数: {self.analysis.get('total_characters', 0)}
核心主题: {', '.join(self.analysis.get('themes', []))}

【创作设定】
- 小说名称: {self.novel_name}（仿写）
- 背景: 架空古代
- 标签: 群像
- 不可抄袭原作内容，人物名称不可一样
- 必须保持一个世界观

{character_bible}

{lookback}

{evolution_sections}

{constraints}

【输出格式】每卷必须包含:
## 第X卷：卷名

**【阶段】**: 铺垫期/发展期/高潮期/收尾期
**【前卷回顾】**: 上一卷的结果
**【本卷提要】**: 本卷核心一句话
**【核心冲突】**: 本卷核心冲突
**【主角成长】**: 主角在本卷的成长
**【关键人物】**: 本卷涉及的关键人物
**【新登场人物】**: 新出现的人物（含身份）
**【伏笔种植】**: 本卷埋下的伏笔
**【伏笔回收】**: 本卷回收的伏笔

**【大纲逻辑】**:
1. ...（6-8个剧情节点）

**【十章细目】**:
- 第X章: 章名 - 核心事件 | 场景 | 关键人物
...

---

现在请生成第 {start_vol} 卷到第 {end_vol} 卷的详细大纲："""
        
        return prompt

    def _build_evolution_sections(self, batch_num: int) -> str:
        """构建进化系统的三段注入内容"""
        sections = []
        try:
            # 1. 历史教训（错题本）
            from mechanisms.negative_memory import NegativeMemory
            neg = NegativeMemory()
            lessons = neg.get_lessons(top_k=5)
            if lessons:
                sections.append(lessons)

            # 2. 生成前反思
            from mechanisms.reflection import ReflectionEngine
            ref = ReflectionEngine()
            reflection = ref.generate_reflection(self.novel_name, batch_num)
            if reflection:
                sections.append(reflection)

            # 3. 跨作品经验
            from mechanisms.meta_rag import MetaRAG
            meta = MetaRAG()
            tags = self.analysis.get('tags', ['群像'])
            cross = meta.query_cross_novel(self.novel_name, batch_num, tags)
            if cross:
                sections.append(cross)

            # 4. 高分案例 Few-Shot（每5卷注入一次，避免 Prompt 过长）
            if batch_num % 5 == 1 or batch_num <= 3:
                from mechanisms.positive_memory import PositiveMemory
                pos = PositiveMemory()
                exemplars = pos.get_exemplars(tags=tags, top_k=1, exclude_novel=self.novel_name)
                if exemplars:
                    sections.append(exemplars)

        except Exception as e:
            # 进化系统不应阻塞主流程
            sections.append(f"<!-- 进化系统加载异常: {e} -->")

        return "\n".join(sections)
    
    def _load_character_bible(self, batch_num: int) -> str:
        """加载核心人物设定库并注入到 prompt 中
        
        前5批(卷1-50): 注入完整设定库
        后5批(卷51-100): 注入压缩摘要（节省 token）
        """
        bible_path = self.data_dir / "核心人物设定库.md"
        
        if not bible_path.exists():
            print(f"   ⚠️ 未找到核心人物设定库: {bible_path}")
            return "【核心人物设定库】: 未配置，请先生成人物设定库。"
        
        with open(bible_path, 'r', encoding='utf-8') as f:
            full_bible = f.read()
        
        if batch_num <= 5:
            # 前50卷: 完整注入
            return f"""【核心人物设定库（铁律：所有剧情必须由以下人物的性格冲突与利益碰撞推动，严禁凭空创造新的核心人物替代以下角色）】

{full_bible}"""
        else:
            # 后50卷: 提取摘要（姓名+身份+核心诉求+弧光阶段）
            summary_lines = ["【核心人物设定库·摘要版（完整版请参阅前文，此处仅列关键信息以节省篇幅）】\n"]
            current_char = None
            current_block = []
            
            for line in full_bible.split('\n'):
                # 匹配人物标题 (### N. 姓名...)
                if line.startswith('### ') and '.' in line:
                    if current_char and current_block:
                        summary_lines.append(self._compress_character(current_char, current_block))
                    current_char = line.strip()
                    current_block = []
                elif current_char:
                    current_block.append(line)
            
            # 最后一个人物
            if current_char and current_block:
                summary_lines.append(self._compress_character(current_char, current_block))
            
            # 附加九线叙事总览
            nine_lines_start = full_bible.find('## 九线叙事总览')
            if nine_lines_start != -1:
                summary_lines.append('\n' + full_bible[nine_lines_start:])
            
            return '\n'.join(summary_lines)
    
    def _compress_character(self, title: str, block: list) -> str:
        """将单个人物的完整设定压缩为关键摘要（宽松正则匹配）"""
        block_text = '\n'.join(block)
        
        def _extract(pattern: str, text: str) -> str:
            """用正则宽松匹配字段值"""
            m = re.search(pattern, text)
            return m.group(1).strip() if m else ""
        
        identity = _extract(r'\*{0,2}身份\*{0,2}\s*[：:]+\s*(.*)', block_text)
        desire = _extract(r'\*{0,2}核心诉求\*{0,2}\s*[：:]+\s*(.*)', block_text)
        arc = _extract(r'\*{0,2}人物弧光\*{0,2}\s*[：:]+\s*(.*)', block_text)
        narrative_line = _extract(r'\*{0,2}所属叙事线\*{0,2}\s*[：:]+\s*(.*)', block_text)
        
        return f"{title}\n  身份: {identity} | 诉求: {desire} | 弧光: {arc} | 叙事线: {narrative_line}\n"
    
    def _get_lookback(self, batch_num: int) -> str:
        """构建前情回顾"""
        if batch_num <= 1:
            return "【前情回顾】: 这是第一批，无前情。"
        
        # 检查前一批是否已完成
        state = self.get_current_state()
        prev_batch = batch_num - 1
        if prev_batch not in state.get("completed_batches", []):
            print(f"   ⚠️ 警告: 第 {prev_batch} 批尚未保存 (save)，前情回顾可能不完整！")
            print(f"   👉 建议先执行: python run_novel.py --step save --batch {prev_batch} --content-file <草稿路径>")
        
        # 从输出文件读取已生成内容
        try:
            if not os.path.exists(self.output_path):
                return f"【前情回顾】: ⚠️ 输出文件不存在 ({self.output_path})，请先完成前 {prev_batch} 批的生成和保存。"
            
            with open(self.output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if len(content.strip()) < 200:
                return f"【前情回顾】: ⚠️ 输出文件内容过少（仅 {len(content)} 字符），请确认前 {prev_batch} 批已正确保存。"
            
            # 提取最近 3 卷的摘要
            lookback_lines = ["【前情回顾（分层压缩）】"]
            
            prev_end = (batch_num - 1) * self.BATCH_SIZE
            
            # 远期: 第1批到倒数第3批 (一句话概括)
            if batch_num > 3:
                lookback_lines.append(f"\n📌 远期 (第1~{(batch_num-3)*10}卷): 已生成，请参考输出文件前部分。")
            
            # 近期: 最后2批完整内容
            recent_start = max(1, (batch_num - 2) * self.BATCH_SIZE + 1)
            recent_end = prev_end
            
            for vol_num in range(recent_start, recent_end + 1):
                vol_pattern = f"## 第{vol_num}卷"
                if vol_pattern in content:
                    idx = content.index(vol_pattern)
                    # 取到下一卷或末尾
                    next_vol = f"## 第{vol_num + 1}卷"
                    end_idx = content.index(next_vol) if next_vol in content else min(idx + 2000, len(content))
                    vol_text = content[idx:end_idx].strip()
                    # 压缩为前500字符
                    lookback_lines.append(f"\n{vol_text[:500]}...")
            
            return "\n".join(lookback_lines)
        except Exception as e:
            return f"【前情回顾】: ⚠️ 读取输出文件失败 ({e})，请回顾输出文件中第1~{(batch_num-1)*self.BATCH_SIZE}卷的内容。"
    
    def _build_constraints(self) -> str:
        """构建创作约束"""
        base = f"""【创作约束 (铁律)】
1. 严格禁止: {', '.join(Config.FORBIDDEN_CONCEPTS)}
2. 必须: 架空古代世界观,严禁科幻/穿越/系统元素
3. 必须: 三幕九线写作手法,明确九条叙事线
4. 必须: 每个人物都是主角,都有完整弧光和高光时刻
5. 必须: 草蛇灰线伏笔千里,前后逻辑严密闭合
6. 必须: 龙头猪肚豹尾,全程高能无尿点
7. 严禁: 换地图打怪升级的流水线写作
8. 严禁: 机械降神/降智/强行装逼/圣母
9. 反派没有绝对的恶,立意高远,都是为了自己认为正确的事情
10. 大结局(第100卷)必须是一切都是人在背后操控,非天道/命运
11. 【新登场人物】中每个角色必须有具体的姓名（2-3字中文名），严禁出现泛指（如"帝国将军""敌方提督"），严禁出现集体名词（如"全城军民""千万学子"），严禁出现非人类实体（如"AI""机甲""战堡"）
12. 必须且只能使用 IDE 中多 agent team 协作生成，严禁使用 local LLM server（Ollama, AI Studio 或 API Key 等）。

【🔴 红线警告：卷数必须绝对完整 🔴】
你每次都必须且**只能生成整整 {self.BATCH_SIZE} 卷**（即包含标题 `## 第X卷` 到 `## 第Y卷` 的所有内容）！
绝不允许中途跳过、漏写任何一卷！当你正在生成某卷时，必须清清楚楚写出完整的这 {self.BATCH_SIZE} 卷。少写一卷系统将直接拒绝入库！！！

{Config.PACING_RULES}

{Config.MULTI_THREAD_NARRATIVE_RULES}

{Config.SCENE_DEPTH_RULES}

{Config.POWER_SCALING_RULES}

{Config.NARRATIVE_QUALITY_RULES}

{Config.NARRATIVE_SPOTLIGHT_RULES}

【🔴 红线警告：世界观锁死 🔴】
本小说的背景设定为「架空古代」，从第1卷到第100卷必须始终处于同一个古代世界观之下。
严禁出现以下任何元素（即便是用"古代化包装"或"机关包装"也严禁）：
❌ 太空/星际元素：星舰、飞船、战堡、星球大战、跃迁、FTL、银河
❌ 高科技元素：AI、机甲、机关高达、激光、暗物质、量子、机器人、机甲炼狱、齿轮核心
❌ 维度/异常元素：高维、低维、平行世界、位面穿梭、深渊、克苏鲁、异形、深渊水晶
❌ 系统/生化元素：系统面板、升级、生化、变异、丧尸、活尸、瓦斯、水晶、抗体、生化兵工厂
❌ 西方科幻实体：利维坦、赛博朋克、纳米机器人
后期（卷51+）的终极大敌必须是「人」而非超自然神明、AI系统或深渊渊主。
终极冲突必须是「理念之争」「路线之争」「人心博弈」，而非单纯打败外星/变异入侵者。
幕后黑手必须是有名有姓且有政治/军事目的的人物，而非抽象概念（天道/命运/系统）。"""
        return base

    def save_batch_output(self, batch_num: int, content: str):
        """将一批生成的内容保存到输出文件和数据文件夹"""
        # 追加到输出文件
        with open(self.output_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{content}\n")
        
        # 保存到数据文件夹
        batch_file = self.data_dir / "volume_plans" / f"batch_{batch_num:03d}_v{batch_num}.md"
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新 generation_state.json
        state = self.get_current_state()
        if batch_num not in state["completed_batches"]:
            state["completed_batches"].append(batch_num)
        state["current_batch"] = batch_num
        self.save_state(state)
        
        # 同步更新 project_config.json
        config_path = self.data_dir / "project_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["current_batch"] = batch_num
                config["status"] = "completed" if batch_num >= self.TOTAL_BATCHES else "in_progress"
                config["last_updated"] = datetime.now().isoformat()
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # 非致命，不阻断主流程
        
        print(f"   ✅ 第{batch_num}批 (卷{batch_num}) 已保存")


# ==========================================================================
# 工作流生成器
# ==========================================================================
class WorkflowGenerator:
    """生成 IDE Agent 可执行的工作流文件"""
    
    @staticmethod
    def generate_workflow(novel_name: str, reference_path: str, output_path: str, 
                         data_dir: Path, analysis: dict) -> str:
        """生成完整的工作流 Markdown"""
        
        workflow = f"""---
description: 一键生成 {novel_name} 仿写 100卷大纲
---

# 🚀 小说大纲一键生成工作流

## 项目信息
- **小说名称**: {novel_name}_仿写
- **参考小说**: {reference_path}
- **输出文件**: {output_path}
- **数据目录**: {data_dir}
- **目标**: 100卷 × 10章/卷 = 1000章

## 执行步骤

### 步骤 0: 环境初始化 (已自动完成 ✅)
// turbo
```bash
cd {Path(__file__).parent} && python run_novel.py --reference "{reference_path}" --setting "架空古代" --tags "群像" --output "{output_path}" --step setup
```

### 步骤 1: 生成核心人物设定库

#### 1a. 生成人物设定 prompt
// turbo
```bash
cd {Path(__file__).parent} && python run_novel.py --reference "{reference_path}" --output "{output_path}" --step characters
```
**铁律要求**: 使用上面生成的 prompt（位于 `{data_dir}/character_profiles/character_bible_prompt.md`），并且**必须使用 IDE 中模型多 agent team 协作，严禁依赖 local LLM server（Ollama 或 AI studio 或 API key）**来创作 20 个核心人物的详细设定，然后执行:

#### 1b. 保存人物设定库
// turbo
```bash
cd {Path(__file__).parent} && python run_novel.py --output "{output_path}" --step save-characters --content-file "{data_dir}/character_profiles/character_bible_draft.md"
```

### 步骤 2: 循环逐卷生成大纲 (第 1~100 卷)

这是一个循环任务。请从第 1 卷开始，一直循环执行到第 100 卷。**每次只生成 1 卷（10 章）**。

对于每一卷 `N` (从 1 到 100):

#### 1. 生成 Prompt
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --reference "{reference_path}" --output "{output_path}" --step prompt --batch N
```
*(注意：请将上面命令中的 `N` 替换为当前的卷号 1, 2, 3...)*

#### 2. 生成大纲内容
读取上一步生成的 `{data_dir}/volume_plans/batch_N_prompt.md`。然后为你自己创建一个任务，根据 prompt 创作该卷（10章）的详细大纲内容。
**铁律要求**: 必须使用 IDE 中模型多 agent team 协作完成该任务，绝对严禁使用 local LLM server（Ollama 或 AI studio 或 API key）。

#### 3. 保存并检查
将你生成的大纲内容保存为 `{data_dir}/volume_plans/batch_N_draft.md`，然后执行保存和检查命令：
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step save --batch N --content-file "{data_dir}/volume_plans/batch_N_draft.md"
```
*(注意：请将上面命令和路径中的 `N` 替换为当前的卷号)*

#### 4. 处理检查结果
- **如果检查通过**（系统输出保存成功），则继续下一卷 `N+1`。
- **如果检查失败**（发现禁词或其他问题被拒绝保存），请根据错误提示，重新修改你的草稿文件，再次执行第 3 步的保存检查命令，直到通过为止。
"""
        
        workflow += """### 步骤 12: 生成人物详志
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step profiles
```

### 步骤 13: 毒点检测
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step poison-scan
```

### 步骤 14: 连贯性检查
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step continuity-check
```

### 步骤 15: 终局大纲深度体检与修复评估
当 100 卷（1000章）生成完毕后，执行终局评价脚本。该脚本将生成极度严格的结构审查 Prompt，请 AI 读取大纲全文并输出诊断修改报告：
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step final-review
```
```
使用上述命令生成的 `{data_dir}/quality_reports/final_review_prompt.md` 作为输入指令，为你自己创建一个任务，审查最终输出的大纲文件 `{output_path}`，直接定位硬伤断层并打分。
**铁律要求**: 必须使用 IDE 中模型多 agent team 协作，严禁使用 local LLM server（Ollama 或 AI studio 或 API key）。

### 步骤 16: 完结经验沉淀（自我进化）
当终局审查通过后，执行经验沉淀命令，将本书的创作经验写入全局知识库，供后续小说使用：
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step evolve-summary
```
读取生成的 `{data_dir}/quality_reports/evolve_summary_prompt.md`，由 IDE Agent 执行深度总结并反馈。

### 步骤 17: 查看进化统计面板
随时可以执行此命令查看自我进化系统的整体状态：
// turbo
```bash
cd """ + str(Path(__file__).parent) + f""" && python run_novel.py --output "{output_path}" --step evolve-stats
```
"""
        return workflow


# ==========================================================================
# 主入口
# ==========================================================================
def parse_prompt(prompt_text: str) -> dict:
    """解析用户提示词，提取参考路径、设定、输出路径"""
    result = {
        "reference": "",
        "setting": "架空古代",
        "tags": ["群像"],
        "output": "",
    }
    
    # 提取参考路径
    ref_match = re.search(r'仿写其内核\s*(.+?\.md)', prompt_text)
    if not ref_match:
        ref_match = re.search(r'拆解.*?(\S+\.md)', prompt_text)
    if ref_match:
        result["reference"] = ref_match.group(1).strip()
    
    # 提取设定
    setting_match = re.search(r'背景为[：:]\s*(.+?)(?=[，,\n]|$)', prompt_text)
    if setting_match:
        result["setting"] = setting_match.group(1).strip()
    
    # 提取标签
    tags_match = re.search(r'标签为[：:]\s*(.+?)(?=[，,\n]|$)', prompt_text)
    if tags_match:
        result["tags"] = [t.strip() for t in tags_match.group(1).split('、')]
    
    # 提取输出路径
    output_match = re.search(r'保存到\s*(.+?\.md)', prompt_text)
    if output_match:
        result["output"] = output_match.group(1).strip()
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="QWen3TTS 一键小说大纲生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整一键初始化
  python run_novel.py \\
    --reference /path/to/大王饶命/1/总.md \\
    --setting "架空古代" --tags "群像" \\
    --output /path/to/dagang/大王饶命_仿写_细纲.md

  # 从提示词解析
  python run_novel.py --prompt "拆解参考仿写其内核/path/to/总.md，保存到/path/to/output.md"
  
  # 分步执行
  python run_novel.py --output /path/to/output.md --step prompt --batch 1
  python run_novel.py --output /path/to/output.md --step save --batch 1 --content-file draft.md
        """
    )
    
    parser.add_argument("--prompt", type=str, help="完整的提示词 (自动解析)")
    parser.add_argument("--reference", type=str, help="参考小说路径")
    parser.add_argument("--setting", type=str, default="架空古代", help="背景设定")
    parser.add_argument("--tags", type=str, default="群像", help="标签 (逗号分隔)")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--step", type=str, choices=["setup", "characters", "save-characters", "prompt", "save", "validate", "profiles", "poison-scan", "continuity-check", "final-review", "evolve-summary", "evolve-stats", "status"],
                       help="执行特定步骤")
    parser.add_argument("--batch", type=int, help="批次号 (1-100)")
    parser.add_argument("--content-file", type=str, help="内容文件路径 (用于 save 步骤)")
    
    args = parser.parse_args()
    
    # 从 prompt 解析参数
    if args.prompt:
        parsed = parse_prompt(args.prompt)
        args.reference = args.reference or parsed["reference"]
        args.output = args.output or parsed["output"]
        args.setting = parsed["setting"]
        args.tags = ','.join(parsed["tags"])
    
    # 验证必要参数
    if not args.output and not args.step == "status":
        parser.error("必须提供 --output 参数")
    
    # 解析标签
    tags = [t.strip() for t in args.tags.split(',')]
    
    # 推断小说名称
    if args.output:
        novel_name = Path(args.output).stem.replace('_仿写_细纲', '').replace('_仿写', '').replace('_细纲', '')
    else:
        novel_name = "未命名"
    
    data_dir = Path(__file__).parent / "novel_data" / f"{novel_name}_仿写"
    
    print(f"""
╔══════════════════════════════════════════════════╗
║         QWen3TTS 一键小说大纲生成器              ║
╚══════════════════════════════════════════════════╝
  小说名称: {novel_name}_仿写
  背景设定: {args.setting}
  标签: {', '.join(tags)}
  输出路径: {args.output}
  数据目录: {data_dir}
""")
    
    # ===== 分步执行 =====
    if args.step == "status":
        _show_status(data_dir)
        return
    
    if args.step == "prompt":
        _generate_prompt(data_dir, args.output, args.batch, novel_name)
        return
    
    if args.step == "validate":
        _run_validate(args.batch, args.content_file)
        return
    
    if args.step == "save":
        _save_batch(data_dir, args.output, args.batch, args.content_file, novel_name)
        return
    
    if args.step == "characters":
        _generate_character_prompt(data_dir, args.output, novel_name, args.reference)
        return
    
    if args.step == "save-characters":
        _save_characters(data_dir, args.content_file)
        return
    
    if args.step == "profiles":
        _generate_profiles(novel_name)
        return
    
    if args.step == "poison-scan":
        _run_poison_scan(novel_name)
        return
    
    if args.step == "continuity-check":
        _run_continuity_check(args.output)
        return
        
    if args.step == "final-review":
        _run_final_review(novel_name, args.output, data_dir)
        return
    
    if args.step == "evolve-summary":
        _run_evolve_summary(novel_name, args.output, data_dir, tags)
        return
    
    if args.step == "evolve-stats":
        _show_evolution_stats()
        return
    
    # ===== 完整初始化流程 =====
    if not args.reference:
        parser.error("完整初始化需要 --reference 参数")
    
    # Step 1: 分析参考小说
    analyzer = ReferenceAnalyzer(args.reference)
    analysis = analyzer.analyze()
    
    # 保存分析结果
    analysis_path = data_dir / "reference_analysis.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 将不可序列化的内容处理掉
    serializable_analysis = {
        "total_chapters": analysis["total_chapters"],
        "total_characters": analysis["total_characters"],
        "characters": analysis["characters"],
        "themes": analysis["themes"],
        "reference_path": args.reference,
    }
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_analysis, f, ensure_ascii=False, indent=2)
    
    # Step 2: 创建项目结构
    setup = NovelProjectSetup(novel_name, args.setting, tags, args.output)
    config = setup.setup()
    
    # Step 3: 生成工作流
    workflow_content = WorkflowGenerator.generate_workflow(
        novel_name, args.reference, args.output, data_dir, analysis
    )
    
    # 保存工作流到 .agent/workflows/
    workflow_dir = Path(__file__).parent.parent / ".agent" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = workflow_dir / f"generate-{novel_name}.md"
    with open(workflow_path, 'w', encoding='utf-8') as f:
        f.write(workflow_content)
    print(f"\n📋 工作流已生成: {workflow_path}")
    
    # 同时保存分析摘要到数据目录
    summary_path = data_dir / "analysis_summary.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(analyzer.get_analysis_summary())
    
    # Step 4: 生成第一批 prompt
    batch_mgr = BatchGenerationManager(data_dir, args.output, serializable_analysis, novel_name)
    prompt = batch_mgr.get_batch_prompt(1)
    
    prompt_path = data_dir / "volume_plans" / "batch_01_prompt.md"
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"""
╔══════════════════════════════════════════════════╗
║                 ✅ 初始化完成!                    ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  📖 参考小说: {analysis['total_chapters']:>4} 章, {analysis['total_characters']:>3} 个人物            ║
║  📁 数据目录: novel_data/{novel_name}_仿写       ║
║  📋 工作流:   .agent/workflows/generate-{novel_name}.md  ║
║  📝 第1批prompt已就绪                             ║
║                                                  ║
║  👉 下一步: 使用 IDE Agent 执行工作流             ║
║     或手动: python run_novel.py --step prompt     ║
║              --batch 1 --output {args.output}     ║
║                                                  ║
╚══════════════════════════════════════════════════╝
""")


# ==========================================================================
# 分步命令实现
# ==========================================================================
def _show_status(data_dir: Path):
    """显示当前生成进度"""
    state_file = data_dir / "generation_state.json"
    if state_file.exists():
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        completed = state.get("completed_batches", [])
        print(f"已完成批次: {completed}")
        print(f"进度: {len(completed)}/100 卷 ({len(completed) * 10}/1000 章)")
    else:
        print("尚未开始生成")


def _generate_prompt(data_dir: Path, output_path: str, batch_num: int, novel_name: str):
    """生成指定批次的 prompt"""
    if not batch_num:
        print("请指定 --batch 参数")
        return
    
    # 加载分析结果
    analysis_path = data_dir / "reference_analysis.json"
    analysis = {}
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
    
    batch_mgr = BatchGenerationManager(data_dir, output_path, analysis, novel_name)
    
    # 批次跳跃防护：检查是否跳过了前面的批次
    if batch_num > 1:
        state = batch_mgr.get_current_state()
        completed = state.get("completed_batches", [])
        for prev in range(1, batch_num):
            if prev not in completed:
                print(f"   ⚠️ 警告: 第 {prev} 批尚未完成，你正在跳到第 {batch_num} 批！")
                print(f"   👉 建议先完成第 {prev} 批的生成和保存")
    
    prompt = batch_mgr.get_batch_prompt(batch_num)
    
    # 保存 prompt
    prompt_path = data_dir / "volume_plans" / f"batch_{batch_num:02d}_prompt.md"
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n{'='*60}")
    print(f"第 {batch_num} 批 prompt 已生成: {prompt_path}")
    print(f"{'='*60}")
    print(prompt[:500])
    print(f"...(共 {len(prompt)} 字符)")


def _validate_content(content: str, batch_num: int = 0) -> tuple:
    """验证内容是否违反世界观约束
    
    Returns:
        (passed: bool, report: str)
        - passed=True: 无违规或仅警告级别 (命中 < 3)
        - passed=False: 严重违规 (命中 >= 3)，禁止保存
    """
    import re as _re
    
    report_lines = []
    total_hits = 0
    
    # 1. 禁词扫描（合并进化禁词）
    try:
        from mechanisms.config_evolver import ConfigEvolver
        evolver = ConfigEvolver()
        all_forbidden = evolver.get_all_forbidden_concepts()
    except Exception:
        all_forbidden = Config.FORBIDDEN_CONCEPTS
    
    forbidden_hits = []
    for concept in all_forbidden:
        count = content.count(concept)
        if count > 0:
            evolved_tag = " [进化新增]" if concept not in Config.FORBIDDEN_CONCEPTS else ""
            forbidden_hits.append(f"  ❌ \"{concept}\" 出现 {count} 次{evolved_tag}")
            total_hits += count
    
    if forbidden_hits:
        report_lines.append(f"\n🔴 禁词命中 ({len(forbidden_hits)} 个不同禁词，共 {total_hits} 次):")
        report_lines.extend(forbidden_hits)
    
    # 2. 角色名校验 (扫描【关键人物】和【新登场人物】行)
    char_violations = []
    char_lines = _re.findall(r'\*\*【(?:关键人物|新登场人物)】\*\*[：:]\s*(.*)', content)
    for line in char_lines:
        names = [n.strip() for n in _re.split(r'[、，,]', line) if n.strip()]
        for raw_name in names:
            # 解析 "名字（注释）" 格式
            name = raw_name
            for opener, closer in [('（', '）'), ('(', ')')]:
                if opener in raw_name:
                    name = raw_name[:raw_name.index(opener)].strip()
                    break
            if not name or name == '无':
                continue
            for pattern in Config.FORBIDDEN_CHARACTER_PATTERNS:
                if _re.search(pattern, name):
                    char_violations.append(f"  ❌ \"{raw_name}\" 匹配禁止模式 {pattern}")
                    total_hits += 1
                    break
    
    if char_violations:
        report_lines.append(f"\n🔴 角色名违规 ({len(char_violations)} 个):")
        report_lines.extend(char_violations)
    
    # 3. 卷号完整性检查
    vol_start = (batch_num - 1) * 1 + 1 if batch_num else 1
    vol_end = batch_num * 1 if batch_num else 100
    missing_vols = []
    for v in range(vol_start, vol_end + 1):
        if f"## 第{v}卷" not in content:
            missing_vols.append(v)
    if missing_vols:
        report_lines.append(f"\n🔴 致命错误 (缺失卷号): {missing_vols}，必须生成完整的 1 卷！")
    
    # 判定: 禁词少于3次，且不能有缺失的卷号
    passed = (total_hits < 3) and (len(missing_vols) == 0)
    
    if total_hits == 0 and not missing_vols:
        report = f"\n✅ 第{batch_num}批验证通过: 无违规, 卷号完整"
    elif passed:
        report = f"\n⚠️ 第{batch_num}批验证警告 (命中{total_hits}次, 允许保存):\n" + "\n".join(report_lines)
    else:
        report_header = f"\n❌ 第{batch_num}批验证失败"
        if len(missing_vols) > 0:
            report_header += f" (检测到漏卷 {missing_vols}, 绝对禁止保存):\n"
        else:
            report_header += f" (命中禁词{total_hits}次, 禁止保存):\n"
            
        report = report_header + "\n".join(report_lines)
        report += f"\n\n💡 请根据以上违规项修改草稿内容，或者要求 AI 重新生成缺失的卷后再次保存。"
    
    return passed, report


def _save_batch(data_dir: Path, output_path: str, batch_num: int, content_file: str, novel_name: str):
    """保存一批生成的内容（含验证门禁、AI 连贯性校验及进化系统反馈闭环）"""
    if not batch_num or not content_file:
        print("请指定 --batch 和 --content-file 参数")
        return
    
    with open(content_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # === 验证门禁 ===
    passed, report = _validate_content(content, batch_num)
    print(report)
    
    if not passed:
        # === 进化系统：记录失败到错题本 + 触发配置进化 ===
        try:
            from mechanisms.negative_memory import NegativeMemory
            from mechanisms.config_evolver import ConfigEvolver
            
            neg = NegativeMemory()
            # 提取命中的禁词
            from config import Config
            hit_words = [c for c in Config.FORBIDDEN_CONCEPTS if c in content]
            
            # 判断错误类型
            if "缺失卷号" in report or "漏卷" in report:
                error_type = "missing_volume"
            elif "角色名违规" in report:
                error_type = "character_name"
            else:
                error_type = "forbidden_word"
            
            neg.record_failure(
                novel_name=novel_name,
                batch_num=batch_num,
                error_type=error_type,
                details=report,
                forbidden_words_hit=hit_words,
                content_snippet=content[:200]
            )
            
            # 触发配置热生长
            evolver = ConfigEvolver()
            evolver.learn_new_pattern(content, error_type, report)
        except Exception as e:
            print(f"   ⚠️ 进化系统记录异常 (不影响主流程): {e}")
        
        print(f"\n🚫 保存被拒绝! 请修复上述违规后重新执行 save。")
        sys.exit(1)
        
    # === AI 逻辑连贯性校验 (Vector DB RAG) ===
    from mechanisms.rag_manager import RAGManager
    from mechanisms.consistency_checker import ConsistencyChecker
    from config import Config
    
    rag = RAGManager(str(data_dir))
    checker = ConsistencyChecker(novel_name, rag)
    
    print(f"\n⏳ 正在通过大模型与向量图谱进行 AI 逻辑连贯性深度校验...")
    ai_passed, ai_report = checker.check_draft(content, batch_num)
    print(ai_report)
    
    if not ai_passed:
        # === 进化系统：AI 驳回也记入错题本 ===
        try:
            from mechanisms.negative_memory import NegativeMemory
            neg = NegativeMemory()
            neg.record_failure(
                novel_name=novel_name,
                batch_num=batch_num,
                error_type="ai_rejected",
                details=ai_report,
                content_snippet=content[:200]
            )
        except Exception:
            pass
        
        print(f"\n🚫 AI主编驳回! 请根据上面的修改建议修复漏洞后重新执行 save。")
        sys.exit(1)
    
    # === 保存成功 ===
    batch_mgr = BatchGenerationManager(data_dir, output_path, {}, "")
    batch_mgr.save_batch_output(batch_num, content)
    
    # === 进化系统：收录高分案例 ===
    try:
        from mechanisms.positive_memory import PositiveMemory
        pos = PositiveMemory()
        pos.record_success(
            novel_name=novel_name,
            batch_num=batch_num,
            draft_snippet=content,
            tags=["群像", "架空古代"],
            score=100
        )
    except Exception as e:
        print(f"   ⚠️ 高分案例收录异常 (不影响主流程): {e}")


def _run_validate(batch_num: int, content_file: str):
    """独立验证步骤：扫描 draft 文件是否违规"""
    if not content_file:
        print("请指定 --content-file 参数")
        return
    
    if not os.path.exists(content_file):
        print(f"❌ 文件不存在: {content_file}")
        sys.exit(1)
    
    with open(content_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    passed, report = _validate_content(content, batch_num or 0)
    print(report)
    
    if not passed:
        print(f"\n❌ 验证失败，请修复后重新提交。")
        sys.exit(1)
    else:
        print(f"\n✅ 验证通过。")


def _generate_character_prompt(data_dir: Path, output_path: str, novel_name: str, reference_path: str = None):
    """生成核心人物设定库的 prompt"""
    
    # 加载分析结果
    analysis_path = data_dir / "reference_analysis.json"
    analysis = {}
    analysis_summary = ""
    
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
    
    # 如果没有传 --reference，从分析结果中回退读取
    if not reference_path and analysis.get('reference_path'):
        reference_path = analysis['reference_path']
        print(f"   ℹ️ 从 reference_analysis.json 回退读取参考路径: {reference_path}")
    
    summary_path = data_dir / "analysis_summary.md"
    if summary_path.exists():
        with open(summary_path, 'r', encoding='utf-8') as f:
            analysis_summary = f.read()
    
    # 如果提供了参考路径，读取更多内容
    ref_excerpt = ""
    if reference_path and os.path.exists(reference_path):
        with open(reference_path, 'r', encoding='utf-8') as f:
            ref_content = f.read()
        # 提取前100章的人物和剧情结构（限制在8000字符以内）
        ref_excerpt = ref_content[:8000]
    
    themes = ', '.join(analysis.get('themes', ['成长', '权谋', '友情', '爱情', '家国']))
    char_count = analysis.get('total_characters', 0)
    
    # 提取参考小说的人物列表
    ref_characters = ""
    if analysis.get('characters'):
        ref_chars = list(analysis['characters'].items())[:30]
        ref_characters = "\n".join([f"- {name}: {desc}" for name, desc in ref_chars])
    
    prompt = f"""你是一名经验丰富的小说架构师，专精于群像小说的人物设计。

【任务】根据参考小说的内核分析，为仿写小说《{novel_name}（仿写）》创建一份包含 20 个核心人物的《核心人物设定库》。

【参考小说内核分析】
核心主题: {themes}
核心人物数: {char_count}

{analysis_summary}

【参考小说人物列表（仅供参考内核，严禁照抄名字和设定）】
{ref_characters}

【参考小说片段（仅供分析叙事风格，严禁抄袭内容）】
{ref_excerpt[:3000]}

【创作设定】
- 小说名称: {novel_name}（仿写）
- 背景: 架空古代（严禁现代/科幻/穿越元素）
- 标签: 群像
- 严禁: {', '.join(Config.FORBIDDEN_CONCEPTS)}
- 必须: 三幕九线写作手法
- 反派没有绝对的恶，立意高远，都是为了自己认为正确的事情

【人物设计铁律】
1. 20个人物必须完全原创，名字和设定不可与参考小说雷同
2. 必须覆盖"主角阵营（6人）、对立阵营（5人）、中立/摇摆阵营（5人）、催化剂型人物（4人）"四类
3. 每个人物都是主角，都有完整弧光和高光时刻
4. 人物的性格必须有"矛盾面"——表面特征与深层创伤的对立
5. 所有人物的诉求必须基于合理的身世和动机，严禁脸谱化
6. 人物之间必须有多维度的交叉关系（盟友/敌对/暧昧/师徒等）
7. 20个人物必须分布在九条叙事线上，每条线至少2个核心人物
8. 必须且只能使用 IDE 中多 agent team 协作生成此人物设定库，严禁使用 local LLM server（Ollama, AI Studio 或 API Key 等）。

【输出格式】请严格按照以下格式输出：

# 《{novel_name}》仿写 · 核心人物设定库

> **铁律**：所有剧情必须由以下人物的性格冲突、利益碰撞与命运交织推动。严禁机械降神。
> **背景**：架空古代 · 群像 · 九线叙事

---

## 一、主角阵营（6人）

### 1. [姓名]（[定位，如"主角"/"义妹"等]）
- **身份**：[详细身份描述]
- **性格**：[主性格描述，至少3个维度]
- **性格矛盾**：[表面特征与深层创伤的对立]
- **身世背景**：[详细身世，至少3句话]
- **核心诉求**：[TA一生最想要的东西。深层：更深层的渴望]
- **与主角的交集**：[如何与主角产生关联]
- **人物弧光**：[从A到B的变化轨迹，用→符号连接]
- **高光时刻**：
  - 第X卷：[具体场景描述，包含台词]
  - 第X卷：[具体场景描述，包含台词]
- **所属叙事线**：[九线中的哪条]
- **关键关系**：[与其他核心人物的关系]

（对每个人物重复以上格式）

---

## 二、对立阵营（5人）
（同上格式）

## 三、中立/摇摆阵营（5人）
（同上格式）

## 四、催化剂型人物（4人）
（同上格式）

---

## 九线叙事总览

| 线号 | 叙事线名称 | 核心人物 | 线索关键词 |
|:---:|:---:|:---:|:---:|
| 1 | **[线名]（主线）** | [人物1]、[人物2] | [一句话关键词] |
...（共9条线）

---

## 核心人物关系网

（用文本图的方式展示所有人物之间的关系）

现在请生成完整的《核心人物设定库》："""
    
    # 保存 prompt
    prompt_path = data_dir / "character_profiles" / "character_bible_prompt.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n{'='*60}")
    print(f"核心人物设定库 prompt 已生成: {prompt_path}")
    print(f"{'='*60}")
    print(prompt[:800])
    print(f"...(共 {len(prompt)} 字符)")
    print(f"\n👉 下一步: ")
    print(f"   1. 使用 IDE 中模型多 agent team 协作，根据此 prompt 生成人物设定")
    print(f"      (严禁使用 local LLM server/Ollama/AI studio/API key)")
    print(f"   2. 将生成的内容保存为草稿文件")
    print(f"   3. 执行: python run_novel.py --output \"{output_path}\" --step save-characters --content-file <草稿文件路径>")


def _save_characters(data_dir: Path, content_file: str):
    """保存 AI 生成的核心人物设定库"""
    if not content_file:
        print("请指定 --content-file 参数（人物设定草稿文件路径）")
        return
    
    content_path = Path(content_file)
    if not content_path.exists():
        print(f"❌ 文件不存在: {content_file}")
        return
    
    with open(content_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 保存为核心人物设定库
    bible_path = data_dir / "核心人物设定库.md"
    with open(bible_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 备份一份
    backup_path = data_dir / "character_profiles" / "character_bible_draft.md"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 统计人物数量
    char_count = content.count('### ')
    
    print(f"\n✅ 核心人物设定库已保存!")
    print(f"   📁 主文件: {bible_path}")
    print(f"   📁 备份: {backup_path}")
    print(f"   👥 检测到 {char_count} 个人物条目")
    print(f"   📏 文件大小: {len(content)} 字符")
    print(f"\n👉 下一步: 开始生成大纲 (人物设定库将自动注入每批次 prompt)")
    print(f"   python run_novel.py --output <输出路径> --step prompt --batch 1")


def _generate_profiles(novel_name: str):
    """生成人物小传"""
    from scripts.generate_profiles import ProfileGenerator
    from mechanisms.continuity_tracker import ContinuityTracker
    
    storage = Config.get_storage_manager(novel_name + "_仿写")
    bible = storage.load_story_bible("story_bible_agent.json")
    
    if not bible:
        print("❌ Story Bible 不存在，请先运行 setup")
        return
    
    tracker = ContinuityTracker()
    gen = ProfileGenerator()
    gen.generate_all_profiles(
        bible=bible,
        output_dir=str(Config.STORAGE_DIR / f"{novel_name}_仿写" / "character_profiles")
    )


def _run_poison_scan(novel_name: str):
    """运行毒点检测"""
    from mechanisms.poison_detector import PoisonDetector
    
    storage = Config.get_storage_manager(novel_name + "_仿写")
    bible = storage.load_story_bible("story_bible_agent.json")
    
    if not bible:
        print("❌ Story Bible 不存在")
        return
    
    detector = PoisonDetector()
    report = detector.scan_all_volumes(bible)
    md = detector.generate_report_markdown(report)
    
    report_path = Config.STORAGE_DIR / f"{novel_name}_仿写" / "quality_reports" / "poison_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"毒点报告已保存: {report_path}")


def _run_continuity_check(output_path: str):
    """运行连贯性检查 (基于已生成的大纲文本)"""
    if not os.path.exists(output_path):
        print(f"❌ 输出文件不存在: {output_path}")
        return
    
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    # 检查卷数完整性
    volumes_found = re.findall(r'## 第(\d+)卷', content)
    vol_nums = sorted([int(v) for v in volumes_found])
    
    print(f"📊 连贯性检查:")
    print(f"   已生成卷数: {len(vol_nums)}/100")
    
    if vol_nums:
        print(f"   卷号范围: {min(vol_nums)}~{max(vol_nums)}")
        
        # 检查缺失卷
        expected = set(range(1, max(vol_nums) + 1))
        missing = expected - set(vol_nums)
        if missing:
            print(f"   ⚠️ 缺失卷: {sorted(missing)}")
        else:
            print(f"   ✅ 无缺失卷")
    
    # 检查禁词
    from config import Config
    forbidden_hits = []
    for concept in Config.FORBIDDEN_CONCEPTS:
        if concept in content:
            count = content.count(concept)
            forbidden_hits.append(f"{concept}({count}次)")
    
    if forbidden_hits:
        print(f"   ⚠️ 禁词出现: {', '.join(forbidden_hits)}")
    else:
        print(f"   ✅ 无禁词")

def _run_final_review(novel_name: str, output_path: str, data_dir: Path):
    """运行终局大纲深度体检与修复评估"""
    print(f"\n🔍 [终局大纲审查] 正在生成《{novel_name}》 100 卷最终评估 Prompt...")
    
    try:
        from scripts.final_reviewer import generate_review_prompt
        prompt_content = generate_review_prompt(novel_name, output_path)
        
        report_dir = data_dir / "quality_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        prompt_file = report_dir / "final_review_prompt.md"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
            
        print(f"✅ 终局审查 Prompt 已生成: {prompt_file}\n")
        print(f"👉 请指示 IDE（AI）读取此 Prompt 内容，并对大纲文件 ({output_path}) 执行全方位终极无情审查与评分！")
        
    except Exception as e:
        print(f"❌ 生成终局审查 Prompt 失败: {e}")

def _run_evolve_summary(novel_name: str, output_path: str, data_dir: Path, tags: list):
    """完结经验沉淀：将一本已完成小说的关键经验写入全局知识库"""
    print(f"\n🧠 [经验沉淀] 正在为《{novel_name}》生成创作经验总结...")
    
    from mechanisms.meta_rag import MetaRAG
    meta = MetaRAG()
    
    # 生成总结 Prompt 供 IDE Agent 使用
    prompt = meta.generate_novel_summary_prompt(novel_name, output_path)
    
    report_dir = data_dir / "quality_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    prompt_file = report_dir / "evolve_summary_prompt.md"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    # 同时自动注册一条基础记录（即使 IDE Agent 不执行总结，系统也有基础记忆）
    try:
        # 读取输出文件获取基础统计
        total_vols = 0
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            import re as _re
            total_vols = len(_re.findall(r'## 第\d+卷', content))
        
        # 从错题本获取教训
        from mechanisms.negative_memory import NegativeMemory
        neg = NegativeMemory()
        neg_stats = neg.get_stats()
        learnings = []
        if neg_stats.get("top_forbidden"):
            top_words = [w for w, c in neg_stats["top_forbidden"][:3]]
            learnings.append(f"最常犯的禁词错误：{'、'.join(top_words)}，需要在后续创作中彻底回避。")
        if neg_stats.get("by_type", {}).get("missing_volume", 0) > 0:
            learnings.append("曾出现卷号缺失问题，后续必须严格校验输出完整性。")
        if not learnings:
            learnings.append("本次创作过程相对顺利，校验通过率高。")
        
        meta.register_novel_completion(
            novel_name=novel_name,
            setting="架空古代",
            tags=tags,
            total_volumes=total_vols,
            key_learnings=learnings,
            best_techniques=["群像叙事交织", "伏笔层层递进"],
            character_insights=["角色矛盾面塑造是群像小说核心驱动力"]
        )
    except Exception as e:
        print(f"   ⚠️ 基础记录注册异常: {e}")
    
    print(f"✅ 经验沉淀 Prompt 已生成: {prompt_file}")
    print(f"👉 请指示 IDE Agent 读取此 Prompt，执行深度总结后将结果反馈回系统。")
    print(f"   基础经验已自动注册到全局知识库。")


def _show_evolution_stats():
    """显示自我进化系统的统计面板"""
    print(f"\n{'='*60}")
    print(f"         🧬 自我进化系统统计面板")
    print(f"{'='*60}")
    
    # 1. 错题本
    try:
        from mechanisms.negative_memory import NegativeMemory
        neg = NegativeMemory()
        neg_stats = neg.get_stats()
        print(f"\n📝 错题本:")
        print(f"   累计失败记录: {neg_stats['total']} 次")
        if neg_stats.get("by_type"):
            for t, c in neg_stats["by_type"].items():
                print(f"   - {t}: {c} 次")
        if neg_stats.get("top_forbidden"):
            words = ", ".join([f"{w}(×{c})" for w, c in neg_stats["top_forbidden"][:5]])
            print(f"   高频禁词: {words}")
    except Exception as e:
        print(f"   ⚠️ 加载失败: {e}")
    
    # 2. 高分案例库
    try:
        from mechanisms.positive_memory import PositiveMemory
        pos = PositiveMemory()
        pos_stats = pos.get_stats()
        print(f"\n⭐ 高分案例库:")
        print(f"   收录案例: {pos_stats['total']} 个")
        print(f"   平均得分: {pos_stats['avg_score']}")
        if pos_stats.get("novels"):
            print(f"   覆盖小说: {', '.join(pos_stats['novels'])}")
    except Exception as e:
        print(f"   ⚠️ 加载失败: {e}")
    
    # 3. 配置进化
    try:
        from mechanisms.config_evolver import ConfigEvolver
        evolver = ConfigEvolver()
        evo_stats = evolver.get_stats()
        print(f"\n🧬 配置热生长:")
        print(f"   进化新增禁词: {evo_stats['evolved_words_count']} 个")
        print(f"   候选观察词: {evo_stats['candidate_count']} 个")
        print(f"   进化事件: {evo_stats['evolution_events']} 次")
        evolved = evolver.get_evolved_forbidden_words()
        if evolved:
            print(f"   新增禁词列表: {', '.join(evolved)}")
    except Exception as e:
        print(f"   ⚠️ 加载失败: {e}")
    
    # 4. 跨小说知识图谱
    try:
        from mechanisms.meta_rag import MetaRAG
        meta = MetaRAG()
        meta_stats = meta.get_stats()
        print(f"\n🌐 跨小说知识图谱:")
        print(f"   已完成小说: {meta_stats['completed_novels']} 本")
        print(f"   叙事技法: {meta_stats['techniques_count']} 条")
        print(f"   角色原型: {meta_stats['archetypes_count']} 条")
    except Exception as e:
        print(f"   ⚠️ 加载失败: {e}")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
