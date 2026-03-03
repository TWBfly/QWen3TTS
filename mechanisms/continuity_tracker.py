"""
Continuity Tracker (连续性追踪器)
追踪人物出场连续性、检测断层、管理伏笔网络
"""

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


@dataclass
class ContinuityGap:
    """人物连续性断层"""
    character: str
    last_seen_vol: int
    reappear_vol: int
    gap_length: int
    severity: str  # "critical" / "warning" / "info"
    suggestion: str


@dataclass 
class CharacterPresence:
    """人物出场记录"""
    name: str
    volumes_appeared: List[int] = field(default_factory=list)
    roles_per_volume: Dict[int, str] = field(default_factory=dict)  # vol -> "key"/"new"/"mentioned"
    first_appearance: int = 0
    last_appearance: int = 0
    total_appearances: int = 0
    is_core: bool = False


class ContinuityTracker:
    """连续性追踪器"""
    
    # 核心角色不得消失超过此值
    CORE_MAX_GAP = 3
    # 重要配角不得消失超过此值
    SUPPORTING_MAX_GAP = 8
    # 一般角色最大间隔
    MINOR_MAX_GAP = 15
    # 出场次数达此值视为核心角色
    CORE_THRESHOLD = 10
    # 出场次数达此值视为重要配角
    SUPPORTING_THRESHOLD = 4
    
    def __init__(self):
        self.presence_matrix: Dict[str, CharacterPresence] = {}
        self.normalized_names: Dict[str, str] = {}  # 别名 -> 标准名
        
    def _normalize_name(self, raw_name: str) -> str:
        """
        标准化角色名称，去除注释性后缀
        例: "秦征（边军校尉）" -> "秦征"
        """
        if raw_name in self.normalized_names:
            return self.normalized_names[raw_name]
        
        # 去除括号注释
        name = raw_name.strip()
        for opener, closer in [("（", "）"), ("(", ")")]:
            if opener in name:
                name = name[:name.index(opener)].strip()
        
        # 缓存映射
        self.normalized_names[raw_name] = name
        return name
    
    def build_presence_matrix(self, bible) -> Dict[str, CharacterPresence]:
        """
        构建人物 × 卷出场矩阵
        
        Args:
            bible: Story Bible
            
        Returns:
            人物出场记录字典
        """
        self.presence_matrix = {}
        
        sorted_vols = sorted(bible.volume_plans.items(), key=lambda x: int(x[0]))
        
        for vol_num_key, plan in sorted_vols:
            vol_num = int(vol_num_key)
            
            # 提取该卷提到的所有角色
            key_chars = plan.key_characters if hasattr(plan, 'key_characters') else plan.get('key_characters', [])
            new_chars = plan.new_characters if hasattr(plan, 'new_characters') else plan.get('new_characters', [])
            
            for raw_name in key_chars:
                name = self._normalize_name(raw_name)
                if not name:
                    continue
                if name not in self.presence_matrix:
                    self.presence_matrix[name] = CharacterPresence(
                        name=name,
                        first_appearance=vol_num
                    )
                cp = self.presence_matrix[name]
                if vol_num not in cp.volumes_appeared:
                    cp.volumes_appeared.append(vol_num)
                cp.roles_per_volume[vol_num] = "key"
                cp.last_appearance = max(cp.last_appearance, vol_num)
                cp.total_appearances += 1
            
            for raw_name in new_chars:
                name = self._normalize_name(raw_name)
                if not name:
                    continue
                if name not in self.presence_matrix:
                    self.presence_matrix[name] = CharacterPresence(
                        name=name,
                        first_appearance=vol_num
                    )
                cp = self.presence_matrix[name]
                if vol_num not in cp.volumes_appeared:
                    cp.volumes_appeared.append(vol_num)
                if vol_num not in cp.roles_per_volume:
                    cp.roles_per_volume[vol_num] = "new"
                cp.last_appearance = max(cp.last_appearance, vol_num)
                cp.total_appearances += 1
            
            # 也从 summary 中检测提及
            summary = plan.summary if hasattr(plan, 'summary') else plan.get('summary', '')
            events_text = ""
            key_events = plan.key_events if hasattr(plan, 'key_events') else plan.get('key_events', [])
            events_text = " ".join(key_events)
            full_text = f"{summary} {events_text}"
            
            # 在文本中搜索已知角色
            for name in list(self.presence_matrix.keys()):
                if name in full_text and vol_num not in self.presence_matrix[name].volumes_appeared:
                    self.presence_matrix[name].volumes_appeared.append(vol_num)
                    self.presence_matrix[name].roles_per_volume[vol_num] = "mentioned"
                    self.presence_matrix[name].last_appearance = max(
                        self.presence_matrix[name].last_appearance, vol_num
                    )
                    self.presence_matrix[name].total_appearances += 1
        
        # 排序出场卷号
        for cp in self.presence_matrix.values():
            cp.volumes_appeared = sorted(set(cp.volumes_appeared))
            cp.is_core = cp.total_appearances >= self.CORE_THRESHOLD
        
        return self.presence_matrix
    
    def detect_gaps(self) -> List[ContinuityGap]:
        """
        检测人物出场断层
        
        Returns:
            断层列表
        """
        gaps = []
        
        for name, cp in self.presence_matrix.items():
            if len(cp.volumes_appeared) < 2:
                continue
            
            # 确定最大间隔阈值
            if cp.is_core or cp.total_appearances >= self.CORE_THRESHOLD:
                max_gap = self.CORE_MAX_GAP
                char_type = "核心角色"
            elif cp.total_appearances >= self.SUPPORTING_THRESHOLD:
                max_gap = self.SUPPORTING_MAX_GAP
                char_type = "重要配角"
            else:
                max_gap = self.MINOR_MAX_GAP
                char_type = "一般角色"
            
            # 检测连续出场之间的间隔
            for i in range(len(cp.volumes_appeared) - 1):
                vol_a = cp.volumes_appeared[i]
                vol_b = cp.volumes_appeared[i + 1]
                gap = vol_b - vol_a
                
                if gap > max_gap:
                    severity = "critical" if gap > max_gap * 2 else "warning"
                    gaps.append(ContinuityGap(
                        character=name,
                        last_seen_vol=vol_a,
                        reappear_vol=vol_b,
                        gap_length=gap,
                        severity=severity,
                        suggestion=f"{char_type}「{name}」从第{vol_a}卷消失到第{vol_b}卷（间隔{gap}卷），"
                                   f"建议在第{vol_a+1}~{vol_b-1}卷中通过侧面提及、传闻或他人口述来保持存在感。"
                    ))
        
        # 按严重程度和间隔排序
        gaps.sort(key=lambda g: (-1 if g.severity == "critical" else 0, -g.gap_length))
        return gaps
    
    def build_foreshadowing_network(self, bible) -> Dict[str, Any]:
        """
        构建伏笔网络
        
        Args:
            bible: Story Bible
            
        Returns:
            伏笔网络数据
        """
        network = {
            "planted": [],    # 埋设的伏笔
            "resolved": [],   # 已回收的伏笔
            "dangling": [],   # 悬空的伏笔 (埋了没收)
            "characters_involved": defaultdict(list),  # 角色 -> 涉及的伏笔
        }
        
        all_planted = {}  # title -> vol_num
        all_resolved = set()
        
        sorted_vols = sorted(bible.volume_plans.items(), key=lambda x: int(x[0]))
        
        for vol_num_key, plan in sorted_vols:
            vol_num = int(vol_num_key)
            
            loops_to_plant = plan.loops_to_plant if hasattr(plan, 'loops_to_plant') else plan.get('loops_to_plant', [])
            loops_to_resolve = plan.loops_to_resolve if hasattr(plan, 'loops_to_resolve') else plan.get('loops_to_resolve', [])
            
            for loop in loops_to_plant:
                if loop:
                    all_planted[loop] = vol_num
                    network["planted"].append({
                        "title": loop,
                        "planted_vol": vol_num,
                        "status": "open"
                    })
                    # 关联角色
                    key_chars = plan.key_characters if hasattr(plan, 'key_characters') else plan.get('key_characters', [])
                    for c in key_chars:
                        cn = self._normalize_name(c)
                        if cn:
                            network["characters_involved"][cn].append(loop)
            
            for loop in loops_to_resolve:
                if loop:
                    all_resolved.add(loop)
                    network["resolved"].append({
                        "title": loop,
                        "resolved_vol": vol_num
                    })
        
        # 找出悬空伏笔
        for title, planted_vol in all_planted.items():
            if title not in all_resolved:
                network["dangling"].append({
                    "title": title,
                    "planted_vol": planted_vol,
                    "status": "dangling"
                })
        
        return network
    
    def verify_character_plot_contribution(self, bible) -> Dict[str, Any]:
        """
        验证每个角色是否推动了剧情
        
        Returns:
            角色剧情贡献报告
        """
        if not self.presence_matrix:
            self.build_presence_matrix(bible)
        
        foreshadow = self.build_foreshadowing_network(bible)
        
        report = {
            "推动剧情的角色": [],
            "可能冗余的角色": [],
            "统计": {}
        }
        
        for name, cp in self.presence_matrix.items():
            involved_loops = foreshadow["characters_involved"].get(name, [])
            
            if cp.total_appearances >= 3 or len(involved_loops) > 0:
                report["推动剧情的角色"].append({
                    "name": name,
                    "出场卷数": cp.total_appearances,
                    "关联伏笔": involved_loops[:5],
                    "跨度": f"第{cp.first_appearance}卷 ~ 第{cp.last_appearance}卷"
                })
            elif cp.total_appearances <= 1 and not involved_loops:
                report["可能冗余的角色"].append({
                    "name": name,
                    "出场卷数": cp.total_appearances,
                    "建议": "考虑增加此角色的出场频率，或赋予其推动剧情的伏笔任务"
                })
        
        report["统计"] = {
            "总角色数": len(self.presence_matrix),
            "推动剧情": len(report["推动剧情的角色"]),
            "可能冗余": len(report["可能冗余的角色"])
        }
        
        return report
    
    def generate_continuity_report(self, bible) -> str:
        """生成完整的 Markdown 连续性报告"""
        self.build_presence_matrix(bible)
        gaps = self.detect_gaps()
        foreshadow = self.build_foreshadowing_network(bible)
        contribution = self.verify_character_plot_contribution(bible)
        
        lines = []
        lines.append("# 📊 人物连续性 & 伏笔追踪报告\n")
        
        # ======= 角色统计 =======
        core = [cp for cp in self.presence_matrix.values() if cp.is_core]
        supporting = [cp for cp in self.presence_matrix.values() 
                      if self.SUPPORTING_THRESHOLD <= cp.total_appearances < self.CORE_THRESHOLD]
        minor = [cp for cp in self.presence_matrix.values() 
                 if cp.total_appearances < self.SUPPORTING_THRESHOLD]
        
        lines.append(f"## 角色统计\n")
        lines.append(f"| 类别 | 数量 |")
        lines.append(f"|---|---|")
        lines.append(f"| 🌟 核心角色 (≥{self.CORE_THRESHOLD}卷) | {len(core)} |")
        lines.append(f"| ⭐ 重要配角 (≥{self.SUPPORTING_THRESHOLD}卷) | {len(supporting)} |")
        lines.append(f"| 📌 一般角色 | {len(minor)} |")
        lines.append(f"| **总计** | **{len(self.presence_matrix)}** |")
        lines.append("")
        
        # 核心角色出场概览
        if core:
            lines.append("### 核心角色出场热力图\n")
            lines.append("| 角色 | 出场卷数 | 首次 | 末次 | 出场记录 |")
            lines.append("|---|---|---|---|---|")
            for cp in sorted(core, key=lambda x: -x.total_appearances):
                vols_str = ",".join(str(v) for v in cp.volumes_appeared[:20])
                if len(cp.volumes_appeared) > 20:
                    vols_str += "..."
                lines.append(f"| {cp.name} | {cp.total_appearances} | 第{cp.first_appearance}卷 | 第{cp.last_appearance}卷 | {vols_str} |")
            lines.append("")
        
        # ======= 断层检测 =======
        lines.append(f"## ⚠️ 人物连续性断层 ({len(gaps)} 处)\n")
        if gaps:
            critical = [g for g in gaps if g.severity == "critical"]
            warning = [g for g in gaps if g.severity == "warning"]
            
            if critical:
                lines.append("### 🔴 严重断层\n")
                for g in critical:
                    lines.append(f"- **{g.character}**: 第{g.last_seen_vol}卷 → 第{g.reappear_vol}卷 (消失 {g.gap_length} 卷)")
                    lines.append(f"  - 💡 {g.suggestion}")
                lines.append("")
            
            if warning:
                lines.append("### 🟡 一般断层\n")
                for g in warning:
                    lines.append(f"- **{g.character}**: 第{g.last_seen_vol}卷 → 第{g.reappear_vol}卷 (消失 {g.gap_length} 卷)")
                lines.append("")
        else:
            lines.append("✅ 未发现人物连续性断层\n")
        
        # ======= 伏笔网络 =======
        lines.append(f"## 🎯 伏笔追踪\n")
        lines.append(f"| 指标 | 数量 |")
        lines.append(f"|---|---|")
        lines.append(f"| 已埋伏笔 | {len(foreshadow['planted'])} |")
        lines.append(f"| 已回收 | {len(foreshadow['resolved'])} |")
        lines.append(f"| ⚠️ 悬空伏笔 | {len(foreshadow['dangling'])} |")
        lines.append("")
        
        if foreshadow["dangling"]:
            lines.append("### 悬空伏笔 (未回收)\n")
            for d in foreshadow["dangling"]:
                lines.append(f"- 第{d['planted_vol']}卷埋设: _{d['title']}_")
            lines.append("")
        
        # ======= 角色贡献 =======
        lines.append(f"## 👥 角色剧情贡献\n")
        lines.append(f"- 推动剧情: {contribution['统计']['推动剧情']} 人")
        lines.append(f"- 可能冗余: {contribution['统计']['可能冗余']} 人\n")
        
        if contribution["可能冗余的角色"]:
            lines.append("### 可能冗余的角色\n")
            for c in contribution["可能冗余的角色"][:20]:
                lines.append(f"- {c['name']} (出场{c['出场卷数']}卷) — {c['建议']}")
            lines.append("")
        
        return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="人物连续性追踪器")
    parser.add_argument("--story", type=str, default="万族之劫_仿写", help="小说名称")
    parser.add_argument("--bible", type=str, default="story_bible_agent.json", help="Bible 文件名")
    parser.add_argument("--output", type=str, default=None, help="输出报告路径")
    
    args = parser.parse_args()
    
    storage = Config.get_storage_manager(args.story)
    bible = storage.load_story_bible(args.bible)
    
    if not bible:
        print("错误: 无法加载 Story Bible")
        sys.exit(1)
    
    tracker = ContinuityTracker()
    md = tracker.generate_continuity_report(bible)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"报告已保存到 {args.output}")
    else:
        print(md)
