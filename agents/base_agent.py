"""
Base Agent - 所有 Agent 的基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import LLMClient, get_default_client
from models import StoryBible


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(
        self,
        name: str,
        role: str,
        llm_client: Optional[LLMClient] = None,
        rag_manager: Optional[Any] = None,
        context_manager: Optional[Any] = None
    ):
        """
        初始化 Agent
        
        Args:
            name: Agent 名称
            role: Agent 角色描述
            llm_client: LLM 客户端
            rag_manager: RAG 管理器
            context_manager: 上下文管理器
        """
        self.name = name
        self.role = role
        self.llm_client = llm_client or get_default_client()
        self.rag_manager = rag_manager
        self.context_manager = context_manager
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        获取系统提示词
        
        Returns:
            系统提示词
        """
        pass
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            生成的文本
        """
        system_prompt = self.get_system_prompt()
        return self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def generate_json(
        self,
        prompt: str,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        生成 JSON 格式的响应
        
        Args:
            prompt: 用户提示词
            temperature: 温度参数
            
        Returns:
            解析后的 JSON 对象
        """
        system_prompt = self.get_system_prompt()
        return self.llm_client.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature
        )
    
    def log(self, message: str):
        """记录日志"""
        print(f"[{self.name}] {message}")
    
    @abstractmethod
    def process(self, bible: StoryBible, **kwargs) -> Any:
        """
        处理任务
        
        Args:
            bible: 故事圣经
            **kwargs: 其他参数
            
        Returns:
            处理结果
        """
        pass
