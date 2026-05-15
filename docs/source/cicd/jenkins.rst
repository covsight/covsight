#######
Jenkins
#######

The declarative pipeline below merges coverage, publishes a Cobertura report
via the Jenkins Cobertura plugin, and generates an HTML report artifact.

Prerequisites
=============

Install the `Cobertura Plugin <https://plugins.jenkins.io/cobertura/>`_
(or `JaCoCo Plugin <https://plugins.jenkins.io/jacoco/>`_) in Jenkins.

Full Pipeline Example
=====================

.. code-block:: groovy

    pipeline {
        agent any

        stages {
            stage('Test') {
                steps {
                    sh 'make run_all_tests'  // produces test_*.ncdb
                }
            }

            stage('Coverage') {
                steps {
                    sh 'pip install covsight'

                    // Merge all test coverage files
                    sh 'covsight merge -o merged.ncdb test_*.ncdb'

                    // Coverage gate
                    sh '''
                        COV=$(covsight show summary merged.ncdb -of json | jq -r '.overall_coverage')
                        echo "Coverage: ${COV}%"
                        python3 -c "import sys; sys.exit(0 if float('$COV') >= 80 else 1)" \
                            || { echo "Coverage below 80%"; exit 1; }
                    '''

                    // Export Cobertura for Jenkins plugin
                    sh 'covsight show code-coverage merged.ncdb --output-format cobertura > coverage.xml'

                    // Generate HTML report
                    sh 'covsight report merged.ncdb -of html -o coverage_report.html'
                }

                post {
                    always {
                        cobertura coberturaReportFile: 'coverage.xml',
                                  failUnhealthy: false,
                                  failUnstable: false

                        archiveArtifacts artifacts: 'coverage_report.html'
                    }
                }
            }
        }
    }

JaCoCo Variant
==============

Replace the Cobertura steps with:

.. code-block:: groovy

    sh 'covsight show code-coverage merged.ncdb --output-format jacoco > jacoco.xml'

    post {
        always {
            jacoco execPattern: 'jacoco.xml'
        }
    }

Verilator Projects
==================

.. code-block:: groovy

    sh 'covsight merge --input-format vltcov -o merged.ncdb tests/*/coverage.dat'
