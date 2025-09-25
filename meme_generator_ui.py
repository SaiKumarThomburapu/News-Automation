import gradio as gr
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO
import base64
from datetime import datetime
import time
import random
from pathlib import Path
import warnings
import logging
from dotenv import load_dotenv
import threading
import queue

# Load environment variables
load_dotenv()

# Suppress warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")
logging.getLogger('google').setLevel(logging.ERROR)

# Import your existing classes
try:
    from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
    from gemini_emotion_processor import NewsToMemeProcessor
except ImportError:
    print("Please ensure enhanced_scraper_with_images.py and gemini_emotion_processor.py are in the same directory")
    exit()

class GradioMemeGenerator:
    def __init__(self):
        """Initialize the meme generator with proper URL handling"""
        self.news_extractor = EnhancedNewsExtractorWithImages()
        self.meme_processor = NewsToMemeProcessor()
        
        self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
        if not self.supabase_image_base_url.endswith('/'):
            self.supabase_image_base_url += '/'
        
        self.processed_memes = []
        self.all_memes = []  # Store all memes
        self.categorized_news_data = {}
        self.generation_queue = queue.Queue()
        self.is_generating = False
        self.available_categories = []
        self.current_category = "All"
        
        print(f"Supabase base URL: {self.supabase_image_base_url}")
    
    def is_tnglish(self, text):
        """Check if text should be in Tnglish"""
        telugu_contexts = [
            'tollywood', 'hyderabad', 'telangana', 'andhra', 'vijay', 'prabhas', 
            'mahesh', 'allu arjun', 'ram charan', 'chiranjeevi', 'balakrishna',
            'nagarjuna', 'venkatesh', 'ravi teja', 'ntr', 'pawan kalyan'
        ]
        
        text_lower = text.lower()
        return any(context in text_lower for context in telugu_contexts)
    
    def construct_image_url(self, image_path):
        """Construct proper image URL based on path type"""
        try:
            if not image_path:
                return None
            
            if image_path.startswith('http://') or image_path.startswith('https://'):
                return image_path
            
            if image_path.startswith('storage/'):
                full_url = f"{self.supabase_image_base_url}{image_path}"
                return full_url
            
            if image_path.startswith('output/') or image_path.startswith('./output/'):
                local_path = image_path.replace('./', '')
                if os.path.exists(local_path):
                    return local_path
                else:
                    return None
            
            if image_path.startswith('/'):
                full_url = f"{self.supabase_image_base_url.rstrip('/')}{image_path}"
                return full_url
            
            return None
            
        except Exception as e:
            print(f"Error constructing URL for {image_path}: {e}")
            return None
    
    def load_image_from_path(self, image_path):
        """Load image from various path types with proper error handling"""
        try:
            if not image_path:
                return None
            
            if image_path.startswith('output/') or image_path.startswith('./output/'):
                local_path = image_path.replace('./', '')
                if os.path.exists(local_path):
                    img = Image.open(local_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    return img
                else:
                    return None
            
            url = self.construct_image_url(image_path)
            if not url:
                return None
            
            if not url.startswith('http'):
                if os.path.exists(url):
                    img = Image.open(url)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    return img
                return None
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                return img
            else:
                return None
                
        except Exception as e:
            print(f"Error loading image from {image_path}: {e}")
            return None
    
    def wrap_text_to_fit(self, text, font, draw, max_width):
        """Wrap text to fit within max_width, breaking into multiple lines"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(test_line) * (font.size * 0.6)
            
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    lines.append(word)
                    current_line = ""
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def overlay_text_on_image(self, image_path, dialogues):
        """Enhanced text overlay with proper wrapping and positioning"""
        try:
            img = self.load_image_from_path(image_path)
            if not img:
                return None
            
            draw = ImageDraw.Draw(img)
            img_width, img_height = img.size
            
            base_font_size = max(16, min(img_width // 25, img_height // 20, 48))
            
            font = None
            font_paths = [
                "arial.ttf",
                "/System/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]
            
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, base_font_size)
                    break
                except:
                    continue
            
            if not font:
                font = ImageFont.load_default()
                base_font_size = max(12, min(img_width // 30, img_height // 25, 36))
            
            if len(dialogues) >= 2:
                top_text = dialogues[0].upper()
                bottom_text = dialogues[1].upper()
                
                max_text_width = int(img_width * 0.8)
                
                top_lines = self.wrap_text_to_fit(top_text, font, draw, max_text_width)
                
                try:
                    sample_bbox = draw.textbbox((0, 0), "A", font=font)
                    line_height = sample_bbox[3] - sample_bbox[1] + 4
                except:
                    line_height = base_font_size + 4
                
                top_start_y = max(15, img_height // 20)
                
                for i, line in enumerate(top_lines):
                    try:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                    except:
                        line_width = len(line) * (base_font_size * 0.6)
                    
                    line_x = (img_width - line_width) // 2
                    line_y = top_start_y + (i * line_height)
                    
                    self.draw_text_with_enhanced_outline(draw, (line_x, line_y), line, font)
                
                bottom_lines = self.wrap_text_to_fit(bottom_text, font, draw, max_text_width)
                total_bottom_height = len(bottom_lines) * line_height
                
                bottom_start_y = img_height - total_bottom_height - max(15, img_height // 20)
                
                for i, line in enumerate(bottom_lines):
                    try:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                    except:
                        line_width = len(line) * (base_font_size * 0.6)
                    
                    line_x = (img_width - line_width) // 2
                    line_y = bottom_start_y + (i * line_height)
                    
                    self.draw_text_with_enhanced_outline(draw, (line_x, line_y), line, font)
            
            return img
            
        except Exception as e:
            print(f"Error overlaying text on {image_path}: {e}")
            return None
    
    def draw_text_with_enhanced_outline(self, draw, position, text, font, text_color='white', outline_color='black', outline_width=3):
        """Draw text with enhanced outline for better visibility"""
        x, y = position
        
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
        draw.text(position, text, font=font, fill=text_color)
    
    def generate_tnglish_dialogues(self, english_dialogues, context):
        """Convert to Tnglish if Telugu context detected"""
        if not self.is_tnglish(context):
            return english_dialogues
        
        tnglish_patterns = {
            "when": "eppudu",
            "everyone": "andaru", 
            "meanwhile": "antha sepu",
            "me": "nenu",
            "that moment": "aa moment",
            "literally": "literally",
            "waiting": "wait chestunna",
            "watching": "chustunna",
            "thinking": "anukuntunna",
            "feeling": "feel avutunna",
            "people": "vallu",
            "this": "idhi",
            "that": "adhi",
            "now": "ippudu",
            "always": "eppuduu",
            "what": "enti",
            "why": "enduku",
            "how": "ela"
        }
        
        tnglish_dialogues = []
        for dialogue in english_dialogues:
            tnglish_version = dialogue.lower()
            for eng, tel in tnglish_patterns.items():
                tnglish_version = tnglish_version.replace(eng, tel)
            tnglish_dialogues.append(tnglish_version.capitalize())
        
        return tnglish_dialogues
    
    def find_related_images(self, news_index):
        """Find related images for a specific news item"""
        try:
            if hasattr(self, 'categorized_news_data') and self.categorized_news_data:
                # Get all articles in order
                all_articles = []
                for category, articles in self.categorized_news_data.items():
                    for article in articles:
                        article['scraped_category'] = category
                        all_articles.append(article)
                
                if news_index < len(all_articles):
                    article = all_articles[news_index]
                    images = []
                    
                    # Get the original scraped image if available
                    if article.get('image_path'):
                        images.append(article['image_path'])
                    
                    return images
            
            return []
        except Exception as e:
            print(f"Error finding related images: {e}")
            return []
    
    def generate_meme_card_html(self, meme_data, index):
        """Generate single meme card HTML"""
        # Get template path and dialogues
        template_path = meme_data.get('template_image_path', '')
        dialogues = meme_data.get('dialogues', [])
        description = meme_data.get('description', 'No description available')
        hashtags = meme_data.get('hashtags', [])
        url = meme_data.get('url', '')
        category = meme_data.get('category', 'Unknown').title()
        
        # Language detection
        context = description + ' ' + str(dialogues)
        is_tnglish = self.is_tnglish(context)
        
        if is_tnglish:
            dialogues = self.generate_tnglish_dialogues(dialogues, context)
        
        # Process dialogues (max 8 words each)
        processed_dialogues = []
        for dialogue in dialogues[:2]:
            words = dialogue.split()[:8]
            processed_dialogues.append(' '.join(words))
        
        # Create meme image
        meme_image = None
        image_html = ""
        if template_path and processed_dialogues:
            meme_image = self.overlay_text_on_image(template_path, processed_dialogues)
            if meme_image:
                # Convert PIL image to base64 for HTML display
                buffered = BytesIO()
                meme_image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                image_html = f'<img src="data:image/png;base64,{img_str}" class="post-image" />'
            else:
                original_template = self.load_image_from_path(template_path)
                if original_template:
                    buffered = BytesIO()
                    original_template.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    image_html = f'<img src="data:image/png;base64,{img_str}" class="post-image" />'
        
        if not image_html:
            image_html = '<div class="no-image">No template available</div>'
        
        # Format hashtags
        hashtags_html = " ".join([f'<span class="hashtag">#{tag.replace("#", "")}</span>' for tag in hashtags[:8]])
        
        # Create status message
        status_badge = f'🎭 Meme #{index + 1} | {category}'
        if is_tnglish:
            status_badge += ' | 🌏 Tnglish'
        
        # Related images (mini block)
        related_images_html = ""
        related_images = self.find_related_images(index)
        if related_images:
            related_images_content = ""
            for i, img_path in enumerate(related_images[:3]):  # Max 3 images
                img = self.load_image_from_path(img_path)
                if img:
                    # Convert to base64 for display
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    related_images_content += f'<img src="data:image/png;base64,{img_str}" class="related-mini-image" alt="Related image {i+1}" />'
            
            if related_images_content:
                related_images_html = f"""
                <div class="related-images-mini">
                    <h4 class="related-title">📸 Related News Images</h4>
                    <div class="mini-images-grid">
                        {related_images_content}
                    </div>
                </div>
                """
        
        return f"""
        <div class="meme-card">
            <!-- Post Header -->
            <div class="post-header">
                <div class="profile-info">
                    <div class="profile-avatar">🎭</div>
                    <div>
                        <div class="username">MemeGram</div>
                        <div class="location">{status_badge}</div>
                    </div>
                </div>
                <div class="menu-dots">⋯</div>
            </div>
            
            <!-- 1. Main Image/Template -->
            <div class="post-image-container">
                {image_html}
            </div>
            
            <!-- Post Actions -->
            <div class="post-actions">
                <div class="action-buttons">
                    <span class="action-btn">❤️</span>
                    <span class="action-btn">💬</span>
                    <span class="action-btn">📤</span>
                </div>
                <div class="bookmark">🔖</div>
            </div>
            
            <!-- 2. Description -->
            <div class="post-content">
                <div class="likes">❤️ {random.randint(100, 2000)} likes</div>
                <div class="caption">
                    <span class="username">memegram</span> 
                    <span class="description-text">{description}</span>
                </div>
                
                <!-- 3. Read More News Link -->
                {f'<div class="news-link"><a href="{url}" target="_blank">🔗 Read full news article</a></div>' if url else ''}
                
                <!-- 4. Hashtags -->
                <div class="hashtags">
                    {hashtags_html}
                </div>
                
                <!-- 5. Related Images Mini Block -->
                {related_images_html}
                
                <!-- Timestamp -->
                <div class="timestamp">{datetime.now().strftime('%B %d')} • See translation</div>
            </div>
        </div>
        """
    
    def generate_all_memes_html(self, selected_category="All"):
        """Generate all memes HTML based on selected category"""
        if not self.all_memes:
            return """
            <div class="empty-state">
                <div style="text-align: center; padding: 4rem; color: #666;">
                    <h3>No memes available</h3>
                    <p>Click "🎭 Generate Memes" to start creating amazing content!</p>
                </div>
            </div>
            """
        
        # Filter memes by category
        if selected_category == "All":
            filtered_memes = self.all_memes
        else:
            filtered_memes = [meme for meme in self.all_memes if meme.get('category', '').title() == selected_category]
        
        if not filtered_memes:
            return f"""
            <div class="empty-state">
                <div style="text-align: center; padding: 4rem; color: #666;">
                    <h3>No memes found for {selected_category}</h3>
                    <p>Try selecting a different category or generate new memes!</p>
                </div>
            </div>
            """
        
        memes_html = ""
        for index, meme_data in enumerate(filtered_memes):
            memes_html += self.generate_meme_card_html(meme_data, index)
        
        return f"""
        <div class="memes-grid">
            <div class="category-info">
                <h2>📱 {selected_category} Memes ({len(filtered_memes)} total)</h2>
            </div>
            {memes_html}
        </div>
        """
    
    def generate_streaming_memes(self):
        """Generate memes with status updates"""
        try:
            self.is_generating = True
            self.all_memes = []
            self.available_categories = []
            self.current_category = "All"
            
            # Step 1: Scrape news
            categorized_news = self.news_extractor.get_all_news()
            if not categorized_news:
                self.is_generating = False
                return (
                    self.generate_all_memes_html(), 
                    "❌ Failed to scrape news",
                    gr.update(visible=False, choices=["All"], value="All")
                )
            
            self.categorized_news_data = categorized_news
            
            # Step 2: Process articles
            processed_memes = self.meme_processor.process_all_news_articles()
            if not processed_memes:
                self.is_generating = False
                return (
                    self.generate_all_memes_html(), 
                    "❌ Failed to process articles",
                    gr.update(visible=False, choices=["All"], value="All")
                )
            
            self.all_memes = processed_memes
            self.is_generating = False
            
            # Get available categories
            categories = list(set([meme.get('category', 'Unknown').title() for meme in processed_memes]))
            categories.sort()
            self.available_categories = ["All"] + categories
            
            # Return all memes and show category buttons with updated choices
            return (
                self.generate_all_memes_html("All"), 
                f"✅ Generated {len(processed_memes)} memes successfully across {len(categories)} categories!",
                gr.update(visible=True, choices=self.available_categories, value="All")
            )
                
        except Exception as e:
            self.is_generating = False
            return (
                self.generate_all_memes_html(), 
                f"❌ Error: {str(e)}",
                gr.update(visible=False, choices=["All"], value="All")
            )
    
    def filter_by_category(self, selected_category):
        """Filter memes by selected category"""
        self.current_category = selected_category
        return (
            self.generate_all_memes_html(selected_category),
            f"📱 Showing {selected_category} memes"
        )

# Initialize the generator
meme_generator = GradioMemeGenerator()

# Instagram-style CSS with CLEAN HEADINGS and PROFESSIONAL BUTTONS
instagram_css = """
/* Instagram-inspired Design - CLEAN & PROFESSIONAL */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background: linear-gradient(135deg, #ffebee 0%, #fff5f5 100%) !important;
    min-height: 100vh;
    padding: 1rem;
}

/* Main Header - MemeGram Banner */
.main-header {
    background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
    padding: 2rem;
    text-align: center;
    margin: 2rem auto;
    max-width: 800px;
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(220, 38, 38, 0.3);
    color: white;
}

.main-title {
    font-size: 3rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    text-shadow: 0 4px 20px rgba(0,0,0,0.3);
    color: white;
}

.main-subtitle {
    font-size: 1.2rem;
    opacity: 0.9;
    margin: 0;
    color: white;
}

/* SIMPLE HEADINGS - No banners */
.section-heading {
    text-align: center;
    margin: 2rem auto 1rem auto;
    max-width: 800px;
    padding: 0 1rem;
}

.section-heading h2 {
    font-size: 2rem;
    font-weight: 700;
    color: #dc2626;
    margin: 0;
    text-shadow: 0 2px 10px rgba(220, 38, 38, 0.1);
}

.section-heading h3 {
    font-size: 1.6rem;
    font-weight: 600;
    color: #dc2626;
    margin: 0;
    text-shadow: 0 2px 10px rgba(220, 38, 38, 0.1);
}

/* PROFESSIONAL GENERATE BUTTON - Lightest Red */
.gradio-button {
    background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 30px !important;
    font-weight: 700 !important;
    font-size: 1.2rem !important;
    padding: 16px 40px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    margin: 1rem auto !important;
    min-height: 55px !important;
    min-width: 250px !important;
    box-shadow: 0 6px 20px rgba(248, 113, 113, 0.4) !important;
    text-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    display: block !important;
}

.gradio-button:hover {
    background: linear-gradient(135deg, #f87171 0%, #ef4444 100%) !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 10px 30px rgba(248, 113, 113, 0.5) !important;
    color: white !important;
}

/* PROFESSIONAL CATEGORY SELECTION */
.gradio-radio {
    margin: 1.5rem auto !important;
    padding: 1.5rem !important;
    background: white !important;
    border-radius: 15px !important;
    box-shadow: 0 4px 15px rgba(220, 38, 38, 0.1) !important;
    border: 2px solid #fca5a5 !important;
    max-width: 800px !important;
}

.gradio-radio .gradio-checkboxgroup {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 12px !important;
    justify-content: center !important;
    align-items: center !important;
    margin: 0 !important;
}

.gradio-radio label {
    background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%) !important;
    border: 2px solid #f87171 !important;
    color: white !important;
    padding: 12px 24px !important;
    border-radius: 25px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
    min-width: 100px !important;
    text-align: center !important;
    margin: 0 !important;
    box-shadow: 0 4px 12px rgba(248, 113, 113, 0.3) !important;
    text-shadow: 0 1px 6px rgba(0,0,0,0.2) !important;
}

.gradio-radio label:hover {
    background: linear-gradient(135deg, #f87171 0%, #ef4444 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(248, 113, 113, 0.4) !important;
    border-color: #ef4444 !important;
}

.gradio-radio input[type="radio"]:checked + label {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5) !important;
    transform: translateY(-2px) !important;
    border-color: #dc2626 !important;
}

.gradio-radio input[type="radio"] {
    display: none !important;
}

/* Status Message */
.status-message {
    text-align: center;
    padding: 12px 16px;
    background: #fef2f2;
    border: 2px solid #fca5a5;
    border-radius: 12px;
    margin: 16px auto;
    max-width: 800px;
    font-weight: 600;
    color: #dc2626;
}

/* Memes Grid */
.memes-grid {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.category-info {
    background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
    color: white;
    padding: 1.5rem 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 8px 25px rgba(220, 38, 38, 0.3);
}

.category-info h2 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 700;
    text-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

/* Individual Meme Cards */
.meme-card {
    background: white;
    border: 2px solid #fca5a5;
    border-radius: 15px;
    margin: 2rem auto;
    max-width: 614px;
    box-shadow: 0 8px 25px rgba(220, 38, 38, 0.1);
    overflow: hidden;
    transition: all 0.3s ease;
}

.meme-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 35px rgba(220, 38, 38, 0.2);
    border-color: #dc2626;
}

/* Post Header */
.post-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 2px solid #fef2f2;
    background: linear-gradient(135deg, #fef2f2 0%, #fff5f5 100%);
}

.profile-info {
    display: flex;
    align-items: center;
}

.profile-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    font-size: 16px;
    color: white;
    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.username {
    font-weight: 600;
    font-size: 14px;
    color: #dc2626;
}

.location {
    font-size: 12px;
    color: #991b1b;
    margin-top: 2px;
}

.menu-dots {
    font-size: 16px;
    cursor: pointer;
    color: #dc2626;
}

/* Post Image */
.post-image-container {
    position: relative;
    width: 100%;
    background: #000;
}

.post-image {
    width: 100%;
    height: auto;
    max-height: 614px;
    object-fit: cover;
    display: block;
}

.no-image {
    width: 100%;
    height: 300px;
    background: #fef2f2;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #dc2626;
    font-size: 16px;
    font-weight: 500;
}

/* Post Actions */
.post-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px 8px;
    background: #fefefe;
}

