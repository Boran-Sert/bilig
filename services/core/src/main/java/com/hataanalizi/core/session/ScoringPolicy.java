package com.hataanalizi.core.session;

import java.math.BigDecimal;

/** Test sonuçlarının net hesabı sözleşmesini tanımlar. */
public interface ScoringPolicy {

    /** Doğru ve yanlış cevaplardan net puanı hesaplar. */
    BigDecimal calculateNet(long correct, long wrong);
}
