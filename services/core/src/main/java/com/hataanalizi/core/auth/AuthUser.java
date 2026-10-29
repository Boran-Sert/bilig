package com.hataanalizi.core.auth;

/** Giriş yapmış kullanıcıyı güvenlik bağlamında temsil eder. */
public record AuthUser(Long id, String email, String role) {}
