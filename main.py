import speech_recognition
import pyttsx3
import noisereduce as nr
import sounddevice as sd
import numpy as np
from pedalboard.io import AudioFile
from pedalboard import *
from scipy.io.wavfile import write

# Initialize recognizer and text-to-speech engine
recognizer = speech_recognition.Recognizer()
engine = pyttsx3.init()

# Sampling rate for the audio
sr = 44100

# Noise reduction and audio enhancement function
def enhance_audio(input_audio, sample_rate):
    # Perform noise reduction using noisereduce library
    reduced_noise = nr.reduce_noise(y=input_audio, sr=sample_rate, stationary=True, prop_decrease=0.75)

    # Use Pedalboard for further audio effects
    board = Pedalboard([
        NoiseGate(threshold_db=-30, ratio=1.5, release_ms=250),
        Compressor(threshold_db=-16, ratio=2.5),
        LowShelfFilter(cutoff_frequency_hz=400, gain_db=10, q=1),
        Gain(gain_db=10)
    ])

    # Apply the effects to the noise-reduced audio
    effected = board(reduced_noise, sample_rate)
    return effected

# Record audio using sounddevice for a few seconds
def record_audio(duration=5, fs=sr):
    print("Recording audio...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()  # Wait until recording is finished
    print("Recording complete.")
    return recording[:, 0]  # Return a single channel of audio

# Main loop for speech recognition with noise reduction
while True:
    try:
        print("Listening...")

        # Record audio for 5 seconds
        audio_data = record_audio(duration=5, fs=sr)

        # Save recorded audio to a temporary file
        write("input_audio.wav", sr, audio_data)

        # Enhance the audio
        with AudioFile("input_audio.wav").resampled_to(sr) as f:
            recorded_audio = f.read(f.frames)

        # Apply noise reduction and audio effects
        enhanced_audio = enhance_audio(recorded_audio, sr)


        # Save the enhanced audio as a temporary file
        with AudioFile("enhanced_audio.wav", 'w', sr, enhanced_audio.shape[0]) as f:
            f.write(enhanced_audio)

        # Use SpeechRecognition library to convert enhanced audio to text
        with speech_recognition.AudioFile("enhanced_audio.wav") as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.record(source)

        # Recognize speech using Google Web Speech API
        text = recognizer.recognize_google(audio)
        print(f"Recognized Text: {text}")

        # Exit loop if the recognized text is 'exit'
        if text.lower() == 'exit':
            print("Exiting...")
            break

    except speech_recognition.RequestError:
        print('Network error')
    except speech_recognition.UnknownValueError:
        print('Unable to recognize speech')
    except speech_recognition.WaitTimeoutError:
        print('Timeout error')
    except KeyboardInterrupt:
        break
