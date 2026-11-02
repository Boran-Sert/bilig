package com.hataanalizi.core.tutor;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** Öğrenciye soru ipucu uç noktasını sunar. */
@RestController
public class HintController {

    private final HintService hintService;

    /** İpucu iş kurallarını saklar. */
    public HintController(HintService hintService) {
        this.hintService = hintService;
    }

    /** Sorunun ipucunu döndürür. */
    @GetMapping("/api/questions/{id}/hint")
    public HintResponse getHint(@PathVariable Long id) {
        return new HintResponse(hintService.getHint(id));
    }

    /** İpucu uç noktasının JSON yanıtını tanımlar. */
    public record HintResponse(String hint) {}
}
