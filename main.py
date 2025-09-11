# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
from enhanced_llm_processor_with_images import EnhancedNewsProcessorWithImages
from datetime import datetime

app = FastAPI(title="Enhanced News API v2.0", description="Buzzy news with LLM-generated summaries and images")

news_extractor = EnhancedNewsExtractorWithImages()
news_processor = EnhancedNewsProcessorWithImages()

@app.get("/trending", response_class=PlainTextResponse)
def get_trending_news():
    """Get enhanced trending news with LLM-generated buzzy summaries"""
    try:
        categorized_news = news_extractor.get_top_5_by_category()
        
        if not categorized_news:
            return "No trending news found. Please try again later."
        
        processed_news = news_processor.process_news_with_images(categorized_news)
        
        # Generate outputs
        html_file = news_extractor.generate_html_summary(processed_news)
        json_file = news_extractor.save_json_output(processed_news)
        
        # Create text response
        output = f"ENHANCED TRENDING NEWS WITH LLM SUMMARIES - {datetime.now().strftime('%d %B %Y')}\n"
        output += "=" * 80 + "\n\n"
        
        total_stories = 0
        total_with_images = 0
        
        for category, news_list in processed_news.items():
            if news_list:
                images_count = len([item for item in news_list if item['has_image']])
                avg_buzz = sum(item.get('buzz_score', 5) for item in news_list) / len(news_list)
                
                output += f"{category.upper()} - TOP 5 TRENDING (Avg Buzz: {avg_buzz:.1f}/10)\n"
                output += "-" * 60 + "\n"
                
                for i, news_item in enumerate(news_list, 1):
                    output += f"{i}. {news_item['buzzy_summary']}\n"
                    
                    if news_item['has_image']:
                        output += "   [VISUAL STORY READY]\n"
                        total_with_images += 1
                    else:
                        output += "   [TEXT STORY]\n"
                    
                    output += "\n"
                    total_stories += 1
        
        output += f"COMPLETE PACKAGE:\n"
        output += f"- Stories: {total_stories} (With Images: {total_with_images})\n"
        output += f"- HTML File: {html_file}\n"
        output += f"- JSON File: {json_file}\n"
        output += f"- Images: ./output/images/\n\n"
        output += "All stories enhanced with LLM-generated buzzy summaries (max 3 emojis each)!"
        
        return output
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/category/{category}", response_class=PlainTextResponse)
def get_category_news(category: str):
    """Get enhanced news for specific category"""
    valid_categories = ['movies', 'sports', 'politics', 'business', 'technology', 
                       'health', 'crime', 'international', 'general']
    
    if category.lower() not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Use: {', '.join(valid_categories)}")
    
    try:
        categorized_news = news_extractor.get_top_5_by_category()
        category_news = categorized_news.get(category.lower(), [])
        
        if not category_news:
            return f"No trending {category} news found today. Try another category!"
        
        processed = news_processor.process_news_with_images({category.lower(): category_news})
        category_data = processed.get(category.lower(), [])
        
        images_count = len([item for item in category_data if item['has_image']])
        avg_buzz = sum(item.get('buzz_score', 5) for item in category_data) / len(category_data) if category_data else 0
        
        output = f"{category.upper()} - ENHANCED TRENDING NEWS\n"
        output += f"Date: {datetime.now().strftime('%d %B %Y')} | Avg Buzz: {avg_buzz:.1f}/10 | {images_count}/{len(category_data)} with images\n"
        output += "=" * 80 + "\n\n"
        
        for i, news_item in enumerate(category_data, 1):
            output += f"{i}. {news_item['buzzy_summary']}\n"
            
            if news_item['has_image']:
                output += "   [VIRAL VISUAL READY]\n"
            else:
                output += "   [TRENDING TEXT]\n"
            
            output += "\n"
        
        output += f"Enhanced {category} stories with LLM-generated summaries ready!"
        
        return output
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)










# # main.py
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import PlainTextResponse
# from enhanced_scraper import EnhancedNewsExtractor
# from enhanced_llm_processor import EnhancedNewsProcessor
# from datetime import datetime

# app = FastAPI(title="Litzchill News API", description="Trending news for meme creators")

# # Initialize components
# news_extractor = EnhancedNewsExtractor()
# news_processor = EnhancedNewsProcessor()

# @app.get("/trending", response_class=PlainTextResponse)
# def get_trending_news():
#     """Get top 5 trending news per category with buzzy summaries"""
#     try:
#         # Get top 5 by category
#         categorized_news = news_extractor.get_top_5_by_category()
        
