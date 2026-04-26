#!/bin/bash
# GNG Video Maker — Start Script
# Built by Christopher Hughes · Sacramento, CA
# Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
# Truth · Safety · We Got Your Back

echo "Starting GNG Video Maker..."
echo "Python version: $(python --version)"
echo "FFmpeg version: $(ffmpeg -version | head -n 1)"

# Check environment variables
echo "Checking environment variables..."
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OpenAI API key is set"
else
    echo "⚠️  OpenAI API key not set"
fi

if [ -n "$ELEVENLABS_API_KEY" ]; then
    echo "✅ ElevenLabs API key is set"
else
    echo "ℹ️  ElevenLabs API key not set (optional)"
fi

# Create directories if they don't exist
mkdir -p static/audio static/videos static/thumbnails

# Start the application
echo "Starting Flask application on port 8000..."
python app.py
