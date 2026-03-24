import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ytpl_sync.models import Video, VideoStatus, FailedStage
from ytpl_sync.config import EncodingConfig
from ytpl_sync.utils.subprocess_runner import run_command

logger = logging.getLogger(__name__)

class Encoder:
    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path

    def encode(self, video: Video, encoding_config: EncodingConfig) -> Video:
        """
        Encodes a video using ffmpeg. Returns updated Video with status ENCODED or FAILED.
        Skips encoding if encoding_config.enabled is False - in that case just remux to MKV losslessly and return.
        """
        if not video.temp_path or not os.path.exists(video.temp_path):
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.ENCODE
            video.failed_reason = "Input file missing or temp_path not set"
            logger.error(f"Cannot encode {video.video_id}: {video.failed_reason}")
            return video

        input_path = Path(video.temp_path)
        tmp_output_path = input_path.with_suffix(".mkv.tmp")
        output_path = input_path.with_suffix(".mkv")

        if not encoding_config.enabled:
            # Lossless remux
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(input_path),
                "-c", "copy",
                "-map", "0:v:0",
                "-map", "0:a:0",
                "-map_metadata", "-1",
                str(tmp_output_path)
            ]

            video.status = VideoStatus.ENCODING
            video.encode_started_at = datetime.now(timezone.utc).isoformat()

            logger.info(f"Remuxing {input_path.name} to MKV without encoding.")
            returncode, stdout, stderr = run_command(cmd, f"Remux {video.video_id}", raise_on_error=False)

            if returncode == 0:
                os.replace(tmp_output_path, output_path)
                
                if input_path != output_path:
                    try:
                        os.remove(input_path)
                    except OSError as e:
                        logger.warning(f"Failed to delete original file {input_path}: {e}")

                video.final_filename = output_path.name
                video.final_size_bytes = output_path.stat().st_size
                video.encoded_at = datetime.now(timezone.utc).isoformat()
                video.status = VideoStatus.ENCODED
                # If there was an original size, we keep savings as None or 0.
            else:
                if tmp_output_path.exists():
                    tmp_output_path.unlink()
                video.status = VideoStatus.FAILED
                video.failed_stage = FailedStage.ENCODE
                video.failed_reason = stderr
                logger.error(f"Remux failed for {video.video_id}: {stderr}")
            return video

        # Encoding enabled
        encoder_map = {
            "software": "libx265",
            "nvenc": "hevc_nvenc",
            "vaapi": "hevc_vaapi",
            "videotoolbox": "hevc_videotoolbox"
        }
        encoder = encoder_map.get(encoding_config.encoder, "libx265")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-c:v", encoder
        ]

        if encoding_config.encoder == "software":
            cmd.extend(["-crf", str(encoding_config.crf), "-preset", encoding_config.preset])
        elif encoding_config.encoder == "nvenc":
            cmd.extend(["-qp", str(encoding_config.crf), "-preset", "quality"])
        else:
            # vaapi, videotoolbox
            cmd.extend(["-qp", str(encoding_config.crf)])

        cmd.extend([
            "-c:a", "libopus",
            "-b:a", encoding_config.audio_bitrate,
            "-map", "0:v:0",
            "-map", "0:a:0",
            "-map_metadata", "-1",
            str(tmp_output_path)
        ])

        video.status = VideoStatus.ENCODING
        video.encode_started_at = datetime.now(timezone.utc).isoformat()

        logger.info(f"Encoding {input_path.name} using {encoder}.")
        returncode, stdout, stderr = run_command(cmd, f"Encode {video.video_id}", raise_on_error=False)

        if returncode == 0:
            original_size = input_path.stat().st_size
            os.replace(tmp_output_path, output_path)
            
            if input_path != output_path:
                try:
                    os.remove(input_path)
                except OSError as e:
                    logger.warning(f"Failed to delete original file {input_path}: {e}")

            final_size = output_path.stat().st_size
            
            video.final_filename = output_path.name
            video.final_size_bytes = final_size
            video.encoded_at = datetime.now(timezone.utc).isoformat()
            video.status = VideoStatus.ENCODED

            if original_size > 0:
                savings_pct = (1 - (final_size / original_size)) * 100
                video.encoding_savings_pct = round(savings_pct, 1)
                logger.info(f"Encoding successful for {video.video_id}. Saved {video.encoding_savings_pct}%")
            else:
                video.encoding_savings_pct = 0.0
                logger.info(f"Encoding successful for {video.video_id}.")
        else:
            if tmp_output_path.exists():
                tmp_output_path.unlink()
            video.status = VideoStatus.FAILED
            video.failed_stage = FailedStage.ENCODE
            video.failed_reason = stderr
            logger.error(f"Encoding failed for {video.video_id}: {stderr}")

        return video
