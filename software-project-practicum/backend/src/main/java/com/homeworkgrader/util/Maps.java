package com.homeworkgrader.util;

import java.util.HashMap;
import java.util.Map;

public final class Maps {
    private Maps() {
    }

    public static Map<String, Object> of(String key, Object value) {
        Map<String, Object> map = new HashMap<>();
        map.put(key, value);
        return map;
    }

    public static Map<String, Object> of(String key1, Object value1, String key2, Object value2) {
        Map<String, Object> map = of(key1, value1);
        map.put(key2, value2);
        return map;
    }

    public static Map<String, Object> of(String key1, Object value1, String key2, Object value2, String key3, Object value3) {
        Map<String, Object> map = of(key1, value1, key2, value2);
        map.put(key3, value3);
        return map;
    }
}
