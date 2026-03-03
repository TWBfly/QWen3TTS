"""
LLM 客户端 - 统一的 LLM API 调用接口
"""

import os
from typing import Optional, List, Dict, Any
from config import Config


class LLMClient:
    """LLM 客户端"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        初始化 LLM 客户端
        
        Args:
            provider: 提供商 (openai, anthropic, local)
            model: 模型名称
            api_key: API 密钥
            base_url: 基础 URL (用于本地模型)
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        self.provider = provider or Config.LLM_PROVIDER
        self.model = model or Config.LLM_MODEL
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.temperature = temperature if temperature is not None else Config.LLM_TEMPERATURE
        self.max_tokens = max_tokens or Config.LLM_MAX_TOKENS
        
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        if self.provider in ["openai", "local"]:
            try:
                from openai import OpenAI
                import httpx
                
                # Monkey patch to fix OpenAI client with newer httpx which removed 'proxies'
                if not hasattr(httpx.Client, 'proxies'):
                    class MockHttpxClient(httpx.Client):
                        def __init__(self, *args, **kwargs):
                            kwargs.pop('proxies', None)
                            super().__init__(*args, **kwargs)
                    http_client = MockHttpxClient()
                else:
                    http_client = httpx.Client()
                    
                self._client = OpenAI(
                    api_key=self.api_key if self.api_key else "dummy",
                    base_url=self.base_url,
                    http_client=http_client
                )
            except ImportError:
                raise ImportError("请安装 openai 库: pip install openai")
        
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            生成的文本
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens or self.max_tokens
        
        if self.provider in ["openai", "local"]:
            return self._generate_openai(prompt, system_prompt, temp, max_tok)
        elif self.provider == "anthropic":
            return self._generate_anthropic(prompt, system_prompt, temp, max_tok)
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """使用 OpenAI API 生成"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """使用 Anthropic API 生成"""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        生成 JSON 格式的响应（带重试机制）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_retries: 最大重试次数
            
        Returns:
            解析后的 JSON 对象
        """
        import json
        import re
        import time
        
        json_prompt = f"{prompt}\n\n请严格以 JSON 格式返回结果，不要包含任何其他文字。"
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.generate(json_prompt, system_prompt, temperature)
                return self._extract_json(response)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"  ⚠️ JSON 解析失败 (第{attempt+1}次), {wait_time}s 后重试... 错误: {str(e)[:100]}")
                time.sleep(wait_time)
                # 重试时降低温度以获得更稳定的输出
                temperature = max(0.1, (temperature or self.temperature) - 0.2)
        
        raise ValueError(f"JSON 解析在 {max_retries} 次重试后仍失败: {last_error}")
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON（多策略）"""
        import json
        import re
        
        # 策略 1: 直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # 策略 2: 提取 ```json ... ``` 代码块
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 策略 3: 第一个 { 到最后一个 }
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(response[start:end+1])
            except json.JSONDecodeError:
                pass
        
        # 策略 4: 提取 [ ... ] 数组格式
        start = response.find('[')
        end = response.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                arr = json.loads(response[start:end+1])
                return {"items": arr}  # Wrap in dict
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"无法从响应中提取 JSON: {response[:200]}...")


# 创建默认客户端实例
default_client = None

def get_default_client() -> LLMClient:
    """获取默认 LLM 客户端"""
    global default_client
    if default_client is None:
        default_client = LLMClient()
    return default_client