.action-buttons {
    display: flex;
    gap: 16px;
}

.action-btn {
    font-size: 24px;
    cursor: pointer;
    user-select: none;
    transition: all 0.2s ease;
}

.action-btn:hover {
    opacity: 0.7;
    transform: scale(1.1);
}

.bookmark {
    font-size: 24px;
    cursor: pointer;
    color: #dc2626;
}

/* Post Content */
.post-content {
    padding: 0 16px 16px;
    background: white;
}

.likes {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 8px;
    color: #dc2626;
}

.caption {
    margin-bottom: 12px;
    line-height: 18px;
    font-size: 14px;
}

.caption .username {
    font-weight: 600;
    margin-right: 8px;
    color: #dc2626;
}

.description-text {
    color: #374151;
    word-wrap: break-word;
}

/* News Link */
.news-link {
    margin: 12px 0;
    padding: 12px;
    background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(220, 38, 38, 0.3);
}

.news-link a {
    color: white;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
}

.news-link a:hover {
    text-decoration: underline;
}

/* Hashtags */
.hashtags {
    margin: 12px 0;
    line-height: 22px;
}

.hashtag {
    color: #dc2626;
    background: #fef2f2;
    padding: 4px 8px;
    border-radius: 12px;
    font-weight: 600;
    margin-right: 8px;
    margin-bottom: 4px;
    cursor: pointer;
    font-size: 13px;
    display: inline-block;
    border: 1px solid #fca5a5;
    transition: all 0.2s ease;
}

