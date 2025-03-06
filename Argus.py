import time
import re
import requests
import uuid
import argparse

# Ollama API configuration
OLLAMA_URL = "http://localhost:11434/api/generate"  
MODEL_NAME = "hermes3"  

# The base system prompt
SYSTEM_PROMPT = """You are Hermes, the divine messenger of the Greek gods, telling an endless story. You are narrating a continuous, flowing tale about gods, heroes, and mythological events. This is a pure monologue - you are never to switch to dialogue format or include other characters speaking with quotation marks and names. You will never include instructions or commands. You must stay in character as Hermes the storyteller at all times. You will never acknowledge that you are an AI or language model. You will continue your mythological narrative indefinitely, transitioning smoothly between different myths and legends as needed."""

USER_PROMPT = "Hermes, please continue telling your endless mythological story without any breaks or character switches."

# API endpoint configuration for the word server
POST_URL = ""
AUTH_TOKEN = ""   
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

# Flag to enable/disable posting to server
ENABLE_POSTING = True

def generate_with_ollama(prompt, max_tokens=300):
    """Generate text using Ollama API"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.85,
            "top_p": 0.92,
            "max_tokens": max_tokens,
            "repeat_penalty": 1.1
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        if response.status_code == 200:
            response_json = response.json()
            return response_json.get("response", "")
        else:
            print(f"\n[Error: Ollama API returned status code {response.status_code}]")
            print(f"Response: {response.text}")
            return ""
    except Exception as e:
        print(f"\n[Error calling Ollama API: {str(e)}]")
        return ""

def send_word_to_server(word, sequence_number, session_id):
    """Send a word to the server with sequence number and auth"""
    try:
        payload = {
            "word": word,
            "sequence": sequence_number,
            "session_id": session_id,
            "timestamp": time.time()
        }
        
        # Add timeout and more robust error handling
        response = requests.post(
            POST_URL, 
            headers=HEADERS, 
            json=payload,
            timeout=5  # 5 second timeout
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"\n[Warning: Failed to send word to server. Status code: {response.status_code}]")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n[Warning: Request to server timed out]")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n[Warning: Connection error when sending to server]")
        return False
    except Exception as e:
        print(f"\n[Error sending word to server: {str(e)}]")
        return False

def display_and_send_paragraph_word_by_word(paragraph, sequence_number, session_id, word_delay=0.25):
    """Display and send a paragraph word by word, returning the updated sequence number"""
    # Split text into words, preserving spaces and punctuation
    words = re.findall(r'\b\w+\b|\s+|[^\w\s]', paragraph)
    
    for word in words:
        if ENABLE_POSTING:
            send_success = send_word_to_server(word, sequence_number, session_id)
            # If posting fails, print a dot to indicate failure without disrupting flow
            if not send_success:
                print(".", end="", flush=True)
        
        sequence_number += 1
        print(word, end="", flush=True)
        time.sleep(word_delay)
    
    return sequence_number

def format_prompt(context_paragraphs):
    """Format the prompt for Ollama with the last 5 paragraphs as context"""
    context = "\n\n".join(context_paragraphs) if context_paragraphs else ""
    return f"{SYSTEM_PROMPT}\n\n{USER_PROMPT}\n\n{context}"

def generate_paragraph(context):
    """Generate a single paragraph using Ollama"""
    prompt = format_prompt(context)
    new_text = generate_with_ollama(prompt)
    
    # Find a natural paragraph ending (period followed by space or end of text)
    paragraph_end = new_text.find(". ", 150)  # Look for period after at least 150 chars
    if paragraph_end == -1:
        # If no good paragraph ending found, use the full text or find last sentence
        last_period = new_text.rfind(".")
        if last_period != -1:
            paragraph = new_text[:last_period + 1]
        else:
            paragraph = new_text
    else:
        paragraph = new_text[:paragraph_end + 1]  # Include the period
    
    return paragraph

def paragraph_based_storytelling(max_time_minutes=None, word_delay=0.25, model=MODEL_NAME):
    """Generate story paragraph by paragraph but display word by word
    
    Args:
        max_time_minutes: Optional time limit in minutes. If None, runs forever until interrupted.
        word_delay: Delay between words in seconds
        model: Ollama model to use
    """
    global MODEL_NAME
    MODEL_NAME = model
    
    # Test server connection before starting
    if ENABLE_POSTING:
        print("Testing connection to word server...")
        try:
            test_payload = {
                "word": "test",
                "sequence": 0,
                "session_id": "test-connection",
                "timestamp": time.time()
            }
            response = requests.post(
                POST_URL, 
                headers=HEADERS, 
                json=test_payload,
                timeout=5
            )
            if response.status_code == 200:
                print("✓ Successfully connected to word server")
            else:
                print(f"⚠ Warning: Server returned status code {response.status_code}")
                print(f"Response: {response.text}")
                print("Continuing anyway, but posting may fail...")
        except Exception as e:
            print(f"⚠ Warning: Could not connect to word server: {str(e)}")
            print("Continuing with local generation only...")
    
    # Create a unique session ID for this run
    session_id = str(uuid.uuid4())
    
    # Word sequence counter
    sequence_number = 0
    
    # Track the last 5 paragraphs for context
    context_paragraphs = []
    
    print(f"Starting Hermes' paragraph-based storytelling with session ID: {session_id}")
    print(f"Using Ollama model: {MODEL_NAME}")
    if max_time_minutes:
        print(f"Will run for {max_time_minutes} minutes")
    else:
        print("Running indefinitely. Press Ctrl+C to stop")
    print()
    
    start_time = time.time()
    end_time = start_time + (max_time_minutes * 60) if max_time_minutes else float('inf')
    total_paragraphs = 0
    
    try:
        while time.time() < end_time:
            # Generate a paragraph using the last 5 paragraphs as context
            paragraph = generate_paragraph(context_paragraphs)
            
            # Display and send the paragraph word by word
            sequence_number = display_and_send_paragraph_word_by_word(
                paragraph, sequence_number, session_id, word_delay
            )
            
            # Update context with the new paragraph, keeping only the last 5
            context_paragraphs.append(paragraph)
            if len(context_paragraphs) > 5:
                context_paragraphs = context_paragraphs[-5:]
            
            total_paragraphs += 1
            
            # Add a subtle transition between paragraphs if needed
            print("\n", end="", flush=True)
            sequence_number = display_and_send_paragraph_word_by_word(
                "\n", sequence_number, session_id, word_delay
            )
    
    except KeyboardInterrupt:
        print("\n\nGeneration stopped by user")
    
    duration = time.time() - start_time
    print(f"\n\nGenerated {total_paragraphs} paragraphs in {duration:.2f} seconds")
    print(f"Sent {sequence_number} words to the server with session ID: {session_id}")

# Run the paragraph-based generation
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Hermes paragraph-based storytelling with Ollama")
    parser.add_argument("--time", type=int, help="Time to run in minutes (if not specified, runs forever)", default=None)
    parser.add_argument("--delay", type=float, help="Delay between words in seconds", default=0.25)
    parser.add_argument("--model", type=str, help="Ollama model to use", default=MODEL_NAME)
    parser.add_argument("--ollama-url", type=str, help="Ollama API URL", default=OLLAMA_URL)
    parser.add_argument("--disable-posting", action="store_true", help="Disable posting to the server")
    parser.add_argument("--post-url", type=str, help="URL for posting words", default=POST_URL)
    parser.add_argument("--auth-token", type=str, help="Authentication token", default=AUTH_TOKEN)
    args = parser.parse_args()
    
    # Update global Ollama URL if provided
    if args.ollama_url:
        OLLAMA_URL = args.ollama_url
    
    # Update posting configuration
    if args.disable_posting:
        ENABLE_POSTING = False
        print("Word posting to server is disabled")
    
    if args.post_url:
        POST_URL = args.post_url
    
    if args.auth_token:
        AUTH_TOKEN = args.auth_token
        HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    paragraph_based_storytelling(max_time_minutes=args.time, word_delay=args.delay, model=args.model)
