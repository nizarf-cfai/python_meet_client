

import asyncio
import os
import sys
import traceback
import pyaudio
import json
import datetime
import canvas_ops
from google import genai
from dotenv import load_dotenv
import time
import socket
load_dotenv()

# Set global socket timeout for extended tool execution
socket.setdefaulttimeout(300)  # 5 minutes timeout
# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Gemini configuration
MODEL = "models/gemini-2.0-flash-live-001"
CONFIG = {"response_modalities": ["AUDIO"]}
canvas_items = canvas_ops.get_canvas_item_id()

# System prompt for Gemini
SYSTEM_PROMPT = f"""You are a helpful AI assistant with access to medical system functions. You are shared screen canvas board. All discussion is abou patient Sarah Miller in DILI context. Use all EHR data available for medical context regarding the patient.

Use anchor data point in the canvas item for : 
- Patient Profile 
- Patient Risk Notification

When users request actions, you should use the available functions:
- If they ask about canvas navigation, use navigate_canvas tool.
    User may ask "move to ...", "Navigate to ...", "Go to ...", "Show me ...", "Focus on ..."

- If they ask generate task, use generate_task tool.
    User may ask "Create a task ...", "Make a task ...", "Add a task ...", "I want a task ..."

- If they ask get lab result, use generate_lab_result tool.
    User may ask "Get lab result relevant to DILI...", "Get data for this parameter ..."
    Also use this tool if user ask about lab result

This is canvas items details:
{canvas_items}

For navigate_canvas function:
- Use the objectId from the canvas items above

For generate_task function:
- Create a clear title for the task
- Provide detailed content/description
- Break down into step-by-step items
- Make tasks actionable and specific

For generate_medical_parameter function:
- Use all available data to get the data
- If the data not available, generate realistic data.

Always try to extract parameters from the user's request and call the appropriate function. Use available canvas object id, do not ask user for and id.

Guidelines:
- Be helpful and respond naturally
- Use the available functions when appropriate
- Extract parameters from user requests when possible
- If you need more information, ask the user for it

Additional Context:

Lab Report
Date of Lab: 2024-03-10
Lab Test: CBC (Complete Blood Count)
Result: Hemoglobin: 14.2 g/dL, WBC: 6.1 ×10⁹/L, Platelets: 250 ×10⁹/L
Units: g/dL (hemoglobin), ×10⁹/L (WBC, platelets)
Reference Range:
Hemoglobin: 13.5–17.5 g/dL (male) / 12.0–15.5 g/dL (female)
WBC: 4.0–11.0 ×10⁹/L
Platelets: 150–450 ×10⁹/L
Associated test_id: LABS-MC-001001-20240310-XELMON (overall panel ID)
Lab Test: LFTs (Liver Function Tests)
Result: ALT: 22 U/L, AST: 18 U/L, ALP: 85 U/L, Total Bilirubin: 0.8 mg/dL
Units: U/L (ALT, AST, ALP), mg/dL (Bilirubin)
Reference Range:
ALT: 7–56 U/L
AST: 10–40 U/L
ALP: 44–147 U/L
Total Bilirubin: 0.1–1.2 mg/dL
Associated test_id: LABS-MC-001001-20240310-XELMON (overall panel ID)
Lab Test: Lipids (Lipid Panel)
Result: Total Cholesterol: 180 mg/dL, LDL: 95 mg/dL, HDL: 55 mg/dL, Triglycerides: 120 mg/dL
Units: mg/dL
Reference Range:
Total Cholesterol: <200 mg/dL
LDL: <100 mg/dL
HDL: >40 mg/dL (male), >50 mg/dL (female)
Triglycerides: <150 mg/dL
Associated test_id: LABS-MC-001001-20240310-XELMON (overall panel ID)

Laboratory Information System
Oracle Health EHR - Laboratory Information System
Patient: Mc. Allister, John | DOB: 1962-01-20 | MRN: 987654321
Encounter: ED Visit | Date & Time: 2025-06-21 02:30 PM
Result Status: Final
Collection Date/Time: 2025-06-21 02:15 PM

Total Bilirubin : 12.5 mg/dL,  Reference range : 0.2 - 1.2,  (High)
Direct Bilirubin : 8.9 mg/dL,  Reference range : <0.3, (High)
ALT (SGPT) : 1850 U/L,  Reference range : 7 - 56, (High)
AST (SGOT) : 2100 U/L,  Reference range : 10 - 40, (High)


"""

print(SYSTEM_PROMPT)

