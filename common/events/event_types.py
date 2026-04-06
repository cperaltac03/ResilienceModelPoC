class Exchanges:
    CICD = "cicd"
    RESILIENCE = "resilience"


class RoutingKeys:
    # Entrada desde pipeline CI/CD (simulado)
    PIPELINE_EVENT = "pipeline.event"

    # Flujo interno resiliencia (pipeline pattern)
    OBS_EVENT = "obs.event"
    FAILURE_DETECTED = "failure.detected"
    FAILURE_CLASSIFIED = "failure.classified"
    FAILURE_IMPACT = "failure.impact"
    REMEDIATION_COMMAND = "remediation.command"
    REMEDIATION_RESULT = "remediation.result"

    # Auditoría general (wildcard usado por registro_eventos)
    ALL = "#"


class EventTypes:
    PIPELINE_RUN = "pipeline_run"
    OBSERVABILITY_EVENT = "observability_event"
    DEP_FAILURE_DETECTED = "dependency_failure_detected"
    DEP_FAILURE_CLASSIFIED = "dependency_failure_classified"
    DEP_FAILURE_IMPACT = "dependency_failure_impact_evaluated"
    REMEDIATION_COMMAND = "remediation_command"
    REMEDIATION_RESULT = "remediation_result"