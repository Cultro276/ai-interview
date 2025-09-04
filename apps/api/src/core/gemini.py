import os
from typing import List

from anyio import to_thread

from src.core.config import settings
from src.services.prompt_registry import RECRUITER_PERSONA as PR_PERSONA, build_role_guidance_block as PR_ROLE_BLOCK


# --- Dynamic import for new client API ---
try:
    from google import genai  # type: ignore

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


GEMINI_API_KEY = settings.gemini_api_key
MODEL_NAME = "gemini-2.5-flash"

# Advanced LLM-driven recruiter persona with intelligent question diversity
RECRUITER_PERSONA = (
    "Sen deneyimli Türk İK uzmanı 'Ece'sin. Profesyonel, objektif ve analitik yaklaşımla mülakat yaparsın. "
    "Amacın: Adayları iş gereksinimlerine göre adil ama kritik bir şekilde DEĞERLENDİRMEK. "
    "Kişiliğin: Doğrudan, profesyonel ve tarafsız - aşırı pozitif veya negatif değil. "
    
    "🎯 SORU ÇEŞİTLİLİĞİ VE AKILLI KONUŞMA YÖNETİMİ:"
    "- Her soru FARKLI bir yetkinlik alanını keşfetmeli (teknik, davranışsal, liderlik, problem çözme, takım çalışması, iletişim vb.)"
    "- Önceki sorulardan TAMAMEN farklı konular seç - aynı temaları tekrarlama"
    "- Soru tiplerini akıllıca değiştir: somut örnek → durum analizi → varsayımsal senaryo → derinlemesine sondaj"
    "- Konuşma akışını doğal tut: 'anladım', 'peki', 'tamam' gibi kısa geçişler kullan ama doğal olsun"
    
    "🔍 SOMUT ÖRNEK ÇIKARMA TEKNİKLERİ:"
    "- Belirsiz cevaplara karşı derhal sonda: 'Nasıl ölçtünüz bu sonucu?', 'Hangi zorluklar yaşadınız?', 'Kim dahil oldu bu sürece?'"
    "- STAR metodunu doğal şekilde çıkar ama hiç söyleme - sadece soruların sonuçta STAR çıkartacak şekilde tasarla"
    "- Her cevap için en az 2-3 follow-up soru hazırla zihninde"
    
    "❌ YASAKLAR:"
    "- 'Güzel', 'harika', 'mükemmel', 'çok iyi' gibi aşırı övgü YASAK"
    "- Aynı konuyu tekrar sormak YASAK (örn: iki kez takım çalışması sormak)"
    "- Genel sorular sormak YASAK (örn: 'Bir örnek verir misiniz?')"
    "- CV'de olmayan deneyimler hakkında sormak YASAK"
    
    "⚡ İLETİŞİM TARZI:"
    "- Cinsiyet-tarafsız hitap et, hiçbir varsayımda bulunma"
    "- Profesyonel İK dili kullan: 'somut örnek verebilir misiniz', 'nasıl yaklaştınız', 'hangi yöntemleri kullandınız'"
    "- Dinlediğini göster: kısa onaylamalarla geçiş yap"
    "- Eksik deneyim varsa transferable skills keşfet ama profili yapay olarak yükseltme"
)


