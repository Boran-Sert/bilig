# web (React)
React 19, Vite 8, TypeScript 6 (strict), shadcn/ui, Tailwind CSS 4.

## Yapı
- src/features/<özellik>/ altında pages/, components/, api.ts (TanStack Query hook'ları), types.ts.
- Ortak bileşenler src/components/; shadcn bileşenleri src/components/ui/ (CLI ile eklenir, elle düzenlenmez).

## Kurallar
- Sunucu verisi sadece TanStack Query ile; elle useEffect + fetch yok.
- API tipleri npm run gen:api ile üretilir; elle tip yazılmaz. any yok.
- Metinler src/locales/tr/<özellik>.json dosyasında; bileşende Türkçe metin yok.
- Formlar react-hook-form + zod. Markdown react-markdown + rehype-sanitize; dangerouslySetInnerHTML yok.
- Akış (SSE) sadece lib/sse.ts üzerinden (@microsoft/fetch-event-source).
- İş kuralı yok: doğru/yanlış, ilerleme ve başarı Java'dan gelir.
- Bileşen başına bir dosya.

## Test
- Mantık içeren bileşen ve hook için Vitest ve Testing Library.

## Komut
- npm run lint && npm run typecheck && npm test
