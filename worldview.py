"""
世界观引擎 (Worldview Engine)
==============================
标签组合式世界观系统。每个标签携带自己的允许/禁止元素包，
标签自由组合即可覆盖任意题材（都市修仙、诡异修仙、穿越造科技等）。

核心原理：白名单优先。
- 多个标签的 allowed_elements 取并集 → 最终允许集
- 多个标签的 forbidden_elements 取并集 → 基础禁止集
- 最终禁止集 = 基础禁止集 - 最终允许集（白名单覆盖黑名单）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
import json
from pathlib import Path


# ==========================================================================
# 1. 数据模型
# ==========================================================================

@dataclass
class WorldviewTag:
    """单个维度标签"""
    name: str                                    # 标签名，如 "修仙", "现代"
    dimension: str                               # 所属维度: 时代/力量/社会/特殊
    description: str = ""                        # 一句话描述
    
    allowed_elements: List[str] = field(default_factory=list)    # 允许元素
    forbidden_elements: List[str] = field(default_factory=list)  # 禁止元素
    writing_guidance: str = ""                   # 写作风格指导片段
    keywords: List[str] = field(default_factory=list)            # 常用关键词


# ==========================================================================
# 2. 标签注册表（按维度组织）
# ==========================================================================

DIMENSION_TAGS: Dict[str, Dict[str, WorldviewTag]] = {}


def _register_all_tags():
    """注册所有预定义标签"""
    global DIMENSION_TAGS

    tags = [
        # ============================
        # 时代维度
        # ============================
        WorldviewTag(
            name="远古",
            dimension="时代",
            description="上古蛮荒时代，部落文明",
            allowed_elements=["部落", "图腾", "祭司", "蛮荒", "猛兽", "石器", "篝火", "巫术", "狩猎", "洪荒"],
            forbidden_elements=["手机", "电脑", "汽车", "飞机", "枪炮", "电力", "网络", "朝堂", "科举",
                                "火箭", "导弹", "坦克", "炸弹", "地雷", "机枪", "步枪", "手枪"],
            writing_guidance="原始粗犷的叙事风格，强调生存本能和部落信仰。"
        ),
        WorldviewTag(
            name="古代",
            dimension="时代",
            description="封建王朝时代，冷兵器文明",
            allowed_elements=["朝堂", "后宫", "世家", "江湖", "冷兵器", "弓弩", "马匹", "轿子", "府邸",
                              "科举", "丝绸", "瓷器", "中医", "针灸", "草药", "城墙", "护城河",
                              "暗器", "毒", "镖局", "客栈", "茶楼", "酒肆", "集市", "商帮",
                              "皇帝", "王爷", "将军", "丞相", "太监", "宫女", "丫鬟"],
            forbidden_elements=["手机", "电脑", "汽车", "飞机", "枪炮", "电力", "网络", "电报", "电话",
                                "火箭", "导弹", "坦克", "炸弹", "地雷", "机枪", "步枪", "手枪",
                                "蒸汽机", "内燃机", "大炮", "工业革命",
                                "星舰", "飞船", "机甲", "激光", "AI", "机器人", "克隆", "纳米",
                                "赛博", "虚拟现实", "全息", "芯片", "防火墙", "数据", "服务器", "代码",
                                "太空", "外星人", "银河系", "星际", "黑洞", "量子",
                                "基因", "DNA", "辐射"],
            writing_guidance="古风文言与白话结合，注重礼仪规矩描写，人物称谓使用古代敬语。"
        ),
        WorldviewTag(
            name="近代",
            dimension="时代",
            description="工业革命到20世纪初",
            allowed_elements=["蒸汽机", "火车", "电报", "洋枪", "洋炮", "租界", "报纸",
                              "工厂", "轮船", "煤矿", "钢铁", "火药", "炸弹"],
            forbidden_elements=["手机", "电脑", "网络", "AI", "机甲", "飞船", "星际",
                                "修仙", "灵气", "飞剑"],
            writing_guidance="融合新旧交替的时代感，中西碰撞的文化冲突。"
        ),
        WorldviewTag(
            name="现代",
            dimension="时代",
            description="当代都市社会",
            allowed_elements=["手机", "电脑", "汽车", "网络", "公司", "学校", "医院", "警察",
                              "高铁", "飞机", "社交媒体", "外卖", "公寓", "写字楼", "地铁",
                              "电力", "电话", "电报", "GPS", "监控"],
            forbidden_elements=["朝堂", "科举", "太监", "宫女", "轿子",
                                "星舰", "跃迁", "光年", "义体改造"],
            writing_guidance="现代都市语言风格，注重社会关系和职场描写。"
        ),
        WorldviewTag(
            name="未来",
            dimension="时代",
            description="科幻未来世界",
            allowed_elements=["AI", "机器人", "飞船", "太空", "星际", "义体", "虚拟现实",
                              "全息", "芯片", "纳米", "量子", "基因编辑", "克隆",
                              "空间站", "外星", "光年", "跃迁", "赛博空间",
                              "黑客", "防火墙", "数据", "服务器", "网络"],
            forbidden_elements=["朝堂", "科举", "马匹", "轿子", "弓弩"],
            writing_guidance="科幻术语与未来感设定，探讨科技与人性的关系。"
        ),

        # ============================
        # 力量维度
        # ============================
        WorldviewTag(
            name="无超能力",
            dimension="力量",
            description="纯写实，无任何超自然力量",
            allowed_elements=["谋略", "权术", "人心", "政治", "军事", "经商"],
            forbidden_elements=["修仙", "灵气", "飞剑", "法术", "魔法", "异能", "超能力",
                                "修炼", "内力", "真气", "武功", "轻功",
                                "斗气", "魔兽", "结界", "封印", "阵法"],
            writing_guidance="纯写实风格，所有冲突通过人物智谋、政治博弈和军事对抗推动。"
        ),
        WorldviewTag(
            name="武功低武",
            dimension="力量",
            description="低武世界，武功存在但不超越物理极限",
            allowed_elements=["武功", "内力", "轻功", "暗器", "点穴", "拳法", "剑法", "刀法",
                              "江湖", "门派", "掌门", "侠客", "镖局"],
            forbidden_elements=["修仙", "灵气", "飞剑", "法术", "阵法", "符文", "丹药",
                                "飞升", "渡劫", "金丹", "元婴", "化神",
                                "魔法", "斗气", "魔兽", "结界", "封印", "虚空",
                                "修炼", "丹田", "元气", "法宝", "铭文", "力场",
                                "血脉觉醒", "召唤", "魔力", "魔王",
                                "异能", "超能力", "念力", "心灵感应",
                                "母体", "母巢", "病毒", "感染", "寄生", "共生", "宿主",
                                "触手", "进化", "意识体", "傀儡", "机关兽", "齿轮"],
            writing_guidance="武功以巧妙招式和内力运用为主，不可出现毁天灭地的超自然战力。"
        ),
        WorldviewTag(
            name="武功高武",
            dimension="力量",
            description="高武世界，武功可破山裂海",
            allowed_elements=["武功", "内力", "真气", "轻功", "气劲", "罡气", "剑气",
                              "武道宗师", "武圣", "破碎虚空", "先天境界",
                              "江湖", "门派", "武林盟主"],
            forbidden_elements=["修仙", "灵气", "飞剑", "法术", "阵法", "丹药",
                                "魔法", "斗气", "魔兽",
                                "母体", "病毒", "感染", "寄生"],
            writing_guidance="武功战力可以很强但需要层次分明，有明确天花板。"
        ),
        WorldviewTag(
            name="修仙",
            dimension="力量",
            description="仙侠修炼体系",
            allowed_elements=["修炼", "灵气", "飞剑", "法术", "阵法", "丹药", "法宝", "符文",
                              "丹田", "元气", "飞升", "渡劫", "金丹", "元婴", "化神",
                              "宗门", "修仙者", "灵石", "灵脉", "天劫", "道心",
                              "封印", "结界", "虚空", "须弥", "铭文",
                              "内丹", "外丹", "御剑飞行", "传音", "神识"],
            forbidden_elements=["手机", "电脑", "汽车", "枪炮", "电力", "网络",
                                "赛博", "AI", "机器人", "星舰", "太空"],
            writing_guidance="融入道家哲学，注重境界突破描写，战斗以法术对决为主。"
        ),
        WorldviewTag(
            name="魔法",
            dimension="力量",
            description="西方奇幻魔法体系",
            allowed_elements=["魔法", "法杖", "咒语", "魔力", "精灵", "矮人", "兽人", "巨龙",
                              "魔法学院", "骑士", "圣骑士", "牧师", "游侠", "刺客",
                              "魔法阵", "召唤", "附魔", "魔药", "地下城", "副本",
                              "冒险者公会", "魔王", "勇者"],
            forbidden_elements=["修仙", "灵气", "飞剑", "丹药", "宗门", "手机", "电脑"],
            writing_guidance="西方奇幻设定，职业体系和冒险探索。"
        ),
        WorldviewTag(
            name="科技",
            dimension="力量",
            description="科技为核心力量来源",
            allowed_elements=["科技", "发明", "实验", "工程", "机械", "电力", "化学",
                              "物理", "数学", "医学", "生物学", "天文", "地质",
                              "火药", "蒸汽", "电", "引擎", "齿轮", "机关"],
            forbidden_elements=["修仙", "灵气", "飞剑", "法术", "魔法", "斗气"],
            writing_guidance="知识就是力量，主角通过科学知识解决问题。"
        ),
        WorldviewTag(
            name="异能",
            dimension="力量",
            description="超自然异能体系",
            allowed_elements=["异能", "超能力", "念力", "心灵感应", "预知", "瞬移",
                              "精神力", "觉醒", "能力者", "异能组织"],
            forbidden_elements=["修仙", "灵气", "飞剑", "魔法", "斗气"],
            writing_guidance="异能设定需要明确的规则和限制，避免万能化。"
        ),
        WorldviewTag(
            name="诡异",
            dimension="力量",
            description="克苏鲁/恐怖/未知力量",
            allowed_elements=["诡异", "怪物", "触手", "感染", "寄生", "共生", "母体",
                              "未知存在", "疯狂", "污染", "扭曲", "异变",
                              "诡物", "规则", "禁忌", "都市怪谈", "恐惧",
                              "深渊", "虚空", "意识体"],
            forbidden_elements=[],
            writing_guidance="恐怖悬疑氛围，强调未知与不可名状，规则型怪谈。"
        ),

        # ============================
        # 社会维度
        # ============================
        WorldviewTag(
            name="皇权",
            dimension="社会",
            description="帝制社会体系",
            allowed_elements=["皇帝", "朝堂", "后宫", "世家", "门阀", "士族", "科举",
                              "将军", "丞相", "太监", "宫女", "藩王", "封地"],
            forbidden_elements=[],
            writing_guidance="权谋博弈，宫廷斗争，朝堂政治。"
        ),
        WorldviewTag(
            name="宗门",
            dimension="社会",
            description="宗门/门派体系",
            allowed_elements=["宗门", "掌门", "长老", "弟子", "外门", "内门", "核心弟子",
                              "宗门大比", "仙门", "世家", "散修"],
            forbidden_elements=[],
            writing_guidance="宗门政治与门派竞争，师徒关系。"
        ),
        WorldviewTag(
            name="都市",
            dimension="社会",
            description="现代都市社会",
            allowed_elements=["公司", "学校", "医院", "警察", "黑帮", "财团", "家族企业",
                              "地下世界", "酒吧", "夜店", "社交"],
            forbidden_elements=[],
            writing_guidance="都市社会关系，职场斗争，家族企业。"
        ),
        WorldviewTag(
            name="部落",
            dimension="社会",
            description="部落/氏族体系",
            allowed_elements=["部落", "酋长", "长老", "勇士", "祭司", "图腾", "血脉"],
            forbidden_elements=[],
            writing_guidance="部落文化与生存竞争。"
        ),
        WorldviewTag(
            name="企业",
            dimension="社会",
            description="企业/财团统治",
            allowed_elements=["企业", "CEO", "董事会", "股份", "并购", "商战", "财团",
                              "黑市", "佣兵", "私人军队"],
            forbidden_elements=[],
            writing_guidance="资本运作与权力游戏。"
        ),
        WorldviewTag(
            name="学院",
            dimension="社会",
            description="学院/学校体系",
            allowed_elements=["学院", "老师", "学生", "考试", "竞赛", "社团", "年级排名",
                              "入学", "毕业", "校规"],
            forbidden_elements=[],
            writing_guidance="校园生活与成长竞争。"
        ),

        # ============================
        # 特殊维度
        # ============================
        WorldviewTag(
            name="穿越",
            dimension="特殊",
            description="穿越/转生设定",
            allowed_elements=["穿越", "前世记忆", "现代知识", "金手指", "先知",
                              "蝴蝶效应", "历史改写"],
            forbidden_elements=[],
            writing_guidance="主角拥有超越时代的知识，但需要合理限制。"
        ),
        WorldviewTag(
            name="重生",
            dimension="特殊",
            description="重生/回档设定",
            allowed_elements=["重生", "回档", "前世记忆", "先知", "悔恨", "弥补"],
            forbidden_elements=[],
            writing_guidance="主角借前世经验避坑，但命运已改变，不能全知。"
        ),
        WorldviewTag(
            name="系统",
            dimension="特殊",
            description="系统/面板辅助设定",
            allowed_elements=["系统", "面板", "任务", "奖励", "升级", "等级",
                              "经验值", "属性", "技能树", "抽奖"],
            forbidden_elements=[],
            writing_guidance="系统辅助成长，但不能过度依赖。"
        ),
        WorldviewTag(
            name="末世",
            dimension="特殊",
            description="末世/废土设定",
            allowed_elements=["末日", "丧尸", "变异", "废墟", "避难所", "物资",
                              "幸存者", "感染", "病毒", "基因突变", "异变体",
                              "辐射", "核冬天"],
            forbidden_elements=["正常社会秩序", "物资充足"],
            writing_guidance="生存压力和人性考验，资源争夺是核心冲突。"
        ),
        WorldviewTag(
            name="无特殊",
            dimension="特殊",
            description="无特殊设定",
            allowed_elements=[],
            forbidden_elements=["穿越", "重生", "系统", "面板", "升级", "等级",
                                "经验值", "属性", "金手指", "空间戒指", "属性板"],
            writing_guidance=""
        ),
    ]

    # 按维度归档
    for tag in tags:
        dim = tag.dimension
        if dim not in DIMENSION_TAGS:
            DIMENSION_TAGS[dim] = {}
        DIMENSION_TAGS[dim][tag.name] = tag


_register_all_tags()


# 全局通用禁词（叙事手法层面，与世界观无关）
UNIVERSAL_FORBIDDEN = [
    "机械降神", "金手指", "穿越者", "直播", "天道",
]


# ==========================================================================
# 3. 旧名称 → 标签组合 映射（向后兼容）
# ==========================================================================

LEGACY_SETTING_MAP: Dict[str, List[str]] = {
    "架空古代":   ["古代", "武功低武", "皇权", "无特殊"],
    "仙侠":       ["古代", "修仙", "宗门", "无特殊"],
    "东方玄幻":   ["古代", "武功高武", "宗门", "无特殊"],
    "都市玄幻":   ["现代", "异能", "都市", "无特殊"],
    "都市修仙":   ["现代", "修仙", "都市", "无特殊"],
    "诡异修仙":   ["古代", "修仙", "诡异", "无特殊"],
    "西方奇幻":   ["古代", "魔法", "学院", "无特殊"],
    "末世":       ["现代", "异能", "末世"],
    "赛博朋克":   ["未来", "科技", "企业", "无特殊"],
    "穿越古代造科技": ["古代", "科技", "皇权", "穿越"],
}


# ==========================================================================
# 4. 世界观引擎
# ==========================================================================

def _find_tag(name: str) -> Optional[WorldviewTag]:
    """在所有维度中查找标签"""
    for dim_tags in DIMENSION_TAGS.values():
        if name in dim_tags:
            return dim_tags[name]
    return None


class WorldviewEngine:
    """
    世界观引擎 — 核心类
    
    用法:
        engine = WorldviewEngine(["现代", "修仙", "都市"])
        forbidden = engine.get_forbidden_elements()
        prompt = engine.get_constraint_prompt()
    """

    def __init__(self, tags: List[str]):
        """
        初始化引擎。

        Args:
            tags: 标签名列表，如 ["古代", "修仙", "宗门"]
        """
        self.tag_names = tags
        self.tags: List[WorldviewTag] = []
        self._unknown_tags: List[str] = []

        for name in tags:
            tag = _find_tag(name)
            if tag:
                self.tags.append(tag)
            else:
                self._unknown_tags.append(name)

        if self._unknown_tags:
            print(f"⚠️ 未识别的世界观标签: {self._unknown_tags}")

    # ----- 核心计算 -----

    def get_allowed_elements(self) -> Set[str]:
        """合并所有选中标签的允许元素（并集）"""
        result = set()
        for tag in self.tags:
            result.update(tag.allowed_elements)
        return result

    def get_raw_forbidden_elements(self) -> Set[str]:
        """合并所有选中标签的禁止元素（并集）"""
        result = set()
        for tag in self.tags:
            result.update(tag.forbidden_elements)
        return result

    def get_forbidden_elements(self) -> List[str]:
        """
        最终禁止列表 = (所有标签的 forbidden 并集) - (所有标签的 allowed 并集) + 通用禁词
        
        白名单优先原则：如果某个标签明确 allow 了某元素，
        即使另一个标签 forbid 了它，最终也是允许的。
        """
        allowed = self.get_allowed_elements()
        raw_forbidden = self.get_raw_forbidden_elements()
        
        # 白名单覆盖黑名单
        final_forbidden = raw_forbidden - allowed
        
        # 加入通用禁词（除非被白名单覆盖）
        for word in UNIVERSAL_FORBIDDEN:
            if word not in allowed:
                final_forbidden.add(word)
        
        return sorted(final_forbidden)

    # ----- Prompt 生成 -----

    def get_setting_name(self) -> str:
        """生成可读的世界观名称"""
        return "+".join(self.tag_names)

    def get_setting_summary(self) -> str:
        """一行概要"""
        allowed = self.get_allowed_elements()
        forbidden = self.get_forbidden_elements()
        allowed_sample = list(allowed)[:5]
        forbidden_sample = forbidden[:5]
        return (f"世界观标签: {self.get_setting_name()}, "
                f"核心元素: {', '.join(allowed_sample)}, "
                f"禁止: {', '.join(forbidden_sample)}等{len(forbidden)}项")

    def get_constraint_prompt(self) -> str:
        """生成完整的「世界观锁死」约束段落"""
        forbidden = self.get_forbidden_elements()
        allowed = self.get_allowed_elements()
        
        # 组装标签描述
        tag_descriptions = []
        for tag in self.tags:
            if tag.description:
                tag_descriptions.append(f"- {tag.name}({tag.dimension}): {tag.description}")

        # 组装写作指导
        guidances = []
        for tag in self.tags:
            if tag.writing_guidance:
                guidances.append(f"- [{tag.name}] {tag.writing_guidance}")

        forbidden_str = ", ".join(forbidden) if forbidden else "（无特定禁止元素）"
        allowed_sample = ", ".join(sorted(allowed)[:20]) if allowed else "（无特定要求）"

        return f"""【🔴 红线警告：世界观锁死 🔴】
