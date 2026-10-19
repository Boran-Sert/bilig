package com.hataanalizi.core;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** Java servisinin giriş noktası; Spring Boot uygulamasını başlatır. */
@SpringBootApplication
public class CoreApplication {

    /** Uygulamayı verilen komut satırı argümanlarıyla başlatır. */
    public static void main(String[] args) {
        SpringApplication.run(CoreApplication.class, args);
    }
}
