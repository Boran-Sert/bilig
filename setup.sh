#!/bin/sh
# Projeyi ilk kez kurar ve çalıştırır: araçları kontrol eder, .env oluşturur, servisleri başlatır.
cd "$(dirname "$0")" || exit 1

dur() { echo "$1"; exit 1; }

command -v git >/dev/null || dur "[EKSİK] Git kurulu değil. Kurmak için: xcode-select --install"
command -v docker >/dev/null || dur "[EKSİK] Docker Desktop kurulu değil. İndirmek için: https://www.docker.com/products/docker-desktop/"
docker info >/dev/null 2>&1 || dur "[EKSİK] Docker Desktop açık değil. Docker Desktop'ı açıp tekrar deneyin."
command -v jq >/dev/null || echo "[BİLGİ] jq kurulu değil. Claude Code kullanacaksan: brew install jq"

if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env dosyası oluşturuldu."
fi

echo "Servisler hazırlanıyor. İlk seferde birkaç dakika sürebilir..."
docker compose up --build -d --wait || dur "[HATA] Servisler başlatılamadı. Yukarıdaki mesajı Boran'a gönderin."

echo
echo "Hazır: http://localhost:8080"
echo "Kapatmak için: docker compose down"
open http://localhost:8080 2>/dev/null || xdg-open http://localhost:8080 2>/dev/null || true
