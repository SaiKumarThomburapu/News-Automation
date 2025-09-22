import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from enhanced_scraper_with_images import EnhancedNewsExtractorWithImages
from gemini_emotion_processor import GeminiEmotionProcessor
from datetime import datetime

load_dotenv()

app = FastAPI(title="Gemini Emotion Meme API v2.0", description="Complete emotion-based meme generation with Supabase templates")

news_extractor = EnhancedNewsExtractorWithImages()
meme_processor = GeminiEmotionProcessor()

@app.get("/memes/emotion-gemini")
def generate_emotion_memes():
    """Generate emotion-based memes using Gemini AI + Supabase templates"""
    try:
        # Get scraped news
        categorized_news = news_extractor.get_top_10_by_category()
        
        if not categorized_news:
            return {"error": "No news found", "timestamp": datetime.now().isoformat()}
        
        # Process with Gemini + Supabase (CORRECT METHOD NAME)
        emotion_memes = meme_processor.process_news_with_emotion_templates(categorized_news)
        
        # Format response
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "total_memes_generated": len(emotion_memes),
            "emotion_memes": emotion_memes,
            "system_info": {
                "ai_processor": "Gemini Pro",
                "emotion_detection": "Gemini AI with Supabase emotions",
                "template_source": "Supabase memes_dc table",
                "caption_style": "Meme dialogues",
                "hashtag_generation": "AI-generated trending tags"
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Meme generation error: {str(e)}")

