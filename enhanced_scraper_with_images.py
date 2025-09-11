# enhanced_scraper_with_images.py
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

class EnhancedNewsExtractorWithImages:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # ENHANCED NEWS SOURCES - Including Social Media Trending
        self.news_sources = {
            # TIMES OF INDIA - Working sections
            'toi_sports': {
                'url': 'https://timesofindia.indiatimes.com/sports',
                'selectors': ['a[href*="/cricket/"]', 'a[href*="/sports/"]', 'h2 a', 'h3 a'],
                'buzz_level': 'HIGH'
            },
            'toi_entertainment': {
                'url': 'https://timesofindia.indiatimes.com/entertainment',
                'selectors': ['a[href*="/entertainment/"]', 'a[href*="/bollywood/"]', 'h2 a', 'h3 a'],
                'buzz_level': 'HIGH'
            },
            'toi_business': {
                'url': 'https://timesofindia.indiatimes.com/business',
                'selectors': ['a[href*="/business/"]', 'h2 a', 'h3 a'],
                'buzz_level': 'MEDIUM'
            },
            
            # INDIAN EXPRESS - All categories
            'ie_trending': {
                'url': 'https://indianexpress.com/section/trending/',
                'selectors': ['h2 a', 'h3 a', '.story-title a', '.headline a'],
                'buzz_level': 'HIGH'
            },
            'ie_politics': {
                'url': 'https://indianexpress.com/section/politics/',
                'selectors': ['h2 a', 'h3 a', '.headline a', '.politics-title a'],
                'buzz_level': 'HIGH'
            },
            'ie_entertainment': {
                'url': 'https://indianexpress.com/section/entertainment/',
                'selectors': ['h2 a', 'h3 a', '.entertainment-title a', '.headline a'],
                'buzz_level': 'HIGH'
            },
            'ie_business': {
                'url': 'https://indianexpress.com/section/business/',
                'selectors': ['h2 a', 'h3 a', '.business-title a', '.headline a'],
                'buzz_level': 'MEDIUM'
            },
            'ie_technology': {
                'url': 'https://indianexpress.com/section/technology/',
                'selectors': ['h2 a', 'h3 a', '.tech-headline a', '.headline a'],
                'buzz_level': 'MEDIUM'
            },
            
            # NEWS18 - Enhanced
            'news18_sports': {
                'url': 'https://www.news18.com/cricketnext/',
                'selectors': ['h1 a', 'h2 a', 'h3 a', '.sports-title a'],
                'buzz_level': 'HIGH'
            },
            'news18_entertainment': {
                'url': 'https://www.news18.com/movies/',
                'selectors': ['h1 a', 'h2 a', 'h3 a', '.movie-title a'],
                'buzz_level': 'HIGH'
            },
            'news18_business': {
                'url': 'https://www.news18.com/business/',
                'selectors': ['h1 a', 'h2 a', 'h3 a', '.business-story a'],
                'buzz_level': 'MEDIUM'
            },
            
            # NPR - International 
            'npr_politics': {
                'url': 'https://www.npr.org/sections/politics/',
                'selectors': ['h2 a', 'h3 a', '.story-title a', '.headline a'],
                'buzz_level': 'HIGH'
            },
            'npr_technology': {
                'url': 'https://www.npr.org/sections/technology/',
                'selectors': ['h2 a', 'h3 a', '.story-title a', '.headline a'],
                'buzz_level': 'MEDIUM'
            },
            'npr_entertainment': {
                'url': 'https://www.npr.org/sections/arts/',
                'selectors': ['h2 a', 'h3 a', '.story-title a', '.headline a'],
                'buzz_level': 'MEDIUM'
            },
            
            # SOCIAL MEDIA TRENDING SOURCES - NEW!
            'reddit_india_trending': {
                'url': 'https://www.reddit.com/r/india/hot/',
                'selectors': ['h3 a', '[data-click-id="body"] h3', '.title a'],
                'buzz_level': 'EXTREME'
            },
            'reddit_bollywood': {
                'url': 'https://www.reddit.com/r/bollywood/hot/',
                'selectors': ['h3 a', '[data-click-id="body"] h3', '.title a'],
                'buzz_level': 'EXTREME'
            },
            'reddit_cricket': {
                'url': 'https://www.reddit.com/r/Cricket/hot/',
                'selectors': ['h3 a', '[data-click-id="body"] h3', '.title a'],
                'buzz_level': 'EXTREME'
            },
            
            # YOUTUBE TRENDING
            'youtube_trending_india': {
                'url': 'https://www.youtube.com/feed/trending?gl=IN',
                'selectors': ['#video-title', '.ytd-video-renderer h3 a', '#video-title-link'],
                'buzz_level': 'HIGH'
            },
            
            # ADDITIONAL WORKING SOURCES
            'bbc_trending': {
                'url': 'https://www.bbc.com/news/trending',
                'selectors': ['h2 a', 'h3 a', '.trending-story a'],
                'buzz_level': 'MEDIUM'
            },
            'india_today': {
                'url': 'https://www.indiatoday.in/trending-news',
                'selectors': ['h1 a', 'h2 a', 'h3 a', '.trending-title a'],
                'buzz_level': 'HIGH'
            },
            'zee_news': {
                'url': 'https://zeenews.india.com/entertainment',
                'selectors': ['h1 a', 'h2 a', 'h3 a', '.entertainment-link a'],
                'buzz_level': 'HIGH'
            },
            'times_now': {
                'url': 'https://www.timesnownews.com/trending',
                'selectors': ['h1 a', 'h2 a', 'h3 a', '.trending-news a'],
                'buzz_level': 'HIGH'
            }
        }
        
        self.downloaded_image_hashes = set()
        self.setup_output_directory()

    def setup_output_directory(self):
        """Setup and clean output directory"""
        self.output_dir = Path('./output')
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'images').mkdir(exist_ok=True)
        print("Output directory setup complete")

    def get_image_hash(self, image_content: bytes) -> str:
        return hashlib.sha256(image_content).hexdigest()

    def extract_content_from_listing(self, link_element) -> str:
        """Extract detailed content below headline from listing page"""
        try:
            container = link_element.parent
            content_parts = []
            
            if container:
                for level in range(4):  # Look deeper for more content
                    if container:
                        content_selectors = [
                            '.summary', '.snippet', '.description', '.excerpt', 
                            '.intro', '.lead', '.standfirst', '.subhead',
                            '.article-summary', '.story-summary', '.news-summary',
                            'p', '.content', '.text', '.story-excerpt'
                        ]
                        
                        for selector in content_selectors:
                            content_elements = container.select(selector)
                            for elem in content_elements:
                                text = elem.get_text(strip=True)
                                if (len(text) > 40 and 
                                    text != link_element.get_text(strip=True) and
                                    not text.startswith(('Photo:', 'Image:', 'Video:'))):
                                    content_parts.append(text)
                        
                        container = container.parent
            
            # Check siblings for additional context
            sibling = link_element.find_next_sibling()
            while sibling and len(content_parts) < 4:
                if sibling.name in ['p', 'div', 'span']:
                    text = sibling.get_text(strip=True)
                    if len(text) > 40:
                        content_parts.append(text)
                sibling = sibling.find_next_sibling()
            
            full_content = ' '.join(content_parts[:4])  # Max 4 pieces
            return full_content[:1000] if full_content else ""
            
        except Exception:
            return ""

    def extract_full_article_content(self, article_url: str) -> str:
        """Extract full article content"""
        try:
            response = requests.get(article_url, headers=self.headers, timeout=12)
            if response.status_code != 200:
                return ""
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            content_selectors = [
                'div.article-content', 'div.story-content', 'section.article-body',
                'div.post-content', 'div.entry-content', 'div#main-content',
                'article div.content', 'div.news-detail', 'div.full-text',
                'div.articleBody', 'div.story-element', 'div.ArticleBody-articleBody',
                '.story-body', '.article-body', '.news-content'
            ]
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    paragraphs = content_div.find_all(['p', 'div'])
                    content_parts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if (len(text) > 60 and 
                            not text.startswith(('Photo:', 'Image:', 'Also Read:', 'ALSO READ:', 'READ MORE:'))):
                            content_parts.append(text)
                    
                    full_content = ' '.join(content_parts)
                    if len(full_content) > 300:
                        return full_content[:2000]  # Increased for better LLM context
            
            return ""
        except Exception:
            return ""

    def get_buzz_score(self, title: str, content: str, source_buzz_level: str) -> int:
        """Enhanced buzz scoring"""
        base_score = {'EXTREME': 9, 'HIGH': 7, 'MEDIUM': 5}[source_buzz_level]
        
        text = (title + ' ' + content).lower()
        
        buzz_keywords = {
            'viral': 3, 'trending': 2, 'shocking': 3, 'exclusive': 2,
            'breaking': 2, 'controversy': 3, 'scandal': 3, 'bizarre': 3,
            'weird': 2, 'funny': 2, 'hilarious': 3, 'epic': 2,
            'fail': 2, 'drama': 2, 'fight': 2, 'clash': 2,
            'amazing': 1, 'incredible': 2, 'unbelievable': 2,
            'reddit': 2, 'twitter': 2, 'social media': 2, 'youtube': 2
        }
        
        keyword_bonus = sum(points for keyword, points in buzz_keywords.items() if keyword in text)
        
        if len(content) > 500:
            keyword_bonus += 2  # Better content gets higher score
        
        return min(10, base_score + keyword_bonus)

    # Keep all existing helper methods (extract_headline_image, normalize_image_url, etc.)
    def extract_headline_image(self, link_element, base_url: str) -> str:
        try:
            container = link_element.parent
            if container:
                for _ in range(3):
                    if container:
                        img = container.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                            if img_url and self.is_valid_news_image(img_url):
                                return self.normalize_image_url(img_url, base_url)
                        container = container.parent
            return None
        except Exception:
            return None

    def normalize_image_url(self, img_url: str, base_url: str) -> str:
        if not img_url or img_url.startswith('data:'):
            return None
        if img_url.startswith('//'):
            return 'https:' + img_url
        elif img_url.startswith('/'):
            return urljoin(base_url, img_url)
        elif img_url.startswith('http'):
            return img_url
        else:
            return urljoin(base_url + '/', img_url)

    def is_valid_news_image(self, img_url: str) -> bool:
        if not img_url or len(img_url) < 15:
            return False
        img_lower = img_url.lower()
        skip_patterns = ['logo', 'icon', 'avatar', 'placeholder', 'ad_', 'banner', 'social']
        if any(pattern in img_lower for pattern in skip_patterns):
            return False
        valid_patterns = ['.jpg', '.jpeg', '.png', '.webp', '.gif', 'image', 'photo']
        return any(pattern in img_lower for pattern in valid_patterns)

    def download_image_unique(self, image_url: str, filename: str) -> str:
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                image_content = response.content
                image_hash = self.get_image_hash(image_content)
                
                if image_hash in self.downloaded_image_hashes:
                    return None
                
                self.downloaded_image_hashes.add(image_hash)
                ext = image_url.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = 'jpg'
                
                filename_with_ext = f"{filename}.{ext}"
                image_path = self.output_dir / 'images' / filename_with_ext
                
                with open(image_path, 'wb') as f:
                    f.write(image_content)
                
                return str(image_path)
        except Exception:
            pass
        return None

    def scrape_single_source_with_images(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Enhanced scraping - MINIMUM 15 articles with full content"""
        news_list = []
        
        try:
            response = requests.get(source_config['url'], headers=self.headers, timeout=15)
            if response.status_code != 200:
                print(f"{source_name}: Status {response.status_code}")
                return news_list
                
            soup = BeautifulSoup(response.content, 'html.parser')
            buzz_level = source_config.get('buzz_level', 'MEDIUM')
            print(f"{source_name}: Connected successfully (Buzz Level: {buzz_level})")
            
            for selector in source_config['selectors']:
                links = soup.select(selector)[:30]  # Get more to ensure 15+ quality
                
                for link in links:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not title or len(title) < 20:
                        continue
                    
                    if href.startswith('/'):
                        href = source_config['url'] + href
                    elif not href.startswith('http'):
                        continue
                    
                    # Extract content from listing first
                    listing_content = self.extract_content_from_listing(link)
                    
                    # Get full content for first 10 articles per source
                    full_content = ""
                    if len(news_list) < 10:
                        full_content = self.extract_full_article_content(href)
                    
                    # Combine best content
                    final_content = full_content if full_content else listing_content if listing_content else ""
                    
                    # Only proceed if we have substantial content for LLM
                    if len(final_content) < 50:
                        continue
                    
                    buzz_score = self.get_buzz_score(title, final_content, buzz_level)
                    
                    if buzz_score < 5:
                        continue
                    
                    category = self.advanced_categorization(title, final_content)
                    
                    # Extract image
                    image_url = self.extract_headline_image(link, source_config['url'])
                    local_image_path = None
                    if image_url:
                        image_filename = f"{source_name}_{len(news_list)}"
                        local_image_path = self.download_image_unique(image_url, image_filename)
                    
                    news_list.append({
                        'title': title,
                        'content': final_content,  # Full content for LLM processing
                        'listing_content': listing_content,
                        'full_content': full_content,
                        'url': href,
                        'image_url': image_url,
                        'local_image_path': local_image_path,
                        'has_image': bool(local_image_path),
                        'source': source_name.replace('_', ' ').title(),
                        'category': category,
                        'buzz_score': buzz_score,
                        'content_length': len(final_content),
                        'has_full_content': bool(full_content),
                        'source_buzz_level': buzz_level
                    })
                
                if len(news_list) >= 15:  # Ensure minimum 15 articles
                    break
            
            images_found = len([item for item in news_list if item['local_image_path']])
            full_content_count = len([item for item in news_list if item['has_full_content']])
            avg_buzz = sum(item['buzz_score'] for item in news_list) / len(news_list) if news_list else 0
            
            print(f"{source_name}: {len(news_list)} articles | {full_content_count} full content | {images_found} images | Avg Buzz: {avg_buzz:.1f}")
            
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            
        return news_list

    def advanced_categorization(self, title: str, content: str) -> str:
        """FIXED categorization - politics goes to politics"""
        text = (title + ' ' + content).lower()
        
        # POLITICS FIRST - Higher priority for political keywords
        if any(word in text for word in [
            'election', 'parliament', 'minister', 'government', 'modi', 'congress',
            'bjp', 'political', 'pm', 'chief minister', 'assembly', 'vote', 'policy',
            'president', 'supreme court', 'law', 'constitution', 'politics', 'politician',
            'campaign', 'democracy', 'cabinet', 'governance', 'legislature'
        ]):
            return 'politics'
        elif any(word in text for word in [
            'movie', 'film', 'actor', 'actress', 'bollywood', 'hollywood', 'director',
            'cinema', 'box office', 'trailer', 'release', 'oscar', 'award', 'celebrity',
            'music', 'album', 'concert', 'song', 'singer', 'musician', 'entertainment'
        ]):
            return 'movies'
        elif any(word in text for word in [
            'cricket', 'football', 'soccer', 'tennis', 'basketball', 'match', 'player',
            'team', 'tournament', 'championship', 'olympics', 'ipl', 'world cup',
            'score', 'goal', 'win', 'defeat', 'champion', 'sports'
        ]):
            return 'sports'
        elif any(word in text for word in [
            'market', 'stock', 'rupee', 'business', 'company', 'economy', 'bank',
            'investment', 'profit', 'loss', 'trade', 'finance', 'gdp', 'inflation',
            'startup', 'ipo', 'revenue', 'funding', 'economic'
        ]):
            return 'business'
        elif any(word in text for word in [
            'technology', 'tech', 'ai', 'artificial intelligence', 'software', 'app',
            'google', 'apple', 'microsoft', 'phone', 'iphone', 'android', 'internet',
            'cyber', 'data', 'digital', 'innovation'
        ]):
            return 'technology'
        elif any(word in text for word in [
            'health', 'medical', 'hospital', 'doctor', 'disease', 'medicine',
            'covid', 'virus', 'vaccine', 'treatment', 'patient', 'healthcare'
        ]):
            return 'health'
        elif any(word in text for word in [
            'crime', 'police', 'arrest', 'murder', 'theft', 'security', 'terrorism',
            'investigation', 'court', 'jail', 'accused', 'suspect'
        ]):
            return 'crime'
        elif any(word in text for word in [
            'international', 'world', 'global', 'country', 'nations', 'embassy',
            'foreign', 'diplomacy', 'war', 'conflict', 'peace', 'treaty'
        ]):
            return 'international'
        else:
            return 'general'

    # Keep all other existing methods (get_all_news, remove_duplicates, etc.)
    def get_all_news(self) -> List[Dict]:
        print("Starting enhanced news extraction with social media sources...")
        all_news = []
        for source_name, config in self.news_sources.items():
            news_data = self.scrape_single_source_with_images(source_name, config)
            all_news.extend(news_data)
            time.sleep(1)
        print(f"Total articles collected: {len(all_news)}")
        unique_news = self.remove_duplicates(all_news)
        unique_images_count = len([item for item in unique_news if item['local_image_path']])
        print(f"Unique articles: {len(unique_news)} ({unique_images_count} unique images)")
        return unique_news

    def remove_duplicates(self, news_list: List[Dict]) -> List[Dict]:
        unique_news = []
        seen_titles = []
        for news in news_list:
            title_words = set(news['title'].lower().split())
            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(seen_title.lower().split())
                if title_words and seen_words:
                    similarity = len(title_words.intersection(seen_words)) / len(title_words.union(seen_words))
                    if similarity > 0.7:
                        is_duplicate = True
                        break
            if not is_duplicate:
                seen_titles.append(news['title'])
                unique_news.append(news)
        return unique_news

    def get_top_5_by_category(self) -> Dict[str, List[Dict]]:
        all_news = self.get_all_news()
        categorized = {}
        for news in all_news:
            category = news['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(news)
        
        top_5_by_category = {}
        for category, news_list in categorized.items():
            sorted_news = sorted(news_list, key=lambda x: (
                x['buzz_score'], x['has_image'], len(x['content'])
            ), reverse=True)
            top_5_by_category[category] = sorted_news[:5]
        return top_5_by_category

    def save_json_output(self, processed_news: Dict):
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'execution_date': datetime.now().strftime('%d %B %Y'),
            'categories': processed_news,
            'summary': {
                'total_stories': sum(len(stories) for stories in processed_news.values()),
                'stories_with_images': sum(
                    len([s for s in stories if s.get('has_image')]) 
                    for stories in processed_news.values()
                )
            }
        }
        json_file = self.output_dir / 'news_data.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"JSON data saved to: {json_file}")
        return json_file

    def generate_html_summary(self, processed_news: Dict):
        html_content = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<title>Enhanced News Summary</title>',
            '<style>',
            'body { font-family: Arial, sans-serif; margin: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }',
            '.container { max-width: 1200px; margin: 0 auto; }',
            '.header { text-align: center; color: white; margin-bottom: 30px; }',
            '.category { margin-bottom: 40px; background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }',
            '.category h2 { color: #333; border-bottom: 3px solid #ff6b35; padding-bottom: 10px; }',
            '.news-item { margin-bottom: 30px; padding: 20px; border-left: 5px solid #ff6b35; background: #f9f9f9; border-radius: 10px; }',
            '.buzzy-headline { font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px; line-height: 1.5; }',
            '.buzz-score { display: inline-block; padding: 4px 8px; background: #ff6b35; color: white; border-radius: 12px; font-size: 12px; margin-bottom: 10px; }',
            '.news-image { max-width: 100%; height: auto; border-radius: 10px; margin-top: 15px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); }',
            '.no-image { color: #666; font-style: italic; margin-top: 10px; }',
            '</style>',
            '</head>',
            '<body>',
            '<div class="container">',
            f'<div class="header"><h1>Enhanced News Summary</h1><p>{datetime.now().strftime("%d %B %Y")} | With Social Media Trends</p></div>'
        ]
        
        for category, news_list in processed_news.items():
            if news_list:
                html_content.append('<div class="category">')
                html_content.append(f'<h2>{category.title()} News</h2>')
                
                for news in news_list:
                    html_content.append('<div class="news-item">')
                    buzz_score = news.get('buzz_score', 5)
                    html_content.append(f'<div class="buzz-score">BUZZ: {buzz_score}/10</div>')
                    html_content.append(f'<div class="buzzy-headline">{news["buzzy_summary"]}</div>')
                    
                    if news.get('local_image_path') and Path(news['local_image_path']).exists():
                        img_relative = Path(news['local_image_path']).relative_to(self.output_dir)
                        html_content.append(f'<img src="{img_relative}" alt="News Image" class="news-image">')
                    else:
                        html_content.append('<div class="no-image">No image available</div>')
                    
                    html_content.append('</div>')
                html_content.append('</div>')
        
        html_content.extend(['</div>', '</body>', '</html>'])
        html_file = self.output_dir / 'news_summary.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
        print(f"HTML summary generated: {html_file}")
        return html_file









# # enhanced_scraper_with_images.py
# import requests
# from bs4 import BeautifulSoup
# from typing import List, Dict
# from urllib.parse import urljoin
# import time
# import concurrent.futures

# class EnhancedNewsExtractorWithImages:
#     def __init__(self):
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#             'Accept-Encoding': 'gzip, deflate',
#             'Connection': 'keep-alive',
#         }
        
#         # Updated sources - REMOVED: firstpost, scroll, bbc_world, hindustan_times
#         # ADDED: scraper-friendly alternatives
#         self.news_sources = {
#             # Working Indian Sources (Keep These)
#             'times_of_india': {
#                 'url': 'https://timesofindia.indiatimes.com',
#                 'selectors': ['a[href*="/news/"]', 'a[href*="/articleshow/"]'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
#             'indian_express': {
#                 'url': 'https://indianexpress.com', 
#                 'selectors': ['h2 a', 'h3 a', '[class*="title"] a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
#             'news18': {
#                 'url': 'https://www.news18.com',
#                 'selectors': ['h2 a', 'h3 a', '.story-card a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
            
#             # Working International Sources (Keep These)
#             'cnn': {
#                 'url': 'https://edition.cnn.com',
#                 'selectors': ['h3 a', '.container__link'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
#             'reuters': {
#                 'url': 'https://www.reuters.com',
#                 'selectors': ['h3 a', '.story-title a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
            
#             # NEW SCRAPER-FRIENDLY SOURCES (24x7 Allowed)
#             'ap_news': {
#                 'url': 'https://apnews.com',
#                 'selectors': ['h2 a', 'h3 a', '.CardHeadline a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
#             'npr': {
#                 'url': 'https://www.npr.org',
#                 'selectors': ['h2 a', 'h3 a', '.story-title a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
#             'abc_news': {
#                 'url': 'https://abcnews.go.com',
#                 'selectors': ['h2 a', 'h3 a', '.ContentRoll__Headline a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             },
#             'business_standard': {
#                 'url': 'https://www.business-standard.com',
#                 'selectors': ['h2 a', 'h3 a', '.headline a'],
#                 'image_selectors': ['img.lazy', 'img[data-src]', 'img']
#             }
#         }

#     def extract_headline_image(self, link_element, base_url: str) -> str:
#         """Extract image specifically for the headline from the same container"""
#         try:
#             # Look for image in the same container as the headline
#             container = link_element.parent
#             if container:
#                 # Try to find image in parent container
#                 for _ in range(3):  # Check up to 3 parent levels
#                     if container:
#                         img = container.find('img')
#                         if img:
#                             img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
#                             if img_url and self.is_valid_news_image(img_url):
#                                 return self.normalize_image_url(img_url, base_url)
#                         container = container.parent
                        
#             # If not found in container, check siblings
#             sibling = link_element.find_next_sibling()
#             while sibling and sibling.name:
#                 img = sibling.find('img')
#                 if img:
#                     img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
#                     if img_url and self.is_valid_news_image(img_url):
#                         return self.normalize_image_url(img_url, base_url)
#                 sibling = sibling.find_next_sibling()
                
#             return None
            
#         except Exception as e:
#             print(f"Error extracting headline image: {e}")
#             return None

#     def extract_article_page_image(self, article_url: str, base_url: str) -> str:
#         """Extract main image from article page (fallback method)"""
#         try:
#             response = requests.get(article_url, headers=self.headers, timeout=8)
#             soup = BeautifulSoup(response.content, 'html.parser')
            
#             # Priority order for article images
#             image_selectors = [
#                 'meta[property="og:image"]',      # Open Graph (most reliable)
#                 'meta[name="twitter:image"]',     # Twitter card
#                 '.story-image img',               # Common news image class
#                 '.article-image img',             # Another common pattern
#                 'article img:first-of-type',      # First image in article
#                 '.lead-image img',                # Lead image
#                 '.featured-image img',            # Featured image
#                 'img[alt*="representat"]',        # Representative images
#                 'img'                             # Fallback to any image
#             ]
            
#             for selector in image_selectors:
#                 if 'meta' in selector:
#                     meta = soup.select_one(selector)
#                     if meta and meta.get('content'):
#                         img_url = meta.get('content')
#                         if self.is_valid_news_image(img_url):
#                             return self.normalize_image_url(img_url, base_url)
#                 else:
#                     img = soup.select_one(selector)
#                     if img:
#                         img_url = img.get('src') or img.get('data-src')
#                         if img_url and self.is_valid_news_image(img_url):
#                             return self.normalize_image_url(img_url, base_url)
                            
#             return None
            
#         except Exception as e:
#             print(f"Error extracting article image from {article_url}: {e}")
#             return None

#     def normalize_image_url(self, img_url: str, base_url: str) -> str:
#         """Convert relative URLs to absolute URLs"""
#         if not img_url or img_url.startswith('data:'):
#             return None
            
#         if img_url.startswith('//'):
#             return 'https:' + img_url
#         elif img_url.startswith('/'):
#             return urljoin(base_url, img_url)
#         elif img_url.startswith('http'):
#             return img_url
#         else:
#             return urljoin(base_url + '/', img_url)

#     def is_valid_news_image(self, img_url: str) -> bool:
#         """Check if image URL is valid for news content"""
#         if not img_url or len(img_url) < 15:
#             return False
            
#         img_lower = img_url.lower()
        
#         # Skip unwanted images
#         skip_patterns = [
#             'logo', 'icon', 'avatar', 'profile', 'placeholder', 'loading',
#             'advertisement', 'ad_', 'banner', '1x1', 'spacer', 'pixel',
#             'facebook', 'twitter', 'social', 'share', 'comment'
#         ]
        
#         if any(pattern in img_lower for pattern in skip_patterns):
#             return False
            
#         # Must contain image indicators
#         valid_patterns = [
#             '.jpg', '.jpeg', '.png', '.webp', '.gif',
#             'image', 'photo', 'pic', 'thumb', 'resize'
#         ]
        
#         # Check minimum dimensions in URL (some sites include dimensions)
#         dimension_patterns = ['150x', '200x', '300x', 'w_150', 'w_200', 'w_300']
#         has_good_dimensions = any(pattern in img_lower for pattern in dimension_patterns)
        
#         return any(pattern in img_lower for pattern in valid_patterns) or has_good_dimensions

#     def scrape_single_source_with_images(self, source_name: str, source_config: Dict) -> List[Dict]:
#         """Enhanced scraping with headline-specific image extraction"""
#         news_list = []
        
#         try:
#             response = requests.get(source_config['url'], headers=self.headers, timeout=15)
#             if response.status_code != 200:
#                 print(f"❌ {source_name}: Status {response.status_code}")
#                 return news_list
                
#             soup = BeautifulSoup(response.content, 'html.parser')
#             print(f"✅ {source_name}: Connected successfully")
            
#             for selector in source_config['selectors']:
#                 links = soup.select(selector)[:12]  # Get more links
                
#                 for link in links:
#                     title = link.get_text(strip=True)
#                     href = link.get('href', '')
                    
#                     if not title or len(title) < 25:
#                         continue
                    
#                     # Make URL absolute
#                     if href.startswith('/'):
#                         href = source_config['url'] + href
#                     elif not href.startswith('http'):
#                         continue
                    
#                     # STEP 1: Try to get image from the same headline container (FAST)
#                     image_url = self.extract_headline_image(link, source_config['url'])
                    
#                     # STEP 2: If no image found, try article page (SLOWER - only for first 5 articles)
#                     if not image_url and len(news_list) < 5:
#                         image_url = self.extract_article_page_image(href, source_config['url'])
                    
#                     news_list.append({
#                         'title': title,
#                         'content': self.generate_buzz_content(title),
#                         'url': href,
#                         'image_url': image_url,
#                         'has_image': bool(image_url),
#                         'source': source_name.replace('_', ' ').title(),
#                         'category': self.advanced_categorization(title, '')
#                     })
                
#                 if len(news_list) >= 10:  # Limit per source
#                     break
            
#             images_found = len([item for item in news_list if item['image_url']])
#             print(f"✅ {source_name}: Extracted {len(news_list)} articles ({images_found} with images)")
            
#         except Exception as e:
#             print(f"❌ Error scraping {source_name}: {e}")
            
#         return news_list

#     def generate_buzz_content(self, title: str) -> str:
#         """Generate buzz content for better LLM processing"""
#         buzz_elements = [
#             "Breaking news that's creating massive social media buzz!",
#             "This story has all the elements for viral meme content.",
#             "Perfect trending topic for meme creators right now!",
#             "Social media is going crazy over this development."
#         ]
#         return f"{title} {buzz_elements[len(title) % len(buzz_elements)]}"

#     def advanced_categorization(self, title: str, content: str) -> str:
#         """Enhanced categorization for news content"""
#         text = (title + ' ' + content).lower()
        
#         # Movies/Entertainment
#         if any(word in text for word in [
#             'movie', 'film', 'actor', 'actress', 'bollywood', 'hollywood', 'director',
#             'cinema', 'box office', 'trailer', 'release', 'oscar', 'award', 'celebrity',
#             'music', 'album', 'concert', 'song', 'singer', 'musician', 'entertainment'
#         ]):
#             return 'movies'
        
#         # Sports
#         elif any(word in text for word in [
#             'cricket', 'football', 'soccer', 'tennis', 'basketball', 'match', 'player',
#             'team', 'tournament', 'championship', 'olympics', 'ipl', 'world cup',
#             'score', 'goal', 'win', 'defeat', 'champion', 'sports'
#         ]):
#             return 'sports'
        
#         # Politics
#         elif any(word in text for word in [
#             'election', 'parliament', 'minister', 'government', 'modi', 'congress',
#             'bjp', 'political', 'pm', 'chief minister', 'assembly', 'vote', 'policy',
#             'president', 'supreme court', 'law', 'constitution', 'politics'
#         ]):
#             return 'politics'
        
#         # Business/Economy
#         elif any(word in text for word in [
#             'market', 'stock', 'rupee', 'business', 'company', 'economy', 'bank',
#             'investment', 'profit', 'loss', 'trade', 'finance', 'gdp', 'inflation',
#             'startup', 'ipo', 'revenue', 'funding', 'economic'
#         ]):
#             return 'business'
        
#         # Technology
#         elif any(word in text for word in [
#             'technology', 'tech', 'ai', 'artificial intelligence', 'software', 'app',
#             'google', 'apple', 'microsoft', 'phone', 'iphone', 'android', 'internet',
#             'cyber', 'data', 'digital', 'innovation'
#         ]):
#             return 'technology'
        
#         # Health
#         elif any(word in text for word in [
#             'health', 'medical', 'hospital', 'doctor', 'disease', 'medicine',
#             'covid', 'virus', 'vaccine', 'treatment', 'patient', 'healthcare'
#         ]):
#             return 'health'
        
#         # Crime/Security
#         elif any(word in text for word in [
#             'crime', 'police', 'arrest', 'murder', 'theft', 'security', 'terrorism',
#             'investigation', 'court', 'jail', 'accused', 'suspect'
#         ]):
#             return 'crime'
        
#         # International
#         elif any(word in text for word in [
#             'international', 'world', 'global', 'country', 'nations', 'embassy',
#             'foreign', 'diplomacy', 'war', 'conflict', 'peace', 'treaty'
#         ]):
#             return 'international'
        
#         else:
#             return 'general'

#     def get_all_news(self) -> List[Dict]:
#         """Get news from all sources with parallel processing"""
#         print("🚀 Starting enhanced news extraction with images...\n")
        
#         all_news = []
        
#         # Sequential processing for better stability
#         for source_name, config in self.news_sources.items():
#             news_data = self.scrape_single_source_with_images(source_name, config)
#             all_news.extend(news_data)
#             time.sleep(1)  # Be respectful
        
#         print(f"\n📊 Total articles collected: {len(all_news)}")
        
#         # Remove duplicates
#         unique_news = self.remove_duplicates(all_news)
#         images_count = len([item for item in unique_news if item['image_url']])
#         print(f"📊 Unique articles: {len(unique_news)} ({images_count} with images)")
        
#         return unique_news

#     def remove_duplicates(self, news_list: List[Dict]) -> List[Dict]:
#         """Remove duplicate news based on title similarity"""
#         unique_news = []
#         seen_titles = []
        
#         for news in news_list:
#             title_words = set(news['title'].lower().split())
#             is_duplicate = False
            
#             for seen_title in seen_titles:
#                 seen_words = set(seen_title.lower().split())
#                 if title_words and seen_words:
#                     similarity = len(title_words.intersection(seen_words)) / len(title_words.union(seen_words))
                    
#                     if similarity > 0.7:
#                         is_duplicate = True
#                         break
            
#             if not is_duplicate:
#                 seen_titles.append(news['title'])
#                 unique_news.append(news)
        
#         return unique_news

#     def get_top_5_by_category(self) -> Dict[str, List[Dict]]:
#         """Get top 5 news for each category with images"""
#         all_news = self.get_all_news()
        
#         # Group by category
#         categorized = {}
#         for news in all_news:
#             category = news['category']
#             if category not in categorized:
#                 categorized[category] = []
#             categorized[category].append(news)
        
#         # Get top 5 from each category, prioritize items with images
#         top_5_by_category = {}
#         for category, news_list in categorized.items():
#             # Sort by: 1) Has image (priority), 2) Title length (quality indicator)
#             sorted_news = sorted(news_list, key=lambda x: (x['has_image'], len(x['title'])), reverse=True)
#             top_5_by_category[category] = sorted_news[:5]
        
#         return top_5_by_category
