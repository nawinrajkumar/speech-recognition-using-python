import speech_recognition
import pyttsx3
import noisereduce as nr
import sounddevice as sd
import numpy as np
from pedalboard.io import AudioFile
from pedalboard import *
from scipy.io.wavfile import write
import argparse
import os

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

# Process audio from a file
def process_audio_file(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")
    
    print(f"Processing audio file: {file_path}")
    with AudioFile(file_path).resampled_to(sr) as f:
        return f.read(f.frames)

# Main function to handle input and recognition
def main(input_source, duration=5):
    try:
        if input_source == '0':
            # Record audio from microphone
            audio_data = record_audio(duration=duration, fs=sr)
            write("input_audio.wav", sr, audio_data)
            recorded_audio = process_audio_file("input_audio.wav")
        else:
            # Process audio from the provided file path
            recorded_audio = process_audio_file(input_source)

        # Apply noise reduction and audio effects
        enhanced_audio = enhance_audio(recorded_audio, sr)

        # Save the enhanced audio to a temporary file
        enhanced_file_path = "enhanced_audio.wav"
        with AudioFile(enhanced_file_path, 'w', sr, enhanced_audio.shape[0]) as f:
            f.write(enhanced_audio)

        # Use SpeechRecognition library to convert enhanced audio to text
        with speech_recognition.AudioFile(enhanced_file_path) as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.record(source)

        # Recognize speech using Google Web Speech API
        text = recognizer.recognize_google(audio)
        print(f"Recognized Text: {text}")

        return text

    except speech_recognition.RequestError:
        print('Network error')
    except speech_recognition.UnknownValueError:
        print('Unable to recognize speech')
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Speech Recognition using Python.')
    parser.add_argument(
        'input_source', 
        type=str, 
        help="Specify '0' to use the microphone or provide a file path to an audio file."
    )
    parser.add_argument(
        '--duration', 
        type=int, 
        default=5, 
        help='Duration of the audio recording in seconds (only applicable if using microphone).'
    )

    args = parser.parse_args()

    # Call the main function with input source and duration
    main(input_source=args.input_source, duration=args.duration)
