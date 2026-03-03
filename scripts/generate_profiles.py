"""
Character Profile Generator (人物小传生成器) v2
从 Story Bible 中提取角色数据，为每个有名有姓的角色生成丰富的 Markdown 小传文件。

设计原则：
- 严禁泛指角色（江湖豪杰、皇亲、高官等）
- 每个角色必须有明确的名称与身份
- 小传内容必须包含：生平、性格、关系网、与主角交集、弧光、高光、剧情推动
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from mechanisms.continuity_tracker import ContinuityTracker


# ============================================================
# 泛指角色黑名单 (严禁生成小传)
# ============================================================
GENERIC_NAME_BLACKLIST = {
    # ===== 完全泛指（非人物名称）=====
    "万民", "众弟子", "新一代医者", "全体主要配角",
    "江湖豪杰", "高官", "皇亲", "世家代表", "世家御医代表",
    "豪商代表", "地方官", "朝廷钦差",
    "陆清源铜像", "陆清源（遗体）",
    "陆家全族", "陆家子弟", "陆家曾孙", "贫苦儿童",
    "老太监", "年轻学子", "年轻皇帝",
    # ===== 集体名词 =====
    "全九州军民", "九州军民", "千万学子", "全宇宙众生",
    "大乾众人", "大乾残余高层", "大乾军民", "拾荒海盗团",
    "保皇党诸侯", "南方诸侯", "中原世家余孽",
    "远古剑魂群", "怨魂军队", "皇家近卫队",
    "帝国皇家近卫队", "湮灭骑士团",
    # ===== 无名头衔（没有具体人名）=====
    "敌方水师提督", "帝国巡逻舰队舰长", "帝国大将",
    "帝国歼星指挥官", "帝国歼星群督军",
    "帝国第一先锋大将", "帝国远征军总帅",
    "古神大联盟统帅", "枢纽守备官", "巡游清道夫",
    "神族先锋官", "裁决神将", "智神将",
    "大雍守将张狂",  # 这是无名头衔+形容，非人名
    # ===== 非人物实体 =====
    "最高统帅AI", "天道核心枢纽", "行星战堡", "行星级AI实体",
    "终极机甲", "终极AI", "废土沙虫", "利维坦巨兽",
    "格式化主机AI", "清道夫机甲",
    # ===== 幻境/投影/残像 =====
    "幻境姜小蛮", "幻境父母", "上古帝魂残像",
    "帝魂残像", "远古神皇",
    # ===== 科幻角色（架空古代不应出现）=====
    "亚瑟", "空冥", "银铠", "红发巴克",
    "半机械先驱者", "机械狂人",
    "最后守门人",
    # ===== 其他泛指 =====
    "彩蛋人物", "复苏的古妖祖", "南方古妖池",
    "帝国皇帝", "老船长",
}

# 无意义注释黑名单（选identity时跳过这些）
BAD_ANNOTATIONS = {
    "遗体", "反派", "配角", "龙套", "路人", "幕后",
    "初为反派后转正", "感恩戴德",
    "傲慢的贵族", "只闻其声的终极大反派虚影",
    "录像片段", "只是主机前的一个傀儡音响",
    "使用高维兵器的冷酷将领",
    "驾驶机甲的异界骑士", "玩弄空间的异灵",
    "虚拟形象为一个小女孩",
}

# 用于检测泛指模式的正则
GENERIC_PATTERNS = [
    r"^.{0,1}(代表)$",  # 仅"代表"无名字
    r"^(某|某个|一个|一位)",
    r"^.+铜像$",
    r"^.+（遗体）$",
    # ===== 集体/泛指前缀 =====
    r"^(全|众|千万|大乾|帝国|敌方|远古).*(军民|学子|众生|高层|追兵|残余|近卫|骑士团)$",
    # ===== 无名头衔模式 =====
    r"^(帝国|敌方|神族|皇家).*(将|帅|官|督|长|队)$",
    # ===== 非人物实体关键词 =====
    r"(AI|机甲|战堡|枢纽|残像|投影|沙虫|巨兽|主机|清道夫)",
    # ===== 幻境前缀 =====
    r"^幻境",
    # ===== 隐姓埋名的描述性角色 =====
    r"^(彩蛋|复苏的|南方古)",
]


@dataclass
class CharacterProfile:
    """完整角色档案"""
    name: str
    aliases: List[str] = field(default_factory=list)
    identity: str = ""
    faction: str = ""           # 阵营/组织
    family_info: str = ""       # 家族/血缘信息
    status: str = "存活"
    first_vol: int = 0
    last_vol: int = 0
    total_appearances: int = 0
    volumes_appeared: List[int] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    bio_summary: str = ""       # 生平概述
    arc_events: List[Dict] = field(default_factory=list)
    highlight_moments: List[str] = field(default_factory=list)  # 高光时刻
    relationships: List[Dict] = field(default_factory=list)
    protagonist_intersections: List[str] = field(default_factory=list)  # 与主角交集
    plot_contributions: List[str] = field(default_factory=list)
    foreshadowing: List[str] = field(default_factory=list)
    is_core: bool = False
    role_type: str = ""          # 正派/反派/中立/亦正亦邪


def is_generic_name(name: str) -> bool:
    """检查是否为泛指角色名"""
    if name in GENERIC_NAME_BLACKLIST:
        return True
    for pattern in GENERIC_PATTERNS:
        if re.match(pattern, name):
            return True
    # 同时检查 Config 中的统一禁止模式
    for pattern in Config.FORBIDDEN_CHARACTER_PATTERNS:
        if re.search(pattern, name):
            return True
    # 检查纯头衔（无姓名）
    pure_titles = {"皇帝", "皇后", "太后", "太子", "公主", "新皇", "幼帝", "宰相"}
    # 这些保留，因为在故事中是具体角色
    if name in pure_titles:
        return False
    return False


class ProfileGenerator:
    """人物小传生成器 v2"""
    
    PROTAGONIST_NAME = "陆清源"
    PROTAGONIST_IDENTITY = "底层出身的医者，凭借医术与智谋在乱世中崛起，终成一代大医"
    
    def __init__(self):
        self.tracker = ContinuityTracker()
        self.profiles: Dict[str, CharacterProfile] = {}
        self.raw_name_map: Dict[str, str] = {}
        self.vol_data_cache: Dict[int, Dict] = {}
    
    def _parse_name_and_annotation(self, raw_name: str) -> Tuple[str, str]:
        """解析名称和注释"""
        raw_name = raw_name.strip()
        annotation = ""
        name = raw_name
        for opener, closer in [("（", "）"), ("(", ")")]:
            if opener in raw_name:
                idx = raw_name.index(opener)
                name = raw_name[:idx].strip()
                end_idx = raw_name.index(closer) if closer in raw_name else len(raw_name)
                annotation = raw_name[idx+1:end_idx].strip()
                break
        return name, annotation
    
    def _infer_personality(self, name: str, annotations: List[str], events: List[Dict], identity: str) -> List[str]:
        """从注释和事件中推断性格特征"""
        traits = []
        all_text = " ".join(annotations) + " " + identity + " " + " ".join(e.get("event", "") for e in events)
        
        trait_keywords = {
            "隐忍": ["隐忍", "忍辱", "韬光养晦", "不动声色"],
            "智谋过人": ["毒计", "谋略", "计策", "设计", "运筹"],
            "忠义": ["忠诚", "死战", "护主", "效忠", "誓死"],
            "冷血果断": ["冷血", "果断", "冷酷", "无情", "斩杀", "屠"],
            "骁勇善战": ["血战", "猛将", "悍勇", "勇猛", "先登"],
            "阴险狡诈": ["阴险", "狡诈", "背刺", "陷害", "算计"],
            "医术精湛": ["医术", "诊脉", "针灸", "开方", "治病"],
            "恃才傲物": ["傲慢", "不屑", "目中无人"],
            "心狠手辣": ["心狠", "残暴", "暴虐", "酷吏"],
            "聪慧坚韧": ["聪慧", "坚韧", "聪明", "机敏"],
            "野心勃勃": ["野心", "觊觎", "篡权", "夺嫡"],
            "贤德淑良": ["贤德", "温婉", "善良", "仁慈"],
            "城府深沉": ["城府", "深沉", "不动声色", "深藏不露"],
        }
        
        for trait, keywords in trait_keywords.items():
            for kw in keywords:
                if kw in all_text:
                    traits.append(trait)
                    break
        
        return traits[:5] if traits else ["待深化"]
    
    def _infer_role_type(self, annotations: List[str], identity: str, name: str = "") -> str:
        """推断角色阵营类型"""
        # 主角特殊处理
        if name == self.PROTAGONIST_NAME:
            return "正派主角"
        text = " ".join(annotations) + " " + identity
        if any(kw in text for kw in ["反派", "BOSS", "奸", "恶", "酷吏", "野心家", "叛"]):
            return "反派"
        elif any(kw in text for kw in ["亦师亦友", "亦正亦邪", "中立"]):
            return "亦正亦邪"
        elif any(kw in text for kw in ["盟友", "师傅", "弟子", "忠诚", "好友", "校尉", "将军", "大夫"]):
            return "正派"
        return "中立"
    
    def _infer_faction(self, annotations: List[str], identity: str, events: List[Dict]) -> str:
        """推断所属组织"""
        text = " ".join(annotations) + " " + identity + " " + " ".join(e.get("event", "") for e in events)
        
        factions = {
            "太医院": ["太医", "太医院"],
            "皇室宗族": ["皇帝", "太子", "皇后", "太后", "公主", "皇孙", "宗室", "亲王"],
            "朝廷中枢": ["尚书", "侍郎", "丞相", "宰相", "钦差"],
            "边军": ["边军", "校尉", "戍边", "边关", "将军"],
            "江湖": ["江湖", "武林", "侠客", "门派"],
            "北燕": ["北燕", "燕国"],
            "南疆": ["南疆", "土司", "蛊"],
            "医学院": ["医学院", "学生", "学徒"],
            "内务府/宦官": ["公公", "太监", "内务府", "内相"],
            "药王谷": ["药王谷"],
            "卫生部": ["卫生部"],
            "世家门阀": ["世家", "门阀", "世族"],
            "西域": ["西域", "楼兰"],
            "东瀛": ["倭寇", "东瀛"],
            "泰西/西洋": ["泰西", "传教士", "西洋", "利玛窦"],
        }
        
        for faction, keywords in factions.items():
            for kw in keywords:
                if kw in text:
                    return faction
        return "独立"
    
    def _infer_relationship_type(self, name1: str, name2: str, summary: str, conflict: str, events: list) -> str:
        """Fix #16: 从剧情文本推断质性关系"""
        all_text = f"{summary} {conflict} {' '.join(str(e) for e in events)}"
        
        # 检查两个角色是否在同一句中以特定关系出现
        rel_patterns = {
            "师徒": ["拜师", "师傅", "师父", "传授", "教导", "指点"],
            "父子/家族": ["之子", "之父", "之女", "父亲", "母亲", "血脉", "家族", "兄弟", "姐妹"],
            "死敌": ["杀", "仇", "敌", "对决", "斩杀", "追杀", "屠"],
            "盟友": ["联盟", "结盟", "并肩", "共同", "合作", "携手"],
            "上下级": ["麾下", "效忠", "部下", "属下", "统领"],
            "情感": ["情意", "倾心", "相恋", "暗恋", "夫妻"],
            "对手": ["对峙", "较量", "博弈", "交锋", "角力"],
        }
        
        for rel_type, keywords in rel_patterns.items():
            for kw in keywords:
                # 检查关键词是否与两个角色名出现在相近位置
                if kw in all_text:
                    # 在关键词前后 80 字符范围内搜索两个名字
                    for idx in range(len(all_text)):
                        pos = all_text.find(kw, idx)
                        if pos == -1:
                            break
                        window = all_text[max(0, pos-80):pos+80]
                        if name1 in window and name2 in window:
                            return rel_type
                        idx = pos + 1
        
        return "同卷角色"
    
    def _build_bio_summary(self, profile: CharacterProfile) -> str:
        """构建生平概述"""
        parts = []
        
        if profile.identity:
            parts.append(f"{profile.name}，{profile.identity}。")
        else:
            parts.append(f"{profile.name}。")
        
        if profile.faction and profile.faction != "独立":
            parts.append(f"隶属于{profile.faction}。")
        
        if profile.first_vol:
            parts.append(f"初登场于第{profile.first_vol}卷")
            if profile.last_vol > profile.first_vol:
                parts.append(f"，故事跨度至第{profile.last_vol}卷（共出场{profile.total_appearances}卷）。")
            else:
                parts.append(f"。")
        
        # 从弧光事件中提炼关键转折
        if len(profile.arc_events) >= 2:
            first_event = profile.arc_events[0].get("event", "")[:60]
            last_event = profile.arc_events[-1].get("event", "")[:60]
            parts.append(f"\n\n初始剧情：{first_event}......")
            parts.append(f"\n最终走向：{last_event}......")
        
        return "".join(parts)
    
    def extract_all_characters(self, bible) -> Dict[str, CharacterProfile]:
        """从 Story Bible 中提取所有角色"""
        self.profiles = {}
        self.tracker.build_presence_matrix(bible)
        foreshadow = self.tracker.build_foreshadowing_network(bible)
        
        sorted_vols = sorted(bible.volume_plans.items(), key=lambda x: int(x[0]))
        
        # 第一遍：收集所有角色基础数据
        for vol_num_key, plan in sorted_vols:
            vol_num = int(vol_num_key)
            
            key_chars = plan.key_characters if hasattr(plan, 'key_characters') else plan.get('key_characters', [])
            new_chars = plan.new_characters if hasattr(plan, 'new_characters') else plan.get('new_characters', [])
            summary = plan.summary if hasattr(plan, 'summary') else plan.get('summary', '')
            title = plan.title if hasattr(plan, 'title') else plan.get('title', '')
            conflict = plan.main_conflict if hasattr(plan, 'main_conflict') else plan.get('main_conflict', '')
            growth = plan.protagonist_growth if hasattr(plan, 'protagonist_growth') else plan.get('protagonist_growth', '')
            key_events = plan.key_events if hasattr(plan, 'key_events') else plan.get('key_events', [])
            loops_plant = plan.loops_to_plant if hasattr(plan, 'loops_to_plant') else plan.get('loops_to_plant', [])
            loops_resolve = plan.loops_to_resolve if hasattr(plan, 'loops_to_resolve') else plan.get('loops_to_resolve', [])
            
            # 缓存卷数据
            self.vol_data_cache[vol_num] = {
                "title": title, "summary": summary, "conflict": conflict,
                "growth": growth, "events": key_events,
            }
            
            all_raw = list(key_chars) + list(new_chars)
            
            for raw_name in all_raw:
                name, annotation = self._parse_name_and_annotation(raw_name)
                if not name or is_generic_name(name):
                    continue
                
                self.raw_name_map[raw_name] = name
                
                if name not in self.profiles:
                    self.profiles[name] = CharacterProfile(name=name)
                
                p = self.profiles[name]
                
                if annotation and annotation not in p.aliases:
                    p.aliases.append(annotation)
                # 选取最有意义的身份描述（跳过无意义注释）
                if annotation and annotation not in BAD_ANNOTATIONS:
                    if len(annotation) > len(p.identity) or p.identity in BAD_ANNOTATIONS:
                        p.identity = annotation
                
                if vol_num not in p.volumes_appeared:
                    p.volumes_appeared.append(vol_num)
                if p.first_vol == 0:
                    p.first_vol = vol_num
                p.last_vol = max(p.last_vol, vol_num)
                
                # 弧光事件
                for event in key_events:
                    if name in event:
                        p.arc_events.append({
                            "vol": vol_num,
                            "event": event,
                            "context": f"第{vol_num}卷《{title}》"
                        })
                
                # 高光时刻：从 summary 中提取
                if name in summary:
                    # 提取包含该角色名的句子
                    sentences = re.split(r'[。！？；]', summary)
                    for s in sentences:
                        if name in s and len(s.strip()) > 10:
                            highlight = f"第{vol_num}卷《{title}》: {s.strip()}"
                            if highlight not in p.highlight_moments:
                                p.highlight_moments.append(highlight)
                
                # 与主角交集
                if name != self.PROTAGONIST_NAME and self.PROTAGONIST_NAME in summary and name in summary:
                    intersection = f"第{vol_num}卷《{title}》: {conflict}"
                    if intersection not in p.protagonist_intersections:
                        p.protagonist_intersections.append(intersection)
                
                # 剧情推动
                if name in conflict:
                    p.plot_contributions.append(f"第{vol_num}卷核心冲突: {conflict}")
            
            # 角色共现关系（仅有名角色）
            valid_names = [self._parse_name_and_annotation(r)[0] for r in all_raw 
                           if not is_generic_name(self._parse_name_and_annotation(r)[0])]
            valid_names = [n for n in valid_names if n]
            
            for i in range(len(valid_names)):
                for j in range(i+1, len(valid_names)):
                    n1, n2 = valid_names[i], valid_names[j]
                    if n1 in self.profiles and n2 in self.profiles:
                        # Fix #16: 推断质性关系类型
                        rel_type = self._infer_relationship_type(
                            n1, n2, summary, conflict, key_events
                        )
                        existing = [r for r in self.profiles[n1].relationships if r["target"] == n2]
                        if not existing:
                            self.profiles[n1].relationships.append({
                                "target": n2, "共现卷": [vol_num], "type": rel_type
                            })
                            self.profiles[n2].relationships.append({
                                "target": n1, "共现卷": [vol_num], "type": rel_type
                            })
                        else:
                            if vol_num not in existing[0]["共现卷"]:
                                existing[0]["共现卷"].append(vol_num)
                                # 更新关系类型（如果推断出更精确的）
                                if rel_type != "同卷角色" and existing[0]["type"] == "同卷角色":
                                    existing[0]["type"] = rel_type
                                for r in self.profiles[n2].relationships:
                                    if r["target"] == n1 and vol_num not in r["共现卷"]:
                                        r["共现卷"].append(vol_num)
                                        if rel_type != "同卷角色" and r["type"] == "同卷角色":
                                            r["type"] = rel_type
        
        # 第二遍：关联伏笔 & 推断性格/阵营/生平
        for name, loops in foreshadow["characters_involved"].items():
            if name in self.profiles:
                self.profiles[name].foreshadowing = loops
        
        for name, p in self.profiles.items():
            p.volumes_appeared = sorted(set(p.volumes_appeared))
            p.total_appearances = len(p.volumes_appeared)
            p.is_core = p.total_appearances >= ContinuityTracker.CORE_THRESHOLD
            
            # 清理无意义 aliases
            p.aliases = [a for a in p.aliases if a not in BAD_ANNOTATIONS]
            
            # 主角特殊处理
            if name == self.PROTAGONIST_NAME:
                if not p.identity or p.identity in BAD_ANNOTATIONS:
                    p.identity = self.PROTAGONIST_IDENTITY
            
            # 推断性格
            p.personality_traits = self._infer_personality(name, p.aliases, p.arc_events, p.identity)
            # 推断阵营
            p.role_type = self._infer_role_type(p.aliases, p.identity, name)
            p.faction = self._infer_faction(p.aliases, p.identity, p.arc_events)
            # 构建生平
            p.bio_summary = self._build_bio_summary(p)
            
            # 去重
            seen = set()
            unique = []
            for e in p.arc_events:
                key = e["event"]
                if key not in seen:
                    seen.add(key)
                    unique.append(e)
            p.arc_events = unique
            p.plot_contributions = list(dict.fromkeys(p.plot_contributions))
            p.highlight_moments = list(dict.fromkeys(p.highlight_moments))
            p.protagonist_intersections = list(dict.fromkeys(p.protagonist_intersections))
        
        return self.profiles
    
    def generate_profile_md(self, profile: CharacterProfile) -> str:
        """为单个角色生成丰富的 Markdown 小传"""
        lines = []
        
        # ===== 标题 =====
        emoji = "🌟" if profile.is_core else "⭐"
        role_badge = {"反派": "🔴", "正派": "🟢", "亦正亦邪": "🟠"}.get(profile.role_type, "⚪")
        lines.append(f"# {emoji} {profile.name} — 人物小传\n")
        
        # ===== 基本信息 =====
        lines.append("## 📋 基本信息\n")
        lines.append("| 项目 | 内容 |")
        lines.append("|---|---|")
        lines.append(f"| **姓名** | {profile.name} |")
        if profile.identity:
            lines.append(f"| **身份** | {profile.identity} |")
        if profile.aliases:
            lines.append(f"| **别称/特征** | {', '.join(set(profile.aliases))} |")
        lines.append(f"| **阵营** | {role_badge} {profile.role_type} |")
        if profile.faction != "独立":
            lines.append(f"| **所属组织** | {profile.faction} |")
        if profile.personality_traits:
            lines.append(f"| **性格特征** | {', '.join(profile.personality_traits)} |")
        lines.append(f"| **首次登场** | 第{profile.first_vol}卷 |")
        lines.append(f"| **末次登场** | 第{profile.last_vol}卷 |")
        lines.append(f"| **出场卷数** | {profile.total_appearances}卷 |")
        lines.append(f"| **重要程度** | {'🌟 核心角色' if profile.is_core else '⭐ 重要配角' if profile.total_appearances >= 4 else '📌 一般角色'} |")
        lines.append("")
        
        # ===== 生平概述 =====
        lines.append("## 📖 生平概述\n")
        lines.append(f"{profile.bio_summary}\n")
        
        # ===== 出场轨迹 =====
        lines.append("## 📍 出场轨迹\n")
        vol_parts = []
        for v in profile.volumes_appeared:
            vol_info = self.vol_data_cache.get(v, {})
            vol_title = vol_info.get("title", "")
            vol_parts.append(f"第{v}卷《{vol_title}》" if vol_title else f"第{v}卷")
        lines.append(" → ".join(vol_parts))
        lines.append("")
        
        # ===== 与主角的交集 =====
        if profile.name != self.PROTAGONIST_NAME:
            lines.append(f"## 🤝 与{self.PROTAGONIST_NAME}的交集\n")
            if profile.protagonist_intersections:
                for inter in profile.protagonist_intersections[:10]:
                    lines.append(f"- {inter}")
            else:
                # 从关系网中找主角
                protagonist_rels = [r for r in profile.relationships if r["target"] == self.PROTAGONIST_NAME]
                if protagonist_rels:
                    vols = sorted(set(protagonist_rels[0].get("共现卷", [])))
                    lines.append(f"- 共同出场 {len(vols)} 卷: {', '.join(f'第{v}卷' for v in vols[:10])}")
                else:
                    lines.append("- 暂无直接交集记录")
            lines.append("")
        
        # ===== 人物弧光 =====
        if profile.arc_events:
            lines.append("## 📈 人物弧光 (Character Arc)\n")
            lines.append("| 卷号 | 所在卷名 | 关键事件 |")
            lines.append("|---|---|---|")
            for event in profile.arc_events[:25]:
                event_text = event["event"]
                if len(event_text) > 70:
                    event_text = event_text[:67] + "..."
                vol_info = self.vol_data_cache.get(event["vol"], {})
                vol_title = vol_info.get("title", "")
                lines.append(f"| 第{event['vol']}卷 | {vol_title} | {event_text} |")
            lines.append("")
        
        # ===== 人物高光 =====
        if profile.highlight_moments:
            lines.append("## ✨ 高光时刻\n")
            for hl in profile.highlight_moments[:10]:
                lines.append(f"- {hl}")
            lines.append("")
        
        # ===== 人物关系网 =====
        if profile.relationships:
            lines.append("## 🕸️ 人物关系网\n")
            sorted_rels = sorted(profile.relationships, key=lambda r: len(r.get("共现卷", [])), reverse=True)
            lines.append("| 关联角色 | 关系深度 | 共现卷号 |")
            lines.append("|---|---|---|")
            for rel in sorted_rels[:15]:
                vols = sorted(set(rel.get("共现卷", [])))
                depth = len(vols)
                depth_bar = "█" * min(depth, 10) + "░" * max(0, 10 - depth)
                vol_str = ", ".join(str(v) for v in vols[:10])
                if len(vols) > 10:
                    vol_str += f"... (共{len(vols)}卷)"
                lines.append(f"| {rel['target']} | {depth_bar} {depth}卷 | {vol_str} |")
            lines.append("")
        
        # ===== 剧情推动作用 =====
        if profile.plot_contributions:
            lines.append("## 🎯 对剧情的推动\n")
            for contrib in profile.plot_contributions[:10]:
                lines.append(f"- {contrib}")
            lines.append("")
        
        # ===== 伏笔关联 =====
        if profile.foreshadowing:
            lines.append("## 🧵 伏笔关联 (草蛇灰线)\n")
            for loop in profile.foreshadowing:
                lines.append(f"- 🎯 {loop}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_all_profiles(self, bible, output_dir: str) -> List[str]:
        """为所有有名角色生成小传文件"""
        self.extract_all_characters(bible)
        
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        sorted_profiles = sorted(
            self.profiles.values(),
            key=lambda p: p.total_appearances,
            reverse=True
        )
        
        for profile in sorted_profiles:
            md_content = self.generate_profile_md(profile)
            safe_name = re.sub(r'[\\/*?:"<>|]', "", profile.name)
            filename = f"{safe_name}_人物小传.md"
            filepath = out_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            generated_files.append(str(filepath))
        
        return generated_files
    
    def generate_index(self, bible, output_dir: str) -> str:
        """生成总索引"""
        if not self.profiles:
            self.extract_all_characters(bible)
        
        lines = []
        lines.append(f"# {bible.story_title} — 人物小传总索引\n")
        lines.append(f"**总角色数**: {len(self.profiles)}\n")
        
        core = [p for p in self.profiles.values() if p.is_core]
        supporting = [p for p in self.profiles.values()
                      if ContinuityTracker.SUPPORTING_THRESHOLD <= p.total_appearances < ContinuityTracker.CORE_THRESHOLD]
        minor = [p for p in self.profiles.values()
                 if p.total_appearances < ContinuityTracker.SUPPORTING_THRESHOLD]
        
        for label, emoji, chars in [
            ("核心角色", "🌟", core),
            ("重要配角", "⭐", supporting),
            ("一般角色", "📌", minor),
        ]:
            lines.append(f"## {emoji} {label} ({len(chars)}人)\n")
            lines.append("| 角色 | 身份 | 阵营 | 出场 | 跨度 |")
            lines.append("|---|---|---|---|---|")
            for p in sorted(chars, key=lambda x: -x.total_appearances):
                safe_name = re.sub(r'[\\/*?:"<>|]', "", p.name)
                role_badge = {"反派": "🔴", "正派": "🟢", "亦正亦邪": "🟠"}.get(p.role_type, "⚪")
                lines.append(f"| [{p.name}]({safe_name}_人物小传.md) | {p.identity} | {role_badge} {p.role_type} | {p.total_appearances}卷 | 第{p.first_vol}~{p.last_vol}卷 |")
            lines.append("")
        
        index_path = Path(output_dir) / "人物小传_总索引.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        return str(index_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="人物小传生成器 v2")
    parser.add_argument("--story", type=str, default="万族之劫_仿写", help="小说名称")
    parser.add_argument("--bible", type=str, default="story_bible_agent.json", help="Bible 文件名")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录")
    
    args = parser.parse_args()
    
    storage = Config.get_storage_manager(args.story)
    bible = storage.load_story_bible(args.bible)
    
    if not bible:
        print("错误: 无法加载 Story Bible")
        sys.exit(1)
    
    generator = ProfileGenerator()
    output_dir = args.output_dir or str(Config.STORAGE_DIR / args.story / f"{args.story}_人物小传")
    
    files = generator.generate_all_profiles(bible, output_dir)
    index = generator.generate_index(bible, output_dir)
    
    print(f"\n{'='*60}")
    print(f"✅ 人物小传生成完毕!")
    print(f"   生成角色数: {len(files)}")
    print(f"   输出目录: {output_dir}")
    print(f"   索引文件: {index}")
    print(f"{'='*60}")
