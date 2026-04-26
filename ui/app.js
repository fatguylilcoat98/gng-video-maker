/*
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
*/

class VideoMaker {
    constructor() {
        this.elements = {
            // Upload elements
            uploadArea: document.getElementById('uploadArea'),
            fileInput: document.getElementById('fileInput'),
            transcriptInput: document.getElementById('transcriptInput'),
            titleInput: document.getElementById('titleInput'),
            voiceStyle: document.getElementById('voiceStyle'),
            processButton: document.getElementById('processButton'),
            btnText: document.querySelector('.btn-text'),
            btnLoader: document.querySelector('.btn-loader'),

            // Status elements
            statusSection: document.getElementById('statusSection'),
            progressFill: document.getElementById('progressFill'),
            statusMessage: document.getElementById('statusMessage'),

            // Presenter elements
            presenterSection: document.getElementById('presenterSection'),
            videoDisplay: document.getElementById('videoDisplay'),
            slideContent: document.getElementById('slideContent'),
            slideTitle: document.getElementById('slideTitle'),
            slideText: document.getElementById('slideText'),
            audioPlayer: document.getElementById('audioPlayer'),
            playPauseBtn: document.getElementById('playPauseBtn'),
            stopBtn: document.getElementById('stopBtn'),
            timeDisplay: document.getElementById('timeDisplay'),
            timelineSlider: document.getElementById('timelineSlider'),
            scriptContent: document.getElementById('scriptContent'),
            scriptInfo: document.getElementById('scriptInfo'),

            // Export elements
            exportAudioBtn: document.getElementById('exportAudioBtn'),
            exportVideoBtn: document.getElementById('exportVideoBtn'),
            exportScriptBtn: document.getElementById('exportScriptBtn')
        };

        this.currentPresentation = null;
        this.currentSegmentIndex = 0;
        this.isPlaying = false;
        this.currentJobId = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
    }

    setupEventListeners() {
        // Upload events
        this.elements.uploadArea.addEventListener('click', () => {
            this.elements.fileInput.click();
        });

        this.elements.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        this.elements.processButton.addEventListener('click', () => {
            this.processTranscript();
        });

        // Player controls
        this.elements.playPauseBtn.addEventListener('click', () => {
            this.togglePlayPause();
        });

        this.elements.stopBtn.addEventListener('click', () => {
            this.stopPresentation();
        });

        this.elements.timelineSlider.addEventListener('input', () => {
            this.seekToPosition();
        });

        this.elements.audioPlayer.addEventListener('timeupdate', () => {
            this.updateProgress();
        });

        this.elements.audioPlayer.addEventListener('ended', () => {
            this.nextSegment();
        });

        // Export events
        this.elements.exportAudioBtn.addEventListener('click', () => {
            this.exportAudio();
        });

        this.elements.exportVideoBtn.addEventListener('click', () => {
            this.generateVideo();
        });

        this.elements.exportScriptBtn.addEventListener('click', () => {
            this.exportScript();
        });
    }

    setupDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.elements.uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.elements.uploadArea.addEventListener(eventName, () => {
                this.elements.uploadArea.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.elements.uploadArea.addEventListener(eventName, () => {
                this.elements.uploadArea.classList.remove('dragover');
            });
        });

