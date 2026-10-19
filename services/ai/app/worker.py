"""İş kuyruğu çalışanı.

python -m app.worker ile ayrı süreç olarak başlar, job tablosundaki hazırlık işlerini çalıştırır.
İş alma döngüsü kuyruk uygulamasıyla birlikte eklenir; o zamana kadar süreç ayakta kalıp bekler.
"""

import asyncio


async def run() -> None:
    """Çalışanı başlatır ve süreç durdurulana kadar bekler."""
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run())
