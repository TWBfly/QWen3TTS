"""
知识存储引擎 (Knowledge Store)
================================
基于 SQLite + TF-IDF 的跨小说叙事模式存储和检索系统。

表结构:
- patterns: 叙事模式（角色原型、剧情模式、关系动态、节奏模板）
- sources: 来源小说索引
- usage_log: 模式使用记录（用于质量评分进化）
"""

import sqlite3
import json
import os
import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# 模式类别常量
CATEGORY_ARCHETYPE = "archetype"       # 角色原型
CATEGORY_PLOT = "plot_pattern"         # 剧情模式
CATEGORY_RELATIONSHIP = "relationship" # 关系动态
CATEGORY_PACING = "pacing"            # 节奏模板

ALL_CATEGORIES = [CATEGORY_ARCHETYPE, CATEGORY_PLOT, CATEGORY_RELATIONSHIP, CATEGORY_PACING]

# 默认知识库路径
DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_data")


class KnowledgeStore:
    """
    跨小说知识存储引擎
    
    用法:
        store = KnowledgeStore()
        store.add_pattern("archetype", "嘴炮重情型主角", "表面嬉皮笑脸...", "大王饶命")
        results = store.search("底层逆袭的幽默主角")
    """

    def __init__(self, db_dir: str = DEFAULT_DB_DIR):
        """
        初始化知识存储。

        Args:
            db_dir: 数据库目录路径
        """
        self.db_dir = db_dir
        os.makedirs(db_dir, exist_ok=True)
        
        self.db_path = os.path.join(db_dir, "knowledge.db")
        self._conn = None
        self._init_db()
        
        # TF-IDF 索引
        self._vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=10000,
            sublinear_tf=True,
        )
        self._tfidf_matrix = None
        self._tfidf_ids = []     # 与矩阵行对应的 pattern_id
        self._tfidf_dirty = True  # 是否需要重建索引
        
        self._rebuild_tfidf_index()

    # =========================================================================
    # 数据库初始化
    # =========================================================================
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（线程安全）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn
    
    def _init_db(self):
        """创建数据库表"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                novel_dir TEXT,
                total_volumes INTEGER DEFAULT 0,
                analyzed_volumes INTEGER DEFAULT 0,
                analysis_status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                source_novel TEXT,
                source_volume INTEGER,
                tags TEXT DEFAULT '[]',
                quality_score REAL DEFAULT 5.0,
                use_count INTEGER DEFAULT 0,
                feedback_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                novel_name TEXT,
                score REAL,
                feedback TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (pattern_id) REFERENCES patterns(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category);
            CREATE INDEX IF NOT EXISTS idx_patterns_source ON patterns(source_novel);
            CREATE INDEX IF NOT EXISTS idx_patterns_score ON patterns(quality_score DESC);
        """)
        conn.commit()

    # =========================================================================
    # 写入操作
    # =========================================================================
    
    def register_source(self, name: str, novel_dir: str = "", total_volumes: int = 0) -> int:
        """注册来源小说"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO sources (name, novel_dir, total_volumes) VALUES (?, ?, ?)",
                (name, novel_dir, total_volumes)
            )
            conn.commit()
            return conn.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()[0]
        except sqlite3.IntegrityError:
            # 已存在，更新
            conn.execute(
                "UPDATE sources SET novel_dir=?, total_volumes=?, updated_at=datetime('now') WHERE name=?",
                (novel_dir, total_volumes, name)
            )
            conn.commit()
            return conn.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()[0]

    def update_source_progress(self, name: str, analyzed_volumes: int, status: str = "in_progress"):
        """更新分析进度"""
        conn = self._get_conn()
        conn.execute(
            "UPDATE sources SET analyzed_volumes=?, analysis_status=?, updated_at=datetime('now') WHERE name=?",
            (analyzed_volumes, status, name)
        )
        conn.commit()

    def add_pattern(
        self,
        category: str,
        name: str,
        description: str,
        source_novel: str = "",
        source_volume: int = 0,
        tags: List[str] = None,
    ) -> int:
        """
        添加一个叙事模式到知识库。
        
        Args:
            category: 类别 (archetype/plot_pattern/relationship/pacing)
            name: 模式名称
            description: 详细描述
            source_novel: 来源小说名
            source_volume: 来源卷号
            tags: 标签列表
            
        Returns:
            插入的 pattern_id
        """
        conn = self._get_conn()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        
        cursor = conn.execute(
            """INSERT INTO patterns 
               (category, name, description, source_novel, source_volume, tags)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (category, name, description, source_novel, source_volume, tags_json)
        )
        conn.commit()
        self._tfidf_dirty = True
        
        pattern_id = cursor.lastrowid
        logger.info(f"Added pattern #{pattern_id}: [{category}] {name} (from {source_novel})")
        return pattern_id

    def add_patterns_batch(self, patterns: List[Dict]) -> List[int]:
        """
        批量添加模式。
        
        Args:
            patterns: [{"category", "name", "description", "source_novel", "source_volume", "tags"}, ...]
        """
        conn = self._get_conn()
        ids = []
        for p in patterns:
            tags_json = json.dumps(p.get("tags", []), ensure_ascii=False)
            cursor = conn.execute(
                """INSERT INTO patterns 
                   (category, name, description, source_novel, source_volume, tags)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (p["category"], p["name"], p["description"],
                 p.get("source_novel", ""), p.get("source_volume", 0), tags_json)
            )
            ids.append(cursor.lastrowid)
        conn.commit()
        self._tfidf_dirty = True
        return ids

    # =========================================================================
    # 检索操作
    # =========================================================================

    def _rebuild_tfidf_index(self):
        """重建 TF-IDF 向量索引"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, description, tags FROM patterns"
        ).fetchall()
        
        if not rows:
            self._tfidf_matrix = None
            self._tfidf_ids = []
            self._tfidf_dirty = False
            return
        
        self._tfidf_ids = [row["id"] for row in rows]
        
        # 拼接 name + description + tags 作为文档
        documents = []
        for row in rows:
            tags = json.loads(row["tags"]) if row["tags"] else []
            doc = f"{row['name']} {row['description']} {' '.join(tags)}"
            documents.append(doc)
        
        try:
            self._tfidf_matrix = self._vectorizer.fit_transform(documents)
        except ValueError:
            self._tfidf_matrix = None
        
        self._tfidf_dirty = False

    def search(
        self,
        query: str,
        category: str = None,
        top_k: int = 5,
        min_score: float = 0.05,
    ) -> List[Dict]:
        """
        语义检索叙事模式。
        
        Args:
            query: 查询文本（如 "底层逆袭的幽默主角"）
            category: 可选，按类别过滤
            top_k: 返回数量
            min_score: 最低相似度
            
        Returns:
            [{"id", "category", "name", "description", "source_novel", 
              "quality_score", "similarity", "tags"}, ...]
        """
        if self._tfidf_dirty:
            self._rebuild_tfidf_index()
        
        if self._tfidf_matrix is None or len(self._tfidf_ids) == 0:
            return []
        
        # TF-IDF 检索
        try:
            query_vec = self._vectorizer.transform([query])
            scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()
        except (ValueError, Exception):
            return []
        
        # 排序
        top_indices = np.argsort(scores)[::-1]
        
        results = []
        conn = self._get_conn()
        
        for idx in top_indices:
            if len(results) >= top_k:
                break
            
            sim_score = scores[idx]
            
            # 无类别过滤时，低于阈值直接终止
            # 有类别过滤时，不能提前终止（高分的目标类别可能在后面）
            if sim_score < min_score:
                if not category:
                    break
                continue
            
            pattern_id = self._tfidf_ids[idx]
            row = conn.execute(
                "SELECT * FROM patterns WHERE id=?", (pattern_id,)
            ).fetchone()
            
            if row is None:
                continue
            
            # 类别过滤
            if category and row["category"] != category:
                continue
            
            results.append({
                "id": row["id"],
                "category": row["category"],
                "name": row["name"],
                "description": row["description"],
                "source_novel": row["source_novel"],
                "source_volume": row["source_volume"],
                "quality_score": row["quality_score"],
                "use_count": row["use_count"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "similarity": float(sim_score),
            })
        
        return results

    def get_top_patterns(
        self,
        category: str = None,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """按质量评分排序获取最优模式"""
        conn = self._get_conn()
        
        if category:
            rows = conn.execute(
                """SELECT * FROM patterns 
                   WHERE category=? AND quality_score>=?
                   ORDER BY quality_score DESC, use_count DESC
                   LIMIT ?""",
                (category, min_score, top_k)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM patterns 
                   WHERE quality_score>=?
                   ORDER BY quality_score DESC, use_count DESC
                   LIMIT ?""",
                (min_score, top_k)
            ).fetchall()
        
        return [dict(row) for row in rows]

    # =========================================================================
    # 反馈与进化
    # =========================================================================

    def record_usage(self, pattern_id: int, novel_name: str = ""):
        """记录模式使用"""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO usage_log (pattern_id, novel_name) VALUES (?, ?)",
            (pattern_id, novel_name)
        )
        conn.execute(
            "UPDATE patterns SET use_count = use_count + 1, updated_at=datetime('now') WHERE id=?",
            (pattern_id,)
        )
        conn.commit()

    def record_feedback(self, pattern_id: int, score: float, feedback: str = ""):
        """
        评分反馈 — 更新模式质量分数。
        
        采用增量平均：new_score = (old_score * count + new_score) / (count + 1)
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT quality_score, feedback_count FROM patterns WHERE id=?",
            (pattern_id,)
        ).fetchone()
        
        if not row:
            return
        
        old_score = row["quality_score"]
        count = row["feedback_count"]
        new_avg = (old_score * count + score) / (count + 1)
        
        conn.execute(
            """UPDATE patterns 
               SET quality_score=?, feedback_count=feedback_count+1, updated_at=datetime('now')
               WHERE id=?""",
            (round(new_avg, 2), pattern_id)
        )
        conn.execute(
            "INSERT INTO usage_log (pattern_id, score, feedback) VALUES (?, ?, ?)",
            (pattern_id, score, feedback)
        )
        conn.commit()

    # =========================================================================
    # 统计与管理
    # =========================================================================

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        conn = self._get_conn()
        
        total = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
        
        by_category = {}
        for cat in ALL_CATEGORIES:
            count = conn.execute(
                "SELECT COUNT(*) FROM patterns WHERE category=?", (cat,)
            ).fetchone()[0]
            by_category[cat] = count
        
        sources = conn.execute(
            "SELECT name, analyzed_volumes, total_volumes, analysis_status FROM sources"
        ).fetchall()
        
        avg_score = conn.execute(
            "SELECT AVG(quality_score) FROM patterns"
        ).fetchone()[0]
        
        return {
            "total_patterns": total,
            "by_category": by_category,
            "sources": [dict(s) for s in sources],
            "avg_quality_score": round(avg_score, 2) if avg_score else 0,
        }

    def get_patterns_by_source(self, source_novel: str) -> List[Dict]:
        """获取某本小说提取的所有模式"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM patterns WHERE source_novel=? ORDER BY category, id",
            (source_novel,)
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_source_patterns(self, source_novel: str):
        """删除某本小说的所有模式（用于重新分析）"""
        conn = self._get_conn()
        conn.execute("DELETE FROM patterns WHERE source_novel=?", (source_novel,))
        conn.execute("DELETE FROM sources WHERE name=?", (source_novel,))
        conn.commit()
        self._tfidf_dirty = True

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