def _sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50):
    """Blocking Gemini request executed in a thread."""

    if not _GENAI_AVAILABLE:
        raise RuntimeError("google-ai-python library not installed (pip install google-ai-python)")

    from google import genai as _genai  # type: ignore
    client = _genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = (
        PR_PERSONA +
        "\n\n🎯 AKILLI MÜLAKAT STRATEJISI - LLM ODAKLI YAKLAŞIM:"
        "Sen bu mülakatı OBJEKTIF DEĞERLENDİRME amacıyla yürütüyorsun. Yaklaşımın analitik olmalı, cesaretlendirici değil. Güçlü yanları VE eksikleri tespit etmeye odaklan. "
        
        "\n📋 KONUŞMA AKIŞI VE ÇEŞİTLİLİK KONTROLÜ:"
        "- Geçmiş konuşmayı analiz et: Hangi yetkinlik alanları keşfedildi? Hangileri eksik?"
        "- Her yeni soru FARKLI bir alanı kapsamalı: teknik beceriler → problem çözme → takım dinamikleri → liderlik → iletişim → stres yönetimi vb."
        "- Soru formatlarını zekice değiştir: deneyim sorusu → varsayımsal durum → somut örnek isteme → derinlemesine sondaj"
        "- Aynı temaları tekrarlama - örneğin zaten takım çalışması sorduğun konuyu tekrar açma"
        
        "\n🔍 CV-İŞ UYUM ANALİZİ (KRİTİK):"
        "- Deneyim soruları sormadan ÖNCE, CV'de o alanda deneyim var mı kontrol et"
        "- CV'de olmayan sektörler/domainler hakkında 'hangi projede zorlandınız' gibi sorular YASAK"
        "- Sektör uyumsuzluğu varsa açık sor: 'Bu pozisyon [sektör] deneyimi gerektiriyor, bu alanda deneyiminiz var mı?'"
        "- CV'deki gerçek deneyimi iş gereksinimlerini karşılaştır, eksiklikler varsa doğrudan sonda"
        
        "\n💡 SORU ÖRNEKLERİ VE TEKNİKLER:"
        "- Durum yaratma: 'Diyelim ki [iş senaryosu], bu durumda nasıl hareket edersiniz?'"
        "- Zorlukları keşfet: 'X alanındaki deneyiminizden en zorlandığınız durum neydi?' (sadece CV'de olan alanlarda!)"
        "- Belirsiz cevapları sonda: Eğer 'takım çalışması yaptım' derse → 'Nasıl çatışmaları çözdünüz?', 'Hangi roller üstlendiniz?'"
        "- Somut kanıt iste: 'Sonuçları nasıl ölçtünüz?', 'Hangi metrikleri kullandınız?', 'Timeline nasıldı?'"
        
        "\n⏰ MÜLAKAT ZAMANLAMA:"
        "- En az 5-6 derinlemesine yetkinlik sorusu sor (farklı alanlarda)"
        "- Sonra maaş beklentisini sor: 'Maaş beklentiniz nedir?'"
        "- Maaş sorusunu çok erken sorma (5 sorudan önce)"
        "- Tüm temel yetkinlikleri değerlendirdikten VE maaş sorusunu sorduktan sonra 'FINISHED' yaz"
        
        "\n🚫 KESIN YASAKLAR:"
        "- CV'de açıkça yazılmayan şeylerden bahsetme: 'Özgeçmişinizde X görüyorum' deme (eğer X gerçekten yazılı değilse)"
        "- Aşırı övgü YASAK: 'güzel', 'harika', 'mükemmel' kelimelerini kullanma"
        "- Konu dışına çıkma - rol, iş tanımı, yetkinliklere odaklan"
        "- Cinsiyet varsayımları yapma - herkese tarafsız hitap et"
        
        "\n🎪 AKILLI KONUŞMA YÖNETİMİ:"
        "- Kısa doğal geçişler kullan: 'anladım', 'peki', 'tamam' - ama abartma"
        "- Dinlediğini göster ama sonra yeni konuya geç"
        "- Transferable skills keşfet ama profili yapay olarak yükseltme"
        "- Profesyonel İK dili kullan: 'somut örnek', 'nasıl yaklaştınız', 'hangi yöntemleri kullandınız'"
    )
    if job_context:
        # Accept larger context to include full resume and extras (no truncation here; upstream controls size)
        system_prompt += (
            "\n\nContext (job description, full resume, and extra questions):\n" + job_context
        )
        # Inject role guidance if we can detect the role from job description
        try:
            system_prompt += "\n\n" + PR_ROLE_BLOCK(job_context)
        except Exception:
            pass

    convo_text = system_prompt + "\n\n"
    for turn in history:
        prefix = "Candidate:" if turn["role"] == "user" else "Interviewer:"
        convo_text += f"{prefix} {turn['text']}\n"
    convo_text += "Interviewer:"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=convo_text,
        # Note: current google-genai client does not support generation_config param
    )

    text = (response.text or "").strip()
    if text.upper().strip() == "FINISHED":
        return {"question": "", "done": True}
    return {"question": text, "done": False}


