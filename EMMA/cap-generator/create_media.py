#!/usr/bin/env python3
"""
Create sample emergency alert media files for EMMA testing
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_emergency_alert_image():
    """Create a sample emergency alert image"""
    
    # Create a red background image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color='red')
    draw = ImageDraw.Draw(image)
    
    try:
        # Try to use a default font, fallback to built-in if not available
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVu-Sans-Bold.ttf", 48)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVu-Sans-Bold.ttf", 32)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVu-Sans.ttf", 24)
        footer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVu-Sans.ttf", 18)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()
    
    # Add alert border
    draw.rectangle([10, 10, width-10, height-10], outline='white', width=5)
    draw.rectangle([20, 20, width-20, height-20], outline='yellow', width=3)
    
    # Add emergency symbol (triangle with exclamation)
    triangle_points = [(width//2, 80), (width//2-40, 140), (width//2+40, 140)]
    draw.polygon(triangle_points, fill='yellow', outline='black')
    draw.text((width//2-8, 100), "!", fill='black', font=title_font)
    
    # Add text content
    draw.text((width//2-150, 180), "EMERGENCY ALERT", fill='white', font=title_font)
    draw.text((width//2-140, 240), "SEVERE WEATHER WARNING", fill='yellow', font=subtitle_font)
    draw.text((width//2-120, 300), "Take shelter immediately", fill='white', font=body_font)
    draw.text((width//2-80, 340), "Avoid windows and doors", fill='white', font=body_font)
    draw.text((width//2-100, 380), "Stay indoors until all clear", fill='white', font=body_font)
    
    # Add timestamp and source
    draw.text((50, height-120), "ISSUED: 2025-09-24 05:15 UTC", fill='white', font=footer_font)
    draw.text((50, height-90), "SOURCE: EMMA Alert System", fill='white', font=footer_font)
    draw.text((50, height-60), "ALERT ID: EMMA-WEATHER-001", fill='white', font=footer_font)
    
    # Add QR code placeholder
    draw.rectangle([width-150, height-150, width-50, height-50], fill='white', outline='black')
    draw.text((width-140, height-140), "QR CODE", fill='black', font=footer_font)
    draw.text((width-130, height-120), "PLACEHOLDER", fill='black', font=footer_font)
    
    # Save the image
    image.save('test_image.jpg', 'JPEG', quality=95)
    print("✅ Created test_image.jpg")

def create_sample_video_placeholder():
    """Create a placeholder for video file"""
    
    # Create a simple text file as video placeholder since we can't easily generate video
    with open('test_video.mp4', 'w') as f:
        f.write("""# EMMA Emergency Alert Video Placeholder
# 
# This file represents a multimedia emergency alert video
# that would contain:
# - Spoken alert message
# - Visual weather radar/map
# - Safety instructions
# - Evacuation routes
# - Emergency contact information
#
# In production, this would be an actual MP4 video file
# generated from alert templates and real-time data.
#
# File: test_video.mp4
# Duration: ~30 seconds
# Content: Emergency weather alert with visual aids
""")
    print("✅ Created test_video.mp4 placeholder")

def create_additional_media():
    """Create additional sample media files for comprehensive testing"""
    
    # Create evacuation map image
    width, height = 600, 400
    map_image = Image.new('RGB', (width, height), color='lightblue')
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVu-Sans.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Simple evacuation map
    draw.rectangle([50, 50, width-50, height-50], fill='lightgreen', outline='black', width=2)
    draw.rectangle([100, 100, 200, 150], fill='red', outline='black', width=2)
    draw.text((110, 115), "DANGER", fill='white', font=font)
    draw.text((110, 130), "ZONE", fill='white', font=font)
    
    # Evacuation routes
    draw.line([(200, 125), (300, 125)], fill='blue', width=5)
    draw.line([(300, 125), (350, 80)], fill='blue', width=5)
    draw.line([(300, 125), (350, 170)], fill='blue', width=5)
    
    # Safe zones
    draw.ellipse([400, 60, 500, 110], fill='green', outline='black')
    draw.text((420, 80), "SAFE", fill='white', font=font)
    draw.ellipse([400, 150, 500, 200], fill='green', outline='black')
    draw.text((420, 170), "SAFE", fill='white', font=font)
    
    # Legend
    draw.text((50, height-40), "🔴 Danger Zone  🔵 Evacuation Route  🟢 Safe Zone", fill='black', font=font)
    
    map_image.save('evacuation_map.jpg', 'JPEG', quality=90)
    print("✅ Created evacuation_map.jpg")

if __name__ == "__main__":
    print("🎨 Creating EMMA emergency alert media files...")
    create_emergency_alert_image()
    create_sample_video_placeholder()
    create_additional_media()
    print("✅ All sample media files created successfully!")