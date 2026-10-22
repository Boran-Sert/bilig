package com.hataanalizi.core;

import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.ExecutionException;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.images.builder.ImageFromDockerfile;
import org.testcontainers.utility.DockerImageName;

/** Projenin eklentili PostgreSQL imajını testlerde kullanıma hazırlar. */
@TestConfiguration(proxyBeanMethods = false)
class TestcontainersConfiguration {

    /** Proje Dockerfile'ından oluşturulan PostgreSQL konteynerini sağlar. */
    @Bean
    @ServiceConnection
    PostgreSQLContainer<?> postgresContainer() throws ExecutionException, InterruptedException, URISyntaxException {
        Path dockerfile = findDockerfile();
        String imageName = new ImageFromDockerfile()
                .withBuildArg("TARGETARCH", targetArchitecture())
                .withFileFromPath("Dockerfile", dockerfile)
                .get();
        DockerImageName dockerImageName = DockerImageName.parse(imageName).asCompatibleSubstituteFor("postgres");
        return new PostgreSQLContainer<>(dockerImageName);
    }

    /** Derleme çıktısının üst dizinlerinde proje Dockerfile'ını bulur. */
    private Path findDockerfile() throws URISyntaxException {
        Path location = Path.of(TestcontainersConfiguration.class
                .getProtectionDomain()
                .getCodeSource()
                .getLocation()
                .toURI());
        for (Path directory = location; directory != null; directory = directory.getParent()) {
            Path dockerfile = directory.resolve("infra").resolve("postgres").resolve("Dockerfile");
            if (Files.isRegularFile(dockerfile)) {
                return dockerfile;
            }
        }
        throw new IllegalStateException("Could not locate infra/postgres/Dockerfile");
    }

    /** Docker imajı için ana makine mimarisini döndürür. */
    private String targetArchitecture() {
        return switch (System.getProperty("os.arch")) {
            case "amd64", "x86_64" -> "amd64";
            case "aarch64", "arm64" -> "arm64";
            default -> throw new IllegalStateException("Unsupported test host architecture");
        };
    }
}
