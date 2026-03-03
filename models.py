"""
Story-Sisyphus 核心数据模型
定义故事圣经、角色卡片、世界观设定等核心数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class CharacterState(Enum):
    """角色状态枚举"""
    ALIVE = "alive"
    DEAD = "dead"
    MISSING = "missing"
    INJURED = "injured"


class LoopStatus(Enum):
    """伏笔状态枚举"""
    OPEN = "open"  # 已埋下,未回收
    CLOSED = "closed"  # 已回收
    ABANDONED = "abandoned"  # 红鲱鱼/死线


@dataclass
class WritingTag:
    """写作标签 - 用于引导写作风格和方向"""
    
    name: str  # 标签名称
    category: str  # 标签类型 (人物群像、人物关系、情感基调、叙事风格、人物设定)
    guidance: str  # 写作引导说明
    keywords: List[str] = field(default_factory=list)  # 相关关键词


@dataclass
class BackgroundTheme:
    """背景题材设定 - 确保生成内容严格符合特定世界观背景"""
    
    name: str  # 题材名称，如"架空古代"、"仙侠"、"东方玄幻"
    category: str  # 分类：古代、现代、未来、异世界
    
    # 世界观约束
    era_description: str = ""  # 时代描述
    technology_level: str = ""  # 科技水平约束
    magic_system: str = ""  # 魔法/修炼体系约束
    social_structure: str = ""  # 社会结构约束
    
    # 禁止元素列表 - 生成时不可出现的现代或不符合设定的元素
    forbidden_elements: List[str] = field(default_factory=list)
    # 例如: ["手机", "汽车", "电脑", "网络"]
    
    # 必须元素列表 - 生成时需要融入的核心元素
    required_elements: List[str] = field(default_factory=list)
    # 例如: ["修炼", "灵气", "宗门", "法术"]
    
    # 写作引导
    writing_guidance: str = ""  # 写作风格指导
    keywords: List[str] = field(default_factory=list)  # 常用关键词
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# 预定义背景题材
PREDEFINED_THEMES: Dict[str, 'BackgroundTheme'] = {}


def _init_predefined_themes():
    """初始化预定义背景题材"""
    global PREDEFINED_THEMES
    
    themes_data = [
        # 架空古代
        BackgroundTheme(
            name="架空古代",
            category="古代",
            era_description="非真实历史的古代封建王朝背景，存在皇帝、官员、世家等社会结构",
            technology_level="冷兵器时代，无现代科技，依靠人力、畜力和简单机械",
            magic_system="无或极少，以武功、内功为主要战力体系",
            social_structure="皇权至上，士农工商阶层分明，宗族观念强烈",
            forbidden_elements=["手机", "电脑", "汽车", "飞机", "枪炮", "电力", "网络", "现代医疗", "科幻", "星际", "AI", "程序", "物理宇宙", "数据流", "锚点", "外星人", "银河系", "宇宙", "时间旅行", "平行世界", "维度", "位面", "逻辑武器", "科幻修仙", "缸中之脑", "直播", "天道", "内燃机", "大炮", "工业革命", "丧尸变异", "降维打击"],
            required_elements=["朝堂", "后宫", "世家", "江湖", "武功"],
            writing_guidance="使用古风文言与白话结合的语言风格，注重礼仪规矩描写，人物称谓使用古代敬语，场景描写体现古代生活细节。严禁机械降神，必须拆解仿写群像内核（底层逆袭、多面配角、全员智商在线，没有绝对的恶只有利益与立意）。",
            keywords=["皇上", "王爷", "丫鬟", "轿子", "府邸", "江湖", "武功", "内力"]
        ),
        
        # 仙侠
        BackgroundTheme(
            name="仙侠",
            category="异世界",
            era_description="以修仙为核心的东方神话世界，追求长生不老和问道成仙",
            technology_level="古代科技+法宝炼器，飞剑代步，传音符代替通讯",
            magic_system="修仙体系：练气、筑基、金丹、元婴、化神、渡劫、大乘、仙人等境界",
            social_structure="宗门体系为主，修为决定地位，凡人与修士分隔",
            forbidden_elements=["手机", "电脑", "汽车", "现代武器", "电力设备", "互联网"],
            required_elements=["修炼", "灵气", "宗门", "法术", "飞剑", "丹药", "灵石", "天劫"],
            writing_guidance="融入道家哲学思想，注重境界突破描写，战斗以法术对决为主，"
                           "强调天道因果、心魔劫难等仙侠特色元素。",
            keywords=["修炼", "突破", "境界", "真气", "灵脉", "仙缘", "道心", "劫数", "飞升"]
        ),
        
        # 东方玄幻
        BackgroundTheme(
            name="东方玄幻",
            category="异世界",
            era_description="融合东方神话元素的架空大陆，有多个国家、种族和势力",
            technology_level="玄幻科技，以斗气、元力等能量驱动，有传送阵等魔法设施",
            magic_system="玄幻体系：斗者、斗师、斗灵、斗王、斗皇、斗宗、斗尊、斗圣、斗帝等",
            social_structure="帝国与家族并存，强者为尊，实力决定一切",
            forbidden_elements=["手机", "电脑", "汽车", "现代科技", "电力", "网络"],
            required_elements=["斗气", "功法", "丹药", "魔兽", "家族", "帝国", "秘境"],
            writing_guidance="热血爽快的战斗描写，注重实力碾压和逆袭打脸，"
                           "融入东方神话传说元素，设计层次分明的力量体系。",
            keywords=["斗气", "血脉", "功法", "丹药", "魔兽", "天才", "废物", "逆袭", "打脸"]
        ),
        
        # 都市玄幻
        BackgroundTheme(
            name="都市玄幻",
            category="现代",
            era_description="现代都市背景下隐藏着超自然力量和修炼者世界",
            technology_level="现代科技与古武/修炼并存，两个世界互不干扰",
            magic_system="古武体系或现代修炼体系，境界设定较为简单",
            social_structure="普通社会与修炼者秘密组织并行，有专门管理超自然事件的机构",
            forbidden_elements=["完全的古代背景", "没有现代元素"],
            required_elements=["都市", "隐世家族", "修炼者", "普通人", "超自然力量"],
            writing_guidance="现代都市生活与修炼世界交织，注重身份隐藏和揭秘，"
                           "战斗需考虑对普通人和城市的影响，语言风格现代化。",
            keywords=["隐世", "古武", "高手", "家族", "财团", "豪门", "逆袭", "装X"]
        ),
        
        # 西方奇幻
        BackgroundTheme(
            name="西方奇幻",
            category="异世界",
            era_description="中世纪欧洲风格的魔法世界，有精灵、矮人、兽人等种族",
            technology_level="中世纪+魔法，有魔法驱动的设备和建筑",
            magic_system="魔法体系：学徒、魔法师、大魔法师、魔导士、法圣、法神等",
            social_structure="王国、帝国、教廷并立，有骑士团、魔法学院等组织",
            forbidden_elements=["手机", "电脑", "汽车", "东方元素过多", "网络"],
            required_elements=["魔法", "骑士", "精灵", "矮人", "巨龙", "地下城", "冒险者"],
            writing_guidance="使用西方奇幻常见设定，注重职业体系和冒险探索，"
                           "融入西方神话和中世纪文化元素。",
            keywords=["魔法", "骑士", "精灵", "龙", "公会", "冒险", "副本", "遗迹"]
        ),
        
        # 末世
        BackgroundTheme(
            name="末世",
            category="未来",
            era_description="灾难后的废土世界，人类文明崩溃，资源稀缺",
            technology_level="科技倒退或局部保留，以生存为主",
            magic_system="可有异能/变异体系，也可纯科幻末世",
            social_structure="幸存者聚落，强者为王，资源争夺激烈",
            forbidden_elements=["正常的现代社会秩序", "物资充足的描写"],
            required_elements=["废墟", "丧尸/变异体", "物资", "避难所", "生存"],
            writing_guidance="着重描写生存压力和人性考验，资源争夺是核心冲突，"
                           "注重末世求生的紧迫感和绝望氛围。",
            keywords=["丧尸", "变异", "物资", "基地", "异能", "生存", "废墟", "末日"]
        ),
        
        # 赛博朋克
        BackgroundTheme(
            name="赛博朋克",
            category="未来",
            era_description="高科技低生活的未来都市，巨型企业控制社会",
            technology_level="超高科技，人体改造、人工智能、虚拟现实普及",
            magic_system="无魔法，以科技为核心，有黑客、改造人等",
            social_structure="企业统治，贫富悬殊极大，底层人生活在都市阴暗角落",
            forbidden_elements=["魔法", "修仙", "古代元素"],
            required_elements=["义体改造", "人工智能", "黑客", "巨型企业", "霓虹都市"],
            writing_guidance="阴暗的都市美学，底层视角叙事，科技与人性的冲突，"
                           "使用赛博朋克特有的俚语和设定。",
            keywords=["义体", "芯片", "黑客", "企业", "底层", "霓虹", "赛博空间"]
        ),
    ]
    
    for theme in themes_data:
        PREDEFINED_THEMES[theme.name] = theme


# 初始化预定义背景题材
_init_predefined_themes()


# 预定义写作标签
PREDEFINED_TAGS: Dict[str, 'WritingTag'] = {}


def _init_predefined_tags():
    """初始化预定义标签"""
    global PREDEFINED_TAGS
    
    tags_data = [
        # 人物群像类
        WritingTag(
            name="群像",
            category="人物群像",
            guidance="采用多视角叙事，每个重要角色都有自己的故事线和成长弧。"
                     "避免配角沦为工具人，赋予他们独立的动机和冲突。"
                     "多用群戏场面展现人物关系网络，注重角色间的化学反应。",
            keywords=["多视角", "群戏", "角色塑造", "人物弧光"]
        ),
        
        # 人物关系类
        WritingTag(
            name="团宠",
            category="人物关系",
            guidance="主角被众人宠爱、保护，强调温馨互动和守护欲。"
                     "周围角色主动为主角排忧解难，展现真挚情感。"
                     "设计'被宠'的具体场景：送礼、护短、争相关心等。",
            keywords=["被宠", "保护", "温馨", "守护", "溺爱"]
        ),
        
        # 情感基调类
        WritingTag(
            name="虐恋",
            category="情感基调",
            guidance="情感纠葛深刻，苦尽甘来。设计误会、错过、身份阻隔等障碍。"
                     "重视情感铺垫和情绪渲染，虐中带糖，糖中带刀。"
                     "结局走向HE时要有足够的情感释放。",
            keywords=["虐心", "误会", "错过", "苦尽甘来", "BE美学"]
        ),
        WritingTag(
            name="甜宠",
            category="情感基调",
            guidance="轻松甜蜜的感情线，高糖剧情为主。"
                     "设计撒糖场景：日常互动、宠溺细节、甜蜜对话。"
                     "即使有矛盾也快速化解，保持整体轻松愉快的氛围。",
            keywords=["高糖", "宠溺", "轻松", "甜蜜", "日常"]
        ),
        
        # 叙事风格类
        WritingTag(
            name="爽文",
            category="叙事风格",
            guidance="节奏明快，主角金手指明显，打脸剧情多。"
                     "设计装X打脸循环：压制→反转→碾压→围观惊叹。"
                     "及时给读者正反馈，避免长期压抑。",
            keywords=["打脸", "金手指", "爽点", "逆袭", "碾压"]
        ),
        WritingTag(
            name="慢热",
            category="叙事风格",
            guidance="情节发展缓慢，注重铺垫和细节。"
                     "人物关系渐进发展，避免一见钟情式的突兀。"
                     "重视日常描写和情感积累，读者需要耐心才能体会妙处。",
            keywords=["细腻", "铺垫", "渐进", "日常", "慢节奏"]
        ),
        
        # 人物设定类
        WritingTag(
            name="大女主",
            category="人物设定",
            guidance="女主独立成长，事业线与感情线并重或事业线为主。"
                     "女主有明确目标和独立人格，不依附男性角色。"
                     "展现女性力量和智慧，逆境中成长蜕变。",
            keywords=["独立", "成长", "事业", "女性力量", "蜕变"]
        ),
        WritingTag(
            name="大男主",
            category="人物设定",
            guidance="男主独立成长，权谋/修炼/冒险为主线。"
                     "男主有明确目标，感情线辅助主线发展。"
                     "展现男性成长历程，从弱到强的蜕变轨迹。",
            keywords=["成长", "权谋", "修炼", "变强", "逆袭"]
        ),
    ]
    
    for tag in tags_data:
        PREDEFINED_TAGS[tag.name] = tag


# 初始化预定义标签
_init_predefined_tags()


@dataclass
class CharacterCard:
    """角色卡片 - 动态人物档案"""
    
    # 基础信息
    name: str  # 姓名
    alias: List[str] = field(default_factory=list)  # 别名/代号
    identity: str = ""  # 身份
    
    # 位置与状态
    current_location: str = ""  # 当前位置
    state: CharacterState = CharacterState.ALIVE  # 生存状态
    
    # 能力值
    power_level: int = 0  # 战力值
    power_history: List[Dict[str, Any]] = field(default_factory=list) # 战力成长历史 [{"chapter": 1, "level": 100}]
    cultivation_stage: str = ""  # 修炼境界
    special_abilities: List[str] = field(default_factory=list)  # 特殊能力
    
    # 性格与心理
    personality_keywords: List[str] = field(default_factory=list)  # 性格关键词
    psychological_state: str = ""  # 当前心理状态
    character_arc_progress: float = 0.0  # 人物弧光进度 (0-1)
    
    # 性格坐标系 (用于轨迹分析)
    personality_coordinates: Dict[str, float] = field(default_factory=dict)
    # 例如: {"naive_to_mature": 0.2, "kind_to_ruthless": 0.1}
    
    # 关系网络
    relationships: Dict[str, str] = field(default_factory=dict)
    # 例如: {"张三": "仇敌", "李四": "师父"}
    
    # 物品与资源
    inventory: List[str] = field(default_factory=list)  # 持有物品
    resources: Dict[str, int] = field(default_factory=dict)  # 资源 (金钱、灵石等)
    
    # 经历记录
    major_events: List[str] = field(default_factory=list)  # 重大经历
    first_appearance_chapter: Optional[int] = None  # 首次登场章节
    
    # 详细档案 (MD 生成用)
    biography: str = ""  # 人物小传 (500字+)
    highlights: List[str] = field(default_factory=list)  # 高光时刻
    detailed_relationships: str = ""  # 详细的人物关系描述
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def update_psychological_state(self, new_state: str, reason: str):
        """更新心理状态"""
        self.psychological_state = new_state
        self.major_events.append(f"心理状态变化: {new_state} (原因: {reason})")
        self.updated_at = datetime.now().isoformat()
    
    def update_personality_coordinate(self, axis: str, delta: float):
        """更新性格坐标"""
        if axis not in self.personality_coordinates:
            self.personality_coordinates[axis] = 0.0
        self.personality_coordinates[axis] += delta
        # 限制在 [0, 1] 范围内
        self.personality_coordinates[axis] = max(0.0, min(1.0, self.personality_coordinates[axis]))
        self.updated_at = datetime.now().isoformat()


@dataclass
class EventRecord:
    """事件记录 - 用于事件溯源"""
    
    event_id: str  # 事件唯一ID
    chapter: int  # 发生章节
    event_type: str  # 事件类型 (战斗、对话、获得物品等)
    description: str  # 事件描述
    
    # 事实性数据 (用于逻辑校验)
    facts: Dict[str, Any] = field(default_factory=dict)
    # 例如: {"character": "李四", "action": "左手被砍断", "location": "A城"}
    
    # 影响的角色
    affected_characters: List[str] = field(default_factory=list)
    
    # 时间戳
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_fact(self, key: str) -> Any:
        """获取事实"""
        return self.facts.get(key)


@dataclass
class OpenLoop:
    """伏笔/开放线索"""
    
    loop_id: str  # 伏笔唯一ID
    title: str  # 伏笔标题
    description: str  # 详细描述
    
    # 埋下信息
    planted_chapter: int  # 埋下章节
    planted_content: str  # 埋下时的具体内容
    
    # 回收信息
    status: LoopStatus = LoopStatus.OPEN
    resolved_chapter: Optional[int] = None  # 回收章节
    resolution: str = ""  # 回收方式
    
    # 调度信息
    ttl: int = 50  # Time To Live (建议在多少章内回收)
    weight: int = 5  # 权重 (1-10, 10 最重要)
    category: str = ""  # 类别 (物品、人物、秘密等)
    
    # 相关角色/物品
    related_entities: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def is_overdue(self, current_chapter: int) -> bool:
        """判断是否超期"""
        return current_chapter - self.planted_chapter > self.ttl
    
    def close(self, chapter: int, resolution: str):
        """关闭伏笔"""
        self.status = LoopStatus.CLOSED
        self.resolved_chapter = chapter
        self.resolution = resolution


@dataclass
class WorldSettings:
    """世界观设定"""
    
    # 基础设定
    world_name: str = ""  # 世界名称
    world_type: str = ""  # 世界类型 (修仙、玄幻、都市等)
    
    # 背景题材设定
    background_theme: str = ""  # 背景题材名称，如"仙侠"、"东方玄幻"
    theme_constraints: Dict[str, Any] = field(default_factory=dict)
    # 从 BackgroundTheme 继承的约束规则，用于内容校验
    
    # 战力体系
    power_system: Dict[str, Any] = field(default_factory=dict)
    # 例如: {
    #   "stages": ["练气", "筑基", "金丹", "元婴"],
    #   "power_ranges": {"练气": [1, 100], "筑基": [100, 500]},
    #   "rules": ["低境界不能击败高境界(除非有特殊道具)"]
    # }
    power_ceiling: float = 1000000.0  # 战力天花板 (绝对数值)
    growth_rate_limit: float = 0.05   # 每卷成长速度限制 (5%)
    
    # 地理信息
    geography: Dict[str, Any] = field(default_factory=dict)
    # 例如: {
    #   "continents": ["东域", "西域"],
    #   "cities": {"A城": {"location": "东域", "population": 100000}},
    #   "travel_times": {"A城->B城": "3天"}
    # }
    
    # 势力分布
    factions: Dict[str, Any] = field(default_factory=dict)
    # 例如: {
    #   "天剑宗": {"type": "正派", "leader": "张三", "strength": 8},
    #   "魔教": {"type": "邪派", "leader": "李四", "strength": 9}
    # }
    
    # 经济系统
    economy: Dict[str, Any] = field(default_factory=dict)
    # 例如: {
    #   "currency": "灵石",
    #   "exchange_rate": {"金币": 100, "灵石": 1},
    #   "inflation_rate": 0.0
    # }
    
    # 时间线
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    # 例如: [{"chapter": 1, "date": "天元历1000年", "event": "主角出生"}]
    
    # 物理规则
    physics_rules: List[str] = field(default_factory=list)
    # 例如: ["灵气浓度影响修炼速度", "特定区域禁止飞行"]
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_power_range(self, stage: str) -> Optional[tuple]:
        """获取境界的战力范围"""
        if "power_ranges" in self.power_system and stage in self.power_system["power_ranges"]:
            return tuple(self.power_system["power_ranges"][stage])
        return None
    
    def get_travel_time(self, from_loc: str, to_loc: str) -> Optional[str]:
        """获取两地旅行时间"""
        key = f"{from_loc}->{to_loc}"
        return self.geography.get("travel_times", {}).get(key)


@dataclass
class PlotArc:
    """剧情弧 - 管理卷/章节结构"""
    
    arc_id: str  # 剧情弧ID
    arc_type: str  # 类型: "volume" (卷) 或 "arc" (剧情弧)
    title: str  # 标题
    
    # 章节范围
    start_chapter: int  # 起始章节
    end_chapter: int  # 结束章节
    
    # 剧情信息
    summary: str = ""  # 概要
    main_conflict: str = ""  # 主要冲突
    climax_chapter: Optional[int] = None  # 高潮章节
    
    # 涉及角色
    main_characters: List[str] = field(default_factory=list)
    supporting_characters: List[str] = field(default_factory=list)
    
    # 目标与结果
    protagonist_goal: str = ""  # 主角目标
    outcome: str = ""  # 结果
    
    # 子剧情弧
    sub_arcs: List[str] = field(default_factory=list)  # 子剧情弧ID列表
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Subplot:
    """支线剧情 - 配角视角的独立故事线"""
    
    subplot_id: str  # 支线ID
    title: str  # 支线标题
    
    # 核心信息
    protagonist: str  # 支线主角（配角名）
    summary: str = ""  # 支线概要
    theme: str = ""  # 支线主题（如：救赎、复仇、成长、爱情）
    
    # 人物弧光
    character_start_state: str = ""  # 角色起始状态
    character_end_state: str = ""  # 角色结束状态
    character_transformation: str = ""  # 角色转变过程
    
    # 与主线的关系
    intersection_chapters: List[int] = field(default_factory=list)  # 与主线交汇的章节
    main_plot_influence: str = ""  # 对主线的影响
    
    # 时间跨度
    start_volume: int = 1
    end_volume: int = 1
    
    # 关键节点
    key_moments: List[str] = field(default_factory=list)  # 支线的关键时刻
    
    # 状态
    status: str = "active"  # active, resolved, abandoned
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HiddenPlotline:
    """暗线 - 读者后知的隐藏剧情线"""
    
    plotline_id: str  # 暗线ID
    title: str  # 暗线标题
    
    # 核心信息
    secret: str = ""  # 暗线的秘密/真相
    revelation_impact: str = ""  # 揭晓时的冲击效果
    
    # 伏笔链条
    hints: List[Dict[str, Any]] = field(default_factory=list)
    # 每个hint格式: {"chapter": 章节号, "content": "伏笔内容", "obviousness": "隐晦/中等/明显"}
    
    # 揭晓规划
    partial_reveals: List[Dict[str, Any]] = field(default_factory=list)  # 部分揭晓
    final_reveal_volume: int = 0  # 最终揭晓卷号
    
    # 涉及角色
    key_characters: List[str] = field(default_factory=list)
    
    # 状态
    status: str = "hidden"  # hidden, partially_revealed, fully_revealed
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CharacterArc:
    """人物弧光 - 每个角色都是主角"""
    
    character_name: str  # 角色名
    arc_id: str = ""  # 弧光ID
    
    # 核心设定 - 让每个角色都像主角一样立体
    personal_goal: str = ""  # 个人目标（独立于主角的目标）
    motivation: str = ""  # 动机
    greatest_fear: str = ""  # 最大恐惧
    obsession: str = ""  # 执念
    moral_code: str = ""  # 道德准则
    
    # 人物弧光阶段
    starting_point: str = ""  # 起点：角色最初的状态
    inciting_incident: str = ""  # 触发事件：什么改变了角色
    struggle: str = ""  # 挣扎：角色面对的困境
    turning_point: str = ""  # 转折点：角色做出关键选择
    transformation: str = ""  # 转变：角色如何改变
    resolution: str = ""  # 结局：角色的最终命运
    
    # 与主角的关系
    relationship_to_protagonist: str = ""  # 与主角的关系
    conflict_with_protagonist: str = ""  # 与主角的冲突点
    
    # 高光时刻
    spotlight_chapters: List[int] = field(default_factory=list)  # 角色的高光章节
    signature_moments: List[str] = field(default_factory=list)  # 标志性时刻
    
    # 读者共情点
    empathy_hooks: List[str] = field(default_factory=list)  # 让读者产生共鸣的点
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class NarrativeLineType(Enum):
    """叙事线类型"""
    MAIN = "主线"       # 主线（1条）
    SUBPLOT = "支线"    # 支线（3-4条）
    HIDDEN = "暗线"     # 暗线（2-3条）
    CHARACTER = "角色线"  # 角色专属线（1-2条）


@dataclass
class NarrativeLine:
    """
    叙事线 - 三幕九线写作手法的核心数据结构
    
    九条线 = 1 主线 + 3~4 支线 + 2~3 暗线 + 1~2 角色专属线
    
    【三幕结构】:
    - 第一幕（铺陈）: 卷1~30 — 建立世界、引入冲突、埋设伏笔
    - 第二幕（对抗）: 卷31~70 — 冲突升级、线索交汇、角色转变
    - 第三幕（解决）: 卷71~100 — 暗线揭晓、高潮决战、各线收束
    """
    
    line_id: str           # 叙事线唯一ID
    title: str             # 叙事线标题
    line_type: str = "支线"  # NarrativeLineType 的 value
    
    # 核心内容
    description: str = ""   # 叙事线概要
    theme: str = ""         # 叙事主题（如：权力的代价、爱与牺牲）
    
    # 关键角色
    primary_character: str = ""    # 主要角色
    related_characters: List[str] = field(default_factory=list)
    
    # 三幕阶段进展
    act1_setup: str = ""        # 第一幕铺陈（卷1~30做了什么）
    act2_confrontation: str = "" # 第二幕对抗（卷31~70做了什么）
    act3_resolution: str = ""    # 第三幕解决（卷71~100做了什么）
    
    # 时间跨度
    start_volume: int = 1
    end_volume: int = 100
    
    # 高潮/关键节点
    key_nodes: List[Dict[str, Any]] = field(default_factory=list)
    # [{volume: 15, chapter: 148, event: "暗线首个线索被发现"}]
    
    # 与其他线的交汇
    convergence_points: List[Dict[str, Any]] = field(default_factory=list)
    # [{volume: 50, other_line_id: "main", event: "支线角色加入主线战斗"}]
    
    # 当前状态
    status: str = "active"   # active / suspended / resolved
    current_progress: float = 0.0  # 0.0 ~ 1.0
    
    # 活跃卷（哪些卷是此线的聚光灯）
    active_volumes: List[int] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class VolumePlan:
    """卷规划 - 每卷(10章)的宏观设计，必须在生成章节大纲前完成"""
    
    volume_number: int  # 卷号 (1-100)
    title: str  # 卷标题
    
    # 内容规划
    summary: str = ""  # 本卷内容概要 (300-500字)
    main_conflict: str = ""  # 本卷核心冲突
    protagonist_growth: str = ""  # 主角在本卷的成长目标/收获
    
    # 关键事件 (10项，对应10章)
    key_events: List[str] = field(default_factory=list)
    # 例如: ["主角初遇宿敌", "获得神秘传承", ...]
    
    # 【强制三幕结构与人物细节】
    act_one: str = ""  # 第一幕（起）：开场与危机引入
    act_two: str = ""  # 第二幕（承/转）：调查与冲突升级
    act_three: str = ""  # 第三幕（合）：高潮与结局
    character_details: str = ""  # 核心人物刻画与逻辑闭环说明
    
    # 涉及角色
    key_characters: List[str] = field(default_factory=list)
    new_characters: List[str] = field(default_factory=list)  # 本卷新登场角色
    
    # 伏笔规划
    loops_to_resolve: List[str] = field(default_factory=list)  # 本卷计划回收的伏笔
    loops_to_plant: List[str] = field(default_factory=list)  # 本卷计划埋下的伏笔
    
    # 阶段标记
    phase: str = ""  # 所属阶段: 铺垫期/发展期/高潮期/收尾期
    
    # 【多线叙事规划 - 新增】
    main_scene: str = ""  # 主场景（每10卷最多换1个）
    
    # 支线规划
    active_subplots: List[str] = field(default_factory=list)  # 本卷活跃的支线ID
    subplot_progress: Dict[str, str] = field(default_factory=dict)  # 支线ID -> 本卷进展描述
    
    # 暗线规划
    hidden_hints: List[str] = field(default_factory=list)  # 本卷埋设的暗线伏笔
    
    # 配角弧光
    character_arcs_progress: Dict[str, str] = field(default_factory=dict)  # 角色名 -> 本卷弧光进展
    
    # 节奏控制
    pacing: str = ""  # 节奏: 平缓/渐进/紧张/高潮
    climax_level: int = 0  # 高潮等级: 0=无, 1=小高潮, 2=中等高潮, 3=大高潮
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_event_for_chapter(self, chapter_in_volume: int) -> Optional[str]:
        """获取卷内某章对应的关键事件 (1-10)"""
        if 1 <= chapter_in_volume <= len(self.key_events):
            return self.key_events[chapter_in_volume - 1]
        return None



@dataclass
class ChapterOutline:
    """章节大纲 - 四幕结构（起承转合）"""
    
    chapter_number: int  # 章节号
    title: str  # 章节标题
    
    # 大纲内容
    summary: str = ""  # 概要
    detailed_outline: str = ""  # 详细大纲（格式化后的完整文本）
    
    # 四幕结构 - 核心字段（调整为三幕）
    scene_setting: str = ""  # 场景设定，如"皇家秋猎围场，深林边缘"
    core_plot: str = ""  # 核心剧情概述，如"生死关头的人性抉择，林晚展现生存能力"
    act_one: str = ""  # 第一幕
    act_two: str = ""  # 第二幕
    act_three: str = ""  # 第三幕
    
    # 场景（兼容旧格式）
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    # 例如: [{"location": "A城", "characters": ["主角", "反派"], "action": "战斗"}]
    
    # 涉及角色
    characters: List[str] = field(default_factory=list)
    
    # 伏笔
    loops_planted: List[str] = field(default_factory=list)  # 本章埋下的伏笔ID
    loops_resolved: List[str] = field(default_factory=list)  # 本章回收的伏笔ID
    
    # 状态
    status: str = "planned"  # planned, drafted, reviewed, finalized
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def format_detailed_outline(self) -> str:
        """
        将四幕结构格式化为详细的大纲文本
        
        Returns:
            格式化后的大纲文本
        """
        lines = []
        
        # 章节标题
        lines.append(f"第{self.chapter_number}章：{self.title}")
        lines.append("")
        
        # 场景
        if self.scene_setting:
            lines.append(f"场景：{self.scene_setting}")
            lines.append("")
        
        # 人物
        if self.characters:
            lines.append(f"人物：{'、'.join(self.characters)}。")
            lines.append("")
        
        # 核心剧情
        if self.core_plot:
            lines.append(f"核心剧情：{self.core_plot}")
            lines.append("")
        
        # 第一幕、第二幕、第三幕
        if self.act_one:
            lines.append(f"第一幕：{self.act_one}")
            lines.append("")
        if self.act_two:
            lines.append(f"第二幕：{self.act_two}")
            lines.append("")
        if self.act_three:
            lines.append(f"第三幕：{self.act_three}")
        
        return "\n".join(lines)


@dataclass
class StoryBible:
    """故事圣经 - 核心状态管理器"""
    
    # 基础信息
    story_title: str = ""  # 故事标题
    genre: str = ""  # 类型
    target_chapters: int = 1000  # 目标章节数 (默认100卷 × 10章)
    
    # 背景题材 (确保内容符合世界观)
    background_theme: str = ""  # 背景题材名称，如"仙侠"、"东方玄幻"、"架空古代"
    
    # 写作标签 (用于引导写作风格)
    writing_tags: List[str] = field(default_factory=list)  # 标签名称列表，如 ["群像", "团宠"]
    
    # 核心组件
    world_settings: WorldSettings = field(default_factory=WorldSettings)
    characters: Dict[str, CharacterCard] = field(default_factory=dict)  # 角色字典
    plot_arcs: Dict[str, PlotArc] = field(default_factory=dict)  # 剧情弧字典
    chapter_outlines: Dict[int, ChapterOutline] = field(default_factory=dict)  # 章节大纲
    
    # 卷规划 (必须在生成章节大纲前完成)
    volume_plans: Dict[int, VolumePlan] = field(default_factory=dict)  # 卷号 -> VolumePlan
    
    # 【多线叙事结构 - 新增】
    subplots: Dict[str, Subplot] = field(default_factory=dict)  # 支线剧情 (支线ID -> Subplot)
    hidden_plotlines: Dict[str, HiddenPlotline] = field(default_factory=dict)  # 暗线 (暗线ID -> HiddenPlotline)
    character_arcs: Dict[str, CharacterArc] = field(default_factory=dict)  # 人物弧光 (角色名 -> CharacterArc)
    
    # 【三幕九线 - 核心数据结构 (Fix #8)】
    narrative_lines: Dict[str, NarrativeLine] = field(default_factory=dict)  # 九条叙事线 (线ID -> NarrativeLine)
    
    # 伏笔与事件
    open_loops: Dict[str, OpenLoop] = field(default_factory=dict)  # 伏笔字典
    event_history: List[EventRecord] = field(default_factory=list)  # 事件历史
    
    # 卷总结与回顾
    volume_summaries: Dict[int, str] = field(default_factory=dict)  # 卷总结 (卷号 -> 总结)
    cumulative_review: str = ""  # 累计回顾 (最新的剧情一致性审查)
    
    # 主线骨架
    main_plot_summary: str = ""  # 主线概要
    ending: str = ""  # 结局
    # 等待生成的十条核心线 (Fix #10)
    ten_narrative_lines_summary: str = "" # 用于透传给每卷生成时的上下文
    
    major_turning_points: List[Dict[str, Any]] = field(default_factory=list)
    # 例如: [{"chapter": 50, "description": "主角师父被杀"}]
    
    # 当前进度
    current_chapter: int = 0  # 当前生成到第几章
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1  # 版本号
    
    def get_tags_guidance(self) -> str:
        """
        获取写作标签的引导文本
        
        Returns:
            格式化的标签引导文本
        """
        if not self.writing_tags:
            return ""
        
        guidance_parts = []
        for tag_name in self.writing_tags:
            if tag_name in PREDEFINED_TAGS:
                tag = PREDEFINED_TAGS[tag_name]
                guidance_parts.append(f"【{tag.name}】({tag.category}): {tag.guidance}")
        
        if guidance_parts:
            return "\n".join(guidance_parts)
        return ""
    
    def get_theme_constraints(self) -> Dict[str, Any]:
        """
        获取背景题材的约束规则，用于内容生成时的合规检查
        
        Returns:
            包含禁止元素、必须元素和写作引导的字典
        """
        if not self.background_theme:
            return {}
        
        if self.background_theme in PREDEFINED_THEMES:
            theme = PREDEFINED_THEMES[self.background_theme]
            return {
                "theme_name": theme.name,
                "category": theme.category,
                "era_description": theme.era_description,
                "technology_level": theme.technology_level,
                "magic_system": theme.magic_system,
                "social_structure": theme.social_structure,
                "forbidden_elements": theme.forbidden_elements,
                "required_elements": theme.required_elements,
                "writing_guidance": theme.writing_guidance,
                "keywords": theme.keywords
            }
        return {}
    
    def get_theme_guidance(self) -> str:
        """
        获取背景题材的写作引导文本
        
        Returns:
            格式化的背景题材引导文本
        """
        constraints = self.get_theme_constraints()
        if not constraints:
            return ""
        
        lines = [
            f"【背景题材: {constraints['theme_name']}】({constraints['category']})",
            f"时代背景: {constraints['era_description']}",
            f"科技水平: {constraints['technology_level']}",
            f"力量体系: {constraints['magic_system']}",
            f"社会结构: {constraints['social_structure']}",
            "",
            f"禁止元素: {', '.join(constraints['forbidden_elements'])}",
            f"必须元素: {', '.join(constraints['required_elements'])}",
            "",
            f"写作引导: {constraints['writing_guidance']}",
            f"常用关键词: {', '.join(constraints['keywords'])}"
        ]
        return "\n".join(lines)
    
    def add_character(self, character: CharacterCard):
        """添加角色"""
        self.characters[character.name] = character
        self.updated_at = datetime.now().isoformat()
    
    def get_character(self, name: str) -> Optional[CharacterCard]:
        """获取角色"""
        return self.characters.get(name)
    
    def add_event(self, event: EventRecord):
        """添加事件"""
        self.event_history.append(event)
        self.updated_at = datetime.now().isoformat()
    
    def add_open_loop(self, loop: OpenLoop):
        """添加伏笔"""
        self.open_loops[loop.loop_id] = loop
        self.updated_at = datetime.now().isoformat()
    
    def get_active_loops(self) -> List[OpenLoop]:
        """获取所有未关闭的伏笔"""
        return [loop for loop in self.open_loops.values() if loop.status == LoopStatus.OPEN]
    
    def get_overdue_loops(self) -> List[OpenLoop]:
        """获取所有超期的伏笔"""
        return [loop for loop in self.get_active_loops() if loop.is_overdue(self.current_chapter)]
    
    def add_chapter_outline(self, outline: ChapterOutline):
        """添加章节大纲"""
        self.chapter_outlines[outline.chapter_number] = outline
        self.current_chapter = max(self.current_chapter, outline.chapter_number)
        self.updated_at = datetime.now().isoformat()
    
    def get_recent_events(self, count: int = 10) -> List[EventRecord]:
        """获取最近的事件"""
        return self.event_history[-count:] if self.event_history else []
    
    def increment_version(self):
        """增加版本号"""
        self.version += 1
        self.updated_at = datetime.now().isoformat()
