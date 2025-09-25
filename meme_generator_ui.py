import streamlit as st
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
    st.error("Please ensure enhanced_scraper_with_images.py and gemini_emotion_processor.py are in the same directory")
    st.stop()


# Page configuration
st.set_page_config(
    page_title="AI Meme Generator", 
    page_icon="😂", 
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Enhanced CSS with centered single-column layout
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #FF6B6B;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .meme-container {
        border: 2px solid #E0E0E0;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        max-width: 600px;
        text-align: center;
    }
    
    .meme-image-container {
        margin: 15px 0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        justify-content: center;
    }
    
    .description-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        color: white;
        font-size: 1rem;
        font-weight: 500;
        line-height: 1.4;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
        text-align: left;
    }
    
    .hashtag-container {
        background: linear-gradient(45deg, #667eea, #764ba2);
        border-radius: 15px;
        padding: 8px 15px;
        margin: 5px;
        display: inline-block;
        color: white;
        font-weight: bold;
        font-size: 0.85rem;
        box-shadow: 0 2px 6px rgba(102, 126, 234, 0.2);
    }
    
    .meme-counter {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        padding: 10px 15px;
        border-radius: 15px;
        text-align: center;
        font-weight: bold;
        margin: 10px 0;
        font-size: 1rem;
        box-shadow: 0 3px 8px rgba(76, 175, 80, 0.2);
    }
    
    .related-images-section {
        margin: 15px 0;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    
    .news-link {
        background: linear-gradient(45deg, #FF6B6B, #FF8E8E);
        color: white;
        padding: 10px 20px;
        border-radius: 25px;
        text-decoration: none;
        font-weight: bold;
        margin: 15px 0;
        display: inline-block;
        box-shadow: 0 3px 8px rgba(255, 107, 107, 0.3);
    }
    
    .centered-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        max-width: 800px;
        margin: 0 auto;
    }
    
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
        }
        .meme-container {
            margin: 10px 5px;
            padding: 15px;
        }
    }
