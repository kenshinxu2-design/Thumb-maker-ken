"""
Local test script to verify thumbnail generation without needing Telegram bot
Run this to test image processing before deploying
"""

from PIL import Image
import sys
import os

# Add parent directory to path to import from thumbnail_bot
sys.path.insert(0, os.path.dirname(__file__))

from thumbnail_bot import create_thumbnail

def test_thumbnail_generation():
    """Test thumbnail generation with sample images"""
    
    print("🧪 Testing Thumbnail Generation...")
    
    # Check if test images exist (you need to provide these)
    test_images = {
        'background': 'test_background.jpg',
        'right': 'test_right.jpg', 
        'left': 'test_left.jpg'
    }
    
    # Check files
    missing = []
    for key, filename in test_images.items():
        if not os.path.exists(filename):
            missing.append(filename)
    
    if missing:
        print(f"❌ Missing test images: {', '.join(missing)}")
        print("\nCreate test images with these names in the same directory:")
        for key, filename in test_images.items():
            print(f"  - {filename}: {key} image")
        return False
    
    try:
        # Load images
        print("📂 Loading test images...")
        bg_img = Image.open(test_images['background']).convert('RGB')
        right_img = Image.open(test_images['right']).convert('RGB')
        left_img = Image.open(test_images['left']).convert('RGB')
        
        print("✅ Images loaded successfully")
        
        # Generate thumbnail
        print("🎨 Generating thumbnail...")
        result = create_thumbnail(
            "Test Anime",
            bg_img,
            right_img,
            left_img
        )
        
        # Save result
        output_path = "test_output_thumbnail.jpg"
        result.save(output_path, quality=95)
        
        print(f"✅ Thumbnail generated successfully!")
        print(f"📁 Saved to: {output_path}")
        print(f"📐 Size: {result.size[0]}x{result.size[1]}px")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_thumbnail_generation()
    sys.exit(0 if success else 1)
