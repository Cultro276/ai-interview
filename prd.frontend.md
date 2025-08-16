# Hirevision Frontend PRD (Parallel Work Plan)

## Kapsam ve Amaç
- Admin paneli `(app/(admin))` ve aday mülakat istemcisi `(app/interview/[token])` akışlarının tamamlanması.
- Hız, basitlik ve geliştirici deneyimi: Smooth Dev modunda S3/Gemini olmadan da uçtan uca test edilebilir.

## Out of Scope (bu fazda)
- Gerçek zamanlı diarization/transcript highlight eşlemesi. Şimdilik metin gösterimi ve analize giden buton akışı.
- İleri seviye grafikler (heatmap). Basit metrik kartları yeterli.

## Mimari Notlar
- Next.js App Router, TypeScript, Tailwind. AuthContext ile token yönetimi.
- API erişimi `apps/web/lib/api.ts` üzerinden; `NEXT_PUBLIC_API_URL` ortam değişkeni.

---

## Yol Haritası (2 geliştirici paralel)

### Sprint A (Hafta 1–2)
- Admin: Jobs
  - `Jobs` listesi (mevcut) → oluşturma sonrası anında refresh.
  - `Jobs > [job] > Candidates` sayfasında tekil aday oluşturma + bulk CV yükleme UX (mevcut akışın cilası: hata/success toasts, progress bar).
- Admin: Candidate detay minimal kartı
  - Aday satırında `Send Link` aksiyonu (mevcut endpoint), TTL opsiyonu, toast feedback.
- Candidate App: Interview giriş
  - `interview/[token]` sayfasında token verify, izin/cihaz testi, kayıt başlat butonu.
  - Upload: presign al → `fetch PUT` ile yükle → başarıyla bitince kayıt URL'si UI'da gösterilir.

### Sprint B (Hafta 3–4)
- Admin: Conversation & Analysis görünümü
  - `Run Analysis` butonu → `analysis:run` çağırır → dönen skor/özet UI kartında gösterilir.
  - `Conversation` sekmesi: gönderilmiş soru/cevapların listesi (server verisi veya local echo).
- Candidate App: Transcript stub
  - Kayıt sonrası transcript metninin manuel girildiği/gösterildiği basit form (POST/GET transcript uçlarına).

### Sprint C (Hafta 5–6)
- Metrics mini dashboard
  - Admin `Dashboard` sayfasında latency, error rate gösterimi (cards + sparkline basit SVG ya da sayı).
- UX cilaları
  - Form doğrulama, boş durum ekranları, yükleme durumları, hataların kullanıcı dostu gösterimi.

---

## Ekranlar ve Bileşenler
- `app/(admin)/jobs/page.tsx` (liste)
- `app/(admin)/jobs/new/page.tsx` (form)
- `app/(admin)/jobs/[id]/candidates/page.tsx` (tekil + bulk upload)
- `app/(admin)/dashboard/page.tsx` (metrics)
- `app/interview/[token]/page.tsx` (aday istemci)

---

## API Entegrasyon Sözleşmeleri (freeze v1)
- Token verify:
  - POST `/api/v1/tokens/verify?token=...` → 200 CandidateRead | 400 Invalid
- Upload presign:
  - POST `/api/v1/tokens/presign-upload` Body: { token, file_name, content_type }
  - Response: { presigned_url, url, key } → `fetch(url, { method: 'PUT', body, headers: { 'Content-Type': content_type } })`
- Analysis run/get:
  - POST `/api/v1/interviews/{id}/analysis:run` → InterviewAnalysisRead
  - GET `/api/v1/interviews/{id}/analysis` → InterviewAnalysisRead | 404
- Transcript stub:
  - POST `/api/v1/interviews/{id}/transcript` → { interview_id, length }
  - GET `/api/v1/interviews/{id}/transcript` → { interview_id, text }
- Metrics:
  - GET `/api/v1/metrics` → { upload_p95_ms, analysis_p95_ms, error_rate }

---

## Kabul Kriterleri
- `Jobs` akışı: oluştur, listele, `Candidates` alt sayfasında tekil oluştur ve bulk yükleme; tüm hatalar toasts ile gösterilir.
- `Send Link` aksiyonu çalışır ve konsola link yazılır (mock mail).
- Aday istemci: token doğrulanır, kayıt dosyası presign ile yüklenir, başarı mesajı görünür.
- `Run Analysis`: 2s altında sonuçlanır ve skor/özet kartı güncellenir.
- Transcript formu POST/GET ile çalışır ve metin geri çağrılır.

---

## Görev Dağılımı (1 Frontend Geliştirici)
- Gün 1: `interview/[token]` verify + upload akışı (voice/video `lib/voice.ts` üzerinden)
- Gün 2: `Jobs > [job] > Candidates` cilaları (progress, toast, error handling)
- Gün 3: Analysis run/get entegrasyonu ve basit analiz kartı
- Gün 4: Transcript stub formu + görünüm
- Gün 5: Dashboard mini metrics + genel UX cilası

---

## Çalıştırma / Geliştirme
- Env: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Çalıştır: `yarn dev` veya Docker Compose ile.

---

## Git/GitHub Akışı
- Branch: `feature/fe-interview-upload`, `feat/fe-analysis-card`, `chore/fe-metrics` gibi.
- PR: küçük ve atomik; açıklama + ekran görüntüsü/GIF.
- Commit: Conventional Commits.
- Sync: `git pull --rebase origin main` → `git push -u origin <branch>` → PR → review → squash merge.


