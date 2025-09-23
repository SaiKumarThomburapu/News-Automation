# gemini_emotion_processor.py

import json
import requests
from typing import List, Dict, Optional
import random
import google.generativeai as genai
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import time
import hashlib
from pathlib import Path
from datetime import datetime
import re
import glob
from difflib import SequenceMatcher
import logging
import warnings

# Suppress Google Cloud warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")

# Load environment variables
load_dotenv()

class NewsToMemeProcessor:
    def __init__(self):
        """Initialize Gemini AI and Supabase for sarcastic news processing"""
        
        # Suppress additional Google logging
        logging.getLogger('google').setLevel(logging.ERROR)
        logging.getLogger('googleapiclient').setLevel(logging.ERROR)
        
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
        
        print(f"Found {len(self.api_keys)} API keys")
        
        # API Key rotation settings
        self.current_key_index = 0
        self.max_calls_per_key_per_minute = 10  # Reduced for safety
        self.calls_per_key = {i: [] for i in range(len(self.api_keys))}
        
        # SUPABASE SETUP
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
            
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("Supabase connected successfully")
        
        # Load emotions from database
        self.emotions_db = self.load_emotions_from_supabase()

    def find_latest_news_json(self, output_directory: str = './output') -> str:
        """Automatically find the latest news JSON file from scraper"""
        try:
            print(f"Searching for latest news JSON file in: {output_directory}")
            
            json_pattern = os.path.join(output_directory, 'news_data_*.json')
            json_files = glob.glob(json_pattern)
            
            if not json_files:
                print("No news_data_*.json files found in output directory")
                return None
            
            latest_file = max(json_files, key=os.path.getmtime)
            mod_time = os.path.getmtime(latest_file)
            readable_time = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"Found latest news JSON file:")
            print(f"   File: {os.path.basename(latest_file)}")
            print(f"   Modified: {readable_time}")
            
            return latest_file
            
        except Exception as e:
            print(f"Error finding latest JSON file: {e}")
            return None

    def get_next_available_key_index(self) -> int:
        """Get next available API key index with proper rotation"""
        current_time = time.time()
        
        for attempt in range(len(self.api_keys)):
            key_index = (self.current_key_index + attempt) % len(self.api_keys)
            
            # Clean old timestamps for this key
            self.calls_per_key[key_index] = [
                t for t in self.calls_per_key[key_index] 
                if current_time - t < 60
            ]
            
            current_calls = len(self.calls_per_key[key_index])
            if current_calls < self.max_calls_per_key_per_minute:
                self.current_key_index = (key_index + 1) % len(self.api_keys)
                return key_index
        
        # If all keys are at limit, wait
        print("All API keys at rate limit. Waiting 65 seconds...")
        time.sleep(65)
        
        # Clear all keys and reset
        for i in range(len(self.api_keys)):
            self.calls_per_key[i] = []
        self.current_key_index = 1
        return 0

    def safe_gemini_call(self, prompt: str, retries: int = 3) -> str:
        """Make Gemini API call with proper key rotation"""
        for attempt in range(retries):
            try:
                key_index = self.get_next_available_key_index()
                api_key = self.api_keys[key_index]
                
                print(f"Using API Key #{key_index + 1}")
                
                # Configure Gemini with error suppression
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.0-flash-lite')
                
                # Record the call
                current_time = time.time()
                self.calls_per_key[key_index].append(current_time)
                
                # Make the API call
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    response = model.generate_content(prompt)
                
                time.sleep(3)  # Rate limiting delay
                return response.text.strip()
                
            except Exception as e:
                error_msg = str(e)
                if "ALTS creds ignored" not in error_msg:
                    print(f"API Key #{key_index + 1} failed: {error_msg}")
                
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    clean_error = error_msg.replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
                    raise Exception(f"All API attempts failed: {clean_error}")

    def load_emotions_from_supabase(self) -> Dict[str, Dict]:
        """Load emotions from Supabase"""
        try:
            print("Loading emotions from Supabase...")
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
            print(f"Error loading emotions: {e}")
            return {}

    def find_emotion_similarity(self, target_emotion: str, emotions_list: List[str]) -> str:
        """Find the most similar emotion using text similarity"""
        if not emotions_list:
            return ""
        
        target_lower = target_emotion.lower().strip()
        
        # First try exact match
        for emotion in emotions_list:
            if emotion.lower().strip() == target_lower:
                return emotion
        
        # Then try similarity matching
        best_match = ""
        best_ratio = 0.0
        
        for emotion in emotions_list:
            similarity = SequenceMatcher(None, target_lower, emotion.lower().strip()).ratio()
            if similarity > best_ratio:
                best_ratio = similarity
                best_match = emotion
        
        if best_ratio > 0.5:
            return best_match
        
        return emotions_list[0] if emotions_list else ""

    def get_template_from_supabase_smart(self, detected_emotion: str) -> str:
        """Get meme template from Supabase with exact or nearest emotion matching"""
        try:
            # First, get exact emotion_id match
            if detected_emotion in self.emotions_db:
                emotion_id = self.emotions_db[detected_emotion]['emotion_id']
                
                response = self.supabase.schema('dc').table('memes_dc').select('*').eq('emotion_id', emotion_id).execute()
                
                if response.data:
                    selected_template = random.choice(response.data)
                    image_path = selected_template.get('image_path', '')
                    return image_path
            
            # If exact match fails, find nearest emotion
            available_emotions = list(self.emotions_db.keys())
            nearest_emotion = self.find_emotion_similarity(detected_emotion, available_emotions)
            
            if nearest_emotion and nearest_emotion != detected_emotion:
                emotion_id = self.emotions_db[nearest_emotion]['emotion_id']
                
                response = self.supabase.schema('dc').table('memes_dc').select('*').eq('emotion_id', emotion_id).execute()
                
                if response.data:
                    selected_template = random.choice(response.data)
                    image_path = selected_template.get('image_path', '')
                    return image_path
            
            # If still no match, get any available template
            response = self.supabase.schema('dc').table('memes_dc').select('*').limit(10).execute()
            
            if response.data:
                selected_template = random.choice(response.data)
                image_path = selected_template.get('image_path', '')
                return image_path
            else:
                return ""
                
        except Exception as e:
            print(f"Error in template search: {e}")
            return ""

    def process_single_news_sarcastic(self, news_content: str, news_url: str) -> Dict:
        """Process single news article with ONE comprehensive Gemini API call"""
        
        # Create emotion options list for the prompt
        emotion_options = []
        for label, data in self.emotions_db.items():
            emotion_options.append(f"- {label}: {data['description']}")
        emotion_list_str = '\n'.join(emotion_options)
        
        # COMPREHENSIVE SARCASTIC PROMPT - ALL OPERATIONS IN ONE CALL
        comprehensive_prompt = f"""
        You are a sarcastic, witty social media content creator and news analyst. Process this news article and provide ALL the following information in a single response:

        NEWS CONTENT: "{news_content}"

        Provide ALL the following in JSON format:

        1. DESCRIPTION: Create a SARCASTIC, BUZZY 2-3 line description
           - Make it viral-worthy and engaging
           - Use sarcastic tone and witty commentary
           - No emojis, just pure sarcastic wit
           - Maximum 3 lines that people would want to share
           - Think like a roast comedian analyzing news

        2. EMOTION: After reading your sarcastic description, identify the dominant emotion from these options:
        {emotion_list_str}
           Return ONLY the emotion label in lowercase.

        3. CATEGORY: Based on your description, categorize into ONE from: politics, entertainment, movies, sports, business, technology, crime
           - Read your own description first, then categorize
           - If about films/cinema/actors/bollywood → "movies"
           - If about TV/music/celebrities/awards → "entertainment"
           - If about police/arrest/murder/fraud/court → "crime"
           - If about government/elections/politicians → "politics"

        4. DIALOGUES: Create 2 SARCASTIC meme dialogues (max 8 words each)
           - Use formats: "When...", "Me:", "POV:", "Everyone:", "Meanwhile:"
           - Make them hilariously sarcastic and relatable
           - Each dialogue MUST be maximum 8 words
           - Think like a meme creator roasting the situation

        5. HASHTAGS: Generate 6-8 sarcastic/buzzy hashtags
           - Mix trending tags with sarcastic ones
           - Include category-specific tags
           - Make them shareable and viral-worthy

        RETURN EVERYTHING in this EXACT JSON structure:
        {{
            "description": "Sarcastic line 1\\nSarcastic line 2\\nSarcastic line 3 (if needed)",
            "emotion": "emotion_label",
            "category": "category_name", 
            "dialogues": ["sarcastic dialogue 1 (max 8 words)", "sarcastic dialogue 2 (max 8 words)"],
            "hashtags": ["#SarcasticTag1", "#BuzzyTag2", "#CategoryTag", "#Trending", "#ViralTag", "#SarcasmLevel100"]
        }}

        Analyze and create sarcastic content for this news:
        """
        
        try:
            # SINGLE COMPREHENSIVE API CALL
            response = self.safe_gemini_call(comprehensive_prompt)
            parsed_data = self.parse_sarcastic_response(response)
            
            if parsed_data:
                # Get template using smart emotion matching
                detected_emotion = parsed_data.get('emotion', '').lower()
                template_path = self.get_template_from_supabase_smart(detected_emotion)
                
                # Create final result with ALL requested fields
                final_result = {
                    "description": parsed_data.get('description', ''),
                    "category": parsed_data.get('category', 'entertainment'),
                    "hashtags": parsed_data.get('hashtags', []),
                    "dialogues": parsed_data.get('dialogues', []),
                    "url": news_url,
                    "template_image_path": template_path
                }
                
                return final_result
            else:
                raise Exception("Failed to parse Gemini response")
                
        except Exception as e:
            clean_error = str(e).replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
            print(f"Error in processing: {clean_error}")
            return None

    def parse_sarcastic_response(self, response: str) -> Dict:
        """Parse the JSON response from Gemini"""
        try:
            # Try to extract JSON from response
            json_pattern = r'\{.*?\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(0)
                parsed = json.loads(json_text)
                
                required_fields = ['description', 'emotion', 'category', 'dialogues', 'hashtags']
                if all(key in parsed for key in required_fields):
                    # Ensure dialogues are max 8 words each
                    if 'dialogues' in parsed and isinstance(parsed['dialogues'], list):
                        cleaned_dialogues = []
                        for dialogue in parsed['dialogues'][:2]:
                            words = str(dialogue).split()
                            if len(words) <= 8:
                                cleaned_dialogues.append(' '.join(words))
                            else:
                                cleaned_dialogues.append(' '.join(words[:8]))
                        parsed['dialogues'] = cleaned_dialogues
                    
                    print("Successfully parsed response")
                    return parsed
                    
            return self.manual_parse_sarcastic_response(response)
            
        except json.JSONDecodeError as e:
            return self.manual_parse_sarcastic_response(response)
        except Exception as e:
            print(f"Error parsing response: {e}")
            return None

    def manual_parse_sarcastic_response(self, response: str) -> Dict:
        """Manually parse response if JSON parsing fails"""
        try:
            result = {}
            
            # Extract description
            desc_patterns = [
                r'"?description"?\s*:\s*"([^"]+)"',
                r'description[:\s]+(.+?)(?=emotion|category|\n\n)',
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    result['description'] = desc_match.group(1).strip()
                    break
            
            if 'description' not in result:
                result['description'] = "Another predictable news story that surprises absolutely no one\nBecause apparently this passes for journalism these days\nStay tuned for more earth-shattering updates"
            
            # Extract emotion
            emotion_match = re.search(r'"?emotion"?\s*:\s*"?(\w+)"?', response, re.IGNORECASE)
            result['emotion'] = emotion_match.group(1).lower() if emotion_match else 'sarcasm'
            
            # Extract category
            category_match = re.search(r'"?category"?\s*:\s*"?(\w+)"?', response, re.IGNORECASE)
            result['category'] = category_match.group(1) if category_match else 'entertainment'
            
            # Extract dialogues
            dialogues = re.findall(r'"([^"]+)"', response)
            sarcastic_candidates = [d for d in dialogues if 2 <= len(d.split()) <= 10]
            result['dialogues'] = sarcastic_candidates[:2] if len(sarcastic_candidates) >= 2 else ["When news tries to surprise us", "Everyone: Been there done that"]
            
            # Extract hashtags
            hashtags = re.findall(r'#\w+', response)
            result['hashtags'] = hashtags[:6] if hashtags else ["#Sarcasm", "#News", "#Reality", "#NoSurprise", "#Trending", "#Buzzy"]
            
            return result
            
        except Exception as e:
            print(f"Manual parsing failed: {e}")
            return None

    def load_news_from_json(self, json_file_path: str) -> List[Dict]:
        """Load ALL news articles from BOTH old and new JSON structures"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = []
            
            # Check if it's the new categorized structure
            if 'categorized_news' in data:
                print("Detected categorized news structure")
                categorized_news = data['categorized_news']
                
                for category, category_articles in categorized_news.items():
                    print(f"Loading {len(category_articles)} articles from {category} category")
                    articles.extend(category_articles)
                    
            # Check if it's the old flat structure
            elif 'articles' in data:
                print("Detected flat articles structure")
                articles = data.get('articles', [])
                
            else:
                print("Unknown JSON structure")
                return []
            
            print(f"Total loaded: {len(articles)} articles from {os.path.basename(json_file_path)}")
            return articles
            
        except Exception as e:
            print(f"Error loading news from JSON: {e}")
            return []

    def process_all_news_articles(self) -> List[Dict]:
        """Process ALL articles from the latest JSON file"""
        
        json_file_path = self.find_latest_news_json()
        
        if not json_file_path:
            print("No JSON file found to process")
            return []
        
        # Load ALL articles from JSON file (supports both old and new structures)
        articles = self.load_news_from_json(json_file_path)
        
        if not articles:
            print("No articles found in JSON file")
            return []
        
        processed_news = []
        total_articles = len(articles)
        
        print(f"\nSARCASTIC NEWS PROCESSING STARTED")
        print(f"Processing ALL {total_articles} articles")
        print(f"Using {len(self.api_keys)} API keys with rotation")
        print(f"ONE Gemini call per article")
        
        for i, article in enumerate(articles, 1):
            print(f"\n" + "="*60)
            print(f"Processing article {i}/{total_articles}")
            print(f"Content: {article['content'][:80]}...")
            
            try:
                # SINGLE COMPREHENSIVE API CALL per article
                result = self.process_single_news_sarcastic(
                    article['content'], 
                    article.get('url', '')
                )
                
                if result:
                    processed_news.append(result)
                    print(f"SUCCESS! Article {i} processed")
                    print(f"   Category: {result['category']}")
                    print(f"   Template: {'Yes' if result['template_image_path'] else 'No'}")
                else:
                    print(f"FAILED to process article {i}")
                
            except Exception as e:
                clean_error = str(e).replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
                print(f"Error processing article {i}: {clean_error}")
                continue
            
            # Show progress
            success_rate = (len(processed_news) / i) * 100
            print(f"Progress: {i}/{total_articles} | Success: {len(processed_news)} ({success_rate:.1f}%)")
        
        return processed_news

    def save_processed_news(self, processed_news: List[Dict], output_path: str = None) -> str:
        """Save processed news to JSON file"""
        if not output_path:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
            output_path = f'./output/sarcastic_news_memes_{timestamp}.json'
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'total_processed': len(processed_news),
            'total_api_calls': len(processed_news),
            'processing_type': 'comprehensive_sarcastic_content',
            'fields_generated': ['description', 'category', 'emotion', 'dialogues', 'hashtags', 'template_path'],
            'processed_news': processed_news
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n" + "="*60)
        print(f"PROCESSING COMPLETE!")
        print(f"Processed {len(processed_news)} articles")
        print(f"Made {len(processed_news)} total API calls")
        print(f"Saved to: {output_path}")
        
        return output_path

# Example usage
if __name__ == "__main__":
    processor = NewsToMemeProcessor()
    
    print("COMPREHENSIVE NEWS MEME PROCESSOR")
    print("Processing ALL articles with single API call per article")
    print("Generates: description, category, emotion, dialogues, hashtags, template")
    
    processed_news = processor.process_all_news_articles()
    
    if processed_news:
        output_file = processor.save_processed_news(processed_news)
        
        print(f"\nSuccessfully created comprehensive meme data!")
        print(f"Output file: {output_file}")
        
        if processed_news:
            print(f"\nSample processed article:")
            sample = processed_news[0]
            print(f"Description: {sample['description']}")
            print(f"Category: {sample['category']}")
            print(f"Dialogues: {sample['dialogues']}")
            print(f"Hashtags: {sample['hashtags'][:3]}...")
            print(f"URL: {sample['url']}")
            print(f"Template: {sample['template_image_path']}")
            
        templates_found = len([p for p in processed_news if p['template_image_path']])
        print(f"\nSTATS:")
        print(f"   Articles processed: {len(processed_news)}")
        print(f"   Templates found: {templates_found}")
        print(f"   Success rate: {(templates_found/len(processed_news)*100):.1f}%")
    else:
        print("No articles were successfully processed")