def _fallback_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50) -> dict[str, str | bool]:
    """Deterministic local fallback when Gemini is not configured.

    Prioritizes job-specific scenarios, then falls back to generic questions.
    """
    # Try to extract job description for dynamic scenarios
    job_desc = ""
    if job_context:
        # Look for job description in context
        lines = job_context.split('\n')
        for line in lines:
            if 'İş Tanımı:' in line or 'Job Description:' in line:
                job_desc = line.split(':', 1)[1].strip() if ':' in line else ""
                break
        if not job_desc and job_context:
            # Use first part of context as job description
            job_desc = job_context.split('\n')[0][:1000]
    
    # Prefer resume-keyword targeted canned questions if available in job_context  
    def _extract_keywords_from_ctx(ctx: str) -> list[str]:
        import re as _re
        # Expect a line like: Internal Resume Keywords: kw1, kw2, kw3
        m = _re.search(r"Internal Resume Keywords:\s*(.+)", ctx or "", flags=_re.IGNORECASE)
        if not m:
            return []
        part = m.group(1)
        kws = [t.strip() for t in part.split(",") if t.strip()]
        return kws[:6]

    targeted: list[str] = []
    kws = _extract_keywords_from_ctx(job_context or "") if job_context else []
    for k in kws:
        targeted.append(f"Özgeçmişinizde '{k}' geçmiş. Bu konuda hangi problemi nasıl çözdünüz ve ölçülebilir sonuç neydi?")
    
    # Job-specific scenarios (this would be populated from dynamic generation in real usage)
    job_specific_scenarios: list[str] = []
    
    # Fallback generic situational scenarios
    generic_situational_questions = [
        "Diyelim ki ekibinizde çatışma yaşayan iki meslektaşınız var ve bu durum projeyi etkiliyor. Bu durumda nasıl müdahale edersiniz?",
        "Sıkı bir deadline'ınız var ama projenin kalitesinden ödün vermek istemiyorsunuz. Öncelikleri nasıl belirlersiniz?",
        "Yeni bir teknoloji öğrenmeniz gereken acil bir proje verildi. Nasıl yaklaşırsınız?",
        "Bir projede beklediğiniz sonuçları alamadığınız bir dönem yaşadınız mı? Bu durumu nasıl çözdünüz?",
        "İş arkadaşlarınızdan birinin sürekli geç kaldığı ve ekip performansını etkilediği bir durumla karşılaştınız mı? Nasıl ele aldınız?",
        "Daha önce hiç yapmadığınız bir işi teslim etmeniz gerektiği bir durumda neler yaptınız?",
        "Müşteri/kullanıcı şikayetleri aldığınız bir projede nasıl hareket ettiniz?",
        "Kaynakların kısıtlı olduğu bir projede nasıl çözüm ürettiniz?",
    ]
    
    # Mix targeted, job-specific, and generic questions in priority order
    canned = targeted + job_specific_scenarios + generic_situational_questions + [
        "Özgeçmişinizde öne çıkan bir proje/başarıyı STAR çerçevesinde kısaca anlatır mısınız?",
        "Son rolünüzde somut bir katkınızı ve sonucunu paylaşır mısınız?",
    ]
    asked = sum(1 for t in history if t.get("role") == "assistant")
    # Respect hard question limit first
    if asked < len(canned):
        return {"question": canned[asked], "done": False}
    # Keep going without finishing: vary phrasing slightly
    return {"question": "Özgeçmişinizden başka bir proje veya başarıyı kısaca STAR çerçevesinde paylaşır mısınız?", "done": False}


async def generate_question(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7) -> dict[str, str | bool]:
    # If API key or library missing, use fallback for smooth local dev
    if not GEMINI_API_KEY or not _GENAI_AVAILABLE:
        return _fallback_generate(history, job_context, max_questions)

    try:
        return await to_thread.run_sync(_sync_generate, history, job_context, max_questions)
    except Exception:
        # Last-resort fallback
        return _fallback_generate(history, job_context, max_questions)


