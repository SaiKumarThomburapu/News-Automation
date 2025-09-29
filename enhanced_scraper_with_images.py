#enhanced_scraper_with_images.py

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin
import time
from pathlib import Path
import json
import hashlib
from datetime import datetime
import os
import random

class EnhancedNewsExtractorWithImages:
    def __init__(self):
        self.headers = {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # TARGET CATEGORIES - Only these 6 categories
        self.target_categories = ['politics', 'movies', 'entertainment', 'sports', 'business', 'technology']
        
        # OPTIMIZED: More sources per category to ensure we get enough articles
        self.news_sources = {
    # POLITICS SOURCES - Top 3
    'ie_politics': {'url': 'https://indianexpress.com/section/political-pulse/', 'selectors': ['h3 a', 'h2 a'], 'category': 'politics'},
    'toi_politics': {'url': 'https://timesofindia.indiatimes.com/india', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'politics'},
    'ht_politics': {'url': 'https://www.hindustantimes.com/india-news', 'selectors': ['h3 a', 'h2 a'], 'category': 'politics'},

    # ENTERTAINMENT & MOVIES SOURCES - Top 3
    'toi_movies': {'url': 'https://timesofindia.indiatimes.com/entertainment/hindi/bollywood/news', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'movies'},
    'news18_entertainment': {'url': 'https://www.news18.com/entertainment/', 'selectors': ['h3 a', 'h2 a'], 'category': 'entertainment'},
    'indiatoday_entertainment': {'url': 'https://www.indiatoday.in/movies', 'selectors': ['h2 a', 'h3 a'], 'category': 'entertainment'},

    # SPORTS SOURCES - Top 3
    'toi_sports': {'url': 'https://timesofindia.indiatimes.com/sports', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'sports'},
    'ht_sports': {'url': 'https://www.hindustantimes.com/sports', 'selectors': ['h3 a', 'h2 a'], 'category': 'sports'},
    'indiatoday_sports': {'url': 'https://www.indiatoday.in/sports', 'selectors': ['h2 a', 'h3 a'], 'category': 'sports'},

    # BUSINESS SOURCES - Top 3
    'economic_times': {'url': 'https://economictimes.indiatimes.com/', 'selectors': ['h3 a', 'h2 a'], 'category': 'business'},
    'livemint': {'url': 'https://www.livemint.com/', 'selectors': ['h3 a', 'h2 a'], 'category': 'business'},
    'moneycontrol': {'url': 'https://www.moneycontrol.com/news/', 'selectors': ['h3 a', 'h2 a'], 'category': 'business'},

    # TECHNOLOGY SOURCES - Top 3
    'toi_technology': {'url': 'https://timesofindia.indiatimes.com/gadgets-news', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'technology'},
    'et_tech': {'url': 'https://economictimes.indiatimes.com/tech', 'selectors': ['h3 a', 'h2 a'], 'category': 'technology'},
    'indiatoday_tech': {'url': 'https://www.indiatoday.in/technology/news', 'selectors': ['h2 a', 'h3 a'], 'category': 'technology'},

    # TRENDING / VIRAL SOURCES - Top 3
    'ht_trending': {'url': 'https://www.hindustantimes.com/trending', 'selectors': ['h3 a', 'h2 a'], 'category': 'trending'},
    'indianexpress_trending': {'url': 'https://indianexpress.com/section/trending/', 'selectors': ['h3 a', 'h2 a'], 'category': 'trending'},
    'indiatoday_trending': {'url': 'https://www.indiatoday.in/trending-news', 'selectors': ['h2 a', 'h3 a'], 'category': 'trending'},
}
         
        self.downloaded_image_hashes = set()
        self.setup_output_directory()

    def setup_output_directory(self):
        """Setup simplified output directory structure"""
        self.output_dir = Path('./output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'images').mkdir(exist_ok=True)
        
        print("Output structure created:")
        print("  - ./output/images/ (for scraped images)")
        print("  - ./output/news_data_[timestamp].json (guaranteed 10 per category)")

    def calculate_buzz_score(self, title: str, content: str) -> int:
        """Calculate buzz score - More lenient scoring to ensure we get articles"""
        text = (title + ' ' + content).lower()
        
        # High buzz keywords - Reduced points for more inclusivity
        high_buzz_words = {
            'breaking': 4, 'exclusive': 3, 'shocking': 3, 'controversy': 3,
            'scandal': 3, 'arrest': 2, 'murder': 3, 'viral': 3,
            'trending': 2, 'major': 2, 'important': 2, 'crisis': 2,
            'emergency': 2, 'urgent': 2, 'alert': 2, 'warning': 1,
            'wins': 2, 'loses': 1, 'victory': 2, 'defeat': 1, 'new': 1
        }
        
        # Category specific buzz words - More inclusive
        category_buzz = {
            'bollywood': 2, 'cricket': 2, 'election': 2, 'politics': 1,
            'technology': 1, 'business': 1, 'sports': 1, 'movie': 1,
            'celebrity': 1, 'actor': 1, 'match': 1, 'win': 1, 'lose': 1,
            'ipl': 2, 'box office': 2, 'release': 1, 'hit': 1, 'flop': 1,
            'update': 1, 'news': 1, 'latest': 1, 'today': 1
        }
        
        buzz_score = 1  # Base score of 1 for every article
        
        # Add points for high buzz keywords
        for keyword, points in high_buzz_words.items():
            if keyword in text:
                buzz_score += points
        
        # Add points for category keywords
        for keyword, points in category_buzz.items():
            if keyword in text:
                buzz_score += points
        
        # Content quality bonus - More lenient
        if len(content) > 50:
            buzz_score += 1
        if len(content) > 150:
            buzz_score += 1
        
        # Title engagement bonus
        if any(word in title.lower() for word in ['how', 'why', 'what', 'when', 'where']):
            buzz_score += 1
        
        # Length bonus for substantial content
        if len(title) > 30:
            buzz_score += 1
        
        return min(buzz_score, 15)  # Cap at 15

    def categorize_news_content(self, title: str, content: str, source_category: str = None) -> str:
        """Categorize news content - More flexible categorization"""
        text = (title + ' ' + content).lower()
        
        # If source has predefined category, use it first (higher priority)
        if source_category and source_category in self.target_categories:
            return source_category
        
        # Enhanced category keywords mapping
        category_keywords = {
            'politics': ['election', 'parliament', 'minister', 'government', 'political', 'bjp', 'congress', 'modi', 'politics', 'vote', 'party', 'constituency', 'leader', 'pm', 'chief minister'],
            'movies': ['movie', 'film', 'actor', 'actress', 'bollywood', 'cinema', 'box office', 'trailer', 'director', 'producer', 'release', 'star', 'role', 'shoot', 'debut'],
            'entertainment': ['entertainment', 'celebrity', 'music', 'tv show', 'award', 'concert', 'performance', 'artist', 'singer', 'album', 'show', 'reality', 'dance', 'talent'],
            'sports': ['cricket', 'football', 'sports', 'match', 'player', 'ipl', 'olympics', 'tournament', 'team', 'game', 'score', 'win', 'lose', 'champion', 'league'],
            'business': ['business', 'market', 'stock', 'economy', 'startup', 'investment', 'ipo', 'company', 'profit', 'revenue', 'financial', 'bank', 'money', 'price', 'growth'],
            'technology': ['technology', 'tech', 'ai', 'software', 'app', 'smartphone', 'digital', 'internet', 'gadget', 'innovation', 'cyber', 'data', 'android', 'apple', 'google']
        }
        
        # Score each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 if keyword in text else 0 for keyword in keywords)
            category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            if category_scores[best_category] > 0:
                return best_category
        
        # Default fallback based on source or entertainment
        return source_category if source_category in self.target_categories else 'entertainment'

    def clean_and_decide_content(self, title: str, extracted_content: str) -> str:
        """Clean content and decide between title/content to avoid duplicates"""
        clean_title = title.strip()
        clean_content = extracted_content.strip() if extracted_content else ""
        
        if not clean_content or len(clean_content) < 20:  # Reduced threshold
            return clean_title
        
        title_normalized = ''.join(char.lower() for char in clean_title if char.isalnum() or char.isspace()).strip()
        content_normalized = ''.join(char.lower() for char in clean_content if char.isalnum() or char.isspace()).strip()
        
        if (content_normalized.startswith(title_normalized) or 
            title_normalized in content_normalized[:len(title_normalized) + 50]):
            return clean_content
        
        if len(clean_title) > len(clean_content):
            return clean_title
            
        return clean_content if len(clean_content) > len(clean_title) else clean_title

    def scrape_single_source_with_images(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Scrape source with more lenient filtering"""
        news_list = []
        try:
            print(f"Scraping {source_name} for {source_config.get('category', 'general')} news...")
            response = requests.get(source_config['url'], headers=self.headers, timeout=15)
            if response.status_code != 200:
                print(f"{source_name}: Status {response.status_code} - Skipping")
                return news_list
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for selector in source_config['selectors']:
                links = soup.select(selector)
                
                for i, link in enumerate(links[:30]):  # Increased to get more articles
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not title or len(title) < 10:  # Reduced minimum length
                        continue
                    
                    # URL construction
                    if href.startswith('/'):
                        base_domain = source_config['url'].split('/')[2]
                        if 'timesofindia' in base_domain:
                            href = 'https://timesofindia.indiatimes.com' + href
                        elif 'indianexpress' in base_domain:
                            href = 'https://indianexpress.com' + href
                        elif 'hindustantimes' in base_domain:
                            href = 'https://www.hindustantimes.com' + href
                        elif 'news18' in base_domain:
                            href = 'https://www.news18.com' + href
                        elif 'economictimes' in base_domain:
                            href = 'https://economictimes.indiatimes.com' + href
                        elif 'livemint' in base_domain:
                            href = 'https://www.livemint.com' + href
                        elif 'moneycontrol' in base_domain:
                            href = 'https://www.moneycontrol.com' + href
                        else:
                            href = source_config['url'].split('/')[0] + '//' + base_domain + href
                    elif not href.startswith('http'):
                        continue
                    
                    # Extract content
                    listing_content = self.extract_content_from_listing(link)
                    final_content = self.clean_and_decide_content(title, listing_content)
                    
                    if len(final_content) < 15:  # Reduced minimum length
                        continue
                    
                    # Categorize the news
                    category = self.categorize_news_content(title, final_content, source_config.get('category'))
                    
                    # Only keep news from target categories
                    if category not in self.target_categories:
                        continue
                    
                    # Calculate buzz score - No minimum threshold here
                    buzz_score = self.calculate_buzz_score(title, final_content)
                    
                    # Try to find image
                    image_url = self.extract_simple_headline_image(link, source_config['url'])
                    local_image_path = None
                    
                    if image_url:
                        image_filename = f"{category}_{source_name}_{i}"
                        local_image_path = self.download_image_unique(image_url, image_filename)
                    
                    # Add to news list with metadata
                    news_list.append({
                        'content': final_content,
                        'url': href,
                        'image_path': local_image_path,
                        'category': category,
                        'buzz_score': buzz_score,
                        'source': source_name
                    })
            
            print(f"{source_name}: {len(news_list)} articles scraped")
            
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            
        return news_list

    def extract_content_from_listing(self, link_element) -> str:
        """Simple content extraction"""
        try:
            container = link_element.parent
            content_parts = []
            
            if container:
                content_elements = container.select('.summary, .snippet, p, .description')[:5]  # Increased elements
                for elem in content_elements:
                    text = elem.get_text(strip=True)
                    if len(text) > 10 and text != link_element.get_text(strip=True):  # Reduced minimum
                        content_parts.append(text)
            
            full_content = ' '.join(content_parts[:3])  # Increased parts
            return full_content[:800] if full_content else ""  # Increased length
        except Exception:
            return ""

    def extract_simple_headline_image(self, link_element, base_url: str) -> str:
        """Simple image extraction for headlines"""
        try:
            headline_container = link_element.parent
            if headline_container:
                container_images = headline_container.select('img')
                for img in container_images:
                    img_url = self.get_simple_image_url(img)
                    if img_url and self.is_valid_headline_image(img_url):
                        normalized_url = self.normalize_image_url(img_url, base_url)
                        if normalized_url:
                            return normalized_url
            
            if headline_container and headline_container.parent:
                parent_images = headline_container.parent.select('img')
                for img in parent_images:
                    img_url = self.get_simple_image_url(img)
                    if img_url and self.is_valid_headline_image(img_url):
                        normalized_url = self.normalize_image_url(img_url, base_url)
                        if normalized_url:
                            return normalized_url
            
            return None
            
        except Exception:
            return None

    def get_simple_image_url(self, img_element) -> str:
        return (img_element.get('src') or 
                img_element.get('data-src') or 
                img_element.get('data-lazy-src'))

    def is_valid_headline_image(self, img_url: str) -> bool:
        if not img_url or len(img_url) < 10:
            return False
            
        img_lower = img_url.lower()
        skip_patterns = ['logo', 'icon', 'avatar', 'placeholder', '1x1', 'pixel', 'spacer']
        
        if any(pattern in img_lower for pattern in skip_patterns):
            return False
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        return any(ext in img_url.lower() for ext in valid_extensions)

    def normalize_image_url(self, img_url: str, base_url: str) -> str:
        if not img_url or img_url.startswith('data:'):
            return None
        if img_url.startswith('//'):
            return 'https:' + img_url
        elif img_url.startswith('/'):
            return urljoin(base_url, img_url)
        elif img_url.startswith('http'):
            return img_url
        return urljoin(base_url + '/', img_url)

    def download_image_unique(self, image_url: str, filename: str) -> str:
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                image_content = response.content
                if len(image_content) < 1000:
                    return None
                
                image_hash = hashlib.sha256(image_content).hexdigest()
                if image_hash in self.downloaded_image_hashes:
                    return None
                
                self.downloaded_image_hashes.add(image_hash)
                ext = image_url.lower().split('.')[-1].split('?')[0]
                if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                    ext = 'jpg'
                
                filename_with_ext = f"{filename}.{ext}"
                image_path = self.output_dir / 'images' / filename_with_ext
                with open(image_path, 'wb') as f:
                    f.write(image_content)
                
                return str(image_path)
        except Exception:
            pass
        return None

    def get_all_news(self) -> Dict[str, List[Dict]]:
        """Get news organized by categories - GUARANTEED 10 per category"""
        print("Starting categorized news extraction (GUARANTEED 10 per category)...")
        all_news = []
        
        # Scrape from all sources
        for source_name, config in self.news_sources.items():
            news_data = self.scrape_single_source_with_images(source_name, config)
            all_news.extend(news_data)
            time.sleep(random.uniform(0.3, 0.8))  # Faster scraping
        
        # Remove duplicates
        unique_news = self.remove_duplicates(all_news)
        
        # Organize by categories
        categorized_news = {}
        for category in self.target_categories:
            categorized_news[category] = []
        
        # Group by category
        for news in unique_news:
            category = news.get('category', 'entertainment')
            if category in categorized_news:
                categorized_news[category].append(news)
        
        # Ensure each category has exactly 10 articles
        final_categorized_news = {}
        for category in self.target_categories:
            category_news = categorized_news[category]
            
            if len(category_news) >= 10:
                # Sort by buzz score and take top 10
                category_news.sort(key=lambda x: x.get('buzz_score', 0), reverse=True)
                selected_news = category_news[:10]
            else:
                # If less than 10, take all available
                print(f"WARNING: Only {len(category_news)} articles found for {category}")
                selected_news = category_news
                
                # Fill remaining slots from 'entertainment' if possible
                if category != 'entertainment' and len(selected_news) < 10:
                    entertainment_extras = [n for n in categorized_news.get('entertainment', []) 
                                          if n not in selected_news][:10-len(selected_news)]
                    selected_news.extend(entertainment_extras)
                    print(f"Added {len(entertainment_extras)} entertainment articles to fill {category}")
            
            # Clean the data
            clean_news = []
            for news in selected_news:
                clean_news.append({
                    'content': news['content'],
                    'url': news['url'],
                    'image_path': news['image_path']
                })
            
            final_categorized_news[category] = clean_news
            print(f"{category.upper()}: {len(clean_news)} articles selected")
        
        total_articles = sum(len(articles) for articles in final_categorized_news.values())
        print(f"Total articles selected: {total_articles}")
        
        return final_categorized_news

    def remove_duplicates(self, news_list: List[Dict]) -> List[Dict]:
        """Remove duplicate news items based on content"""
        unique_news = []
        seen_content = set()
        
        for news in news_list:
            content_hash = hashlib.md5(news['content'].encode()).hexdigest()
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_news.append(news)
        
        return unique_news

    def save_single_json_output(self, categorized_news: Dict[str, List[Dict]]) -> str:
        """Save categorized news data to JSON file"""
        today = datetime.now().strftime('%Y-%m-%d_%H-%M')
        
        total_articles = sum(len(articles) for articles in categorized_news.values())
        total_images = 0
        
        for articles in categorized_news.values():
            total_images += len([a for a in articles if a.get('image_path')])
        
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'total_articles': total_articles,
            'categories': list(self.target_categories),
            'target_per_category': 10,
            'selection_method': 'Top buzz score with guaranteed minimum',
            'total_images': total_images,
            'categorized_news': categorized_news
        }
        
        json_file = self.output_dir / f'news_data_{today}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nGUARANTEED CATEGORIZED OUTPUT")
        print(f"JSON file: {json_file}")
        print(f"Images folder: ./output/images/")
        print(f"Total articles: {total_articles}")
        print(f"Articles with images: {total_images}")
        
        print(f"\nFINAL CATEGORY BREAKDOWN:")
        for category, articles in categorized_news.items():
            images_count = len([a for a in articles if a.get('image_path')])
            print(f"  {category.upper()}: {len(articles)} articles, {images_count} with images")
        
        return str(json_file)

# Example usage
if __name__ == "__main__":
    extractor = EnhancedNewsExtractorWithImages()
    categorized_news = extractor.get_all_news()
    json_file = extractor.save_single_json_output(categorized_news)
    
    print("\nEXTRACTION COMPLETE")
    print("GUARANTEED: Minimum articles per category with intelligent fallback")









 
