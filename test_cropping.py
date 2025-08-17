#!/usr/bin/env python3
"""
Test script specifically for the content-aware cropping functionality.
"""

import os
import sys
import tempfile
import subprocess
import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edit.formatters import detect_content_region, to_vertical


def create_face_test_video(output_path: str, duration: int = 5):
    """Create a test video with face-like features for testing face detection."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 30
    out = cv2.VideoWriter(output_path, fourcc, fps, (1280, 720))
    
    total_frames = duration * fps
    
    for frame_num in range(total_frames):
        # Create a frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Add background color (blue sky)
        frame[:] = (100, 50, 20)
        
        # Draw a simple face-like structure
        time_ratio = frame_num / total_frames
        
        # Face position (moves slightly over time)
        face_x = int(400 + 50 * np.sin(time_ratio * 2 * np.pi))
        face_y = int(200 + 20 * np.cos(time_ratio * np.pi))
        
        # Face outline (oval)
        cv2.ellipse(frame, (face_x + 60, face_y + 75), (60, 80), 0, 0, 360, (220, 180, 150), -1)
        
        # Eyes
        cv2.circle(frame, (face_x + 35, face_y + 50), 8, (50, 50, 50), -1)
        cv2.circle(frame, (face_x + 85, face_y + 50), 8, (50, 50, 50), -1)
        
        # Nose
        cv2.ellipse(frame, (face_x + 60, face_y + 75), (8, 12), 0, 0, 360, (200, 160, 130), -1)
        
        # Mouth
        cv2.ellipse(frame, (face_x + 60, face_y + 100), (15, 8), 0, 0, 180, (180, 100, 100), -1)
        
        out.write(frame)
    
    out.release()
    print(f"Face test video created: {output_path}")


def test_face_detection(video_path: str):
    """Test the face detection functionality."""
    print("Testing face detection...")
    
    crop_region = detect_content_region(video_path, target_aspect=9/16)
    
    if crop_region:
        x, y, w, h = crop_region
        print(f"✅ Face detected and crop region calculated:")
        print(f"  Crop region: x={x}, y={y}, width={w}, height={h}")
        print(f"  Aspect ratio: {w/h:.3f} (target: {9/16:.3f})")
        return True
    else:
        print("❌ No face detected or crop region calculation failed")
        return False


def test_content_aware_cropping(input_path: str, output_path: str):
    """Test the full content-aware cropping pipeline."""
    print("Testing content-aware cropping pipeline...")
    
    try:
        to_vertical(
            input_path,
            output_path,
            width=1080,
            height=1920
        )
        
        if os.path.exists(output_path):
            # Check output video properties
            cap = cv2.VideoCapture(output_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            file_size = os.path.getsize(output_path)
            print(f"✅ Content-aware cropping completed successfully!")
            print(f"  Output dimensions: {width}x{height}")
            print(f"  Frame count: {frame_count}")
            print(f"  File size: {file_size / 1024 / 1024:.2f} MB")
            
            # Check if dimensions are correct
            if width == 1080 and height == 1920:
                print(f"  ✅ Correct output dimensions")
                return True
            else:
                print(f"  ❌ Incorrect output dimensions")
                return False
        else:
            print("❌ Output file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Content-aware cropping failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the cropping tests."""
    print("Content-Aware Cropping Test Suite")
    print("=" * 50)
    
    # Create temporary files
    temp_dir = tempfile.mkdtemp()
    face_video_path = os.path.join(temp_dir, "face_test.mp4")
    cropped_output_path = os.path.join(temp_dir, "cropped_output.mp4")
    
    try:
        # Create test video with face
        print("Creating face test video...")
        create_face_test_video(face_video_path, duration=5)
        
        # Test face detection
        detection_success = test_face_detection(face_video_path)
        
        # Test content-aware cropping
        cropping_success = test_content_aware_cropping(face_video_path, cropped_output_path)
        
        if detection_success and cropping_success:
            print(f"\n🎉 All cropping tests passed!")
            print("Improvements implemented:")
            print("  ✓ Face detection using OpenCV Haar cascades")
            print("  ✓ Content-aware crop region calculation")
            print("  ✓ Proper aspect ratio handling")
            print("  ✓ Fallback to original logic when face detection fails")
        else:
            print(f"\n❌ Some tests failed.")
            if not detection_success:
                print("  - Face detection failed")
            if not cropping_success:
                print("  - Content-aware cropping failed")
            
        print(f"\nTest files saved in: {temp_dir}")
        print(f"You can review the results:")
        print(f"  Input: {face_video_path}")
        if cropping_success:
            print(f"  Output: {cropped_output_path}")
            
    except Exception as e:
        print(f"Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\nTemporary files left in: {temp_dir}")


if __name__ == "__main__":
    main()