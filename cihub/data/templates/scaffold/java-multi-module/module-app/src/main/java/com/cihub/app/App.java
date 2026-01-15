package com.cihub.app;

import com.cihub.core.Calculator;

/**
 * Application that uses the core module.
 */
public class App {

    private final Calculator calculator = new Calculator();

    /**
     * Calculate sum using core module.
     */
    public int calculateSum(int a, int b) {
        return calculator.add(a, b);
    }

    /**
     * Main entry point.
     */
    public static void main(String[] args) {
        App app = new App();
        System.out.println("2 + 3 = " + app.calculateSum(2, 3));
    }
}
