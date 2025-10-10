# Google Meet AI Assistant with Audio Bridge

This project provides an AI-powered assistant that can participate in Google Meet sessions using audio bridge technology. The system uses VB-CABLE and Voicemeeter to create a virtual audio pipeline that allows Gemini AI to listen to and respond in Google Meet calls.

## 🎯 Overview

The system consists of two main components:

1. **`gemini_audio_only_cable.py`** - The AI assistant that processes audio and responds
2. **`visit_meet_with_audio.py`** - The Google Meet automation that joins meetings

## 🔧 Prerequisites

### Required Software

1. **VB-CABLE Virtual Audio Device**
   - Download from: https://vb-audio.com/Cable/
   - Install VB-CABLE to create virtual audio devices
   - This creates "CABLE Input" and "CABLE Output" devices

2. **Voicemeeter (Optional but Recommended)**
   - Download from: https://voicemeeter.com/
   - Advanced audio mixing software for better control
   - Provides "Voicemeeter Input" and "Voicemeeter Output" devices

3. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Google API Key**
   - Set up your Google API key in environment variables:
   ```bash
   set GOOGLE_API_KEY=your_api_key_here
   ```

## 🎵 Audio Bridge Technology

### VB-CABLE Virtual Audio Cable

**VB-CABLE** is a virtual audio device that creates a "cable" between applications:

- **CABLE Input**: Virtual microphone that other applications can use as an audio source
- **CABLE Output**: Virtual speaker that receives audio from applications

**How it works:**
1. Google Meet sends audio to "CABLE Output" (virtual speaker)
2. Our Python script listens to "CABLE Output" (captures Google Meet audio)
3. Gemini AI processes the audio and generates responses
4. Our Python script sends AI responses to "CABLE Input" (virtual microphone)
5. Google Meet receives audio from "CABLE Input" (hears AI responses)

### Voicemeeter Audio Mixer

**Voicemeeter** is an advanced audio mixing application that provides:

- **Multiple audio inputs/outputs**
- **Real-time audio mixing and effects**
- **Better audio routing control**
- **Audio monitoring and recording**

**Benefits:**
- More flexible audio routing
- Better audio quality control
- Advanced mixing capabilities
- Real-time audio monitoring

## 📋 Usage Instructions

### Step 1: Setup Audio Devices

1. **Install VB-CABLE**
   - Download and install VB-CABLE from the official website
   - Restart your computer after installation
   - Verify "CABLE Input" and "CABLE Output" appear in Windows audio devices

2. **Install Voicemeeter (Optional)**
   - Download and install Voicemeeter
   - Configure audio routing as needed
   - Set up "Voicemeeter Input" and "Voicemeeter Output" devices

### Step 2: Configure Google Meet Audio

1. **Join a Google Meet session**
2. **Go to Meet Settings** (gear icon)
3. **Set Audio Devices:**
   - **Microphone**: Voicemeeter Out B1
   - **Speaker**: CABLE Input (VB-Audio Virtual Cable)

### Step 3: Run the System

**Terminal 1 - Start the AI Assistant:**
```bash
python gemini_audio_only_cable.py
```

**Terminal 2 - Join Google Meet:**
```bash
python visit_meet_with_audio.py
```

## 🔍 Script Details

### `gemini_audio_only_cable.py`

**Purpose:** AI assistant that processes Google Meet audio and responds

**Key Features:**
- Listens to Google Meet audio via CABLE Output
- Sends audio to Gemini AI for processing
- Receives AI responses and plays them via CABLE Input
- Handles function calls for canvas operations
- Medical context awareness for DILI (Drug-Induced Liver Injury) scenarios

**Audio Flow:**
```
Google Meet → CABLE Output → Python Script → Gemini AI
Gemini AI → Python Script → CABLE Input → Google Meet
```

**Function Capabilities:**
- `navigate_canvas`: Navigate to specific canvas items
- `generate_task`: Create medical tasks with step-by-step items
- `generate_lab_result`: Generate lab results with medical parameters

### `visit_meet_with_audio.py`

**Purpose:** Automates Google Meet joining and screen sharing

