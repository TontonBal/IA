import logging
import uuid
from sanic import Blueprint, response
from sanic.request import Request
from socketio import AsyncServer
from typing import Optional, Text, Any, List, Dict, Iterable

import wave
# import pyaudio
from rasa.core.channels.channel import InputChannel
from rasa.core.channels.channel import UserMessage, OutputChannel

# import deepspeech
# from deepspeech import Model
import scipy.io.wavfile as wav

import os
import sys
import io

import time
import numpy as np
from collections import OrderedDict
import urllib

from google.cloud import texttospeech
from google.cloud import speech

logger = logging.getLogger(__name__)

# def load_deepspeech_model():
#     N_FEATURES = 25
#     N_CONTEXT = 9
#     BEAM_WIDTH = 500
#     LM_ALPHA = 0.75
#     LM_BETA = 1.85
#
#     ds = Model('deepspeech-0.5.1-models/output_graph.pbmm', N_FEATURES, N_CONTEXT,
#                'deepspeech-0.5.1-models/alphabet.txt', BEAM_WIDTH)
#     return ds
#
#
# def load_tts_model():
#     MODEL_PATH = './tts_model/best_model.pth.tar'
#     CONFIG_PATH = './tts_model/config.json'
#     CONFIG = load_config(CONFIG_PATH)
#     use_cuda = False
#
#     num_chars = len(phonemes) if CONFIG.use_phonemes else len(symbols)
#     model = Tacotron(num_chars, CONFIG.embedding_size, CONFIG.audio['num_freq'], CONFIG.audio['num_mels'], CONFIG.r,
#                      attn_windowing=False)
#
#     num_chars = len(phonemes) if CONFIG.use_phonemes else len(symbols)
#     model = Tacotron(num_chars, CONFIG.embedding_size, CONFIG.audio['num_freq'], CONFIG.audio['num_mels'], CONFIG.r,
#                      attn_windowing=False)
#
#     # load the audio processor
#     # CONFIG.audio["power"] = 1.3
#     CONFIG.audio["preemphasis"] = 0.97
#     ap = AudioProcessor(**CONFIG.audio)
#
#     # load model state
#     if use_cuda:
#         cp = torch.load(MODEL_PATH)
#     else:
#         cp = torch.load(MODEL_PATH, map_location=lambda storage, loc: storage)
#
#     # load the model
#     model.load_state_dict(cp['model'])
#     if use_cuda:
#         model.cuda()
#
#     # model.eval()
#     model.decoder.max_decoder_steps = 1000
#     return model, ap, MODEL_PATH, CONFIG, use_cuda
#
#
# ds = load_deepspeech_model()
# model, ap, MODEL_PATH, CONFIG, use_cuda = load_tts_model()
tts_client = speech.SpeechClient()
# p = pyaudio.PyAudio()


class SocketBlueprint(Blueprint):
    def __init__(self, sio: AsyncServer, socketio_path, *args, **kwargs):
        self.sio = sio
        self.socketio_path = socketio_path
        super(SocketBlueprint, self).__init__(*args, **kwargs)

    def register(self, app, options):
        self.sio.attach(app, self.socketio_path)
        super(SocketBlueprint, self).register(app, options)


class SocketIOOutput(OutputChannel):

    @classmethod
    def name(cls) -> Text:
        return "socketio"

    def __init__(self, sio, sid, bot_message_evt, message):
        self.sio = sio
        self.sid = sid
        self.bot_message_evt = bot_message_evt
        self.message = message
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="fr-FR", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        # Select the type of audio file you want returned
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

    # def tts(self, model, text, CONFIG, use_cuda, ap, OUT_FILE):
    #     import numpy as np
    #     waveform, alignment, spectrogram, mel_spectrogram, stop_tokens = synthesis(model, text, CONFIG, use_cuda, ap)
    #     ap.save_wav(waveform, OUT_FILE)
    #     wav_norm = waveform * (32767 / max(0.01, np.max(np.abs(waveform))))
    #     return alignment, spectrogram, stop_tokens, wav_norm

    def tts_predict(self, sentence, OUT_FILE):
        print(sentence)
        wav_norm = self.client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=sentence), voice=self.voice, audio_config=self.audio_config
        )
        with open(OUT_FILE, "wb") as out:
            # Write the response to the output file.
            out.write(wav_norm.audio_content)
        # out.close()
        # wf = wave.open(OUT_FILE, 'rb')
        # data = wf.readframes(1024)
        # stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
        #                 channels=wf.getnchannels(),
        #                 rate=wf.getframerate(),
        #                 output=True)
        # while data != '':
        #     stream.write(data)
        #     data = wf.readframes(1024)
        #
        # stream.close()
        # p.terminate()

        return wav_norm.audio_content

    async def _send_audio_message(self, socket_id, response, **kwargs: Any):
        # type: (Text, Any) -> None
        """Sends a message to the recipient using the bot event."""

        ts = time.time()
        OUT_FILE = str(ts) + '.wav'
        link = "http://localhost:8888/" + OUT_FILE

        wav_norm = self.tts_predict(response['text'], OUT_FILE)

        await self.sio.emit(self.bot_message_evt, {'text': response['text'], "link": link}, room=socket_id)

    async def send_text_message(self, recipient_id: Text, message: Text, **kwargs: Any) -> None:
        """Send a message through this channel."""

        await self._send_audio_message(self.sid, {"text": message})


