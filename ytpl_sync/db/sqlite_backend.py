import sqlite3
import json
import os
from typing import Optional
from datetime import datetime, timezone

from ytpl_sync.models import Video, VideoStatus

class SQLiteBackend:
    def __init__(self, db_path: str):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = None

    def connect(self) -> None:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")

    def initialize(self) -> None:
        if not self.conn:
            self.connect()
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            source_name TEXT,
            source_type TEXT,
            source_url TEXT,
            run_id TEXT,
            title TEXT,
            description TEXT,
            channel_name TEXT,
            channel_id TEXT,
            upload_date TEXT,
            duration_seconds INTEGER,
            view_count INTEGER,
            like_count INTEGER,
            thumbnail_url TEXT,
            tags TEXT,
            categories TEXT,
            youtube_url TEXT,
            status TEXT,
            failed_stage TEXT,
            failed_reason TEXT,
            retry_count INTEGER,
            deleted INTEGER,
            deleted_detected_at TEXT,
            original_filename TEXT,
            original_size_bytes INTEGER,
            final_filename TEXT,
            final_size_bytes INTEGER,
            encoding_savings_pct REAL,
            temp_path TEXT,
            local_path TEXT,
            rclone_remote TEXT,
            rclone_path TEXT,
            discovered_at TEXT,
            download_started_at TEXT,
            downloaded_at TEXT,
            encode_started_at TEXT,
            encoded_at TEXT,
            upload_started_at TEXT,
            uploaded_at TEXT,
            updated_at TEXT,
            pending_neon_sync INTEGER
        );
        """
        self.conn.execute(create_table_sql)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status_pending_sync ON videos (status, pending_neon_sync);")
        self.conn.commit()

    def _row_to_video(self, row: sqlite3.Row) -> Video:
        data = dict(row)
        if data.get('tags'):
            data['tags'] = json.loads(data['tags'])
        if data.get('categories'):
            data['categories'] = json.loads(data['categories'])
        
        data['deleted'] = bool(data['deleted'])
        data['pending_neon_sync'] = bool(data['pending_neon_sync'])
        
        return Video(**data)

    def _video_to_tuple(self, video: Video) -> tuple:
        video.updated_at = datetime.now(timezone.utc).isoformat()
        
        tags_json = json.dumps(video.tags) if video.tags is not None else None
        categories_json = json.dumps(video.categories) if video.categories is not None else None
        
        return (
            video.video_id, video.source_name, video.source_type, video.source_url, video.run_id,
            video.title, video.description, video.channel_name, video.channel_id, video.upload_date,
            video.duration_seconds, video.view_count, video.like_count, video.thumbnail_url,
            tags_json, categories_json, video.youtube_url, video.status, video.failed_stage,
            video.failed_reason, video.retry_count, int(video.deleted), video.deleted_detected_at,
            video.original_filename, video.original_size_bytes, video.final_filename, video.final_size_bytes,
            video.encoding_savings_pct, video.temp_path, video.local_path, video.rclone_remote,
            video.rclone_path, video.discovered_at, video.download_started_at, video.downloaded_at,
            video.encode_started_at, video.encoded_at, video.upload_started_at, video.uploaded_at,
            video.updated_at, int(video.pending_neon_sync)
        )

    def upsert(self, video: Video) -> None:
        sql = """
        INSERT OR REPLACE INTO videos (
            video_id, source_name, source_type, source_url, run_id, title, description, channel_name,
            channel_id, upload_date, duration_seconds, view_count, like_count, thumbnail_url, tags,
            categories, youtube_url, status, failed_stage, failed_reason, retry_count, deleted,
            deleted_detected_at, original_filename, original_size_bytes, final_filename, final_size_bytes,
            encoding_savings_pct, temp_path, local_path, rclone_remote, rclone_path, discovered_at,
            download_started_at, downloaded_at, encode_started_at, encoded_at, upload_started_at,
            uploaded_at, updated_at, pending_neon_sync
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        self.conn.execute(sql, self._video_to_tuple(video))
        self.conn.commit()

    def upsert_many(self, videos: list[Video]) -> None:
        if not videos:
            return
        sql = """
        INSERT OR REPLACE INTO videos (
            video_id, source_name, source_type, source_url, run_id, title, description, channel_name,
            channel_id, upload_date, duration_seconds, view_count, like_count, thumbnail_url, tags,
            categories, youtube_url, status, failed_stage, failed_reason, retry_count, deleted,
            deleted_detected_at, original_filename, original_size_bytes, final_filename, final_size_bytes,
            encoding_savings_pct, temp_path, local_path, rclone_remote, rclone_path, discovered_at,
            download_started_at, downloaded_at, encode_started_at, encoded_at, upload_started_at,
            uploaded_at, updated_at, pending_neon_sync
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        tuples = [self._video_to_tuple(v) for v in videos]
        self.conn.executemany(sql, tuples)
        self.conn.commit()

    def get(self, video_id: str) -> Optional[Video]:
        cur = self.conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))
        row = cur.fetchone()
        return self._row_to_video(row) if row else None

    def get_all(self) -> list[Video]:
        cur = self.conn.execute("SELECT * FROM videos")
        return [self._row_to_video(row) for row in cur.fetchall()]

    def get_by_status(self, *statuses: str) -> list[Video]:
        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        cur = self.conn.execute(f"SELECT * FROM videos WHERE status IN ({placeholders})", statuses)
        return [self._row_to_video(row) for row in cur.fetchall()]

    def get_pending_neon_sync(self) -> list[Video]:
        cur = self.conn.execute("SELECT * FROM videos WHERE pending_neon_sync = 1")
        return [self._row_to_video(row) for row in cur.fetchall()]

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM videos")
        return cur.fetchone()[0]

    def max_updated_at(self) -> Optional[str]:
        cur = self.conn.execute("SELECT MAX(updated_at) FROM videos")
        return cur.fetchone()[0]

    def get_since(self, updated_at: str) -> list[Video]:
        cur = self.conn.execute("SELECT * FROM videos WHERE updated_at > ?", (updated_at,))
        return [self._row_to_video(row) for row in cur.fetchall()]

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
