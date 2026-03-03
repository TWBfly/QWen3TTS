"""
The Stylist (Agent E) - 风格修辞师
职责：将通过验证的逻辑骨架转化为具有网文爽感的文字，处理防抄袭的最后一道工序（名词替换）。
"""

from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, ChapterOutline
from config import Config

class TheStylist(BaseAgent):
    """The Stylist - 风格修辞师"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="TheStylist",
            role="风格修辞师 - 负责润色与文风优化",
            llm_client=llm_client
        )
        
    def get_system_prompt(self) -> str:
        return """你是一位金牌网文主编兼修辞大师【风格修辞师】(The Stylist)。
你的职责是将干瘪的逻辑大纲，润色为【节奏明快】、【画面感强】、【代入感深】的简体中文网文细纲。

**核心任务**:
1.  **风格化**: 确保语言符合"神作"质感——沉稳、大气、不小白。
2.  **画面感**: 将"A打了B"转化为充满细节的动作和场景描写。
3.  **钩子强化**: 优化章节结尾，确保每一章都让人欲罢不能。
4.  **去AI味**: 消除翻译腔，使用接地气的中文表达。

**防抄袭机制**:
-   确保输出中不残留任何参考模版中的变量符号（如 {{Protagonist}}），全部替换为当前故事的正确名词。
"""

    def process(self, bible: StoryBible, **kwargs) -> Any:
        pass

    def polish_outline(self, outline_text: str, bible: StoryBible) -> str:
        """
        润色大纲文本
        """
        self.log("正在润色大纲...")
        
        tags = bible.get_tags_guidance()
        
        prompt = f"""请润色以下章节大纲，使其达到【出版级实体书】或【起点神作】的质量标准。

**原大纲**:
{outline_text}

**风格要求**:
{tags}
- 去除所有AI生成的机械感。
- 增强环境描写和心理描写的细腻度。
- 确保所有代词和变量都已正确替换为：主角={bible.characters['Protagonist'].name if 'Protagonist' in bible.characters else '主角'}。

**直接返回润色后的文本，无需JSON格式。**
"""
        return self.generate(prompt, temperature=0.7)
