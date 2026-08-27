package com.ae8.occ.dto;

import java.util.ArrayList;
import java.util.List;

public class ApiResult<T> {

    private int code;
    private String message;
    private T data;

    public static <T> ApiResult<T> ok(T data) {
        ApiResult<T> result = new ApiResult<>();
        result.setCode(0);
        result.setMessage("success");
        result.setData(data);
        return result;
    }

    public static <T> ApiResult<T> fail(String message) {
        ApiResult<T> result = new ApiResult<>();
        result.setCode(-1);
        result.setMessage(message);
        result.setData(null);
        return result;
    }

    public static ApiResult<List<String>> emptyList() {
        return ok(new ArrayList<>());
    }

    public int getCode() {
        return code;
    }

    public void setCode(int code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }
}
