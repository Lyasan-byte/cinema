# syntax=docker/dockerfile:1.4
FROM maven:3.9.6-eclipse-temurin-21 AS builder
WORKDIR /app


COPY pom.xml .

RUN --mount=type=cache,target=/root/.m2 \
    mvn dependency:go-offline -B


COPY src ./src


RUN --mount=type=cache,target=/root/.m2 \
    mvn clean package -DskipTests

RUN java -Djarmode=layertools -jar target/*.jar extract

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

COPY --from=builder /app/dependencies/ ./
COPY --from=builder /app/spring-boot-loader/ ./
COPY --from=builder /app/snapshot-dependencies/ ./
COPY --from=builder /app/application/ ./

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]