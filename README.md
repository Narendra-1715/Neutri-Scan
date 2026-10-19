# 🥗 Neutri-Scan (MacroSnap)

An AI-powered nutrition assistant built with **Streamlit** and **Google Gemini Vision**. Upload photos of your meals or snacks to instantly receive detailed ingredient breakdowns, protein and macronutrient estimates, and extra dietary insights.

## ✨ Features

- 📸 **Visual Food Recognition**: Upload or snap a food photo to detect dishes and estimated portion sizes.
- 🥗 **Ingredients Breakdown**: Identifies visible and estimated ingredients in your meal.
- 📊 **Protein & Macro Tracking**: Detailed breakdown of Calories, Protein (highlighted), Carbohydrates (with fiber & sugars), and Fats.
- 💡 **Extra Nutritional Insights**: Provides key vitamins & minerals, dietary profiles (High-Protein, Vegan, Gluten-Free), allergen warnings, and actionable health tips.
- 🛡️ **Fault-Tolerant AI Engine**: Built-in retry logic and smart model failover (`gemini-3.5-flash` with `gemini-3.5-flash-lite` fallback) to prevent interruptions during high-demand spikes.
- 📤 **WhatsApp Integration (Optional)**: Send a comprehensive daily meal summary directly to your phone via Twilio WhatsApp API.

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Narendra-1715/Neutri-Scan.git
cd Neutri-Scan
```

### 2. Create a virtual environment and install dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure API Secrets
Create `.streamlit/secrets.toml` by copying the example file:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and insert your [Google AI Studio API Key](https://aistudio.google.com/):
```toml
GEMINI_API_KEY = "your_actual_gemini_api_key"
```

*(Optional) Configure Twilio credentials if you wish to enable WhatsApp meal summaries.*

### 4. Run the Application
```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

## 📦 Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **AI / LLM**: [Google GenAI SDK](https://github.com/googleapis/python-genai) (`gemini-3.5-flash` / `gemini-3.5-flash-lite`)
- **Messaging**: [Twilio REST API](https://www.twilio.com/) (Optional)
