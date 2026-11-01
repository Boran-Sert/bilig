package com.hataanalizi.core.session;

import java.math.BigDecimal;
import java.math.RoundingMode;
import org.springframework.stereotype.Component;

/** AYT netini her dört yanlış için bir doğru eksilterek hesaplar. */
@Component
public class AytScoringPolicy implements ScoringPolicy {

    private static final BigDecimal WRONG_ANSWER_DIVISOR = BigDecimal.valueOf(4);

    /** AYT kuralına göre doğru ve yanlış cevaplardan net puanı hesaplar. */
    @Override
    public BigDecimal calculateNet(long correct, long wrong) {
        BigDecimal wrongCount = BigDecimal.valueOf(wrong);
        BigDecimal wrongPenalty = wrongCount.divide(WRONG_ANSWER_DIVISOR, 2, RoundingMode.UNNECESSARY);
        return BigDecimal.valueOf(correct).subtract(wrongPenalty);
    }
}
