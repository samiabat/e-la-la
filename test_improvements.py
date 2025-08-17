#!/usr/bin/env python3
"""
Test script to validate subtitle and cropping improvements.
"""

import os
import sys
import tempfile
import subprocess

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edit.subtitles import burn_subtitles_karaoke
from src.edit.formatters import to_vertical


def create_test_video(output_path: str, duration: int = 10):
    """Create a simple test video with audio for subtitle testing."""
    # Create a simple video with some visual content and synthetic audio
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'testsrc2=duration={duration}:size=1280x720:rate=30',
        '-f', 'lavfi', '-i', f'sine=frequency=1000:duration={duration}',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Test video created: {output_path}")


def test_subtitle_improvements(input_path: str, output_path: str):
    """Test the improved subtitle functionality."""
    print("Testing improved subtitles (3 words at a time, bigger, bolder)...")
    
    try:
        burn_subtitles_karaoke(
            input_path, 
            output_path,
            font_size=72,  # Bigger text
            outline=5      # Thicker outline
        )
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ Subtitle test completed successfully!")
            print(f"  Output file size: {file_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print("✗ Subtitle output file was not created")
            return False
            
    except Exception as e:
        print(f"✗ Subtitle test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cropping_improvements(input_path: str, output_path: str):
    """Test the improved cropping functionality."""
    print("Testing improved cropping (content-aware, face detection)...")
    
    try:
        to_vertical(
            input_path,
            output_path,
            width=1080,
            height=1920
        )
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ Cropping test completed successfully!")
            print(f"  Output file size: {file_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print("✗ Cropping output file was not created")
            return False
            
    except Exception as e:
        print(f"✗ Cropping test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the improvement tests."""
    print("Subtitle and Cropping Improvement Test Suite")
    print("=" * 60)
    
    # Create temporary files
    temp_dir = tempfile.mkdtemp()
    test_video_path = os.path.join(temp_dir, "test_input.mp4")
    subtitle_output_path = os.path.join(temp_dir, "test_subtitles.mp4")
    cropping_output_path = os.path.join(temp_dir, "test_cropping.mp4")
    
    try:
        # Create test video
        print("Creating test video...")
        create_test_video(test_video_path, duration=10)
        
        # Test subtitle improvements
        subtitle_success = test_subtitle_improvements(test_video_path, subtitle_output_path)
        
        # Test cropping improvements
        cropping_success = test_cropping_improvements(test_video_path, cropping_output_path)
        
        if subtitle_success and cropping_success:
            print(f"\n🎉 All improvement tests passed!")
        else:
            print(f"\n❌ Some tests failed.")
            
        print(f"\nTest files saved in: {temp_dir}")
        print(f"You can review the results:")
        print(f"  Input: {test_video_path}")
        if subtitle_success:
            print(f"  Subtitles: {subtitle_output_path}")
        if cropping_success:
            print(f"  Cropping: {cropping_output_path}")
            
    except Exception as e:
        print(f"Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\nTemporary files left in: {temp_dir}")


if __name__ == "__main__":
    main()