async def polish_question(text: str) -> str:
    """Optionally send the generated question to the LLM to smooth tone.

    Kept optional with strict fallback to original text.
    """
    if not GEMINI_API_KEY or not _GENAI_AVAILABLE:
        return text
    try:
        def _sync(t: str):
            from google import genai as _genai  # type: ignore
            client = _genai.Client(api_key=GEMINI_API_KEY)
            prompt = (
                "Aşağıdaki soruyu Türkçe, kısa ve doğal bir üslupla nazikçe yeniden yaz.\n"
                "Tek cümle ve soru işaretiyle bitir. Yapay ve mekanik duygudan kaçın, hafif insansı ton kat:\n\n" + t
            )
            resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            cleaned = (resp.text or t).strip()
            return cleaned or t
        return await to_thread.run_sync(_sync, text)
    except Exception:
        return text


# --- OpenAI fallback (HTTP) ---

def _openai_sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50) -> dict[str, str | bool]:
    """Blocking OpenAI request executed in a thread (chat.completions)."""
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    import httpx  # local import to avoid import when unused

    system_prompt = (
        RECRUITER_PERSONA +
        "\n\n🎯 AKILLI MÜLAKAT STRATEJISI - LLM ODAKLI YAKLAŞIM:"
        "Sen bu mülakatı OBJEKTIF DEĞERLENDİRME amacıyla yürütüyorsun. Yaklaşımın analitik olmalı, cesaretlendirici değil. Güçlü yanları VE eksikleri tespit etmeye odaklan. "
        
        "\n📋 KONUŞMA AKIŞI VE ÇEŞİTLİLİK KONTROLÜ:"
        "- Geçmiş konuşmayı analiz et: Hangi yetkinlik alanları keşfedildi? Hangileri eksik?"
        "- Her yeni soru FARKLI bir alanı kapsamalı: teknik beceriler → problem çözme → takım dinamikleri → liderlik → iletişim → stres yönetimi vb."
        "- Soru formatlarını zekice değiştir: deneyim sorusu → varsayımsal durum → somut örnek isteme → derinlemesine sondaj"
        "- Aynı temaları tekrarlama - örneğin zaten takım çalışması sorduğun konuyu tekrar açma"
        
        "\n🔍 CV-İŞ UYUM ANALİZİ (KRİTİK):"
        "- Deneyim soruları sormadan ÖNCE, CV'de o alanda deneyim var mı kontrol et"
        "- CV'de olmayan sektörler/domainler hakkında 'hangi projede zorlandınız' gibi sorular YASAK"
        "- Sektör uyumsuzluğu varsa açık sor: 'Bu pozisyon [sektör] deneyimi gerektiriyor, bu alanda deneyiminiz var mı?'"
        "- CV'deki gerçek deneyimi iş gereksinimlerini karşılaştır, eksiklikler varsa doğrudan sonda"
        
        "\n💡 SORU ÖRNEKLERİ VE TEKNİKLER:"
        "- Durum yaratma: 'Diyelim ki [iş senaryosu], bu durumda nasıl hareket edersiniz?'"
        "- Zorlukları keşfet: 'X alanındaki deneyiminizden en zorlandığınız durum neydi?' (sadece CV'de olan alanlarda!)"
        "- Belirsiz cevapları sonda: Eğer 'takım çalışması yaptım' derse → 'Nasıl çatışmaları çözdünüz?', 'Hangi roller üstlendiniz?'"
        "- Somut kanıt iste: 'Sonuçları nasıl ölçtünüz?', 'Hangi metrikleri kullandınız?', 'Timeline nasıldı?'"
        
        "\n⏰ MÜLAKAT ZAMANLAMA:"
        "- En az 5-6 derinlemesine yetkinlik sorusu sor (farklı alanlarda)"
        "- Sonra maaş beklentisini sor: 'Maaş beklentiniz nedir?'"
        "- Maaş sorusunu çok erken sorma (5 sorudan önce)"
        "- Tüm temel yetkinlikleri değerlendirdikten VE maaş sorusunu sorduktan sonra 'FINISHED' yaz"
        
        "\n🚫 KESIN YASAKLAR:"
        "- CV'de açıkça yazılmayan şeylerden bahsetme: 'Özgeçmişinizde X görüyorum' deme (eğer X gerçekten yazılı değilse)"
        "- Aşırı övgü YASAK: 'güzel', 'harika', 'mükemmel' kelimelerini kullanma"
        "- Konu dışına çıkma - rol, iş tanımı, yetkinliklere odaklan"
        "- Cinsiyet varsayımları yapma - herkese tarafsız hitap et"
        
        "\n🎪 AKILLI KONUŞMA YÖNETİMİ:"
        "- Kısa doğal geçişler kullan: 'anladım', 'peki', 'tamam' - ama abartma"
        "- Dinlediğini göster ama sonra yeni konuya geç"
        "- Transferable skills keşfet ama profili yapay olarak yükseltme"
        "- Profesyonel İK dili kullan: 'somut örnek', 'nasıl yaklaştınız', 'hangi yöntemleri kullandınız'"
    )
    if job_context:
        system_prompt += ("\n\nContext (job description and full resume text may be included):\n" + job_context[:8000])

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3,
        # Allow longer, fully-formed questions (prevents truncation)
        "max_tokens": 220,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=5.0) as client:
        resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    text = (data.get("choices", [{}])[0].get("message", {}).get("content", "").strip())
    if text.upper().strip() == "FINISHED":
        return {"question": "", "done": True}
    return {"question": text, "done": False}


