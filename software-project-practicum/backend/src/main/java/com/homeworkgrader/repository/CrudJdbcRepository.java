package com.homeworkgrader.repository;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.StringJoiner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class CrudJdbcRepository {
    private static final Set<String> TABLES = new HashSet<>(Arrays.asList(
            "organization_unit", "teacher", "student", "course", "course_offering",
            "teaching_class", "course_offering_teacher", "teaching_class_student",
            "assessment", "assessment_template", "question_definition", "rubric_definition",
            "standard_answer", "answer_card_layout", "submission", "submission_asset",
            "extraction_run", "extraction_result", "grading_run", "score_item_result",
            "final_result", "course_grade", "grade_publish_record", "grade_export_record"
    ));

    private final JdbcTemplate jdbcTemplate;
    private final NamedParameterJdbcTemplate namedJdbcTemplate;

    public CrudJdbcRepository(JdbcTemplate jdbcTemplate, NamedParameterJdbcTemplate namedJdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        this.namedJdbcTemplate = namedJdbcTemplate;
    }

    public List<Map<String, Object>> list(String table) {
        assertTable(table);
        return jdbcTemplate.queryForList("select * from " + table + " order by id desc");
    }

    public List<Map<String, Object>> listBy(String table, String column, Object value) {
        assertTable(table);
        assertIdentifier(column);
        return namedJdbcTemplate.queryForList(
                "select * from " + table + " where " + column + " = :value order by id desc",
                new MapSqlParameterSource("value", value)
        );
    }

    public Map<String, Object> get(String table, Long id) {
        assertTable(table);
        return namedJdbcTemplate.queryForMap(
                "select * from " + table + " where id = :id",
                new MapSqlParameterSource("id", id)
        );
    }

    public List<Map<String, Object>> query(String sql, Map<String, Object> params) {
        return namedJdbcTemplate.queryForList(sql, params);
    }

    public Integer queryForInteger(String sql, Map<String, Object> params) {
        return namedJdbcTemplate.queryForObject(sql, params, Integer.class);
    }

    public Long insert(String table, Map<String, Object> values) {
        assertTable(table);
        if (values.isEmpty()) {
            throw new IllegalArgumentException("新增数据不能为空");
        }
        List<String> columns = new ArrayList<>(values.keySet());
        columns.forEach(this::assertIdentifier);
        StringJoiner columnSql = new StringJoiner(", ");
        StringJoiner paramSql = new StringJoiner(", ");
        columns.forEach(column -> {
            columnSql.add(column);
            paramSql.add(":" + column);
        });
        String sql = "insert into " + table + " (" + columnSql + ") values (" + paramSql + ")";
        namedJdbcTemplate.update(sql, values);
        return jdbcTemplate.queryForObject("select last_insert_id()", Long.class);
    }

    public int update(String table, Long id, Map<String, Object> values) {
        assertTable(table);
        if (values.isEmpty()) {
            return 0;
        }
        List<String> columns = new ArrayList<>(values.keySet());
        columns.forEach(this::assertIdentifier);
        StringJoiner setSql = new StringJoiner(", ");
        columns.forEach(column -> setSql.add(column + " = :" + column));
        String sql = "update " + table + " set " + setSql + " where id = :id";
        values.put("id", id);
        return namedJdbcTemplate.update(sql, values);
    }

    public int softDisable(String table, Long id) {
        assertTable(table);
        return namedJdbcTemplate.update(
                "update " + table + " set status = 0 where id = :id",
                new MapSqlParameterSource("id", id)
        );
    }

    private void assertTable(String table) {
        if (!TABLES.contains(table)) {
            throw new IllegalArgumentException("不允许访问的数据表：" + table);
        }
    }

    private void assertIdentifier(String name) {
        if (!name.matches("[a-zA-Z_][a-zA-Z0-9_]*")) {
            throw new IllegalArgumentException("非法字段名：" + name);
        }
    }
}
