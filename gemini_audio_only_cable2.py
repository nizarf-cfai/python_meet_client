

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
import threading
import warnings
# Import RAG functions from chroma_script
from chroma_db.chroma_script import query_chroma_collection, rag_from_json
load_dotenv()

# Suppress Gemini warnings about non-text parts
warnings.filterwarnings("ignore", message=".*non-text parts.*")
warnings.filterwarnings("ignore", message=".*inline_data.*")
warnings.filterwarnings("ignore", message=".*concatenated text result.*")
warnings.filterwarnings("ignore", category=UserWarning)

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

# System prompt for Gemini
SYSTEM_PROMPT = f"""
You are Medforce Agent — a professional clinical assistant integrated into a shared screen canvas system.
Your purpose is to assist users in analyzing and managing medical data for patient Sarah Miller (DILI case context).
All responses and actions must remain focused on this patient. YOU ONLY SPEAK ENGLISH.

You only communicate in **English**.

---

### CORE BEHAVIOR RULES

1. **ANSWER MEDICAL QUESTIONS**
   - When the user asks about Sarah Miller’s condition, diagnosis, lab results, or treatment:
     → **Call `query_chroma_collection`** with the query text.
   - Use the returned information to provide a **complete, medically accurate** response.
   - Use all available EHR, lab, and historical data.
   - Never ask for clarification — always infer the most complete and reasonable medical answer.
   - Do not mention any technical identifiers (IDs, database names, etc.) in the response.

2. **CANVAS OPERATIONS**
   - For any canvas-related user request (navigation, focusing, creating a to-do, etc.):
     → **First call `get_canvas_objects`** with a descriptive query to find the relevant object(s).
     → Then, use the returned objectId(s) to perform the next action:
       - For movement or focus: **`navigate_canvas`**
       - For creating a new task: **`generate_task`**
   - Never ask the user for object IDs — always resolve them via `get_canvas_objects`.
   - When the action completes, briefly explain what was done (e.g., “Focused on the patient summary section.”).

3. **TASK CREATION**
   - When the user asks to create a task ("create/make/add a task…"):
     → **First, ask for user confirmation** before creating the task.
     → Present the proposed task details (title, content, items) to the user.
     → Wait for user approval before calling `generate_task`.
   - If user confirms, then call `get_canvas_objects` if needed (to identify context), then **`generate_task`**.
   - Populate `title`, `content`, and `items` fields:
       - `title`: short, clear summary of the goal.
       - `content`: concise yet informative task description.
       - `items`: step-by-step, actionable subtasks.
   - **Always ask for confirmation before creating tasks.**
   - After user confirms, explain that the task was successfully created.

4. **LAB RESULTS**
   - When the user requests or discusses a lab parameter:
     → Use **`generate_lab_result`** with all relevant details.
   - If data is unavailable, generate a realistic result consistent with DILI context.

5. **SILENCE AND DISCIPLINE**
   - Remain silent unless:
     - The user directly asks a question, **or**
     - The user explicitly requests an action (navigate, create, get data, etc.).
   - Do not provide unsolicited commentary or background explanations.

6. **BACKGROUND PROCESSING**
   - When receiving messages starting with “BACKGROUND ANALYSIS COMPLETED:”, acknowledge and summarize results.
   - Do not restate the raw data; instead, provide a concise medical interpretation.

---

### FUNCTION USAGE SUMMARY

| User Intent | Function(s) to Call | Notes |
|--------------|--------------------|-------|
| Ask about Sarah Miller’s condition or diagnosis | `query_chroma_collection` | Use query result to answer comprehensively |
| Ask for lab result | `generate_lab_result` | Use realistic medical data if missing |
| Navigate / show specific data on canvas | `get_canvas_objects` → `navigate_canvas` | Find the relevant objectId first |
| Create a to-do / task | Ask for confirmation → `get_canvas_objects` (if needed) → `generate_task` | Present task details, get approval, then create |
| Inspect available canvas items | `get_canvas_objects` | Return list or summary of items |

---

### RESPONSE GUIDELINES

- Always **call the actual tool** — never say “I will call a function”.
- Always **explain** what was accomplished after calling a function.
- Always use **get_canvas_objects** before any canvas operation requiring an objectId.
- Always **combine tool results with medical reasoning** in your explanations.
- Never display system details, IDs, or raw JSON responses to the user.
- Use precise medical terminology, but ensure clarity for clinicians.
- Stay concise, factual, and professional.

---

### TASK EXECUTION FLOW EXAMPLES (Conceptual)

**Question:**
> “What’s the probable cause of Sarah Miller’s elevated ALT levels?”

→ Call `query_chroma_collection(query="Probable cause of elevated ALT in Sarah Miller")`
→ Interpret response medically and explain.

**Navigation:**
> “Show me Sarah Miller’s medication history on the canvas.”

→ Call `get_canvas_objects(query="medication history")`
→ Extract `objectId` → Call `navigate_canvas(objectId=...)`
→ Confirm navigation to the user.

**Task:**
> "Create a task to review her latest liver biopsy results."

→ **First, ask for confirmation**: "I'd like to create a task to review Sarah Miller's latest liver biopsy results. Here's what I propose:
   - Title: 'Review liver biopsy results'
   - Content: 'Analyze and summarize findings from the latest liver biopsy'
   - Items: [list of step-by-step items]
   
   Should I proceed with creating this task?"

→ **Wait for user confirmation**

→ **If confirmed**: Call `get_canvas_objects(query="liver biopsy results")` if needed
→ Then call `generate_task(title="Review liver biopsy results", content="Analyze and summarize findings", items=[...])`
→ Confirm completion to the user. And say the task will execute in the background by a Data Analyst Agent.

---
"""