#         if not categorized_news:
#             return "❌ No trending news found. Please try again later."
        
#         # Process for buzzy summaries
#         processed_news = news_processor.process_news_with_ollama(categorized_news)
        
#         # Format output
#         output = f"🔥 TOP TRENDING NEWS BY CATEGORY - {datetime.now().strftime('%d %B %Y')} 🔥\n"
#         output += "=" * 80 + "\n\n"
        
#         total_stories = 0
        
#         for category, news_list in processed_news.items():
#             if news_list:
#                 emoji = news_list[0]['category_emoji']
#                 output += f"{emoji} {category.upper()} - TOP 5 TRENDING\n"
#                 output += "-" * 50 + "\n"
                
#                 for i, news_item in enumerate(news_list, 1):
#                     output += f"{i}. {news_item['buzzy_summary']}\n\n"
#                     total_stories += 1
                
#                 output += "\n"
        
#         output += f"🎯 Total Buzzy Stories: {total_stories} | Perfect for Viral Memes! 🚀"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# @app.get("/category/{category}", response_class=PlainTextResponse)
# def get_category_news(category: str):
#     """Get top 5 trending news for specific category"""
#     valid_categories = ['movies', 'sports', 'politics', 'business', 'technology', 
#                        'health', 'crime', 'international', 'general']
    
#     if category.lower() not in valid_categories:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"❌ Invalid category. Use: {', '.join(valid_categories)}"
#         )
    
#     try:
#         categorized_news = news_extractor.get_top_5_by_category()
#         category_news = categorized_news.get(category.lower(), [])
        
#         if not category_news:
#             return f"❌ No trending {category} news found today. Try another category!"
        
#         # Process single category
#         processed = news_processor.process_news_with_ollama({category.lower(): category_news})
#         category_data = processed.get(category.lower(), [])
        
#         if category_data:
#             emoji = category_data[0]['category_emoji']
#         else:
#             emoji = '📰'
            
#         output = f"{emoji} {category.upper()} - TOP 5 TRENDING NEWS {emoji}\n"
#         output += f"📅 {datetime.now().strftime('%d %B %Y')} | Viral Meme Material! \n"
#         output += "=" * 60 + "\n\n"
        
#         for i, news_item in enumerate(category_data, 1):
#             output += f"{i}. {news_item['buzzy_summary']}\n\n"
        
#         output += f"🎯 {len(category_data)} buzzy {category} stories ready for meme magic! ✨"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)






# # main.py
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import PlainTextResponse
# from enhanced_scraper import EnhancedNewsExtractor
# from enhanced_llm_processor import EnhancedNewsProcessor
# from datetime import datetime

# app = FastAPI(title="Litzchill Enhanced News API", description="Buzzy trending news for meme creators")

# # Initialize components
# news_extractor = EnhancedNewsExtractor()
# news_processor = EnhancedNewsProcessor()

# @app.get("/", response_class=PlainTextResponse)
# def root():
#     return """
# 🔥 LITZCHILL ENHANCED NEWS API 🔥
# Buzzy trending news perfect for viral memes!

# Available endpoints:
# - /trending - Get top 5 trending news per category with buzz
# - /category/{category_name} - Get specific category news  
# - /all-categories - Show all available categories
# - /raw-stats - Quick statistics
# """

# @app.get("/all-categories")
# def get_categories():
#     """Show all available categories"""
#     return {
#         "categories": [
#             "movies", "sports", "politics", "business", 
#             "technology", "health", "crime", "international", "general"
#         ],
#         "description": "Each category contains top 5 trending stories"
#     }

# @app.get("/trending", response_class=PlainTextResponse)
# def get_trending_news():
#     """Get top 5 trending news per category with buzzy summaries"""
#     try:
#         # Get top 5 by category
#         categorized_news = news_extractor.get_top_5_by_category()
        
#         if not categorized_news:
#             return "❌ No trending news found. Please try again later."
        
#         # Process with Ollama for buzzy summaries
#         processed_news = news_processor.process_news_with_ollama(categorized_news)
        
#         # Format output
#         output = f"🔥 TOP TRENDING NEWS BY CATEGORY - {datetime.now().strftime('%d %B %Y')} 🔥\n"
#         output += "=" * 80 + "\n\n"
        
#         total_stories = 0
        