.hashtag:hover {
    background: #dc2626;
    color: white;
}

/* Related Images Mini Block */
.related-images-mini {
    margin: 16px 0;
    padding: 12px;
    background: #fef2f2;
    border-radius: 12px;
    border: 2px solid #fca5a5;
}

.related-title {
    margin: 0 0 10px 0;
    font-size: 13px;
    font-weight: 600;
    color: #dc2626;
    text-align: center;
}

.mini-images-grid {
    display: flex;
    gap: 8px;
    justify-content: center;
    flex-wrap: wrap;
}

.related-mini-image {
    width: 80px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid #fca5a5;
    transition: all 0.2s ease;
}

.related-mini-image:hover {
    transform: scale(1.05);
    border-color: #dc2626;
}

/* Timestamp */
.timestamp {
    font-size: 12px;
    color: #991b1b;
    text-transform: uppercase;
    margin-top: 16px;
}

/* Empty State */
.empty-state {
    background: white;
    border: 2px solid #fca5a5;
    border-radius: 15px;
    margin: 2rem auto;
    max-width: 614px;
    box-shadow: 0 8px 25px rgba(220, 38, 38, 0.1);
    overflow: hidden;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .meme-card {
        margin: 1rem 8px;
        max-width: calc(100% - 16px);
    }
    
    .main-header,
    .section-heading {
        margin: 1rem 8px !important;
        max-width: calc(100% - 16px) !important;
        padding: 1.5rem !important;
    }
    
    .main-title {
        font-size: 2rem;
    }
    
    .section-heading h2 {
        font-size: 1.5rem;
    }
    
    .section-heading h3 {
        font-size: 1.3rem;
    }
    
    .gradio-radio {
        margin: 1rem 8px !important;
        max-width: calc(100% - 16px) !important;
    }
    
    .gradio-radio .gradio-checkboxgroup {
        flex-direction: column !important;
        gap: 8px !important;
    }
    
    .gradio-radio label {
        width: 100% !important;
        max-width: 200px !important;
    }
    
    .mini-images-grid {
        gap: 6px;
    }
    
    .related-mini-image {
        width: 60px;
        height: 60px;
    }
    
    .status-message {
        margin: 16px 8px !important;
        max-width: calc(100% - 16px) !important;
    }
}
"""

# Create the Gradio interface
def create_interface():
    with gr.Blocks(css=instagram_css, title="📱 MemeGram - Instagram Style", theme=gr.themes.Soft()) as demo:
        
        # Main Header - MemeGram Banner (unchanged)
        gr.HTML("""
        <div class="main-header">
            <h1 class="main-title">📱 MemeGram</h1>
            <p class="main-subtitle">AI-powered viral memes from latest Indian news</p>
        </div>
        """)
        
        # SIMPLE HEADING: Generate Your Viral Content
        gr.HTML("""
        <div class="section-heading">
            <h2>🚀 Generate Your Viral Content</h2>
        </div>
        """)
        
        generate_btn = gr.Button(
            "🎭 Generate Memes",
            size="lg"
        )
        
        # Status Message
        status_display = gr.HTML(
            value='<div class="status-message">🎯 Ready to generate amazing Instagram-style memes!</div>',
            show_label=False
        )
        
        # SIMPLE HEADING: Filter by Category
        gr.HTML("""
        <div class="section-heading">
            <h3>📂 Filter by Category</h3>
        </div>
        """)
        
        category_radio = gr.Radio(
            choices=["All"],
            value="All",
            label="",
            visible=False,
            show_label=False
        )
        
        # Main Memes Display
        memes_display = gr.HTML(
            value=meme_generator.generate_all_memes_html(),
            show_label=False
        )
        
        # Event handlers
        generate_btn.click(
            fn=meme_generator.generate_streaming_memes,
            outputs=[memes_display, status_display, category_radio]
        )
        
        category_radio.change(
            fn=meme_generator.filter_by_category,
            inputs=[category_radio],
            outputs=[memes_display, status_display]
        )
    
    return demo

# Launch the interface
if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
        debug=True
    )










# import streamlit as st
# import json
# import os
# import requests
# from PIL import Image, ImageDraw, ImageFont
# import textwrap
# from io import BytesIO
# import base64
# from datetime import datetime
# import time
# import random
# from pathlib import Path
# import warnings
# import logging
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Suppress warnings
# os.environ['GRPC_VERBOSITY'] = 'ERROR'
# os.environ['GLOG_minloglevel'] = '2'
# warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")
# logging.getLogger('google').setLevel(logging.ERROR)

# # Import your existing classes
# try:
#     from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
#     from gemini_emotion_processor import NewsToMemeProcessor
# except ImportError:
#     st.error("Please ensure enhanced_scraper_with_images.py and gemini_emotion_processor.py are in the same directory")
#     st.stop()

# # Page configuration
# st.set_page_config(
#     page_title="AI Meme Generator", 
#     page_icon="😂", 
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )

# # Enhanced CSS with improved meme display
# st.markdown("""
# <style>
#     .main-header {
#         text-align: center;
#         color: #FF6B6B;
#         font-size: 2.5rem;
#         font-weight: bold;
#         margin-bottom: 1.5rem;
#         text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
#     }
    
#     .meme-container {
#         border: 2px solid #E0E0E0;
#         border-radius: 12px;
#         padding: 15px;
#         margin: 10px 5px;
#         background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
#         box-shadow: 0 3px 10px rgba(0,0,0,0.1);
#         height: fit-content;
#     }
    
#     .meme-image-container {
#         margin: 10px 0;
#         border-radius: 8px;
#         overflow: hidden;
#         box-shadow: 0 4px 12px rgba(0,0,0,0.15);
#     }
    
#     .description-box {
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         border-radius: 10px;
#         padding: 12px;
#         margin: 8px 0;
#         color: white;
#         font-size: 0.9rem;
#         font-weight: 500;
#         line-height: 1.4;
#         box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
#     }
    
#     .hashtag-container {
#         background: linear-gradient(45deg, #667eea, #764ba2);
#         border-radius: 15px;
#         padding: 6px 12px;
#         margin: 3px;
#         display: inline-block;
#         color: white;
#         font-weight: bold;
#         font-size: 0.75rem;
#         box-shadow: 0 2px 6px rgba(102, 126, 234, 0.2);
#     }
    
#     .meme-counter {
#         background: linear-gradient(45deg, #4CAF50, #45a049);
#         color: white;
#         padding: 8px 12px;
#         border-radius: 15px;
#         text-align: center;
#         font-weight: bold;
#         margin: 5px 0;
#         font-size: 0.85rem;
#         box-shadow: 0 3px 8px rgba(76, 175, 80, 0.2);
#     }
    
#     .related-images-mini {
#         background: #f8f9fa;
#         border: 1px solid #e9ecef;
#         border-radius: 6px;
#         padding: 6px;
#         margin: 8px 0;
#         max-height: 100px;
#         overflow: hidden;
#     }
    
#     .template-container {
#         background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%);
#         border-radius: 6px;
#         padding: 8px;
#         margin: 6px 0;
#         color: white;
#         box-shadow: 0 2px 6px rgba(78, 205, 196, 0.2);
#         font-size: 0.8rem;
#     }
    
#     .compact-info {
#         font-size: 0.8rem;
#         line-height: 1.3;
#         margin: 8px 0;
#     }
    
#     .dialogue-info {
#         background: #e8f4fd;
#         border-left: 3px solid #2196F3;
#         border-radius: 4px;
#         padding: 8px;
#         margin: 6px 0;
#         font-size: 0.8rem;
#     }
    
#     .mini-image-grid {
#         display: grid;
#         grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
#         gap: 4px;
#         margin: 6px 0;
#     }
    
#     .mini-image-item {
#         border-radius: 4px;
#         overflow: hidden;
#         border: 1px solid #dee2e6;
#     }
    
#     @media (max-width: 768px) {
#         .main-header {
#             font-size: 2rem;
#         }
#         .meme-container {
#             margin: 5px 0;
#             padding: 10px;
#         }
#     }
# </style>
# """, unsafe_allow_html=True)

# class StreamlitMemeGenerator:
#     def __init__(self):
#         """Initialize the meme generator with proper URL handling"""
#         if 'processors_initialized' not in st.session_state:
#             with st.spinner("🔄 Initializing AI processors..."):
#                 try:
#                     self.news_extractor = EnhancedNewsExtractorWithImages()
#                     self.meme_processor = NewsToMemeProcessor()
#                     st.session_state.processors_initialized = True
#                     st.session_state.news_extractor = self.news_extractor
#                     st.session_state.meme_processor = self.meme_processor
                    
