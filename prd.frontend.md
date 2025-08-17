# Hirevision Frontend PRD (Parallel Work Plan)

## To Do (High Priority)
- Jobs listesinde yeni işlerin görünmemesi: `DashboardContext` veri çekimi ve hata yönetimi güçlendirilecek; CORS/401/redirect durumlarında kullanıcıya toast gösterilecek. Jobs sayfasına manuel "Refresh" butonu eklenecek. (DONE)
- API taban adresi: `NEXT_PUBLIC_API_URL` dokümantasyonu ve `.env` örneği eklenecek; yanlış/boş olduğunda anlamlı uyarı. (DONE via docker-compose env)
- Toast altyapısı: `ToastContext` + `Toaster` projeye eklendi ve `app/layout.tsx` içinde global; tüm sayfalarda kullanılabilir. (DONE)
- Candidates toplu aksiyon: `Send Link to All` 10’luk batch ile çalışır ve ilerleme bilgisi gösterir. (DONE)
- Interview akışı: Aday UI public endpointlerle çalışır; konuşma mesajları için `/api/v1/conversations/messages-public`, token → interview eşlemesi için `/api/v1/interviews/by-token/{token}` eklendi. (DONE)
- Admin navigation: Jobs kartları → Candidates sayfası linkleri mevcut. (DONE)

## To Do (Stability & DX)
- Global error boundary ve 404/500 özel sayfaları.
- Loading/skeleton durumları (Jobs/Interviews/Reports).
- Tipler: `DashboardContext` modelleri (Interview + scores) TypeScript tarafında güçlendirilecek.
- Test: E2E smoke (create job → create candidate → send link → interview finish → analysis görünümü → reports sıralama).

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

## Ortam Değişkenleri (.env)
- Web (Next.js)
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - (opsiyonel) `NEXT_PUBLIC_LOG_LEVEL=debug`

- API (bilgi amaçlı – frontend için yalnızca yukarıdaki gereklidir)
  - `AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET` (yoksa dev-upload stub çalışır)
  - `RESEND_API_KEY, MAIL_FROM, MAIL_FROM_NAME`

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
- Interview init (candidate):
  - GET `/api/v1/interviews/by-token/{token}` → InterviewRead | 404
- Conversation messages (candidate public):
  - POST `/api/v1/conversations/messages-public` → ConversationMessageRead
- Transcript stub:
  - POST `/api/v1/interviews/{id}/transcript` → { interview_id, length }
  - GET `/api/v1/interviews/{id}/transcript` → { interview_id, text }
- Metrics:
  - GET `/api/v1/metrics` → { upload_p95_ms, analysis_p95_ms, error_rate }

---

## Test Senaryoları (E2E)
- Giriş → Jobs → New Job ile iş oluştur; Jobs listesinde görünmeli (gerekirse Refresh butonu).
- Jobs > [job] > Candidates → tekil aday oluştur (email zorunlu) → başarı tostu ve log’da davet linki.
- Send Link to All → TTL gir, tüm adaylara gönderim (mock) tamamlanır.
- Aday linkiyle `interview/[token]` akışını tamamla → upload denensin; hata varsa toast + konsol logları görünür.
- Admin Interviews → seçilen görüşmede analiz ve Decision rozeti görünmeli.
- Reports → seçilen işte en iyi→en kötü sıralama, Only completed açık, CSV export indirilebilir.

## Kabul Kriterleri
- `Jobs` akışı: oluştur, listele, `Candidates` alt sayfasında tekil oluştur ve bulk yükleme; tüm hatalar toasts ile gösterilir.
- `Send Link` aksiyonu çalışır ve konsola link yazılır (mock mail).
- Aday istemci: token doğrulanır, kayıt dosyası presign ile yüklenir, başarı mesajı görünür.
- `Run Analysis`: 2s altında sonuçlanır ve skor/özet kartı güncellenir.
- Transcript formu POST/GET ile çalışır ve metin geri çağrılır.

---

## Yayın Kontrol Listesi
- `.env` veya docker-compose içinde `NEXT_PUBLIC_API_URL` doğru (lokalde `http://localhost:8000`).
- Web ayağa kalktıktan sonra `/dashboard` ve `/jobs` açılabiliyor.
- CORS hatası yok; 401 durumda login’e yönlendirme çalışıyor.
- Upload denemesinde hata olursa toast + konsolda detay görünüyor.

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


