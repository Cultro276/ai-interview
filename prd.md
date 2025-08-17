# Hirevision - AI-Powered Hiring Platform

## Proje Özeti
Hirevision, yapay zeka destekli mülakat sistemi ile işe alım sürecini otomatikleştiren bir platformdur. İşe alımcılar iş ilanı oluşturur, CV'leri toplu olarak yükler ve sistem otomatik olarak adaylara mülakat linkleri gönderir. Adaylar video mülakat yapar, sistem kayıtları analiz eder ve detaylı raporlar üretir.

## Temel Özellikler
- **AI Destekli Mülakat Sistemi**: Ses/video kayıt, gerçek zamanlı transkript, AI soru-cevap, çok dilli destek
- **Aday Yönetimi**: Toplu CV yükleme, profil analizi, AI değerlendirme, rıza yönetimi
- **İş Yönetimi**: İş ilanı oluşturma, aday eşleştirme, süreç takibi
- **Mülakat Takibi**: Kayıtlar, transkriptler, AI analiz raporları
- **Admin Paneli**: Dashboard, istatistikler, raporlama

## Teknik Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Next.js (React/TypeScript)
- **Veritabanı**: PostgreSQL
- **Dosya Depolama**: AWS S3
- **Container**: Docker
- **Monorepo**: Turbo

## Mevcut Durum
- ✅ Temel CRUD işlemleri
- ✅ Kullanıcı authentication
- ✅ Multi-tenancy (veri izolasyonu)
- ✅ Dosya upload sistemi
- ✅ Admin paneli
- ✅ Mülakat kayıt sistemi (dev modunda presign stub ile çalışır)
- ✅ Konuşma ve rule‑based analiz (otomatik, aday tamamladıktan sonra)

---

## Hirevision Detaylı Yol Haritası (2025 Q3–Q4)

### Vizyon ve Hedef
- **Amaç**: İşe alım sürecinde mülakatı veri odaklı, hızlı ve güvenilir hale getirmek; işe alımcının kararı için "kanıtlı" içgörü üretmek.
- **Varsayım**: Geliştirme/pilotta `Gemini 2.5 Flash (free)`; canlıda daha güçlü modele (örn. Gemini 2.5 Pro) geçiş.
- **Başarı ölçütleri (12 hafta)**:
  - P95 analiz süresi ≤ 60 sn, P95 upload ≤ 10 sn
  - TR WER ≤ %12; otomatik noktalama/paragraflama
  - Tamamlama oranı ≥ %85, panel ilk anlamlı içerik ≤ 2 sn
  - Analiz JSON'u %100 şemaya uygun ve "kanıt‑alıntı (offset)" içerir

---

## Vizyon (E2E Otomasyon)
- İşe alımcı yalnızca iş ilanını açar ve CV'leri yükler; sistem aday e‑postalarını bulur, süreli linkleri gönderir, adaylar o ilana özel akışla video mülakata girer, kayıt → transcript → job‑spesifik AI analiz raporu üretir; işe alımcı tüm raporları panel içinde görür.

### Uçtan Uca Akış
- İş ilanı → CV toplu/tekil yükleme → e‑posta çıkarımı → süreli token'lı linklerin gönderimi → aday cihaz/izin testi → ilan bağlamlı akışta mülakat → medya yükleme (chunked) → transcript (TR odaklı) → job‑spesifik AI analiz (kanıt‑alıntılı) → panel içi raporlar (aday/iş) → webhook/entegrasyonlar (opsiyonel).

