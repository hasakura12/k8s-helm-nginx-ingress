Feature: Expose Nginx monitoring endpoint at localhost:8081
  Scenario: Consume monitoring endpoint at localhost:8081
    When a Nginx container is running
    Then I make GET request to localhost:8081 and I receive 200 response with details from /nginx_status