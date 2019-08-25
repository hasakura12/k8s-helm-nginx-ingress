Feature: Expose /healthz endpoint
  Scenario: Consume http://localhost:8080/healthz
    When a Nginx container is running
    Then I make GET request to http://localhost:8080/healthz then I should receive 200
