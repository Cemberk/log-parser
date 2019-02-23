pipeline {
  agent any
  stages {
    stage('Build') {
      parallel {
        stage('Build') {
          steps {
            echo 'Hello'
          }
        }
        stage('Build2') {
          steps {
            echo 'World'
          }
        }
      }
    }
    stage('Test') {
      steps {
        echo 'This is test'
      }
    }
  }
}