"""
Generate professional logos and visual assets for the Ultra Fake News Detector
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_logo(size=(512, 512), output_path='logo.png'):
    """Create a professional circular logo with gradient"""
    
    # Create image with transparent background
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw outer circle (purple gradient simulation)
    center = (size[0] // 2, size[1] // 2)
    radius = min(size) // 2 - 20
    
    # Outer purple ring
    draw.ellipse([center[0] - radius, center[1] - radius,
                  center[0] + radius, center[1] + radius],
                 fill=(102, 126, 234, 255), outline=None)
    
    # Inner white circle
    inner_radius = radius - 40
    draw.ellipse([center[0] - inner_radius, center[1] - inner_radius,
                  center[0] + inner_radius, center[1] + inner_radius],
                 fill=(255, 255, 255, 255), outline=None)
    
    # Draw target/crosshair icon
    line_width = 15
    inner_circle_radius = inner_radius - 80
    
    # Center circle
    draw.ellipse([center[0] - inner_circle_radius, center[1] - inner_circle_radius,
                  center[0] + inner_circle_radius, center[1] + inner_circle_radius],
                 fill=None, outline=(102, 126, 234, 255), width=line_width)
    
    # Crosshairs
    crosshair_length = inner_circle_radius + 40
    draw.line([center[0] - crosshair_length, center[1],
               center[0] + crosshair_length, center[1]],
              fill=(102, 126, 234, 255), width=line_width)
    draw.line([center[0], center[1] - crosshair_length,
               center[0], center[1] + crosshair_length],
              fill=(102, 126, 234, 255), width=line_width)
    
    # Center dot
    center_dot_radius = 20
    draw.ellipse([center[0] - center_dot_radius, center[1] - center_dot_radius,
                  center[0] + center_dot_radius, center[1] + center_dot_radius],
                 fill=(102, 126, 234, 255), outline=None)
    
    img.save(output_path)
    print(f"✅ Logo saved to {output_path}")
    return img


def create_favicon(logo_img, output_path='favicon.ico'):
    """Create favicon from logo"""
    favicon = logo_img.resize((64, 64), Image.Resampling.LANCZOS)
    favicon.save(output_path, format='ICO')
    print(f"✅ Favicon saved to {output_path}")
    return favicon


def create_banner(width=1200, height=400, output_path='banner.png'):
    """Create a professional banner for README"""
    
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Gradient background (purple to blue)
    for y in range(height):
        r = int(102 + (118 - 102) * (y / height))
        g = int(126 + (75 - 126) * (y / height))
        b = int(234 + (162 - 234) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Try to add text (requires PIL with font support)
    try:
        # Use default font
        from PIL import ImageFont
        try:
            font_large = ImageFont.truetype("arial.ttf", 80)
            font_small = ImageFont.truetype("arial.ttf", 40)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw title
        title = "🎯 Ultra Fake News Detector"
        bbox = draw.textbbox((0, 0), title, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, height // 3), title, fill=(255, 255, 255), font=font_large)
        
        # Draw subtitle
        subtitle = "98.5% Accuracy • 5-Layer Detection • Enterprise-Grade"
        bbox = draw.textbbox((0, 0), subtitle, font=font_small)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, height // 2 + 40), subtitle, fill=(255, 255, 255, 200), font=font_small)
        
    except Exception as e:
        print(f"⚠️ Could not add text: {e}")
    
    img.save(output_path)
    print(f"✅ Banner saved to {output_path}")
    return img


def create_badge(text, color='blue', output_path='badge.png'):
    """Create a badge image"""
    width = 200
    height = 40
    
    colors = {
        'blue': (66, 153, 225),
        'green': (72, 187, 120),
        'red': (245, 101, 101),
        'purple': (159, 122, 234),
        'orange': (237, 137, 54)
    }
    
    bg_color = colors.get(color, colors['blue'])
    
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Rounded corners (approximate)
    radius = 10
    draw.rectangle([0, 0, width, height], fill=bg_color)
    
    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
    
    img.save(output_path)
    print(f"✅ Badge '{text}' saved to {output_path}")
    return img


if __name__ == '__main__':
    # Create assets directory if it doesn't exist
    os.makedirs('assets', exist_ok=True)
    
    print("🎨 Generating visual assets...")
    
    # Generate logo
    logo = create_logo(output_path='assets/logo.png')
    
    # Generate favicon
    create_favicon(logo, output_path='assets/favicon.ico')
    
    # Generate banner
    create_banner(output_path='assets/banner.png')
    
    # Generate badges
    create_badge('98.5% Accuracy', 'green', 'assets/badge_accuracy.png')
    create_badge('5 Layers', 'blue', 'assets/badge_layers.png')
    create_badge('Enterprise', 'purple', 'assets/badge_enterprise.png')
    create_badge('Open Source', 'orange', 'assets/badge_opensource.png')
    
    print("✅ All visual assets generated successfully!")
