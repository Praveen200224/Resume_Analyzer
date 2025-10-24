import os
try:
    from dotenv import load_dotenv
    import google.generativeai as genai
except ImportError:
    print("Required packages not installed. Please install with: pip install google-generativeai python-dotenv")
    exit(1)

# Load .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("GOOGLE_API_KEY not set in environment or .env file.")
    exit(1)

genai.configure(api_key=API_KEY)

try:
    print("Listing available models for your API key:")
    models = genai.list_models()
    for m in models:
        print(f"Model: {m.name} | Description: {getattr(m, 'description', '')}")
    print("\n---\n")
    print("Attempting Gemini API call:")
    model = genai.GenerativeModel('gemini-2.5-pro')
    response = model.generate_content("Hello, Gemini!")
    print("Gemini API call succeeded. Response:")
    print(response.text)
except Exception as e:
    print("Gemini API call failed:", e)
