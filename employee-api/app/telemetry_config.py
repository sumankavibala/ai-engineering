import logging

logger = logging.getLogger(__name__)


def setup_opentelemetry(app):
    """Setup OpenTelemetry instrumentation for FastAPI."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create(attributes={"service.name": "employee-api"})
        provider = TracerProvider(resource=resource)

        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)

        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app)
            logger.info("opentelemetry_fastapi_instrumented")
        except Exception as e:
            logger.warning(f"opentelemetry_instrumentation_failed: {e}")

    except ImportError:
        logger.info("opentelemetry_package_not_installed_skipping")
    except Exception as exc:
        logger.warning(f"opentelemetry_setup_skipped: {exc}")
