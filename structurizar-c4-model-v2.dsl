workspace "CI/CD Resilience System" "Corrected C4 Model" {

  model {

    /********************
     * Personas
     ********************/
    developer = person "Developer" "Pushes code that triggers CI/CD pipelines"
    devops = person "DevOps Engineer" "Configures rules and supervises resilience behavior"

    /********************
     * Sistemas externos
     ********************/
    cicd = softwareSystem "CI/CD Pipeline" "External CI/CD system emitting pipeline execution events"
    elastic_ext = softwareSystem "Elasticsearch" "Centralized logging and observability backend"
    postgres_ext = softwareSystem "PostgreSQL" "External database for audit and traceability"

    /********************
     * Sistema principal
     ********************/
    resilience = softwareSystem "CI/CD Resilience System" "Detects, classifies and remediates dependency resolution failures" {

      pipeline_sim = container "Pipeline Simulator" "Python" "Simulates CI/CD dependency failures and emits pipeline events"

      observability = container "Observability Collector" "Python" "Collects pipeline and resilience events and ships logs to Elasticsearch"

      detector = container "Failure Detector" "Python" "Detects dependency-related failures in pipeline events"

      classifier = container "Failure Classifier" "Python" "Classifies detected failures by category and severity"

      impact_eval = container "Impact Evaluator" "Python" "Evaluates impact and criticality of classified failures"

      decision_engine = container "Decision Engine" "Python" "Selects remediation strategy using deterministic rules"

      remediator = container "Remediation Executor" "Python" "Executes remediation actions (retry, cache clean, substitution)"

      rules_api = container "Rules Manager API" "FastAPI" "Allows DevOps to manage remediation rules via REST"

      event_registry = container "Event Registry" "Python" "Stores audit trail of all resilience events"

      rabbitmq = container "RabbitMQ" "AMQP" "Asynchronous event broker for the resilience pipeline"

      postgres = container "PostgreSQL" "RDBMS" "Stores audit events and remediation results"
    }

    /********************
     * Relaciones
     ********************/
    developer -> cicd "Pushes code"
    cicd -> pipeline_sim "Triggers simulated pipeline runs"

    pipeline_sim -> rabbitmq "Publishes pipeline.event"

    rabbitmq -> detector "Consumes pipeline.event"
    detector -> rabbitmq "Publishes failure.detected"

    rabbitmq -> classifier "Consumes failure.detected"
    classifier -> rabbitmq "Publishes failure.classified"

    rabbitmq -> impact_eval "Consumes failure.classified"
    impact_eval -> rabbitmq "Publishes failure.impact"

    rabbitmq -> decision_engine "Consumes failure.impact"
    decision_engine -> rules_api "Fetches rules (HTTP)"
    decision_engine -> rabbitmq "Publishes remediation.command"

    rabbitmq -> remediator "Consumes remediation.command"
    remediator -> rabbitmq "Publishes remediation.result"

    rabbitmq -> event_registry "Consumes all resilience.* events"
    event_registry -> postgres "Stores audit records"

    rabbitmq -> observability "Consumes pipeline and resilience events"
    observability -> elastic_ext "Indexes logs"

    rules_api -> postgres "Stores and retrieves rules"
    impact_eval -> postgres "Queries audit context"

    postgres -> postgres_ext "Hosted on external DB server"
  }

  views {

    systemContext resilience {
      include *
      autolayout lr
      title "C4 – System Context"
      description "External actors and systems interacting with the CI/CD Resilience System."
    }

    container resilience {
      include *
      autolayout tb
      title "C4 – Container Diagram"
      description "Deployable services composing the CI/CD Resilience System."
    }

    component detector {
      include *
      autolayout lr
      title "Failure Detector – Components"
      description "Bootstrap and detection logic."
    }

    component decision_engine {
      include *
      autolayout lr
      title "Decision Engine – Components"
      description "Decision logic, rule retrieval and action publishing."
    }

    component remediator {
      include *
      autolayout lr
      title "Remediation Executor – Components"
      description "Action handlers and remediation result publishing."
    }

    theme default
  }

  configuration {
    scope softwareSystem
  }
}