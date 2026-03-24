import pytest
from unittest.mock import patch, MagicMock
from ytpl_sync.encoder import Encoder
from ytpl_sync.models import VideoStatus

@pytest.fixture
def encoder(sample_config):
    db_manager = MagicMock()
    return Encoder(sample_config, db_manager)

@patch('ytpl_sync.utils.subprocess_runner.run_with_timeout')
async def test_encode_disabled_remux(mock_run, encoder, sample_video):
    encoder.config.encoding.enabled = False
    mock_run.return_value = (0, "success", "")
    
    with patch('ytpl_sync.encoder.Path.exists', return_value=True):
        with patch('ytpl_sync.encoder.Path.stat', return_value=MagicMock(st_size=100)):
            with patch('ytpl_sync.encoder.Path.unlink'):
                with patch('ytpl_sync.encoder.shutil.move'):
                    await encoder.encode_video(sample_video)
        
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "-c:v" in cmd and "copy" in cmd

@patch('ytpl_sync.utils.subprocess_runner.run_with_timeout')
async def test_encode_software(mock_run, encoder, sample_video):
    encoder.config.encoding.enabled = True
    encoder.config.encoding.encoder = "software"
    mock_run.return_value = (0, "success", "")
    
    with patch('ytpl_sync.encoder.Path.exists', return_value=True):
        with patch('ytpl_sync.encoder.Path.stat', return_value=MagicMock(st_size=100)):
            with patch('ytpl_sync.encoder.Path.unlink'):
                with patch('ytpl_sync.encoder.shutil.move'):
                    await encoder.encode_video(sample_video)
        
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "libx265" in cmd

@patch('ytpl_sync.utils.subprocess_runner.run_with_timeout')
async def test_encode_savings_calculated(mock_run, encoder, sample_video):
    encoder.config.encoding.enabled = True
    mock_run.return_value = (0, "success", "")
    
    with patch('ytpl_sync.encoder.Path.exists', return_value=True):
        with patch('ytpl_sync.encoder.Path.stat', side_effect=[
            MagicMock(st_size=200),
            MagicMock(st_size=100)
        ]):
            with patch('ytpl_sync.encoder.Path.unlink'):
                with patch('ytpl_sync.encoder.shutil.move'):
                    await encoder.encode_video(sample_video)
        
    assert sample_video.encoding_savings_pct == 50.0

@patch('ytpl_sync.utils.subprocess_runner.run_with_timeout')
async def test_encode_failure(mock_run, encoder, sample_video):
    encoder.config.encoding.enabled = True
    mock_run.return_value = (1, "", "error")
    
    with pytest.raises(Exception):
        await encoder.encode_video(sample_video)
        
    assert sample_video.status == VideoStatus.FAILED

