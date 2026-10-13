# Servidor Fuseki oficial de Apache Jena; versión y binario fijados.
FROM eclipse-temurin:21-jre-jammy
ADD --checksum=sha256:2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee https://repo.maven.apache.org/maven2/org/apache/jena/jena-fuseki-server/6.2.0/jena-fuseki-server-6.2.0.jar /fuseki/server.jar
RUN mkdir -p /fuseki/databases && chown -R 10001:10001 /fuseki && chmod 644 /fuseki/server.jar
USER 10001:10001
WORKDIR /fuseki
EXPOSE 3030
ENTRYPOINT ["java", "-jar", "/fuseki/server.jar"]
CMD ["--tdb2", "--loc", "/fuseki/databases/musica", "--update", "/musica"]
