"""
QWen3TTS Novel Generation System Config
"""

import os
from pathlib import Path


class Config:
    """系统配置"""
    
    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent
    
    # 数据存储根目录
    STORAGE_DIR = PROJECT_ROOT / "novel_data"
    
    # 移除全局的硬编码的 KG_PATH 和 VECTOR_DB_PATH
    # 这些现在将在 StorageManager/RAGManager 中基于具体小说的目录动态生成
    
    # LLM 配置 (默认 Local)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")  # Default to local
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-14b-chat") # Example local model
    LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-no-key-needed")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # Example Ollama URL
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192")) # Increased for longer context if possible
    
    # Agent 配置
    MAIN_AGENT_MODEL = os.getenv("MAIN_AGENT_MODEL", LLM_MODEL)
    SUB_AGENT_MODEL = os.getenv("SUB_AGENT_MODEL", LLM_MODEL)
    
    # 生成配置
    DEFAULT_TARGET_CHAPTERS = 1000 # 100 Volumes
    GENERATION_BATCH_SIZE = 10  # 每次生成多少章 (一卷)
    VOLUME_SIZE = 10  # 每一卷的章节数
    TOTAL_VOLUMES = 100
    
    # 伏笔配置
    DEFAULT_LOOP_TTL = 100  # 默认伏笔生存周期 (increased for long form)
    LOOP_WARNING_THRESHOLD = 0.8  # 超过 TTL 的 80% 时开始警告
    
    # 人物铺垫配置
    SHADOW_REGISTRY_MIN_MENTIONS = 5  # Increased for depth
    SHADOW_REGISTRY_MIN_CHAPTERS = 10  # Increased for slower pacing
    
    # 故事约束配置 (Strictly Enforced)
    FORBIDDEN_CONCEPTS = [
        # === 原有禁词 ===
        "科幻", "星际", "AI", "程序", "物理宇宙", "数据流", "锚点", 
        "外星人", "银河系", "宇宙", "时间旅行", "平行世界", "维度", "位面",
        "逻辑武器", "科幻修仙", "缸中之脑", "直播", "天道", "系统", "面板", "穿越者",
        "机械降神", "金手指", "空间戒指", "属性板",
        # === 星际/太空类 ===
        "星舰", "战舰", "飞船", "星球", "星区", "星域", "跃迁", "光年",
        "旗舰", "战堡", "歼星", "舰队", "舰长", "旗舰甲板",
        # === 高科技类 ===
        "机甲", "激光", "暗物质", "量子", "黑洞", "引擎", "机器人", "克隆",
        "纳米", "赛博", "虚拟现实", "全息", "电子", "芯片", "半机械",
        # === 高维/矩阵类 ===
        "高维", "低维", "天网", "矩阵", "熔炉", "休眠舱", "能量阀",
        "格式化", "主机", "覆写", "脉冲", "扫描仪",
        # === 具体违规实体 ===
        "利维坦", "清道夫", "守门人",
        # === 用户新增违禁词（末日/生化/科幻套皮） ===
        "深渊", "怪物", "变异", "生化", "生化兵工厂", "生化学者", "变异大军", "抗体",
        "深渊水晶", "深渊核心", "活尸", "生化关节", "高达", "机械炼狱", "齿轮核心",
        "克苏鲁", "异形", "渊主", "神明", "丧尸", "瓦斯", "水晶",
    ]
    
    # 角色名禁止模式（正则列表，用于校验角色名是否为真实人物）
    FORBIDDEN_CHARACTER_PATTERNS = [
        r"^(全|众|千万|大乾|帝国|敌方|远古).*(军民|学子|众生|高层|追兵|残余|近卫|骑士团)$",
        r"(军民|学子|众生|高层|追兵|残余)$",
        r"^(帝国|敌方|神族|皇家).*(将|帅|官|督|长|队)$",
        r"(AI|机甲|战堡|枢纽|残像|投影|沙虫|巨兽|主机|清道夫)",
        r"^幻境",
        r"^(彩蛋|复苏的|南方古)",
        r"^.+（遗体）$",
        r"^.+铜像$",
    ]
    
    # 叙事质量约束
    NARRATIVE_QUALITY_RULES = """
    【黄金三章 (Golden Opening)】
    前三章（第1-3章）是全书的生死线，必须在最短篇幅内完成以下任务：
    1. 第1章：必须在500字内抛出核心悬念或致命冲突，让读者无法放下。严禁从"主角出生"或"世界观介绍"开始，必须直接从矛盾高潮切入（in medias res）。
    2. 第2章：必须展示主角的独特能力或核心性格魅力，让读者产生认同感。同时埋下至少1个长线伏笔。
    3. 第3章：必须完成第一个小高潮，给读者一个明确的"爽点"或"情绪共鸣点"，同时引出更大的悬念作为钩子。
    黄金三章禁忌：严禁大段旁白、严禁冗长的世界观设定、严禁无关主角的路人视角、严禁"第一天上学/初入门派"的平淡开场。

    【叙事逻辑与伏笔呼应约束（严禁烂俗套路）】
    1. 核心冲突必须一以贯之、由小及大、由内而外逐步升级。绝不允许“倒V字”崩塌退回低级冲突（如解决灭世神明后又和地方县官斗智斗勇，这是逻辑死罪）。
    2. 军事与战略行动必须高度符合古代现实逻辑。严禁为了探险寻宝等副本行为放弃战略要冲。
    3. 拒绝任何不合理“机器降神”与“天降道具”（如天外陨铁、定海珠凭空出现），绝不允许用这种低劣方式满足主角需要。
    4. 严禁随意复活死去的角色（如被深渊等力量腐化复活等敷衍写法）。
    5. 严禁使用“主角武功尽失”、“失忆重开”、“坠崖被救”等刻意低劣的手法强行推进剧情，必须维持人物长线性格积累。
    6. 严禁使用“命运安排”、“巧合”、“天道”来解决困境。所有困境应对必须源于主动选择、利益交换或牺牲。
    7. 风格统一：必须保持背景风格统一，必须在一个纯粹架空古代下（权谋、门阀、军阀争霸），不可出现赛博科幻或者克苏鲁修仙。
    """
    
    # 多线叙事约束
    MULTI_THREAD_NARRATIVE_RULES = """
    【三幕九线写作手法】
    1. 必须明确九条叙事线（主线+支线+暗线），交织进行。
    2. 核心：人物推动剧情。每个人物都是主角，每个人物都有自己的故事线和高光时刻。
    3. 支线与主线必须有交汇点，形成因果呼应。
    4. 暗线的揭晓必须让读者恍然大悟："原来如此！"
    5. 反派没有绝对的恶，立意高远，都是为了自己认为正确的事情。
    """
    
    # 场景深耕约束
    SCENE_DEPTH_RULES = """
    【场景深耕与绝不乱跑地图约束（锁死核心地图）】
    1. 严禁像流水账一样频繁换地图打怪探险（如大漠挖陨铁、东海打海盗、昆仑山爆金币等网游跑图升级恶俗模式）。
    2. 必须把全部100卷的故事牢牢扎根在三个以上的固定核心板块（例如：暗流涌动的皇都大染缸、血肉磨坊的极寒边关、利益盘根错节的江南销金窟）。
    3. 通过深度挖掘这些固定核心阵地的经济规律、官场生态、民生百态、情报网交织来推动漫长的剧情。
    4. 场景中的生活细节（如街边小贩、家族斗争、老建筑）必须有社会派小说的高级伏笔价值。
    5. 离开一个场景前，所有角色关系必须有符合地缘政治和战略的明确结局交代。
    """
    
    # 战力天花板设定
    POWER_SCALING_RULES = """
    【战力天花板锁死约束（绝不修仙玄幻）】
    1. 明确1000章的战力上限，顶配武力只能是“百人敌”级别的武道大宗师。
    2. 严禁出现“冰封整个长江”、“一刀劈碎十丈古塔”、“一己之力对冲十万大军”、“手撕高达”、“物理意义上的弑神”等伪玄幻/高魔表现。
    3. 必须保留拳拳到肉、刀刀见血、需要配合军阵的武侠与冷兵器真实战争质感。
    4. 战力与格局绝不可产生断崖式的回退崩盘（不可出现刚开始毁天灭地战力，后来突然跟普通兵勇苦战的现象）。
    """
    
    # 叙事聚光灯约束 (Narrative Spotlight)
    NARRATIVE_SPOTLIGHT_RULES = """
    【叙事聚光灯约束】
    1. 每一卷（10章）只能聚焦于 2-3 条核心叙事线，其他线索挂起（Suspend）。
    2. 被挂起的线索必须在后台演进（Off-screen Evolution），并在下一卷通过侧面描写或传闻体现其变化。
    3. 严禁试图在单卷内面面俱到，导致流水账。
    4. 聚光灯切换时，必须有自然的过渡事件。
    """
    
    # 节奏控制与后期爆发约束 (The Escalating Crisis Engine)
    PACING_RULES = """
    【节奏与结构终极约束（龙头、猪肚、豹尾）】
    1. 必须始终维持极高的剧情张力，全程高能无尿点。严禁在任何阶段出现“大圆满后强行水日常”、“无压力的退休游历”或平淡的过渡卷。结尾20卷是收尾但绝非日常养老，必须是一场最为猛烈、不见硝烟的思想绞肉机或旧势力终极反扑！
    2. “三段式阶梯跃迁危机”机制：
       - 第1-30卷（龙头）：破局求生。面临生存危机与局部势力压迫，重点在于悬念铺设、世界观展开。
       - 第31-80卷（猪肚）：体系颠覆。危机必须从个人恩怨跃迁为阵营对抗或世界观法则解密。多线交织，群像高潮不断爆发，开始消耗核心伏笔。反派必须是庞大旧体系的代言人。
       - 第81-100卷（豹尾）：信仰/法则坍塌与重构。外部明面强敌崩溃后，最大的阻碍必须来源于内部（同伴背叛、路线之争、新旧势力的利益反扑），或是法则本身的坍塌。必须引入“理念的不可调和”。
    3. 终极思想博弈：在最后三卷（98-100卷），主角必须面临残酷的两难困境或“深渊检测”（屠龙者终成恶龙的诱惑），大结局必须是一场惨烈但伟大的“思想飞升”和体系彻底解构，而非单纯的打赢Boss开香槟。
    4. 伏笔连环引爆器：世界观核心之谜等核心大伏笔，必须在第80卷之后才能彻底揭晓，在最后20卷连环引爆，每一次解密都必须伴随认知颠覆与巨大代价。
    5. 配角牺牲与高光闭环：后期决战阶段，重要配角绝不能沦为看客或随从，他们必须为了各自的“道（理念）”做出极限选择，甚至牺牲。每10卷必须有至少一个重量级角色完成其命运的凄美闭环。
    6. 章节密度阈值校验：任何10章（1卷）内，必须发生至少1次重大势力更迭、1次生死存亡的转折、或者1次核心伏笔的重磅抛出/致命回收。严禁连篇累牍的宴会、赶路、回忆、无意义的闲聊切磋。
    """
    
    # 整合所有约束
    STORY_CONSTRAINTS = f"""
    【禁止概念】: {', '.join(FORBIDDEN_CONCEPTS)}
    
    {NARRATIVE_QUALITY_RULES}
    {MULTI_THREAD_NARRATIVE_RULES}
    {SCENE_DEPTH_RULES}
    {POWER_SCALING_RULES}
    {NARRATIVE_SPOTLIGHT_RULES}
    {PACING_RULES}
    """
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = PROJECT_ROOT / "qwen3tts_novel.log"
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if cls.LLM_PROVIDER == "local" and not cls.LLM_BASE_URL:
             # Default is setup, so this might not raise, but good to check
             pass

    @classmethod
    def get_storage_manager(cls, story_name: str = None):
        """获取存储管理器实例,可指定小说名字以隔离数据"""
        from storage import StorageManager
        
        if story_name:
            # 去除可能非法的路径字符
            import re
            safe_name = re.sub(r'[\\/*?:"<>|]', "", story_name)
            target_dir = cls.STORAGE_DIR / safe_name
        else:
            target_dir = cls.STORAGE_DIR
            
        return StorageManager(str(target_dir))

# Config.validate()