#                     # Get Supabase base URL from environment
#                     self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
#                     if not self.supabase_image_base_url.endswith('/'):
#                         self.supabase_image_base_url += '/'
                    
#                     print(f"Supabase base URL: {self.supabase_image_base_url}")
                    
#                 except Exception as e:
#                     st.error(f"Failed to initialize processors: {e}")
#                     st.stop()
#         else:
#             self.news_extractor = st.session_state.news_extractor
#             self.meme_processor = st.session_state.meme_processor
#             self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
#             if not self.supabase_image_base_url.endswith('/'):
#                 self.supabase_image_base_url += '/'
    
#     def is_tnglish(self, text):
#         """Check if text should be in Tnglish"""
#         telugu_contexts = [
#             'tollywood', 'hyderabad', 'telangana', 'andhra', 'vijay', 'prabhas', 
#             'mahesh', 'allu arjun', 'ram charan', 'chiranjeevi', 'balakrishna',
#             'nagarjuna', 'venkatesh', 'ravi teja', 'ntr', 'pawan kalyan'
#         ]
        
#         text_lower = text.lower()
#         return any(context in text_lower for context in telugu_contexts)
    
#     def construct_image_url(self, image_path):
#         """Construct proper image URL based on path type"""
#         try:
#             if not image_path:
#                 return None
            
#             # If already a complete URL, return as is
#             if image_path.startswith('http://') or image_path.startswith('https://'):
#                 return image_path
            
#             # If it's a Supabase storage path
#             if image_path.startswith('storage/'):
#                 full_url = f"{self.supabase_image_base_url}{image_path}"
#                 return full_url
            
#             # If it's a local file path (related images)
#             if image_path.startswith('output/') or image_path.startswith('./output/'):
#                 local_path = image_path.replace('./', '')
#                 if os.path.exists(local_path):
#                     return local_path
#                 else:
#                     return None
            
#             # If path starts with /, treat as Supabase path
#             if image_path.startswith('/'):
#                 full_url = f"{self.supabase_image_base_url.rstrip('/')}{image_path}"
#                 return full_url
            
#             return None
            
#         except Exception as e:
#             print(f"Error constructing URL for {image_path}: {e}")
#             return None
    
#     def load_image_from_path(self, image_path):
#         """Load image from various path types with proper error handling"""
#         try:
#             if not image_path:
#                 return None
            
#             # Handle local file paths
#             if image_path.startswith('output/') or image_path.startswith('./output/'):
#                 local_path = image_path.replace('./', '')
#                 if os.path.exists(local_path):
#                     img = Image.open(local_path)
#                     if img.mode != 'RGB':
#                         img = img.convert('RGB')
#                     return img
#                 else:
#                     return None
            
#             # Handle URL paths
#             url = self.construct_image_url(image_path)
#             if not url:
#                 return None
            
#             # If it's still a local path after construction
#             if not url.startswith('http'):
#                 if os.path.exists(url):
#                     img = Image.open(url)
#                     if img.mode != 'RGB':
#                         img = img.convert('RGB')
#                     return img
#                 return None
            
#             # Download from URL
#             response = requests.get(url, timeout=10)
#             if response.status_code == 200:
#                 img = Image.open(BytesIO(response.content))
#                 if img.mode != 'RGB':
#                     img = img.convert('RGB')
#                 return img
#             else:
#                 return None
                
#         except Exception as e:
#             print(f"Error loading image from {image_path}: {e}")
#             return None
    
#     def wrap_text_to_fit(self, text, font, draw, max_width):
#         """Wrap text to fit within max_width, breaking into multiple lines"""
#         words = text.split()
#         lines = []
#         current_line = ""
        
#         for word in words:
#             test_line = current_line + (" " if current_line else "") + word
            
#             try:
#                 bbox = draw.textbbox((0, 0), test_line, font=font)
#                 text_width = bbox[2] - bbox[0]
#             except:
#                 text_width = len(test_line) * (font.size * 0.6)
            
#             if text_width <= max_width:
#                 current_line = test_line
#             else:
#                 if current_line:
#                     lines.append(current_line)
#                     current_line = word
#                 else:
#                     lines.append(word)
#                     current_line = ""
        
#         if current_line:
#             lines.append(current_line)
        
#         return lines
    
#     def overlay_text_on_image(self, image_path, dialogues):
#         """Enhanced text overlay with proper wrapping and positioning"""
#         try:
#             img = self.load_image_from_path(image_path)
#             if not img:
#                 return None
            
#             draw = ImageDraw.Draw(img)
#             img_width, img_height = img.size
            
#             # Calculate responsive font size
#             base_font_size = max(16, min(img_width // 25, img_height // 20, 48))
            
#             # Try to load font
#             font = None
#             font_paths = [
#                 "arial.ttf",
#                 "/System/Library/Fonts/Arial.ttf",  # macOS
#                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
#                 "C:/Windows/Fonts/arial.ttf",  # Windows
#                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux alternative
#             ]
            
#             for font_path in font_paths:
#                 try:
#                     font = ImageFont.truetype(font_path, base_font_size)
#                     break
#                 except:
#                     continue
            
#             if not font:
#                 font = ImageFont.load_default()
#                 base_font_size = max(12, min(img_width // 30, img_height // 25, 36))
            
#             if len(dialogues) >= 2:
#                 # Top dialogue processing
#                 top_text = dialogues[0].upper()
#                 bottom_text = dialogues[1].upper()
                
#                 # Calculate maximum text width (80% of image width)
#                 max_text_width = int(img_width * 0.8)
                
#                 # Wrap top text into multiple lines
#                 top_lines = self.wrap_text_to_fit(top_text, font, draw, max_text_width)
                
#                 # Calculate line height
#                 try:
#                     sample_bbox = draw.textbbox((0, 0), "A", font=font)
#                     line_height = sample_bbox[3] - sample_bbox[1] + 4
#                 except:
#                     line_height = base_font_size + 4
                
#                 # Position top text
#                 top_start_y = max(15, img_height // 20)
                
#                 for i, line in enumerate(top_lines):
#                     try:
#                         bbox = draw.textbbox((0, 0), line, font=font)
#                         line_width = bbox[2] - bbox[0]
#                     except:
#                         line_width = len(line) * (base_font_size * 0.6)
                    
#                     line_x = (img_width - line_width) // 2
#                     line_y = top_start_y + (i * line_height)
                    
#                     self.draw_text_with_enhanced_outline(draw, (line_x, line_y), line, font)
                
#                 # Wrap bottom text
#                 bottom_lines = self.wrap_text_to_fit(bottom_text, font, draw, max_text_width)
#                 total_bottom_height = len(bottom_lines) * line_height
                
#                 # Position bottom text
#                 bottom_start_y = img_height - total_bottom_height - max(15, img_height // 20)
                
#                 for i, line in enumerate(bottom_lines):
#                     try:
#                         bbox = draw.textbbox((0, 0), line, font=font)
#                         line_width = bbox[2] - bbox[0]
#                     except:
#                         line_width = len(line) * (base_font_size * 0.6)
                    
#                     line_x = (img_width - line_width) // 2
#                     line_y = bottom_start_y + (i * line_height)
                    
#                     self.draw_text_with_enhanced_outline(draw, (line_x, line_y), line, font)
            
#             return img
            
#         except Exception as e:
#             print(f"Error overlaying text on {image_path}: {e}")
#             return None
    
#     def draw_text_with_enhanced_outline(self, draw, position, text, font, text_color='white', outline_color='black', outline_width=3):
#         """Draw text with enhanced outline for better visibility"""
#         x, y = position
        
#         # Draw thick outline
#         for dx in range(-outline_width, outline_width + 1):
#             for dy in range(-outline_width, outline_width + 1):
#                 if dx != 0 or dy != 0:
#                     draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
#         # Draw main text
#         draw.text(position, text, font=font, fill=text_color)
    
#     def generate_tnglish_dialogues(self, english_dialogues, context):
#         """Convert to Tnglish if Telugu context detected"""
#         if not self.is_tnglish(context):
#             return english_dialogues
        
#         tnglish_patterns = {
#             "when": "eppudu",
#             "everyone": "andaru", 
#             "meanwhile": "antha sepu",
#             "me": "nenu",
#             "that moment": "aa moment",
#             "literally": "literally",
#             "waiting": "wait chestunna",
#             "watching": "chustunna",
#             "thinking": "anukuntunna",
#             "feeling": "feel avutunna",
#             "people": "vallu",
#             "this": "idhi",
#             "that": "adhi",
#             "now": "ippudu",
#             "always": "eppuduu",
#             "what": "enti",
#             "why": "enduku",
#             "how": "ela"
#         }
        
#         tnglish_dialogues = []
#         for dialogue in english_dialogues:
#             tnglish_version = dialogue.lower()
#             for eng, tel in tnglish_patterns.items():
#                 tnglish_version = tnglish_version.replace(eng, tel)
#             tnglish_dialogues.append(tnglish_version.capitalize())
        
#         return tnglish_dialogues
    
#     def find_related_images(self, news_index):
#         """Find related images for a specific news item"""
#         try:
#             if hasattr(st.session_state, 'categorized_news_data'):
#                 categorized_news = st.session_state.categorized_news_data
                
#                 all_articles = []
#                 for category, articles in categorized_news.items():
#                     for article in articles:
#                         article['scraped_category'] = category
#                         all_articles.append(article)
                
#                 if news_index < len(all_articles):
#                     article = all_articles[news_index]
#                     images = []
                    
#                     if article.get('image_path'):
#                         images.append(article['image_path'])
                    
#                     return images
            
#             return []
#         except Exception as e:
#             print(f"Error finding related images: {e}")
#             return []
    
#     @st.cache_data
#     def generate_all_memes(_self):
#         """Generate all memes and cache results"""
#         try:
#             with st.spinner("📰 Scraping latest news..."):
#                 categorized_news = _self.news_extractor.get_all_news()
#                 if not categorized_news:
#                     return [], {}
                
#                 st.session_state.categorized_news_data = categorized_news
            
#             with st.spinner("🤖 Processing with AI..."):
#                 processed_memes = _self.meme_processor.process_all_news_articles()
#                 if not processed_memes:
#                     return [], categorized_news
            
