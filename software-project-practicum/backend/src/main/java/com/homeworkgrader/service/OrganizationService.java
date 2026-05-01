package com.homeworkgrader.service;

import com.homeworkgrader.repository.CrudJdbcRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class OrganizationService {
    private final CrudJdbcRepository repository;

    public OrganizationService(CrudJdbcRepository repository) {
        this.repository = repository;
    }

    public List<Map<String, Object>> tree() {
        List<Map<String, Object>> rows = repository.list("organization_unit").stream()
                .sorted((left, right) -> Long.compare(asLong(left.get("id")), asLong(right.get("id"))))
                .collect(Collectors.toList());
        Map<Long, Map<String, Object>> byId = new LinkedHashMap<>();
        List<Map<String, Object>> roots = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> node = new LinkedHashMap<>(row);
            node.put("children", new ArrayList<Map<String, Object>>());
            byId.put(asLong(row.get("id")), node);
        }
        for (Map<String, Object> node : byId.values()) {
            Object parentId = node.get("parent_id");
            if (parentId == null || !byId.containsKey(asLong(parentId))) {
                roots.add(node);
            } else {
                childrenOf(byId.get(asLong(parentId))).add(node);
            }
        }
        return roots;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> childrenOf(Map<String, Object> node) {
        return (List<Map<String, Object>>) node.get("children");
    }

    private long asLong(Object value) {
        return ((Number) value).longValue();
    }
}
