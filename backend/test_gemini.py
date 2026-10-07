import os
from dotenv import load_dotenv
import google.generativeai as genai

def test_gemini():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("GEMINI CONNECTION: FAIL - No API key found")
        return
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemma-4-26b-a4b-it")
        
        # Make a minimal test prompt
        print("Testing connection...")
        response = model.generate_content("Say the word 'Hello'.")
        
        if response and response.text:
            print("GEMINI CONNECTION: PASS")
            print("MODEL RESPONSE: PASS")
        else:
            print("GEMINI CONNECTION: PASS")
            print("MODEL RESPONSE: FAIL - Empty response")
            
    except Exception as e:
        print("GEMINI CONNECTION: FAIL")
        print(f"ERROR: {type(e).__name__} - {str(e)}")

if __name__ == "__main__":
    test_gemini()
