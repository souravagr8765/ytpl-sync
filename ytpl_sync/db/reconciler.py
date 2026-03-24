import logging
from ytpl_sync.models import Video
from .sqlite_backend import SQLiteBackend
from .neon_backend import NeonBackend

logger = logging.getLogger(__name__)

class Reconciler:
    async def run(self, sqlite: SQLiteBackend, neon: NeonBackend, dry_run: bool) -> dict:
        local_count = sqlite.count()
        local_max = sqlite.max_updated_at()
        
        neon_available = False
        neon_count = None
        neon_max = None
        
        try:
            neon_count = neon.count()
            neon_max = neon.max_updated_at()
            if neon_count is not None:
                neon_available = True
        except Exception:
            pass

        pulled_from_neon = 0
        pushed_to_neon = 0
        
        if neon_available and neon_max is not None and (local_max is None or neon_max > local_max):
            sync_baseline = local_max if local_max is not None else ""
            delta = neon.get_since(sync_baseline)
            if delta:
                pulled_from_neon = len(delta)
                if not dry_run:
                    sqlite.upsert_many(delta)
                logger.info(f"Pulled {pulled_from_neon} records from Neon into SQLite.")

        if neon_available and local_max is not None and (neon_max is None or local_max > neon_max):
            sync_baseline = neon_max if neon_max is not None else ""
            delta = sqlite.get_since(sync_baseline)
            if delta:
                pushed_to_neon = len(delta)
                if not dry_run:
                    neon.upsert_many(delta)
                logger.info(f"Pushed {pushed_to_neon} records from SQLite to Neon.")

        pending_synced = 0
        pending = sqlite.get_pending_neon_sync()
        if pending and neon_available:
            if not dry_run:
                success = neon.upsert_many(pending)
                if success:
                    for v in pending:
                        v.pending_neon_sync = False
                    sqlite.upsert_many(pending)
                    pending_synced = len(pending)
            else:
                pending_synced = len(pending)

        return {
            "neon_available": neon_available,
            "pulled_from_neon": pulled_from_neon,
            "pushed_to_neon": pushed_to_neon,
            "pending_synced": pending_synced,
        }
