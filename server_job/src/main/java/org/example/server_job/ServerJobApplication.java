package org.example.server_job;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("org.example.server_job.**.mapper")
public class ServerJobApplication {

    public static void main(String[] args) {
        SpringApplication.run(ServerJobApplication.class, args);
    }

}
