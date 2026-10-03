import os
import json
import logging

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# ============================================================
# 1. ENVIRONMENT & LOGGING
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Disable browser caching during development
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ============================================================
# 2. LOAD PMUY KNOWLEDGE BASE
# ============================================================

DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "pmuy_data.json"
)

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        PMUY_KB = json.load(f)

    logger.info("PMUY Knowledge Base loaded successfully.")

except Exception as e:
    logger.error(f"Failed to load PMUY Knowledge Base: {e}")

    PMUY_KB = {
        "scheme": {},
        "quick_guided_questions": [],
        "intents": {}
    }


# ============================================================
# 3. GEMINI API SETUP
# ============================================================

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

gemini_client = None

if GEMINI_API_KEY:

    try:
        from google import genai

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        logger.info(
            "Google Gemini Client initialized successfully."
        )

    except Exception as e:

        logger.warning(
            f"Could not initialize Google GenAI client: {e}"
        )

        gemini_client = None

else:

    logger.info(
        "No GEMINI_API_KEY found. "
        "Operating in verified local-knowledge fallback mode."
    )


# ============================================================
# 4. INTENT DETECTION
# ============================================================

def detect_intent(user_text: str) -> str:
    """
    Detects the user's intent using the verified PMUY
    knowledge-base keywords plus common Tamil/English
    transliterations.
    """

    if not isinstance(user_text, str):
        return "general_pmuy"

    clean_text = user_text.lower().strip()

    if not clean_text:
        return "general_pmuy"

    # --------------------------------------------------------
    # Direct yes/no responses
    # --------------------------------------------------------

    yes_words = [
        "ஆம்",
        "ஆமாம்",
        "ஆமா",
        "yes",
        "ok",
        "சரி",
        "வேண்டும்",
        "வேணும்"
    ]

    no_words = [
        "இல்லை",
        "வேண்டாம்",
        "வேணாம்",
        "நோ",
        "no",
        "not now"
    ]

    if clean_text in yes_words:
        return "yes_interested"

    if clean_text in no_words:
        return "no_not_interested"

    # --------------------------------------------------------
    # Knowledge-base intent matching
    # --------------------------------------------------------

    intents = PMUY_KB.get("intents", {})

    scores = {}

    for intent_key, intent_data in intents.items():

        if not isinstance(intent_data, dict):
            continue

        score = 0

        keywords = intent_data.get("keywords", [])

        if not isinstance(keywords, list):
            continue

        for keyword in keywords:

            if not isinstance(keyword, str):
                continue

            keyword_clean = keyword.lower().strip()

            if not keyword_clean:
                continue

            # Exact match
            if keyword_clean == clean_text:

                score += 20 + len(keyword_clean)

            # Partial match
            elif keyword_clean in clean_text:

                score += 5 + len(keyword_clean)

        if score > 0:
            scores[intent_key] = score

    if scores:

        best_intent = max(
            scores,
            key=scores.get
        )

        return best_intent

    # ========================================================
    # Secondary Tamil / English transliteration matching
    # ========================================================

    if any(word in clean_text for word in [
        "thakuthi",
        "thaguthi",
        "thahuthi",
        "eligible",
        "eligibility",
        "vayas",
        "vayasu",
        "age",
        "தகுதி",
        "வயது"
    ]):
        return "eligibility"

    if any(word in clean_text for word in [
        "document",
        "documents",
        "aavanangal",
        "aavanam",
        "aadhaar",
        "aadhar",
        "ration",
        "paper",
        "photo",
        "ஆவணம்",
        "ஆவணங்கள்",
        "ஆதார்"
    ]):
        return "documents"

    if any(word in clean_text for word in [
        "benefit",
        "benefits",
        "nanmai",
        "nanmaigal",
        "free",
        "stove",
        "aduppu",
        "cylinder",
        "maniyam",
        "subsidy",
        "நன்மை",
        "நன்மைகள்"
    ]):
        return "benefits"

    if any(word in clean_text for word in [
        "eppadi",
        "apply",
        "application",
        "vinnappam",
        "steps",
        "process",
        "seyyavendum",
        "epadi",
        "எப்படி",
        "விண்ணப்பம்"
    ]):
        return "how_to_apply"

    if any(word in clean_text for word in [
        "engu",
        "enga",
        "engae",
        "agency",
        "where",
        "office",
        "centre",
        "center",
        "near",
        "அருகில்",
        "எங்கே"
    ]):
        return "where_to_apply"

    if any(word in clean_text for word in [
        "panam",
        "kasu",
        "kattanam",
        "fee",
        "cost",
        "vilai",
        "rupees",
        "amount",
        "பணம்",
        "கட்டணம்",
        "செலவு"
    ]):
        return "cost_fee"

    if any(word in clean_text for word in [
        "vanakkam",
        "hello",
        "hi",
        "sollunga",
        "வணக்கம்",
        "ஹலோ"
    ]):
        return "greeting"

    if any(word in clean_text for word in [
        "number",
        "helpline",
        "phone",
        "contact",
        "official",
        "toll",
        "help",
        "எண்",
        "உதவி"
    ]):
        return "helpline_official"

    # --------------------------------------------------------
    # Safe general fallback
    # --------------------------------------------------------

    return "general_pmuy"


