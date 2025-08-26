## Admin hesapları (yerel geliştirme)

### Owner 1 (mevcut)
- E-posta: `admin@example.com`
- Şifre: `admin123`

### Owner 2 (yeni)
- E-posta: `owner2@example.com`
- Şifre: `Owner2!Pass123`

### Giriş
- URL: `http://localhost:3000/login`

Not: Bu bilgiler sadece yerel geliştirme içindir. Üretimde parolaları derhal değiştirin ve gizli saklayın.

Tarayıcı konsolunu aç (Chrome: F12 → Console).
Şu komutu aynen yapıştır ve Enter’a bas:
localStorage.setItem("founders_secret","dev-internal-secret")
