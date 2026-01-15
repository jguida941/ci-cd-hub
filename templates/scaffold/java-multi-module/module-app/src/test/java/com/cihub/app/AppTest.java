package com.cihub.app;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class AppTest {

    @Test
    void testCalculateSum() {
        App app = new App();
        assertEquals(5, app.calculateSum(2, 3));
    }
}
