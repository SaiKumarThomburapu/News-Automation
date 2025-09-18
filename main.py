from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
from enhanced_llm_processor_with_images import EnhancedNewsProcessorWithImages
from datetime import datetime


app = FastAPI(title="Enhanced Meme News API v9.0", description="Complete Indian news with URLs, Reddit, Crime & Social Media")


news_extractor = EnhancedNewsExtractorWithImages()
news_processor = EnhancedNewsProcessorWithImages()


@app.get("/trending")
def get_trending_news():
    try:
        categorized_news = news_extractor.get_top_10_by_category()
        
        if not categorized_news or all(len(items) == 0 for items in categorized_news.values()):
            return {"error": "No trending news found from websites", "timestamp": datetime.now().isoformat()}
        
        # Process with LLM for buzzy summaries and LLM-generated captions
        processed_news = news_processor.process_news_with_images(categorized_news)
        
        # Save JSON output
        json_file = news_extractor.save_json_output(processed_news)
        
        # Calculate statistics from the clean structure
        total_stories = sum(len(articles) for articles in processed_news.values())
        total_with_images = sum(len([a for a in articles if a.get('image_path')]) for articles in processed_news.values())
        
        # Clean JSON response structure
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "version": "9.0",
                "features": [
                    "32+ Indian news sources including Reddit",
                    "Direct news URLs included", 
                    "Enhanced crime & politics coverage",
                    "LLM-generated meme captions (no fallbacks)",
                    "Social media integration (Reddit)",
                    "Clean 5-field structure with URLs"
                ]
            },
            "summary": {
                "total_stories": total_stories,
                "total_with_images": total_with_images,
                "total_categories": len(processed_news),
                "json_file": json_file,
                "major_categories": list(processed_news.keys())
            },
            "categories": {}
        }
        
        # Format category data with clean structure
        for category, news_list in processed_news.items():
            if news_list:
                images_count = len([item for item in news_list if item.get('image_path')])
                
                response_data["categories"][category] = {
                    "count": len(news_list),
                    "images_count": images_count,
                    "news": [
                        {
                            "category": item["category"],
                            "news_summary": item["news_summary"],
                            "captions": item["captions"],
                            "image_path": item["image_path"],
                            "url": item["url"]  # ✅ NEWS URL INCLUDED
                        }
                        for item in news_list
                    ]
                }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/category/{category}")
def get_category_news(category: str):
    """Get news for specific category with URLs"""
    valid_categories = ['politics', 'entertainment', 'movies', 'sports', 'business', 'technology', 'crime']
    
    if category.lower() not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Use: {', '.join(valid_categories)}")
    
    try:
        categorized_news = news_extractor.get_top_10_by_category()
        category_news = categorized_news.get(category.lower(), [])
        
        if not category_news:
            return {
                "error": f"No {category} news found today",
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "suggestion": "Try another category or check back later"
            }
        
        # Process with LLM
        processed = news_processor.process_news_with_images({category.lower(): category_news})
        category_data = processed.get(category.lower(), [])
        
        # Calculate statistics from clean structure
        images_count = len([item for item in category_data if item.get('image_path')])
        
        # Clean response structure
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "category": category.upper(),
            "summary": {
                "total_stories": len(category_data),
                "images_count": images_count
            },
            "news": [
                {
                    "category": item["category"],
                    "news_summary": item["news_summary"],
                    "captions": item["captions"],
                    "image_path": item["image_path"],
                    "url": item["url"]  # ✅ NEWS URL INCLUDED
                }
                for item in category_data
            ]
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "9.0",
        "sources": "32+ including Reddit, TOI, IndianExpress, Scroll, Wire, etc.",
        "features": {
            "news_urls": True,
            "reddit_integration": True,
            "crime_coverage": True,
            "headline_images": True,
            "llm_generated_captions": True,
            "no_fallback_captions": True,
            "clean_5_field_structure": True,
            "major_categories": ["politics", "entertainment", "movies", "sports", "business", "technology", "crime"],
            "twitter_integration": False,
            "selenium_scraping": False,
            "beautifulsoup_scraping": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

