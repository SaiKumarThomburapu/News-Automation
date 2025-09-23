#main.py

import os
import logging
import warnings

# SUPPRESS GOOGLE CLOUD WARNINGS - MUST BE AT THE TOP
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")
logging.getLogger('google').setLevel(logging.ERROR)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
from gemini_emotion_processor import NewsToMemeProcessor
from datetime import datetime

load_dotenv()

app = FastAPI(
    title="Complete News Meme Pipeline API", 
    description="Single endpoint for complete news scraping and sarcastic meme processing",
    version="1.0.0"
)

# Initialize processors (warnings are now suppressed)
print("Initializing processors...")
news_extractor = EnhancedNewsExtractorWithImages()
meme_processor = NewsToMemeProcessor()
print("Processors initialized successfully!")

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "api": "Complete News Meme Pipeline",
        "version": "1.0.0",
        "endpoint": "/process-news",
        "description": "Single endpoint that scrapes categorized news and processes with sarcastic AI",
        "features": [
            "Scrapes news by categories (politics, movies, entertainment, sports, business, technology)",
            "10 high-buzz articles per category",
            "Processes with sarcastic Gemini AI",
            "Generates descriptions, emotions, dialogues, hashtags",
            "Matches templates from Supabase",
            "Single API call per article"
        ],
        "status": {
            "scraper": "Ready",
            "processor": f"Ready with {len(meme_processor.api_keys)} API keys",
            "emotions_loaded": len(meme_processor.emotions_db),
            "target_categories": news_extractor.target_categories
        }
    }

@app.get("/process-news")
def complete_news_pipeline():
    """
    COMPLETE PIPELINE: Scrape categorized news → Process with Gemini AI → Return comprehensive data
    """
    try:
        print("\n" + "="*80)
        print("Starting COMPLETE NEWS MEME PIPELINE...")
        print("="*80)
        
        # =====================================================
        # STEP 1: SCRAPE CATEGORIZED NEWS
        # =====================================================
        print("\nSTEP 1: Scraping categorized news (10 per category)...")
        categorized_news = news_extractor.get_all_news()
        
        if not categorized_news:
            raise HTTPException(
                status_code=404,
                detail="No news articles could be scraped from any source"
            )
        
        # Save categorized news to JSON file
        news_json_file = news_extractor.save_single_json_output(categorized_news)
        
        # Calculate scraped stats
        total_scraped = sum(len(articles) for articles in categorized_news.values())
        total_images = 0
        for articles in categorized_news.values():
            total_images += len([a for a in articles if a.get('image_path')])
        
        print(f"\nScraping Results:")
        print(f"  Total articles: {total_scraped}")
        print(f"  Categories: {len(categorized_news)}")
        print(f"  Images scraped: {total_images}")
        print(f"  Saved to: {news_json_file}")
        
        # =====================================================
        # STEP 2: PROCESS WITH SARCASTIC AI
        # =====================================================
        print(f"\nSTEP 2: Processing {total_scraped} articles with sarcastic Gemini AI...")
        processed_memes = meme_processor.process_all_news_articles()
        
        if not processed_memes:
            raise HTTPException(
                status_code=500,
                detail="News was scraped but Gemini processing failed"
            )
        
        # Save processed memes
        memes_json_file = meme_processor.save_processed_news(processed_memes)
        
        print(f"\nProcessing Results:")
        print(f"  Articles processed: {len(processed_memes)}")
        print(f"  Success rate: {(len(processed_memes)/total_scraped*100):.1f}%")
        print(f"  Saved to: {memes_json_file}")
        
        # =====================================================
        # PREPARE COMPREHENSIVE RESPONSE
        # =====================================================
        
        # Calculate processing stats
        templates_found = len([m for m in processed_memes if m.get('template_image_path')])
        categories_processed = list(set([m.get('category', 'unknown') for m in processed_memes]))
        
        # Flatten categorized news for response consistency
        flat_scraped_news = []
        for category, articles in categorized_news.items():
            for article in articles:
                # Add category info to each article
                article_with_category = article.copy()
                article_with_category['scraped_category'] = category
                flat_scraped_news.append(article_with_category)
        
        # Complete response
        complete_response = {
            "timestamp": datetime.now().isoformat(),
            "status": "complete_pipeline_success",
            
            # PIPELINE STATISTICS
            "pipeline_stats": {
                "scraping": {
                    "total_articles": total_scraped,
                    "categories_scraped": list(categorized_news.keys()),
                    "articles_per_category": {cat: len(articles) for cat, articles in categorized_news.items()},
                    "images_scraped": total_images,
                    "scraping_method": "High-buzz selection, 10 per category"
                },
                "processing": {
                    "articles_processed": len(processed_memes),
                    "templates_matched": templates_found,
                    "template_success_rate": f"{(templates_found/len(processed_memes)*100):.1f}%" if processed_memes else "0%",
                    "categories_generated": categories_processed,
                    "gemini_api_calls": len(processed_memes),
                    "processing_method": "Single comprehensive call per article"
                },
                "overall_success_rate": f"{(len(processed_memes)/total_scraped*100):.1f}%" if total_scraped > 0 else "0%"
            },
            
            # OUTPUT FILES
            "output_files": {
                "categorized_news_json": news_json_file,
                "processed_memes_json": memes_json_file,
                "images_directory": "./output/images/"
            },
            
            # CATEGORIZED SCRAPED NEWS DATA
            "categorized_scraped_news": {
                "structure": "Organized by categories",
                "categories": categorized_news
            },
            
            # FLAT SCRAPED NEWS (for compatibility)
            "flat_scraped_news": {
                "total_articles": len(flat_scraped_news),
                "articles": flat_scraped_news
            },
            
            # PROCESSED MEMES DATA  
            "processed_memes_data": {
                "total_memes": len(processed_memes),
                "fields_per_meme": ["description", "category", "hashtags", "dialogues", "url", "template_image_path"],
                "memes": processed_memes
            },
            
            # SAMPLE DATA
            "samples": {
                "sample_categorized_news": {
                    category: articles[:1] for category, articles in categorized_news.items() if articles
                },
                "sample_processed_meme": processed_memes[0] if processed_memes else None
            },
            
            # SYSTEM INFORMATION
            "system_info": {
                "scraper_version": "Enhanced with categorization and buzz scoring",
                "processor_version": "Gemini 2.0 Flash Lite with comprehensive sarcasm",
                "emotion_matching": "Smart Supabase template matching",
                "api_keys_available": len(meme_processor.api_keys),
                "target_categories": ["politics", "movies", "entertainment", "sports", "business", "technology"],
                "processing_features": [
                    "Sarcastic descriptions",
                    "Emotion detection", 
                    "Category classification",
                    "Meme dialogues generation",
                    "Viral hashtags creation",
                    "Template matching"
                ]
            }
        }
        
        print(f"\n" + "="*80)
        print("PIPELINE COMPLETE!")
        print(f"SUCCESS: {total_scraped} articles scraped → {len(processed_memes)} memes generated")
        print(f"Templates matched: {templates_found}/{len(processed_memes)} ({(templates_found/len(processed_memes)*100):.1f}%)")
        print("="*80)
        
        return JSONResponse(content=complete_response)
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean error message from Google warnings
        clean_error = str(e)
        if "ALTS creds ignored" in clean_error:
            clean_error = clean_error.replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
        
        print(f"\nPipeline error: {clean_error}")
        print("="*80)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Complete pipeline failed",
                "message": clean_error,
                "timestamp": datetime.now().isoformat(),
                "suggestion": "Check if news sources are accessible and API keys are configured"
            }
        )

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "news_extractor": "ready",
                "meme_processor": "ready",
                "api_keys": len(meme_processor.api_keys),
                "emotions_loaded": len(meme_processor.emotions_db),
                "supabase": "connected"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    
    print("="*80)
    print("Complete News Meme Pipeline API")
    print("="*80)
    print("Features:")
    print("  - Categorized news scraping (10 per category)")
    print("  - Sarcastic AI processing with Gemini")
    print("  - Emotion-based template matching")
    print("  - Single API call per article")
    print("  - Google Cloud warnings suppressed")
    print("="*80)
    print("Starting server...")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)








