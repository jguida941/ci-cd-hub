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
 * <p>Run with: mvn test
 * <p>Coverage: mvn jacoco:report
 */
class AppTest {
    @Test
    void addAddsNumbers() {
        assertEquals(5, App.add(2, 3));
    }
}
