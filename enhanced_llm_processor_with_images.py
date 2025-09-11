# enhanced_llm_processor_with_images.py
import requests
import json
from typing import List, Dict
import random

class EnhancedNewsProcessorWithImages:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2:latest"
        
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
                # Extract only emojis and LIMIT TO 2
                emoji_chars = ''.join(char for char in emojis if ord(char) > 127)
                # Ensure exactly 2 emojis
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
            'technology': '🤖', 'health': '🏥', 'crime': '🚨', 'international': '🌍', 'general': '📰'
        }
        return single_emojis.get(category, '🔥')
    
    def fallback_emoji(self, category: str) -> str:
        """Fallback emojis - EXACTLY 2"""
        category_emojis = {
            'movies': '🎬🎭', 'sports': '⚡🏆', 'politics': '🔥🏛', 'business': '💰📈',
            'technology': '🤖💻', 'health': '🏥💊', 'crime': '🚨⚖', 'international': '🌍🌎', 'general': '📰⭐'
        }
        return category_emojis.get(category, '📰🔥')
    
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
                # Ensure maximum 2 lines
                lines = summary.split('\n')
                return '\n'.join(lines[:2]) if len(lines) > 1 else summary
            else:
                return self.create_manual_summary(title, content, category)
                
        except Exception as e:
            print(f"Error calling Ollama for summary: {e}")
            return self.create_manual_summary(title, content, category)
    
    def create_manual_summary(self, title: str, content: str, category: str) -> str:
        """Manual buzzy summary as fallback"""
        if content and len(content) > 100:
            # Extract key points from content
            content_preview = content[:200] + "..."
            return f"This {category} story is creating massive buzz across social media!\n{content_preview}"
        else:
            category_phrases = {
                'movies': "Entertainment industry is buzzing about this major development!",
                'sports': "Sports fans are going absolutely crazy over this news!",
                'politics': "Political circles are in intense debate over this revelation!",
                'technology': "Tech community is excited about this groundbreaking innovation!",
                'business': "Market experts are closely analyzing this game-changing move!",
                'health': "Healthcare professionals are discussing the significant implications!",
                'crime': "This shocking case has captured everyone's attention nationwide!",
                'international': "Global observers are monitoring this developing situation!",
                'general': "Everyone's talking about this trending story that's going viral!"
            }
            return f"{title}\n{category_phrases.get(category, 'This story is trending everywhere and creating massive buzz!')}"
    
    def create_buzzy_summary(self, title: str, content: str, category: str, has_image: bool) -> str:
        """Create final buzzy summary with EXACTLY 2 emojis"""
        
        # Step 1: Get LLM to elaborate content and create buzzy summary
        llm_summary = self.call_ollama_for_buzzy_summary(title, content, category)
        
        # Step 2: Get exactly 2 contextual emojis
        contextual_emojis = self.call_ollama_for_emoji(title, category)
        
        # Step 3: Combine with image context
        if has_image:
            final_summary = f"{contextual_emojis} {llm_summary} Perfect visual content ready!"
        else:
            final_summary = f"{contextual_emojis} {llm_summary} Trending story alert!"
        
        return final_summary
    
    def process_news_with_images(self, news_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Process news with LLM content elaboration and exactly 2 emojis"""
        
        processed_categories = {}
        
        for category, news_list in news_data.items():
            processed_news = []
            
            print(f"Processing {category.upper()} news with LLM content elaboration...")
            
            for news_item in news_list:
                # LLM processes the scraped content and creates buzzy summary
                buzzy_summary = self.create_buzzy_summary(
                    news_item['title'],
                    news_item['content'],  # Full scraped content 
                    category,
                    news_item['has_image']
                )
                
                processed_item = {
                    'title': news_item['title'],
                    'buzzy_summary': buzzy_summary,  # LLM-elaborated with exactly 2 emojis
                    'local_image_path': news_item.get('local_image_path'),
                    'has_image': news_item.get('has_image', False),
                    'buzz_score': news_item.get('buzz_score', 5),
                    'source': news_item.get('source', ''),
                    'content': news_item.get('content', ''),
                    'url': news_item.get('url', '')
                }
                
                processed_news.append(processed_item)
            
            processed_categories[category] = processed_news
            
        return processed_categories








# # enhanced_llm_processor_with_images.py
# import requests
# import json
# from typing import List, Dict
# import random

# class EnhancedNewsProcessorWithImages:
#     def __init__(self):
#         self.ollama_url = "http://localhost:11434/api/generate"
#         self.model = "llama3.2:latest"
        
#     def create_buzzy_summary(self, title: str, content: str, category: str, has_image: bool) -> str:
#         """Create buzzworthy summaries, enhanced for items with images"""
        
#         # Enhanced prompts for items with images
#         if has_image:
#             image_boost = " This visual story is perfect for meme creation! 📸"
#         else:
#             image_boost = ""
        
#         category_templates = {
#             'movies': f"🎬 Bollywood/Hollywood alert! {title[:60]}... Social media is buzzing!{image_boost} 💥",
#             'sports': f"⚡ Sports sensation! {title[:60]}... Fans are going absolutely crazy!{image_boost} 🏆",
#             'politics': f"🔥 Political drama! {title[:60]}... Nation is talking about this!{image_boost} 🚨",
#             'business': f"💰 Market buzz! {title[:60]}... Everyone's discussing the impact!{image_boost} 📈",
#             'technology': f"🤖 Tech breakthrough! {title[:60]}... Future is happening now!{image_boost} ⚡",
#             'health': f"🏥 Health update! {title[:60]}... Important news everyone should know!{image_boost} 💊",
#             'crime': f"🚨 Breaking story! {title[:60]}... Details are shocking!{image_boost} ⚖️",
#             'international': f"🌍 Global news! {title[:60]}... World is watching!{image_boost} 🌎",
#             'general': f"📰 Trending now! {title[:60]}... Perfect meme material!{image_boost} 🔥"
#         }
        
#         return category_templates.get(category, f"🔥 Breaking! {title[:60]}... is trending everywhere!{image_boost} 🚨")
    
#     def assign_category_emoji(self, category: str) -> str:
#         """Assign emojis based on category"""
#         emoji_map = {
#             'movies': '🎬',
#             'sports': '⚡',
#             'politics': '🔥', 
#             'business': '💰',
#             'technology': '🤖',
#             'health': '🏥',
#             'crime': '🚨',
#             'international': '🌍',
#             'general': '📰'
#         }
#         return emoji_map.get(category, '📰')
    
#     def process_news_with_images(self, news_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
#         """Process all news including image information"""
        
#         processed_categories = {}
        
#         for category, news_list in news_data.items():
#             processed_news = []
#             category_emoji = self.assign_category_emoji(category)
            
#             print(f"🎯 Processing {category.upper()} news with images...")
            
#             for news_item in news_list:
#                 buzzy_summary = self.create_buzzy_summary(
#                     news_item['title'],
#                     news_item['content'], 
#                     category,
#                     news_item['has_image']
#                 )
                
#                 processed_item = {
#                     'original_title': news_item['title'],
#                     'buzzy_summary': buzzy_summary,
#                     'category_emoji': category_emoji,
#                     'source': news_item['source'],
#                     'url': news_item['url'],
#                     'image_url': news_item.get('image_url'),
#                     'has_image': news_item.get('has_image', False)
#                 }
                
#                 processed_news.append(processed_item)
            
#             processed_categories[category] = processed_news
            
#         return processed_categories
