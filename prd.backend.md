# Hirevision Backend PRD (Parallel Work Plan)

## Kapsam ve Amaç
- Admin paneli ve aday istemcisini besleyecek API'lar, iş/aday/konuşma/analiz akışları, davet & token, media upload presign ve metrik uçları.
- Yerel geliştirmede harici servis olmadan çalışabilme (Smooth Dev): Gemini yoksa deterministic soru seti, S3 yoksa dev presign URL, e‑posta mock.

## Out of Scope (bu fazda)
- Gerçek ASR entegrasyonu (VAD/diarization/noise reduce prod kalitesi). Şimdilik transcript elle upload/patch.
- E‑posta sağlayıcı: Resend API ile e‑posta gönderimi (env: RESEND_API_KEY, MAIL_FROM, MAIL_FROM_NAME).

## Mimari Notlar
- FastAPI `apps/api/src` altında `v1` router'lar. Çok kiracılı (user_id scoped) veri erişimi.
- Modeller: `Candidate`, `Job`, `Interview`, `ConversationMessage`, `InterviewAnalysis` (mevcut). Analiz için `services/analysis.generate_rule_based_analysis` hazır.
- Smooth Dev: `src/core/s3.py` dev fallback; `src/core/gemini.py` fallback soru üretimi.

---

## Yol Haritası (2 geliştirici paralel)

### Sprint A (Hafta 1–2)
- Conversation API (mevcutsa doğrula, eksikse ekle)
  - POST `/api/v1/conversation` (mesaj ekle)
  - GET `/api/v1/conversation/{interview_id}` (mesaj listesi)
- Analysis Trigger & Read
  - POST `/api/v1/interviews/{id}/analysis:run` → `services/analysis.generate_rule_based_analysis` çağırır
  - GET `/api/v1/interviews/{id}/analysis` → son analiz kaydı
- Upload Presign (mevcut) ve Dev Upload
  - POST `/api/v1/tokens/presign-upload` (mevcut)
  - GET `/dev-upload/{key}` (opsiyonel echo endpoint; S3 yoksa 200 dön)
- Metrics & Health
  - GET `/healthz` (mevcut)
  - GET `/api/v1/metrics` → basit JSON: { upload_p95, analysis_p95, errors_by_type }
  - (Opsiyonel) `POST /api/v1/metrics/log-upload` → { interview_id|token, kind, duration_ms, size_bytes, success }

### Sprint B (Hafta 3–4)
- Invite/Token Geliştirmeleri
  - POST `/api/v1/tokens/verify?token=...` (mevcut) → ilk doğrulamada `used_at` set opsiyonu
  - POST `/api/v1/candidates/{id}/send-link` (mevcut) → TTL güncelleme desteği
- Transcript Uçları (ASR stub)
  - POST `/api/v1/interviews/{id}/transcript` → { text, provider: "manual" }
  - GET `/api/v1/interviews/{id}/transcript`
- Bulk CV Upload iyileştirme
  - Var olan `jobs/{id}/candidates/bulk-upload` için hata raporu ve sonuç özeti genişletme

### Sprint C (Hafta 5–6)
- Webhook
  - POST `/api/v1/webhooks/analysis-ready` (internal trigger) ve tenant scoped secret doğrulama
- Audit & Retention iskeleti
  - Basit `access_logs` tablosu ve günlük purge job skeleton (cron/apscheduler)

---

## API Sözleşmeleri (kontrat freeze v1)

1) Analysis
```
POST /api/v1/interviews/{id}/analysis:run
Response 200: { "id": number, "interview_id": number, "overall_score": number, "summary": string, "strengths": string, "weaknesses": string, "communication_score": number, "technical_score": number, "cultural_fit_score": number, "model_used": "rule-based-v1", "created_at": iso }

GET /api/v1/interviews/{id}/analysis
Response 200: InterviewAnalysisRead | 404
```

2) Conversation
```
POST /api/v1/conversation
Body: { "interview_id": number, "role": "assistant"|"user", "content": string, "sequence_number": number }
Response: ConversationMessageRead

GET /api/v1/conversation/{interview_id}
Response: ConversationMessageRead[]
```

3) Upload Presign (mevcut)
```
POST /api/v1/tokens/presign-upload
Body: { "token": string, "file_name": string, "content_type": "video/webm|video/mp4|audio/webm|audio/wav|..." }
Response: { "presigned_url": string, "url": string, "key": string }
```

4) Token Verify (mevcut)
```
POST /api/v1/tokens/verify?token=... → 200 CandidateRead | 400 invalid
```

5) Transcript (stub)
```
POST /api/v1/interviews/{id}/transcript
Body: { "text": string, "provider": "manual" }
Response: { "interview_id": number, "length": number }

GET /api/v1/interviews/{id}/transcript
Response: { "interview_id": number, "text": string } | 404
```

6) Metrics
```
GET /api/v1/metrics
Response: { "upload_p95_ms": number, "analysis_p95_ms": number, "error_rate": number }

POST /api/v1/metrics/log-upload
Body: { interview_id?: number, token?: string, kind: "video"|"audio", duration_ms: number, size_bytes?: number, success: boolean }
Response: { ok: true }
```

---

## Veri Modeli Notları
- `ConversationMessage(role: assistant|user, sequence_number int, timestamp)`
- `InterviewAnalysis(overall_score, summary, strengths, weaknesses, communication_score, technical_score, cultural_fit_score, model_used)`

---

## Kabul Kriterleri
- Tüm uçlar `401` → auth yoksa, `403/404` → tenant dışı erişimlerde doğru döner.
- Presign üretimi S3 yoksa dev URL ile cevap verir; front bu URL'ye PUT atınca 200 alır.
- `analysis:run` 2s altında rule‑based sonuç üretir ve `InterviewAnalysis` tablosuna yazar.
- Transcript uçları metni kaydeder/okur; analiz promptu için ileride kullanılacaktır.

---

## Görev Dağılımı (1 Backend Geliştirici)
- Gün 1: `analysis:run`, `analysis:get` uçları + service entegrasyonu
- Gün 2: Conversation POST/GET uçlarının doğrulanması/eklenmesi
- Gün 3: Transcript POST/GET (stub) + model
- Gün 4: Metrics endpoint + basit ölçüm toplayıcı
- Gün 5: Testler (unit + minimal e2e) ve dokümantasyon

---

## Çalıştırma / Geliştirme
- Docker Compose: `docker compose up -d --build`
- Alembic: `docker compose exec -T api alembic upgrade head`
- Admin seed: `docker compose exec -T api python -m scripts.seed_admin`

---

## Git/GitHub Akışı
- Branch: `feature/backend-analysis`, `feature/backend-transcript`, `chore/metrics` gibi.
- PR: küçük ve atomik; açıklama + test çıktısı; reviewer = diğer geliştirici.
- Commit: Conventional Commits (feat:, fix:, chore:, refactor:, docs:).
- Sync: `git pull --rebase origin main` → `git push -u origin <branch>` → PR → review → squash merge.


