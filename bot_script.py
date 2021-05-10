## Run this command in terminal  before executing this program
## rasa run -m models --endpoints endpoints.yml --port 5002 --credentials credentials.yml
## and also run this in seperate terminal
## rasa run actions

import requests  # import the library
import subprocess
from google.cloud import texttospeech
from google.cloud import speech
from micStream import *

# sender = input("What is your name?\n")

tts_client = texttospeech.TextToSpeechClient()
# Build the voice request, select the language code ("en-US") and the ssml
# voice gender ("neutral")
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
)

# Select the type of audio file you want returned
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

stt_client = speech.SpeechClient()
config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,
    language_code="en-US",
)
streaming_config = speech.StreamingRecognitionConfig(
    config=config, single_utterance=True
)

bot_message = ""
message = ""

r = requests.post('http://localhost:5002/webhooks/rest/webhook', json={"message": "Hello"})

print("Bot says, ", end=' ')
for i in r.json():
    bot_message = i['text']
    print(f"{bot_message}")

synthesis_input = texttospeech.SynthesisInput(text=bot_message)
response = tts_client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)

with open("welcome.mp3", "wb") as out:
    # Write the response to the output file.
    out.write(response.audio_content)

# Playing the converted file
subprocess.call(['mpg321', "welcome.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

while bot_message != "Bye" or bot_message != 'thanks':

    with MicrophoneStream(RATE, CHUNK) as stream:  # mention source it will be either Microphone or audio files.
        print("A vous de parler")
        audio_generator = stream.generator()
        audio_requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        responses = stt_client.streaming_recognize(streaming_config, audio_requests)
        message = ""

        for response in responses:
            # On s'assure que le stream en entrée ne soit pas vide
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            transcript = result.alternatives[0].transcript
            message += transcript
            # Lorsque l'on a un message, comme on est en mode sinlge_utterance,
            # on peut fermer le stream
            stream.__exit__(0, 0, 0)
            # break
        print(message)

    r = requests.post('http://localhost:5002/webhooks/rest/webhook', json={"message": message})

    print("Lisa dit, ", end=' ')
    for i in r.json():
        bot_message = i['text']
        print(f"{bot_message}")

    synthesis_input = texttospeech.SynthesisInput(text=bot_message)
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open("welcome.mp3", "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)
    # Playing the converted file
    subprocess.call(['mpg321', "welcome.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
