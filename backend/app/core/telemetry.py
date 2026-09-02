from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from app.core.config import get_settings

settings = get_settings()


def setup_telemetry(app: FastAPI) -> None:
    resource = Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME})

    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    otlp_trace_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,
    )
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        ),
        export_interval_millis=settings.OTEL_METRICS_EXPORT_INTERVAL_MS,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=trace_provider)
    SQLAlchemyInstrumentor().instrument(engine=None, tracer_provider=trace_provider)
    RedisInstrumentor().instrument(tracer_provider=trace_provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=trace_provider)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    return metrics.get_meter(name)


class TracedOperation:
    def __init__(self, tracer: trace.Tracer, operation_name: str, attributes: dict = None):
        self.tracer = tracer
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.span = None

    def __enter__(self):
        self.span = self.tracer.start_span(self.operation_name, attributes=self.attributes)
        self.span.__enter__()
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))
        self.span.__exit__(exc_type, exc_val, exc_tb)


def trace_operation(operation_name: str, attributes: dict = None):
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with TracedOperation(tracer, operation_name, attributes) as _span:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with TracedOperation(tracer, operation_name, attributes) as _span:
                return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
