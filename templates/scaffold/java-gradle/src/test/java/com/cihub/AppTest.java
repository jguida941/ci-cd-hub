package com.cihub;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * CI/CD Hub Scaffold - Sample Tests.
 *
 * <p>These tests demonstrate:
 * <ul>
 *   <li>JUnit 5 test discovery</li>
 *   <li>Basic assertions (for coverage metrics)</li>
 *   <li>Mutation-killable logic (for PITest)</li>
 * </ul>
 *
 * <p>Run with: ./gradlew test
 * <p>Coverage: ./gradlew jacocoTestReport
 */
class AppTest {
    @Test
    void multiplyMultipliesNumbers() {
        assertEquals(6, App.multiply(2, 3));
    }
}