本小说的世界观标签组合为：{self.get_setting_name()}
从第1卷到第100卷必须始终在同一个世界观之下，不可中途改变设定。

【世界观维度定义】
{chr(10).join(tag_descriptions)}

【核心允许元素（白名单）】
以下元素是本题材的核心组成部分，可以自由使用：
{allowed_sample}

【严格禁止元素（红线）】
以下{len(forbidden)}个元素严禁出现（即便包装伪装也严禁）：
{forbidden_str}

【写作风格指导】
{chr(10).join(guidances)}"""

    # ----- 序列化 -----

    def to_dict(self) -> dict:
        """序列化为可存储的字典"""
        return {
            "worldview_tags": self.tag_names,
            "allowed_elements": sorted(self.get_allowed_elements()),
            "forbidden_elements": self.get_forbidden_elements(),
            "setting_name": self.get_setting_name(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorldviewEngine':
        """从字典恢复"""
        tags = data.get("worldview_tags", ["古代", "武功低武", "皇权", "无特殊"])
        return cls(tags)

    @classmethod
    def from_setting(cls, setting: str) -> 'WorldviewEngine':
        """
        从旧的 --setting 参数创建引擎（向后兼容）。
        
        支持：
        - 旧名称: "架空古代" → 映射为标签组合
        - 逗号分隔标签: "现代,修仙,都市" → 直接使用
        """
        # 如果包含逗号，视为标签组合
        if "," in setting or "，" in setting:
            tags = [t.strip() for t in setting.replace("，", ",").split(",") if t.strip()]
            return cls(tags)
        
        # 尝试旧名称映射
        if setting in LEGACY_SETTING_MAP:
            return cls(LEGACY_SETTING_MAP[setting])
        
        # 尝试作为单一标签
        if _find_tag(setting):
            return cls([setting])
        
        # 兜底：默认架空古代
        print(f"⚠️ 未识别的世界观 '{setting}'，回退到'架空古代'")
        return cls(LEGACY_SETTING_MAP["架空古代"])


# ==========================================================================
# 5. 便捷函数
# ==========================================================================

def get_available_tags() -> Dict[str, List[str]]:
    """返回所有可用标签（按维度分组）"""
    result = {}
    for dim, tags in DIMENSION_TAGS.items():
        result[dim] = list(tags.keys())
    return result


def get_available_presets() -> Dict[str, List[str]]:
    """返回所有预设题材及其标签组合"""
    return dict(LEGACY_SETTING_MAP)