#         for category, news_list in processed_news.items():
#             if news_list:
#                 emoji = news_list[0]['category_emoji']
#                 output += f"{emoji} {category.upper()} - TOP 5 TRENDING\n"
#                 output += "-" * 50 + "\n"
                
#                 for i, news_item in enumerate(news_list, 1):
#                     output += f"{i}. {news_item['buzzy_summary']}\n"
#                     output += f"   📰 {news_item['source']}\n\n"
#                     total_stories += 1
                
#                 output += "\n"
        
#         output += f"🎯 Total Buzzy Stories: {total_stories} | Perfect for Viral Memes! 🚀"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# @app.get("/category/{category}", response_class=PlainTextResponse)
# def get_category_news(category: str):
#     """Get top 5 trending news for specific category"""
#     valid_categories = ['movies', 'sports', 'politics', 'business', 'technology', 
#                        'health', 'crime', 'international', 'general']
    
#     if category.lower() not in valid_categories:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"❌ Invalid category. Use: {', '.join(valid_categories)}"
#         )
    
#     try:
#         categorized_news = news_extractor.get_top_5_by_category()
#         category_news = categorized_news.get(category.lower(), [])
        
#         if not category_news:
#             return f"❌ No trending {category} news found today. Try another category!"
        
#         # Process single category
#         processed = news_processor.process_news_with_ollama({category.lower(): category_news})
#         category_data = processed.get(category.lower(), [])
        
#         if category_data:
#             emoji = category_data[0]['category_emoji']
#         else:
#             emoji = '📰'
            
#         output = f"{emoji} {category.upper()} - TOP 5 TRENDING NEWS {emoji}\n"
#         output += f"📅 {datetime.now().strftime('%d %B %Y')} | Viral Meme Material! \n"
#         output += "=" * 60 + "\n\n"
        
#         for i, news_item in enumerate(category_data, 1):
#             output += f"{i}. {news_item['buzzy_summary']}\n"
#             output += f"   📰 Source: {news_item['source']}\n\n"
        
#         output += f"🎯 {len(category_data)} buzzy {category} stories ready for meme magic! ✨"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# @app.get("/raw-stats")
# def get_stats():
#     """Quick statistics about news sources"""
#     try:
#         categorized_news = news_extractor.get_top_5_by_category()
        
#         stats = {
#             "total_categories": len(categorized_news),
#             "stories_per_category": {cat: len(stories) for cat, stories in categorized_news.items()},
#             "total_stories": sum(len(stories) for stories in categorized_news.values()),
#             "sources_covered": len(news_extractor.news_sources),
#             "timestamp": datetime.now().isoformat()
#         }
        
#         return stats
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)






# # main.py
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import PlainTextResponse
# from scraper import WorkingNewsExtractor  # Your working scraper
# from llm_processor import NewsProcessor
# from datetime import datetime
# import json

# app = FastAPI(title="Litzchill News API", description="Trending news for meme creators")

# # Initialize components
# news_extractor = WorkingNewsExtractor()
# news_processor = NewsProcessor()

# @app.get("/", response_class=PlainTextResponse)
# def root():
#     return """
# 🔥 LITZCHILL NEWS API - WORKING! 🔥
# Your daily dose of meme-worthy trending news!

# Available endpoints:
# - /trending - Get all trending news with meme summaries
# - /category/{category_name} - Get news by category  
# - /daily-digest - Complete news summary
# - /raw-news - Raw scraped news (for testing)
# """

# @app.get("/raw-news")
# def get_raw_news():
#     """Get raw scraped news data for testing"""
#     try:
#         raw_news = news_extractor.get_all_news()
        
#         # Group by category for better display
#         categorized = {}
#         for news in raw_news:
#             cat = news['category']
#             if cat not in categorized:
#                 categorized[cat] = []
#             categorized[cat].append({
#                 'title': news['title'],
#                 'source': news['source'],
#                 'url': news['url']
#             })
        
#         return {
#             "total_headlines": len(raw_news),
#             "categories": categorized,
#             "timestamp": datetime.now().isoformat()
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")

# @app.get("/trending", response_class=PlainTextResponse)
# def get_trending_news():
#     """Get trending news with appealing meme-worthy summaries"""
#     try:
#         # Get fresh scraped news
#         raw_news = news_extractor.get_all_news()
        
#         if not raw_news:
#             return "❌ No trending news found. Please try again later."
        
#         # Process with LLM for appealing summaries
#         processed_news = news_processor.categorize_and_summarize(raw_news)
        
