pipeline {
    agent any
    
    }

    environment {
        PYTHON = "C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python314\\python.exe"
    }

    stages {

        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                bat "\"${PYTHON}\" --version"
            }
        }

        stage('Install Dependencies') {
            steps {
                bat "\"${PYTHON}\" -m ensurepip --upgrade"
                bat "\"${PYTHON}\" -m pip install --upgrade pip"
                bat "\"${PYTHON}\" -m pip install -r requirements.txt"
            }
        }

        stage('Run Script') {
            steps {
                bat "\"${PYTHON}\" barcelona_match_alert.py"
            }
        }
    }

    post {
        success {
            echo 'Build completed successfully 🎉'
        }
        failure {
            echo 'Build failed ❌ Check logs above'
        }
    }
