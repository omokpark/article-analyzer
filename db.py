import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "articles.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """앱 시작 시 테이블 생성 (없으면)"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE,
                title       TEXT NOT NULL,
                summary     TEXT,
                category    TEXT,
                depth       TEXT,
                tags        TEXT DEFAULT '[]',
                created_at  TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)


def save_article(url: str, title: str, summary: str,
                 category: str, depth: str, tags: list) -> int:
    """아티클 저장 (중복 URL이면 업데이트). 저장된 id 반환."""
    tags_json = json.dumps(tags, ensure_ascii=False)
    with get_conn() as conn:
        cursor = conn.execute("""
            INSERT INTO articles (url, title, summary, category, depth, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title      = excluded.title,
                summary    = excluded.summary,
                category   = excluded.category,
                depth      = excluded.depth,
                tags       = excluded.tags,
                created_at = datetime('now', 'localtime')
            RETURNING id
        """, (url, title, summary, category, depth, tags_json))
        row = cursor.fetchone()
        return row[0]


def get_all_articles() -> list[dict]:
    """전체 아티클 조회 (최신순). tags는 리스트로 파싱."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, url, title, summary, category, depth, tags, created_at
            FROM articles
            ORDER BY created_at DESC
        """).fetchall()

    result = []
    for row in rows:
        a = dict(row)
        a["tags"] = json.loads(a["tags"])
        result.append(a)
    return result


def delete_article(article_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))


def compute_relations(articles: list[dict]) -> list[dict]:
    """태그/카테고리 기반 관계 계산. weight >= 1 인 엣지만 반환."""
    edges = []
    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            a, b = articles[i], articles[j]
            shared = list(set(a["tags"]) & set(b["tags"]))
            same_cat = bool(a["category"] and b["category"]
                            and a["category"] == b["category"])
            weight = len(shared) + (1 if same_cat else 0)
            if weight >= 1:
                edges.append({
                    "source": a["id"],
                    "target": b["id"],
                    "shared_tags": shared,
                    "same_category": same_cat,
                    "weight": weight,
                })
    return edges