        this.elements.uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    async handleFileSelect(file) {
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            this.elements.transcriptInput.value = e.target.result;

            // Auto-generate title from filename
            if (!this.elements.titleInput.value) {
                const title = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, ' ');
                this.elements.titleInput.value = this.capitalizeWords(title);
            }
        };
        reader.readAsText(file);
    }

    capitalizeWords(str) {
        return str.replace(/\w\S*/g, (txt) =>
            txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
        );
    }

    async processTranscript() {
        const transcript = this.elements.transcriptInput.value.trim();

        if (!transcript) {
            this.showError('Please enter a transcript to process');
            return;
        }

        this.setProcessingState(true);
        this.showStatusSection();

        const requestData = {
            transcript: transcript,
            title: this.elements.titleInput.value || 'GNG Presentation',
            voice_style: this.elements.voiceStyle.value
        };

        try {
            const response = await fetch('/process-transcript', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.currentJobId = result.job_id;

            if (result.status === 'completed') {
                // Handle immediate completion
                this.loadPresentation(result.presentation_url);
            } else {
                // Poll for status updates
                this.pollJobStatus();
            }

        } catch (error) {
            console.error('Error processing transcript:', error);
            this.showError('Failed to process transcript. Please try again.');
        }
    }

    async pollJobStatus() {
        if (!this.currentJobId) return;

        try {
            const response = await fetch(`/status/${this.currentJobId}`);
            const status = await response.json();

            this.updateProgress(status.progress);
            this.elements.statusMessage.textContent = status.message;

            if (status.status === 'completed') {
                this.loadPresentation(`/presentation/${this.currentJobId}`);
            } else if (status.status === 'failed') {
                this.showError('Processing failed: ' + status.message);
            } else {
                // Continue polling
                setTimeout(() => this.pollJobStatus(), 1000);
            }

        } catch (error) {
            console.error('Error polling status:', error);
            this.showError('Failed to check processing status');
        }
    }

    async loadPresentation(url) {
        try {
            const response = await fetch(url);
            const presentationData = await response.json();

            this.currentPresentation = presentationData.presentation;
            this.hideStatusSection();
            this.showPresenterSection();
            this.setupPresentation();

        } catch (error) {
            console.error('Error loading presentation:', error);
            this.showError('Failed to load presentation data');
        }
    }

    setupPresentation() {
        if (!this.currentPresentation) return;

        this.currentSegmentIndex = 0;

        // Update script info
        this.elements.scriptInfo.innerHTML = `
            <span>${this.currentPresentation.segments.length} segments</span>
            <span>${Math.round(this.currentPresentation.total_duration)}s total</span>
        `;

        // Load first segment
        this.loadSegment(0);
        this.renderScript();
    }

    loadSegment(index) {
        if (!this.currentPresentation || index >= this.currentPresentation.segments.length) {
            return;
        }

        const segment = this.currentPresentation.segments[index];
        const voiceSegment = this.currentPresentation.voice_segments.find(
            vs => vs.segment_id === segment.id
        );

        // Update slide content
        this.elements.slideTitle.textContent = this.stripMarkdown(segment.title);
        this.elements.slideText.textContent = this.stripMarkdown(segment.narration_text);

        // Update audio
        if (voiceSegment) {
            this.elements.audioPlayer.src = voiceSegment.audio_url;
        }

        this.currentSegmentIndex = index;
        this.highlightCurrentSegment();
    }

    renderScript() {
        if (!this.currentPresentation) return;

        const scriptHtml = this.currentPresentation.segments.map((segment, index) => {
            const voiceSegment = this.currentPresentation.voice_segments.find(
                vs => vs.segment_id === segment.id
            );

            return `
                <div class="script-segment" data-segment-index="${index}">
                    <div class="segment-header">
                        <h4 class="segment-title">${this.stripMarkdown(segment.title)}</h4>
                        <span class="segment-type">${segment.type}</span>
                        <span class="segment-duration">${voiceSegment ? Math.round(voiceSegment.duration) + 's' : ''}</span>
                    </div>
                    <p class="segment-narration">${this.stripMarkdown(segment.narration_text)}</p>
                    <div class="segment-cues">
                        ${segment.visual_cues.map(cue => `<span class="cue-tag">${this.stripMarkdown(cue)}</span>`).join('')}
                    </div>
                </div>
            `;
        }).join('');

        this.elements.scriptContent.innerHTML = scriptHtml;

        // Add click handlers for segments
        this.elements.scriptContent.querySelectorAll('.script-segment').forEach((el, index) => {
            el.addEventListener('click', () => {
                this.loadSegment(index);
            });
        });
    }

    highlightCurrentSegment() {
        // Remove previous highlights
        this.elements.scriptContent.querySelectorAll('.script-segment').forEach(el => {
            el.classList.remove('current-segment');
        });

        // Highlight current segment
        const currentEl = this.elements.scriptContent.querySelector(
            `[data-segment-index="${this.currentSegmentIndex}"]`
        );
        if (currentEl) {
            currentEl.classList.add('current-segment');
            currentEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.pausePresentation();
        } else {
            this.playPresentation();
        }
    }

    playPresentation() {
        if (this.elements.audioPlayer.src) {
            this.elements.audioPlayer.play();
            this.isPlaying = true;
            this.elements.playPauseBtn.textContent = '⏸️';
        }
    }

    pausePresentation() {
        this.elements.audioPlayer.pause();
        this.isPlaying = false;
        this.elements.playPauseBtn.textContent = '▶️';
    }

    stopPresentation() {
        this.elements.audioPlayer.pause();
        this.elements.audioPlayer.currentTime = 0;
        this.isPlaying = false;
        this.elements.playPauseBtn.textContent = '▶️';
        this.loadSegment(0);
    }

    seekToPosition() {
        if (this.elements.audioPlayer.duration) {
            const seekTime = (this.elements.timelineSlider.value / 100) * this.elements.audioPlayer.duration;
            this.elements.audioPlayer.currentTime = seekTime;
        }
    }

    updateProgress(progress = null) {
        if (progress !== null) {
            // Update processing progress
            this.elements.progressFill.style.width = progress + '%';
        } else if (this.elements.audioPlayer.duration) {
            // Update playback progress
            const progress = (this.elements.audioPlayer.currentTime / this.elements.audioPlayer.duration) * 100;
            this.elements.timelineSlider.value = progress;

            const current = this.formatTime(this.elements.audioPlayer.currentTime);
            const total = this.formatTime(this.elements.audioPlayer.duration);
            this.elements.timeDisplay.textContent = `${current} / ${total}`;
        }
    }

    nextSegment() {
        const nextIndex = this.currentSegmentIndex + 1;
        if (nextIndex < this.currentPresentation.segments.length) {
            this.loadSegment(nextIndex);
            if (this.isPlaying) {
                setTimeout(() => this.playPresentation(), 500); // Small delay between segments
            }
        } else {
            // Presentation finished
            this.stopPresentation();
        }
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // UI State Management
    setProcessingState(processing) {
        this.elements.processButton.disabled = processing;

        if (processing) {
            this.elements.btnText.style.display = 'none';
            this.elements.btnLoader.style.display = 'flex';
        } else {
            this.elements.btnText.style.display = 'inline';
            this.elements.btnLoader.style.display = 'none';
        }
    }

    showStatusSection() {
        this.elements.statusSection.style.display = 'block';
        this.elements.presenterSection.style.display = 'none';
    }

    hideStatusSection() {
        this.elements.statusSection.style.display = 'none';
        this.setProcessingState(false);
    }

    showPresenterSection() {
        this.elements.presenterSection.style.display = 'block';
    }

    showError(message) {
        this.setProcessingState(false);
        alert(message); // Replace with better error UI later
        console.error(message);
    }

    // Export Functions
    exportAudio() {
        // Placeholder - would need backend support
        alert('Audio export feature coming soon!');
    }

    async generateVideo() {
        if (!this.currentPresentation) {
            this.showError('No presentation loaded for video generation');
            return;
        }

        try {
            // Update button to show progress
            const originalText = this.elements.exportVideoBtn.textContent;
            this.elements.exportVideoBtn.disabled = true;

            // Start video generation
            const response = await fetch('/generate-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    presentation_data: this.currentPresentation
                })
            });

            if (!response.ok) {
                throw new Error(`Video generation failed: ${response.status}`);
            }

            const result = await response.json();
            const videoJobId = result.job_id;

            // Poll for video generation status
            this.pollVideoStatus(videoJobId, originalText);

        } catch (error) {
            console.error('Error starting video generation:', error);
            this.showError('Failed to start video generation: ' + error.message);
            this.elements.exportVideoBtn.disabled = false;
        }
    }

    async pollVideoStatus(jobId, originalButtonText) {
        try {
            const response = await fetch(`/status/${jobId}`);
            const status = await response.json();

            // Update button with progress
            this.elements.exportVideoBtn.textContent = status.message || 'Generating video...';

            if (status.status === 'completed') {
                // Video is ready for download
                const videoResult = status.result;
                this.downloadVideoFile(videoResult.video_url);

                this.elements.exportVideoBtn.textContent = originalButtonText;
                this.elements.exportVideoBtn.disabled = false;

            } else if (status.status === 'failed') {
                this.showError('Video generation failed: ' + status.message);
                this.elements.exportVideoBtn.textContent = originalButtonText;
                this.elements.exportVideoBtn.disabled = false;

            } else {
                // Continue polling
                setTimeout(() => this.pollVideoStatus(jobId, originalButtonText), 2000);
            }

        } catch (error) {
            console.error('Error checking video status:', error);
            this.showError('Failed to check video generation status');
            this.elements.exportVideoBtn.textContent = originalButtonText;
            this.elements.exportVideoBtn.disabled = false;
        }
    }

    downloadVideoFile(videoUrl) {
        // Trigger download
        const a = document.createElement('a');
        a.href = videoUrl;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    stripMarkdown(text) {
        // Remove markdown formatting for clean script export
        return text
            .replace(/\*\*(.*?)\*\*/g, '$1')  // Bold
            .replace(/\*(.*?)\*/g, '$1')      // Italic
            .replace(/`(.*?)`/g, '$1')        // Code
            .replace(/#{1,6}\s*(.*)/g, '$1')  // Headers
            .replace(/\[(.*?)\]\(.*?\)/g, '$1')  // Links
            .replace(/^[\s]*[-*+]\s+/gm, '')  // List items
            .replace(/\s+/g, ' ')             // Extra whitespace
            .trim();
    }

    exportScript() {
        if (!this.currentPresentation) {
            this.showError('No presentation to export');
            return;
        }

        const scriptText = this.currentPresentation.segments.map(segment => {
            const cleanTitle = this.stripMarkdown(segment.title);
            const cleanNarration = this.stripMarkdown(segment.narration_text);
            const cleanCues = segment.visual_cues.map(cue => this.stripMarkdown(cue)).join(', ');

            return `${cleanTitle}\n${'='.repeat(cleanTitle.length)}\n\n${cleanNarration}\n\nVisual Cues: ${cleanCues}\n\n`;
        }).join('');

        const blob = new Blob([scriptText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.currentPresentation.title || 'presentation'}-script.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VideoMaker();
});

// Add CSS for script segments
const additionalCSS = `
.script-segment {
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.script-segment:hover {
    border-color: var(--primary-blue);
    background: rgba(0, 212, 255, 0.05);
}

.script-segment.current-segment {
    border-color: var(--primary-orange);
    background: rgba(255, 107, 53, 0.1);
    box-shadow: 0 0 10px var(--glow-orange);
}

.segment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    gap: 1rem;
}

.segment-title {
    color: var(--text-primary);
    font-size: 1rem;
    margin: 0;
}

.segment-type {
    background: var(--surface-darker);
    color: var(--text-secondary);
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
}

.segment-duration {
    color: var(--text-muted);
    font-size: 0.8rem;
    font-family: 'DM Mono', monospace;
}

.segment-narration {
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0.5rem 0;
}

.segment-cues {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.cue-tag {
    background: var(--border-subtle);
    color: var(--text-muted);
    font-size: 0.7rem;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
}
`;

// Add the CSS to the page
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);