### Sistem Mimarisi (Bileşenler)
- **CV İçe Aktarım Servisi**: PDF/DOC/TXT parse, e‑posta çıkarımı, kalite kontrol, "eksik e‑posta" durumunda manuel girme.
- **Davet/Token Servisi**: tek‑kullanımlık token, süre + sayfa görüntüleme sınırı; re‑send/expire/extend akışları; rate‑limit.
- **Aday İstemcisi**: cihaz testi, izin yönetimi, MediaRecorder optimizasyonları (bitrate/fps/keyframe), bağlantı dayanımı.
- **Upload Servisi**: presigned S3 (chunked), kaldığı yerden devam, checksum; P95 upload < 10 sn hedef.
- **ASR Pipeline**: VAD + gürültü azaltma → TR ASR sağlayıcı seçimi (AWS/Google/Deepgram) + domain sözlüğü → noktalama/paragraflama → diarization (opsiyon).
- **Analiz Motoru**: `Gemini 2.5 Flash (free)` ile "evidence‑first" JSON; job‑spesifik rubric/coverage; guardrails (schema/limits/retry).
- **Raporlama UI**: aday raporu (Summary/Scores/Evidence/Timeline), iş panoları (karşılaştırma/ısı haritası/filtre).
- **İzleme/Alarm**: upload/ASR/LLM latency & error, maliyet panosu; alarm eşikleri.
- **Güvenlik/KVKK**: aydınlatma/rıza ekranı + denetim logları + otomatik silme; TR veri yerelleştirme opsiyonu tek sayfalık teklif.

### Fonksiyonel Gereksinimler (Detay)
- **İş İlanı**
  - İş tanımı, gereksinimler → "job‑spesifik rubric" ve "mülakat planı" otomatik üretimi (AI).
- **CV İçe Aktarma**
  - Toplu/tekil; e‑posta regex + header/metadata fallback; "yoksa manuel gir" akışı.
  - Duplicate/format kontrolleri; tenant bazlı e‑posta benzersizliği.
- **Davet & Token**
  - Per‑candidate süre (örn. 7 gün), ilk tıklamada aktif, tek cihaz/tek seans sınırı (yapılandırılabilir).
  - E‑posta sağlayıcı (SES/Sendgrid) + SPF/DKIM; bounce/suppress list; kişiye özel şablon.
- **Aday Mülakatı**
  - İlan bağlamı: AI, iş tanımı + CV + önceki yanıtlarla dinamik sorular.
  - Kesintide devam; izin/cihaz testi; test kaydı 10 sn.
- **Medya & Upload**
  - Presigned chunked S3; parça boyutu uyarlanır; hatada retry/backoff; P95 < 10 sn.
- **Transcript (TR Odak)**
  - VAD + noise reduction; sağlayıcı benchmark; sözlük (şirket/pozisyon terimleri).
  - Noktalama/paragraflama; (opsiyonel) konuşmacı ayrımı.
- **AI Analiz (Evidence‑First)**
  - JSON şeması: summary, strengths, weaknesses, competence scores (communication/technical/problem‑solving/culture), risk flags, "önerilen karar", coverage listesi.
  - Kanıt‑alıntılar: transcript offset'leri; coverage check (gereksinimlerden kapsananlar).
  - Guardrails: schema validation, token/temperature sınırı, retry/backoff, idempotency; prompt sürümleme.
- **Panel İçi Raporlar**
  - Aday raporu: 4 sekme; highlight'lı kanıt; re‑run analysis; versiyon/metrik görünümü.
  - İş panoları: heatmap/karşılaştırma, skor dağılımı, tamamlama süreleri, kaydedilebilir filtreler.
  - Hız: FMP ≤ 2 sn; 200 aday kartında akıcı scroll (virtualization).
- **Güvenlik/KVKK**
  - Rıza/aydınlatma ekranı zorunlu; saklama (default 180 gün) + otomatik purge.
  - Erişim/indirme/export audit; S3/KMS + TLS; token hırsızlığı mitigation (kısa TTL + IP/UA bağlama opsiyonu).
- **Entegrasyon (Opsiyonel)**
  - Webhook (analysis_ready); CSV/JSON export; sonraki aşama SSO ve ATS konektörleri.

