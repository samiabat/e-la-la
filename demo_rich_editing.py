#!/usr/bin/env python3
"""
Demonstration script to showcase rich editing capabilities.
Creates a test video with multiple people and shows the different effects applied.
"""

import os
import sys
import tempfile
import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edit.rich_effects import detect_people_segments, plan_rich_effects, apply_rich_edits


def create_demo_video(output_path: str, duration: int = 40, fps: int = 30):
    """Create a demo video that simulates a conversation with multiple people."""
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    avi_path = output_path.replace('.mp4', '.avi')
    out = cv2.VideoWriter(avi_path, fourcc, fps, (1280, 720))
    
    total_frames = duration * fps
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    for frame_num in range(total_frames):
        # Create a frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Add background gradient
        for y in range(720):
            color_val = int(30 + (y / 720) * 50)
            frame[y, :] = (color_val, color_val // 2, color_val // 3)
        
        time_ratio = frame_num / total_frames
        time_sec = time_ratio * duration
        
        # Scene 1: Single person (0-10 seconds)
        if time_sec < 10:
            # Single person speaking (center)
            x1 = int(500 + 50 * np.sin(time_ratio * 8 * np.pi))
            y1 = int(200 + 20 * np.cos(time_ratio * 6 * np.pi))
            cv2.rectangle(frame, (x1, y1), (x1 + 160, y1 + 250), (120, 180, 220), -1)
            cv2.putText(frame, "Single Speaker", (x1, y1-10), font, 0.7, (255, 255, 255), 2)
            
        # Scene 2: Two people conversation (10-25 seconds)
        elif time_sec < 25:
            # Person 1 (left side)
            x1 = int(200 + 60 * np.sin((time_ratio - 0.25) * 6 * np.pi))
            y1 = int(180 + 30 * np.cos((time_ratio - 0.25) * 4 * np.pi))
            cv2.rectangle(frame, (x1, y1), (x1 + 140, y1 + 220), (100, 150, 200), -1)
            cv2.putText(frame, "Person A", (x1, y1-10), font, 0.6, (255, 255, 255), 2)
            
            # Person 2 (right side)
            x2 = int(850 + 50 * np.cos((time_ratio - 0.25) * 5 * np.pi))
            y2 = int(160 + 40 * np.sin((time_ratio - 0.25) * 3 * np.pi))
            cv2.rectangle(frame, (x2, y2), (x2 + 120, y2 + 200), (200, 120, 150), -1)
            cv2.putText(frame, "Person B", (x2, y2-10), font, 0.6, (255, 255, 255), 2)
            
        # Scene 3: Group scene with 3 people (25-35 seconds)
        elif time_sec < 35:
            # Person 1 (left)
            x1 = int(150 + 30 * np.sin((time_ratio - 0.625) * 4 * np.pi))
            y1 = int(200 + 20 * np.cos((time_ratio - 0.625) * 3 * np.pi))
            cv2.rectangle(frame, (x1, y1), (x1 + 100, y1 + 180), (100, 150, 200), -1)
            cv2.putText(frame, "A", (x1+30, y1-10), font, 0.5, (255, 255, 255), 2)
            
            # Person 2 (center)
            x2 = int(540 + 40 * np.cos((time_ratio - 0.625) * 3 * np.pi))
            y2 = int(180 + 25 * np.sin((time_ratio - 0.625) * 5 * np.pi))
            cv2.rectangle(frame, (x2, y2), (x2 + 120, y2 + 200), (150, 200, 100), -1)
            cv2.putText(frame, "B", (x2+40, y2-10), font, 0.5, (255, 255, 255), 2)
            
            # Person 3 (right)
            x3 = int(950 + 35 * np.sin((time_ratio - 0.625) * 6 * np.pi))
            y3 = int(190 + 30 * np.cos((time_ratio - 0.625) * 4 * np.pi))
            cv2.rectangle(frame, (x3, y3), (x3 + 110, y3 + 190), (200, 100, 150), -1)
            cv2.putText(frame, "C", (x3+40, y3-10), font, 0.5, (255, 255, 255), 2)
            
        # Scene 4: Return to single person (35-40 seconds)
        else:
            # Single person again (different position)
            x1 = int(450 + 80 * np.sin((time_ratio - 0.875) * 10 * np.pi))
            y1 = int(150 + 40 * np.cos((time_ratio - 0.875) * 8 * np.pi))
            cv2.rectangle(frame, (x1, y1), (x1 + 180, y1 + 270), (180, 120, 200), -1)
            cv2.putText(frame, "Final Speaker", (x1, y1-10), font, 0.7, (255, 255, 255), 2)
        
        # Add timestamp
        cv2.putText(frame, f"Time: {time_sec:.1f}s", (20, 50), font, 0.8, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    
    # Convert to MP4 using ffmpeg
    import subprocess
    result = subprocess.run([
        'ffmpeg', '-y', '-i', avi_path, 
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        output_path
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        return False
    
    # Remove temporary AVI file
    os.remove(avi_path)
    print(f"Demo video created: {output_path}")
    return True


def analyze_and_demonstrate(video_path: str):
    """Analyze the demo video and show what rich editing will do."""
    print("\n" + "="*60)
    print("RICH EDITING ANALYSIS AND DEMONSTRATION")
    print("="*60)
    
    # Get video duration
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps
    cap.release()
    
    print(f"Video duration: {duration:.1f} seconds")
    print(f"Video FPS: {fps}")
    
    # Detect people segments
    print("\n1. PEOPLE DETECTION:")
    print("-" * 30)
    segments = detect_people_segments(video_path, sample_interval=1.0)
    
    if not segments:
        print("   No people detected (may be due to simple test shapes)")
    else:
        for i, segment in enumerate(segments):
            print(f"   Segment {i+1}: {segment.start_sec:.1f}s - {segment.end_sec:.1f}s")
            print(f"      People count: {segment.person_count}")
            print(f"      Confidence: {segment.confidence:.2f}")
    
    # Plan effects
    print("\n2. EFFECT PLANNING:")
    print("-" * 30)
    effects = plan_rich_effects(video_path, duration, segments)
    
    for i, effect in enumerate(effects):
        print(f"   Effect {i+1}: {effect.start_sec:.1f}s - {effect.end_sec:.1f}s")
        print(f"      Type: {effect.effect_type}")
        print(f"      Parameters: {effect.params}")
        
        # Explain what this effect does
        if effect.effect_type == 'zoom_in':
            focus = effect.params.get('focus', 'center')
            scale = effect.params.get('target_scale', 1.2)
            print(f"      → Zooms to {scale:.1f}x focusing on {focus}")
        elif effect.effect_type == 'split_screen':
            orientation = effect.params.get('orientation', 'horizontal')
            print(f"      → Creates {orientation} split screen for multiple people")
        elif effect.effect_type == 'pan_left':
            print(f"      → Pans from right to left with zoom")
        elif effect.effect_type == 'pan_right':
            print(f"      → Pans from left to right with zoom")
        else:
            print(f"      → Standard full-frame view with transitions")
        print()
    
    return effects


def main():
    """Demonstrate rich editing capabilities."""
    print("RICH EDITING DEMONSTRATION")
    print("=" * 50)
    
    # Create temporary files
    temp_dir = tempfile.mkdtemp()
    demo_video_path = os.path.join(temp_dir, "demo_input.mp4")
    rich_output_path = os.path.join(temp_dir, "rich_output.mp4")
    
    try:
        # Create demo video
        print("Creating demonstration video...")
        if not create_demo_video(demo_video_path, duration=30):
            print("Failed to create demo video")
            return
        
        # Analyze the video
        effects = analyze_and_demonstrate(demo_video_path)
        
        # Apply rich editing
        print("\n3. APPLYING RICH EFFECTS:")
        print("-" * 30)
        print("Processing video with rich editing...")
        
        try:
            apply_rich_edits(demo_video_path, rich_output_path)
            
            if os.path.exists(rich_output_path):
                file_size = os.path.getsize(rich_output_path)
                print(f"✓ Rich editing completed successfully!")
                print(f"  Output file size: {file_size / 1024 / 1024:.2f} MB")
                
                print(f"\n4. RESULTS:")
                print("-" * 30)
                print(f"Original video: {demo_video_path}")
                print(f"Rich edited video: {rich_output_path}")
                print(f"Temporary directory: {temp_dir}")
                print(f"\nThe rich edited video now includes:")
                print(f"  • Dynamic zooms and crops optimized for mobile")
                print(f"  • Split screen effects for multi-person scenes")
                print(f"  • Smooth transitions between different effects")
                print(f"  • TikTok-optimized 1080x1920 vertical format")
                print(f"  • Enhanced engagement through varied visual dynamics")
                
            else:
                print("✗ Output file was not created")
                
        except Exception as e:
            print(f"✗ Rich editing failed with error: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\nFiles available for inspection in: {temp_dir}")
        print("(Files are left for manual review)")


if __name__ == "__main__":
    main()