#         # Format output for meme creators
#         output = f"🔥 TRENDING NEWS FOR MEME CREATORS - {datetime.now().strftime('%d %B %Y')} 🔥\n"
#         output += "=" * 70 + "\n\n"
        
#         total_news = 0
#         for category, news_list in processed_news.items():
#             if news_list and category != 'trending':
#                 output += f"📱 {category.upper()} ({len(news_list)} stories)\n"
#                 output += "-" * 40 + "\n"
                
#                 for i, news_item in enumerate(news_list[:3], 1):  # Top 3 per category
#                     output += f"{i}. {news_item['appealing_summary']}\n"
#                     output += f"   📰 Source: {news_item['source']}\n"
#                     output += f"   🔥 Meme Score: {news_item['meme_score']}/10\n\n"
#                     total_news += 1
                
#                 output += "\n"
        
#         # Add trending section
#         if processed_news.get('trending'):
#             output += f"🚨 SUPER TRENDING (High Meme Potential) 🚨\n"
#             output += "-" * 40 + "\n"
#             for i, news_item in enumerate(processed_news['trending'][:5], 1):
#                 output += f"{i}. {news_item['appealing_summary']}\n"
#                 output += f"   📰 Source: {news_item['source']}\n\n"
        
#         output += f"📊 Total Stories: {total_news} | Perfect for Meme Creation! 🎯"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing news: {str(e)}")

# @app.get("/category/{category}", response_class=PlainTextResponse)
# def get_category_news(category: str):
#     """Get trending news for specific category with meme summaries"""
#     valid_categories = ['politics', 'sports', 'entertainment', 'business', 'technology', 'general']
    
#     if category.lower() not in valid_categories:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"❌ Invalid category. Use one of: {', '.join(valid_categories)}"
#         )
    
#     try:
#         raw_news = news_extractor.get_all_news()
        
#         # Filter by category
#         category_news = [news for news in raw_news if news['category'].lower() == category.lower()]
        
#         if not category_news:
#             return f"❌ No trending {category} news found today. Try another category!"
        
#         # Process with LLM
#         processed_news = news_processor.categorize_and_summarize(category_news)
#         category_data = processed_news.get(category.lower(), [])
        
#         output = f"🎯 {category.upper()} TRENDING NEWS 🎯\n"
#         output += f"📅 {datetime.now().strftime('%d %B %Y')} | Perfect for Memes! \n"
#         output += "=" * 50 + "\n\n"
        
#         for i, news_item in enumerate(category_data, 1):
#             output += f"{i}. {news_item['appealing_summary']}\n"
#             output += f"   📰 Source: {news_item['source']}\n"
#             output += f"   🔥 Meme Score: {news_item['meme_score']}/10\n\n"
        
#         output += f"💡 Total {category} stories: {len(category_data)} | Ready for meme magic! ✨"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# @app.get("/daily-digest", response_class=PlainTextResponse)
# def get_daily_digest():
#     """Get complete daily news digest with meme potential"""
#     try:
#         raw_news = news_extractor.get_all_news()
#         processed_news = news_processor.categorize_and_summarize(raw_news)
        
#         output = f"📰 DAILY MEME-WORTHY NEWS DIGEST 📰\n"
#         output += f"🗓️  {datetime.now().strftime('%A, %d %B %Y')} \n"
#         output += "=" * 60 + "\n\n"
        
#         output += "🎯 QUICK OVERVIEW:\n"
#         total_stories = sum(len(news_list) for news_list in processed_news.values())
#         output += f"• Total trending stories: {total_stories}\n"
#         output += f"• High meme potential: {len(processed_news.get('trending', []))}\n"
#         output += f"• Categories covered: {len([cat for cat, news in processed_news.items() if news and cat != 'trending'])}\n\n"
        
#         # Detailed breakdown by category
#         for category, news_list in processed_news.items():
#             if news_list and category != 'trending':
#                 output += f"📱 {category.upper()} HIGHLIGHTS\n"
#                 output += "-" * 30 + "\n"
                
#                 for i, news_item in enumerate(news_list[:3], 1):  # Top 3 per category
#                     output += f"{i}. {news_item['appealing_summary']}\n"
#                     output += f"   Source: {news_item['source']} | Meme Score: {news_item['meme_score']}/10\n\n"
                
#                 output += "\n"
        
#         output += "🔥 Get creative and start making those viral memes! 🚀"
        
#         return output
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)

