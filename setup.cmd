@echo off
chcp 65001 >nul
rem Projeyi ilk kez kurar ve çalıştırır: araçları kontrol eder, .env oluşturur, servisleri başlatır.
cd /d "%~dp0"

where git >nul 2>nul || (echo [EKSİK] Git kurulu değil. Kurmak için: winget install Git.Git & goto :hata)
where docker >nul 2>nul || (echo [EKSİK] Docker Desktop kurulu değil. Kurmak için: winget install Docker.DockerDesktop & goto :hata)
docker info >nul 2>nul || (echo [EKSİK] Docker Desktop açık değil. Docker Desktop'ı açıp tekrar deneyin. & goto :hata)
where jq >nul 2>nul || echo [BİLGİ] jq kurulu değil. Claude Code kullanacaksan: winget install jqlang.jq

if not exist .env (
    copy .env.example .env >nul
    echo .env dosyası oluşturuldu.
)

echo Servisler hazırlanıyor. İlk seferde birkaç dakika sürebilir...
docker compose up --build -d --wait || (echo [HATA] Servisler başlatılamadı. Yukarıdaki mesajı Boran'a gönderin. & goto :hata)

echo.
echo Hazır: http://localhost:8080
echo Kapatmak için: docker compose down
start "" http://localhost:8080
pause
exit /b 0

:hata
pause
exit /b 1
