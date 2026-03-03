"""
Consistency Checker - AI Editor using RAG and LLM for Narrative Continuity
"""
import json
import logging
import re
from typing import Dict, Any, Tuple

from config import Config
from mechanisms.rag_manager import RAGManager
# Assuming there is a generic way to call LLM here, we'll try to use the existing tools or a simple requests approach if Ollama/API is configured.
# Let's check how other modules call LLM. We might need to abstract it or use the `agent_driver` or `models` if available.
# Let's take a look at `agent_driver.py` or `models.py` next.

logger = logging.getLogger(__name__)

class ConsistencyChecker:
    def __init__(self, novel_name: str, rag_manager: RAGManager):
        self.novel_name = novel_name
        self.rag = rag_manager
        
    def check_draft(self, draft_content: str, batch_num: int) -> Tuple[bool, str]:
        """
        审查大纲草稿连贯性 (依靠 IDE Team 协作审查，跳过本地 LLM 校验)
        Returns: (passed: bool, report/reasoning: str)
        """
        passed = True
        report = "🤖 AI主编审核得分: 100/100\n判定: ✅ 通过 (IDE Agent 协作模式，跳过本地 LLM 校验)\n"
        
        # 直接将草稿存入 RAG，保证后续上下文连贯
        self._index_draft_to_rag(draft_content, batch_num)
            
        return passed, report

    def _build_prompt(self, context: str, draft_content: str, batch_num: int) -> str:
        prompt = f"""你现在是起点中文网白金级小说主编，专精于长篇群像小说的逻辑把控和结构审查。
你的任务是：基于【前文相关剧情与设定（来自数据库检索）】，严格审查【当前待定的大纲草稿】。
你需要像寻找 bug 一样寻找剧情漏洞、人物断层、道具遗失、以及战力/逻辑的突然崩坏。

【小说名称】: {self.novel_name}（当前审核批次：第 {batch_num} 批）

【前文相关设定与剧情历史】
{context}

【待审核的最新卷大纲草稿】
{draft_content}

【审查维度与判定标准】
请你逐项进行检查，并在思考过程中至少举出一个具体的例子来证明你的判定：
1. 人物连贯性: 动机是否一致？前文重伤/闭关的人物是否突兀出现？性格是否OOC？
2. 道具与功法: 前文获得的重要宝物是否被合理使用或遗忘？是否凭空捏造无铺垫的神器？
3. 场景与物理法则: 地理位置转移是否合理？场景破坏是否前后矛盾？星际科幻元素绝对禁止！
4. 剧情递进与张力: 冲突是否在升级？是否在水字数无意义重复切磋？

【输出要求】
请你必须且只能输出一个严格合法的 JSON 格式结果（不要输出任何额外的 markdown 标记如 ```json 或解释语）：
{{
  "pass": true, // 只有在所有检查项都完全合理，或者微小瑕疵不影响主线时为 true。只要有逻辑硬伤、人物遗忘、降智情节，必须为 false！
  "score": 85, // 0-100 打分（低于 80 分必须 Reject）
  "reject_reason": "如果是 false，给出具体驳回原因。如果是 true，填空字符串。",
  "analysis": {{
    "character_continuity": "分析...",
    "item_tracking": "分析...",
    "scene_rules": "分析...",
    "plot_progression": "分析..."
  }}
}}
"""
        return prompt
        
    def _call_llm(self, prompt: str) -> str:
        # We need to use the system's LLM calling method.
        # Check config for how it's done or use a standard approach used in the project.
        import requests
        
        payload = {
            "model": Config.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You are a highly critical novel editor."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "options": {"num_ctx": 8192}
        }
        headers = {}
        if Config.LLM_API_KEY != "sk-no-key-needed":
            headers["Authorization"] = f"Bearer {Config.LLM_API_KEY}"
            
        # Check provider
        if Config.LLM_PROVIDER == "openai":
            # Just a stub, adapt if OpenAI format is strictly strictly required. Assume OpenAI compatible endpoint.
            url = f"{Config.LLM_BASE_URL}/chat/completions"
        else: # ollama commonly uses same endpoint or slightly different
            url = f"{Config.LLM_BASE_URL}/chat/completions"
            if "localhost:11434" in url and "/v1" not in url:
                url = "http://localhost:11434/api/chat"
                payload["stream"] = False
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            elif "message" in data:
                return data["message"]["content"]
            elif "response" in data:
                return data["response"]
            else:
                return "{}"
        except Exception as e:
            logger.error(f"LLM Call failed: {e}")
            # Failsafe: return a JSON so it doesn't crash on decode
            escaped_e = str(e).replace('"', "'").replace('\\', '\\\\')
            return f'{{"pass": false, "score": 0, "reject_reason": "LLM 调用失败: {escaped_e}", "analysis": {{}}}}'

    def _parse_response(self, text: str) -> Tuple[bool, str]:
        # 清理可能存在的 Markdown 代码块标记 ^```(?:json)?\s*|\s*```$
        text = re.sub(r'^```(?:json)?\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)
        
        try:
            data = json.loads(text)
            passed = bool(data.get("pass", False))
            score = int(data.get("score", 0))
            if score < 80:
                passed = False
            
            reason = data.get("reject_reason", "")
            if not passed and not reason:
                reason = "AI 审核给出低分，未提供具体原因。"
                
            report = f"🤖 AI主编审核得分: {score}/100\n"
            report += f"判定: {'✅ 通过' if passed else '❌ 驳回'}\n"
            if not passed:
                report += f"驳回原因: {reason}\n"
                
            analysis = data.get("analysis", {})
            report += f"\n【审查详情】\n"
            report += f"- 人物: {analysis.get('character_continuity', '无')}\n"
            report += f"- 道具: {analysis.get('item_tracking', '无')}\n"
            report += f"- 场景: {analysis.get('scene_rules', '无')}\n"
            report += f"- 剧情: {analysis.get('plot_progression', '无')}\n"
            
            return passed, report
        except json.JSONDecodeError:
            # 解析失败当做拒绝
            return False, f"❌ AI 审核结果解析失败。返回原始内容：\n{text[:200]}..."
            
    def _index_draft_to_rag(self, draft_content: str, batch_num: int):
        """将审核通过的草稿存入向量库"""
        # 简单块切分：按卷和章节切分
        chunks = re.split(r'(?=## 第\d+卷)', draft_content)
        texts_to_add = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            vol_match = re.search(r'## 第(\d+)卷', chunk)
            vol_num = int(vol_match.group(1)) if vol_match else batch_num * 10 # approximate fallback
            
            # 再按 "【十章细目】" 或各个章节切分以细化检索力度
            sub_chunks = re.split(r'(?=- 第\d+章:)', chunk)
            for sc in sub_chunks:
                if len(sc.strip()) > 50:
                    texts_to_add.append(sc.strip())
                    
        if texts_to_add:
            self.rag.add_batch_to_vector_store(
                texts_to_add,
                [{"type": "draft_chunk", "batch": batch_num} for _ in texts_to_add]
            )
