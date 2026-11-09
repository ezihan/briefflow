import sqlite3
import json
from news_analyzer import NewsEvaluation

DB_NAME = "news_cache.db"

# ==========================================
# 1. テーブル作成（定义数据库表结构 Schema）
# ==========================================
def init_db():
    """データベースとテーブルを初期化する（存在しない場合のみ作成）"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # SQLのCREATE TABLE文：link（URL）を主キー（PRIMARY KEY）にして重複保存を防ぐ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            link TEXT PRIMARY KEY,
            title TEXT,
            published TEXT,
            importance_rank TEXT,
            summary_3lines TEXT,
            reason TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ==========================================
# 2. データ検索（SELECT：查一下这篇新闻是不是已经算过了）
# ==========================================
def get_cached_evaluation(link: str) -> NewsEvaluation | None:
    """URL(link)をキーにして、DBから過去のAI分析結果を取得する"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # SQLのSELECT文：プレースホルダ（?）を使ってSQLインジェクション攻撃を防ぐ
    cursor.execute(
        "SELECT importance_rank, summary_3lines, reason, category FROM articles WHERE link = ?",
        (link,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        # DBに見つかった場合、JSON文字列の3行要約をPythonのリストに戻して返す
        return NewsEvaluation(
            importance_rank=row[0],
            summary_3lines=json.loads(row[1]),
            reason=row[2],
            category=row[3]
        )
    return None

# ==========================================
# 3. データ保存（INSERT：把新算出来的AI结果存入硬盘）
# ==========================================
def save_evaluation_to_db(article: dict, evaluation: NewsEvaluation):
    """AIの分析結果をSQLデータベースに永続化する"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # SQLのINSERT文：リスト型のsummary_3linesはJSON文字列に変換して保存
    cursor.execute("""
        INSERT OR REPLACE INTO articles
        (link, title, published, importance_rank, summary_3lines, reason, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        article["link"],
        article["title"],
        article["published"],
        evaluation.importance_rank,
        json.dumps(evaluation.summary_3lines, ensure_ascii=False),
        evaluation.reason,
        evaluation.category
    ))
    conn.commit()
    conn.close()