### Performans & Kalite Hedefleri
- P95 analiz ≤ 60 sn; P95 upload ≤ 10 sn; transcript WER (TR) ≤ %12; panel render ≤ 2 sn.
- JSON validity %100; kanıt‑alıntı ≥ 5; job coverage puanı raporlanır.
- Tamamlama oranı ≥ %85; hata oranı ≤ %1; maliyet/aday (dev) < $0.6, (canlı hedef) < $0.3.

---

## Sprint Planı (12 Hafta / 6 Sprint)

### Sprint 1: Yakalama & ASR Temel
- MediaRecorder tuning; chunked S3 upload + retry/backoff; VAD + noise reduction; TR ASR benchmark (WER/noktalama/latency tablosu); metrik endpoint'leri.
- **DoD**: P95 upload ≤ 15 sn başlangıç; benchmark raporu hazır.

### Sprint 2: Analiz JSON v1 + Panel (Beta)
- Evidence‑first prompt + JSON schema + guardrails; konuşma metrikleri (talk ratio/wpm/filler).
- Aday raporu (Summary/Scores/Evidence minimal); re‑run analysis; versiyon/meta loglama.
- **DoD**: JSON %100 valid; re‑run çalışıyor; P95 analiz ≤ 75 sn.

### Sprint 3: İş Panoları + Coverage
- Heatmap/karşılaştırma; transcript arama & kanıt highlight pairing; job requirement coverage hesaplama.
- **DoD**: 200 adayda akıcı render; P95 analiz ≤ 60 sn.

### Sprint 4: Davet/Token & E‑posta Kalitesi
- Token TTL/tek seans/IP/UA bağlama; bounce/suppress; re‑send; link uzatma.
- E‑posta şablonları (kişisel, iş başlığı bağlamlı); deliverability ölçümü.
- **DoD**: Davet gönderimi %99 başarı; deliverability > %95.

### Sprint 5: KVKK & Audit & Otomatik Silme
- Rıza/aydınlatma; denetim logları (görüntüleme/indirme/export); retention job (180g).
- **DoD**: otomatik purge çalışır; tüm erişimler audit'lenir; güvenlik dokümanı güncel.

### Sprint 6: Pilot & ROI
- 3–5 pilot müşteri; ROI raporu (tamamlama, süre, skor dağılımı, önerilen karar doğruluğu).
- Model upgrade değerlendirmesi (Gemini Pro/alternatif), geçiş planı.

---

## Kabul Ölçütleri (DoD)
- Her mülakat için: transcript + JSON analiz + en az 5 kanıt‑alıntı + coverage raporu + P95 süre hedefleri sağlanmış.
- İş panosu: sıralama/filtreleme/karşılaştırma akıcı; kaydedilebilir görünüm; 200 adayda performans iyi.
- Davet/Token: TTL, re‑send, expire/extend, loglar başarılı; deliverability ölçümleri takipli.
- KVKK: rıza metinleri, audit logları, otomatik silme devrede.

---

## Riskler ve Önlemler
- **ASR Kalitesi**: çoklu sağlayıcı fallback, sözlük, gerektiğinde insan doğrulaması.
- **LLM Tutarlılık**: schema/coverage/kanıt zorunlu; re‑run/versiyonlama.
- **Maliyet**: Flash ile geliştirme; Pro'ya yalnızca ROI kanıtı sonrası geçiş.
- **E‑posta Deliverability**: SPF/DKIM/DMARC, domain ısındırma, bounce yönetimi.

---

## Geliştirme Notları (Seçme Teknik)
- `Gemini 2.5 Flash` ile "structured JSON" üretimi; prompt'ta job description + CV + transcript + konuşma metrikleri; temperature düşük; max tokens kontrollü.
- "Rubric builder": job description'dan yetkinlik matrisi ve coverage checklist otomatik üretimi; JSON'a gömülü.
- Upload: S3 multipart (5–15 MB parçalar), ETag doğrulama; object key standardı: `cvs/{YYYY}/{MM}/{job_id}/{timestamp}_{safe_name}`.
- Token: kısa TTL + rotation; link paylaşımına karşı IP/UA bağlama opsiyonu; rate‑limit ve replay detection.

