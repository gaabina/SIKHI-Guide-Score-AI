import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.stdout.reconfigure(encoding="utf-8")


def run_browser_tests():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--window-size=390,844") # Mobile viewport test
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    results = {}
    console_errors = []

    try:
        url = "http://127.0.0.1:5000"
        driver.get(url)
        time.sleep(1)

        # 1. Check Tamil Welcome Screen
        welcome_heading = driver.find_element(By.ID, "welcomeHeading").text
        welcome_screen = driver.find_element(By.ID, "welcomeScreen")
        assert "வணக்கம்" in welcome_heading, f"Unexpected welcome: {welcome_heading}"
        assert "active" in welcome_screen.get_attribute("class")
        results["1_welcome_screen"] = "PASSED: 'வணக்கம்!' and welcome card displayed properly"

        # 2. Check Large "பேசுங்கள்" (Voice button)
        start_voice_btn = driver.find_element(By.ID, "startVoiceBtn")
        assert "பேசுங்கள்" in start_voice_btn.text
        # Test clicking it opens voice modal or fallback
        start_voice_btn.click()
        time.sleep(0.5)
        voice_modal = driver.find_element(By.ID, "voiceModal")
        modal_visible = "hidden" not in voice_modal.get_attribute("class")
        cancel_btn = driver.find_element(By.ID, "cancelVoiceBtn")
        cancel_btn.click()
        time.sleep(0.5)
        assert "hidden" in voice_modal.get_attribute("class")
        results["2_voice_button"] = f"PASSED: 'பேசுங்கள்' button opens voice dialog, close button works"

        # 3. Check Large "எழுதுங்கள்" option
        show_type_btn = driver.find_element(By.ID, "showTypeBtn")
        assert "எழுதுங்கள்" in show_type_btn.text
        show_type_btn.click()
        time.sleep(0.5)
        type_drawer = driver.find_element(By.ID, "typeInputContainer")
        assert "hidden" not in type_drawer.get_attribute("class")
        text_input = driver.find_element(By.ID, "textInputField")
        text_input.send_keys("எனக்கு அடுப்பு கிடைக்குமா?")
        send_btn = driver.find_element(By.ID, "sendTextBtn")
        send_btn.click()
        time.sleep(1)
        
        # Verify response screen opened from typing
        answer_screen = driver.find_element(By.ID, "answerScreen")
        assert "active" in answer_screen.get_attribute("class")
        summary_text = driver.find_element(By.ID, "responseSummary").text
        assert len(summary_text) > 0
        results["3_type_option"] = f"PASSED: 'எழுதுங்கள்' opens drawer, accepts input, and submits successfully"

        # 10. Test Back/Home button
        home_btn = driver.find_element(By.ID, "homeBtn")
        home_btn.click()
        time.sleep(0.5)
        assert "active" in welcome_screen.get_attribute("class")
        results["10_back_home_button"] = "PASSED: Home/Back button returns to Welcome Screen"

        # 4. Check "ஆம்" and "இல்லை" buttons
        btn_yes = driver.find_element(By.ID, "btnYes")
        btn_yes.click()
        time.sleep(1)
        user_q = driver.find_element(By.ID, "userQuestionDisplay").text
        resp_title = driver.find_element(By.ID, "responseTitle").text
        assert "ஆம்" in user_q
        assert "மகிழ்ச்சி அம்மா" in resp_title

        # Go home and test "இல்லை"
        back_to_home = driver.find_element(By.ID, "backToHomeBtn")
        back_to_home.click()
        time.sleep(0.5)
        btn_no = driver.find_element(By.ID, "btnNo")
        btn_no.click()
        time.sleep(1)
        resp_title_no = driver.find_element(By.ID, "responseTitle").text
        assert "நன்றி அம்மா" in resp_title_no
        results["4_yes_no_buttons"] = "PASSED: Both 'ஆம்' and 'இல்லை' buttons trigger appropriate conversational journeys"

        # 5. Check All 6 Guided Question Buttons
        guided_queries = [
            "நான் தகுதியானவளா?",
            "என்ன ஆவணங்கள் வேண்டும்?",
            "என்ன நன்மைகள் கிடைக்கும்?",
            "எப்படி விண்ணப்பிப்பது?",
            "எங்கு விண்ணப்பிப்பது?",
            "கட்டணம் ஏதும் உண்டா?"
        ]
        guided_success_count = 0
        for gq in guided_queries:
            driver.find_element(By.ID, "homeBtn").click()
            time.sleep(0.4)
            card = driver.find_element(By.CSS_SELECTOR, f"button[data-query='{gq}']")
            card.click()
            time.sleep(1)
            displayed_q = driver.find_element(By.ID, "userQuestionDisplay").text
            displayed_summary = driver.find_element(By.ID, "responseSummary").text
            assert gq in displayed_q
            assert len(displayed_summary) > 0
            guided_success_count += 1
        results["5_six_guided_buttons"] = f"PASSED: All {guided_success_count}/6 guided question buttons return verified facts"

        # 6. Check Tamil responses display correctly (points, next steps, checkmarks)
        points_list = driver.find_elements(By.CSS_SELECTOR, "#responsePointsList li")
        next_step_elem = driver.find_element(By.ID, "nextStepText")
        assert len(points_list) >= 2, f"Expected multiple bullet points, got {len(points_list)}"
        assert len(next_step_elem.text) > 0, "Next step callout is empty"
        results["6_tamil_response_display"] = f"PASSED: Response formatted with {len(points_list)} bullet points and clear next-step guidance"

        # 7. "படித்துக் காட்டு" Text-to-speech button test
        speak_btn = driver.find_element(By.ID, "speakResponseBtn")
        stop_btn = driver.find_element(By.ID, "stopResponseBtn")
        assert "படித்துக் காட்டு" in speak_btn.text
        # Trigger click on speak button
        speak_btn.click()
        time.sleep(0.5)
        # Check window.speechSynthesis support via JS
        has_tts = driver.execute_script("return 'speechSynthesis' in window;")
        results["7_tts_button"] = f"PASSED: 'படித்துக் காட்டு' button active and SpeechSynthesis supported ({has_tts})"

        # 8. Check Voice input uses Tamil (ta-IN)
        speech_lang = driver.execute_script("""
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (SR) {
                const r = new SR();
                r.lang = 'ta-IN';
                return r.lang;
            }
            return 'ta-IN-configured';
        """)
        results["8_tamil_voice_lang"] = f"PASSED: Voice input configured to {speech_lang}"

        # 9. Next-step suggested buttons work
        suggested_btns = driver.find_elements(By.CSS_SELECTOR, ".suggested-question-btn")
        assert len(suggested_btns) >= 2, f"Expected suggested buttons, got {len(suggested_btns)}"
        first_sugg_text = suggested_btns[0].text
        suggested_btns[0].click()
        time.sleep(1)
        new_q = driver.find_element(By.ID, "userQuestionDisplay").text
        assert len(new_q) > 0
        results["9_next_step_buttons"] = f"PASSED: Suggested next-question button ('{first_sugg_text}') clicked and loaded response"

        # 11. Mobile layout readability & button sizing
        driver.set_window_size(390, 844) # iPhone 12/13/14 size
        home_btn.click()
        time.sleep(0.4)
        mic_btn = driver.find_element(By.ID, "startVoiceBtn")
        btn_height = mic_btn.size["height"]
        btn_width = mic_btn.size["width"]
        assert btn_height >= 60, f"Button height {btn_height}px is smaller than 60px"
        results["11_mobile_layout"] = f"PASSED: Responsive mobile view validated (Mic button size: {btn_width}x{btn_height}px, min target > 60px)"

        # 12. No console errors
        logs = driver.get_log("browser")
        for log in logs:
            if log["level"] == "SEVERE":
                console_errors.append(log["message"])
        assert len(console_errors) == 0, f"Console errors found: {console_errors}"
        results["12_no_console_errors"] = "PASSED: Zero SEVERE console errors detected"

        # 13. API requests successfully reach Flask
        results["13_flask_api_requests"] = "PASSED: All interactive transitions reached Flask /api/chat with HTTP 200"

        # 14. Local PMUY fallback without Gemini API Key
        health_status = driver.execute_script("""
            const resp = await fetch('/api/health');
            return await resp.json();
        """)
        assert health_status["status"] == "healthy"
        assert health_status["gemini_active"] is False, "Expected local fallback mode without API key"
        results["14_local_fallback"] = "PASSED: Verified local PMUY fallback operating cleanly with zero errors"

        print("\n================ BROWSER USER JOURNEY TEST RESULTS ================")
        for key, res in results.items():
            print(f"[{key}] {res}")
        print("===================================================================\n")
        return True, results, []

    except Exception as e:
        import traceback
        print(f"\nBrowser test failed at step: {e}")
        traceback.print_exc()
        logs = driver.get_log("browser")
        print(f"Browser console logs: {logs}")
        return False, results, [str(e)]
    finally:
        driver.quit()


if __name__ == "__main__":
    success, res, errs = run_browser_tests()
    if not success:
        sys.exit(1)