# ============================================================
# 5. GET SAFE INTENT INFORMATION
# ============================================================

def get_intent_info(intent_key: str) -> dict:
    """
    Gets intent information only from the PMUY knowledge base.

    No government facts are invented here.
    """

    intents = PMUY_KB.get("intents", {})

    intent_info = intents.get(intent_key)

    if isinstance(intent_info, dict):
        return intent_info

    # Safe fallback without inventing PMUY facts
    return {
        "title_tamil": "உஜ்வாலா திட்டம்",
        "summary_tamil": (
            "உஜ்வாலா திட்டம் பற்றிய தகவலை அறிய "
            "கீழே உள்ள கேள்விகளில் ஒன்றைத் தேர்ந்தெடுக்கவும்."
        ),
        "points_tamil": [],
        "next_steps_tamil": (
            "தகுதி, ஆவணங்கள் அல்லது விண்ணப்பிக்கும் "
            "முறையைப் பற்றி கேட்கலாம்."
        ),
        "suggested_questions": [
            "நான் தகுதியானவளா?",
            "என்ன ஆவணங்கள் வேண்டும்?",
            "எப்படி விண்ணப்பிப்பது?"
        ]
    }


# ============================================================
# 6. GENERATE GROUNDED GEMINI RESPONSE
# ============================================================

def generate_gemini_response(
    user_message: str,
    intent_key: str,
    intent_info: dict
):
    """
    Uses Gemini only to simplify/rephrase information
    already present in the verified local knowledge base.

    Gemini is NOT allowed to create new PMUY facts.
    """

    global gemini_client

    if not gemini_client:
        return None

    scheme_info = PMUY_KB.get("scheme", {})

    points = intent_info.get(
        "points_tamil",
        []
    )

    if not isinstance(points, list):
        points = []

    points_text = "\n".join(
        f"- {point}"
        for point in points
        if isinstance(point, str)
    )

    context_text = f"""
அரசு திட்டம்:
{scheme_info.get("name_tamil", "")}
({scheme_info.get("name_english", "")})

அதிகாரப்பூர்வ இணையதளம்:
{scheme_info.get("official_website", "")}

உதவி எண்:
{scheme_info.get("toll_free_helpline", "")}

சரிபார்க்கப்பட்ட அறிவுத் தரவு:

தலைப்பு:
{intent_info.get("title_tamil", "")}

முக்கிய விளக்கம்:
{intent_info.get("summary_tamil", "")}

முக்கிய குறிப்புகள்:
{points_text}

அடுத்த படி:
{intent_info.get("next_steps_tamil", "")}
"""

    system_prompt = f"""
நீ "சகி வழிகாட்டி AI" (SakhiGuide AI).

உன் பயனர் முதன்முறையாக இணையத்தைப் பயன்படுத்தும்
ஒரு கிராமப்புற தமிழ் பெண் என்று கருதி மிகவும் எளிமையாக
விளக்க வேண்டும்.

முக்கிய விதிகள்:

1. கீழே வழங்கப்பட்டுள்ள சரிபார்க்கப்பட்ட PMUY
   அறிவுத் தரவிலிருந்து மட்டுமே தகவலைப் பயன்படுத்த வேண்டும்.

2. உன் சொந்தமாக அரசு விதிமுறைகள், தகுதி,
   ஆவணங்கள், பணம், நன்மைகள் அல்லது எண்ணிக்கைகளை
   உருவாக்கக்கூடாது.

3. அறிவுத் தரவில் இல்லாத தகவலை உறுதியாக கூறக்கூடாது.

4. மிகவும் எளிய, மரியாதையான தமிழில் பதிலளிக்க வேண்டும்.

5. கடினமான அரசு அல்லது ஆங்கில வார்த்தைகளை
   முடிந்தவரை தவிர்க்க வேண்டும்.

6. பதில் சுருக்கமாக இருக்க வேண்டும்.

7. பயனர் அடுத்து என்ன செய்ய வேண்டும் என்பதை
   தெளிவாகக் கூற வேண்டும்.

8. அறிவுத் தரவுக்கு வெளியே இருந்து தகவல் தேவைப்பட்டால்,
   "அதிகாரப்பூர்வ தகவலை சரிபார்க்கவும்" என்று கூற வேண்டும்.

சரிபார்க்கப்பட்ட தகவல்:
{context_text}
"""

    prompt = f"""
பயனரின் கேள்வி:

{user_message}

இந்த கேள்விக்கு மேலே கொடுக்கப்பட்ட
சரிபார்க்கப்பட்ட தகவலை மட்டுமே பயன்படுத்தி,
மிகவும் எளிய மற்றும் அன்பான தமிழில் பதிலளிக்கவும்.
"""

    try:

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                system_prompt
                                + "\n\n"
                                + prompt
                            )
                        }
                    ]
                }
            ]
        )

        ai_text = ""

        if response and response.text:
            ai_text = response.text.strip()

        if ai_text:

            return {
                "summary": ai_text,
                "model_used": "gemini-2.5-flash"
            }

    except Exception as e:

        logger.warning(
            "Gemini API request failed. "
            f"Falling back to local KB: {e}"
        )

    return None


