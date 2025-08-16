#!/usr/bin/env python3
"""
Simple test script to validate rich editing functionality.
Creates a test video and processes it through the rich editing pipeline.
"""

import os
import sys
import tempfile
import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edit.rich_effects import detect_people_segments, plan_rich_effects, apply_rich_edits


def create_test_video(output_path: str, duration: int = 30, fps: int = 30):
    """Create a simple test video with moving shapes to simulate people."""
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Use XVID codec
    out = cv2.VideoWriter(output_path.replace('.mp4', '.avi'), fourcc, fps, (1280, 720))  # Use AVI format
    
    total_frames = duration * fps
    
    for frame_num in range(total_frames):
        # Create a frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Add background color
        frame[:] = (50, 50, 50)
        
        # Simulate people with moving rectangles
        time_ratio = frame_num / total_frames
        
        # Person 1 (left side)
        x1 = int(200 + 100 * np.sin(time_ratio * 4 * np.pi))
        y1 = int(200 + 50 * np.cos(time_ratio * 2 * np.pi))
        cv2.rectangle(frame, (x1, y1), (x1 + 120, y1 + 200), (100, 150, 200), -1)
        
        # Person 2 (right side) - appears after 10 seconds
        if time_ratio > 0.33:
            x2 = int(800 + 80 * np.cos(time_ratio * 3 * np.pi))
            y2 = int(180 + 60 * np.sin(time_ratio * 1.5 * np.pi))
            cv2.rectangle(frame, (x2, y2), (x2 + 100, y2 + 180), (200, 100, 150), -1)
        
        out.write(frame)
    
    out.release()
    avi_path = output_path.replace('.mp4', '.avi')
    
    # Convert to MP4 using ffmpeg for better compatibility
    import subprocess
    subprocess.run([
        'ffmpeg', '-y', '-i', avi_path, 
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        output_path
    ], check=True, capture_output=True)
    
    # Remove temporary AVI file
    os.remove(avi_path)
    
    print(f"Test video created: {output_path}")


def test_people_detection(video_path: str):
    """Test the people detection functionality."""
    print("Testing people detection...")
    segments = detect_people_segments(video_path, sample_interval=1.0)
    
    print(f"Detected {len(segments)} person segments:")
    for i, segment in enumerate(segments):
        print(f"  Segment {i+1}: {segment.start_sec:.1f}s - {segment.end_sec:.1f}s, "
              f"{segment.person_count} people, confidence: {segment.confidence:.2f}")
    
    return segments


def test_effect_planning(video_path: str, segments):
    """Test the effect planning functionality."""
    print("\nTesting effect planning...")
    
    # Get video duration
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps
    cap.release()
    
    effects = plan_rich_effects(video_path, duration, segments)
    
    print(f"Planned {len(effects)} effects:")
    for i, effect in enumerate(effects):
        print(f"  Effect {i+1}: {effect.start_sec:.1f}s - {effect.end_sec:.1f}s, "
              f"type: {effect.effect_type}, params: {effect.params}")
    
    return effects


def test_rich_editing(input_path: str, output_path: str):
    """Test the full rich editing pipeline."""
    print(f"\nTesting rich editing pipeline...")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    
    try:
        apply_rich_edits(input_path, output_path)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ Rich editing completed successfully!")
            print(f"  Output file size: {file_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print("✗ Output file was not created")
            return False
            
    except Exception as e:
        print(f"✗ Rich editing failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the rich editing tests."""
    print("Rich Editing Test Suite")
    print("=" * 50)
    
    # Create temporary files
    temp_dir = tempfile.mkdtemp()
    test_video_path = os.path.join(temp_dir, "test_input.mp4")
    output_video_path = os.path.join(temp_dir, "test_output.mp4")
    
    try:
        # Create test video
        print("Creating test video...")
        create_test_video(test_video_path, duration=20)
        
        # Test people detection
        segments = test_people_detection(test_video_path)
        
        # Test effect planning
        effects = test_effect_planning(test_video_path, segments)
        
        # Test rich editing
        success = test_rich_editing(test_video_path, output_video_path)
        
        if success:
            print(f"\n🎉 All tests passed!")
            print(f"Test files saved in: {temp_dir}")
            print(f"You can review the results:")
            print(f"  Input: {test_video_path}")
            print(f"  Output: {output_video_path}")
        else:
            print(f"\n❌ Some tests failed.")
            
    except Exception as e:
        print(f"Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Note: Not cleaning up temp files so user can inspect results
        print(f"\nTemporary files left in: {temp_dir}")


if __name__ == "__main__":
    main()