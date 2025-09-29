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
/* Instagram-inspired Design - ORANGISH RED & WHITE */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background: linear-gradient(135deg, #fff5f0 0%, #fef7f0 100%) !important;
    min-height: 100vh;
    padding: 1rem;
}

/* Main Header - MemeGram Banner */
.main-header {
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%);
    padding: 2rem;
    text-align: center;
    margin: 2rem auto;
    max-width: 800px;
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(255, 107, 53, 0.3);
    color: white;
}

#generate-btn {
    background: linear-gradient(135deg, #135dff 0%, #ff0500 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: bold !important;
    padding: 12px 24px !important;
    cursor: pointer;
    margin: 2rem auto;
    max-width: 230px;
    transition: all 0.3s ease-in-out;
}

#generate-btn:hover {
    opacity: 0.95;
    transform: scale(1.05);
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
    color: #ff6b35;
    margin: 0;
    text-shadow: 0 2px 10px rgba(255, 107, 53, 0.1);
}

.section-heading h3 {
    font-size: 1.6rem;
    font-weight: 600;
    color: #ff6b35;
    margin: 0;
    text-shadow: 0 2px 10px rgba(255, 107, 53, 0.1);
}

/* Create MemeGram-style container for the button */
/* GENERATE BUTTON SECTION - CENTERED AND PROMINENT like Streamlit */
.gradio-container .form {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    margin: 3rem auto !important;
    padding: 0 1rem !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    max-width: 100% !important;
}

.gradio-button {
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 50px !important;                /* Rounded like Streamlit */
    font-weight: 800 !important;                   /* Bold like Streamlit */
    font-size: 1.3rem !important;                  /* Larger font */
    padding: 20px 50px !important;                 /* Bigger padding */
    cursor: pointer !important;
    transition: all 0.4s ease !important;          /* Smooth animation */
    min-height: 70px !important;                   /* Fixed height */
    min-width: 300px !important;                   /* Fixed width - won't expand */
    max-width: 300px !important;                   /* Maximum width limit */
    width: 300px !important;                       /* Exact width */
    box-shadow: 0 10px 30px rgba(255, 107, 53, 0.4) !important;
    text-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
    letter-spacing: 1px !important;                /* Spacing like Streamlit */
    text-transform: uppercase !important;          /* Uppercase like Streamlit */
    display: block !important;
    text-align: center !important;
    flex-shrink: 0 !important;                     /* Prevent shrinking */
    flex-grow: 0 !important;                       /* Prevent growing */
}

.gradio-button:hover {
    background: linear-gradient(135deg, #ff8c42 0%, #ff6b35 100%) !important;
    transform: translateY(-5px) scale(1.05) !important;  /* Lift and scale effect */
    box-shadow: 0 20px 50px rgba(255, 107, 53, 0.6) !important;
    color: white !important;
}

.gradio-button:active {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 15px 40px rgba(255, 107, 53, 0.5) !important;
}

/* Ensure button container centers properly */
.gradio-container .form > div {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
}


/* PROFESSIONAL CATEGORY SELECTION */
.gradio-radio {
    margin: 1.5rem auto !important;
    padding: 1.5rem !important;
    background: white !important;
    border-radius: 15px !important;
    box-shadow: 0 4px 15px rgba(255, 107, 53, 0.1) !important;
    border: 2px solid #ffb399 !important;
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
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%) !important;
    border: 2px solid #ff8c42 !important;
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
    box-shadow: 0 4px 12px rgba(255, 140, 66, 0.3) !important;
    text-shadow: 0 1px 6px rgba(0,0,0,0.2) !important;
}

