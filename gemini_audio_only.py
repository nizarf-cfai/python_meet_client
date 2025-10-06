#!/usr/bin/env python3
"""
Gemini Live API - Audio Only
Simplified version that only handles audio input/output with Gemini Live API

Setup:
pip install google-genai pyaudio

Before running, set your GOOGLE_API_KEY environment variable or update the api_key in the script.

Usage:
python gemini_audio_only.py

Important: Use headphones to prevent echo/feedback loops.
"""

import asyncio
import os
import sys
import traceback
import pyaudio

from google import genai

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Gemini configuration
MODEL = "models/gemini-2.0-flash-live-001"
CONFIG = {"response_modalities": ["AUDIO"]}

# Initialize PyAudio
pya = pyaudio.PyAudio()

class AudioOnlyGemini:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None
        
        # Initialize Gemini client
        # You can either set GOOGLE_API_KEY environment variable or update this line
        api_key = os.getenv("GOOGLE_API_KEY", "")
        self.client = genai.Client(http_options={"api_version": "v1beta"}, api_key=api_key)

    async def listen_audio(self):
        """Listen to microphone and send audio to Gemini"""
        print("🎤 Starting microphone...")
        
        # Get default microphone
        mic_info = pya.get_default_input_device_info()
        print(f"🎤 Using microphone: {mic_info['name']}")
        
        # Open audio stream
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        
        print("🎤 Microphone ready - start speaking!")
        
        # Read audio chunks and send to Gemini
        while True:
            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
            except Exception as e:
                print(f"❌ Error reading audio: {e}")
                break

    async def receive_audio(self):
        """Receive audio responses from Gemini and play them"""
        print("🔊 Starting audio output...")
        
        while True:
            try:
                turn = self.session.receive()
                async for response in turn:
                    # Handle audio data
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        print(f"🔊 Gemini audio response received: {len(data)} bytes")
                        continue
                    
                    # Handle text responses (print them)
                    if text := response.text:
                        print(f"🤖 Gemini: {text}")
                
                # Clear audio queue on turn completion to prevent overlap
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
                    
            except Exception as e:
                print(f"❌ Error receiving audio: {e}")
                break

    async def play_audio(self):
        """Play audio responses from Gemini"""
        print("🔊 Setting up audio output...")
        
        # Get default speaker
        speaker_info = pya.get_default_output_device_info()
        print(f"🔊 Using speaker: {speaker_info['name']}")
        
        # Open output stream
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            output_device_index=speaker_info["index"],
        )
        
        print("🔊 Audio output ready!")
        
        # Play audio from queue
        while True:
            try:
                bytestream = await self.audio_in_queue.get()
                await asyncio.to_thread(stream.write, bytestream)
            except Exception as e:
                print(f"❌ Error playing audio: {e}")
                break

    async def send_audio_to_gemini(self):
        """Send audio data to Gemini"""
        while True:
            try:
                audio_data = await self.out_queue.get()
                await self.session.send(input=audio_data)
            except Exception as e:
                print(f"❌ Error sending audio: {e}")
                break

    async def run(self):
        """Main function to run the audio-only Gemini session"""
        print("🚀 Starting Gemini Live API - Audio Only")
        print("=" * 50)
        print("📝 Instructions:")
        print("• Speak into your microphone to interact with Gemini")
        print("• Gemini will respond with audio")
        print("• Press Ctrl+C to exit")
        print("• Make sure to use headphones to prevent echo!")
        print("=" * 50)
        
        try:
            async with (
                self.client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                
                # Create queues
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                
                print("🔗 Connected to Gemini Live API")
                
                # Start all tasks
                tg.create_task(self.send_audio_to_gemini())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                
                # Keep running until interrupted
                try:
                    await asyncio.Event().wait()
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down...")
                    raise asyncio.CancelledError("User requested exit")
                
        except asyncio.CancelledError:
            print("✅ Session ended")
        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
        finally:
            # Clean up audio stream
            if self.audio_stream:
                self.audio_stream.close()
            print("🧹 Cleanup completed")

def main():
    """Main entry point"""
    print("🎵 Gemini Live API - Audio Only")
    print("=" * 30)
    
    # Check if API key is available
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key and "AIzaSyAKpwKuinlUKSSJhYdZKHLXuK5-TEgB7Ng" not in "AIzaSyAKpwKuinlUKSSJhYdZKHLXuK5-TEgB7Ng":
        print("⚠️  Warning: No GOOGLE_API_KEY environment variable found")
        print("   Using hardcoded API key (not recommended for production)")
    
    # Create and run the audio session
    audio_session = AudioOnlyGemini()
    asyncio.run(audio_session.run())

if __name__ == "__main__":
    main()
