pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Install dependencies') {
            steps {
                sh 'python3 -m venv .venv'
                sh '.venv/bin/pip install -r requirements.txt'
            }
        }
        stage('Run tests') {
            steps { sh '.venv/bin/pytest -q' }
        }
        stage('Build Docker image') {
            steps { sh 'docker build -t classic-ir-demo .' }
        }
    }
    post {
        always { echo 'Classic IR Demonstrator pipeline finished.' }
    }
}
