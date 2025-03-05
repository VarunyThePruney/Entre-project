import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
from google.cloud import speech
from pydub import AudioSegment

# Load YAML config for auth
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )

name, auth_status, username = authenticator.login("Login", "main")




# Set the path to your Google Cloud service account key
# credentials_path = "C:\Users\srira\OneDrive\Documents\codemedix-14732eb7cdc9.json"
credentials_path = r"/Users/varunsai/Documents/codemedix-14732eb7cdc9.json"

# Initialize Google Cloud Speech client using the credentials directly
client = speech.SpeechClient.from_service_account_file(credentials_path)

# Function to convert mp3 to flac (since Google Speech API works better with FLAC/WAV)
def convert_mp3_to_flac(mp3_file_path):
    audio = AudioSegment.from_mp3(mp3_file_path)
    flac_file_path = mp3_file_path.replace(".mp3", ".flac") #format for transcribing mp3 audio to text
    audio.export(flac_file_path, format="flac")
    return flac_file_path

# Function to split the audio file into chunks
def split_audio(input_file, chunk_duration_ms=60000):
    """Split the input audio file into smaller chunks."""
    audio = AudioSegment.from_file(input_file)
    chunks = []
    start_time = 0
    while start_time < len(audio):
        end_time = min(start_time + chunk_duration_ms, len(audio))
        chunk = audio[start_time:end_time]
        chunk_file = f"chunk_{start_time}.flac"
        chunk.export(chunk_file, format="flac")
        chunks.append(chunk_file)
        start_time = end_time
    return chunks

# Function to transcribe audio chunk directly to Google Cloud Speech-to-Text
def transcribe_audio_chunk(chunk_file):
    """Transcribe audio chunk directly to Google Cloud Speech-to-Text."""
    with open(chunk_file, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    medical_terms = [
        "hypertension", "diabetes", "stroke", "glucose", "insulin",
        "cardiovascular", "neurology", "epilepsy", "seizure", "radiology",
        "medication", "prescription", "surgical", "oncology", "chemotherapy"
    ]
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=48000,  # Adjust based on your audio sample rate
        language_code="en-US",  # You can adjust for different languages
        model="medical",  # Use the medical model
        speech_contexts=[speech.SpeechContext(
            phrases=medical_terms)
        ]
    )

    # Send the audio data to Google Cloud Speech API for recognition
    response = client.recognize(config=config, audio=audio)

    # Extract and return the transcript
    transcripts = []
    for result in response.results:
        transcripts.append(result.alternatives[0].transcript)

    return "\n".join(transcripts)

# Streamlit interface
def main():
    if auth_status is False:
        st.error("Authentication Failed")

    if auth_status is None:
        st.warning("Please login first")

    if auth_status:
        st.sidebar.success(f"Welcome, {name}!")
        authenticator.logout("Logout", "sidebar")




        st.title("Speech-to-Text Medical Dictation")

        # File uploader widget
        audio_file = st.file_uploader("Upload your MP3 file", type=["mp3"])

        if audio_file is not None:
            # Save the uploaded file to disk
            with open("temp_audio.mp3", "wb") as f:
                f.write(audio_file.read())

            st.success("File uploaded successfully!")

            # Convert MP3 to FLAC
            st.write("Converting MP3 to FLAC...")
            flac_file = convert_mp3_to_flac("temp_audio.mp3")

            # Split the audio file into chunks
            st.write("Splitting the audio file into chunks...")
            chunks = split_audio(flac_file)

            st.write(f"Audio file split into {len(chunks)} chunks.")

            full_transcript = ""

            # Process each chunk and transcribe
            for chunk_file in chunks:
                st.write(f"Processing chunk: {chunk_file}...")
                transcript = transcribe_audio_chunk(chunk_file)
                full_transcript += transcript + "\n\n"
                # st.write(f"full_transcript: {full_transcript}..")
                # Clean up the chunk file after processing
                os.remove(chunk_file)

            # Show the full transcription
            st.subheader("Full Transcript:")
            st.text_area("Transcription", full_transcript, height=600)

            # Clean up
            os.remove("temp_audio.mp3")
            os.remove(flac_file)



if __name__ == "__main__":
    main()
