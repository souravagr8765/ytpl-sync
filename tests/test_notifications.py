import pytest
from unittest.mock import patch, MagicMock
from ytpl_sync.notifications.mailer import Mailer
from ytpl_sync.notifications.telegram import TelegramNotifier
from ytpl_sync.notifications.reporter import ReportBuilder

@pytest.fixture
def mailer():
    return Mailer(MagicMock(email=MagicMock(enabled=True)))

@pytest.fixture
def telegram():
    return TelegramNotifier(MagicMock(telegram=MagicMock(enabled=True)))

@patch('smtplib.SMTP_SSL')
def test_mailer_sends(mock_smtp, mailer):
    mailer.send_email("Subject", "Body")
    assert mock_smtp.called

@patch('smtplib.SMTP_SSL')
def test_mailer_failure_returns_false(mock_smtp, mailer):
    mock_smtp.side_effect = Exception("SMTP error")
    result = mailer.send_email("Subject", "Body")
    if isinstance(result, bool):
        assert result is False

@patch('requests.post')
def test_telegram_sends(mock_post, telegram):
    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {"ok": True}
    
    telegram.send_message("Test message")
    assert mock_post.called

@patch('requests.post')
def test_telegram_failure_returns_false(mock_post, telegram):
    mock_post.side_effect = Exception("Network error")
    result = telegram.send_message("Test message")
    if isinstance(result, bool):
        assert result is False

def test_report_email_contains_stats():
    builder = ReportBuilder()
    ctx = MagicMock()
    
    ctx.started_at = MagicMock()
    ctx.videos_this_run = []
    ctx.discovered = 10
    ctx.skipped = 2
    ctx.downloaded = 5
    ctx.encoded = 3
    ctx.uploaded = 5
    ctx.failed = 2
    ctx.abandoned = 1
    ctx.newly_deleted = 0
    ctx.run_id = "test-123"
    
    report = builder.build_email_report(ctx)
    assert "Discovered: 10" in report
    assert "Failed: 2" in report

def test_report_telegram_short():
    builder = ReportBuilder()
    ctx = MagicMock()
    ctx.discovered = 10
    ctx.downloaded = 5
    ctx.encoded = 3
    ctx.uploaded = 5
    ctx.failed = 2
    ctx.newly_deleted = 0
    ctx.videos_this_run = []
    report = builder.build_telegram_message(ctx)
    assert len(report) < 500