**Key Features:**
- Uses saved Chrome profile for automatic login
- Joins Google Meet sessions automatically
- Handles screen sharing permissions
- Opens canvas page for medical context
- Provides coordinate checking for UI automation

**Chrome Profile Management:**
- Saves login credentials for automatic authentication
- Handles Google Meet permissions
- Manages screen sharing dialogs

## 🏥 Medical Context

The system is configured for medical scenarios, specifically:

- **Patient**: Sarah Miller with DILI (Drug-Induced Liver Injury)
- **EHR Integration**: Access to medical records and lab results
- **Canvas Operations**: Interactive medical dashboard
- **Lab Results**: ALT, AST, Bilirubin, and other liver function tests

## 🛠️ Troubleshooting

### Common Issues

1. **"CABLE Output device not found"**
   - Ensure VB-CABLE is properly installed
   - Check Windows audio devices in Sound settings
   - Restart the application

2. **"Google API key not set"**
   - Set the GOOGLE_API_KEY environment variable
   - Verify the API key is valid and has proper permissions

3. **Audio not working in Google Meet**
   - Check Google Meet audio settings
   - Ensure CABLE Input/Output are selected
   - Test audio devices in Windows Sound settings

4. **Chrome profile issues**
   - Run `chrome_profile_manager.py` first to set up profile
   - Check if profile directory exists
   - Verify login credentials are saved

### Audio Device Configuration

**Windows Sound Settings:**
1. Right-click speaker icon → "Open Sound settings"
2. Go to "Sound Control Panel"
3. Verify CABLE Input and CABLE Output devices are present
4. Test devices to ensure they're working

**Google Meet Audio Test:**
1. Join a test meeting
2. Go to Meet settings
3. Test microphone and speaker
4. Verify audio is routing through CABLE devices

## 📁 File Structure

```
python_client/
├── gemini_audio_only_cable.py    # AI assistant with audio processing
├── visit_meet_with_audio.py      # Google Meet automation
├── canvas_ops.py                  # Canvas operations for medical context
├── chrome_profile/               # Saved Chrome profile
├── function_call_object/         # Function call logs
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔧 Configuration

### Environment Variables
```bash
GOOGLE_API_KEY=your_google_api_key_here
```

### Audio Settings
- **Input Device**: CABLE Output (VB-Audio Virtual Cable)
- **Output Device**: CABLE Input (VB-Audio Virtual Cable)
- **Sample Rate**: 16000 Hz (input), 24000 Hz (output)
- **Channels**: Mono (1 channel)

### Google Meet Settings
- **Microphone**: CABLE Output
- **Speaker**: CABLE Input
- **Camera**: Any available camera

## 🚀 Advanced Usage

### Custom Audio Routing
You can modify the audio device selection in `gemini_audio_only_cable.py`:

```python
# Change input device
input_device_index = self.find_input_device("Your Device Name")

# Change output device  
output_device_index = self.find_output_device("Your Device Name")
```

### Medical Context Customization
Modify the system prompt in `gemini_audio_only_cable.py` to change the medical context:

```python
SYSTEM_PROMPT = f"""Your custom medical context here..."""
```

## 📞 Support

For issues related to:
- **VB-CABLE**: Visit https://vb-audio.com/Cable/
- **Voicemeeter**: Visit https://voicemeeter.com/
- **Google Meet**: Check Google Meet support documentation
- **Python/Audio**: Check PyAudio documentation

## ⚠️ Important Notes

1. **Audio Latency**: There may be slight audio delay due to processing
2. **Internet Connection**: Requires stable internet for Google Meet and Gemini AI
3. **API Costs**: Gemini AI usage may incur costs based on your Google Cloud billing
4. **Privacy**: Audio is processed by Google's Gemini AI service
5. **Compatibility**: Tested on Windows 10/11 with Chrome browser

## 🔄 Updates

- **v1.0**: Initial release with basic audio bridge functionality
- **v1.1**: Added medical context and canvas operations
- **v1.2**: Improved error handling and device detection
- **v1.3**: Added Voicemeeter support and advanced audio routing

---

**Made with ❤️ for medical professionals and AI enthusiasts**