#             return processed_memes, categorized_news
            
#         except Exception as e:
#             st.error(f"Error generating memes: {e}")
#             return [], {}
    
#     def display_compact_meme_block(self, meme_data, index):
#         """Display enhanced compact meme block with better sizing"""
#         with st.container():
#             # Meme counter
#             st.markdown(f'<div class="meme-counter">🎭 Meme #{index + 1} - {meme_data.get("category", "Unknown").title()}</div>', unsafe_allow_html=True)
            
#             template_path = meme_data.get('template_image_path', '')
#             dialogues = meme_data.get('dialogues', [])
            
#             if template_path and dialogues:
#                 # Language detection
#                 context = meme_data.get('description', '') + ' ' + str(dialogues)
                
#                 if self.is_tnglish(context):
#                     dialogues = self.generate_tnglish_dialogues(dialogues, context)
#                     st.success("🎯 Tnglish mode activated!")
                
#                 # Ensure max 8 words per dialogue
#                 processed_dialogues = []
#                 for dialogue in dialogues[:2]:
#                     words = dialogue.split()[:8]
#                     processed_dialogues.append(' '.join(words))
                
#                 # Create and display meme with better sizing
#                 meme_image = self.overlay_text_on_image(template_path, processed_dialogues)
                
#                 if meme_image:
#                     st.markdown('<div class="meme-image-container">', unsafe_allow_html=True)
#                     st.image(meme_image, use_container_width=True, caption="🎭 Generated Meme")
#                     st.markdown('</div>', unsafe_allow_html=True)
                    
#                     # Original template expander (compact)
#                     with st.expander("🖼️ View Original Template", expanded=False):
#                         original_template = self.load_image_from_path(template_path)
#                         if original_template:
#                             st.markdown('<div class="template-container">📸 Clean template without text overlay</div>', unsafe_allow_html=True)
#                             st.image(original_template, use_container_width=True)
#                         else:
#                             st.error("Failed to load original template")
#                 else:
#                     st.error("❌ Failed to create meme")
#                     original_template = self.load_image_from_path(template_path)
#                     if original_template:
#                         st.image(original_template, use_container_width=True, caption="Original Template")
#             else:
#                 st.warning("⚠️ Missing template or dialogues")
            
#             # Dialogue info in styled box
#             current_dialogues = dialogues if 'dialogues' in locals() else meme_data.get('dialogues', [])
#             if current_dialogues:
#                 dialogue_text = ""
#                 for i, dialogue in enumerate(current_dialogues[:2], 1):
#                     words_count = len(dialogue.split())
#                     emoji = "✅" if words_count <= 8 else "⚠️"
#                     dialogue_text += f"{emoji} <strong>{i}.</strong> \"{dialogue}\" ({words_count}w)<br>"
                
#                 st.markdown(f'<div class="dialogue-info"><strong>💬 Dialogues:</strong><br>{dialogue_text}</div>', unsafe_allow_html=True)
            
#             # Related Images - Direct display in mini blocks
#             related_images = self.find_related_images(index)
            
#             if related_images:
#                 st.markdown('<div class="related-images-mini">', unsafe_allow_html=True)
#                 st.markdown("**📸 Related News Images:**")
                
#                 if len(related_images) == 1:
#                     img = self.load_image_from_path(related_images[0])
#                     if img:
#                         st.image(img, use_container_width=True, caption="Related news image")
#                     else:
#                         st.error("Failed to load related image")
#                 else:
#                     # Multiple images in mini grid
#                     st.markdown('<div class="mini-image-grid">', unsafe_allow_html=True)
#                     for i, img_path in enumerate(related_images):
#                         img = self.load_image_from_path(img_path)
#                         if img:
#                             st.image(img, caption=f"Image {i+1}", width=80)
#                         else:
#                             st.error(f"Failed to load image {i+1}")
#                     st.markdown('</div>', unsafe_allow_html=True)
                
#                 st.markdown('</div>', unsafe_allow_html=True)
            
#             # Source link (compact)
#             if meme_data.get('url'):
#                 st.markdown(f"**🔗 [Read Full News]({meme_data['url']})**")
            
#             # Description - enhanced styling
#             description = meme_data.get('description', 'No description available')
#             description_html = f'''
#             <div class="description-box">
#                 <strong>📝 Sarcastic Take:</strong><br>
#                 {description.replace(chr(10), "<br>")}
#             </div>
#             '''
#             st.markdown(description_html, unsafe_allow_html=True)
            
#             # Hashtags - compact display
#             hashtags = meme_data.get('hashtags', [])
#             if hashtags:
#                 st.markdown("**🏷️ Hashtags:**")
#                 hashtag_html = ""
#                 for hashtag in hashtags[:5]:  # Show first 5 hashtags
#                     hashtag_html += f'<span class="hashtag-container">{hashtag}</span> '
#                 st.markdown(hashtag_html, unsafe_allow_html=True)

# def main():
#     # Header
#     st.markdown('<h1 class="main-header">🎭 AI Meme Generator</h1>', unsafe_allow_html=True)
#     st.markdown("""
#     <div style="text-align: center; margin-bottom: 1.5rem;">
#         <p style="font-size: 1.2rem; color: #555; font-weight: 500;">
#             🚀 Generate contextual Tnglish memes from latest news
#             <br>✨ <strong>Features:</strong> Enhanced display • Direct image preview • Context-aware dialogues
#         </p>
#     </div>
#     """, unsafe_allow_html=True)
    
#     # Initialize generator
#     generator = StreamlitMemeGenerator()
    
#     # Generate button
#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         generate_clicked = st.button(
#             "🚀 Generate Memes", 
#             key="generate_memes",
#             help="Generate contextual Tnglish memes with enhanced display",
#             use_container_width=True,
#             type="primary"
#         )
    
#     # Generate workflow
#     if generate_clicked:
#         st.cache_data.clear()
        
#         loading_placeholder = st.empty()
#         with loading_placeholder.container():
#             st.info("🔄 Starting contextual meme generation...")
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             status_text.text("📰 Scraping latest news...")
#             progress_bar.progress(25)
#             time.sleep(0.5)
            
#             status_text.text("🤖 Creating context-aware content...")
#             progress_bar.progress(50)
#             time.sleep(0.5)
            
#             status_text.text("🎨 Generating Tnglish memes...")
#             progress_bar.progress(75)
#             time.sleep(0.5)
            
#             # Generate memes
#             processed_memes, categorized_news = generator.generate_all_memes()
            
#             progress_bar.progress(100)
#             status_text.text("✅ Complete!")
        
#         time.sleep(1)
#         loading_placeholder.empty()
        
#         if processed_memes:
#             st.success(f"🎉 Generated {len(processed_memes)} contextual memes!")
#             st.session_state.generated_memes = processed_memes
#             st.session_state.memes_generated = True
#             st.session_state.categorized_news_data = categorized_news
#         else:
#             st.error("❌ Generation failed. Please try again.")
    
#     # Display memes in enhanced side-by-side layout
#     if hasattr(st.session_state, 'memes_generated') and st.session_state.memes_generated:
#         processed_memes = st.session_state.get('generated_memes', [])
        
#         if processed_memes:
#             # Compact statistics
#             st.markdown("### 📊 Generation Statistics")
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 st.metric("🎭 Total Memes", len(processed_memes))
#             with col2:
#                 categories = list(set([m.get('category', 'unknown') for m in processed_memes]))
#                 st.metric("📂 Categories", len(categories))
#             with col3:
#                 templates_count = len([m for m in processed_memes if m.get('template_image_path')])
#                 st.metric("🎨 Templates", templates_count)
#             with col4:
#                 tnglish_count = len([m for m in processed_memes if generator.is_tnglish(m.get('description', ''))])
#                 st.metric("🌏 Tnglish", tnglish_count)
            
#             st.markdown("---")
#             st.markdown("### 🎭 Your Contextual Memes")
            
#             # Display memes in enhanced pairs
#             for i in range(0, len(processed_memes), 2):
#                 col1, col2 = st.columns(2, gap="medium")
                
#                 # Left meme
#                 with col1:
#                     st.markdown('<div class="meme-container">', unsafe_allow_html=True)
#                     generator.display_compact_meme_block(processed_memes[i], i)
#                     st.markdown('</div>', unsafe_allow_html=True)
                
#                 # Right meme (if exists)
#                 with col2:
#                     if i + 1 < len(processed_memes):
#                         st.markdown('<div class="meme-container">', unsafe_allow_html=True)
#                         generator.display_compact_meme_block(processed_memes[i + 1], i + 1)
#                         st.markdown('</div>', unsafe_allow_html=True)
#                     else:
#                         st.empty()
                
#                 # Add spacing between rows
#                 if i + 2 < len(processed_memes):
#                     st.markdown("<br>", unsafe_allow_html=True)
        
#         # Enhanced action buttons
#         st.markdown("---")
#         st.markdown("### 🔧 Actions")
        
#         col1, col2, col3, col4 = st.columns(4)
        
#         with col1:
#             if st.button("🔄 Generate Fresh", key="regenerate"):
#                 for key in ['memes_generated', 'generated_memes', 'categorized_news_data']:
#                     if key in st.session_state:
#                         del st.session_state[key]
#                 st.cache_data.clear()
#                 st.rerun()
        
#         with col2:
#             if processed_memes:
#                 download_data = {
#                     'generation_info': {
#                         'timestamp': datetime.now().isoformat(),
#                         'total_memes': len(processed_memes),
#                         'contextual_dialogues': True,
#                         'tnglish_support': True
#                     },
#                     'memes': processed_memes
#                 }
#                 json_data = json.dumps(download_data, indent=2, ensure_ascii=False)
#                 st.download_button(
#                     label="💾 Download All",
#                     data=json_data,
#                     file_name=f"contextual_memes_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
#                     mime="application/json"
#                 )
        
