# AI Interview Projesi Temizlik ve Güncelleme Scripti (PowerShell)
Write-Host "🧹 AI Interview Projesi Temizlik ve Güncelleme Scripti" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# 1. Git durumunu kontrol et
Write-Host "📋 Git durumu kontrol ediliyor..." -ForegroundColor Yellow
git status
Write-Host ""

# 2. En son değişiklikleri al
Write-Host "⬇️ En son değişiklikler alınıyor..." -ForegroundColor Yellow
git fetch origin
git reset --hard origin/main
git clean -fd
Write-Host "✅ Git güncellemesi tamamlandı" -ForegroundColor Green
Write-Host ""

# 3. Docker container'ları durdur
Write-Host "🐳 Docker container'ları durduruluyor..." -ForegroundColor Yellow
docker-compose down
Write-Host "✅ Docker container'ları durduruldu" -ForegroundColor Green
Write-Host ""

# 4. Docker cache temizle
Write-Host "🗑️ Docker cache temizleniyor..." -ForegroundColor Yellow
docker system prune -a --volumes -f
Write-Host "✅ Docker cache temizlendi" -ForegroundColor Green
Write-Host ""

# 5. Node modules temizle (web)
Write-Host "📦 Web app node_modules temizleniyor..." -ForegroundColor Yellow
Set-Location apps/web
if (Test-Path "node_modules") { Remove-Item -Recurse -Force "node_modules" }
if (Test-Path "package-lock.json") { Remove-Item -Force "package-lock.json" }
npm install
Write-Host "✅ Web app dependencies güncellendi" -ForegroundColor Green
Write-Host ""

# 6. Root node modules temizle
Write-Host "📦 Root node_modules temizleniyor..." -ForegroundColor Yellow
Set-Location ../..
if (Test-Path "node_modules") { Remove-Item -Recurse -Force "node_modules" }
if (Test-Path "package-lock.json") { Remove-Item -Force "package-lock.json" }
npm install
Write-Host "✅ Root dependencies güncellendi" -ForegroundColor Green
Write-Host ""

# 7. Python dependencies güncelle
Write-Host "🐍 Python dependencies güncelleniyor..." -ForegroundColor Yellow
Set-Location apps/api
pip install -r requirements.txt --upgrade
Write-Host "✅ Python dependencies güncellendi" -ForegroundColor Green
Write-Host ""

# 8. Docker yeniden build et
Write-Host "🔨 Docker images yeniden build ediliyor..." -ForegroundColor Yellow
Set-Location ../..
docker-compose build --no-cache
Write-Host "✅ Docker images build edildi" -ForegroundColor Green
Write-Host ""

# 9. Servisleri başlat
Write-Host "🚀 Servisler başlatılıyor..." -ForegroundColor Yellow
docker-compose up -d
Write-Host "✅ Servisler başlatıldı" -ForegroundColor Green
Write-Host ""

# 10. Durum kontrolü
Write-Host "🔍 Servis durumları kontrol ediliyor..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "📊 Servis Durumları:" -ForegroundColor Cyan
Write-Host "Web App (http://localhost:3000):" -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Başlatılıyor..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "API (http://localhost:8000):" -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Başlatılıyor..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Temizlik ve güncelleme tamamlandı!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Sonraki adımlar:" -ForegroundColor Cyan
Write-Host "1. Browser'da http://localhost:3000 adresini aç" -ForegroundColor White
Write-Host "2. Ctrl+Shift+R ile hard refresh yap" -ForegroundColor White
Write-Host "3. Developer Tools > Network > Disable cache seç" -ForegroundColor White
Write-Host "4. Eğer hala eski sistem görünüyorsa, browser cache'ini tamamen temizle" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Sorun devam ederse:" -ForegroundColor Cyan
Write-Host "- docker-compose logs web api komutu ile logları kontrol et" -ForegroundColor White
Write-Host "- TROUBLESHOOTING.md dosyasını incele" -ForegroundColor White
