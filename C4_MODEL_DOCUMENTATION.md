# Structurizr C4 Model - Resilience PoC

Este archivo contiene la definición completa del modelo C4 para la implementación de Resilience PoC.

## Cómo usar

### Opción 1: Importar a structurizr.com (RECOMENDADO)
1. Ve a https://structurizr.com/dsl
2. Copia el contenido de `structurizr-c4-model.dsl`
3. Pégalo en el editor
4. Presiona "Parse" para visualizar

### Opción 2: Usar Structurizr CLI
```bash
# Instalar CLI
npm install -g @structurizr/cli

# Exportar a diferentes formatos
structurizr push .

# O generar HTML local
structurizr export --format=html --output=.
```

## Estructura del Modelo

### Nivel 1: System Context
- **User**: CI/CD Pipeline externo
- **Resilience System**: Sistema de detección y resolución de fallos
- **Sistemas Externos**: Elasticsearch, PostgreSQL

### Nivel 2: Container Architecture (11 contenedores)

#### Generadores de Eventos
- **Pipeline Simulator**: Simula fallos en pipelines, publica pipeline.event

#### Pipeline de Detección → Clasificación → Decisión → Resolución
1. **Failure Detector**: Escucha pipeline.event, publica failure.detected
2. **Failure Classifier**: Clasifica fallos, publica failure.classified (Category + Severity)
3. **Decision Engine**: Consulta reglas, decide acción, publica remediation.command
4. **Failure Solver**: Ejecuta acciones (retry, cache_clean, dependency_substitution), publica remediation.result

#### Capas de Apoyo
- **Event Registry**: Audit trail en PostgreSQL (events_audit table)
- **Impact Evaluator**: Correlaciona eventos, calcula impacto
- **Observability**: Envía logs a Elasticsearch
- **Rules Manager**: API REST para gestión de reglas (FastAPI en puerto 8000)

#### Infraestructura
- **RabbitMQ**: Exchanges (cicd, resilience), queues, health check
- **PostgreSQL**: events_audit, rules tables
- **Elasticsearch**: resilience-logs index

### Nivel 3: Component Architecture (Dentro de cada servicio)

#### Common Library (Shared across all services)
- **config/settings.py**: 120 retries × 1s delay, env var injection
- **logging/elastic_logger.py**: ElasticLogger.log(level, message, **fields)
- **messaging/rabbitmq_client.py**: RabbitMQClient wrapper con ConsumeSpec
- **events/schemas.py**: Shared DTOs

#### Failure Detector Components
- **app.py**: Bootstrap consumer
- **detection_rules.py**: Evaluates DetectionRules
- **Detector logic**: Returns DetectionResult

#### Failure Classifier Components
- **app.py**: Bootstrap consumer
- **classifier.py**: Maps to Category/Severity
- **Event publisher**: AMQP sender

#### Decision Engine Components
- **app.py**: Bootstrap consumer
- **decision_engine.py**: DecisionEngine.decide(DecisionContext)
- **Context builder**: HTTP fetch de reglas
- **Action publisher**: AMQP sender

#### Failure Solver Components
- **app.py**: Bootstrap consumer
- **cache_clean.py**: Action handler
- **retry.py**: Action handler
- **dependency_substitution.py**: Action handler
- **Result publisher**: AMQP sender

### Nivel 4: Code-level Details

#### Decision Engine (Ejemplo)
```
DecisionContext: {
  pipeline_id, classification: {category, severity}, 
  impact: {score, criticality}
}
↓
DecisionEngine.decide(context) → "retry" | "cache_clean" | "dependency_substitution"
↓
HTTP GET /api/rules?category={category}&severity={severity}
↓
AMQP Publish to remediation.command: {action, parameters}
```

#### ElasticLogger (All services)
```
log.log("INFO", "Mensaje", field1=value1, field2=value2)
↓
JSON: {
  "@timestamp": "2026-04-04T...",
  "level": "INFO",
  "service": "decision_engine",
  "message": "Mensaje",
  "field1": "value1",
  "field2": "value2"
}
↓
POST http://elasticsearch:9200/resilience-logs/_doc (si está configurado)
```

#### RabbitMQClient (All services)
```
Retry Logic: 120 attempts × 1 second = 2 minutes tolerance
├─ Attempt 1-5: Local interface errors
├─ Attempt 6+: container-to-container Docker networking
└─ Success: Service healthy log output

depends_on: {condition: service_healthy} in docker-compose.yml
↓
Ensures RabbitMQ is ready before service startup
```

## Flujo de Eventos (Event Cascade)

```
1. pipeline_simulator → rabbitmq
   Publica: pipeline.event {status: "success|failed"}

2. failure_detector ← rabbitmq
   Consume: pipeline.event
   Publica: failure.detected {failure_type, detection_rules}

3. failure_classifier ← rabbitmq
   Consume: failure.detected
   Publica: failure.classified {category, severity}

4. decision_engine ← rabbitmq
   Consume: failure.classified
   HTTP: GET /api/rules
   Publica: remediation.command {action: "retry|cache_clean|dependency_substitution"}

5. failure_solver ← rabbitmq
   Consume: remediation.command
   Execute: action handler
   Publica: remediation.result {status: "success|failed"}

6. event_registry ← rabbitmq
   Consume: resilience.* → PostgreSQL events_audit table

7. impact_evaluator ← rabbitmq
   Consume: resilience.* → PostgreSQL query → Impact score

8. observability ← rabbitmq
   Consume: platform.status → Elasticsearch
```

## Configuración de Docker Compose

- **Build context**: . (raíz del proyecto)
- **Dockerfile path**: ./service/Dockerfile
- **PYTHONPATH**: /app (para imports absolutos)
- **RabbitMQ Health Check**: rabbitmq-diagnostics ping @ 5s interval
- **depends_on**: service_healthy para RabbitMQ, service_started para otros

## Notas Importantes

1. **Typo en Filename**: `common/messaging/rabbitmg_client.py` (notar "rabbitmg" en lugar de "rabbitmq")
   - Importes correctos en `common/messaging/__init__.py`

2. **Log Signature**: `ElasticLogger.log(level: str, message: str, **fields)` 
   - Requiere argumentos posicionales level y message

3. **Resilience**: 
   - 120 reintentos @ 1s cada uno = 2 minutos de tolerancia
   - RabbitMQ health check + depends_on evita race conditions

4. **Exchanges**:
   - `cicd`: events from external CI/CD systems
   - `resilience`: internal topic exchange (failure.*, remediation.*, obs.*)

5. **Databases**:
   - PostgreSQL: events_audit (audit trail), rules (rule definitions)
   - Elasticsearch: resilience-logs (JSON logs)