</style>
""", unsafe_allow_html=True)


class StreamlitMemeGenerator:
    def __init__(self):
        """Initialize the meme generator with proper URL handling"""
        if 'processors_initialized' not in st.session_state:
            with st.spinner("🔄 Initializing AI processors..."):
                try:
                    self.news_extractor = EnhancedNewsExtractorWithImages()
                    self.meme_processor = NewsToMemeProcessor()
                    st.session_state.processors_initialized = True
                    st.session_state.news_extractor = self.news_extractor
                    st.session_state.meme_processor = self.meme_processor
                    
                    # Get Supabase base URL from environment
                    self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
                    if not self.supabase_image_base_url.endswith('/'):
                        self.supabase_image_base_url += '/'
                    
                    print(f"Supabase base URL: {self.supabase_image_base_url}")
                    
                except Exception as e:
                    st.error(f"Failed to initialize processors: {e}")
                    st.stop()
        else:
            self.news_extractor = st.session_state.news_extractor
            self.meme_processor = st.session_state.meme_processor
            self.supabase_image_base_url = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
            if not self.supabase_image_base_url.endswith('/'):
                self.supabase_image_base_url += '/'
    
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
            
            # If already a complete URL, return as is
            if image_path.startswith('http://') or image_path.startswith('https://'):
                return image_path
            
            # If it's a Supabase storage path
            if image_path.startswith('storage/'):
                full_url = f"{self.supabase_image_base_url}{image_path}"
                return full_url
            
            # If it's a local file path (related images)
            if image_path.startswith('output/') or image_path.startswith('./output/'):
                local_path = image_path.replace('./', '')
                if os.path.exists(local_path):
                    return local_path
                else:
                    return None
            
            # If path starts with /, treat as Supabase path
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
            
            # Handle local file paths
            if image_path.startswith('output/') or image_path.startswith('./output/'):
                local_path = image_path.replace('./', '')
                if os.path.exists(local_path):
                    img = Image.open(local_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    return img
                else:
                    return None
            
            # Handle URL paths
            url = self.construct_image_url(image_path)
            if not url:
                return None
            
            # If it's still a local path after construction
            if not url.startswith('http'):
                if os.path.exists(url):
                    img = Image.open(url)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    return img
                return None
            
            # Download from URL
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
            
            # Calculate responsive font size
            base_font_size = max(16, min(img_width // 25, img_height // 20, 48))
            
            # Try to load font
            font = None
            font_paths = [
                "arial.ttf",
                "/System/Library/Fonts/Arial.ttf",  
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf", 
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux alternative
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
                # Top dialogue processing
                top_text = dialogues[0].upper()
                bottom_text = dialogues[1].upper()
                
                # Calculate maximum text width (80% of image width)
                max_text_width = int(img_width * 0.8)
                
                # Wrap top text into multiple lines
                top_lines = self.wrap_text_to_fit(top_text, font, draw, max_text_width)
                
                # Calculate line height
                try:
                    sample_bbox = draw.textbbox((0, 0), "A", font=font)
                    line_height = sample_bbox[3] - sample_bbox[1] + 4
                except:
                    line_height = base_font_size + 4
                
                # Position top text
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
                
                # Wrap bottom text
                bottom_lines = self.wrap_text_to_fit(bottom_text, font, draw, max_text_width)
                total_bottom_height = len(bottom_lines) * line_height
                
                # Position bottom text
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
        
        # Draw thick outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
        # Draw main text
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
            if hasattr(st.session_state, 'categorized_news_data'):
                categorized_news = st.session_state.categorized_news_data
                
                all_articles = []
                for category, articles in categorized_news.items():
                    for article in articles:
                        article['scraped_category'] = category
                        all_articles.append(article)
                
                if news_index < len(all_articles):
                    article = all_articles[news_index]
                    images = []
                    
                    if article.get('image_path'):
                        images.append(article['image_path'])
                    
                    return images
            
            return []
        except Exception as e:
            print(f"Error finding related images: {e}")
            return []
    
    def process_and_display_meme_streaming(self, processed_memes, categorized_news, index):
        """Process and display individual meme in streaming fashion with corrected order"""
        meme_data = processed_memes[index]
        
        # Initialize placeholder
        meme_placeholder = st.empty()
        
        with meme_placeholder.container():
            # Create centered container
            st.markdown('<div class="centered-content">', unsafe_allow_html=True)
            st.markdown('<div class="meme-container">', unsafe_allow_html=True)
            
            # Meme counter
            st.markdown(f'<div class="meme-counter">🎭 Meme #{index + 1} - {meme_data.get("category", "Unknown").title()}</div>', unsafe_allow_html=True)
            
            # 1. Description (sarcastic take)
            description = meme_data.get('description', 'No description available')
            st.markdown(f"""
            <div class="description-box">
                <strong>📝 Sarcastic Take:</strong><br>
                {description.replace(chr(10), "<br>")}
            </div>
            """, unsafe_allow_html=True)
            
            # 2. Read full news link
            if meme_data.get('url'):
                st.markdown(f'<a href="{meme_data["url"]}" target="_blank" class="news-link">🔗 Read Full News</a>', unsafe_allow_html=True)
            
            # 3. Hashtags
            hashtags = meme_data.get('hashtags', [])
            if hashtags:
                st.markdown("**🏷️ Hashtags:**")
                hashtag_html = ""
                for hashtag in hashtags[:5]:  # Show first 5 hashtags
                    hashtag_html += f'<span class="hashtag-container">{hashtag}</span> '
                st.markdown(hashtag_html, unsafe_allow_html=True)
            
            # 4. Overlayed Template (after hashtags)
            template_path = meme_data.get('template_image_path', '')
            dialogues = meme_data.get('dialogues', [])
            
            if template_path and dialogues:
                # Language detection
                context = meme_data.get('description', '') + ' ' + str(dialogues)
                
                if self.is_tnglish(context):
                    dialogues = self.generate_tnglish_dialogues(dialogues, context)
                    st.success("🎯 Tnglish mode activated!")
                
                # Ensure max 8 words per dialogue
                processed_dialogues = []
                for dialogue in dialogues[:2]:
                    words = dialogue.split()[:8]
                    processed_dialogues.append(' '.join(words))
                
                # Create and display meme (larger size)
                meme_image = self.overlay_text_on_image(template_path, processed_dialogues)
                
                if meme_image:
                    st.markdown('<div class="meme-image-container">', unsafe_allow_html=True)
                    st.image(meme_image, width=500, caption="🎭 Generated Meme")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error("❌ Failed to create meme")
                    original_template = self.load_image_from_path(template_path)
                    if original_template:
                        st.image(original_template, width=500, caption="Original Template")
            else:
                st.warning("⚠️ Missing template or dialogues")
            
            # 5. Related Images (smaller than template - at the end)
            related_images = self.find_related_images(index)
            
            if related_images:
                st.markdown('<div class="related-images-section">', unsafe_allow_html=True)
                st.markdown("**📸 Related News Images:**")
                
                if len(related_images) == 1:
                    img = self.load_image_from_path(related_images[0])
                    if img:
                        st.image(img, width=300, caption="Related news image")
                    else:
                        st.error("Failed to load related image")
                else:
                    # Multiple images in columns
                    cols = st.columns(min(len(related_images), 3))
                    for i, img_path in enumerate(related_images):
                        with cols[i % 3]:
                            img = self.load_image_from_path(img_path)
                            if img:
                                st.image(img, width=200, caption=f"Image {i+1}")
                            else:
                                st.error(f"Failed to load image {i+1}")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    def generate_and_stream_memes(self):
        """Generate and stream memes one by one"""
        try:
            # Step 1: Scrape news
            with st.spinner("📰 Scraping latest news..."):
                categorized_news = self.news_extractor.get_all_news()
                if not categorized_news:
                    st.error("Failed to scrape news")
                    return
                
                st.session_state.categorized_news_data = categorized_news
            
            # Step 2: Process articles one by one
            st.success(f"✅ Found news articles. Starting meme generation...")
            
            processed_memes = self.meme_processor.process_all_news_articles()
            if not processed_memes:
                st.error("Failed to process articles")
                return
            
            st.session_state.generated_memes = processed_memes
            st.session_state.total_memes = len(processed_memes)
            
            # Step 3: Display memes one by one with streaming effect
            st.markdown("### 🎭 Your Contextual Memes")
            
            for i, meme_data in enumerate(processed_memes):
                with st.spinner(f"🎨 Generating meme {i+1}/{len(processed_memes)}..."):
                    time.sleep(0.5)  # Small delay for streaming effect
                    self.process_and_display_meme_streaming(processed_memes, categorized_news, i)
                    
                    # Add separator between memes (except for the last one)
                    if i < len(processed_memes) - 1:
                        st.markdown("---")
            
            st.success(f"🎉 Successfully generated {len(processed_memes)} contextual memes!")
            st.session_state.memes_generated = True
            
        except Exception as e:
            st.error(f"Error during generation: {e}")


def main():
    # Header
    st.markdown('<h1 class="main-header">🎭 AI Meme Generator</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <p style="font-size: 1.2rem; color: #555; font-weight: 500;">
            🚀 Generate contextual Tnglish memes from latest news
            <br>✨ <strong>Features:</strong> Streaming output • Centered display • Context-aware dialogues
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize generator
    generator = StreamlitMemeGenerator()
    
    # Generate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_clicked = st.button(
            "🚀 Generate Streaming Memes", 
            key="generate_memes",
            help="Generate contextual Tnglish memes with streaming output",
            use_container_width=True,
            type="primary"
        )
    
    # Generate workflow with streaming
    if generate_clicked:
        st.cache_data.clear()
        generator.generate_and_stream_memes()
    
    # Action buttons (if memes were generated)
    if hasattr(st.session_state, 'memes_generated') and st.session_state.memes_generated:
        st.markdown("---")
        st.markdown("### 🔧 Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Generate Fresh", key="regenerate"):
                for key in ['memes_generated', 'generated_memes', 'categorized_news_data', 'total_memes']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            if hasattr(st.session_state, 'generated_memes'):
                download_data = {
                    'generation_info': {
                        'timestamp': datetime.now().isoformat(),
                        'total_memes': len(st.session_state.generated_memes),
                        'contextual_dialogues': True,
                        'tnglish_support': True
                    },
                    'memes': st.session_state.generated_memes
                }
                json_data = json.dumps(download_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="💾 Download All",
                    data=json_data,
                    file_name=f"contextual_memes_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("📊 Detailed Stats", key="stats"):
                if hasattr(st.session_state, 'generated_memes'):
                    memes = st.session_state.generated_memes
                    st.json({
                        "total_memes": len(memes),
                        "categories": list(set([m.get('category', 'unknown') for m in memes])),
                        "templates_matched": len([m for m in memes if m.get('template_image_path')]),
                        "tnglish_contexts": len([m for m in memes if generator.is_tnglish(m.get('description', ''))]),
                        "timestamp": datetime.now().isoformat()
                    })
        
        with col4:
            if st.button("🗑️ Clear All", key="clear"):
                for key in ['memes_generated', 'generated_memes', 'categorized_news_data', 'total_memes']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
    else:
        # Enhanced instructions
        st.markdown("### 🎯 Enhanced Features")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🔍 Smart Processing:**
            - Latest Indian news scraping
            - Context-aware dialogue generation
            - Streaming meme output
            
            **🎨 Visual Improvements:**
            - Centered single-column layout
            - Larger meme templates
            - Smaller related images
            """)
        
        with col2:
            st.markdown("""
            **🌏 Contextual Intelligence:**
            - News-specific Tnglish dialogues
            - Regional context detection
            - Humor based on actual content
            
            **📱 User Experience:**
            - Real-time meme generation
            - One-by-one display
            - Clean information layout
            """)
        
        st.info("👆 Click '**Generate Streaming Memes**' to create contextual memes with real-time streaming output!")


if __name__ == "__main__":
    main()










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

