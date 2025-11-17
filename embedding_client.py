import os
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in .env")

client = genai.Client(api_key=GOOGLE_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-2.5-pro"


def get_embeddings(texts):
    """Generate embeddings using official google-genai format."""
    if isinstance(texts, str):
        texts = [texts]

    vectors = []
    for text in texts:
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            embedding_obj = response.embeddings[0].values
            vectors.append(np.array(embedding_obj, dtype=np.float32))
        except Exception as e:
            print(f"❌ Embedding error: {e}")
            vectors.append(np.zeros(768, dtype=np.float32))
    return vectors


def generate_text_with_gemini(prompt, max_output_tokens=4096):
    """Generate text with proper error handling."""
    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                temperature=0.7
            )
        )
        
        # Method 1: Try direct text property
        try:
            if response.text:
                print(f"✅ Got response text")
                return response.text
        except:
            pass
        
        # Method 2: Extract from candidates
        if hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            print(f"🔍 Finish reason: {cand.finish_reason}")
            
            # Check for content.parts
            if (hasattr(cand, "content") and cand.content and 
                hasattr(cand.content, "parts") and cand.content.parts):
                
                texts = []
                for part in cand.content.parts:
                    if hasattr(part, "text") and part.text:
                        texts.append(part.text)
                
                if texts:
                    result = "".join(texts)
                    print(f"✅ Extracted {len(result)} chars from parts")
                    return result
        
        print(f"⚠️ Empty response - check finish_reason above")
        return "Error: Model returned empty response. Try with a shorter prompt."
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return f"Error: {str(e)}"
    
    