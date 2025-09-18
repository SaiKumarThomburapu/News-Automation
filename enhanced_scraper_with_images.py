import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin
import time
import shutil
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
        
        #  OPTIMIZED: Top 3 per category + working social media
        self.news_sources = {
            #  POLITICS - Top 3 fastest & most reliable
            'ie_politics': {'url': 'https://indianexpress.com/section/political-pulse/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            'toi_politics': {'url': 'https://timesofindia.indiatimes.com/india', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'buzz_level': 'HIGH'},
            'ht_politics': {'url': 'https://www.hindustantimes.com/india-news', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            
            #  CRIME - Top 3 with best crime coverage
            'india_today_crime': {'url': 'https://www.indiatoday.in/crime', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            #'ndtv_crime': {'url': 'https://www.ndtv.com/india', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            'ie_cities': {'url': 'https://indianexpress.com/section/cities/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            
            #  ENTERTAINMENT & MOVIES - Top 3 fastest loading
            'toi_entertainment': {'url': 'https://timesofindia.indiatimes.com/entertainment', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'buzz_level': 'HIGH'},
            #'ndtv_entertainment': {'url': 'https://www.ndtv.com/entertainment', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            'news18_entertainment': {'url': 'https://www.news18.com/entertainment/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            
            # SPORTS - Top 3 with fastest updates
            'toi_sports': {'url': 'https://timesofindia.indiatimes.com/sports', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'buzz_level': 'HIGH'},
            #'ndtv_sports': {'url': 'https://sports.ndtv.com/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            'ht_sports': {'url': 'https://www.hindustantimes.com/sports', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH'},
            
            # BUSINESS - Top 3 financial sites
            'economic_times': {'url': 'https://economictimes.indiatimes.com/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'MEDIUM'},
            'livemint': {'url': 'https://www.livemint.com/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'MEDIUM'},
            'moneycontrol': {'url': 'https://www.moneycontrol.com/news/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'MEDIUM'},
            
            #  TECHNOLOGY - Top 3 tech sources
            'toi_technology': {'url': 'https://timesofindia.indiatimes.com/gadgets-news', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'buzz_level': 'MEDIUM'},
            #'ndtv_tech': {'url': 'https://gadgets.ndtv.com/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'MEDIUM'},
            'et_tech': {'url': 'https://economictimes.indiatimes.com/tech', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'MEDIUM'},
            
            #  WORKING SOCIAL MEDIA & TRENDING - Replaced non-working sources
            'yahoo_trending': {'url': 'https://in.news.yahoo.com/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH', 'is_social': True},
            'msn_trending': {'url': 'https://www.msn.com/en-in/news', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH', 'is_social': True},
            'outlook_trending': {'url': 'https://www.outlookindia.com/', 'selectors': ['h3 a', 'h2 a'], 'buzz_level': 'HIGH', 'is_social': True},
        }
         
        self.downloaded_image_hashes = set()
        self.setup_output_directory()

    def setup_output_directory(self):
        """Setup output directory with archiving"""
        self.output_dir = Path('./output')
        archive_dir = self.output_dir / 'archives' / datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        if self.output_dir.exists():
            try:
                archive_dir.mkdir(parents=True, exist_ok=True)
                for item in self.output_dir.iterdir():
                    if item.name != 'archives':
                        shutil.move(str(item), archive_dir)
                print("✓ Moved previous output to archive")
            except Exception as e:
                print(f"Error archiving: {e}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'images').mkdir(exist_ok=True)
        print("✓ Fresh output directory created")

    def scrape_social_source(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Handle social/trending sources (Yahoo, MSN, Outlook)"""
        news_list = []
        try:
            print(f"\nConnecting to trending source: {source_name}...")
            response = requests.get(source_config['url'], headers=self.headers, timeout=15)
            if response.status_code != 200:
                print(f"{source_name}: Status {response.status_code} - Skipping")
                return news_list
                
            soup = BeautifulSoup(response.content, 'html.parser')
            buzz_level = source_config.get('buzz_level', 'HIGH')
            print(f"{source_name}: Connected successfully (Buzz Level: {buzz_level})")
            
            # Get trending headlines
            links = []
            for selector in source_config['selectors']:
                links.extend(soup.select(selector)[:10])
            
            print(f"  Found {len(links)} trending links")
            
            for i, link in enumerate(links[:15]):
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                if not title or len(title) < 20:
                    continue
                
                # Handle URLs properly
                if href.startswith('/'):
                    if 'yahoo.com' in source_config['url']:
                        href = 'https://in.news.yahoo.com' + href
                    elif 'msn.com' in source_config['url']:
                        href = 'https://www.msn.com' + href
                    elif 'outlookindia.com' in source_config['url']:
                        href = 'https://www.outlookindia.com' + href
                elif not href.startswith('http'):
                    continue
                
                print(f"  Processing trending: {title[:50]}...")
                
                final_content = f"Trending story: {title}"
                buzz_score = min(10, 8 + random.randint(0, 2))
                category = self.advanced_categorization(title, final_content)
                
                # Try to find image for social sources too
                image_url = self.extract_simple_headline_image(link, source_config['url'])
                local_image_path = None
                
                if image_url:
                    image_filename = f"{source_name}_trending_{i}"
                    local_image_path = self.download_image_unique(image_url, image_filename)
                    if local_image_path:
                        print(f"    ✓ Trending image saved: {local_image_path}")
                
                news_list.append({
                    'title': title,
                    'content': final_content,
                    'url': href,
                    'image_url': image_url,
                    'local_image_path': local_image_path,
                    'has_image': bool(local_image_path),
                    'source': f'Trending ({source_name})',
                    'category': category,
                    'buzz_score': buzz_score,
                    'scraped_with': 'social_trending'
                })
                
            print(f"{source_name}: {len(news_list)} trending topics scraped")
            
        except Exception as e:
            print(f" Error scraping trending {source_name}: {e}")
            
        return news_list

    def scrape_single_source_with_images(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Optimized scraping with simple headline-specific image search"""
        # Handle social sources separately
        if source_config.get('is_social', False):
            return self.scrape_social_source(source_name, source_config)
            
        news_list = []
        try:
            print(f"\nConnecting to {source_name}...")
            response = requests.get(source_config['url'], headers=self.headers, timeout=15)
            if response.status_code != 200:
                print(f"{source_name}: Status {response.status_code} - Skipping")
                return news_list
                
            soup = BeautifulSoup(response.content, 'html.parser')
            buzz_level = source_config.get('buzz_level', 'MEDIUM')
            print(f"{source_name}: Connected successfully (Buzz Level: {buzz_level})")
            
            for selector in source_config['selectors']:
                links = soup.select(selector)
                print(f"  Found {len(links)} links with selector {selector}")
                
                for i, link in enumerate(links[:15]):  # Reduced for speed
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not title or len(title) < 15:
                        continue
                    
                    # URL construction with better coverage
                    if href.startswith('/'):
                        base_domain = source_config['url'].split('/')[2]
                        if 'timesofindia' in base_domain:
                            href = 'https://timesofindia.indiatimes.com' + href
                        elif 'indianexpress' in base_domain:
                            href = 'https://indianexpress.com' + href
                        elif 'hindustantimes' in base_domain:
                            href = 'https://www.hindustantimes.com' + href
                        elif 'ndtv' in base_domain:
                            href = 'https://www.ndtv.com' + href
                        elif 'news18' in base_domain:
                            href = 'https://www.news18.com' + href
                        elif 'indiatoday' in base_domain:
                            href = 'https://www.indiatoday.in' + href
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
                    
                    print(f"Processing headline: {title[:50]}...")
                    
                    # Simple content extraction
                    listing_content = self.extract_content_from_listing(link)
                    final_content = listing_content if listing_content else title
                    
                    if len(final_content) < 25:
                        continue
                    
                    buzz_score = self.get_buzz_score(title, final_content, buzz_level)
                    if buzz_score < 4:
                        continue
                    
                    category = self.advanced_categorization(title, final_content)
                    
                    # SIMPLE headline-specific image search
                    image_url = self.extract_simple_headline_image(link, source_config['url'])
                    local_image_path = None
                    
                    if image_url:
                        image_filename = f"{source_name}_headline_{i}"
                        local_image_path = self.download_image_unique(image_url, image_filename)
                        if local_image_path:
                            print(f"    ✓ Headline image saved")
                        else:
                            print(f"    ✗ Image download failed")
                    else:
                        print(f"    ✗ No headline image found")
                    
                    news_list.append({
                        'title': title,
                        'content': final_content,
                        'url': href,
                        'image_url': image_url,
                        'local_image_path': local_image_path,
                        'has_image': bool(local_image_path),
                        'source': source_name.replace('_', ' ').title(),
                        'category': category,
                        'buzz_score': buzz_score,
                        'scraped_with': 'beautifulsoup'
                    })
                    
            images_found = len([item for item in news_list if item['local_image_path']])
            avg_buzz = sum(item['buzz_score'] for item in news_list) / len(news_list) if news_list else 0
            print(f"{source_name}: {len(news_list)} headlines | {images_found} images | Avg Buzz: {avg_buzz:.1f}")
            
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            
        return news_list

    def extract_content_from_listing(self, link_element) -> str:
        """Simple content extraction"""
        try:
            container = link_element.parent
            content_parts = []
            
            if container:
                # Simple search in immediate parent
                content_elements = container.select('.summary, .snippet, p')[:3]
                for elem in content_elements:
                    text = elem.get_text(strip=True)
                    if len(text) > 15 and text != link_element.get_text(strip=True):
                        content_parts.append(text)
            
            full_content = ' '.join(content_parts[:2])
            return full_content[:600] if full_content else ""
        except Exception:
            return ""

    def extract_simple_headline_image(self, link_element, base_url: str) -> str:
        """SIMPLE: Only look for images directly associated with the headline"""
        try:
            print(f"Simple headline image search...")
            
            # Method 1: Look in immediate parent container ONLY
            headline_container = link_element.parent
            if headline_container:
                # Search for images in the same container as the headline
                container_images = headline_container.select('img')
                for img in container_images:
                    img_url = self.get_simple_image_url(img)
                    if img_url and self.is_valid_headline_image(img_url):
                        normalized_url = self.normalize_image_url(img_url, base_url)
                        if normalized_url:
                            print(f"    ✓ Found headline container image")
                            return normalized_url
            
            # Method 2: Look in parent's parent (one level up) - for article cards
            if headline_container and headline_container.parent:
                parent_images = headline_container.parent.select('img')
                for img in parent_images:
                    img_url = self.get_simple_image_url(img)
                    if img_url and self.is_valid_headline_image(img_url):
                        normalized_url = self.normalize_image_url(img_url, base_url)
                        if normalized_url:
                            print(f"    ✓ Found parent level image")
                            return normalized_url
            
            # Method 3: Look for figure/picture elements near the headline
            if headline_container:
                figure_images = headline_container.select('figure img, picture img')
                for img in figure_images:
                    img_url = self.get_simple_image_url(img)
                    if img_url and self.is_valid_headline_image(img_url):
                        normalized_url = self.normalize_image_url(img_url, base_url)
                        if normalized_url:
                            print(f"    ✓ Found figure/picture image")
                            return normalized_url
            
            return None
            
        except Exception as e:
            print(f"    ✗ Simple image search error: {e}")
            return None

    def get_simple_image_url(self, img_element) -> str:
        """Simple image URL extraction"""
        return (img_element.get('src') or 
                img_element.get('data-src') or 
                img_element.get('data-lazy-src'))

    def is_valid_headline_image(self, img_url: str) -> bool:
        """Simple validation for headline images"""
        if not img_url or len(img_url) < 10:
            return False
            
        img_lower = img_url.lower()
        
        # Skip obvious non-content images
        skip_patterns = ['logo', 'icon', 'avatar', 'placeholder', '1x1', 'pixel', 'spacer']
        
        if any(pattern in img_lower for pattern in skip_patterns):
            return False
        
        # Must have valid image extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        return any(ext in img_url.lower() for ext in valid_extensions)

    def normalize_image_url(self, img_url: str, base_url: str) -> str:
        """Normalize image URL"""
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
        """Download image with deduplication"""
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

    def get_buzz_score(self, title: str, content: str, source_buzz_level: str) -> int:
        """Enhanced buzz score calculation"""
        base_score = {'EXTREME': 9, 'HIGH': 7, 'MEDIUM': 5}[source_buzz_level]
        text = (title + ' ' + content).lower()
        
        buzz_keywords = {
            'viral': 4, 'trending': 3, 'breaking': 3, 'exclusive': 3, 
            'shocking': 4, 'controversy': 4, 'scandal': 4, 'arrest': 3,
            'murder': 4, 'politics': 2, 'election': 3, 'bollywood': 2, 
            'cricket': 2, 'technology': 2
        }
        
        keyword_bonus = sum(points for keyword, points in buzz_keywords.items() if keyword in text)
        return min(10, base_score + keyword_bonus)

    def advanced_categorization(self, title: str, content: str) -> str:
        """Enhanced categorization for better category coverage"""
        text = (title + ' ' + content).lower()
        
        # POLITICS
        if any(word in text for word in ['election', 'parliament', 'minister', 'government', 'political', 'bjp', 'congress', 'modi', 'politics', 'vote']):
            return 'politics'
        # CRIME  
        elif any(word in text for word in ['crime', 'police', 'arrest', 'murder', 'rape', 'fraud', 'court', 'jail', 'investigation']):
            return 'crime'
        # MOVIES & ENTERTAINMENT
        elif any(word in text for word in ['movie', 'film', 'actor', 'bollywood', 'cinema', 'box office', 'trailer']):
            return 'movies'
        elif any(word in text for word in ['entertainment', 'celebrity', 'music', 'tv show', 'award', 'concert']):
            return 'entertainment'
        # SPORTS
        elif any(word in text for word in ['cricket', 'football', 'sports', 'match', 'player', 'ipl', 'olympics']):
            return 'sports'
        # BUSINESS  
        elif any(word in text for word in ['business', 'market', 'stock', 'economy', 'startup', 'investment', 'ipo']):
            return 'business'
        # TECHNOLOGY
        elif any(word in text for word in ['technology', 'tech', 'ai', 'software', 'app', 'smartphone', 'digital']):
            return 'technology'
        else:
            return 'entertainment'  # Default fallback

    def get_all_news(self) -> List[Dict]:
        """Get all news from optimized sources"""
        print("Starting OPTIMIZED news extraction (Top 3 per category)...")
        all_news = []
        
        for source_name, config in self.news_sources.items():
            news_data = self.scrape_single_source_with_images(source_name, config)
            all_news.extend(news_data)
            time.sleep(random.uniform(0.5, 1))  # Faster between requests
        
        unique_news = self.remove_duplicates(all_news)
        print(f"Collected {len(unique_news)} unique articles from {len(self.news_sources)} sources")
        return unique_news

    def remove_duplicates(self, news_list: List[Dict]) -> List[Dict]:
        """Remove duplicate news items"""
        unique_news = []
        seen_content = set()
        
        for news in news_list:
            content_hash = hashlib.md5((news['title'] + news['content']).encode()).hexdigest()
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_news.append(news)
        
        return unique_news

    def get_top_10_by_category(self) -> Dict[str, List[Dict]]:
        """Get top 10 trending news items per category"""
        all_news = self.get_all_news()
        categorized = {}
        
        for news in all_news:
            category = news['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(news)
        
        # Limit to top 10 per category based on buzz score
        for category in categorized:
            categorized[category].sort(key=lambda x: x.get('buzz_score', 0), reverse=True)
            categorized[category] = categorized[category][:10]
        
        return categorized

    def save_json_output(self, processed_news: Dict) -> str:
        """Save processed news to JSON file"""
        today = datetime.now().strftime('%Y-%m-%d_%H-%M')
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'categories': processed_news,
            'total_articles': sum(len(articles) for articles in processed_news.values()),
            'total_images': sum(len([a for a in articles if a.get('image_path')]) for articles in processed_news.values())
        }
        
        json_file = self.output_dir / f'news_data_{today}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"JSON data saved to: {json_file}")
        return str(json_file)