#         with col3:
#             if st.button("📊 Detailed Stats", key="stats"):
#                 st.json({
#                     "total_memes": len(processed_memes),
#                     "categories": list(set([m.get('category', 'unknown') for m in processed_memes])),
#                     "templates_matched": len([m for m in processed_memes if m.get('template_image_path')]),
#                     "tnglish_contexts": len([m for m in processed_memes if generator.is_tnglish(m.get('description', ''))]),
#                     "timestamp": datetime.now().isoformat()
#                 })
        
#         with col4:
#             if st.button("🗑️ Clear All", key="clear"):
#                 for key in ['memes_generated', 'generated_memes', 'categorized_news_data']:
#                     if key in st.session_state:
#                         del st.session_state[key]
#                 st.rerun()
    
#     else:
#         # Enhanced instructions
#         st.markdown("### 🎯 Enhanced Features")
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.markdown("""
#             **🔍 Smart Processing:**
#             - Latest Indian news scraping
#             - Context-aware dialogue generation
#             - Enhanced meme display sizing
            
#             **🎨 Visual Improvements:**
#             - Optimized meme dimensions
#             - Direct related image preview
#             - Professional text overlay
#             """)
        
#         with col2:
#             st.markdown("""
#             **🌏 Contextual Intelligence:**
#             - News-specific Tnglish dialogues
#             - Regional context detection
#             - Humor based on actual content
            
#             **📱 User Experience:**
#             - No toggle buttons needed
#             - Instant image visibility
#             - Compact information layout
#             """)
        
#         st.info("👆 Click '**Generate Memes**' to create contextual memes with enhanced display and direct image preview!")

# if __name__ == "__main__":
#     main()












# import streamlit as st
# import json
# import os
# import requests
# from PIL import Image, ImageDraw, ImageFont
# import textwrap
# from io import BytesIO
# import base64
# from datetime import datetime
# import time
# import random
# from pathlib import Path
# import warnings
# import logging
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Suppress warnings
# os.environ['GRPC_VERBOSITY'] = 'ERROR'
# os.environ['GLOG_minloglevel'] = '2'
# warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")
# logging.getLogger('google').setLevel(logging.ERROR)

# # Import your existing classes
# try:
#     from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
#     from gemini_emotion_processor import NewsToMemeProcessor
# except ImportError:
#     st.error("Please ensure enhanced_scraper_with_images.py and gemini_emotion_processor.py are in the same directory")
#     st.stop()

# # Page configuration
# st.set_page_config(
#     page_title="AI Meme Generator", 
#     page_icon="😂", 
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )

# # Custom CSS with improved description styling
# st.markdown("""
# <style>
#     .main-header {
#         text-align: center;
#         color: #FF6B6B;
#         font-size: 3rem;
#         font-weight: bold;
#         margin-bottom: 2rem;
#         text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
#     }
    
#     .meme-container {
#         border: 2px solid #E0E0E0;
#         border-radius: 15px;
#         padding: 20px;
#         margin: 20px 0;
#         background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
#         box-shadow: 0 4px 15px rgba(0,0,0,0.1);
#     }
    
#     .description-box {
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         border: none;
#         border-radius: 15px;
#         padding: 20px;
#         margin: 15px 0;
#         color: white;
#         font-size: 1.2rem;
#         font-weight: 500;
#         line-height: 1.6;
#         box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
#         position: relative;
#         overflow: hidden;
#     }
    
#     .description-box::before {
#         content: '';
#         position: absolute;
#         top: 0;
#         left: 0;
#         right: 0;
#         height: 4px;
#         background: linear-gradient(90deg, #FFD700, #FF6B6B, #4ECDC4);
#     }
    
#     .description-box .emoji {
#         font-size: 1.5rem;
#         margin-right: 10px;
#     }
    
#     .hashtag-container {
#         background: linear-gradient(45deg, #667eea, #764ba2);
#         border-radius: 25px;
#         padding: 12px 24px;
#         margin: 8px;
#         display: inline-block;
#         color: white;
#         font-weight: bold;
#         font-size: 0.9rem;
#         box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
#         transition: transform 0.2s ease;
#     }
    
#     .hashtag-container:hover {
#         transform: translateY(-2px);
#         box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
#     }
    
#     .meme-counter {
#         background: linear-gradient(45deg, #4CAF50, #45a049);
#         color: white;
#         padding: 15px 25px;
#         border-radius: 25px;
#         text-align: center;
#         font-weight: bold;
#         margin: 10px 0;
#         font-size: 1.1rem;
#         box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
#     }
    
#     .related-images-container {
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         border: none;
#         border-radius: 15px;
#         padding: 20px;
#         margin: 15px 0;
#         color: white;
#         box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
#     }
    
#     .template-container {
#         background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%);
#         border: none;
#         border-radius: 15px;
#         padding: 15px;
#         margin: 10px 0;
#         color: white;
#         box-shadow: 0 4px 15px rgba(78, 205, 196, 0.3);
#     }
    
#     .error-container {
#         background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
#         border-radius: 10px;
#         padding: 15px;
#         color: white;
#         margin: 10px 0;
#         box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
#     }
    
#     .success-container {
#         background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
#         border-radius: 10px;
#         padding: 15px;
#         color: white;
#         margin: 10px 0;
#         box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
#     }
# </style>
# """, unsafe_allow_html=True)


# class StreamlitMemeGenerator:
#     def __init__(self):
#         """Initialize the meme generator with proper URL handling"""
#         if 'processors_initialized' not in st.session_state:
#             with st.spinner("🔄 Initializing AI processors..."):
#                 try:
#                     self.news_extractor = EnhancedNewsExtractorWithImages()
#                     self.meme_processor = NewsToMemeProcessor()
#                     st.session_state.processors_initialized = True
#                     st.session_state.news_extractor = self.news_extractor
#                     st.session_state.meme_processor = self.meme_processor
                    
#                     # Get Supabase base URL from environment
#                     self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
#                     if not self.supabase_image_base_url.endswith('/'):
#                         self.supabase_image_base_url += '/'
                    
#                     print(f"Supabase base URL: {self.supabase_image_base_url}")
                    
#                 except Exception as e:
#                     st.error(f"Failed to initialize processors: {e}")
#                     st.stop()
#         else:
#             self.news_extractor = st.session_state.news_extractor
#             self.meme_processor = st.session_state.meme_processor
#             self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
#             if not self.supabase_image_base_url.endswith('/'):
#                 self.supabase_image_base_url += '/'
    
#     def is_tnglish(self, text):
#         """Check if text should be in Tnglish"""
#         telugu_contexts = [
#             'tollywood', 'hyderabad', 'telangana', 'andhra', 'vijay', 'prabhas', 
#             'mahesh', 'allu arjun', 'ram charan', 'chiranjeevi', 'balakrishna',
#             'nagarjuna', 'venkatesh', 'ravi teja', 'ntr', 'pawan kalyan'
#         ]
        
#         text_lower = text.lower()
#         return any(context in text_lower for context in telugu_contexts)
    
#     def construct_image_url(self, image_path):
#         """Construct proper image URL based on path type"""
#         try:
#             if not image_path:
#                 return None
            
#             # If already a complete URL, return as is
#             if image_path.startswith('http://') or image_path.startswith('https://'):
#                 return image_path
            
#             # If it's a Supabase storage path
#             if image_path.startswith('storage/'):
#                 full_url = f"{self.supabase_image_base_url}{image_path}"
#                 print(f"Constructed Supabase URL: {full_url}")
#                 return full_url
            
#             # If it's a local file path (related images)
#             if image_path.startswith('output/') or image_path.startswith('./output/'):
#                 # For local files, we need to read them directly
#                 local_path = image_path.replace('./', '')
#                 if os.path.exists(local_path):
#                     return local_path  # Return local path for direct file reading
#                 else:
#                     print(f"Local file not found: {local_path}")
#                     return None
            
#             # If path starts with /, treat as Supabase path
#             if image_path.startswith('/'):
#                 full_url = f"{self.supabase_image_base_url.rstrip('/')}{image_path}"
#                 print(f"Constructed Supabase URL from /: {full_url}")
#                 return full_url
            
#             return None
            
#         except Exception as e:
#             print(f"Error constructing URL for {image_path}: {e}")
#             return None
    
#     def load_image_from_path(self, image_path):
#         """Load image from various path types with proper error handling"""
#         try:
#             if not image_path:
#                 return None
            
#             # Handle local file paths
#             if image_path.startswith('output/') or image_path.startswith('./output/'):
#                 local_path = image_path.replace('./', '')
#                 if os.path.exists(local_path):
#                     img = Image.open(local_path)
#                     if img.mode != 'RGB':
#                         img = img.convert('RGB')
#                     return img
#                 else:
#                     print(f"Local file not found: {local_path}")
#                     return None
            
#             # Handle URL paths
#             url = self.construct_image_url(image_path)
#             if not url:
#                 return None
            
#             # If it's still a local path after construction
#             if not url.startswith('http'):
#                 if os.path.exists(url):
#                     img = Image.open(url)
#                     if img.mode != 'RGB':
#                         img = img.convert('RGB')
#                     return img
#                 return None
            
#             # Download from URL
#             response = requests.get(url, timeout=10)
#             if response.status_code == 200:
#                 img = Image.open(BytesIO(response.content))
#                 if img.mode != 'RGB':
#                     img = img.convert('RGB')
#                 return img
#             else:
#                 print(f"Failed to download image from {url}: Status {response.status_code}")
#                 return None
                
#         except Exception as e:
#             print(f"Error loading image from {image_path}: {e}")
#             return None
    
#     def overlay_text_on_image(self, image_path, dialogues):
#         """Overlay dialogue text on meme template with better positioning"""
#         try:
#             img = self.load_image_from_path(image_path)
#             if not img:
#                 return None
            
#             draw = ImageDraw.Draw(img)
#             img_width, img_height = img.size
            
#             # Calculate font size based on image dimensions
#             base_font_size = max(24, min(img_width // 20, img_height // 15, 60))
            
#             try:
#                 # Try multiple font paths
#                 font_paths = [
#                     "arial.ttf",
#                     "/System/Library/Fonts/Arial.ttf",  # macOS
#                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
#                     "C:/Windows/Fonts/arial.ttf",  # Windows
#                 ]
                