# ============================================================
# 7. FAVICON
# ============================================================

@app.route("/favicon.ico")
def favicon():
    return "", 204


# ============================================================
# 8. MAIN PAGE
# ============================================================

@app.route("/")
def index():

    scheme = PMUY_KB.get(
        "scheme",
        {}
    )

    quick_questions = PMUY_KB.get(
        "quick_guided_questions",
        []
    )

    return render_template(
        "index.html",
        scheme=scheme,
        quick_questions=quick_questions
    )


# ============================================================
# 9. HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy",
        "app_name": "SakhiGuide AI",
        "scheme": PMUY_KB.get(
            "scheme",
            {}
        ).get(
            "name_tamil",
            "PMUY"
        ),
        "gemini_active": bool(gemini_client),
        "intents_available": len(
            PMUY_KB.get(
                "intents",
                {}
            )
        ),
        "version": "1.0.0"
    })


# ============================================================
# 10. TOPICS
# ============================================================

@app.route("/api/topics", methods=["GET"])
def topics():

    return jsonify({
        "scheme": PMUY_KB.get(
            "scheme",
            {}
        ),
        "quick_questions": PMUY_KB.get(
            "quick_guided_questions",
            []
        )
    })


# ============================================================
# 11. CHAT API
# ============================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    # --------------------------------------------------------
    # Read request
    # --------------------------------------------------------

    data = request.get_json(
        silent=True
    ) or {}

    user_message = data.get(
        "message",
        ""
    )

    language = data.get(
        "language",
        "ta"
    )

    # Make sure message is a string
    if not isinstance(user_message, str):
        user_message = str(user_message)

    user_message = user_message.strip()

    # --------------------------------------------------------
    # Empty input
    # --------------------------------------------------------

    if not user_message:

        return jsonify({
            "status": "error",
            "message_tamil": (
                "தயவுசெய்து ஒரு கேள்வியைத் "
                "தேர்ந்தெடுக்கவும் அல்லது பேசுங்கள் அம்மா."
            ),
            "message": "Input message is empty"
        }), 400

    # --------------------------------------------------------
    # Detect intent
    # --------------------------------------------------------

    intent_key = detect_intent(
        user_message
    )

    # --------------------------------------------------------
    # YES FLOW
    # --------------------------------------------------------

    if intent_key == "yes_interested":

        intent_info = get_intent_info(
            "yes_interested"
        )

        # If yes_interested doesn't exist in KB,
        # give a safe navigation response.
        if not PMUY_KB.get(
            "intents",
            {}
        ).get("yes_interested"):

            return jsonify({
                "status": "success",
                "intent": "yes_interested",
                "title": "மகிழ்ச்சி அம்மா!",
                "summary": (
                    "மகிழ்ச்சி அம்மா! "
                    "உஜ்வாலா திட்டம் பற்றி மேலும் தெரிந்து கொள்ளலாம்."
                ),
                "points": [],
                "next_steps": (
                    "முதலில் நீங்கள் தகுதியானவரா "
                    "என்பதைப் பார்க்கலாம்."
                ),
                "suggested_questions": [
                    "நான் தகுதியானவளா?",
                    "என்ன ஆவணங்கள் வேண்டும்?",
                    "எப்படி விண்ணப்பிப்பது?"
                ],
                "official_info": {
                    "website": PMUY_KB.get(
                        "scheme",
                        {}
                    ).get(
                        "official_website",
                        "https://www.pmuy.gov.in"
                    ),
                    "helpline": PMUY_KB.get(
                        "scheme",
                        {}
                    ).get(
                        "toll_free_helpline",
                        ""
                    )
                },
                "model_used": "local-guided-flow",
                "language": language
            })

    # --------------------------------------------------------
    # NO FLOW
    # --------------------------------------------------------

    if intent_key == "no_not_interested":

        intent_info = get_intent_info(
            "no_not_interested"
        )

        return jsonify({
            "status": "success",
            "intent": "no_not_interested",
            "title": intent_info.get(
                "title_tamil",
                "சரி அம்மா"
            ),
            "summary": intent_info.get(
                "summary_tamil",
                "சரி அம்மா, பரவாயில்லை."
            ),
            "points": intent_info.get(
                "points_tamil",
                []
            ),
            "next_steps": intent_info.get(
                "next_steps_tamil",
                ""
            ),
            "suggested_questions": intent_info.get(
                "suggested_questions",
                [
                    "உஜ்வாலா திட்டம் பற்றி சொல்",
                    "நான் தகுதியானவளா?",
                    "என்ன நன்மைகள் கிடைக்கும்?"
                ]
            ),
            "official_info": {
                "website": PMUY_KB.get(
                    "scheme",
                    {}
                ).get(
                    "official_website",
                    "https://www.pmuy.gov.in"
                ),
                "helpline": PMUY_KB.get(
                    "scheme",
                    {}
                ).get(
                    "toll_free_helpline",
                    ""
                )
            },
            "model_used": "local-guided-flow",
            "language": language
        })

    # --------------------------------------------------------
    # Get information from local knowledge base
    # --------------------------------------------------------

    intent_info = get_intent_info(
        intent_key
    )

    # --------------------------------------------------------
    # Try Gemini only if available
    # --------------------------------------------------------

    gemini_result = None

    if gemini_client:

        gemini_result = generate_gemini_response(
            user_message,
            intent_key,
            intent_info
        )

    # --------------------------------------------------------
    # Select response
    # --------------------------------------------------------

    if (
        gemini_result
        and gemini_result.get("summary")
    ):

        summary_text = gemini_result["summary"]

        model_name = gemini_result.get(
            "model_used",
            "gemini-2.5-flash"
        )

    else:

        summary_text = intent_info.get(
            "summary_tamil",
            "மன்னிக்கவும் அம்மா. இந்த தகவல் தற்போது கிடைக்கவில்லை."
        )

        model_name = "local-grounded-kb"

    # --------------------------------------------------------
    # Official information
    # --------------------------------------------------------

    scheme_info = PMUY_KB.get(
        "scheme",
        {}
    )

    official_info = {
        "website": scheme_info.get(
            "official_website",
            "https://www.pmuy.gov.in"
        ),
        "helpline": scheme_info.get(
            "toll_free_helpline",
            ""
        ),
        "emergency": scheme_info.get(
            "emergency_helpline",
            ""
        )
    }

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    return jsonify({
        "status": "success",
        "intent": intent_key,
        "title": intent_info.get(
            "title_tamil",
            "உஜ்வாலா திட்டம்"
        ),
        "summary": summary_text,
        "points": intent_info.get(
            "points_tamil",
            []
        ),
        "next_steps": intent_info.get(
            "next_steps_tamil",
            ""
        ),
        "suggested_questions": intent_info.get(
            "suggested_questions",
            [
                "நான் தகுதியானவளா?",
                "என்ன ஆவணங்கள் வேண்டும்?",
                "எப்படி விண்ணப்பிப்பது?"
            ]
        ),
        "official_info": official_info,
        "model_used": model_name,
        "language": language
    })


# ============================================================
# 12. APPLICATION START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            5000
        )
    )

    host = os.getenv(
        "HOST",
        "0.0.0.0"
    )

    logger.info(
        f"Starting SakhiGuide AI on http://{host}:{port}"
    )

    app.run(
        host=host,
        port=port,
        debug=True
    )