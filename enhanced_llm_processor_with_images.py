import requests
import json
from typing import List, Dict
import random


class EnhancedNewsProcessorWithImages:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2:latest"
        
        # Focus on major categories only 
        self.major_categories = ['politics', 'entertainment', 'movies', 'sports', 'business', 'technology', 'crime']
        
    def call_ollama_for_emoji(self, title: str, category: str) -> str:
        """Generate EXACTLY 2 emojis maximum"""
        try:
            prompt = f"""
            Generate EXACTLY 2 relevant emojis for this {category} news headline:
            "{title}"
            
            Requirements:
            - Return ONLY 2 emojis, no text, no spaces
            - Make emojis relevant to content and emotion
            - MAXIMUM 2 emojis total
            - No explanations, no extra text
            
            Emojis:
            """
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(self.ollama_url, json=payload, timeout=10)
            if response.status_code == 200:
                emojis = response.json()['response'].strip()
                emoji_chars = ''.join(char for char in emojis if ord(char) > 127)
                if len(emoji_chars) >= 2:
                    return emoji_chars[:2]
                elif len(emoji_chars) == 1:
                    return emoji_chars + self.get_single_fallback_emoji(category)
                else:
                    return self.fallback_emoji(category)
            else:
                return self.fallback_emoji(category)
                
        except Exception as e:
            print(f"Error calling Ollama for emojis: {e}")
            return self.fallback_emoji(category)
    
    def get_single_fallback_emoji(self, category: str) -> str:
        """Get single emoji for combination"""
        single_emojis = {
            'movies': '🎬', 'sports': '⚡', 'politics': '🔥', 'business': '💰',
            'technology': '🤖', 'entertainment': '🎭', 'crime': '🚨', 'general': '📰'
        }
        return single_emojis.get(category)
    
    def fallback_emoji(self, category: str) -> str:
        """Fallback emojis - EXACTLY 2"""
        category_emojis = {
            'movies': '🎬🎭', 'sports': '⚡🏆', 'politics': '🔥🏛', 'business': '💰📈',
            'technology': '🤖💻', 'entertainment': '🎭🎪', 'crime': '🚨⚖️', 'general': '📰⭐'
        }
        return category_emojis.get(category, '📰🔥')

    def call_ollama_for_category(self, title: str, content: str, fallback_category: str) -> str:
        """Categorize news into major categories only"""
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
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(self.ollama_url, json=payload, timeout=10)
            if response.status_code == 200:
                category = response.json()['response'].strip().lower()
                if category in self.major_categories:
                    return category
                if category in ['health', 'international', 'general']:
                    return 'entertainment'  # Default mapping
            return fallback_category if fallback_category in self.major_categories else 'entertainment'
        except Exception as e:
            print(f"Error classifying category: {e}")
            return fallback_category if fallback_category in self.major_categories else 'entertainment'
    
    def call_ollama_for_buzzy_summary(self, title: str, content: str, category: str) -> str:
        """LLM elaborates content and creates buzzy 2-line summary"""
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
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(self.ollama_url, json=payload, timeout=20)
            if response.status_code == 200:
                summary = response.json()['response'].strip()
                lines = [l.strip() for l in summary.split('\n') if l.strip()]
                return '\n'.join(lines[:2]) if len(lines) > 1 else (lines[0] if lines else title)
            else:
                return title  # Simple fallback
                
        except Exception as e:
            print(f"Error calling Ollama for summary: {e}")
            return title  # Simple fallback
    
    def call_ollama_for_buzzy_captions(self, summary: str, category: str, title: str, content: str) -> List[str]:
        """ PURE LLM: Generate captions based on news content - NO FALLBACKS"""
        
        prompt = f"""
        You are a viral meme caption writer. Read this {category} news carefully and create 2-3 sarcastic, witty captions based on the specific story details.

        Title: {title}
        Summary: {summary}
        Full Content: {content[:800]}
        Category: {category}

        Instructions:
        - READ and UNDERSTAND the specific news story
        - Create 2-3 sarcastic meme captions that reference THIS exact story
        - Each caption should be 6-12 words
        - Make them witty, relatable, and specific to this news
        - Reference actual people, events, or situations from the story
        - Be sarcastic but not offensive or inappropriate
        - No emojis, no hashtags
        - Return ONLY a JSON array of strings like: ["caption 1", "caption 2", "caption 3"]

        Think about what's ironic, funny, or surprising about THIS specific news story.

        Generate captions:
        """
        
        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False}
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                raw_response = response.json().get("response", "").strip()
                print(f"✓ LLM Caption Response: {raw_response[:100]}...")
                
                # Try to parse LLM response
                captions = self.parse_llm_captions(raw_response)
                
                if len(captions) >= 2:
                    print(f"✓ Successfully generated {len(captions)} LLM captions")
                    return captions
                else:
                    print(f" LLM generated only {len(captions)} valid captions - SKIPPING NEWS ITEM")
                    return []  # Return empty to signal failure
            
            print(" LLM request failed - SKIPPING NEWS ITEM")
            return []  # Return empty to signal failure
            
        except Exception as e:
            print(f" Error generating captions: {e} - SKIPPING NEWS ITEM")
            return []  # Return empty to signal failure

    def parse_llm_captions(self, raw_response: str) -> List[str]:
        """Parse LLM response into valid captions"""
        captions = []
        
        # Method 1: Try JSON parsing
        try:
            # Clean up common LLM formatting issues
            cleaned_response = raw_response.strip()
            
            # Remove common prefixes/suffixes
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            # Try to find JSON array in the response
            start_bracket = cleaned_response.find('[')
            end_bracket = cleaned_response.rfind(']')
            
            if start_bracket != -1 and end_bracket != -1:
                json_str = cleaned_response[start_bracket:end_bracket+1]
                captions_array = json.loads(json_str)
                
                if isinstance(captions_array, list):
                    for caption in captions_array[:3]:
                        caption_text = str(caption).strip().strip('"').strip("'")
                        word_count = len(caption_text.split())
                        # Validate caption quality
                        if (6 <= word_count <= 12 and 
                            all(ord(char) < 128 for char in caption_text) and
                            len(caption_text) > 10):  # Minimum length check
                            captions.append(caption_text)
                    
                    return captions[:3]
        except json.JSONDecodeError:
            pass
        
        # Method 2: Extract from text format if JSON fails
        lines = [line.strip().strip('"').strip("'") for line in raw_response.split('\n') if line.strip()]
        
        for line in lines:
            # Remove common prefixes
            for prefix in ['1.', '2.', '3.', '-', '*', '•', 'Caption:', 'caption:']:
                if line.lower().startswith(prefix.lower()):
                    line = line[len(prefix):].strip()
            
            # Validate and add caption
            word_count = len(line.split())
            if (6 <= word_count <= 12 and 
                all(ord(char) < 128 for char in line) and
                len(line) > 10):
                captions.append(line)
        
        return captions[:3]

    def create_buzzy_summary_with_captions(self, title: str, content: str, category: str, has_image: bool) -> Dict[str, str | List[str]] | None:
        """Create buzzy summary and PURE LLM captions - returns None if LLM fails"""
        
        # Step 1: Generate buzzy summary
        llm_summary = self.call_ollama_for_buzzy_summary(title, content, category)
        
        # Step 2: Generate PURE LLM captions - NO FALLBACKS
        captions = self.call_ollama_for_buzzy_captions(llm_summary, category, title, content)
        
        #  If LLM fails to generate valid captions, return None to skip this news item
        if not captions or len(captions) < 2:
            print(f" Skipping news item - LLM failed to generate sufficient captions")
            return None
        
        # Step 3: Add emojis to summary
        contextual_emojis = self.call_ollama_for_emoji(title, category)
        if has_image:
            final_summary = f"{contextual_emojis} {llm_summary} Perfect visual content ready!"
        else:
            final_summary = f"{contextual_emojis} {llm_summary} Trending story alert!"
        
        return {"summary": final_summary, "captions": captions}

    def process_news_with_images(self, news_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Process news with PURE LLM caption generation - skip items where LLM fails"""
        all_news = []
        for category_list in news_data.values():
            all_news.extend(category_list)
        
        processed_categories = {}
        
        print(f"Processing {len(all_news)} news items with PURE LLM caption generation (no fallbacks)...")
        
        successful_items = 0
        skipped_items = 0
        
        for i, news_item in enumerate(all_news, 1):
            print(f"Processing item {i}/{len(all_news)}: {news_item['title'][:50]}...")
            
            try:
                category = self.call_ollama_for_category(news_item['title'], news_item['content'], news_item.get('category', 'entertainment'))
                
                # Only process major categories
                if category not in self.major_categories:
                    skipped_items += 1
                    continue
                    
                #  PURE LLM GENERATION - No fallbacks
                buzzy = self.create_buzzy_summary_with_captions(
                    news_item['title'],
                    news_item['content'],
                    category,
                    news_item.get('has_image', False)
                )
                
                #  Skip if LLM failed to generate captions
                if buzzy is None:
                    print(f" SKIPPED item {i} - LLM caption generation failed")
                    skipped_items += 1
                    continue
                
                #  Only include items with successful LLM caption generation
                processed_item = {
                    'category': category,
                    'news_summary': buzzy['summary'],
                    'captions': buzzy['captions'],  # 100% LLM generated
                    'image_path': news_item.get('local_image_path'),
                    'url': news_item.get('url')
                }
                
                if category not in processed_categories:
                    processed_categories[category] = []
                processed_categories[category].append(processed_item)
                successful_items += 1
                
            except Exception as e:
                print(f" Error processing item {i}: {e} - SKIPPED")
                skipped_items += 1
                continue
        
        # Limit to 5-10 news per major category
        for category in processed_categories:
            processed_categories[category].sort(key=lambda x: len(x.get('news_summary', '')), reverse=True)
            category_count = len(processed_categories[category])
            if category_count > 10:
                processed_categories[category] = processed_categories[category][:10]
        
        # Keep categories with 3+ items 
        filtered_categories = {k: v for k, v in processed_categories.items() if len(v) >= 3}
        
        print(f" PURE LLM PROCESSING COMPLETE:")
        print(f"   - Successful items: {successful_items}")
        print(f"   - Skipped items: {skipped_items}")
        print(f"   - Final items: {sum(len(v) for v in filtered_categories.values())} across {len(filtered_categories)} categories")
        
        return filtered_categories
