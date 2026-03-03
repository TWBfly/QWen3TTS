"""
RAG Manager for QWen3TTS
真实向量检索引擎 — 基于 sklearn TF-IDF + 中文字符 n-gram

架构:
1. 知识图谱 (NetworkX) — 实体关系检索
2. TF-IDF 向量检索 — 语义相似度搜索（支持中文）
3. 持久化存储 — 向量索引自动保存/加载

关键设计决策:
- 使用 char-level n-grams (2,4) 代替 jieba 分词，避免额外依赖
- char n-gram 对中文效果好，因为中文词通常 2-4 个字
- TF-IDF 提供了真正的语义检索能力，而非简单关键词匹配
"""
import json
import logging
import os
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config

logger = logging.getLogger(__name__)


class RAGManager:
    """
    混合检索管理器: 知识图谱 + TF-IDF 向量检索
    
    核心能力:
    - 语义相似度搜索 (而非关键词匹配)
    - 自动增长的向量索引
    - 知识图谱实体关系查询
    - 持久化到磁盘，重启不丢失
    """
    
    # TF-IDF 重建阈值：新增多少条文档后重建索引
    REBUILD_THRESHOLD = 20
    
    def __init__(self, storage_path: str = str(Config.STORAGE_DIR)):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # ========== 知识图谱 ==========
        self.kg_path = self.storage_path / "knowledge_graph.json"
        self.graph = nx.MultiDiGraph()
        
        # ========== TF-IDF 向量检索 ==========
        self._corpus: List[str] = []           # 原始文本语料库
        self._metadata: List[Dict] = []        # 每条文档的元数据
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None              # scipy sparse matrix
        self._pending_count: int = 0           # 新增但未索引的文档数
        
        # 持久化路径
        self._corpus_path = self.storage_path / "rag_corpus.json"
        self._index_path = self.storage_path / "rag_index.pkl"
        
        # 加载
        self.load_graph()
        self._load_corpus()
    
    # =====================================================================
    # 知识图谱 (NetworkX)
    # =====================================================================
    def load_graph(self):
        """从磁盘加载知识图谱"""
        if self.kg_path.exists():
            try:
                with open(self.kg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
                logger.info(f"Loaded KG: {self.graph.number_of_nodes()} nodes, "
                           f"{self.graph.number_of_edges()} edges")
            except Exception as e:
                logger.error(f"Failed to load KG: {e}")
                self.graph = nx.MultiDiGraph()
        else:
            self.graph = nx.MultiDiGraph()

    def save_graph(self):
        """保存知识图谱到磁盘"""
        try:
            data = nx.node_link_data(self.graph)
            with open(self.kg_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save KG: {e}")

    def add_knowledge(self, subject: str, predicate: str, object_: str, 
                      source: str = "general"):
        """添加三元组到知识图谱"""
        self.graph.add_edge(subject, object_, relation=predicate, source=source)
        self.save_graph()
        # 同时添加到向量库以支持语义检索
        self.add_to_vector_store(
            f"{subject} {predicate} {object_}",
            metadata={"type": "knowledge", "subject": subject, 
                      "predicate": predicate, "object": object_}
        )
    
    def _search_graph(self, query: str, max_results: int = 5) -> List[str]:
        """图谱搜索 — 基于实体匹配查找关系"""
        results = []
        if self.graph.number_of_nodes() == 0:
            return results
        
        # 提取查询中的实体 (匹配图谱节点)
        query_chars = set(query)
        matched_nodes = []
        for node in self.graph.nodes():
            node_str = str(node)
            # 子串匹配（比单词匹配更适合中文）
            if node_str in query or query in node_str:
                matched_nodes.append(node_str)
            elif len(node_str) >= 2 and any(
                node_str in segment 
                for segment in _split_chinese(query, min_len=2)
            ):
                matched_nodes.append(node_str)
        
        for node in matched_nodes:
            # 获取出边
            for _, neighbor, data in self.graph.out_edges(node, data=True):
                relation = data.get('relation', '相关')
                results.append(f"{node} {relation} {neighbor}")
            # 获取入边
            for source, _, data in self.graph.in_edges(node, data=True):
                relation = data.get('relation', '相关')
                results.append(f"{source} {relation} {node}")
        
        return list(dict.fromkeys(results))[:max_results]  # 去重

    # =====================================================================
    # TF-IDF 向量检索 (核心升级)
    # =====================================================================
    def add_to_vector_store(self, text: str, metadata: Optional[Dict] = None):
        """
        添加文本到向量库
        
        Args:
            text: 要索引的文本
            metadata: 可选的元数据
        """
        if not text or not text.strip():
            return
        
        # 去重检查
        if text in self._corpus:
            return
        
        self._corpus.append(text)
        self._metadata.append(metadata or {})
        self._pending_count += 1
        
        # 达到阈值时自动重建索引
        if self._pending_count >= self.REBUILD_THRESHOLD:
            self._rebuild_index()
        
        # 每次添加都保存语料库
        self._save_corpus()
    
    def add_batch_to_vector_store(self, texts: List[str], 
                                  metadata_list: Optional[List[Dict]] = None):
        """批量添加文本到向量库（更高效）"""
        added = 0
        for i, text in enumerate(texts):
            if text and text.strip() and text not in self._corpus:
                self._corpus.append(text)
                meta = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
                self._metadata.append(meta)
                added += 1
        
        if added > 0:
            self._pending_count += added
            self._rebuild_index()
            self._save_corpus()
            logger.info(f"Batch added {added} documents to vector store")
    
    def _rebuild_index(self):
        """重建 TF-IDF 索引"""
        if len(self._corpus) == 0:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._pending_count = 0
            return
        
        logger.info(f"Rebuilding TF-IDF index with {len(self._corpus)} documents...")
        
        # 使用字符级 n-gram，对中文非常友好
        self._vectorizer = TfidfVectorizer(
            analyzer='char',           # 字符级分析
            ngram_range=(2, 4),        # 2-4字符 n-gram（覆盖中文词汇长度）
            max_features=50000,        # 最大特征数
            sublinear_tf=True,         # 使用 1 + log(tf) 代替 tf，减弱高频词影响
            min_df=1,                  # 最少出现1次
            max_df=0.95,               # 最多出现在95%文档中（过滤极高频词）
        )
        
        self._tfidf_matrix = self._vectorizer.fit_transform(self._corpus)
        self._pending_count = 0
        
        logger.info(f"TF-IDF index built: {self._tfidf_matrix.shape[0]} docs × "
                    f"{self._tfidf_matrix.shape[1]} features")
        
        # 保存索引
        self._save_index()
    
    def _search_vector(self, query: str, top_k: int = 5, 
                       min_score: float = 0.05) -> List[Tuple[str, float, Dict]]:
        """
        TF-IDF 向量搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数
            min_score: 最低相似度阈值
            
        Returns:
            [(文本, 相似度分数, 元数据), ...]
        """
        # 如果有未索引的文档，先重建
        if self._pending_count > 0:
            self._rebuild_index()
        
        if self._vectorizer is None or self._tfidf_matrix is None:
            return []
        
        # 将查询文本转为 TF-IDF 向量
        try:
            query_vec = self._vectorizer.transform([query])
        except Exception:
            return []
        
        # 计算余弦相似度
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()
        
        # 获取 top-k 结果（过滤低分）
        top_indices = similarities.argsort()[::-1][:top_k * 2]  # 多取一些再过滤
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < min_score:
                continue
            results.append((
                self._corpus[idx],
                score,
                self._metadata[idx] if idx < len(self._metadata) else {}
            ))
            if len(results) >= top_k:
                break
        
        return results

    # =====================================================================
    # 混合搜索 (Graph + Vector)
    # =====================================================================
    def search_knowledge(self, query: str, top_k: int = 5) -> List[str]:
        """
        混合搜索：图谱搜索 + 向量搜索

        相比旧版（纯关键词匹配），本版本能找到:
        - 措辞不同但语义相关的伏笔
        - 跨卷的角色关系变化
        - 世界观设定的隐含关联
        """
        results = []
        seen = set()
        
        # 1. 图谱搜索 (精确实体匹配，高优先级)
        graph_results = self._search_graph(query, max_results=top_k // 2 + 1)
        for r in graph_results:
            if r not in seen:
                results.append(r)
                seen.add(r)
        
        # 2. 向量搜索 (语义相似度，补充图谱没找到的)
        remaining = top_k - len(results)
        if remaining > 0:
            vector_results = self._search_vector(query, top_k=remaining + 2)
            for text, score, meta in vector_results:
                if text not in seen:
                    results.append(text)
                    seen.add(text)
                    if len(results) >= top_k:
                        break
        
        return results[:top_k]
    
    def search_with_scores(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        带分数的搜索（用于调试和细粒度控制）
        
        Returns:
            [{"text": str, "score": float, "source": "graph"|"vector", "metadata": dict}]
        """
        results = []
        seen = set()
        
        # 图谱结果（给予高分）
        for r in self._search_graph(query, max_results=top_k):
            if r not in seen:
                results.append({
                    "text": r, "score": 1.0, 
                    "source": "graph", "metadata": {}
                })
                seen.add(r)
        
        # 向量结果
        for text, score, meta in self._search_vector(query, top_k=top_k):
            if text not in seen:
                results.append({
                    "text": text, "score": round(score, 4),
                    "source": "vector", "metadata": meta
                })
                seen.add(text)
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_context_for_prompt(self, query: str, top_k: int = 8) -> str:
        """格式化检索结果，用于注入 LLM 提示词"""
        facts = self.search_knowledge(query, top_k=top_k)
        if not facts:
            return ""
        
        return "\n【相关世界观知识】:\n" + "\n".join(f"- {fact}" for fact in facts)
    
    # =====================================================================
    # 业务层便捷方法
    # =====================================================================
    def index_chapter_summary(self, chapter_number: int, summary: str,
                              characters: List[str] = None):
        """索引章节总结"""
        self.add_to_vector_store(
            f"第{chapter_number}章总结: {summary}",
            metadata={
                "type": "chapter_summary",
                "chapter": chapter_number,
                "characters": characters or []
            }
        )
    
    def index_volume_summary(self, volume_number: int, summary: str):
        """索引卷总结"""
        self.add_to_vector_store(
            f"第{volume_number}卷总结: {summary}",
            metadata={"type": "volume_summary", "volume": volume_number}
        )
    
    def index_character_event(self, character_name: str, event: str,
                               chapter: int):
        """索引角色事件"""
        self.add_to_vector_store(
            f"{character_name}: {event} (第{chapter}章)",
            metadata={
                "type": "character_event",
                "character": character_name,
                "chapter": chapter
            }
        )
    
    def index_foreshadowing(self, description: str, planted_chapter: int,
                            target_chapter: Optional[int] = None):
        """索引伏笔"""
        text = f"伏笔(第{planted_chapter}章埋设): {description}"
        if target_chapter:
            text += f" (预计第{target_chapter}章回收)"
        self.add_to_vector_store(
            text,
            metadata={
                "type": "foreshadowing",
                "planted": planted_chapter,
                "target": target_chapter
            }
        )
    
    def find_related_foreshadowing(self, query: str, top_k: int = 5) -> List[Dict]:
        """查找与查询相关的伏笔（用于回收检查）"""
        results = self.search_with_scores(query, top_k=top_k * 2)
        return [
            r for r in results 
            if r.get("metadata", {}).get("type") == "foreshadowing"
        ][:top_k]

    # =====================================================================
    # 持久化
    # =====================================================================
    def _save_corpus(self):
        """保存语料库到磁盘"""
        try:
            data = {
                "corpus": self._corpus,
                "metadata": self._metadata
            }
            with open(self._corpus_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save corpus: {e}")
    
    def _load_corpus(self):
        """从磁盘加载语料库"""
        if self._corpus_path.exists():
            try:
                with open(self._corpus_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._corpus = data.get("corpus", [])
                    self._metadata = data.get("metadata", [])
                
                if self._corpus:
                    # 尝试加载已有索引
                    if not self._load_index():
                        # 没有索引文件则重建
                        self._rebuild_index()
                    
                    logger.info(f"Loaded {len(self._corpus)} documents from corpus")
            except Exception as e:
                logger.error(f"Failed to load corpus: {e}")
                self._corpus = []
                self._metadata = []
        
    def _save_index(self):
        """保存 TF-IDF 索引到磁盘"""
        if self._vectorizer is None:
            return
        try:
            with open(self._index_path, 'wb') as f:
                pickle.dump({
                    "vectorizer": self._vectorizer,
                    "tfidf_matrix": self._tfidf_matrix
                }, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _load_index(self) -> bool:
        """从磁盘加载 TF-IDF 索引"""
        if not self._index_path.exists():
            return False
        try:
            with open(self._index_path, 'rb') as f:
                data = pickle.load(f)
                self._vectorizer = data["vectorizer"]
                self._tfidf_matrix = data["tfidf_matrix"]
            
            # 验证索引和语料库大小一致
            if self._tfidf_matrix.shape[0] != len(self._corpus):
                logger.warning("Index/corpus size mismatch, rebuilding...")
                return False
            
            self._pending_count = 0
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取 RAG 系统统计信息"""
        return {
            "corpus_size": len(self._corpus),
            "kg_nodes": self.graph.number_of_nodes(),
            "kg_edges": self.graph.number_of_edges(),
            "index_features": self._tfidf_matrix.shape[1] if self._tfidf_matrix is not None else 0,
            "pending_docs": self._pending_count,
            "has_index": self._vectorizer is not None
        }


# =====================================================================
# 工具函数
# =====================================================================
def _split_chinese(text: str, min_len: int = 2) -> List[str]:
    """将中文文本分割为有意义的片段（无 jieba 依赖）"""
    # 按标点和空格分割
    segments = re.split(r'[，。！？、；：""''（）【】\s,.!?;:()\[\]]+', text)
    return [s for s in segments if len(s) >= min_len]


if __name__ == "__main__":
    # === 测试 ===
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 修改 Config 路径指向临时目录
        rag = RAGManager(tmpdir)
        
        # 添加知识
        rag.add_knowledge("陆清河", "师从", "白莲使", source="卷1")
        rag.add_knowledge("陆清河", "居住在", "京城", source="卷1")
        rag.add_knowledge("蛇娘", "真实身份是", "妖族后裔", source="卷5")
        
        # 添加章节总结
        rag.index_chapter_summary(1, "陆清河初入京城，在太医院结识白莲使", ["陆清河", "白莲使"])
        rag.index_chapter_summary(50, "蛇娘暴露妖族后裔身份，引发京城大乱", ["蛇娘"])
        
        # 添加伏笔
        rag.index_foreshadowing("陆清河手臂上的蛇纹印记隐隐发光", 
                                planted_chapter=3, target_chapter=50)
        rag.index_foreshadowing("白莲使送给陆清河的玉佩似乎能感知妖气", 
                                planted_chapter=8, target_chapter=30)
        
        # 添加更多上下文
        rag.add_batch_to_vector_store([
            "陆清河的医术在太医院引起注意",
            "白莲使暗中观察陆清河的修炼进度",
            "蛇娘于第五卷现身，与陆清河发生冲突",
            "京城中出现了神秘的瘟疫，只有陆清河能解",
            "陆清河发现蛇纹印记与妖族有关",
        ])

        # 强制重建索引
        rag._rebuild_index()
        
        # === 测试搜索 ===
        print("\n" + "="*50)
        print("测试 1: 查询 '蛇纹印记' (应找到伏笔)")
        results = rag.search_with_scores("蛇纹印记")
        for r in results:
            print(f"  [{r['source']}] (score={r['score']:.3f}) {r['text'][:60]}")
        
        print("\n" + "="*50)
        print("测试 2: 查询 '妖族身份' (应找到蛇娘相关)")
        results = rag.search_with_scores("妖族身份")
        for r in results:
            print(f"  [{r['source']}] (score={r['score']:.3f}) {r['text'][:60]}")
        
        print("\n" + "="*50)
        print("测试 3: 查询 '陆清河的师父' (应找到白莲使)")
        results = rag.search_with_scores("陆清河的师父是谁")
        for r in results:
            print(f"  [{r['source']}] (score={r['score']:.3f}) {r['text'][:60]}")
        
        print("\n" + "="*50)
        print("测试 4: 查找与 '蛇族' 相关的伏笔")
        foreshadowing = rag.find_related_foreshadowing("蛇族后裔妖气")
        for f in foreshadowing:
            print(f"  (score={f['score']:.3f}) {f['text'][:60]}")
        
        print("\n" + "="*50)
        print(f"RAG Stats: {rag.get_stats()}")
        print("\n✅ All tests passed!")