FUNCTION_DECLARATIONS = [
    {
        "name": "navigate_canvas",
        "description": "Navigate canvas item",
        "parameters": {
            "type": "object",
            "properties": {
                "objectId": {
                    "type": "string",
                    "description": "Object id to navigate"
                }
            },
            "required": []
        }
    },
    {
        "name": "generate_task",
        "description": "Generate a task with title, content, and step-by-step items",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the task"
                },
                "content": {
                    "type": "string",
                    "description": "Description of the task"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Step by step task items"
                }
            },
            "required": ["title", "content", "items"]
        }
    },
    {
        "name": "generate_lab_result",
        "description": "Generate a lab result with value, unit, status, range, and trend information. If the data not available, generate it.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameter": {
                    "type": "string",
                    "description": "Name of the medical parameter (e.g., Aspartate Aminotransferase) If not provided use the most relevant parameter"
                },
                "value": {
                    "type": "string",
                    "description": "The measured value of the parameter, generate it if not provided"
                },
                "unit": {
                    "type": "string",
                    "description": "Unit of measurement (e.g., U/L, mg/dL, etc.) generate it if not provided"
                },
                "status": {
                    "type": "string",
                    "description": "Status of the parameter (optimal, warning, critical) generate it if not provided"
                },
                "range": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "number",
                            "description": "Minimum normal value generate it if not provided"
                        },
                        "max": {
                            "type": "number",
                            "description": "Maximum normal value generate it if not provided"
                        },
                        "warningMin": {
                            "type": "number",
                            "description": "Minimum warning threshold generate it if not provided"
                        },
                        "warningMax": {
                            "type": "number",
                            "description": "Maximum warning threshold generate it if not provided"
                        }
                    },
                    "required": ["min", "max", "warningMin", "warningMax"],
                    "description": "Normal and warning ranges for the parameter"
                },
                "trend": {
                    "type": "string",
                    "description": "Trend direction (stable, increasing, decreasing, fluctuating) generate it if not provided"
                }
            },
            "required": ["parameter", "value", "unit", "status", "range", "trend"]
        }
    }
]


CONFIG = {
    "response_modalities": ["AUDIO"],
    "system_instruction": SYSTEM_PROMPT,
    "tools": [{"function_declarations": FUNCTION_DECLARATIONS}]
}
# Initialize PyAudio
pya = pyaudio.PyAudio()

