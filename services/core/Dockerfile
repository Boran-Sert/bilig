# Java servisinin imajı: Maven Wrapper ile derler, sadece JRE ile çalıştırır.
FROM eclipse-temurin:25-jdk AS build
WORKDIR /src
COPY mvnw pom.xml checkstyle.xml ./
COPY .mvn .mvn
COPY src src
RUN --mount=type=cache,target=/root/.m2 sh mvnw -q -DskipTests package

FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=build /src/target/core-*.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java", "-jar", "app.jar"]
