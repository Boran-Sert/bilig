package com.hataanalizi.core.session;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

/** AYT net hesabının doğru ve yanlış cevap kurallarını doğrular. */
class AytScoringPolicyTest {

    private final AytScoringPolicy scoringPolicy = new AytScoringPolicy();

    /** Dört yanlışın bir doğruyu götürdüğünü ve neti iki basamakla döndürdüğünü doğrular. */
    @Test
    void calculatesAytNet() {
        assertThat(scoringPolicy.calculateNet(18, 4)).isEqualByComparingTo(new BigDecimal("17.00"));
    }

    /** Yanlış cevap olmadığında netin doğru cevap sayısına eşit olduğunu doğrular. */
    @Test
    void calculatesNetWithoutWrongAnswers() {
        assertThat(scoringPolicy.calculateNet(18, 0)).isEqualByComparingTo(new BigDecimal("18.00"));
    }
}