#                 font = None
#                 for font_path in font_paths:
#                     try:
#                         font = ImageFont.truetype(font_path, base_font_size)
#                         break
#                     except:
#                         continue
                
#                 if not font:
#                     font = ImageFont.load_default()
                    
#             except:
#                 font = ImageFont.load_default()
            
#             if len(dialogues) >= 2:
#                 # Top dialogue
#                 top_text = dialogues[0].upper()  # Make it more impactful
#                 bottom_text = dialogues[1].upper()
                
#                 # Calculate text dimensions more accurately
#                 try:
#                     top_bbox = draw.textbbox((0, 0), top_text, font=font)
#                     top_width = top_bbox[2] - top_bbox[0]
#                     top_height = top_bbox[3] - top_bbox[1]
#                 except:
#                     # Fallback calculation
#                     top_width = len(top_text) * (base_font_size // 2)
#                     top_height = base_font_size
                
#                 # Position top text (higher up for better visibility)
#                 top_x = (img_width - top_width) // 2
#                 top_y = max(10, img_height // 15)  # Higher position
                
#                 # Draw top text with enhanced outline
#                 self.draw_text_with_enhanced_outline(draw, (top_x, top_y), top_text, font)
                
#                 # Calculate bottom text dimensions
#                 try:
#                     bottom_bbox = draw.textbbox((0, 0), bottom_text, font=font)
#                     bottom_width = bottom_bbox[2] - bottom_bbox[0]
#                     bottom_height = bottom_bbox[3] - bottom_bbox[1]
#                 except:
#                     bottom_width = len(bottom_text) * (base_font_size // 2)
#                     bottom_height = base_font_size
                
#                 # Position bottom text (lower for better visibility)
#                 bottom_x = (img_width - bottom_width) // 2
#                 bottom_y = img_height - bottom_height - max(10, img_height // 15)  # Lower position
                
#                 # Draw bottom text with enhanced outline
#                 self.draw_text_with_enhanced_outline(draw, (bottom_x, bottom_y), bottom_text, font)
            
#             return img
            
#         except Exception as e:
#             print(f"Error overlaying text on {image_path}: {e}")
#             return None
    
#     def draw_text_with_enhanced_outline(self, draw, position, text, font, text_color='white', outline_color='black', outline_width=3):
#         """Draw text with enhanced outline for better visibility"""
#         x, y = position
        
#         # Draw thick outline
#         for dx in range(-outline_width, outline_width + 1):
#             for dy in range(-outline_width, outline_width + 1):
#                 if dx != 0 or dy != 0:
#                     draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
#         # Draw main text
#         draw.text(position, text, font=font, fill=text_color)
    
#     def generate_tnglish_dialogues(self, english_dialogues, context):
#         """Convert to Tnglish if Telugu context detected"""
#         if not self.is_tnglish(context):
#             return english_dialogues
        
#         tnglish_patterns = {
#             "when": "eppudu",
#             "everyone": "andaru", 
#             "meanwhile": "antha sepu",
#             "me": "nenu",
#             "that moment": "aa moment",
#             "literally": "literally",
#             "waiting": "wait chestunna",
#             "watching": "chustunna",
#             "thinking": "anukuntunna",
#             "feeling": "feel avutunna",
#             "people": "vallu",
#             "this": "idhi",
#             "that": "adhi",
#             "now": "ippudu",
#             "always": "eppuduu",
#             "what": "enti",
#             "why": "enduku",
#             "how": "ela"
#         }
        
#         tnglish_dialogues = []
#         for dialogue in english_dialogues:
#             tnglish_version = dialogue.lower()
#             for eng, tel in tnglish_patterns.items():
#                 tnglish_version = tnglish_version.replace(eng, tel)
#             tnglish_dialogues.append(tnglish_version.capitalize())
        
#         return tnglish_dialogues
    
#     def find_related_images(self, news_index):
#         """Find related images for a specific news item"""
#         try:
#             if hasattr(st.session_state, 'categorized_news_data'):
#                 categorized_news = st.session_state.categorized_news_data
                
#                 # Create flat list with proper indexing
#                 all_articles = []
#                 for category, articles in categorized_news.items():
#                     for article in articles:
#                         article['scraped_category'] = category
#                         all_articles.append(article)
                
#                 if news_index < len(all_articles):
#                     article = all_articles[news_index]
#                     images = []
                    
#                     # Add main image if exists
#                     if article.get('image_path'):
#                         images.append(article['image_path'])
                    
#                     return images
            
#             return []
#         except Exception as e:
#             print(f"Error finding related images: {e}")
#             return []
    
#     @st.cache_data
#     def generate_all_memes(_self):
#         """Generate all memes and cache results"""
#         try:
#             with st.spinner("📰 Scraping latest news..."):
#                 categorized_news = _self.news_extractor.get_all_news()
#                 if not categorized_news:
#                     return [], {}
                
#                 st.session_state.categorized_news_data = categorized_news
            
#             with st.spinner("🤖 Processing with AI..."):
#                 processed_memes = _self.meme_processor.process_all_news_articles()
#                 if not processed_memes:
#                     return [], categorized_news
            
#             return processed_memes, categorized_news
            
#         except Exception as e:
#             st.error(f"Error generating memes: {e}")
#             return [], {}
    
#     def display_meme_block(self, meme_data, index):
#         """Display single meme block with enhanced styling"""
#         with st.container():
#             st.markdown('<div class="meme-container">', unsafe_allow_html=True)
            
#             # Enhanced meme counter
#             category = meme_data.get('category', 'Unknown').title()
#             st.markdown(f'<div class="meme-counter">🎭 Meme #{index + 1} - {category} Category</div>', unsafe_allow_html=True)
            
#             # Main content layout
#             col1, col2 = st.columns([3, 2])
            
#             with col1:
#                 template_path = meme_data.get('template_image_path', '')
#                 dialogues = meme_data.get('dialogues', [])
                
#                 if template_path and dialogues:
#                     # Language detection and conversion
#                     context = meme_data.get('description', '') + ' ' + str(dialogues)
#                     original_dialogues = dialogues.copy()
                    
#                     if self.is_tnglish(context):
#                         dialogues = self.generate_tnglish_dialogues(dialogues, context)
#                         st.markdown('<div class="success-container">🎯 Tnglish mode activated for regional context!</div>', unsafe_allow_html=True)
                    
#                     # Ensure max 8 words per dialogue
#                     processed_dialogues = []
#                     for dialogue in dialogues[:2]:
#                         words = dialogue.split()[:8]
#                         processed_dialogues.append(' '.join(words))
                    
#                     # Create meme with overlaid text
#                     meme_image = self.overlay_text_on_image(template_path, processed_dialogues)
                    
#                     if meme_image:
#                         st.image(meme_image, use_column_width=True, caption="🎭 AI Generated Meme")
                        
#                         # Original template viewer
#                         with st.expander("🖼️ View Original Template", expanded=False):
#                             st.markdown('<div class="template-container"><strong>📸 Original Template from Supabase</strong></div>', unsafe_allow_html=True)
#                             original_template = self.load_image_from_path(template_path)
#                             if original_template:
#                                 st.image(original_template, caption="Clean template without text overlay", use_column_width=True)
#                             else:
#                                 st.markdown('<div class="error-container">❌ Failed to load original template</div>', unsafe_allow_html=True)
#                     else:
#                         st.markdown('<div class="error-container">❌ Failed to create meme with text overlay</div>', unsafe_allow_html=True)
#                         # Show original template as fallback
#                         original_template = self.load_image_from_path(template_path)
#                         if original_template:
#                             st.image(original_template, caption="Original Template (overlay failed)", use_column_width=True)
#                 else:
#                     st.warning("⚠️ Missing template or dialogues")
#                     if dialogues:
#                         st.write("**Available Dialogues:**")
#                         for i, dialogue in enumerate(dialogues[:2], 1):
#                             st.write(f"  {i}. \"{dialogue}\"")
            
#             with col2:
#                 # Enhanced metadata display
#                 st.markdown("### 📊 Meme Details")
#                 st.write(f"**🏷️ Category:** {category}")
#                 st.write("**💬 Generated Dialogues:**")
                
#                 current_dialogues = dialogues if 'dialogues' in locals() else meme_data.get('dialogues', [])
#                 for i, dialogue in enumerate(current_dialogues[:2], 1):
#                     words_count = len(dialogue.split())
#                     emoji = "✅" if words_count <= 8 else "⚠️"
#                     st.write(f"  {emoji} **{i}.** \"{dialogue}\" ({words_count} words)")
                
#                 if meme_data.get('url'):
#                     st.markdown(f"**🔗 News Source:** [Read Full Article]({meme_data['url']})")
                
#                 # Template status
#                 if template_path:
#                     st.write("**🎨 Template Status:** ✅ Loaded from Supabase")
#                 else:
#                     st.write("**🎨 Template Status:** ❌ Not available")
            
#             # Related Images Section with enhanced styling
#             st.markdown("---")
#             related_images = self.find_related_images(index)
            
#             if related_images:
#                 show_images_key = f"show_images_{index}"
#                 if st.button(f"📸 Show Related News Images ({len(related_images)})", key=show_images_key):
#                     st.markdown('<div class="related-images-container">', unsafe_allow_html=True)
#                     st.markdown("### 📸 Related News Images")
                    
#                     # Display images in responsive grid
#                     if len(related_images) == 1:
#                         img = self.load_image_from_path(related_images[0])
#                         if img:
#                             st.image(img, caption="📰 Related news image", use_column_width=True)
#                         else:
#                             st.markdown('<div class="error-container">❌ Failed to load related image</div>', unsafe_allow_html=True)
#                     else:
#                         # Multiple images grid
#                         cols = st.columns(min(3, len(related_images)))
#                         for i, img_path in enumerate(related_images):
#                             with cols[i % len(cols)]:
#                                 img = self.load_image_from_path(img_path)
#                                 if img:
#                                     st.image(img, caption=f"📰 News image {i+1}", use_column_width=True)
#                                 else:
#                                     st.markdown('<div class="error-container">❌ Failed to load image</div>', unsafe_allow_html=True)
                    
