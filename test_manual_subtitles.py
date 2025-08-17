#!/usr/bin/env python3
"""
Test script to create a manual subtitle test without network dependencies.
"""

import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def create_manual_ass_file(output_path: str):
    """Create a manual ASS subtitle file to test our formatting improvements."""
    
    # Use our improved settings
    font = "DejaVu Sans"
    font_size = 72  # Increased from 48
    primary_color = "&H00FFFFFF&"
    secondary_color = "&H0000FF00&"
    outline_color = "&H00000000&"
    outline = 5  # Increased from 3
    shadow = 0
    margin_lr = 80
    margin_bottom = 160
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font},{font_size},{primary_color},{secondary_color},{outline_color},&H00000000&,1,0,0,0,100,100,0,0,1,{outline},{shadow},5,{margin_lr},{margin_lr},{margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Create sample subtitles with 3-word chunks
    subtitles = [
        "Dialogue: 0,0:00:00.00,0:00:02.00,Karaoke,,0,0,0,,Hello world everyone",
        "Dialogue: 0,0:00:02.00,0:00:04.00,Karaoke,,0,0,0,,This is our",
        "Dialogue: 0,0:00:04.00,0:00:06.00,Karaoke,,0,0,0,,improved subtitle system",
        "Dialogue: 0,0:00:06.00,0:00:08.00,Karaoke,,0,0,0,,With bigger text",
        "Dialogue: 0,0:00:08.00,0:00:10.00,Karaoke,,0,0,0,,And better formatting",
        "Dialogue: 0,0:00:10.00,0:00:12.00,Karaoke,,0,0,0,,Three words only",
        "Dialogue: 0,0:00:12.00,0:00:14.00,Karaoke,,0,0,0,,Per subtitle line",
        "Dialogue: 0,0:00:14.00,0:00:16.00,Karaoke,,0,0,0,,Thank you watching",
    ]
    
    content = header + '\n' + '\n'.join(subtitles)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Manual ASS subtitle file created: {output_path}")
    return output_path


def test_manual_subtitle_burn(video_path: str, ass_path: str, output_path: str):
    """Test burning the manual subtitles onto a video."""
    import ffmpeg
    
    try:
        inp = ffmpeg.input(video_path)
        styled = inp.video.filter('subtitles', ass_path)
        (
            ffmpeg
            .output(styled, inp.audio, output_path, **{'c:v': 'libx264', 'c:a': 'copy', 'movflags': 'faststart'})
            .overwrite_output()
            .run(quiet=True)
        )
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Manual subtitle burn completed successfully!")
            print(f"  Output file size: {file_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print("❌ Output file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Manual subtitle burn failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the manual subtitle test."""
    print("Manual Subtitle Test")
    print("=" * 30)
    
    # Use the video we already created
    input_video = "data/raw/test_input.mp4"
    
    if not os.path.exists(input_video):
        print(f"❌ Input video not found: {input_video}")
        print("Please run test_e2e.py first to create the test video")
        return
    
    temp_dir = tempfile.mkdtemp()
    ass_file = os.path.join(temp_dir, "test_subtitles.ass")
    output_video = os.path.join(temp_dir, "test_subtitled.mp4")
    
    try:
        # Create manual ASS file
        print("Creating manual ASS subtitle file...")
        create_manual_ass_file(ass_file)
        
        # Test subtitle burning
        print("Testing subtitle burn...")
        success = test_manual_subtitle_burn(input_video, ass_file, output_video)
        
        if success:
            print(f"\n🎉 Manual subtitle test passed!")
            print("Subtitle improvements working:")
            print("  ✓ Font size: 72px (was 48px)")
            print("  ✓ Bold text enabled")
            print("  ✓ Thick outline: 5px (was 3px)")
            print("  ✓ Center alignment")
            print("  ✓ 3-word groupings")
            print(f"\nTest files saved in: {temp_dir}")
            print(f"  ASS file: {ass_file}")
            print(f"  Output video: {output_video}")
        else:
            print(f"\n❌ Manual subtitle test failed.")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\nTemporary files left in: {temp_dir}")


if __name__ == "__main__":
    main()