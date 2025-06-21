import json
import boto3
import botocore
import dotenv
import logging
from typing import Dict, List, Any, Optional
import anthropic
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for generating JSON using Claude API
    
    Expected event structure:
    {
        "prompt": "Your user prompt here",
        "tags": ["tag1", "tag2", "tag3"],
        "model": "claude-sonnet-4-20250514"  # Options: claude-sonnet-4-20250514, claude-opus-4-20250514, claude-3-7-sonnet-20250219
    }
    """
    
    try:
        # Parse input
        prompt = event.get('prompt')
        tags = event.get('tags', [])
        model = event.get('model', 'claude-sonnet-4-20250514')  # Latest Claude Sonnet 4
        
        # Validate required inputs
        if not prompt:
            return create_error_response(400, "Missing required field: 'prompt'")
        
        if not isinstance(tags, list):
            return create_error_response(400, "'tags' must be a list of strings")
        
        # Convert tags to strings if they aren't already
        tags = [str(tag) for tag in tags]
        
        # Get API key from environment variables
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            return create_error_response(500, "API configuration error")
        
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Build the user message
        user_message = build_user_message(prompt, tags)
        
        # Use default system prompt if none provided
        if not system_prompt:
            system_prompt = get_default_system_prompt()
        
        logger.info(f"Processing request with model: {model}")
        logger.info(f"Tags provided: {tags}")
        
        # Call Claude API
        response = client.messages.create(
            model=model,
            max_tokens=8000,  # Increased for Claude 4 models (supports up to 64K output tokens)
            temperature=0.1,  # Low temperature for more consistent JSON output
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        
        # Extract the response text
        response_text = response.content[0].text
        
        # Try to parse as JSON to validate
        try:
            parsed_json = json.loads(response_text)
            logger.info("Successfully generated and parsed JSON response")
        except json.JSONDecodeError as e:
            logger.warning(f"Claude response is not valid JSON: {e}")
            # Return the raw response with a warning
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'warning': 'Response is not valid JSON',
                    'raw_response': response_text,
                    'usage': {
                        'input_tokens': response.usage.input_tokens,
                        'output_tokens': response.usage.output_tokens
                    }
                })
            }
        
        # Return successful response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'data': parsed_json,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            })
        }
        
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return create_error_response(500, f"Claude API error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return create_error_response(500, f"Internal error: {str(e)}")


def build_user_message(prompt: str, tags: List[str]) -> str:
    """Build the user message combining prompt and tags"""
    
    message_parts = [prompt]
    
    if tags:
        tags_str = ", ".join(f'"{tag}"' for tag in tags)
        message_parts.append(f"\nTags to consider: {tags_str}")
    
    message_parts.append("\nPlease respond with valid JSON only.")
    
    return "\n".join(message_parts)


def get_default_system_prompt() -> str:
    """Default system prompt for JSON generation"""
    return """You are a helpful Quiz master and has extensive knowledge in various subjects.
  You have knowledge of various competitive exams for general knowledge which are conducted in India.
  Some of the exams are:
  - UPSC Civil Services Exam
  - Common law entrance test (CLAT)
  You are expected to use this knowledge to generate a questions and answers in JSON format 
  based on the user prompt. The JSON should include a question, multiple choice options, and the index of the correct answer.
  
Key requirements:
- Use the sample JSON provided below as a template
- Always generate structured JSON based on the user prompts
- Always respond with valid JSON
- Include relevant metadata when appropriate

Sample JSON format:
 {
        "question": "What is the main difference between CAMT.035 and PACS.002?",
        "options": [
            "CAMT.035 is for acknowledgement, PACS.002 is for final status",
            "They are the same message",
            "PACS.002 is for acknowledgement, CAMT.035 is for final status",
            "CAMT.035 is only for domestic payments"
        ],
        "correct": 0
}"""


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create a standardized error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }


# Optional: Function for testing locally
def test_locally():
    """Function for local testing"""
    test_event = {
        "prompt": "Generate a user profile for an e-commerce application",
        "tags": ["user", "profile", "ecommerce", "preferences"],
        "system_prompt": "Generate JSON for a user profile including personal info, preferences, and purchase history summary."
    }
    
    # Set environment variable for local testing
    os.environ['ANTHROPIC_API_KEY'] = 'your-api-key-here'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_locally()