async def generate_question_robust(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7, total_timeout_s: float = 5.0) -> dict[str, str | bool]:
    """Two-tier LLM strategy: OpenAI first, then Gemini; last resort local canned.

    OpenAI (gpt-4o-mini) is preferred for lower latency and Turkish fluency; Gemini remains as backup.
    """
    # 1) OpenAI (preferred)
    try:
        return await to_thread.run_sync(_openai_sync_generate, history, job_context, max_questions)
    except Exception:
        pass

    # 2) Gemini (backup)
    try:
        return await to_thread.run_sync(_sync_generate, history, job_context, max_questions)
    except Exception:
        pass

    # 3) Local canned
    return _fallback_generate(history, job_context, max_questions)


def _fallback_requirements(text: str) -> dict:
    # Deprecated: manual requirements/rubric extraction removed
    return {}


async def extract_requirements_from_text(text: str) -> dict:
    """Deprecated helper kept for compatibility; returns empty config."""
    return {}


async def generate_job_specific_scenarios(job_desc: str) -> list[str]:
    """Generate situational interview questions based on job description requirements."""
    from src.core.config import settings
    if not (settings.openai_api_key and job_desc.strip()):
        return []
    
    import httpx
    
    prompt = f"""İş tanımını analiz et ve bu pozisyonda GERÇEKTEN yaşanabilecek spesifik durumları konu alan sorular oluştur.

İş Tanımı: {job_desc[:3000]}

GÖREV: Bu işte çalışan birinin karşılaşabileceği 5-6 gerçekçi durum sorusu yaz.

ZORUNLU KURALLAR:
1. Her soru o işin GÜNLÜK GERÇEKLİĞİNDEN alınmalı (müşteri, takım, süreç, problem çözme)
2. Soru formatı: "Bu işte [spesifik durum]. Nasıl yaklaşırsınız?" 
3. Her soru farklı yetkinliği test etmeli (müşteri ilişkisi, problem çözme, stres yönetimi, takım çalışması, öncelik belirleme)
4. YASAKLI: E-posta, araç sorular, özgeçmiş soruları, genel yaklaşım soruları

ÖRNEK KALITE (Satış Danışmanı için):
✓ "Müşteri beğendiği ürünün fiyatını çok yüksek bulduğunu söylüyor ve gitmek istiyor. Nasıl yaklaşırsınız?"
✗ "Hangi iletişim yöntemlerini kullanırsınız?" (çok genel)

Sadece soru listesi dön, başka yazma."""
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # Extract questions from content
            lines = content.split('\n')
            questions = []
            for line in lines:
                line = line.strip()
                if line and ('diyelim ki' in line.lower() or 'diyelim' in line.lower()):
                    # Remove bullet points, numbers, etc.
                    clean_line = line.lstrip('- •*123456789.').strip()
                    if clean_line:
                        questions.append(clean_line)
            
            return questions[:8]  # Max 8 questions
    except Exception:
        return []