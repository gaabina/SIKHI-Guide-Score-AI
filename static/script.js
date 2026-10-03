/**
 * SakhiGuide AI — Premium Redesign Controller
 * Preserves all original backend functionality:
 *   /api/chat · /api/health · Tamil voice (ta-IN) · TTS · PMUY KB · 6 questions
 * Adds: floating chatbot · scroll reveals · cinematic transitions
 */

document.addEventListener("DOMContentLoaded", () => {

  // =========================================================================
  // DOM REFERENCES — existing IDs kept intact
  // =========================================================================

  const welcomeScreen        = document.getElementById("welcomeScreen");
  const answerScreen         = document.getElementById("answerScreen");
  const homeBtn              = document.getElementById("homeBtn");
  const backToHomeBtn        = document.getElementById("backToHomeBtn");
  const scrollProgressBar    = document.getElementById("scrollProgressBar");

  // Yes / No
  const btnYes = document.getElementById("btnYes");
  const btnNo  = document.getElementById("btnNo");

  // Voice + text (existing IDs preserved)
  const startVoiceBtn      = document.getElementById("startVoiceBtn");
  const showTypeBtn        = document.getElementById("showTypeBtn");
  const typeInputContainer = document.getElementById("typeInputContainer");
  const closeTypeBtn       = document.getElementById("closeTypeBtn");
  const textQueryForm      = document.getElementById("textQueryForm");
  const textInputField     = document.getElementById("textInputField");

  // Voice modal
  const voiceModal             = document.getElementById("voiceModal");
  const cancelVoiceBtn         = document.getElementById("cancelVoiceBtn");
  const voiceTranscriptPreview = document.getElementById("voiceTranscriptPreview");

  // Answer screen
  const userQuestionDisplay  = document.getElementById("userQuestionDisplay");
  const loadingBox           = document.getElementById("loadingBox");
  const responseCard         = document.getElementById("responseCard");
  const responseTitle        = document.getElementById("responseTitle");
  const responseSummary      = document.getElementById("responseSummary");
  const responsePointsList   = document.getElementById("responsePointsList");
  const nextStepText         = document.getElementById("nextStepText");
  const suggestedButtonsGrid = document.getElementById("suggestedButtonsGrid");
  const speakResponseBtn     = document.getElementById("speakResponseBtn");
  const stopResponseBtn      = document.getElementById("stopResponseBtn");
  const speakAgainBtn        = document.getElementById("speakAgainBtn");

  // Floating chatbot
  const chatbotToggle  = document.getElementById("chatbotToggle");
  const chatbotWindow  = document.getElementById("chatbotWindow");
  const chatbotClose   = document.getElementById("chatbotClose");
  const chatMessages   = document.getElementById("chatMessages");
  const chatTyping     = document.getElementById("chatTyping");
  const chatVoiceBtn   = document.getElementById("chatVoiceBtn");
  const chatTextInput  = document.getElementById("chatTextInput");
  const chatSendBtn    = document.getElementById("chatSendBtn");

  let currentSpokenText  = "";
  let chatbotOpen        = false;

  // =========================================================================
  // 1. SCROLL PROGRESS BAR
  // =========================================================================
  function updateScrollProgress() {
    const scrollTop    = window.scrollY || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    if (scrollHeight > 0 && scrollProgressBar) {
      scrollProgressBar.style.width = `${(scrollTop / scrollHeight) * 100}%`;
    }
  }

  window.addEventListener("scroll", updateScrollProgress, { passive: true });

  // =========================================================================
  // 2. SCROLL-REVEAL (IntersectionObserver)
  // =========================================================================
  const revealItems = document.querySelectorAll(".reveal-section");

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });

    revealItems.forEach(el => observer.observe(el));
  } else {
    revealItems.forEach(el => el.classList.add("is-visible"));
  }

  // Reveal first section immediately
  const section1 = document.getElementById("section1");
  if (section1) {
    // No reveal class on section1 — it's always visible
  }

  // =========================================================================
  // 3. SPEECH RECOGNITION — Tamil (ta-IN) — UNCHANGED
  // =========================================================================
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition  = null;
  let isListening  = false;
  let voiceLang    = "ta";
  const VOICE_LANG_CODES = { ta: "ta-IN", en: "en-IN" };

  if (SpeechRecognition) {
    try {
      recognition               = new SpeechRecognition();
      recognition.continuous    = false;
      recognition.interimResults = true;
      recognition.lang          = "ta-IN"; // Tamil (India) — REQUIRED, do not change

      recognition.onstart = () => {
        isListening = true;
        voiceModal.classList.remove("hidden");
        voiceTranscriptPreview.textContent = "பேசுங்கள், நான் கேட்கிறேன்...";

        // Visual: activate mic button
        if (startVoiceBtn) startVoiceBtn.classList.add("listening");
      };

      recognition.onresult = (event) => {
        let interim   = "";
        let finalText = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalText += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }

        const current = finalText || interim;
        if (current) voiceTranscriptPreview.textContent = current;

        if (finalText.trim()) {
          recognition.stop();
          voiceModal.classList.add("hidden");
          if (startVoiceBtn) startVoiceBtn.classList.remove("listening");

          // Route: if chatbot is open, answer in chatbot
          if (chatbotOpen) {
            appendChatUserMessage(finalText.trim());
            fetchChatbotResponse(finalText.trim());
          } else {
            askQuestion(finalText.trim());
          }
        }
      };

      recognition.onerror = (event) => {
        console.warn("Speech Recognition notice:", event.error);
        if (event.error === "no-speech") {
          voiceTranscriptPreview.textContent = "குரல் கேட்கவில்லை. மீண்டும் பேசுங்கள் அம்மா.";
        } else if (event.error === "not-allowed") {
          voiceTranscriptPreview.textContent = "மைக் அனுமதி தேவை. அனுமதி வழங்கவும்.";
        } else {
          voiceTranscriptPreview.textContent = "குரல் அறிவதில் சிரமம். எழுத்து மூலம் கேட்கலாம்.";
        }
        setTimeout(() => { if (isListening) stopListening(); }, 2200);
      };

      recognition.onend = () => {
        isListening = false;
        if (startVoiceBtn) startVoiceBtn.classList.remove("listening");
      };
    } catch (err) {
      console.warn("Speech recognition init notice:", err);
      recognition = null;
    }
  }

  function startListening(forChatbot = false) {
    stopSpeaking();
    if (recognition) {
      recognition.lang = VOICE_LANG_CODES[voiceLang] || "ta-IN";
      voiceModal.classList.remove("hidden");
      voiceTranscriptPreview.textContent = "தயாராகிறது... பேசுங்கள் அம்மா...";
      isListening = true;
      try { recognition.start(); } catch (e) { console.warn("Recognition start:", e); }
    } else {
      if (forChatbot) {
        // Fallback: focus text input in chatbot
        chatTextInput.focus();
      } else {
        typeInputContainer.classList.remove("hidden");
        typeInputContainer.removeAttribute("aria-hidden");
        textInputField.focus();
      }
    }
  }

  function stopListening() {
    if (recognition && isListening) {
      try { recognition.stop(); } catch (e) { console.warn("Recognition stop:", e); }
    }
    isListening = false;
    voiceModal.classList.add("hidden");
    if (startVoiceBtn) startVoiceBtn.classList.remove("listening");
  }

  function setVoiceLang(lang) {
    voiceLang = (lang === "en") ? "en" : "ta";
    if (recognition) recognition.lang = VOICE_LANG_CODES[voiceLang];
    document.querySelectorAll(".lang-btn").forEach(btn => {
      const on = btn.getAttribute("data-lang") === voiceLang;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    });
  }

  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => setVoiceLang(btn.getAttribute("data-lang")));
  });

  // =========================================================================
  // 4. SPEECH SYNTHESIS (TTS) — UNCHANGED
  // =========================================================================
  function speakText(textToSpeak) {
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();
    if (!textToSpeak || !textToSpeak.trim()) return;

    const clean = textToSpeak
      .replace(/[✓✅👉📞🚨🏛️🎁📝📍💰🙋‍♀️❌👍🏠🎤⌨️🔊⏹️✨🆓📋🔒🗣️🎙️💡🏡→←↓⌚]/g, "")
      .replace(/[*#_~]/g, "")
      .trim();

    const utterance  = new SpeechSynthesisUtterance(clean);
    utterance.lang   = "ta-IN";
    utterance.rate   = 0.9;
    utterance.pitch  = 1.0;

    const voices     = window.speechSynthesis.getVoices();
    const tamilVoice = voices.find(v => v.lang.includes("ta") || v.lang.includes("Tamil"));
    if (tamilVoice) utterance.voice = tamilVoice;

    utterance.onstart = () => {
      if (speakResponseBtn) speakResponseBtn.classList.add("hidden");
      if (stopResponseBtn)  stopResponseBtn.classList.remove("hidden");
    };

    utterance.onend = () => {
      if (speakResponseBtn) speakResponseBtn.classList.remove("hidden");
      if (stopResponseBtn)  stopResponseBtn.classList.add("hidden");
    };

    utterance.onerror = () => {
      if (speakResponseBtn) speakResponseBtn.classList.remove("hidden");
      if (stopResponseBtn)  stopResponseBtn.classList.add("hidden");
    };

    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    if (speakResponseBtn) speakResponseBtn.classList.remove("hidden");
    if (stopResponseBtn)  stopResponseBtn.classList.add("hidden");
  }

  if ("speechSynthesis" in window) {
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
  }

  // =========================================================================
  // 5. SCREEN TRANSITIONS — UNCHANGED
  // =========================================================================
  function showScreen(name) {
    stopSpeaking();
    stopListening();

    if (name === "welcome") {
      welcomeScreen.classList.add("active");
      answerScreen.classList.remove("active");
      window.scrollTo({ top: 0, behavior: "smooth" });

      // Re-trigger reveals
      setTimeout(() => {
        revealItems.forEach(el => {
          const r = el.getBoundingClientRect();
          if (r.top < window.innerHeight) el.classList.add("is-visible");
        });
      }, 100);
    } else if (name === "answer") {
      welcomeScreen.classList.remove("active");
      answerScreen.classList.add("active");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  // =========================================================================
  // 6. API CHAT — UNCHANGED
  // =========================================================================
  async function askQuestion(questionText) {
    if (!questionText || !questionText.trim()) return;

    const q = questionText.trim();
    showScreen("answer");

    userQuestionDisplay.textContent = q;
    loadingBox.classList.remove("hidden");
    responseCard.classList.add("hidden");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: q, language: "ta" })
      });

      if (!res.ok) throw new Error(`Server ${res.status}`);
      const data = await res.json();
      renderResponse(data);
    } catch (err) {
      console.error("API error, using local fallback:", err);
      renderFallbackResponse(q);
    }
  }

  function renderResponse(data) {
    loadingBox.classList.add("hidden");
    responseCard.classList.remove("hidden");

    responseTitle.textContent = data.title || "உஜ்வாலா கேஸ் திட்டம்";
    responseSummary.textContent = data.summary || "";

    responsePointsList.innerHTML = "";
    (data.points || []).forEach((pt, i) => {
      const li = document.createElement("li");
      li.textContent = pt;
      li.style.animationDelay = `${(i + 1) * 0.12}s`;
      responsePointsList.appendChild(li);
    });

    const nsb = nextStepText.closest(".next-step-box");
    if (data.next_steps) {
      nextStepText.textContent = data.next_steps;
      if (nsb) nsb.style.display = "";
    } else {
      if (nsb) nsb.style.display = "none";
    }

    suggestedButtonsGrid.innerHTML = "";
    const suggestions = data.suggested_questions || [
      "நான் தகுதியானவளா?",
      "என்ன ஆவணங்கள் வேண்டும்?",
      "எப்படி விண்ணப்பிப்பது?"
    ];

    suggestions.forEach(q => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "suggested-question-btn";
      btn.textContent = q;
      btn.addEventListener("click", () => askQuestion(q));
      suggestedButtonsGrid.appendChild(btn);
    });

    currentSpokenText = `${data.title || ""}. ${data.summary || ""}. ${(data.points || []).join(". ")}. அடுத்த படி: ${data.next_steps || ""}`;
  }

  function renderFallbackResponse(query) {
    loadingBox.classList.add("hidden");
    responseCard.classList.remove("hidden");

    responseTitle.textContent   = "உஜ்வாலா கேஸ் திட்டம் தகவல்";
    responseSummary.textContent = "அரசு வழங்கும் இலவச கேஸ் இணைப்பு (உஜ்வாலா திட்டம்) மூலம் ஏழை குடும்பப் பெண்கள் இலவச சிலிண்டர் மற்றும் அடுப்பு பெற்றுக்கொள்ளலாம்.";

    responsePointsList.innerHTML = `
      <li style="animation-delay:0.1s">18 வயது நிரம்பிய ஏழை பெண்கள் விண்ணப்பிக்கலாம்.</li>
      <li style="animation-delay:0.2s">ஆதார் அட்டை, ரேஷன் கார்டு மற்றும் வங்கி பாஸ்புக் நகல் தேவை.</li>
      <li style="animation-delay:0.3s">உங்கள் ஊர் கேஸ் ஏஜென்சியில் (பாரத் கேஸ் / இண்டேன் / ஹெச்பி) இலவசமாக விண்ணப்பிக்கலாம்.</li>
    `;

    nextStepText.textContent = "ஆவணங்களை எடுத்துக்கொண்டு அருகில் உள்ள கேஸ் கடைக்கு செல்லுங்கள் அம்மா.";
    const nsb = nextStepText.closest(".next-step-box");
    if (nsb) nsb.style.display = "";

    suggestedButtonsGrid.innerHTML = "";
    ["நான் தகுதியானவளா?", "என்ன ஆவணங்கள் வேண்டும்?", "எங்கு விண்ணப்பிப்பது?"].forEach(q => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "suggested-question-btn";
      btn.textContent = q;
      btn.addEventListener("click", () => askQuestion(q));
      suggestedButtonsGrid.appendChild(btn);
    });

    currentSpokenText = `${responseTitle.textContent}. ${responseSummary.textContent}. அடுத்த படி: ${nextStepText.textContent}`;
  }

  // =========================================================================
  // 7. FLOATING CHATBOT
  // =========================================================================
  function openChatbot() {
    chatbotOpen = true;
    chatbotToggle.setAttribute("aria-expanded", "true");
    chatbotWindow.setAttribute("aria-hidden", "false");
    chatbotWindow.classList.add("open");
    // Focus input after animation
    setTimeout(() => chatTextInput.focus(), 300);
  }

  function closeChatbot() {
    chatbotOpen = false;
    chatbotToggle.setAttribute("aria-expanded", "false");
    chatbotWindow.setAttribute("aria-hidden", "true");
    chatbotWindow.classList.remove("open");
  }

  chatbotToggle.addEventListener("click", () => {
    if (chatbotOpen) closeChatbot();
    else openChatbot();
  });

  chatbotClose.addEventListener("click", closeChatbot);

  // Chatbot send message
  function sendChatMessage(text) {
    if (!text || !text.trim()) return;
    const t = text.trim();
    appendChatUserMessage(t);
    chatTextInput.value = "";
    fetchChatbotResponse(t);
  }

  chatSendBtn.addEventListener("click", () => sendChatMessage(chatTextInput.value));
  chatTextInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendChatMessage(chatTextInput.value);
    }
  });

  chatVoiceBtn.addEventListener("click", () => startListening(true));

  function appendChatUserMessage(text) {
    const wrap = document.createElement("div");
    wrap.className = "cwm-user";
    const bubble = document.createElement("div");
    bubble.className = "cwm-bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendChatSakhiMessage(text) {
    const wrap = document.createElement("div");
    wrap.className = "cwm-sakhi";
    const bubble = document.createElement("div");
    bubble.className = "cwm-bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async function fetchChatbotResponse(question) {
    // Show typing indicator
    chatTyping.classList.remove("hidden");
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, language: "ta" })
      });

      if (!res.ok) throw new Error(`Server ${res.status}`);
      const data = await res.json();

      chatTyping.classList.add("hidden");

      const summary = data.summary || "";
      const points  = (data.points || []).slice(0, 2).join(" • ");
      const reply   = summary + (points ? "\n• " + points : "");

      appendChatSakhiMessage(reply || "மன்னிக்கவும், சற்று பிறகு கேட்கவும் அம்மா.");
    } catch (err) {
      chatTyping.classList.add("hidden");
      appendChatSakhiMessage("மன்னிக்கவும் அம்மா. இணைப்பு சிக்கல் உள்ளது. கீழே பொத்தானை அழுத்தி கேட்கலாம்.");
    }
  }

  // =========================================================================
  // 8. EVENT LISTENERS — ALL ORIGINAL BINDINGS PRESERVED
  // =========================================================================

  // Home / back
  homeBtn.addEventListener("click", () => showScreen("welcome"));
  backToHomeBtn.addEventListener("click", () => showScreen("welcome"));

  // Yes / No
  btnYes.addEventListener("click", () => askQuestion("ஆம்"));
  btnNo.addEventListener("click",  () => askQuestion("இல்லை"));

  // Voice button (existing id=startVoiceBtn — required by browser test)
  startVoiceBtn.addEventListener("click", () => startListening(false));
  speakAgainBtn.addEventListener("click", () => startListening(false));

  // Section-5 mic / type buttons (same voice & drawer flow)
  const s5VoiceBtn = document.getElementById("s5VoiceBtn");
  const s5TypeBtn  = document.getElementById("s5TypeBtn");
  if (s5VoiceBtn) s5VoiceBtn.addEventListener("click", () => startListening(false));
  if (s5TypeBtn) s5TypeBtn.addEventListener("click", () => {
    typeInputContainer.classList.remove("hidden");
    typeInputContainer.removeAttribute("aria-hidden");
    textInputField.focus();
    typeInputContainer.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  // Type drawer toggle
  showTypeBtn.addEventListener("click", () => {
    const isHidden = typeInputContainer.classList.contains("hidden");
    typeInputContainer.classList.toggle("hidden");
    typeInputContainer.setAttribute("aria-hidden", String(!isHidden));
    if (isHidden) {
      textInputField.focus();
      typeInputContainer.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  closeTypeBtn.addEventListener("click", () => {
    typeInputContainer.classList.add("hidden");
    typeInputContainer.setAttribute("aria-hidden", "true");
  });

  // Text form (existing id=textQueryForm)
  textQueryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = textInputField.value.trim();
    if (q) {
      textInputField.value = "";
      typeInputContainer.classList.add("hidden");
      typeInputContainer.setAttribute("aria-hidden", "true");
      askQuestion(q);
    }
  });

  // Six guided question buttons (existing data-query attr)
  document.querySelectorAll(".guide-card").forEach(btn => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-query");
      if (q) askQuestion(q);
    });
  });

  // Real-life help cards (section 2): expand in place, load verified docs once
  let helpDocsLoaded = false;

  async function loadVerifiedDocs() {
    const list = document.getElementById("helpDocsList");
    if (!list) return;
    list.innerHTML = "";
    const loading = document.createElement("li");
    loading.className = "hc-loading";
    loading.textContent = "தகவல் பெறப்படுகிறது…";
    list.appendChild(loading);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "என்ன ஆவணங்கள் வேண்டும்?", language: "ta" })
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      const data = await res.json();
      const pts = (data && Array.isArray(data.points)) ? data.points : [];
      if (!pts.length) throw new Error("no points");
      list.innerHTML = "";
      pts.forEach(p => {
        const li = document.createElement("li");
        li.textContent = p;
        list.appendChild(li);
      });
    } catch (err) {
      list.innerHTML = "";
      const li = document.createElement("li");
      li.className = "hc-loading";
      li.textContent = "ஆவணத் தகவலை அதிகாரப்பூர்வ இணையதளத்தில் பார்க்கவும்.";
      list.appendChild(li);
      helpDocsLoaded = false;
    }
  }

  document.querySelectorAll(".help-card-head").forEach(head => {
    head.addEventListener("click", () => {
      const card = head.closest(".help-card");
      if (!card) return;
      const open = head.getAttribute("aria-expanded") === "true";
      head.setAttribute("aria-expanded", String(!open));
      card.classList.toggle("open", !open);
      if (!open && head.hasAttribute("data-docs") && !helpDocsLoaded) {
        helpDocsLoaded = true;
        loadVerifiedDocs();
      }
    });
  });

  // Click / Enter / Space → glitter frame + big view (Kural card & hero portrait)
  function wireGlitterZoom(el, bigClass) {
    if (!el) return;
    const toggle = () => {
      const on = el.classList.toggle("glitter");
      el.classList.toggle(bigClass, on);
      el.setAttribute("aria-pressed", String(on));
    };
    el.addEventListener("click", toggle);
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });
  }
  wireGlitterZoom(document.getElementById("kuralCard"), "kc-big");
  wireGlitterZoom(document.getElementById("humanVisual"), "hv-big");

  // TTS buttons
  speakResponseBtn.addEventListener("click", () => speakText(currentSpokenText));
  stopResponseBtn.addEventListener("click",  () => stopSpeaking());

  // Voice modal cancel
  cancelVoiceBtn.addEventListener("click", () => stopListening());
  voiceModal.addEventListener("click", (e) => {
    if (e.target === voiceModal) stopListening();
  });

  // Escape closes chatbot or voice modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (isListening) stopListening();
      if (chatbotOpen) closeChatbot();
    }
  });

  // =========================================================================
  // 8b. DRAGGABLE BIG AI ORB (section 3) — pointer events, mouse + touch
  // =========================================================================
  const bigAiOrb = document.querySelector(".big-ai-orb");
  const orbSection = document.getElementById("section3");
  if (bigAiOrb && orbSection) {
    let orbDragging = false;
    let orbMoved = false;
    let startX = 0, startY = 0;
    let baseX = 0, baseY = 0;   // translate committed at drag start
    let curX = 0, curY = 0;     // live translate (persists after release)
    let minX = 0, maxX = 0, minY = 0, maxY = 0;
    const DRAG_THRESHOLD = 6;
    const PAD = 8;

    function applyOrbTransform() {
      bigAiOrb.style.transform = `translate(${curX}px, ${curY}px)`;
    }

    function onOrbDown(e) {
      orbDragging = true;
      orbMoved = false;
      startX = e.clientX;
      startY = e.clientY;
      baseX = curX;
      baseY = curY;

      const oRect = bigAiOrb.getBoundingClientRect();
      const sRect = orbSection.getBoundingClientRect();
      const naturalLeft = oRect.left - curX;
      const naturalTop = oRect.top - curY;
      minX = (sRect.left + PAD) - naturalLeft;
      maxX = (sRect.right - PAD) - (naturalLeft + oRect.width);
      minY = (sRect.top + PAD) - naturalTop;
      maxY = (sRect.bottom - PAD) - (naturalTop + oRect.height);

      try { bigAiOrb.setPointerCapture(e.pointerId); } catch (_) {}
      bigAiOrb.classList.add("dragging");
      e.preventDefault();
    }

    function onOrbMove(e) {
      if (!orbDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (!orbMoved && Math.hypot(dx, dy) > DRAG_THRESHOLD) orbMoved = true;
      curX = Math.min(Math.max(baseX + dx, minX), maxX);
      curY = Math.min(Math.max(baseY + dy, minY), maxY);
      applyOrbTransform();
      e.preventDefault();
    }

    function onOrbUp(e) {
      if (!orbDragging) return;
      orbDragging = false;
      bigAiOrb.classList.remove("dragging");
      try { bigAiOrb.releasePointerCapture(e.pointerId); } catch (_) {}
      if (!orbMoved) openChatbot();   // simple click → existing chatbot
    }

    bigAiOrb.style.touchAction = "none";
    bigAiOrb.addEventListener("pointerdown", onOrbDown);
    bigAiOrb.addEventListener("pointermove", onOrbMove);
    bigAiOrb.addEventListener("pointerup", onOrbUp);
    bigAiOrb.addEventListener("pointercancel", onOrbUp);
  }

  // =========================================================================
  // 9. INITIAL REVEAL CHECK
  // =========================================================================
  setTimeout(() => {
    revealItems.forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.top < window.innerHeight * 0.9) el.classList.add("is-visible");
    });
  }, 100);

});
