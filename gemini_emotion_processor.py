import requests
import json
from typing import List, Dict
import random
import google.generativeai as genai
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import time
import hashlib
from urllib.parse import urlparse
import re
import base64  # Added for base64 encoding


# Load environment variables
load_dotenv()


class GeminiEmotionProcessor:
    def __init__(self):
        """Initialize Multiple Gemini AI instances and Supabase for emotion-based meme generation"""
        
        # MULTIPLE GEMINI API KEYS SETUP
        self.api_keys = [
            os.getenv('GEMINI_API_KEY_1'),
            os.getenv('GEMINI_API_KEY_2'),
            os.getenv('GEMINI_API_KEY_3'),
            os.getenv('GEMINI_API_KEY_4')
        ]
        
        # Filter out None values
        self.api_keys = [key for key in self.api_keys if key]
        
        if not self.api_keys:
            raise Exception("No GEMINI_API_KEY found in .env file")
        
        # Create multiple Gemini model instances
        self.gemini_models = []
        for i, api_key in enumerate(self.api_keys, 1):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash-lite')
                self.gemini_models.append({
                    'model': model,
                    'key_index': i,
                    'api_key': api_key[:8] + '...',  # For logging
                    'calls_made': 0,
                    'last_call_time': 0
                })
            except Exception as e:
                print(f"Warning: Failed to initialize API key {i}: {e}")
        
        if not self.gemini_models:
            raise Exception("Failed to initialize any Gemini models")
        
        print(f"Successfully initialized {len(self.gemini_models)} Gemini model instances")
        
        # API Key rotation settings
        self.current_key_index = 0
        self.max_calls_per_key_per_minute = 15  # Per API key limit
        self.calls_per_key = {i: [] for i in range(len(self.gemini_models))}
        
        # SUPABASE SETUP
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
            
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("Supabase connected successfully")
        
        # Get Supabase image base URL from environment
        self.supabase_image_base = os.getenv('SUPABASE_IMAGE_BASE_URL', 'https://ixnbfvyeniksbqcfdmdo.supabase.co/')
        print(f"Supabase image base URL: {self.supabase_image_base}")
        
        # Load emotions from database
        self.emotions_db = self.load_emotions_from_supabase()
        
        # Focus on major categories
        self.major_categories = ['politics', 'entertainment', 'movies', 'sports', 'business', 'technology', 'crime']


    def get_next_available_model(self):
        """Get the next available Gemini model with rate limiting per key"""
        current_time = time.time()
        
        # Try each model starting from current index
        for attempt in range(len(self.gemini_models)):
            model_index = (self.current_key_index + attempt) % len(self.gemini_models)
            model_info = self.gemini_models[model_index]
            
            # Clean old timestamps for this key
            self.calls_per_key[model_index] = [
                t for t in self.calls_per_key[model_index] 
                if current_time - t < 60
            ]
            
            # Check if this key has capacity
            if len(self.calls_per_key[model_index]) < self.max_calls_per_key_per_minute:
                # Update current key index for next call
                self.current_key_index = (model_index + 1) % len(self.gemini_models)
                return model_index, model_info
        
        # If no key has capacity, wait and use the first one
        wait_time = 60 - (current_time - min(self.calls_per_key[0])) + 1
        print(f"All API keys at limit. Waiting {wait_time:.1f} seconds...")
        time.sleep(wait_time)
        
        # Clear the oldest key's calls and use it
        self.calls_per_key[0] = []
        return 0, self.gemini_models[0]


    def safe_gemini_call(self, prompt: str, retries: int = 2) -> str:
        """Make Gemini API call with automatic key rotation and rate limiting"""
        
        for attempt in range(retries):
            try:
                # Get next available model
                model_index, model_info = self.get_next_available_model()
                
                # Record the call
                current_time = time.time()
                self.calls_per_key[model_index].append(current_time)
                model_info['calls_made'] += 1
                model_info['last_call_time'] = current_time
                
                print(f"Using API Key #{model_info['key_index']} ({model_info['api_key']}) - Call #{model_info['calls_made']}")
                
                # Make the API call
                response = model_info['model'].generate_content(prompt)
                
                # Small delay to be respectful
                time.sleep(1)
                
                return response.text.strip()
                
            except Exception as e:
                print(f"API Key #{model_info['key_index']} failed (attempt {attempt + 1}/{retries}): {e}")
                
                if attempt < retries - 1:
                    # Wait before retry with different key
                    time.sleep(3)
                else:
                    # Last attempt failed
                    raise Exception(f"All API call attempts failed: {e}")


    def load_emotions_from_supabase(self) -> Dict[str, Dict]:
        """Load all emotions from Supabase dc.emotions table"""
        try:
            print("Loading emotions from Supabase dc.emotions table...")
            response = self.supabase.schema('dc').table('emotions').select('*').execute()
            
            if response.data:
                emotions_dict = {}
                for emotion in response.data:
                    emotion_label = emotion['emotion_label'].lower()
                    emotions_dict[emotion_label] = {
                        'emotion_id': emotion['emotion_id'],
                        'emotion_label': emotion['emotion_label'],
                        'description': emotion['description']
                    }
                
                print(f"Loaded {len(emotions_dict)} emotions from database")
                return emotions_dict
            else:
                print("No emotions found in database")
                return {}
                
        except Exception as e:
            print(f"Error loading emotions from Supabase: {e}")
            return {}


    def download_template_as_base64(self, template_path: str, emotion: str) -> str:
        """Download template image and return as base64 string only"""
        try:
            if not template_path:
                return None
            
            # Construct full image URL using environment variable
            if template_path.startswith('http'):
                full_image_url = template_path
            elif template_path.startswith('/'):
                full_image_url = self.supabase_image_base.rstrip('/') + template_path
            else:
                full_image_url = self.supabase_image_base.rstrip('/') + '/' + template_path
                
            print(f"Downloading template from: {full_image_url}")
            
            # Download the image with proper headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache'
            }
            
            response = requests.get(full_image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check if we got actual image content
            content_type = response.headers.get('content-type', 'image/jpeg')
            if not content_type.startswith('image/'):
                print(f"Warning: Content-Type is {content_type}, assuming image")
            
            # Check image size
            if len(response.content) < 1000:
                print(f"Warning: Image too small ({len(response.content)} bytes)")
                return None
            
            # Convert to base64
            base64_data = base64.b64encode(response.content).decode('utf-8')
            
            print(f"Template converted to base64 successfully")
            print(f"Base64 size: {len(base64_data)} characters")
            print(f"Original size: {len(response.content)} bytes")
            
            return base64_data
            
        except requests.exceptions.RequestException as e:
            print(f"Network error downloading template: {e}")
            return None
        except Exception as e:
            print(f"Error downloading template: {e}")
            return None


    def call_gemini_for_category(self, title: str, content: str, fallback_category: str) -> str:
        """Categorize news using Gemini AI with multi-key rotation"""
        try:
            major_cats = "politics, entertainment, movies, sports, business, technology, crime"
            
            prompt = f"""
            Classify this news into ONE of these major categories: {major_cats}
            
            Title: {title}
            Content: {content[:1000]}
            
            Rules:
            - Choose the MOST relevant category
            - If it's about films/cinema/actors/bollywood, use "movies"
            - If it's about TV shows/music/celebrities/awards, use "entertainment"  
            - If it's about police/arrest/murder/fraud/court cases, use "crime"
            - Return ONLY the category name in lowercase, no other text
            
            Category:
            """
            
            category = self.safe_gemini_call(prompt).lower()
            
            if category in self.major_categories:
                return category
            if category in ['health', 'international', 'general']:
                return 'entertainment'
                
            return fallback_category if fallback_category in self.major_categories else 'entertainment'
            
        except Exception as e:
            print(f"Error classifying category: {e}")
            return fallback_category if fallback_category in self.major_categories else 'entertainment'


    def call_gemini_for_buzzy_summary(self, title: str, content: str, category: str) -> str:
        """Generate buzzy 2-line summary using Gemini AI with multi-key rotation"""
        try:
            prompt = f"""
            You are a social media content creator. Create a buzzy, engaging summary for this {category} news:
            
            Title: {title}
            Content: {content}
            
            Instructions:
            - Read and understand the full content provided
            - Create a 2-line maximum buzzy summary that elaborates on the key points
            - Make it exciting and viral-worthy for social media
            - Use casual, engaging language
            - Focus on the most interesting/shocking aspects
            - Do NOT include emojis in your response
            - Maximum 2 lines, make each line impactful
            
            Buzzy Summary:
            """
            
            summary = self.safe_gemini_call(prompt)
            lines = [l.strip() for l in summary.split('\n') if l.strip()]
            return '\n'.join(lines[:2]) if len(lines) > 1 else (lines[0] if lines else title)
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return title


    def analyze_emotion_in_summary(self, news_summary: str) -> Dict[str, any]:
        """Analyze emotion in news summary using Gemini AI with multi-key rotation"""
        try:
            # Create emotion options from database
            emotion_options = []
            for label, data in self.emotions_db.items():
                emotion_options.append(f"- {label}: {data['description']}")
            
            emotion_list_str = '\n'.join(emotion_options)
            
            prompt = f"""
            Analyze the emotion in this news summary and match it to ONE of the available emotions from the database.
            
            Available emotions with descriptions:
            {emotion_list_str}
            
            News Summary: "{news_summary}"
            
            Instructions:
            1. Read the news summary carefully
            2. Understand the dominant emotion/feeling it conveys  
            3. Match it to the BEST fitting emotion from the list above
            4. Consider the context, tone, and emotional impact
            5. Return ONLY the emotion label in lowercase (e.g., "disgust", "excitement", "surprised")
            
            No explanation needed, just the emotion label:
            """
            
            detected_emotion = self.safe_gemini_call(prompt).lower()
            
            # Validate emotion exists in database
            if detected_emotion in self.emotions_db:
                emotion_data = self.emotions_db[detected_emotion]
                print(f"Detected emotion: {detected_emotion}")
                
                return {
                    'detected_emotion': detected_emotion,
                    'emotion_id': emotion_data['emotion_id'],
                    'description': emotion_data['description'],
                    'confidence': 'high'
                }
            else:
                print(f"Unknown emotion detected: {detected_emotion}, using fallback")
                if self.emotions_db:
                    fallback_emotion = list(self.emotions_db.keys())[0]
                    emotion_data = self.emotions_db[fallback_emotion]
                    
                    return {
                        'detected_emotion': fallback_emotion,
                        'emotion_id': emotion_data['emotion_id'],
                        'description': emotion_data['description'],
                        'confidence': 'fallback'
                    }
                else:
                    return {
                        'detected_emotion': 'neutral',
                        'emotion_id': '',
                        'description': 'No emotions available',
                        'confidence': 'error'
                    }
                
        except Exception as e:
            print(f"Error in emotion analysis: {e}")
            return {
                'detected_emotion': 'neutral',
                'emotion_id': '',
                'description': 'Error fallback',
                'confidence': 'error'
            }


    def get_template_from_supabase(self, emotion_id: str) -> str:
        """Get meme template from Supabase dc.memes_dc table"""
        try:
            print(f"Fetching template for emotion_id: {emotion_id}")
            
            response = self.supabase.schema('dc').table('memes_dc').select('*').eq('emotion_id', emotion_id).execute()
            
            if response.data:
                selected_template = random.choice(response.data)
                image_path = selected_template.get('image_path', '')
                print(f"Found template: {image_path}")
                return image_path
            else:
                print(f"No template found for emotion_id: {emotion_id}")
                return None
                
        except Exception as e:
            print(f"Error fetching template: {e}")
            return None


    def generate_meme_captions(self, news_summary: str, emotion: str) -> List[str]:
        """Generate REAL meme dialogue captions using multi-key rotation"""
        
        max_attempts = 4  # Try up to 4 times with different dialogue prompts
        
        dialogue_prompts = [
            f"""
            You are a professional memer creating viral content. Generate 2 meme dialogue captions for this news:
            
            News: "{news_summary}"
            Emotion: {emotion}
            
            Create captions like real memers do - use these patterns:
            - "When [situation]" (max 8 words)
            - "Me trying to [action]" (max 8 words)
            - "That moment when [situation]" (max 8 words)
            - "[Someone]: [dialogue]" (max 8 words)
            - "POV: You [situation]" (max 8 words)
            - "Everyone: [reaction]" (max 8 words)
            
            Make them sarcastic, relatable, and viral-worthy. Return ONLY as JSON array:
            ["caption 1", "caption 2"]
            """,
            
            f"""
            Create 2 meme dialogues about this news. Think like a Gen-Z memer:
            
            News: "{news_summary}"
            
            Use real meme dialogue formats:
            - Internal monologue: "Me: [thought]"
            - Reaction dialogue: "[Person]: [reaction]" 
            - Situation comedy: "When you [action]"
            - Relatable moments: "That feeling when [situation]"
            
            Each caption maximum 8 words. Make it funny and shareable.
            
            JSON format: ["dialogue 1", "dialogue 2"]
            """,
            
            f"""
            Write 2 meme captions as if you're commenting on this news in a group chat:
            
            News: "{news_summary}"
            
            Style: Casual, sarcastic, relatable
            Format: Short dialogue/commentary (max 8 words each)
            
            Examples:
            - "Government: Trust us. Everyone: Sure bro"
            - "Me explaining why I'm broke"
            - "When politicians make new promises"
            
            Return: ["caption 1", "caption 2"]
            """,
            
            f"""
            Generate 2 viral meme captions for: {news_summary}
            
            Requirements:
            - Sound like real internet slang
            - Maximum 8 words each
            - Use formats: "POV:", "Me:", "When", "Everyone:"
            - Make it relatable and funny
            - Think Reddit/Twitter meme style
            
            JSON: ["caption 1", "caption 2"]
            """
        ]
        
        for attempt in range(max_attempts):
            try:
                print(f"Meme dialogue generation attempt {attempt + 1}/{max_attempts}")
                
                prompt = dialogue_prompts[attempt]
                captions_text = self.safe_gemini_call(prompt)
                print(f"Raw meme response: {captions_text[:150]}...")
                
                captions = self.extract_dialogue_captions(captions_text)
                
                if captions and len(captions) >= 2:
                    final_dialogues = []
                    for caption in captions[:2]:
                        words = caption.strip().split()
                        if 3 <= len(words) <= 8:
                            final_dialogues.append(' '.join(words))
                        elif len(words) > 8:
                            truncated = ' '.join(words[:8])
                            final_dialogues.append(truncated)
                        elif len(words) >= 2:
                            final_dialogues.append(' '.join(words))
                    
                    if len(final_dialogues) >= 2:
                        print(f"SUCCESS! Generated meme dialogues: {final_dialogues}")
                        return final_dialogues[:2]
                
                print(f"Attempt {attempt + 1} failed, trying different dialogue style...")
                
            except Exception as e:
                print(f"Error in dialogue attempt {attempt + 1}: {e}")
                if attempt == max_attempts - 1:
                    print("All dialogue attempts failed!")
        
        raise Exception(f"Failed to generate meme dialogues after {max_attempts} attempts. News: {news_summary[:50]}...")


    def extract_dialogue_captions(self, response_text: str) -> List[str]:
        """Extract meme dialogue captions from Gemini response"""
        captions = []
        
        # Method 1: JSON extraction
        try:
            json_pattern = r'\[.*?\]'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(0)
                parsed = json.loads(json_text)
                if isinstance(parsed, list):
                    captions = [str(item).strip().strip('"').strip("'") for item in parsed]
                    if len(captions) >= 2:
                        print(f"JSON dialogue extraction: {captions}")
                        return captions
        except:
            pass
        
        # Method 2: Quoted dialogue extraction
        try:
            quotes_pattern = r'"([^"]+)"|\'([^\']+)\''
            matches = re.findall(quotes_pattern, response_text)
            for match in matches:
                caption = match[0] if match[0] else match[1]
                if len(caption.split()) >= 2:
                    captions.append(caption.strip())
            
            if len(captions) >= 2:
                print(f"Quotes dialogue extraction: {captions}")
                return captions
        except:
            pass
        
        # Method 3: Dialogue pattern extraction  
        try:
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                
                dialogue_patterns = [
                    r'^[1-9]\.\s*(.+)',
                    r'^[-*]\s*(.+)', 
                    r'^(.+:.+)',
                    r'^(When .+)',
                    r'^(Me .+)',
                    r'^(POV:.+)',
                    r'^(That .+)',
                ]
                
                for pattern in dialogue_patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        dialogue = match.group(1).strip().strip('"').strip("'")
                        if 2 <= len(dialogue.split()) <= 10:
                            captions.append(dialogue)
                        break
            
            if len(captions) >= 2:
                print(f"Pattern dialogue extraction: {captions[:2]}")
                return captions[:2]
        except:
            pass
        
        print("All dialogue extraction methods failed")
        return []


    def generate_hashtags(self, news_summary: str, category: str) -> List[str]:
        """Generate trending hashtags using Gemini AI with multi-key rotation"""
        try:
            prompt = f"""
            Generate 6-8 trending hashtags for this news summary. Make them viral, catchy, and perfect for social media.
            
            News Summary: "{news_summary}"
            Category: {category}
            
            Instructions:
            - Create hashtags that are relevant and trending
            - Mix general and specific hashtags
            - Include category-specific tags
            - Make them viral-worthy and shareable
            - Return as a JSON array of strings
            - Each hashtag should start with #
            
            Example: ["#BreakingNews", "#Trending", "#Viral", "#Politics", "#NewsUpdate"]
            
            Generate hashtags:
            """
            
            hashtags_text = self.safe_gemini_call(prompt)
            
            try:
                hashtags = json.loads(hashtags_text)
                if isinstance(hashtags, list) and len(hashtags) > 0:
                    print(f"Generated {len(hashtags)} hashtags")
                    return hashtags[:8]
            except json.JSONDecodeError:
                hashtags = re.findall(r'#\w+', hashtags_text)
                if hashtags:
                    return hashtags[:8]
            
            return [f"#{category.title()}", "#News", "#Trending", "#Viral", "#Breaking", "#Update"]
            
        except Exception as e:
            print(f"Error generating hashtags: {e}")
            return [f"#{category.title()}", "#News", "#Trending", "#Update"]


    def get_api_usage_stats(self):
        """Get current API usage statistics"""
        stats = []
        for i, model_info in enumerate(self.gemini_models):
            current_calls = len([t for t in self.calls_per_key[i] if time.time() - t < 60])
            stats.append({
                'key_index': model_info['key_index'],
                'api_key': model_info['api_key'],
                'total_calls': model_info['calls_made'],
                'calls_last_minute': current_calls,
                'capacity_remaining': self.max_calls_per_key_per_minute - current_calls
            })
        return stats


    def process_news_with_emotion_templates(self, news_data: Dict[str, List[Dict]]) -> List[Dict]:
        """Process news with multi-key Gemini AI and emotion-based templates - returns base64 templates in clean format"""
        all_news = []
        for category_list in news_data.values():
            all_news.extend(category_list)
        
        processed_memes = []
        
        # With 4 API keys, we can process more items
        max_items = min(len(all_news), 20)  # Increased from 10 to 20
        print(f"Processing {max_items} news items with {len(self.gemini_models)} API keys...")
        
        for i, news_item in enumerate(all_news[:max_items], 1):
            print(f"\n{'='*70}")
            print(f"Processing item {i}/{max_items}: {news_item['title'][:50]}...")
            
            # Show current API usage
            stats = self.get_api_usage_stats()
            active_keys = [s for s in stats if s['capacity_remaining'] > 0]
            print(f"API Keys Status: {len(active_keys)}/{len(stats)} keys available")
            
            try:
                # Step 1: Categorize news
                print("Step 1: Categorizing...")
                category = self.call_gemini_for_category(
                    news_item['title'], 
                    news_item['content'], 
                    news_item.get('category', 'entertainment')
                )
                
                if category not in self.major_categories:
                    print(f"Category '{category}' not in major categories, skipping...")
                    continue
                
                # Step 2: Generate buzzy summary
                print("Step 2: Generating summary...")
                news_summary = self.call_gemini_for_buzzy_summary(
                    news_item['title'], 
                    news_item['content'], 
                    category
                )
                print(f"Summary: {news_summary[:50]}...")
                
                # Step 3: Analyze emotion in summary
                print("Step 3: Analyzing emotion...")
                emotion_analysis = self.analyze_emotion_in_summary(news_summary)
                print(f"Emotion: {emotion_analysis['detected_emotion']}")
                
                # Step 4: Get template from Supabase
                print("Step 4: Fetching template...")
                template_url = self.get_template_from_supabase(emotion_analysis['emotion_id'])
                
                if not template_url:
                    print("No template found, skipping...")
                    continue
                
                # Step 5: Download template as base64 (NO LOCAL SAVING)
                print("Step 5: Converting template to base64...")
                template_base64 = self.download_template_as_base64(template_url, emotion_analysis['detected_emotion'])
                
                if not template_base64:
                    print("Template base64 conversion failed, skipping...")
                    continue
                
                # Step 6: Generate meme dialogues
                print("Step 6: Generating meme dialogues...")
                try:
                    meme_captions = self.generate_meme_captions(news_summary, emotion_analysis['detected_emotion'])
                    print(f"Generated dialogues: {meme_captions}")
                except Exception as caption_error:
                    print(f"CRITICAL: Meme dialogue generation failed: {caption_error}")
                    print("Skipping this item")
                    continue
                
                # Step 7: Generate hashtags
                print("Step 7: Generating hashtags...")
                hashtags = self.generate_hashtags(news_summary, category)
                
                # Step 8: Create final meme data - EXACT FORMAT YOU REQUESTED
                meme_data = {
                    "template": template_base64,  # base64 string instead of file path
                    "captions": meme_captions,
                    "summary": news_summary,
                    "hashtags": hashtags,
                    "url": news_item.get('url', '')
                }
                
                processed_memes.append(meme_data)
                print(f"SUCCESS! Complete meme created with base64 template!")
                
                print(f"Progress: {i}/{max_items} items | Generated: {len(processed_memes)} memes")
                
            except Exception as e:
                print(f"ERROR processing item {i}: {e}")
                continue
        
        # Final statistics
        final_stats = self.get_api_usage_stats()
        total_calls = sum(s['total_calls'] for s in final_stats)
        
        print(f"\n{'='*70}")
        print(f"FINAL RESULT: Generated {len(processed_memes)} memes using {len(self.gemini_models)} API keys")
        print(f"Total API calls made: {total_calls}")
        print("API Key Usage:")
        for stat in final_stats:
            print(f"  Key #{stat['key_index']}: {stat['total_calls']} calls")
        
        return processed_memes
