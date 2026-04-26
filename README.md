# GNG Video Maker

**The Good Neighbor Guard Video Maker** - Transform transcripts into powerful presentations with AI voiceover.

Built by Christopher Hughes · Sacramento, CA  
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)  
*Truth · Safety · We Got Your Back*

## Features

🎯 **Intelligent Transcript Processing**
- Analyzes conversation flow and key themes
- Structures content into logical presentation segments
- Optimizes for video narration and engagement

🎙️ **AI Voice Generation**
- Multiple voice styles (Professional, Conversational, Authoritative, Friendly, Dramatic)
- ElevenLabs integration for high-quality speech synthesis
- Dynamic emphasis and pacing based on content

🎬 **Presenter Interface**
- Two-panel synchronized playback
- Real-time script following
- Professional video presentation layout

📤 **Export Options**
- Audio-only downloads
- Full video generation (coming soon)
- Script export for manual editing

## Quick Start

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/fatguylilcoat98/gng-video-maker.git
   cd gng-video-maker
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   export ANTHROPIC_API_KEY="your_anthropic_api_key"
   export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   ```
   http://localhost:8000
   ```

### Deployment on Render

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on [Render](https://render.com)

3. **Connect your forked repository**

4. **Set environment variables:**
   - `ANTHROPIC_API_KEY`: Your Claude API key
   - `ELEVENLABS_API_KEY`: Your ElevenLabs API key

5. **Deploy** - Render will automatically install dependencies and start the service

## API Keys Required

### Anthropic Claude API
- Sign up at [Claude.ai](https://claude.ai) 
- Get your API key from the Claude dashboard
- Used for transcript analysis and content structuring

### ElevenLabs Voice API
- Sign up at [ElevenLabs.io](https://elevenlabs.io)
- Get your API key from your account settings
- Used for AI voice generation and narration

## Usage

1. **Upload or paste your transcript** - Any conversation, meeting notes, or text content
2. **Choose a voice style** - Select from professional to dramatic tones
3. **Add a title** - Optional presentation title
4. **Click "Create Presentation"** - AI processes and structures your content
5. **Preview and play** - Use the presenter interface to review
6. **Export** - Download audio or generate video

## Technology Stack

- **Backend:** FastAPI, Python 3.11+
- **Frontend:** Vanilla JavaScript, CSS Grid/Flexbox
- **AI Services:** Anthropic Claude, ElevenLabs Voice
- **Deployment:** Render (recommended), or any Python hosting

## Project Structure

```
gng-video-maker/
├── app.py                 # Main FastAPI application
├── config.py             # Configuration and settings
├── schemas.py            # Pydantic data models
├── requirements.txt      # Python dependencies
├── modules/              # Processing modules
│   ├── transcript_processor.py
│   ├── voice_generator.py
│   ├── presentation_builder.py
│   ├── video_composer.py
│   └── llm_utils.py
├── ui/                   # Frontend files
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── static/              # Generated content
    ├── audio/
    ├── videos/
    └── thumbnails/
```

## Contributing

This is a Good Neighbor Guard project focused on helping people communicate more effectively. 

**Current priorities:**
- Video generation implementation
- Advanced visual effects
- Mobile-responsive improvements
- Batch processing capabilities

## License

Built with ❤️ for the community. See license for details.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

*Good Neighbor Guard - Truth · Safety · We Got Your Back*