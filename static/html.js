let mediaRecorder;
let audioChunks = [];

document.addEventListener('DOMContentLoaded', function () {
    const notesTextarea = document.getElementById('notes-textarea');
    const flashcardOption = document.getElementById('flashcard-option');
    const quizOption = document.getElementById('quiz-option');
    const notesOption = document.getElementById('notes-option');
    const storyOption = document.getElementById('story-option');
    const imageOption = document.getElementById('image-option');
    const generateBtn = document.getElementById('generate-btn');
    const microphoneBtn = document.getElementById('microphone-btn');
    const recordingStatus = document.getElementById('recording-status');

    // Add event listeners to enable the button based on input.
    notesTextarea.addEventListener('input', enableGenerateButton);
    flashcardOption.addEventListener('change', enableGenerateButton);
    quizOption.addEventListener('change', enableGenerateButton);
    notesOption.addEventListener('change', enableGenerateButton);
    storyOption.addEventListener('change', enableGenerateButton);
    imageOption.addEventListener('change', enableGenerateButton);
    microphoneBtn.addEventListener('click', toggleRecording);

    function enableGenerateButton() {
        const notes = notesTextarea.value.trim();
        const isAnyOptionSelected = flashcardOption.checked || quizOption.checked || notesOption.checked || storyOption.checked || imageOption.checked;
        generateBtn.disabled = !(notes && isAnyOptionSelected);
    }

    function toggleRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            microphoneBtn.innerHTML = '<i class="fas fa-microphone"></i> Record';
            recordingStatus.textContent = 'Processing...';
        } else {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.start();

                    microphoneBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
                    recordingStatus.textContent = 'Recording...';

                    mediaRecorder.addEventListener('dataavailable', event => {
                        audioChunks.push(event.data);
                    });

                    mediaRecorder.addEventListener('stop', () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        sendAudioToServer(audioBlob);
                        audioChunks = [];
                    });
                })
                .catch(error => {
                    console.error('Error accessing microphone:', error);
                    recordingStatus.textContent = 'Error: Unable to access microphone';
                });
        }
    }

    function sendAudioToServer(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        fetch('/transcribe-audio', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            notesTextarea.value = data.transcription;
            recordingStatus.textContent = 'Transcription complete';
            enableGenerateButton();
        })
        .catch(error => {
            console.error('Error:', error);
            recordingStatus.textContent = 'Error: Unable to transcribe audio';
        });
    }

    generateBtn.addEventListener('click', () => {
        const notes = notesTextarea.value.trim();
        const selectedTypes = [];

        if (flashcardOption.checked) selectedTypes.push('flashcards');
        if (quizOption.checked) selectedTypes.push('quiz');
        if (notesOption.checked) selectedTypes.push('notes');
        if (storyOption.checked) selectedTypes.push('story');
        if (imageOption.checked) selectedTypes.push('images');

        fetch('/generate-content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                article: notes,
                types: selectedTypes
            })
        })
        .then(response => response.json())
        .then(data => {
            localStorage.clear();
            if (data.flashcard) {
                localStorage.setItem('flashcardQuestion', data.flashcard.question);
                localStorage.setItem('flashcardAnswer', data.flashcard.answer);
            }
            if (data.quiz) {
                localStorage.setItem('quizQuestion', data.quiz.question);
                localStorage.setItem('quizChoices', JSON.stringify(data.quiz.choices));
                localStorage.setItem('quizCorrectAnswer', data.quiz.correct_answer);
            }
            if (data.notes) {
                localStorage.setItem('generatedNotes', data.notes);
            }
            if (data.story) {
                localStorage.setItem('generatedStory', data.story);
            }
            if (data.image) {
                localStorage.setItem('generatedImage', data.image);
            }
            window.location.href = '/output-selection';
        })
        .catch(error => console.error('Error:', error));
    });
});