---

## Onay Sonrası Başlatılacak İşler (Sprint 1 Görevleri)
- VAD + chunked upload + retry/backoff uygulanması
- TR ASR benchmark scriptleri; ilk ölçümler ve tablo
- Queue tabanlı analiz tetikleme; konuşma metrikleri çıkarımı
- Metrik endpoint'leri + basit dashboard (latency/error)

---

## Yerel Geliştirme ve "Smooth Dev" Çalıştırma

- **Stack**: Docker Compose ile PostgreSQL + API (FastAPI) + Web (Next.js)
- **Başlatma**:
  - `docker compose up -d --build`
  - İlk kurulumda veritabanı boş ise Alembic migrasyonları otomatik uygulanmaz; şu komutla uygula: `docker compose exec -T api alembic upgrade head`
- **Sağlık kontrolü**: `http://localhost:8000/healthz` → `{ "status": "ok" }`
- **Admin hesabı (varsayılan)**:
  - E-posta: `admin@example.com`
  - Parola: `admin123`
  - Bu hesap konteyner başına bir kez oluşturulur. Gerekirse komut ile tohumla: `docker compose exec -T api python -m scripts.seed_admin`
- **Giriş**: `http://localhost:3000/login` → giriş sonrası `/dashboard`

### Smooth Dev Modu (Harici servis olmadan çalışır)
- **Gemini (AI soru üretimi)**: `GEMINI_API_KEY` yoksa deterministik yerel soru seti kullanılır (5 soru sonra biter).
- **S3 (dosya yükleme)**:
  - `S3_BUCKET`/AWS kimlikleri yoksa presign istekleri `http://localhost:8000/dev-upload/...` ile yanıtlanır; API bu endpointi 200 döner ve URL'ler kayıt altına alınır.
  - Toplu CV yüklemede S3 başarısız ise yükleme atlanır; akış devam eder.

### Web → API Bağlantısı
- Varsayılan API adresi: `NEXT_PUBLIC_API_URL=http://localhost:8000` (Compose ile otomatik set edilir). Lokalde portlar: Web 3000, API 8000, PG 5433.

### Hızlı Test Akışı
- Giriş yap → `Jobs` sekmesi → `Create New Job` ile ilan oluştur → anında listede görünür (client tarafı `refreshData()` tetiklenir).
- `Jobs > [job] > Candidates` sayfasından tekil aday oluştur veya toplu CV yükle (S3 dev modunda da çalışır).
- Aday linki gönderildiğinde konsolda link log'lanır; `http://localhost:3000/interview/{token}` üzerinden aday akışını test et.

### Sorun Giderme
- "Unauthorized" hata alırsanız token'ın `Authorization: Bearer <token>` başlığıyla gönderildiğini doğrulayın. Tarayıcıda giriş yaptıktan sonra panel sorunsuz çalışır.
- Alembic hatası (eksik revision) alırsanız: `docker compose down -v` ile hacmi sıfırlayıp ardından `docker compose up -d --build` ve `alembic upgrade head` çalıştırın.
- PowerShell scriptleri execution policy nedeniyle engellenirse komutları tek tek çalıştırın veya `powershell -ExecutionPolicy Bypass -File .\create-test-data.ps1` kullanın.

---

## UX Akışı ve Basitleştirmeler

- Aday yönetimi tek yerde: `Jobs > [job] > Candidates`.
- Üst menüdeki ayrı `Candidates` sayfası kaldırıldı; tüm aday oluşturma/link gönderme akışı job bağlamında ilerler.
- Tekil aday oluşturma formunda e‑posta formatı önceden doğrulanır; geçersiz girişlerde API'ye istek gitmez.
- API hata mesajları (422 validation gibi) artık kullanıcıya okunabilir şekilde gösteriliyor; çoklu alan hataları birleştirilerek sunulur.