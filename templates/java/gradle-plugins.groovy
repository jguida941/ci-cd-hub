/*
 * CI/CD Hub - Gradle Plugin Snippets (config-driven)
 * ==================================================
 * Add only the plugins for tools enabled in .ci-hub.yml.
 *
 * These snippets are parsed and inserted into build.gradle files
 * by the `cihub fix-gradle` command.
 *
 * IMPORTANT: Gradle requires plugins to be declared before tasks can run.
 * Unlike Maven, you can't just invoke a plugin goal on-the-fly.
 */

// ============================================================================
// PLUGIN BLOCK SNIPPETS
// Format: // @plugin:<plugin-id>
// ============================================================================

// @plugin:jacoco
// JaCoCo - Code Coverage (enabled by default)
id 'jacoco'

// @plugin:checkstyle
// Checkstyle - Code Style (enabled by default)
id 'checkstyle'

// @plugin:com.github.spotbugs
// SpotBugs - Bug Detection (enabled by default)
id 'com.github.spotbugs' version '6.0.7'

// @plugin:pmd
// PMD - Static Analysis (enabled by default)
id 'pmd'

// @plugin:info.solidsoft.pitest
// PITest - Mutation Testing (enabled by default, expensive)
id 'info.solidsoft.pitest' version '1.15.0'

// @plugin:org.owasp.dependencycheck
// OWASP Dependency Check - Vulnerability Scanning (enabled by default)
id 'org.owasp.dependencycheck' version '9.0.9'

// ============================================================================
// CONFIGURATION BLOCK SNIPPETS
// Format: // @config:<plugin-id>
// ============================================================================

// @config:jacoco
jacoco {
    toolVersion = "0.8.11"
}

jacocoTestReport {
    dependsOn test
    reports {
        xml.required = true
        html.required = true
    }
}

// @config:checkstyle
checkstyle {
    toolVersion = '10.12.5'
    maxWarnings = 0
    ignoreFailures = false
}

// @config:com.github.spotbugs
spotbugs {
    toolVersion = '4.8.3'
    ignoreFailures = false
    effort = 'max'
    reportLevel = 'low'
}

spotbugsMain {
    reports {
        xml.required = true
        html.required = true
    }
}

// @config:pmd
pmd {
    toolVersion = '7.0.0'
    consoleOutput = true
    ruleSetFiles = files("config/pmd/ruleset.xml")
    ruleSets = []
    ignoreFailures = false
}

// @config:info.solidsoft.pitest
pitest {
    junit5PluginVersion = '1.2.1'
    targetClasses = ['com.example.*']
    targetTests = ['com.example.*']
    threads = 4
    outputFormats = ['XML', 'HTML']
    timestampedReports = false
}

// @config:org.owasp.dependencycheck
dependencyCheck {
    format = 'ALL'
    failBuildOnCVSS = 11
    suppressionFile = 'config/owasp/suppressions.xml'
}

/*
 * Tools that do NOT require build.gradle changes:
 * - CodeQL, Semgrep, Trivy, Docker (run in GitHub Actions)
 * - jqwik is a dependency, not a Gradle plugin
 */