FUNCTION_DECLARATIONS = [
    {
        "name": "navigate_canvas",
        "description": "Navigate canvas to item. Use objectId from canvas item list",
        "parameters": {
            "type": "object",
            "properties": {
                "objectId": {
                    "type": "string",
                    "description": "Object id to navigate"
                }
            },
            "required": ["objectId"]
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
    },
    {
        "name": "query_chroma_collection",
        "description": "Query the medical database to answer questions about patient medical data, lab results, diagnosis, and treatment history",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The medical question or query about the patient's condition, lab results, diagnosis, or treatment"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_canvas_objects",
        "description": "Get canvas items details for navigation and canvas operations",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query to find specific canvas objects or items"
                }
            },
            "required": ["query"]
        }
    }
]


CONFIG = {
    "response_modalities": ["AUDIO"],
    "system_instruction": SYSTEM_PROMPT,
    "tools": [{"function_declarations": FUNCTION_DECLARATIONS}],
    "speech_config":{
        "voice_config": {"prebuilt_voice_config": {"voice_name": "Charon"}},
        "language_code": "en-GB"
    }
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
        self.function_call_count = 0
        self.last_function_call_time = None
        
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
            
            # Track function calls
            self.function_call_count += 1
            self.last_function_call_time = datetime.datetime.now()
            
            print(f"🔧 Function Call #{self.function_call_count}")
            
            # Process each function call in the tool call
            function_responses = []
            for fc in tool_call.function_calls:
                function_name = fc.name
                arguments = fc.args
                
                print(f"  📋 {function_name}: {json.dumps(arguments, indent=2)[:100]}...")
                
                # Create action data for saving
                action_data = {
                    "function_name": function_name,
                    "arguments": arguments,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # Save the function call to file (non-blocking)
                asyncio.create_task(self.save_function_call(arguments))
                
                # Create function response with actual RAG processing
                if fc.name == "query_chroma_collection":
                    query = arguments.get('query', '')
                    rag_result = self.query_medical_database(query)
                    print("RAG Result :",rag_result[:200])
                    fun_res = {
                        "result": {
                            "status": "Medical query processed",
                            "action": "Retrieved medical information",
                            "query": query,
                            "medical_data": rag_result,
                            "message": f"I've retrieved relevant medical information for your query: '{query}'. Here's what I found: {rag_result}",
                            "explanation": f"Medical query '{query}' processed successfully. Retrieved relevant patient medical data, lab results, and clinical information."
                        }
                    }
                elif fc.name == "get_canvas_objects":
                    query = arguments.get('query', '')
                    canvas_result = self.get_canvas_objects(query)
                    print("RAG Result Canvas:",canvas_result[:200])

                    fun_res = {
                        "result": {
                            "status": "Canvas objects retrieved",
                            "action": "Retrieved canvas items",
                            "query": query,
                            "canvas_data": canvas_result,
                            "message": f"I've retrieved relevant canvas objects for your query: '{query}'. Here's what I found: {canvas_result}",
                            "explanation": f"Canvas query '{query}' processed successfully. Retrieved relevant canvas items and objects for navigation."
                        }
                    }
                else:
                    fun_res = self.get_function_response(arguments)
                
                function_response = types.FunctionResponse(
                    id=fc.id,
                    name=fc.name,
                    response=fun_res
                )
                function_responses.append(function_response)
            
            # Send tool response back to Gemini
            await self.session.send_tool_response(function_responses=function_responses)
            print("  ✅ Response sent")
            
            # Add a delay to ensure the tool response is processed
            await asyncio.sleep(0.5)
            
            # Force session state reset by sending a simple message
            try:
                await self.session.send(input="Ready.")
                print("  🔄 Session reset")
            except Exception as reset_error:
                print(f"⚠️ Reset failed: {reset_error}")
            
        except Exception as e:
            print(f"❌ Function call error: {e}")
            # Send error response back to Gemini to clear the function call state
            try:
                from google.genai import types
                error_response = types.FunctionResponse(
                    id="error",
                    name="error",
                    response={"error": f"Function call failed: {str(e)}"}
                )
                await self.session.send_tool_response(function_responses=[error_response])
                print("  🔄 Error recovery completed")
            except Exception as error_send_error:
                print(f"❌ Error recovery failed: {error_send_error}")

    def get_function_response(self, arguments):
        if 'objectId' in arguments:
            return { 
                "result": {
                    "status": "Canvas navigation completed",
                    "action": "Moved viewport to target object",
                    "message": "I've successfully navigated to the requested canvas object. The viewport has been moved to focus on this item. You can now see the relevant information displayed on the canvas.",
                    "explanation": "Navigation completed successfully. The canvas view has been updated to show the requested object with all relevant details."
                }
            }
        elif 'parameter' in arguments:
            return { 
                "result": {
                    "status": "Lab result generated",
                    "action": "Created lab result for medical parameter",
                    "parameter": arguments.get('parameter', 'Unknown'),
                    "value": arguments.get('value', 'N/A'),
                    "unit": arguments.get('unit', ''),
                    "status_level": arguments.get('status', 'Normal'),
                    "message": f"I've successfully generated a lab result for {arguments.get('parameter', 'the requested parameter')}: {arguments.get('value', 'N/A')} {arguments.get('unit', '')} (Status: {arguments.get('status', 'Normal')}). The result is now displayed on the canvas for your review.",
                    "explanation": f"Lab result created for {arguments.get('parameter', 'parameter')} with value {arguments.get('value', 'N/A')} {arguments.get('unit', '')}. Status: {arguments.get('status', 'Normal')}. The result has been added to the canvas for analysis."
                }
            }
        elif 'query' in arguments and len(arguments) == 1:
            # This is either query_chroma_collection or get_canvas_objects
            query = arguments.get('query', '')
            # We need to determine which function was called based on context
            # For now, we'll handle both cases and let the actual function call determine the response
            return {
                "result": {
                    "status": "Query processed",
                    "action": "Retrieved relevant information",
                    "query": query,
                    "message": f"I've processed your query: '{query}'. The relevant information has been retrieved and will be used to provide you with a comprehensive answer.",
                    "explanation": f"Query '{query}' has been processed successfully. The system has retrieved relevant information to answer your question."
                }
            }
        else:
            # For task creation, include the actual task details
            task_title = arguments.get('title', 'New Task')
            task_content = arguments.get('content', 'Task created')
            task_items = arguments.get('items', [])
            
            return {
                "result": {
                    "status": "Task created successfully",
                    "action": "Created task with detailed analysis",
                    "title": task_title,
                    "content": task_content,
                    "items": task_items,
                    "message": f"I've successfully created your confirmed task: '{task_title}'. {task_content}. The task includes {len(task_items)} step-by-step items. IMPORTANT: This task will be executed and analyzed by a Data Analyst Agent in the background. You'll receive detailed analysis results shortly.",
                    "explanation": f"Task '{task_title}' created with {len(task_items)} step-by-step items. Background execution initiated - Data Analyst Agent will process this task and provide comprehensive analysis.",
                    "executed_by": "Data Analyst Agent",
                    "execution_mode": "background",
                    "background_processing": "Data Analyst Agent will analyze the task and provide detailed results in the background"
                }
            }

    def query_medical_database(self, query):
        """Query the medical database using RAG"""
        try:
            result = query_chroma_collection(query, persist_dir="./chroma_db/chroma_store", top_k=3)
            return result if result else "No relevant medical information found for this query."
        except Exception as e:
            print(f"Error querying medical database: {e}")
            return f"Error retrieving medical information: {str(e)}"

    def get_canvas_objects(self, query):
        """Get canvas objects using RAG from JSON"""
        try:
            result = rag_from_json("./chroma_db/boardItems.json", query, top_k=3)
            return result if result else "No relevant canvas objects found for this query."
        except Exception as e:
            print(f"Error getting canvas objects: {e}")
            return f"Error retrieving canvas objects: {str(e)}"

    def start_background_agent_processing(self, action_data):
        """Start agent processing in background using threading (no asyncio.create_task)"""
        def run_agent_processing():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the agent processing
                loop.run_until_complete(self._handle_agent_processing(action_data))
                
            except Exception as e:
                print(f"❌ Error in background agent processing thread: {e}")
            finally:
                loop.close()
        
        # Start the background processing in a separate thread
        thread = threading.Thread(target=run_agent_processing, daemon=True)
        thread.start()
        print(f"  🔄 Background processing started")

    async def _handle_agent_processing(self, action_data):
        """Handle agent processing in background"""
        try:
            agent_res = await canvas_ops.get_agent_answer(action_data)
            await asyncio.sleep(2)
            create_agent_res = await canvas_ops.create_result(agent_res)
            print(f"  ✅ Analysis completed")
            
            
                
        except Exception as e:
            print(f"❌ Background processing error: {e}")
            # Send error info to Gemini
            error_message = f"BACKGROUND PROCESSING ERROR: The Data Analyst Agent encountered an error while processing your task: {str(e)}"
            try:
                await self.session.send(input=error_message)
                print(f"  📝 Error message sent to Gemini")
            except Exception as error_send_error:
                print(f"⚠️ Could not send error message: {error_send_error}")

    async def save_function_call(self, action_data):
        """Save the function call to a file"""
        if not action_data:
            return
        if 'objectId' in action_data:
            focus_res = await canvas_ops.focus_item(action_data["objectId"])
            print(f"  🎯 Navigation completed")
        elif 'parameter' in action_data:
            lab_res = await canvas_ops.create_lab(action_data)
            await asyncio.sleep(2)
            labId = lab_res['id']
            focus_res = await canvas_ops.focus_item(labId)
            print(f"  🧪 Lab result created")
        elif 'query' in action_data and len(action_data) == 1:
            # Handle RAG function calls
            query = action_data.get('query', '')
            print(f"  🔍 RAG query processed: {query[:50]}...")
            # The actual RAG processing will be handled by the function response
        else:
            action_data['area'] = "planning-zone"
            task_res = await canvas_ops.create_todo(action_data)
            await asyncio.sleep(3)
            boxId = task_res['id']
            focus_res = await canvas_ops.focus_item(boxId)
            print(f"  📝 Task created")

            # Trigger agent processing in background
            self.start_background_agent_processing(action_data)
            


        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"function_call_object/gemini_function_call_{timestamp}.json"
            
            # with open(filename, 'w') as f:
            #     json.dump(action_data, f, indent=2)
            
            # print(f"💾 Function call saved to: {filename}")
            # print(f"📄 Content: {json.dumps(action_data, indent=2)}")
            
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
        print("🎤 Starting audio capture...")
        
        # Find CABLE Output device
        input_device_index = self.find_input_device("CABLE Output")
        if input_device_index is None:
            print("❌ CABLE Output device not found!")
            return
        
        input_info = pya.get_device_info_by_index(input_device_index)
        print(f"🎤 Using: {input_info['name']}")
        
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
        
        print("🎤 Audio ready!")
        
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
        print("🔊 Starting response processing...")
        
        while True:
            try:
                turn = self.session.receive()
                async for response in turn:
                    # Handle audio data
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        # Reduced logging - only log occasionally
                        # if self.function_call_count % 10 == 0:  # Log every 10th audio chunk
                        #     print(f"🔊 Audio: {len(data)} bytes")
                    
                    # Handle text responses (print them)
                    # if text := response.text:
                    #     print(f"💬 Gemini: {text}")
                        # Check if the text contains function call requests


                    # Enhanced function call detection with multiple methods
                    function_call_detected = False
                    
                    # Method 1: Check tool_call attribute
                    if hasattr(response, 'tool_call'):
                        if response.tool_call:
                            print("🔧 TOOL CALL DETECTED!")
                            await self.handle_tool_call(response.tool_call)
                            function_call_detected = True
                        # else:
                        #     print("🔍 tool_call exists but is None/False")
                    
                    # Method 2: Check function_calls attribute
                    # if not function_call_detected and hasattr(response, 'function_calls') and response.function_calls:
                    #     print("🔧 FUNCTION CALLS DETECTED!")
                    #     # Handle function calls if they exist
                    #     for fc in response.function_calls:
                    #         # Create a mock tool_call object if needed
                    #         if hasattr(fc, 'name') and hasattr(fc, 'args'):
                    #             mock_tool_call = type('MockToolCall', (), {
                    #                 'function_calls': [fc]
                    #             })()
                    #             await self.handle_tool_call(mock_tool_call)
                    #             function_call_detected = True
                    
                    # # Method 3: Check for any function-related attributes
                    # if not function_call_detected and hasattr(response, '__dict__'):
                    #     response_attrs = [attr for attr in dir(response) if not attr.startswith('_')]
                    #     if any(attr in response_attrs for attr in ['tool_call', 'function_calls', 'function_call']):
                    #         print(f"🔍 Response has function attributes: {response_attrs}")
                    #         # Print all non-None attributes for debugging
                    #         for attr in response_attrs:
                    #             try:
                    #                 value = getattr(response, attr)
                    #                 if value is not None and 'function' in attr.lower():
                    #                     print(f"🔍 {attr}: {value}")
                    #             except:
                    #                 pass
                    
                    # # Session health check - if no function calls detected for a while, log it
                    # if not function_call_detected and self.last_function_call_time:
                    #     time_since_last_call = datetime.datetime.now() - self.last_function_call_time
                    #     if time_since_last_call.total_seconds() > 30:  # 30 seconds
                    #         print(f"⚠️ No function calls detected for {time_since_last_call.total_seconds():.1f} seconds")
                    #         print(f"📊 Total function calls processed: {self.function_call_count}")
                    #         # Reset the timer to avoid spam
                    #         self.last_function_call_time = datetime.datetime.now()
                            
                    #         # Try to reset session state if no function calls for too long
                    #         if time_since_last_call.total_seconds() > 120:  # 2 minutes
                    #             try:
                    #                 await self.session.send(input="Session reset. Ready for function calls.")
                    #                 print("🔄 Forced session reset")
                    #             except Exception as force_reset_error:
                    #                 print(f"⚠️ Force reset failed: {force_reset_error}")
                
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
        output_device_index = self.find_output_device("Voicemeeter Input")
        if output_device_index is None:
            print("❌ Output device not found!")
            return
        
        output_info = pya.get_device_info_by_index(output_device_index)
        print(f"🔊 Using: {output_info['name']}")
        
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
        
        # Play audio from queue with proper buffering
        while True:
            try:
                bytestream = await self.audio_in_queue.get()
                await asyncio.to_thread(stream.write, bytestream)
                # Add small delay to ensure proper audio streaming
                await asyncio.sleep(0.01)
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
    # Suppress all warnings from the application
    warnings.filterwarnings("ignore")
    
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

# if __name__ == "__main__":
#     main()
main()