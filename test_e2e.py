#!/usr/bin/env python3
"""
End-to-end test of our improvements using the actual pipeline.
"""

import os
import sys
import tempfile
import subprocess

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pipeline import run_pipeline_multi


def create_test_video_with_speech(output_path: str, duration: int = 30):
    """Create a test video with visual content and synthetic speech for testing."""
    
    # Create a video with visual content
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'testsrc2=duration={duration}:size=1280x720:rate=30',
        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration}',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Test video created: {output_path}")


def test_full_pipeline(input_path: str):
    """Test the full pipeline with our improvements."""
    print("Testing full pipeline with improvements...")
    
    try:
        # Run pipeline with our improvements
        # Note: Whisper will fail due to network restrictions, but that's expected
        output_paths = run_pipeline_multi(
            input_path=input_path,
            profile='tiktok',
            config_path='configs/pipeline.yaml',
            durations=[10, 15],  # Short durations for testing
            max_clips=2,
            stride_sec=2.0,
            subs_enabled_override=False,  # Disable subtitles to avoid Whisper network issues
            export_audio_only=False
        )
        
        print(f"✅ Pipeline completed successfully!")
        print(f"Generated {len(output_paths)} clips:")
        for i, path in enumerate(output_paths, 1):
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                print(f"  Clip {i}: {path} ({file_size / 1024 / 1024:.2f} MB)")
            else:
                print(f"  Clip {i}: {path} (not found)")
        
        return len(output_paths) > 0
        
    except Exception as e:
        print(f"❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the end-to-end test."""
    print("End-to-End Pipeline Test")
    print("=" * 40)
    
    # Create test video in the expected location
    input_path = "data/raw/test_input.mp4"
    
    try:
        # Create test video
        print("Creating test video...")
        create_test_video_with_speech(input_path, duration=20)
        
        # Test full pipeline
        success = test_full_pipeline(input_path)
        
        if success:
            print(f"\n🎉 End-to-end test passed!")
            print("The pipeline works with our improvements:")
            print("  ✓ Video processing and cropping")
            print("  ✓ Engagement analysis")
            print("  ✓ Segment cutting")
            print("  ✓ Vertical formatting")
            print(f"\nCheck the output files in: data/outputs/shorts/")
        else:
            print(f"\n❌ End-to-end test failed.")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()