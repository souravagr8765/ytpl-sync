import pytest
from unittest.mock import patch, MagicMock
from ytpl_sync.downloader import Downloader
from ytpl_sync.models import VideoStatus
from yt_dlp.utils import DownloadError

@pytest.fixture
def downloader():
    return Downloader(ffmpeg_path="ffmpeg", cookies_file=None)

@patch('yt_dlp.YoutubeDL')
async def test_download_success(mock_ytdl_class, downloader, sample_video):
    mock_ytdl = MagicMock()
    mock_ytdl.download.return_value = 0
    mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
    
    with patch('ytpl_sync.downloader.glob.glob', return_value=["test.mp4"]):
        with patch('ytpl_sync.downloader.os.path.basename', return_value="test.mp4"):
            with patch('ytpl_sync.downloader.os.path.getsize', return_value=100):
                video = downloader.download(sample_video, "/tmp", MagicMock(max_resolution=1080, prefer_format="webm"), "run1")
                assert video.status == VideoStatus.DOWNLOADED

async def test_download_skips_known_id(downloader, sample_video):
    sample_video.status = VideoStatus.UPLOADED.value
    # since it logs warning and returns instead of asserting now
    video = downloader.download(sample_video, "/tmp", MagicMock(max_resolution=1080, prefer_format="webm"), "run1")
    assert video.status == VideoStatus.UPLOADED.value

@patch('yt_dlp.YoutubeDL')
async def test_download_failure(mock_ytdl_class, downloader, sample_video):
    mock_ytdl = MagicMock()
    mock_ytdl.download.side_effect = DownloadError("HTTP Error")
    mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
    
    video = downloader.download(sample_video, "/tmp", MagicMock(max_resolution=1080, prefer_format="webm"), "run1")
        
    assert video.status == VideoStatus.FAILED
    assert video.failed_stage == "DOWNLOAD"
