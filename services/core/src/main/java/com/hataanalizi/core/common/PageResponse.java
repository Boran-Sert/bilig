package com.hataanalizi.core.common;

import java.util.List;

/**
 * Sayfalı listelerin ortak cevap biçimidir: {items, page, size, total}. Sayfa numarası 0'dan başlar,
 * total bütün kayıtların sayısıdır.
 */
public record PageResponse<T>(List<T> items, int page, int size, long total) {}
