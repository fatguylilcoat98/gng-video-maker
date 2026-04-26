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
            videoModeInputs: document.querySelectorAll('input[name="videoMode"]'),
            processButton: document.getElementById('processButton'),
            btnText: document.querySelector('.btn-text'),
            btnLoader: document.querySelector('.btn-loader'),

            // Phase switcher
            transcriptModeBtn: document.getElementById('transcriptModeBtn'),
            videoModeBtn: document.getElementById('videoModeBtn'),
            backToTranscriptBtn: document.getElementById('backToTranscriptBtn'),

            // Phase 3: Video upload elements
            videoUploadSection: document.getElementById('videoUploadSection'),
            uploadSection: document.querySelector('.upload-section'),
            videoUploadArea: document.getElementById('videoUploadArea'),
            videoFileInput: document.getElementById('videoFileInput'),
            videoUploadStatus: document.getElementById('videoUploadStatus'),
            videoProgressFill: document.getElementById('videoProgressFill'),
            videoStatusMessage: document.getElementById('videoStatusMessage'),
            videoAnalysisResults: document.getElementById('videoAnalysisResults'),
            analysisSummary: document.getElementById('analysisSummary'),
            continueToProcessingBtn: document.getElementById('continueToProcessingBtn'),

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
        this.currentVideoAnalysis = null; // Phase 3
        this.currentMode = 'transcript'; // 'transcript' or 'video'

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

        // Phase switcher events
        this.elements.transcriptModeBtn.addEventListener('click', () => {
            this.switchToTranscriptMode();
        });

        this.elements.videoModeBtn.addEventListener('click', () => {
            this.switchToVideoMode();
        });

        this.elements.backToTranscriptBtn.addEventListener('click', () => {
            this.switchToTranscriptMode();
        });

        // Phase 3: Video upload events
        this.elements.videoUploadArea.addEventListener('click', () => {
            this.elements.videoFileInput.click();
        });

        this.elements.videoFileInput.addEventListener('change', (e) => {
            this.handleVideoUpload(e.target.files[0]);
        });

        this.elements.continueToProcessingBtn.addEventListener('click', () => {
            this.continueToContentExtraction();
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

    setupVideoDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.elements.videoUploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.elements.videoUploadArea.addEventListener(eventName, () => {
                this.elements.videoUploadArea.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.elements.videoUploadArea.addEventListener(eventName, () => {
                this.elements.videoUploadArea.classList.remove('dragover');
            });
        });

        this.elements.videoUploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleVideoUpload(files[0]);
            }
        });
    }

    // ============================================================================
    // PHASE 3: VIDEO MODE FUNCTIONALITY
    // ============================================================================

    switchToTranscriptMode() {
        this.currentMode = 'transcript';

        // Update UI
        this.elements.transcriptModeBtn.classList.add('active');
        this.elements.videoModeBtn.classList.remove('active');

        // Show/hide sections
        this.elements.uploadSection.style.display = 'block';
        this.elements.videoUploadSection.style.display = 'none';
    }

    switchToVideoMode() {
        this.currentMode = 'video';

        // Update UI
        this.elements.videoModeBtn.classList.add('active');
        this.elements.transcriptModeBtn.classList.remove('active');

        // Show/hide sections
        this.elements.uploadSection.style.display = 'none';
        this.elements.videoUploadSection.style.display = 'block';

        // Setup video drag and drop if not already done
        if (!this.videoDragDropSetup) {
            this.setupVideoDragAndDrop();
            this.videoDragDropSetup = true;
        }
    }

    async handleVideoUpload(file) {
        if (!file) return;

        // Validate file type
        const allowedTypes = ['video/mp4', 'video/mov', 'video/webm', 'video/avi'];
        if (!allowedTypes.includes(file.type)) {
            this.showError('Please upload a video file (MP4, MOV, WebM, or AVI)');
            return;
        }

        // Check file size (500MB limit)
        const maxSize = 500 * 1024 * 1024; // 500MB in bytes
        if (file.size > maxSize) {
            this.showError('Video file too large. Please keep files under 500MB.');
            return;
        }

        try {
            // Show upload status
            this.elements.videoUploadStatus.style.display = 'block';
            this.elements.videoAnalysisResults.style.display = 'none';
            this.updateVideoProgress(0, 'Uploading video...');

            // Create form data
            const formData = new FormData();
            formData.append('video', file);

            // Upload video
            const response = await fetch('/upload-video', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }

            const result = await response.json();
            this.currentJobId = result.job_id;

            // Start polling for analysis results
            this.pollVideoAnalysis();

        } catch (error) {
            console.error('Error uploading video:', error);
            this.showError('Failed to upload video: ' + error.message);
            this.elements.videoUploadStatus.style.display = 'none';
        }
    }

    async pollVideoAnalysis() {
        if (!this.currentJobId) return;

        try {
            const response = await fetch(`/video-analysis/${this.currentJobId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                this.currentVideoAnalysis = data.analysis;
                this.displayVideoAnalysis(data.analysis);
            } else if (data.status === 'failed') {
                this.showError('Video analysis failed: ' + data.message);
                this.elements.videoUploadStatus.style.display = 'none';
            } else {
                // Update progress and continue polling
                this.updateVideoProgress(data.progress || 50, data.message || 'Analyzing video...');
                setTimeout(() => this.pollVideoAnalysis(), 1000);
            }

        } catch (error) {
            console.error('Error polling video analysis:', error);
            this.showError('Failed to get analysis status');
            this.elements.videoUploadStatus.style.display = 'none';
        }
    }

    updateVideoProgress(progress, message) {
        this.elements.videoProgressFill.style.width = progress + '%';
        this.elements.videoStatusMessage.textContent = message;
    }

    displayVideoAnalysis(analysis) {
        // Hide upload status, show results
        this.elements.videoUploadStatus.style.display = 'none';
        this.elements.videoAnalysisResults.style.display = 'block';

        const videoInfo = analysis.video_info;
        const sceneCount = analysis.scene_changes.length;
        const silenceCount = analysis.silence_periods.length;

        // Format duration
        const minutes = Math.floor(videoInfo.duration / 60);
        const seconds = Math.floor(videoInfo.duration % 60);

        // Create analysis summary
        this.elements.analysisSummary.innerHTML = `
            <div class="analysis-item">
                <span class="analysis-label">Duration:</span>
                <span class="analysis-value">${minutes}:${seconds.toString().padStart(2, '0')}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Resolution:</span>
                <span class="analysis-value">${videoInfo.width}×${videoInfo.height}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Scene Changes:</span>
                <span class="analysis-value">${sceneCount} detected</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Silence Periods:</span>
                <span class="analysis-value">${silenceCount} detected</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Audio:</span>
                <span class="analysis-value">${videoInfo.has_audio ? 'Present' : 'Not detected'}</span>
            </div>
        `;

        // Show continue button
        this.elements.continueToProcessingBtn.style.display = 'block';
    }

    async continueToContentExtraction() {
        if (!this.currentJobId || !this.currentVideoAnalysis) {
            this.showError('No video analysis data available');
            return;
        }

        try {
            // Update button to show processing
            this.elements.continueToProcessingBtn.disabled = true;
            this.elements.continueToProcessingBtn.textContent = 'Processing...';

            // Get title for the video
            const title = prompt('Enter a title for your video presentation:', 'Video Presentation') || 'Video Presentation';

            // Start Steps 3-4: Auto-trim and script generation
            const response = await fetch('/process-video-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    analysis_job_id: this.currentJobId,
                    title: title
                })
            });

            if (!response.ok) {
                throw new Error(`Processing failed: ${response.status}`);
            }

            const result = await response.json();
            this.currentProcessingJobId = result.job_id;

            // Show processing status and poll for results
            this.showVideoProcessingStatus();
            this.pollVideoProcessing();

        } catch (error) {
            console.error('Error starting video processing:', error);
            this.showError('Failed to start video processing: ' + error.message);
            this.elements.continueToProcessingBtn.disabled = false;
            this.elements.continueToProcessingBtn.textContent = 'Continue to Content Extraction';
        }
    }

    showVideoProcessingStatus() {
        // Hide analysis results, show processing status
        this.elements.videoAnalysisResults.style.display = 'none';
        this.elements.videoUploadStatus.style.display = 'block';
        this.updateVideoProgress(0, 'Starting video processing...');
    }

    async pollVideoProcessing() {
        if (!this.currentProcessingJobId) return;

        try {
            const response = await fetch(`/video-processing/${this.currentProcessingJobId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                this.displayVideoProcessingResults(data.processing);
            } else if (data.status === 'failed') {
                this.showError('Video processing failed: ' + data.message);
                this.resetToAnalysisResults();
            } else {
                // Update progress and continue polling
                this.updateVideoProgress(data.progress || 50, data.message || 'Processing video...');
                setTimeout(() => this.pollVideoProcessing(), 2000);
            }

        } catch (error) {
            console.error('Error polling video processing:', error);
            this.showError('Failed to get processing status');
            this.resetToAnalysisResults();
        }
    }

    displayVideoProcessingResults(processing) {
        // Hide processing status
        this.elements.videoUploadStatus.style.display = 'none';

        // Show results
        this.elements.videoAnalysisResults.style.display = 'block';
        this.elements.analysisSummary.innerHTML = `
            <h4>🎬 Video Processing Complete</h4>

            <div class="processing-results">
                <div class="result-section">
                    <h5>📹 Auto-Trim Results</h5>
                    <div class="analysis-item">
                        <span class="analysis-label">Original Duration:</span>
                        <span class="analysis-value">${this.formatDuration(processing.original_duration)}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Trimmed Duration:</span>
                        <span class="analysis-value">${this.formatDuration(processing.trimmed_duration)}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Time Saved:</span>
                        <span class="analysis-value">${this.formatDuration(processing.time_saved)} removed</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Silence Periods Removed:</span>
                        <span class="analysis-value">${processing.processing_metadata.silence_periods_removed}</span>
                    </div>
                </div>

                <div class="result-section">
                    <h5>📝 Narration Script</h5>
                    <div class="analysis-item">
                        <span class="analysis-label">Script Segments:</span>
                        <span class="analysis-value">${processing.processing_metadata.script_segments}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Estimated Duration:</span>
                        <span class="analysis-value">${this.formatDuration(processing.narration_script.script_metadata.estimated_narration_duration)}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Style:</span>
                        <span class="analysis-value">${processing.narration_script.script_notes.tone}</span>
                    </div>
                </div>

                <div class="script-preview">
                    <h5>Script Preview</h5>
                    <div class="script-segments">
                        ${processing.narration_script.narration_segments.slice(0, 2).map(segment => `
                            <div class="script-segment-preview">
                                <strong>${segment.title}:</strong>
                                <p>${segment.narration_text}</p>
                            </div>
                        `).join('')}
                        ${processing.narration_script.narration_segments.length > 2 ? '<p><em>...and more segments</em></p>' : ''}
                    </div>
                </div>
            </div>
        `;

        // Update button for next steps
        this.elements.continueToProcessingBtn.style.display = 'block';
        this.elements.continueToProcessingBtn.disabled = false;
        this.elements.continueToProcessingBtn.textContent = 'Generate Voiceover & Export MP4';
        this.elements.continueToProcessingBtn.onclick = () => {
            this.startFinalSteps();
        };
    }

    formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    resetToAnalysisResults() {
        // Reset UI state
        this.elements.videoUploadStatus.style.display = 'none';
        this.elements.videoAnalysisResults.style.display = 'block';
        this.elements.continueToProcessingBtn.disabled = false;
        this.elements.continueToProcessingBtn.textContent = 'Continue to Content Extraction';
    }

    // ============================================================================
    // PHASE 3 STEPS 5-6: VOICEOVER AND FINAL EXPORT
    // ============================================================================

    async startFinalSteps() {
        if (!this.currentProcessingJobId) {
            this.showError('No processing job available for finalization');
            return;
        }

        try {
            // Get voice style preference
            const voiceOptions = ['professional', 'conversational', 'authoritative', 'friendly', 'dramatic'];
            const voiceStyle = prompt(
                'Choose voice style:\n' + voiceOptions.map((v, i) => `${i + 1}. ${v}`).join('\n'),
                'professional'
            ) || 'professional';

            // Validate voice style
            const selectedVoice = voiceOptions.includes(voiceStyle) ? voiceStyle : 'professional';

            // Update button state
            this.elements.continueToProcessingBtn.disabled = true;
            this.elements.continueToProcessingBtn.textContent = 'Generating voiceover...';

            // Start Steps 5-6: Voiceover and export
            const response = await fetch('/finalize-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    processing_job_id: this.currentProcessingJobId,
                    voice_style: selectedVoice
                })
            });

            if (!response.ok) {
                throw new Error(`Finalization failed: ${response.status}`);
            }

            const result = await response.json();
            this.currentFinalizationJobId = result.job_id;

            // Show finalization status and poll for results
            this.showFinalizationStatus();
            this.pollVideoFinalization();

        } catch (error) {
            console.error('Error starting finalization:', error);
            this.showError('Failed to start video finalization: ' + error.message);
            this.elements.continueToProcessingBtn.disabled = false;
            this.elements.continueToProcessingBtn.textContent = 'Generate Voiceover & Export MP4';
        }
    }

    showFinalizationStatus() {
        // Hide processing results, show status
        this.elements.videoAnalysisResults.style.display = 'none';
        this.elements.videoUploadStatus.style.display = 'block';
        this.updateVideoProgress(0, 'Starting voiceover generation...');
    }

    async pollVideoFinalization() {
        if (!this.currentFinalizationJobId) return;

        try {
            const response = await fetch(`/video-finalization/${this.currentFinalizationJobId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                this.displayFinalizationResults(data.finalization, data.download_url);
            } else if (data.status === 'failed') {
                this.showError('Video finalization failed: ' + data.message);
                this.resetToProcessingResults();
            } else {
                // Update progress and continue polling
                this.updateVideoProgress(data.progress || 50, data.message || 'Finalizing video...');
                setTimeout(() => this.pollVideoFinalization(), 2000);
            }

        } catch (error) {
            console.error('Error polling finalization:', error);
            this.showError('Failed to get finalization status');
            this.resetToProcessingResults();
        }
    }

    displayFinalizationResults(finalization, downloadUrl) {
        // Hide finalization status
        this.elements.videoUploadStatus.style.display = 'none';

        // Show final results
        this.elements.videoAnalysisResults.style.display = 'block';
        this.elements.analysisSummary.innerHTML = `
            <h4>🎉 Phase 3 Complete!</h4>

            <div class="finalization-results">
                <div class="result-section success-section">
                    <h5>✅ Final Video Ready</h5>
                    <div class="analysis-item">
                        <span class="analysis-label">Final Duration:</span>
                        <span class="analysis-value">${this.formatDuration(finalization.final_duration)}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Resolution:</span>
                        <span class="analysis-value">${finalization.final_resolution}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">File Size:</span>
                        <span class="analysis-value">${this.formatFileSize(finalization.final_file_size)}</span>
                    </div>
                </div>

                <div class="result-section">
                    <h5>🎵 Voiceover Details</h5>
                    <div class="analysis-item">
                        <span class="analysis-label">Voice Style:</span>
                        <span class="analysis-value">${finalization.voiceover_metadata.voice_style}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Voice Segments:</span>
                        <span class="analysis-value">${finalization.voiceover_metadata.total_segments}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Total Voice Duration:</span>
                        <span class="analysis-value">${this.formatDuration(finalization.voiceover_metadata.total_voice_duration)}</span>
                    </div>
                </div>

                <div class="result-section">
                    <h5>📊 Complete Pipeline Summary</h5>
                    <div class="analysis-item">
                        <span class="analysis-label">Original Duration:</span>
                        <span class="analysis-value">${this.formatDuration(finalization.complete_pipeline.original_duration)}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">After Auto-Trim:</span>
                        <span class="analysis-value">${this.formatDuration(finalization.complete_pipeline.trimmed_duration)}</span>
                    </div>
                    <div class="analysis-item">
                        <span class="analysis-label">Time Saved:</span>
                        <span class="analysis-value">${this.formatDuration(finalization.complete_pipeline.time_saved)}</span>
                    </div>
                </div>

                <div class="download-section">
                    <button class="download-btn" onclick="window.location.href='${downloadUrl}'">
                        📥 Download Final Video
                    </button>
                </div>
            </div>
        `;

        // Hide continue button
        this.elements.continueToProcessingBtn.style.display = 'none';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    resetToProcessingResults() {
        // Reset UI to processing results state
        this.elements.videoUploadStatus.style.display = 'none';
        this.elements.videoAnalysisResults.style.display = 'block';
        this.elements.continueToProcessingBtn.disabled = false;
        this.elements.continueToProcessingBtn.textContent = 'Generate Voiceover & Export MP4';
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

        // Get selected video mode
        const selectedMode = Array.from(this.elements.videoModeInputs).find(input => input.checked)?.value || 'standard';

        const requestData = {
            transcript: transcript,
            title: this.elements.titleInput.value || 'GNG Presentation',
            voice_style: this.elements.voiceStyle.value,
            video_mode: selectedMode
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

            // Show summarization indicator if needed
            if (status.summarization && !this.elements.statusMessage.classList.contains('summarization-mode')) {
                this.elements.statusMessage.classList.add('summarization-mode');
            }

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
            this.presentationMetadata = {
                was_summarized: presentationData.was_summarized,
                summary_reason: presentationData.summary_reason
            };

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

        // Update script info with summarization indicator
        let scriptInfo = `
            <span>${this.currentPresentation.segments.length} segments</span>
            <span>${Math.round(this.currentPresentation.total_duration)}s total</span>
        `;

        if (this.presentationMetadata && this.presentationMetadata.was_summarized) {
            scriptInfo += `<span class="summarized-indicator">📝 Key moments extracted</span>`;
        }

        this.elements.scriptInfo.innerHTML = scriptInfo;

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