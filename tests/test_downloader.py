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
                video_meta = {"video_id": "1", "url": "url"}
                video = downloader.download(video_meta, "/tmp", MagicMock(max_resolution=1080, prefer_format="webm"), "run1")
                assert video.status == VideoStatus.DOWNLOADED

async def test_download_skips_known_id(downloader, sample_video):
    video_meta = {"video_id": "1", "url": "url", "status": VideoStatus.UPLOADED.value}
    
    with pytest.raises(AssertionError):
        downloader.download(video_meta, "/tmp", MagicMock(max_resolution=1080, prefer_format="webm"), "run1")

@patch('yt_dlp.YoutubeDL')
async def test_download_failure(mock_ytdl_class, downloader, sample_video):
    mock_ytdl = MagicMock()
    mock_ytdl.download.side_effect = DownloadError("HTTP Error")
    mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
    
    video_meta = {"video_id": "1", "url": "url"}
    video = downloader.download(video_meta, "/tmp", MagicMock(max_resolution=1080, prefer_format="webm"), "run1")
        
    assert video.status == VideoStatus.FAILED
    assert video.failed_stage == "DOWNLOAD"
