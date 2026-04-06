workspace {

    model {
        user = person "CI/CD Pipeline" "External CI/CD system triggering resilience scenarios"
        
        # System boundary
        system = softwareSystem "Resilience System" "Detects, classifies, and resolves dependency failures in CI/CD pipelines" {
            
            # Level 2: Containers
            
            # Pipeline Event Generation
            pipeline_sim = container "Pipeline Simulator" "Python service" "Simulates CI/CD pipeline failures and publishes pipeline events" {
                # Level 3: Components
                app_ps = component "app.py" "FastAPI entry point" "Entry point, initializes RabbitMQ consumer" {
                }
                sim_engine = component "simulate_failure.py" "Failure simulation logic" "Generates pipeline events with random failure status" {
                }
                sim_app = component "Main loop" "Event publishing" "Publishes every 15s to pipeline.event exchange" {
                }
            }
            
            # Observability Aggregation
            observability_svc = container "Observability Collector" "Python service" "Aggregates observability events and forwards to Elasticsearch" {
                app_obs = component "app.py" "Consumer bootstrap" "Initializes listener on pipeline.status exchange" {
                }
                listener = component "pipeline_listener.py" "Event listener" "Captures platform events and buffers for shipping" {
                }
                elastic_shipper = component "Shipping layer" "Bulk indexing" "Batches and sends JSON logs to Elasticsearch" {
                }
            }
            
            # Event Registry (Audit Trail)
            event_registry_svc = container "Event Registry" "Python service" "Audit trail for all resilience events" {
                app_er = component "app.py" "Entry point" "Consumer on resilience exchange, routes to postgres" {
                }
                db_handler = component "Event persistence" "PostgreSQL writer" "Stores events in events_audit table" {
                }
            }
            
            # Failure Detection Layer
            failure_detect = container "Failure Detector" "Python service" "Analyzes pipeline events and detects failures" {
                app_fd = component "app.py" "Consumer bootstrap" "Listens on pipeline.event, triggers detection" {
                }
                detection_rules_engine = component "detection_rules.py" "Rule evaluation" "Evaluates DetectionRules against pipeline status" {
                }
                detector = component "Detector logic" "Failure classification" "Returns DetectionResult (status, failure_type)" {
                }
            }
            
            # Failure Classification Layer
            failure_class = container "Failure Classifier" "Python service" "Categorizes detected failures by type and severity" {
                app_fc = component "app.py" "Consumer bootstrap" "Listens on failure.detected exchange" {
                }
                classifier = component "classifier.py" "Classification logic" "Maps failure types to Category (NETWORK, DEPENDENCY, etc) and Severity" {
                }
                output = component "Event publisher" "AMQP sender" "Publishes Classification to failure.classified exchange" {
                }
            }
            
            # Decision Engine Layer
            decision_eng = container "Decision Engine" "Python service" "Decides remediation action based on classification" {
                app_de = component "app.py" "Consumer bootstrap" "Listens on failure.classified exchange" {
                }
                engine = component "decision_engine.py" "Decision logic" "DecisionEngine.decide(DecisionContext) -> action" {
                }
                context_builder = component "Context builder" "Rule lookup" "Fetches rules from rules_service via HTTP" {
                }
                publisher = component "Action publisher" "AMQP sender" "Publishes action to remediation.command exchange" {
                }
            }
            
            # Impact Evaluation Layer
            impact_eval = container "Impact Evaluator" "Python service" "Measures impact of failure before remediation" {
                app_ie = component "app.py" "Consumer bootstrap" "Listens on all resilience.* events" {
                }
                matrix = component "impact_matrix.py" "Impact calculation" "ImpactMatrix.evaluate() -> Impact(score, criticality)" {
                }
                correlator = component "Event correlator" "Postgres reader" "Queries events_audit for context" {
                }
            }
            
            # Failure Solver (Remediation Executor)
            failure_solv = container "Failure Solver" "Python service" "Executes remediation actions" {
                app_fs = component "app.py" "Consumer bootstrap" "Listens on remediation.command exchange" {
                }
                cache_clean = component "cache_clean.py" "Cache action" "Clears local/shared caches" {
                }
                retry_handler = component "retry.py" "Retry action" "Initiates dependent package retry" {
                }
                dep_subst = component "dependency_substitution.py" "Substitution action" "Swaps to alternate dependency version" {
                }
                result_pub = component "Result publisher" "AMQP sender" "Publishes action result to remediation.result" {
                }
            }
            
            # Rules Management (API)
            rules_mgr = container "Rules Manager" "FastAPI service" "REST API for rule management and queries" {
                api = component "REST endpoints" "FastAPI routes" "GET/POST rules, GET rule/{id}, POST evaluate" {
                }
                rules_engine = component "Rules engine" "In-memory + JSON" "Loads rules.json, evaluates contexts" {
                }
                db_conn = component "PostgreSQL connector" "SQL driver" "Queries event history for context" {
                }
            }
            
            # Message Broker
            rabbitmq = container "RabbitMQ" "AMQP broker" "Message broker for asynchronous event routing" {
                cicd_ex = component "cicd exchange" "Direct exchange" "External CI/CD events (fanout)" {
                }
                resilience_ex = component "resilience exchange" "Topic exchange" "Internal resilience events (topic routing)" {
                }
                queues = component "Message queues" "Durable queues" "Per-service consumer queues with auto_ack=False" {
                }
                health = component "Health probe" "rabbitmq-diagnostics" "Docker Compose health check endpoint" {
                }
            }
            
            # Persistence Layer
            postgres_db = container "PostgreSQL" "Relational DB" "Audit trail and system state" {
                audit_table = component "events_audit table" "Schema" "Stores all resilience events with context" {
                }
                rules_table = component "rules table" "Schema" "Stores detection and remediation rules" {
                }
            }
            
            # Observability Backend
            elastic_search = container "Elasticsearch" "Search & analytics" "Centralized logging and metrics" {
                index = component "resilience-logs index" "Logstash-style" "JSON logs from all services via HTTP _doc API" {
                }
            }
            
            # Common Library (Shared)
            common_lib = container "Common Library" "Python package" "Shared utilities across all services" {
                config_mod = component "config/settings.py" "Configuration" "Settings dataclass with env var injection (120 RabbitMQ retries)" {
                }
                logging_mod = component "logging/elastic_logger.py" "Structured logging" "ElasticLogger.log(level, message, **fields) with ES shipping" {
                }
                messaging_mod = component "messaging/rabbitmq_client.py" "AMQP client" "RabbitMQClient wrapper around Pika with ConsumeSpec" {
                }
                events_mod = component "events/schemas.py" "Event schemas" "Shared DTO classes for events (schemas, types)" {
                }
            }
        }
        
        # External Systems
        elasticsearch_external = softwareSystem "Elasticsearch Cluster" "External observability backend" {
        }
        
        postgres_external = softwareSystem "PostgreSQL Server" "External database server" {
        }
        
        # Relationships

        # User to System
        user -> pipeline_sim "Triggers failure simulation"
        user -> rules_mgr "Manages detection/remediation rules"
        
        # Pipeline Simulator flow
        pipeline_sim -> rabbitmq "Publishes pipeline.event (status: success/failed)"
        
        # Event cascade through resilience system
        rabbitmq -> failure_detect "Consumes pipeline.event"
        failure_detect -> rabbitmq "Publishes failure.detected"
        
        rabbitmq -> failure_class "Consumes failure.detected"
        failure_class -> rabbitmq "Publishes failure.classified"
        
        rabbitmq -> decision_eng "Consumes failure.classified"
        decision_eng -> rules_mgr "HTTP GET rules for context"
        decision_eng -> rabbitmq "Publishes remediation.command (action: retry|cache_clean|dependency_substitution)"
        
        rabbitmq -> failure_solv "Consumes remediation.command"
        failure_solv -> rabbitmq "Publishes remediation.result (status: success|failed)"
        
        # Audit & Observability
        rabbitmq -> event_registry_svc "Consumes resilience.* events"
        event_registry_svc -> postgres_db "Stores events_audit"
        
        rabbitmq -> impact_eval "Consumes resilience.* events for correlation"
        impact_eval -> postgres_db "Queries events_audit for context"
        
        rabbitmq -> observability_svc "Consumes platform.status events"
        observability_svc -> elasticsearch_external "Bulk indexes JSON logs"
        
        # Common library dependencies
        pipeline_sim -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        failure_detect -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        failure_class -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        decision_eng -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        failure_solv -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        event_registry_svc -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        impact_eval -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        observability_svc -> common_lib "Imports Settings, ElasticLogger, RabbitMQClient"
        rules_mgr -> common_lib "Imports Settings, ElasticLogger"
        
        # Database access
        rules_mgr -> postgres_external "Query rules and events"
        postgres_db -> postgres_external "External database"
        
        # Observability
        elastic_search -> elasticsearch_external "External Elasticsearch"
    }

    views {
        # Level 1: System Context
        systemContext system {
            include *
            autolayout lr
            title "Resilience - System Context (C4 L1)"
            description "High-level view showing external actors and the resilience system."
        }
        
        # Level 2: Container Architecture
        container system {
            include *
            autolayout tb
            title "Resilience - Container Architecture (C4 L2)"
            description "Main services, databases, and message broker. Shows async event flow through resilience pipeline."
        }
        
        # Level 3a: Failure Detection Component Diagram
        component failure_detect {
            include *
            autolayout lr
            title "Failure Detector - Components (C4 L3)"
            description "Internal components of failure detection service: bootstrap, rule evaluation, detection logic."
        }
        
        # Level 3b: Failure Classification Component Diagram
        component failure_class {
            include *
            autolayout lr
            title "Failure Classifier - Components (C4 L3)"
            description "Internal components of failure classification service: bootstrap, classifier logic, publisher."
        }
        
        # Level 3c: Decision Engine Component Diagram
        component decision_eng {
            include *
            autolayout lr
            title "Decision Engine - Components (C4 L3)"
            description "Internal components: bootstrap, decision logic, rule lookup, action publishing."
        }
        
        # Level 3d: Failure Solver Component Diagram
        component failure_solv {
            include *
            autolayout lr
            title "Failure Solver - Components (C4 L3)"
            description "Internal components: bootstrap, action handlers (cache_clean, retry, dependency_substitution), result publisher."
        }
        
        # Level 3e: Common Library Components
        component common_lib {
            include *
            autolayout tb
            title "Common Library - Modules (C4 L3)"
            description "Shared Python modules: configuration, structured logging, AMQP client, event schemas."
        }
        
        # Level 3f: RabbitMQ Internal Structure
        component rabbitmq {
            include *
            autolayout tb
            title "RabbitMQ - Internal Structure (C4 L3)"
            description "Message exchanges (cicd, resilience), durable queues, and health check probe."
        }
        
        # Level 4: Code classes (example - Decision Engine)
        component decision_eng {
            include *
            autolayout lr
            title "Decision Engine - Code Classes (C4 L4)"
            description "app.py orchestrates consumer bootstrap. decision_engine.py contains DecisionEngine class with decide() method. HTTP client fetches rules, AMQP publisher sends actions."
        }
    }

    configuration {
        scope softwareSystem
    }
}
