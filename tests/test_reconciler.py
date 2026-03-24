import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from ytpl_sync.db.reconciler import Reconciler

@pytest.fixture
def mock_db_manager():
    manager = MagicMock()
    # local DB mocks
    manager.local.list_all_video_ids = MagicMock(return_value={"1", "2"})
    manager.local.get_video = MagicMock()
    manager.local.upsert_videos = MagicMock()
    
    # neon DB mocks
    manager.neon.list_all_video_ids = MagicMock(return_value={"1", "2", "3"})
    manager.neon.get_video = MagicMock()
    manager.neon.upsert_videos = MagicMock(return_value=True)
    manager.neon.connect = MagicMock(return_value=True)
    return manager

@pytest.mark.asyncio
async def test_pull_delta_from_neon(mock_db_manager):
    # neon has 30, local has 25
    mock_db_manager.neon.list_all_video_ids.return_value = {str(i) for i in range(30)}
    mock_db_manager.local.list_all_video_ids.return_value = {str(i) for i in range(25)}
    
    reconciler = Reconciler(mock_db_manager)
    await reconciler.reconcile()
    
    assert mock_db_manager.local.upsert_videos.called
    args, _ = mock_db_manager.local.upsert_videos.call_args
    assert len(args[0]) == 5

@pytest.mark.asyncio
async def test_push_delta_to_neon(mock_db_manager):
    mock_db_manager.neon.list_all_video_ids.return_value = {str(i) for i in range(20)}
    mock_db_manager.local.list_all_video_ids.return_value = {str(i) for i in range(25)}
    
    reconciler = Reconciler(mock_db_manager)
    await reconciler.reconcile()
    
    assert mock_db_manager.neon.upsert_videos.called
    args, _ = mock_db_manager.neon.upsert_videos.call_args
    assert len(args[0]) == 5

@pytest.mark.asyncio
async def test_both_remotes_down(mock_db_manager):
    mock_db_manager.neon.connect.return_value = False
    
    reconciler = Reconciler(mock_db_manager)
    await reconciler.reconcile()
    assert not mock_db_manager.neon.list_all_video_ids.called

@pytest.mark.asyncio
async def test_dry_run_no_writes(mock_db_manager):
    mock_db_manager.neon.list_all_video_ids.return_value = {str(i) for i in range(30)}
    mock_db_manager.local.list_all_video_ids.return_value = {str(i) for i in range(25)}
    
    reconciler = Reconciler(mock_db_manager)
    await reconciler.reconcile(dry_run=True)
    
    assert not mock_db_manager.local.upsert_videos.called
