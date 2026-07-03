# 多阶段构建：Maven 打包 + JRE 运行
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build

COPY pom.xml .
RUN mvn -B dependency:go-offline -DskipTests || true

COPY src ./src
RUN mvn -B -DskipTests package

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /build/target/server_job-*.jar app.jar
RUN chown app:app app.jar

USER app
EXPOSE 8002

ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
