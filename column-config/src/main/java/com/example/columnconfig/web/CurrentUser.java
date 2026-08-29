package com.example.columnconfig.web;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * Resolves the current user from X-User-Id. Replace with SecurityContext in a real SSO setup.
 */
public final class CurrentUser {

    public static final String HEADER = "X-User-Id";

    private CurrentUser() {
    }

    public static String require() {
        RequestAttributes attributes = RequestContextHolder.getRequestAttributes();
        if (attributes instanceof ServletRequestAttributes servletAttributes) {
            HttpServletRequest request = servletAttributes.getRequest();
            String userId = request.getHeader(HEADER);
            if (StringUtils.hasText(userId)) {
                return userId.trim();
            }
        }
        throw new IllegalStateException("Missing login user, header " + HEADER + " is required");
    }
}
