from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import base64
import mimetypes
import os
import re
import struct
import tempfile
import uuid
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is required. Please set it in your .env file.")

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size
        1,                # AudioFormat
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """Generate speech from text using Gemini TTS API"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Text is required'}), 400
        
        text = data['text']
        voice_name = data.get('voice', 'Enceladus')  # Default voice
        temperature = data.get('temperature', 1.0)
        
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        model = "gemini-2.5-flash-preview-tts"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )

        # Collect all audio chunks
        audio_chunks = []
        mime_type = None
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
                
            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_chunks.append(inline_data.data)
                if mime_type is None:
                    mime_type = inline_data.mime_type
        
        if not audio_chunks:
            return jsonify({'error': 'No audio generated'}), 500
        
        # Combine all audio chunks
        combined_audio = b''.join(audio_chunks)
        
        # Convert to WAV if needed
        file_extension = mimetypes.guess_extension(mime_type)
        if file_extension is None or file_extension != '.wav':
            combined_audio = convert_to_wav(combined_audio, mime_type)
            mime_type = 'audio/wav'
            file_extension = '.wav'
        
        # Return base64 encoded audio for easy frontend handling
        audio_base64 = base64.b64encode(combined_audio).decode('utf-8')
        
        return jsonify({
            'success': True,
            'audio_data': audio_base64,
            'mime_type': mime_type,
            'file_extension': file_extension
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/text-to-speech/file', methods=['POST'])
def text_to_speech_file():
    """Generate speech and return as downloadable file"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Text is required'}), 400
        
        text = data['text']
        voice_name = data.get('voice', 'Enceladus')
        temperature = data.get('temperature', 1.0)
        
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        model = "gemini-2.5-flash-preview-tts"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )

        # Collect all audio chunks
        audio_chunks = []
        mime_type = None
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
                
            if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_chunks.append(inline_data.data)
                if mime_type is None:
                    mime_type = inline_data.mime_type
        
        if not audio_chunks:
            return jsonify({'error': 'No audio generated'}), 500
        
        # Combine all audio chunks
        combined_audio = b''.join(audio_chunks)
        
        # Convert to WAV if needed
        file_extension = mimetypes.guess_extension(mime_type)
        if file_extension is None or file_extension != '.wav':
            combined_audio = convert_to_wav(combined_audio, mime_type)
            mime_type = 'audio/wav'
            file_extension = '.wav'
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_file.write(combined_audio)
        temp_file.close()
        
        filename = f"speech_{uuid.uuid4().hex[:8]}{file_extension}"
        
        return send_file(
            temp_file.name,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voices', methods=['GET'])
def get_available_voices():
    """Return list of available voices"""
    voices = [
        'Enceladus',
        'Puck',
        'Charon',
        'Kore',
        'Fenrir',
        'Aoede'
    ]
    return jsonify({'voices': voices})

@app.route('/')
def index():
    """Serve the main page"""
    try:
        return send_from_directory('static', 'index.html')
    except:
        return jsonify({
            'message': 'Gemini TTS API is running!',
            'endpoints': {
                'POST /api/text-to-speech': 'Generate speech from text (returns base64)',
                'POST /api/text-to-speech/file': 'Generate speech from text (returns file)',
                'GET /api/voices': 'Get available voices',
                'GET /health': 'Health check'
            },
            'frontend': 'Place index.html in static/ directory to access web interface'
        })

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'api_key_configured': bool(GEMINI_API_KEY),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    print("🚀 Gemini TTS API Server Starting...")
    print(f"📍 Server URL: http://localhost:{port}")
    print(f"🌐 Frontend URL: http://localhost:{port}/static/index.html")
    print(f"📋 API Docs: http://localhost:{port}/health")
    print(f"🔧 Debug Mode: {debug}")
    print(f"🔑 API Key Configured: {'✅' if GEMINI_API_KEY else '❌'}")
    print("-" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=debug)