class SocketIOInput(InputChannel):
    """A socket.io input channel."""

    @classmethod
    def name(cls) -> Text:
        return "socketio"

    @classmethod
    def from_credentials(cls, credentials):
        credentials = credentials or {}
        return cls(credentials.get("user_message_evt", "user_uttered"),
                   credentials.get("bot_message_evt", "bot_uttered"),
                   credentials.get("namespace"),
                   credentials.get("session_persistence", False),
                   credentials.get("socketio_path", "/socket.io"),
                   )

    def __init__(self,
                 user_message_evt: Text = "user_uttered",
                 bot_message_evt: Text = "bot_uttered",
                 namespace: Optional[Text] = None,
                 session_persistence: bool = False,
                 socketio_path: Optional[Text] = '/socket.io'
                 ):
        self.bot_message_evt = bot_message_evt
        self.session_persistence = session_persistence
        self.user_message_evt = user_message_evt
        self.namespace = namespace
        self.socketio_path = socketio_path

    def blueprint(self, on_new_message):
        # sio = AsyncServer(async_mode="sanic")
        sio = AsyncServer(async_mode="sanic", cors_allowed_origins='*')
        socketio_webhook = SocketBlueprint(
            sio, self.socketio_path, "socketio_webhook", __name__
        )

        @socketio_webhook.route("/", methods=['GET'])
        async def health(request):
            return response.json({"status": "ok"})

        @sio.on('connect', namespace=self.namespace)
        async def connect(sid, environ):
            logger.debug("User {} connected to socketIO endpoint.".format(sid))
            print('Connected!')

        @sio.on('disconnect', namespace=self.namespace)
        async def disconnect(sid):
            logger.debug("User {} disconnected from socketIO endpoint."
                         "".format(sid))

        @sio.on('session_request', namespace=self.namespace)
        async def session_request(sid, data):
            print('This is sessioin request')

            if data is None:
                data = {}
            if 'session_id' not in data or data['session_id'] is None:
                data['session_id'] = uuid.uuid4().hex
            await sio.emit("session_confirm", data['session_id'], room=sid)
            logger.debug("User {} connected to socketIO endpoint."
                         "".format(sid))

        @sio.on('user_uttered', namespace=self.namespace)
        async def handle_message(sid, data):

            output_channel = SocketIOOutput(sio, sid, self.bot_message_evt, data['message'])
            if data['message'] == "/get_started":
                message = data['message']
            else:
                ##receive audio
                received_file = 'output_' + sid + '.wav'

                urllib.request.urlretrieve(data['message'], received_file)
                path = os.path.dirname(__file__)
                with wave.open("output_{0}.wav".format(sid)) as fd:
                    frames = fd.readframes(1000000)

                fs, audio = wav.read("output_{0}.wav".format(sid))
                print(type(audio))
                audio = speech.RecognitionAudio(content=frames)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code="fr-FR",
                )
                audio_response = tts_client.recognize(config=config, audio=audio)
                message = ""
                for result in audio_response.results:
                    message += u"Transcript: {}".format(result.alternatives[0].transcript)
            		
	
                await sio.emit(self.user_message_evt, {"text": message}, room=sid)
            print(message)
            message_rasa = UserMessage(message, output_channel, sid,
                                       input_channel=self.name())
            await on_new_message(message_rasa)

        return socketio_webhook
