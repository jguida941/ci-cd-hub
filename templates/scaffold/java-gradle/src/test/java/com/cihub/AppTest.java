package com.cihub;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AppTest {
    @Test
    void multiplyMultipliesNumbers() {
        assertEquals(6, App.multiply(2, 3));
    }
}
