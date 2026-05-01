package com.homeworkgrader;

import com.homeworkgrader.config.GraderProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableAsync;

@EnableAsync
@SpringBootApplication
@EnableConfigurationProperties(GraderProperties.class)
public class HomeworkGraderBackendApplication {
    public static void main(String[] args) {
        SpringApplication.run(HomeworkGraderBackendApplication.class, args);
    }
}
