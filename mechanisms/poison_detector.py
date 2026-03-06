"""
Poison Detector (毒点检测器) - 检测剧情中的写作毒点
检测机械降神、降智、强行装逼、圣母、战力崩坏等常见网文弊病
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


class PoisonType(Enum):
    """毒点类型"""
    DEUS_EX_MACHINA = "机械降神"
    DUMBING_DOWN = "降智"
    FORCED_COOL = "强行装逼"
    MARY_SUE = "圣母"
    POWER_CREEP = "战力崩坏"
    CLICHE = "剧情老套"
    SCIFI_LEAK = "科幻穿越泄露"
    PLOT_ARMOR = "主角光环"
    PACING_ISSUE = "节奏失控"


class Severity(Enum):
    """严重级别"""
    FATAL = "致命"      # 🔴 必须修改
    SERIOUS = "严重"    # 🟡 强烈建议修改
    WARNING = "警告"    # 🟠 需要关注
    INFO = "提示"       # 🔵 供参考


@dataclass
class PoisonHit:
    """单个毒点命中"""
    poison_type: PoisonType
    severity: Severity
    keyword: str
    context: str        # 命中的上下文（前后各30字）
    location: str       # 位置描述
    suggestion: str     # 修改建议

    def to_dict(self):
        return {
            "type": self.poison_type.value,
            "severity": self.severity.value,
            "keyword": self.keyword,
            "context": self.context,
            "location": self.location,
            "suggestion": self.suggestion
        }


@dataclass
class PoisonReport:
    """毒点报告"""
    target: str
    total_hits: int = 0
    fatal_count: int = 0
    serious_count: int = 0
    warning_count: int = 0
    hits: List[PoisonHit] = field(default_factory=list)
    verdict: str = "PASS"

    def add_hit(self, hit: PoisonHit):
        self.hits.append(hit)
        self.total_hits += 1
        if hit.severity == Severity.FATAL:
            self.fatal_count += 1
        elif hit.severity == Severity.SERIOUS:
            self.serious_count += 1
        elif hit.severity == Severity.WARNING:
            self.warning_count += 1
        # 更新判定
        if self.fatal_count > 0:
            self.verdict = "REJECT"
        elif self.serious_count >= 3:
            self.verdict = "WARN"
        else:
            self.verdict = "PASS"


# ============================================================
# 毒点模式库 (Poison Pattern Library)
# ============================================================

POISON_PATTERNS: Dict[PoisonType, Dict[str, Any]] = {
    PoisonType.DEUS_EX_MACHINA: {
        "severity": Severity.FATAL,
        "keywords": [
            "天道", "命运安排", "冥冥之中", "天意如此", "上天注定",
            "正好", "恰巧", "碰巧", "刚好遇到", "巧合",
            "天降神兵", "奇迹般地", "莫名其妙就", "突然获得",
            "系统提示", "叮", "任务完成", "奖励发放",
            "凑巧", "无巧不成书", "老天开眼", "天助我也",
            "福星高照", "天降奇缘", "命中注定",
        ],
        "suggestion": "所有困境的解决必须源于角色的主动选择、智谋或牺牲，严禁依赖巧合或超自然力量。"
    },
    
    PoisonType.DUMBING_DOWN: {
        "severity": Severity.FATAL,
        "keywords": [
            "降智", "一时冲动", "忘记了", "没想到", "脑子一热",
            "失去理智", "冲昏头脑", "不假思索", "鬼使神差",
            "被仇恨蒙蔽", "不顾后果地", "莫名其妙地相信",
            "轻信", "落入显而易见的圈套", "明知是陷阱还跳",
            "送上门", "放下戒心", "毫无防备", "居然没人发现",
        ],
        "suggestion": "角色行为必须符合其智力水平和人设。如需冲动行为，须有充分的情绪铺垫和合理动机。"
    },
    
    PoisonType.FORCED_COOL: {
        "severity": Severity.SERIOUS,
        "keywords": [
            "不屑一顾", "碾压", "一指弹飞", "秒杀", "如蝼蚁",
            "在我面前不值一提", "给你一个机会", "跪下",
            "你也配", "蝼蚁", "不堪一击", "灰飞烟灭",
            "轻描淡写", "谈笑间", "一招制敌", "手到擒来",
            "我只用了三成功力", "随手一击", "弹指间",
            "装逼打脸", "一个能打的都没有",
        ],
        "suggestion": "展示实力应通过具体的战术描写和实际效果，而非空洞的碾压式描述。每次战斗都应有悬念和代价。"
    },
    
    PoisonType.MARY_SUE: {
        "severity": Severity.SERIOUS,
        "keywords": [
            "原谅", "不忍心", "放走", "宽恕敌人", "以德报怨",
            "饶你一命", "放过", "网开一面", "心太软",
            "妇人之仁", "不该杀他", "放虎归山",
            "人性本善", "浪子回头", "给他一个改过的机会",
            "我不能做和他一样的人", "对所有人都好",
        ],
        "suggestion": "角色做出宽恕决定时必须有充分的利益考量或代价，不能单纯出于善良。在残酷的世界观中，圣母行为=找死。"
    },
    
    PoisonType.POWER_CREEP: {
        "severity": Severity.FATAL,
        "keywords": [
            "突破", "暴涨", "觉醒", "开挂", "血脉觉醒",
            "隐藏血统", "天赋异禀", "百年一遇的天才",
            "连升三级", "实力暴增", "顿悟", "一夜之间",
            "战力飙升", "越级挑战", "以弱胜强（无合理铺垫）",
            "吊打同级", "仙人传功", "秘境奇遇", "丹药突破",
            "气运之子", "天选之人", "龙傲天", "弑神", "斩杀神明",
            "冰封长江", "劈碎古塔", "对冲十万大军", "一指灭城"
        ],
        "suggestion": "战力提升必须有漫长的训练/代价/铺垫。战力天花板必须锁死为武道宗师水平。"
    },
    
    PoisonType.CLICHE: {
        "severity": Severity.SERIOUS,
        "keywords": [
            "退婚", "废柴", "天才家族废物", "踩低捧高",
            "三年之约", "你们会后悔的", "且看他日",
            "扮猪吃虎", "大赛夺冠", "拍卖抢宝",
            "毒舌女配", "恶毒女配", "白莲花", "绿茶婊",
            "龙王赘婿", "全城震惊", "老爷子出手",
            "我爷爷是", "你知道我是谁吗", "有眼不识泰山",
            "跪着求我", "今天你对我爱答不理", "打脸",
            "失忆", "武功尽失", "天外陨铁", "坠崖", "随意复活", "老爷爷",
        ],
        "suggestion": "避免使用网文模板剧情。每个冲突都应有独特性，源于角色的个人情境而非套路。"
    },
    
    PoisonType.SCIFI_LEAK: {
        "severity": Severity.FATAL,
        "keywords": Config.FORBIDDEN_CONCEPTS + [
            "基因", "DNA", "量子", "纳米", "克隆", "芯片", "电磁",
            "引力波", "暗物质", "反物质", "核聚变", "激光",
            "星球", "太空", "飞船", "机器人", "赛博",
        ],
        "suggestion": "严格保持架空古代世界观。所有技术、医学、军事元素必须在古代技术范围内。"
    },
    
    PoisonType.PLOT_ARMOR: {
        "severity": Severity.SERIOUS,
        "keywords": [
            "千钧一发", "死里逃生", "九死一生", "绝处逢生",
            "险之又险", "差一点就", "幸好", "幸亏",
            "关键时刻", "最后关头", "千钧一发之际",
            "大难不死", "总能化险为夷",
        ],
        "suggestion": "主角的脱险必须有先前铺垫的伏笔或能力支撑，不能每次都'刚好'逃过。偶尔的失败和代价更能增加真实感。"
    },
    
    PoisonType.PACING_ISSUE: {
        "severity": Severity.WARNING,
        "keywords": [
            "一年后", "数年过去", "时光飞逝", "转眼间",
            "不知不觉", "岁月如梭", "弹指一挥间",
            "日复一日", "平静地过了", "无事发生",
            "一路顺利", "毫无阻碍", "轻松地完成",
        ],
        "suggestion": "时间跳跃必须交代角色在这段时间的更具体发展，不能用一句话略过重大变化。"
    },
}


class PoisonDetector:
    """毒点检测器"""
    
    def __init__(self, custom_patterns: Dict = None):
        """
        初始化检测器
        
        Args:
            custom_patterns: 额外的自定义毒点模式
        """
        self.patterns = dict(POISON_PATTERNS)
        if custom_patterns:
            self.patterns.update(custom_patterns)
    
    def scan_text(self, text: str, location: str = "") -> List[PoisonHit]:
        """
        扫描文本中的毒点
        
        Args:
            text: 待检测文本
            location: 位置描述
            
        Returns:
            命中的毒点列表
        """
        hits = []
        
        for poison_type, config in self.patterns.items():
            severity = config["severity"]
            suggestion = config["suggestion"]
            
            for keyword in config["keywords"]:
                # 查找所有出现的位置
                start = 0
                while True:
                    idx = text.find(keyword, start)
                    if idx == -1:
                        break
                    
                    # 提取上下文
                    ctx_start = max(0, idx - 30)
                    ctx_end = min(len(text), idx + len(keyword) + 30)
                    context = text[ctx_start:ctx_end]
                    if ctx_start > 0:
                        context = "..." + context
                    if ctx_end < len(text):
                        context = context + "..."
                    
                    hit = PoisonHit(
                        poison_type=poison_type,
                        severity=severity,
                        keyword=keyword,
                        context=context,
                        location=location,
                        suggestion=suggestion
                    )
                    hits.append(hit)
                    start = idx + len(keyword)
        
        return hits
    
    def scan_volume_plan(self, plan, vol_num: int, bible=None) -> PoisonReport:
        """扫描单卷规划 (Fix #15: 扩展扫描范围)"""
        report = PoisonReport(target=f"第{vol_num}卷")
        
        # 扫描所有文本字段
        texts = []
        if hasattr(plan, 'title'):
            texts.append(("标题", plan.title))
        if hasattr(plan, 'summary'):
            texts.append(("概要", plan.summary))
        if hasattr(plan, 'main_conflict'):
            texts.append(("核心冲突", plan.main_conflict))
        if hasattr(plan, 'protagonist_growth'):
            texts.append(("主角成长", plan.protagonist_growth))
        if hasattr(plan, 'key_events'):
            for i, event in enumerate(plan.key_events):
                texts.append((f"事件{i+1}", event))
        
        # Fix #15: 扫描伏笔
        if hasattr(plan, 'loops_to_plant'):
            for i, loop in enumerate(plan.loops_to_plant):
                texts.append((f"伏笔种植{i+1}", str(loop)))
        if hasattr(plan, 'loops_to_resolve'):
            for i, loop in enumerate(plan.loops_to_resolve):
                texts.append((f"伏笔回收{i+1}", str(loop)))
        
        # Fix #15: 扫描该卷对应的章节大纲 (如果 bible 提供)
        if bible and hasattr(bible, 'chapter_outlines'):
            start_ch = (vol_num - 1) * 10 + 1
            end_ch = vol_num * 10
            for ch_num in range(start_ch, end_ch + 1):
                if ch_num in bible.chapter_outlines:
                    outline = bible.chapter_outlines[ch_num]
                    if hasattr(outline, 'detailed_outline') and outline.detailed_outline:
                        texts.append((f"第{ch_num}章详纲", outline.detailed_outline))
                    if hasattr(outline, 'core_plot') and outline.core_plot:
                        texts.append((f"第{ch_num}章核心", outline.core_plot))
        
        for field_name, text in texts:
            if text:
                location = f"第{vol_num}卷 > {field_name}"
                hits = self.scan_text(str(text), location)
                for hit in hits:
                    report.add_hit(hit)
        
        return report
    
    def scan_all_volumes(self, bible) -> Dict[str, Any]:
        """
        扫描全部卷规划
        
        Args:
            bible: Story Bible
            
        Returns:
            完整毒点报告
        """
        full_report = {
            "总览": {
                "总卷数": len(bible.volume_plans),
                "致命毒点卷": [],
                "严重毒点卷": [],
                "清洁卷": [],
            },
            "全局统计": {
                "致命": 0,
                "严重": 0,
                "警告": 0,
                "total_hits": 0,
            },
            "毒点类型分布": {},
            "逐卷报告": {},
            "verdict": "PASS"
        }
        
        # 初始化类型分布
        for pt in PoisonType:
            full_report["毒点类型分布"][pt.value] = 0
        
        sorted_vols = sorted(bible.volume_plans.items(), key=lambda x: int(x[0]))
        
        for vol_num, plan in sorted_vols:
            report = self.scan_volume_plan(plan, int(vol_num))
            
            vol_key = f"第{vol_num}卷"
            full_report["逐卷报告"][vol_key] = {
                "verdict": report.verdict,
                "致命": report.fatal_count,
                "严重": report.serious_count,
                "警告": report.warning_count,
                "hits": [h.to_dict() for h in report.hits]
            }
            
            # 累加统计
            full_report["全局统计"]["致命"] += report.fatal_count
            full_report["全局统计"]["严重"] += report.serious_count
            full_report["全局统计"]["警告"] += report.warning_count
            full_report["全局统计"]["total_hits"] += report.total_hits
            
            # 更新类型分布
            for hit in report.hits:
                full_report["毒点类型分布"][hit.poison_type.value] += 1
            
            # 分类
            if report.fatal_count > 0:
                full_report["总览"]["致命毒点卷"].append(vol_key)
            elif report.serious_count > 0:
                full_report["总览"]["严重毒点卷"].append(vol_key)
            else:
                full_report["总览"]["清洁卷"].append(vol_key)
        
        # 全局判定
        if full_report["全局统计"]["致命"] > 0:
            full_report["verdict"] = "REJECT"
        elif full_report["全局统计"]["严重"] >= 5:
            full_report["verdict"] = "WARN"
        else:
            full_report["verdict"] = "PASS"
        
        return full_report
    
    def generate_report_markdown(self, full_report: Dict) -> str:
        """生成 Markdown 格式的毒点报告"""
        lines = []
        lines.append("# 🔍 毒点扫描报告\n")
        
        verdict = full_report["verdict"]
        emoji = {"PASS": "✅", "WARN": "⚠️", "REJECT": "❌"}
        lines.append(f"**总体判定**: {emoji.get(verdict, '❓')} {verdict}\n")
        
        # 全局统计
        stats = full_report["全局统计"]
        lines.append(f"## 统计总览\n")
        lines.append(f"| 级别 | 数量 |")
        lines.append(f"|---|---|")
        lines.append(f"| 🔴 致命 | {stats['致命']} |")
        lines.append(f"| 🟡 严重 | {stats['严重']} |")
        lines.append(f"| 🟠 警告 | {stats['警告']} |")
        lines.append(f"| **总计** | **{stats['total_hits']}** |")
        lines.append("")
        
        # 类型分布
        lines.append("## 毒点类型分布\n")
        lines.append("| 类型 | 出现次数 |")
        lines.append("|---|---|")
        for ptype, count in full_report["毒点类型分布"].items():
            if count > 0:
                lines.append(f"| {ptype} | {count} |")
        lines.append("")
        
        # 致命毒点详情
        fatal_vols = full_report["总览"]["致命毒点卷"]
        if fatal_vols:
            lines.append("## 🔴 致命毒点详情\n")
            for vol_key in fatal_vols:
                vol_data = full_report["逐卷报告"][vol_key]
                lines.append(f"### {vol_key}\n")
                for hit in vol_data["hits"]:
                    if hit["severity"] == "致命":
                        lines.append(f"- **[{hit['type']}]** 关键词: `{hit['keyword']}`")
                        lines.append(f"  - 上下文: _{hit['context']}_")
                        lines.append(f"  - 💡 {hit['suggestion']}")
                        lines.append("")
        
        # 严重毒点
        serious_vols = full_report["总览"]["严重毒点卷"]
        if serious_vols:
            lines.append("## 🟡 严重毒点详情\n")
            for vol_key in serious_vols:
                vol_data = full_report["逐卷报告"][vol_key]
                lines.append(f"### {vol_key}\n")
                for hit in vol_data["hits"]:
                    if hit["severity"] == "严重":
                        lines.append(f"- **[{hit['type']}]** `{hit['keyword']}` → {hit['location']}")
                lines.append("")
        
        # 清洁卷
        clean_count = len(full_report["总览"]["清洁卷"])
        lines.append(f"\n## ✅ 清洁卷: {clean_count}/{full_report['总览']['总卷数']} 卷无毒点\n")
        
        return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="毒点检测器")
    parser.add_argument("--story", type=str, default="万族之劫_仿写", help="小说名称")
    parser.add_argument("--bible", type=str, default="story_bible_agent.json", help="Bible 文件名")
    parser.add_argument("--output", type=str, default=None, help="输出报告路径")
    
    args = parser.parse_args()
    
    storage = Config.get_storage_manager(args.story)
    bible = storage.load_story_bible(args.bible)
    
    if not bible:
        print("错误: 无法加载 Story Bible")
        sys.exit(1)
    
    detector = PoisonDetector()
    report = detector.scan_all_volumes(bible)
    md = detector.generate_report_markdown(report)
    
    # 输出
    if args.output:
        from pathlib import Path
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"报告已保存到 {args.output}")
    else:
        print(md)