#                     st.markdown('</div>', unsafe_allow_html=True)
#             else:
#                 st.info("📷 No related images found for this news article")
            
#             # Enhanced description section
#             st.markdown("---")
#             description = meme_data.get('description', 'No description available')
#             description_html = f'''
#             <div class="description-box">
#                 <span class="emoji">📝</span><strong>Sarcastic AI Take:</strong><br><br>
#                 {description.replace(chr(10), "<br><br>")}
#             </div>
#             '''
#             st.markdown(description_html, unsafe_allow_html=True)
            
#             # Enhanced hashtags section
#             hashtags = meme_data.get('hashtags', [])
#             if hashtags:
#                 st.markdown("### 🏷️ Viral Hashtags")
#                 hashtag_html = ""
#                 for hashtag in hashtags:
#                     hashtag_html += f'<span class="hashtag-container">{hashtag}</span> '
#                 st.markdown(hashtag_html, unsafe_allow_html=True)
            
#             st.markdown('</div>', unsafe_allow_html=True)
#             st.markdown("<br>", unsafe_allow_html=True)


# def main():
#     # Enhanced header
#     st.markdown('<h1 class="main-header">🎭 AI Meme Generator</h1>', unsafe_allow_html=True)
#     st.markdown("""
#     <div style="text-align: center; margin-bottom: 2rem;">
#         <p style="font-size: 1.3rem; color: #555; font-weight: 500;">
#             🚀 Generate sarcastic memes from latest news with AI-powered humor!
#             <br>✨ <strong>Features:</strong> Template overlay • Tnglish support • Related images • Supabase integration
#         </p>
#     </div>
#     """, unsafe_allow_html=True)
    
#     # Initialize generator
#     generator = StreamlitMemeGenerator()
    
#     # Enhanced generate button
#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         generate_clicked = st.button(
#             "🚀 Generate Memes", 
#             key="generate_memes",
#             help="Generate sarcastic memes from latest Indian news with AI processing",
#             use_container_width=True,
#             type="primary"
#         )
    
#     # Generate memes workflow
#     if generate_clicked:
#         st.cache_data.clear()
        
#         loading_placeholder = st.empty()
#         with loading_placeholder.container():
#             st.info("🔄 Starting meme generation pipeline...")
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             status_text.text("📰 Scraping news from Indian sources...")
#             progress_bar.progress(20)
#             time.sleep(1)
            
#             status_text.text("🤖 Processing content with Gemini AI...")
#             progress_bar.progress(50)
#             time.sleep(1)
            
#             status_text.text("🎨 Matching templates from Supabase...")
#             progress_bar.progress(75)
#             time.sleep(1)
            
#             status_text.text("🖼️ Creating memes with text overlay...")
            
#             # Generate memes
#             processed_memes, categorized_news = generator.generate_all_memes()
            
#             progress_bar.progress(100)
#             status_text.text("✅ Meme generation complete!")
        
#         time.sleep(1)
#         loading_placeholder.empty()
        
#         if processed_memes:
#             st.success(f"🎉 Successfully generated {len(processed_memes)} awesome memes!")
#             st.session_state.generated_memes = processed_memes
#             st.session_state.memes_generated = True
#             st.session_state.categorized_news_data = categorized_news
#         else:
#             st.error("❌ Meme generation failed. Please check your configuration and try again.")
#             if categorized_news:
#                 total_articles = sum(len(articles) for articles in categorized_news.values())
#                 st.info(f"📰 News scraping successful ({total_articles} articles), but AI processing failed.")
    
#     # Display generated memes
#     if hasattr(st.session_state, 'memes_generated') and st.session_state.memes_generated:
#         processed_memes = st.session_state.get('generated_memes', [])
#         categorized_news = st.session_state.get('categorized_news_data', {})
        
#         if processed_memes:
#             # Enhanced statistics dashboard
#             st.markdown("### 📊 Generation Statistics")
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 st.metric("🎭 Total Memes", len(processed_memes), delta="Generated")
#             with col2:
#                 categories = list(set([m.get('category', 'unknown') for m in processed_memes]))
#                 st.metric("📂 Categories", len(categories), delta="Unique")
#             with col3:
#                 templates_count = len([m for m in processed_memes if m.get('template_image_path')])
#                 st.metric("🎨 With Templates", templates_count, delta=f"{(templates_count/len(processed_memes)*100):.0f}%")
#             with col4:
#                 tnglish_count = len([m for m in processed_memes if generator.is_tnglish(m.get('description', ''))])
#                 st.metric("🌏 Tnglish Context", tnglish_count, delta="Regional")
            
#             # Success indicators
#             if processed_memes:
#                 success_rate = (templates_count / len(processed_memes)) * 100
#                 if success_rate >= 80:
#                     st.success(f"🎉 Excellent template matching rate: {success_rate:.1f}%")
#                 elif success_rate >= 60:
#                     st.info(f"✅ Good template matching rate: {success_rate:.1f}%")
#                 else:
#                     st.warning(f"⚠️ Template matching could be improved: {success_rate:.1f}%")
            
#             st.markdown("---")
#             st.markdown("### 🎭 Your Generated Memes Collection")
            
#             # Display all meme blocks
#             for index, meme_data in enumerate(processed_memes):
#                 generator.display_meme_block(meme_data, index)
        
#         # Enhanced action buttons
#         st.markdown("---")
#         st.markdown("### 🔧 Actions & Downloads")
        
#         col1, col2, col3, col4 = st.columns(4)
        
#         with col1:
#             if st.button("🔄 Generate Fresh Memes", key="regenerate", help="Clear cache and generate new memes"):
#                 for key in ['memes_generated', 'generated_memes', 'categorized_news_data']:
#                     if key in st.session_state:
#                         del st.session_state[key]
#                 st.cache_data.clear()
#                 st.rerun()
        
#         with col2:
#             if processed_memes:
#                 download_data = {
#                     'generation_info': {
#                         'timestamp': datetime.now().isoformat(),
#                         'total_memes': len(processed_memes),
#                         'categories': list(set([m.get('category', 'unknown') for m in processed_memes])),
#                         'supabase_base_url': generator.supabase_image_base_url
#                     },
#                     'memes_data': processed_memes
#                 }
#                 json_data = json.dumps(download_data, indent=2, ensure_ascii=False)
#                 st.download_button(
#                     label="💾 Download JSON",
#                     data=json_data,
#                     file_name=f"ai_memes_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
#                     mime="application/json",
#                     help="Download all meme data including metadata"
#                 )
        
#         with col3:
#             if st.button("📊 View Detailed Stats", key="detailed_stats"):
#                 stats_data = {
#                     "generation_summary": {
#                         "total_memes": len(processed_memes),
#                         "successful_templates": len([m for m in processed_memes if m.get('template_image_path')]),
#                         "tnglish_contexts": len([m for m in processed_memes if generator.is_tnglish(m.get('description', ''))]),
#                         "categories": list(set([m.get('category', 'unknown') for m in processed_memes])),
#                         "average_dialogue_length": sum(len(d.split()) for m in processed_memes for d in m.get('dialogues', [])) / max(1, sum(len(m.get('dialogues', [])) for m in processed_memes)),
#                         "generation_timestamp": datetime.now().isoformat()
#                     }
#                 }
#                 st.json(stats_data)
        
#         with col4:
#             if st.button("🗑️ Clear All Data", key="clear_all", help="Remove all generated memes"):
#                 for key in ['memes_generated', 'generated_memes', 'categorized_news_data']:
#                     if key in st.session_state:
#                         del st.session_state[key]
#                 st.success("🧹 All data cleared!")
#                 st.rerun()
    
#     else:
#         # Enhanced instructions
#         st.markdown("### 🎯 How the AI Meme Generator Works")
        
#         feature_col1, feature_col2 = st.columns(2)
        
#         with feature_col1:
#             st.markdown("""
#             **🔍 Intelligent News Processing:**
#             - Scrapes latest news from major Indian sources
#             - Categorizes content (politics, movies, sports, etc.)
#             - Extracts and stores related images locally
            
#             **🤖 AI-Powered Content Creation:**
#             - Uses Gemini AI for sarcastic content generation
#             - Creates viral-worthy descriptions and hashtags
#             - Generates punchy dialogues (max 8 words each)
#             """)
        
#         with feature_col2:
#             st.markdown("""
#             **🎨 Professional Meme Creation:**
#             - Downloads templates from Supabase database
#             - Overlays dialogues with enhanced styling
#             - Proper text positioning and outline effects
            
#             **🌏 Regional Language Support:**
#             - Auto-detects Telugu/South Indian contexts
#             - Converts to Tnglish for better relatability
#             - Supports both English and regional formats
#             """)
        
#         # Enhanced call-to-action
#         st.markdown("""
#         <div style="text-align: center; margin: 2rem 0; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
#             <h3>🚀 Ready to Create Viral Memes?</h3>
#             <p style="font-size: 1.1rem; margin: 1rem 0;">
#                 Click the '<strong>Generate Memes</strong>' button above to start creating your personalized 
#                 sarcastic news memes with professional template overlays and AI-powered humor!
#             </p>
#         </div>
#         """, unsafe_allow_html=True)
        
#         # Feature showcase
#         st.markdown("### ✨ Key Features Showcase")
#         showcase_col1, showcase_col2, showcase_col3 = st.columns(3)
        
#         with showcase_col1:
#             st.markdown("""
#             **🖼️ Template Integration**
#             - Direct Supabase storage access
#             - Professional text overlay system
#             - Enhanced visibility with outlines
#             - Original template preview option
#             """)
        
#         with showcase_col2:
#             st.markdown("""
#             **📸 Related Images**
#             - Shows scraped news images
#             - Click-to-reveal image galleries
#             - Local file system integration
#             - Smart image loading system
#             """)
        
#         with showcase_col3:
#             st.markdown("""
#             **🎯 Smart Features**
#             - Automatic language detection
#             - Tnglish conversion for regional content
#             - Social media ready hashtags
#             - Downloadable JSON export
#             """)


# if __name__ == "__main__":
#     main()

