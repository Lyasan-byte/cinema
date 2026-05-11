package homework.hwqdrant;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

@RequiredArgsConstructor
@Slf4j
@SpringBootApplication
@RestController
@RequestMapping("/api")
public class QdrantDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(QdrantDemoApplication.class, args);
    }

    private final VectorStore vectorStore;

    @PostMapping("/add")
    public String addDocument(@RequestBody String text) {
        log.info("Добавляем элемент: {}", text);
        vectorStore.add(List.of(new Document(text, Map.of("source", "user-ui"))));
        return "Успешно добавлено!";
    }


    @PostMapping("/add-batch")
    public String addBatchDocuments(@RequestBody String text) {
        log.info("Получен текст для массовой загрузки. Начинаем обработку...");

        List<Document> documents = Arrays.stream(text.split(";"))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(sentence -> {
                    log.info("Подготовлен элемент: {}", sentence);
                    return new Document(sentence, Map.of("source", "batch-upload"));
                })
                .toList();

        if (documents.isEmpty()) {
            return "Текст пуст или не содержит элементов для добавления.";
        }

        vectorStore.add(documents);
        log.info("Успешно загружено {} элементов в базу.", documents.size());

        return "Успешно добавлено " + documents.size() + " элементов!";
    }

    @GetMapping("/search")
    public List<String> search(@RequestParam String query) {
        log.info("Ищем по запросу: {}", query);
        SearchRequest request = SearchRequest.builder()
                .query(query)
                .topK(1)
                .build();

        try {
            var res = vectorStore.similaritySearch(request)
                    .stream()
                    .map(Document::getText)
                    .toList();
            log.info("Результат поиска: {}", res);
            return res;
        } catch (NullPointerException e) {
            return "Ничего не найдено".lines().toList();
        }
    }
}