# import os
# from dotenv import load_dotenv
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import JSONResponse
# from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
# from gemini_emotion_processor import GeminiEmotionProcessor
# from datetime import datetime

# load_dotenv()

# app = FastAPI(title="Gemini Emotion Meme API v2.0", description="Complete emotion-based meme generation with Supabase templates")

# news_extractor = EnhancedNewsExtractorWithImages()
# meme_processor = GeminiEmotionProcessor()

# @app.get("/memes/emotion-gemini")
# def generate_emotion_memes():
#     """Generate emotion-based memes using Gemini AI + Supabase templates"""
#     try:
#         # Get scraped news
#         categorized_news = news_extractor.get_top_10_by_category()
        
#         if not categorized_news:
#             return {"error": "No news found", "timestamp": datetime.now().isoformat()}
        
#         # Process with Gemini + Supabase (CORRECT METHOD NAME)
#         emotion_memes = meme_processor.process_news_with_emotion_templates(categorized_news)
        
#         # Format response
#         response_data = {
#             "timestamp": datetime.now().isoformat(),
#             "total_memes_generated": len(emotion_memes),
#             "emotion_memes": emotion_memes,
#             "system_info": {
#                 "ai_processor": "Gemini Pro",
#                 "emotion_detection": "Gemini AI with Supabase emotions",
#                 "template_source": "Supabase memes_dc table",
#                 "caption_style": "Meme dialogues",
#                 "hashtag_generation": "AI-generated trending tags"
#             }
#         }
        
#         return JSONResponse(content=response_data)
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Meme generation error: {str(e)}")