.gradio-radio label:hover {
    background: linear-gradient(135deg, #ff5722 0%, #ff6b35 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(255, 107, 53, 0.4) !important;
    border-color: #ff5722 !important;
}

.gradio-radio input[type="radio"]:checked + label {
    background: linear-gradient(135deg, #ff5722 0%, #e65100 100%) !important;
    box-shadow: 0 6px 20px rgba(255, 87, 34, 0.5) !important;
    transform: translateY(-2px) !important;
    border-color: #e65100 !important;
}

.gradio-radio input[type="radio"] {
    display: none !important;
}

/* Status Message */
.status-message {
    text-align: center;
    padding: 12px 16px;
    background: #fff5f0;
    border: 2px solid #ffb399;
    border-radius: 12px;
    margin: 16px auto;
    max-width: 800px;
    font-weight: 600;
    color: #ff6b35;
}

/* Memes Grid */
.memes-grid {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.category-info {
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%);
    color: white;
    padding: 1.5rem 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 8px 25px rgba(255, 107, 53, 0.3);
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
    border: 2px solid #ffb399;
    border-radius: 15px;
    margin: 2rem auto;
    max-width: 614px;
    box-shadow: 0 8px 25px rgba(255, 107, 53, 0.1);
    overflow: hidden;
    transition: all 0.3s ease;
}

.meme-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 35px rgba(255, 107, 53, 0.2);
    border-color: #ff6b35;
}

/* Post Header - Fix text colors */
.post-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 2px solid #fff5f0;
    background: linear-gradient(135deg, #fff5f0 0%, #fef7f0 100%);
}

.profile-info {
    display: flex;
    align-items: center;
}

.profile-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%);  /* Changed to orangish-red */
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    font-size: 16px;
    color: white;
    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);  /* Changed shadow color */
}

.username {
    font-weight: 600;
    font-size: 14px;
    color: #ff6b35;  /* Changed to orangish-red */
}

.location {
    font-size: 12px;
    color: #e65100;  /* Changed to darker orangish-red */
    margin-top: 2px;
}

.menu-dots {
    font-size: 16px;
    cursor: pointer;
    color: #ff6b35;  /* Changed to orangish-red */
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
    background: #fff5f0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ff6b35;
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
    color: #ff6b35;  /* Changed to orangish-red */
}

/* Post Content - Fix text colors */
.post-content {
    padding: 0 16px 16px;
    background: white;
}

.likes {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 8px;
    color: #ff6b35;  /* Changed to orangish-red */
}

.caption {
    margin-bottom: 12px;
    line-height: 18px;
    font-size: 14px;
}

.caption .username {
    font-weight: 600;
    margin-right: 8px;
    color: #ff6b35;  /* Changed to orangish-red */
}

.description-text {
    color: #374151;  /* Dark gray for better readability */
    word-wrap: break-word;
}

/* News Link */
.news-link {
    margin: 12px 0;
    padding: 12px;
    background: linear-gradient(135deg, #ff6b35 0%, #ff8c42 100%);  /* Changed to orangish-red */
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);  /* Changed shadow */
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
    color: #ff6b35;  /* Changed to orangish-red */
    background: #fff5f0;  /* Light orangish background */
    padding: 4px 8px;
    border-radius: 12px;
    font-weight: 600;
    margin-right: 8px;
    margin-bottom: 4px;
    cursor: pointer;
    font-size: 13px;
    display: inline-block;
    border: 1px solid #ffb399;  /* Changed border color */
    transition: all 0.2s ease;
}

.hashtag:hover {
    background: #ff6b35;  /* Changed to orangish-red */
    color: white;
}

/* Related Images Mini Block */
.related-images-mini {
    margin: 16px 0;
    padding: 12px;
    background: #fff5f0;  /* Light orangish background */
    border-radius: 12px;
    border: 2px solid #ffb399;  /* Changed border color */
}

.related-title {
    margin: 0 0 10px 0;
    font-size: 13px;
    font-weight: 600;
    color: #ff6b35;  /* Changed to orangish-red */
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
    border: 1px solid #ffb399;  /* Changed border color */
    transition: all 0.2s ease;
}

.related-mini-image:hover {
    transform: scale(1.05);
    border-color: #ff6b35;  /* Changed to orangish-red */
}

/* Timestamp */
.timestamp {
    font-size: 12px;
    color: #e65100;  /* Changed to darker orangish-red */
    text-transform: uppercase;
    margin-top: 16px;
}

/* Empty State */
.empty-state {
    background: white;
    border: 2px solid #ffb399;  /* Changed border color */
    border-radius: 15px;
    margin: 2rem auto;
    max-width: 614px;
    box-shadow: 0 8px 25px rgba(255, 107, 53, 0.1);  /* Changed shadow */
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
    
    .gradio-radio, .gradio-container .form {
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
        
        generate_btn = gr.Button("🎭 Generate Memes",elem_id="generate-btn")
        
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
