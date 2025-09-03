# 🔧 Troubleshooting Guide - Eski Sistem Sorunu

## Sorun
Arkadaşınız pull etmesine rağmen mülakat UI ve CV analiz özet sistemi eski sistemde kalıyor.

## Çözüm Adımları

### 1. Git Durumunu Kontrol Et
```bash
git status
git log --oneline -5
git remote -v
```

### 2. Temiz Pull Yap
```bash
git fetch origin
git reset --hard origin/main
git clean -fd
```

### 3. Node Modules'ü Temizle ve Yeniden Yükle
```bash
# Web app için
cd apps/web
rm -rf node_modules package-lock.json
npm install

# Root için
cd ../..
rm -rf node_modules package-lock.json
npm install
```

### 4. Python Dependencies'leri Güncelle
```bash
cd apps/api
pip install -r requirements.txt --upgrade
```

### 5. Docker Cache'ini Temizle
```bash
# Tüm container'ları durdur
docker-compose down

# Tüm image'ları sil
docker system prune -a --volumes

# Yeniden build et
docker-compose build --no-cache
docker-compose up -d
```

### 6. Browser Cache'ini Temizle
- Chrome: Ctrl+Shift+R (hard refresh)
- Veya Developer Tools > Network > Disable cache
- Veya Ctrl+Shift+Delete ile cache temizle

### 7. Environment Variables Kontrol Et
```bash
# API için .env dosyasını kontrol et
cat apps/api/.env

# Web için environment variables
echo $NEXT_PUBLIC_API_URL
```

### 8. Database Migration'ları Çalıştır
```bash
cd apps/api
alembic upgrade head
```

### 9. Son Kontrol
```bash
# Web app çalışıyor mu?
curl http://localhost:3000

# API çalışıyor mu?
curl http://localhost:8000/health

# Database bağlantısı var mı?
docker-compose logs postgres
```

## Eğer Hala Sorun Varsa

### Manuel Kontroller:
1. **Browser Developer Tools** aç ve Console'da hata var mı kontrol et
2. **Network tab**'ında API çağrıları doğru endpoint'e gidiyor mu?
3. **Docker logs** kontrol et: `docker-compose logs web api`

### Son Çare:
```bash
# Tamamen temiz başlangıç
git clone https://github.com/Cultro276/ai-interview.git ai-interview-fresh
cd ai-interview-fresh
docker-compose up -d
```

## Önemli Notlar
- En son commit: `cdb6dea` - "Major updates including new interview components, analytics improvements, and API enhancements"
- API port: 8000
- Web port: 3000
- Database port: 5433