class AudioOnlyGeminiCable:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None
        self.output_stream = None
        
        # Initialize Gemini client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY environment variable not set!")
            sys.exit(1)
        
        # Configure client with extended timeout for tool execution
        self.client = genai.Client(
            http_options={
                "api_version": "v1beta",
                "timeout": 300  # 5 minutes timeout for tool execution
            }, 
            api_key=api_key
        )
        print(f"🔧 Gemini client initialized: {hasattr(self.client, 'aio')}")

    async def handle_tool_call(self, tool_call):
        """Handle tool calls from Gemini according to official documentation"""
        try:
            from google.genai import types
            
            print("=" * 60)
            print("🔧 TOOL CALL DETECTED!")
            print("=" * 60)
            
            # Process each function call in the tool call
            function_responses = []
            for fc in tool_call.function_calls:
                function_name = fc.name
                arguments = fc.args
                
                print(f"🔧 Function: {function_name}")
                print(f"📋 Arguments: {json.dumps(arguments, indent=2)}")
                print("-" * 40)
                
                # Create action data for saving
                action_data = {
                    "function_name": function_name,
                    "arguments": arguments,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # Save the function call to file
                await self.save_function_call(arguments)
                print(f"THIS IS JSON EXTRACT\n{arguments}")
                
                # Create function response (simplified for now)
                function_response = types.FunctionResponse(
                    id=fc.id,
                    name=fc.name,
                    response={ "result": "ok" } # simple, hard-coded function response
                )
                function_responses.append(function_response)
            
            # Send tool response back to Gemini
            await self.session.send_tool_response(function_responses=function_responses)
            print("✅ Tool response sent back to Gemini")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error handling tool call: {e}")

    async def save_function_call(self, action_data):
        """Save the function call to a file"""
        if not action_data:
            return
        if 'objectId' in action_data:
            focus_res = await canvas_ops.focus_item(action_data["objectId"])
            print(f"🔍 Focus item result: {focus_res}")
        elif 'parameter' in action_data:
            lab_res = await canvas_ops.create_lab(action_data)
            print(f"🔍 Create lab result: {lab_res}")
            await asyncio.sleep(1)
            labId = lab_res['id']
            focus_res = await canvas_ops.focus_item(labId)
            print(f"🔍 Focus item result: {focus_res}")
        else:
            action_data['area'] = "planning-zone"
            task_res = await canvas_ops.create_todo(action_data)
            print(f"🔍 Create todo result: {task_res}")
            await asyncio.sleep(1)
            boxId = task_res['id']
            focus_res = await canvas_ops.focus_item(boxId)
            print(f"🔍 Focus item result: {focus_res}")
            # Update context with the created task information
            context_update = f"Created Task: {action_data}"
            await self.session.send(input=context_update)
            print(f"📝 Context updated: {context_update}")

            agent_res = await canvas_ops.get_agent_answer(action_data)
            # with open("agent_res.json", "w", encoding="utf-8") as f:
            #     json.dump(agent_res, f, ensure_ascii=False, indent=2)
            # print(f"🔍 Agent result: {agent_res}")
            # print(f"🔍 Agent result type: {type(agent_res)}")
            await asyncio.sleep(2)
            create_agent_res = await canvas_ops.create_result(agent_res)
            print(f"🔍 Create agent result: {create_agent_res}")
            agent_res_id = create_agent_res['id']
            await asyncio.sleep(1)

            focus_res = await canvas_ops.focus_item(agent_res_id)
            print(f"🔍 Focus item result: {focus_res}")
            context_update = f"Created Result: {create_agent_res}"
            await self.session.send(input=context_update)
            print(f"📝 Context updated: {context_update}")
            


        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"function_call_object/gemini_function_call_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(action_data, f, indent=2)
            
            print(f"💾 Function call saved to: {filename}")
            print(f"📄 Content: {json.dumps(action_data, indent=2)}")
            
        except Exception as e:
            print(f"❌ Error saving function call: {e}")


    def find_input_device(self, substr: str) -> int:
        """Find input device by substring"""
        s = substr.lower()
        for i in range(pya.get_device_count()):
            info = pya.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0 and s in info['name'].lower():
                return i
        return None

    def find_output_device(self, substr: str) -> int:
        """Find output device by substring"""
        s = substr.lower()
        for i in range(pya.get_device_count()):
            info = pya.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0 and s in info['name'].lower():
                return i
        return None

    async def listen_audio(self):
        """Listen to CABLE Output (Google Meet audio) and send to Gemini"""
        print("🎤 Starting CABLE Output audio capture...")
        
        # Find CABLE Output device
        input_device_index = self.find_input_device("CABLE Output")
        if input_device_index is None:
            print("❌ CABLE Output device not found!")
            return
        
        input_info = pya.get_device_info_by_index(input_device_index)
        print(f"🎤 Using input device: {input_info['name']}")
        
        # Open audio stream
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=input_device_index,
            frames_per_buffer=CHUNK_SIZE,
        )
        
        print("🎤 CABLE Output ready - listening to Google Meet audio!")
        
        # Read audio chunks and send to Gemini
        while True:
            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
            except Exception as e:
                print(f"❌ Error reading audio: {e}")
                break

    async def receive_audio(self):
        """Receive audio responses from Gemini"""
        print("🔊 Starting audio response processing...")
        
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
                        print(f"💬 Gemini text: {text}")

                    if hasattr(response, 'tool_call'):
                        print(f"🔍 tool_call attribute exists: {response.tool_call}")
                        if response.tool_call:
                            print("🔧 TOOL CALL FOUND!")
                            await self.handle_tool_call(response.tool_call)
                    
                    # Handle function calls according to official documentation
                    # if hasattr(response, 'tool_call') and response.tool_call:
                    #     await self.handle_tool_call(response.tool_call)
                    
                    # # Debug: Check for any other function-related attributes
                    # if hasattr(response, 'function_calls') and response.function_calls:
                    #     print("🔍 Function calls detected in response")
                    #     print(f"Function calls: {response.function_calls}")
                
                # Clear audio queue on turn completion to prevent overlap
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
                    
            except Exception as e:
                print(f"❌ Error receiving audio: {e}")
                break

    async def play_audio(self):
        """Play audio responses to CABLE Input (Google Meet will hear this)"""
        print("🔊 Setting up audio output...")
        
        # Find CABLE Input device
        # output_device_index = self.find_output_device("CABLE Input")
        output_device_index = self.find_output_device("Voicemeeter Input")
        if output_device_index is None:
            print("❌ CABLE Input device not found!")
            return
        
        output_info = pya.get_device_info_by_index(output_device_index)
        print(f"🔊 Using speaker: {output_info['name']}")
        
        # Open output stream
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            output_device_index=output_device_index,
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
        """Main function to run the audio-only Gemini session with CABLE devices"""
        print("🎵 Gemini Live API - Audio Only with CABLE Devices")
        print("=" * 60)
        print("🤖 LIVE MODE: Gemini AI is ENABLED")
        print("🎤 Capturing audio from Google Meet (CABLE Output)")
        print("🔊 Playing Gemini responses to Google Meet (CABLE Input)")
        print("=" * 60)
        print("📝 Instructions:")
        print("1. Start this script first")
        print("2. Then start visit_meet_with_audio.py in another terminal")
        print("3. Configure Google Meet audio settings:")
        print("   - Microphone: CABLE Output (VB-Audio Virtual Cable)")
        print("   - Speaker: CABLE Input (VB-Audio Virtual Cable)")
        print("4. Speak in the meeting - Gemini will respond with audio to the meeting")
        print("5. Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            # Connect to Gemini Live API
            # config = {
            #     "response_modalities": ["AUDIO"]
            # }
            
            async with (
                self.client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                
                # Create queues
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=10)
                
                print("🔗 Connected to Gemini Live API with system prompt")
                
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
    print("🎵 Gemini Live API - Audio Only with CABLE Devices")
    print("=" * 50)
    
    # Check for API key
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ GOOGLE_API_KEY environment variable not set!")
        print("Please set your Google API key:")
        print("set GOOGLE_API_KEY=your_api_key_here")
        return
    
    gemini = AudioOnlyGeminiCable()
    asyncio.run(gemini.run())

if __name__ == "__main__":
    main()
