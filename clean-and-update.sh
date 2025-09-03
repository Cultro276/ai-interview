#!/bin/bash

echo "🧹 AI Interview Projesi Temizlik ve Güncelleme Scripti"
echo "=================================================="

# 1. Git durumunu kontrol et
echo "📋 Git durumu kontrol ediliyor..."
git status
echo ""

# 2. En son değişiklikleri al
echo "⬇️ En son değişiklikler alınıyor..."
git fetch origin
git reset --hard origin/main
git clean -fd
echo "✅ Git güncellemesi tamamlandı"
echo ""

# 3. Docker container'ları durdur
echo "🐳 Docker container'ları durduruluyor..."
docker-compose down
echo "✅ Docker container'ları durduruldu"
echo ""

# 4. Docker cache temizle
echo "🗑️ Docker cache temizleniyor..."
docker system prune -a --volumes -f
echo "✅ Docker cache temizlendi"
echo ""

# 5. Node modules temizle (web)
echo "📦 Web app node_modules temizleniyor..."
cd apps/web
rm -rf node_modules package-lock.json
npm install
echo "✅ Web app dependencies güncellendi"
echo ""

# 6. Root node modules temizle
echo "📦 Root node_modules temizleniyor..."
cd ../..
rm -rf node_modules package-lock.json
npm install
echo "✅ Root dependencies güncellendi"
echo ""

# 7. Python dependencies güncelle
echo "🐍 Python dependencies güncelleniyor..."
cd apps/api
pip install -r requirements.txt --upgrade
echo "✅ Python dependencies güncellendi"
echo ""

# 8. Docker yeniden build et
echo "🔨 Docker images yeniden build ediliyor..."
cd ../..
docker-compose build --no-cache
echo "✅ Docker images build edildi"
echo ""

# 9. Servisleri başlat
echo "🚀 Servisler başlatılıyor..."
docker-compose up -d
echo "✅ Servisler başlatıldı"
echo ""

# 10. Durum kontrolü
echo "🔍 Servis durumları kontrol ediliyor..."
sleep 10

echo "📊 Servis Durumları:"
echo "Web App (http://localhost:3000):"
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "Başlatılıyor..."

echo ""
echo "API (http://localhost:8000):"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "Başlatılıyor..."

echo ""
echo "🎉 Temizlik ve güncelleme tamamlandı!"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. Browser'da http://localhost:3000 adresini aç"
echo "2. Ctrl+Shift+R ile hard refresh yap"
echo "3. Developer Tools > Network > Disable cache seç"
echo "4. Eğer hala eski sistem görünüyorsa, browser cache'ini tamamen temizle"
echo ""
echo "🔧 Sorun devam ederse:"
echo "- docker-compose logs web api komutu ile logları kontrol et"
echo "- TROUBLESHOOTING.md dosyasını incele"
