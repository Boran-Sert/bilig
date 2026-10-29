package com.hataanalizi.core.storage;

import java.io.InputStream;

/** Dosyaları kullanılan depolama altyapısından bağımsız olarak yönetir. */
public interface FileStorage {

    /** Dosyayı verilen yola kaydeder. */
    void save(String path, InputStream content);

    /** Verilen yoldaki dosyayı açar. */
    InputStream open(String path);

    /** Verilen yolda dosya olup olmadığını bildirir. */
    boolean exists(String path);
}
