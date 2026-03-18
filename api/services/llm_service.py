"""
Secure LLM Service Layer for FinTrack
All AI/LLM calls go through this module - API keys never exposed to frontend.
"""
import os
import json
import logging
import base64
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Maximum input length to prevent abuse
MAX_PROMPT_LENGTH = 4000
MAX_IMAGE_SIZE_MB = 5


def _get_openai_client():
    """Get OpenAI client with API key from environment."""
    try:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            logger.warning("OPENAI_API_KEY not configured")
            return None
        return OpenAI(api_key=api_key)
    except ImportError:
        logger.error("openai package not installed")
        return None


def _get_gemini_model():
    """Get Gemini model with API key from environment (fallback for receipt scanning)."""
    try:
        import google.generativeai as genai
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            logger.warning("GEMINI_API_KEY not configured")
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    except ImportError:
        logger.error("google-generativeai package not installed")
        return None


def generate_insights(prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate AI-powered financial insights using OpenAI.
    
    Args:
        prompt: User's question or context for insights
        context: Optional financial data context
        
    Returns:
        AI-generated insight text or fallback message
    """
    # Input validation
    if not prompt or not prompt.strip():
        return "Please provide a valid question or context."
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        return "Input too long. Please shorten your request."
    
    client = _get_openai_client()
    
    if not client:
        logger.info("OpenAI not available, using rule-based fallback")
        return _generate_fallback_insight(context)
    
    try:
        # Build system prompt with financial context
        system_prompt = """You are a helpful financial advisor assistant for FinTrack, 
a personal finance tracking app. Provide concise, actionable financial insights.
Keep responses under 150 words. Focus on practical advice.
Do not provide specific investment advice or guarantees."""

        # Add context if provided
        user_message = prompt
        if context:
            context_str = json.dumps(context, default=str)
            user_message = f"Financial Context: {context_str}\n\nUser Query: {prompt}"
        
        logger.info(f"Calling OpenAI API for insights (prompt length: {len(prompt)})")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        logger.info("OpenAI API call successful")
        return result
        
    except Exception as e:
        logger.error(f"OpenAI API error: {type(e).__name__} - {str(e)[:100]}")
        return _generate_fallback_insight(context)


def scan_receipt_image(image_data: str) -> Dict[str, Any]:
    """
    Scan receipt image using AI to extract transaction data.
    Supports both OpenAI Vision and Gemini as fallback.
    
    Args:
        image_data: Base64 encoded image data
        
    Returns:
        Dict with success status, demo_mode flag, and extracted data
    """
    # Input validation
    if not image_data:
        return {
            'success': False,
            'error': 'No image data provided'
        }
    
    # Check image size (rough estimate)
    if ',' in image_data:
        image_data_clean = image_data.split(',')[1]
    else:
        image_data_clean = image_data
    
    estimated_size_mb = len(image_data_clean) * 0.75 / (1024 * 1024)
    if estimated_size_mb > MAX_IMAGE_SIZE_MB:
        return {
            'success': False,
            'error': f'Image too large. Maximum size is {MAX_IMAGE_SIZE_MB}MB'
        }
    
    # Try OpenAI Vision first
    result = _scan_with_openai(image_data_clean)
    if result['success'] and not result.get('demo_mode'):
        return result
    
    # Fallback to Gemini
    result = _scan_with_gemini(image_data_clean)
    if result['success'] and not result.get('demo_mode'):
        return result
    
    # Demo mode fallback
    logger.info("No AI service available, returning demo data")
    return {
        'success': True,
        'demo_mode': True,
        'data': {
            'amount': '299.00',
            'category': 'Shopping',
            'description': 'Demo: Configure OPENAI_API_KEY or GEMINI_API_KEY for AI scanning',
            'type': 'expense'
        }
    }


def _scan_with_openai(image_data: str) -> Dict[str, Any]:
    """Scan receipt using OpenAI Vision."""
    client = _get_openai_client()
    if not client:
        return {'success': True, 'demo_mode': True, 'data': {}}
    
    try:
        prompt = """Analyze this receipt/transaction image and extract:
{
    "amount": "total amount as number (e.g., 299.50)",
    "category": "Food, Shopping, Transportation, Entertainment, Utilities, Healthcare, Education, or Other",
    "description": "brief description of transaction",
    "type": "expense or income"
}
Return ONLY valid JSON. Focus on TOTAL amount."""

        logger.info("Calling OpenAI Vision API for receipt scan")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=150
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean markdown if present
        if response_text.startswith('```'):
            import re
            response_text = re.sub(r'^```json?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        data = json.loads(response_text)
        logger.info("OpenAI Vision scan successful")
        
        return {
            'success': True,
            'demo_mode': False,
            'data': data
        }
        
    except Exception as e:
        logger.error(f"OpenAI Vision error: {type(e).__name__} - {str(e)[:100]}")
        return {'success': True, 'demo_mode': True, 'data': {}}


def _scan_with_gemini(image_data: str) -> Dict[str, Any]:
    """Scan receipt using Google Gemini."""
    model = _get_gemini_model()
    if not model:
        return {'success': True, 'demo_mode': True, 'data': {}}
    
    try:
        prompt = """Analyze this receipt/transaction screenshot and extract:
{
    "amount": "total amount as number (e.g., 299.50)",
    "category": "Food, Shopping, Transportation, Entertainment, Utilities, Healthcare, Education, or Other",
    "description": "brief description of transaction",
    "type": "expense or income"
}
Return ONLY valid JSON. Focus on TOTAL amount."""

        logger.info("Calling Gemini API for receipt scan")
        
        image_bytes = base64.b64decode(image_data)
        
        response = model.generate_content([
            prompt,
            {'mime_type': 'image/jpeg', 'data': image_bytes}
        ])
        
        response_text = response.text.strip()
        
        # Clean markdown if present
        if response_text.startswith('```'):
            import re
            response_text = re.sub(r'^```json?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        data = json.loads(response_text)
        logger.info("Gemini scan successful")
        
        return {
            'success': True,
            'demo_mode': False,
            'data': data
        }
        
    except Exception as e:
        logger.error(f"Gemini error: {type(e).__name__} - {str(e)[:100]}")
        return {'success': True, 'demo_mode': True, 'data': {}}


def _generate_fallback_insight(context: Optional[Dict[str, Any]] = None) -> str:
    """Generate rule-based insight when AI is unavailable."""
    if not context:
        return "Track your expenses regularly to build better financial habits. Set budgets for each category to stay on track."
    
    # Simple rule-based insights
    insights = []
    
    if context.get('spending_change_pct'):
        change = context['spending_change_pct']
        if change > 20:
            insights.append(f"Your spending increased by {change:.0f}%. Consider reviewing your recent expenses.")
        elif change < -10:
            insights.append(f"Great job! You've reduced spending by {abs(change):.0f}%.")
    
    if context.get('top_category'):
        insights.append(f"Your biggest expense category is {context['top_category']}. Look for ways to optimize.")
    
    if context.get('over_budget_count', 0) > 0:
        insights.append(f"You've exceeded {context['over_budget_count']} budget(s). Time to reassess!")
    
    return " ".join(insights) if insights else "Keep tracking your finances to get personalized insights!"
