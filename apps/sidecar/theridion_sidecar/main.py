"""FastAPI sidecar entrypoint.

Runs as a localhost-only HTTP server consumed by the Tauri shell over
loopback. Port is selected dynamically and printed to stdout on startup so
the parent process can read it; if THERIDION_PORT is set, that port is used
instead (handy in dev).
"""

from __future__ import annotations

import atexit
import os
import socket
import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from theridion_sidecar import __version__, storage
from theridion_sidecar.api.advanced import router as advanced_router
from theridion_sidecar.api.apidocs import router as apidocs_router
from theridion_sidecar.api.batchrunner import router as batch_router
from theridion_sidecar.api.ai import router as ai_router
from theridion_sidecar.api.assertions import router as assertions_router
from theridion_sidecar.api.chaining import router as chaining_router
from theridion_sidecar.api.codegen import router as codegen_router
from theridion_sidecar.api.collections import router as collections_router
from theridion_sidecar.api.cookies import router as cookies_router
from theridion_sidecar.api.curl import router as curl_router
from theridion_sidecar.api.diagnostics import router as diagnostics_router
from theridion_sidecar.api.envdiff import router as envdiff_router
from theridion_sidecar.api.examples import router as examples_router
from theridion_sidecar.api.environments import router as environments_router
from theridion_sidecar.api.extras import router as extras_router
from theridion_sidecar.api.favorites import router as favorites_router
from theridion_sidecar.api.globals import router as globals_router
from theridion_sidecar.api.graphql import router as graphql_router
from theridion_sidecar.api.grpc_api import router as grpc_router
from theridion_sidecar.api.health import router as health_router
from theridion_sidecar.api.importer import router as importer_router
from theridion_sidecar.api.kafka import router as kafka_router
from theridion_sidecar.api.load_runner import router as load_runner_router
from theridion_sidecar.api.loadtest import router as loadtest_router
from theridion_sidecar.api.mock import router as mock_router
from theridion_sidecar.api.mock_record import replay_router as mock_replay_router
from theridion_sidecar.api.mock_record import router as mock_record_router
from theridion_sidecar.api.multipart import router as multipart_router
from theridion_sidecar.api.oauth2 import router as oauth2_router
from theridion_sidecar.api.projects import router as projects_router
from theridion_sidecar.api.requests import router as requests_router
from theridion_sidecar.api.runner import router as runner_router
from theridion_sidecar.api.schema_validation import router as schema_router
from theridion_sidecar.api.scripts import router as scripts_router
from theridion_sidecar.api.servicemap import router as servicemap_router
from theridion_sidecar.api.soap import router as soap_router
from theridion_sidecar.api.testgen import router as testgen_router
from theridion_sidecar.api.timeline import router as timeline_router
from theridion_sidecar.api.websocket import router as websocket_router
from theridion_sidecar.api.workspace import router as workspace_router
from theridion_sidecar.api.response_trends import router as response_trends_router
from theridion_sidecar.api.security_audit import router as security_audit_router
from theridion_sidecar.api.ssl_inspect import router as ssl_inspect_router
from theridion_sidecar.api.dns_inspect import router as dns_inspect_router
from theridion_sidecar.api.compression_stats import router as compression_stats_router
from theridion_sidecar.api.redirect_chain import router as redirect_chain_router
from theridion_sidecar.api.content_type_validator import router as content_type_validator_router
from theridion_sidecar.api.loadtest_patterns import router as loadtest_patterns_router
from theridion_sidecar.api.latency_histogram import router as latency_histogram_router
from theridion_sidecar.api.throughput_timeline import router as throughput_timeline_router
from theridion_sidecar.api.connection_stats import router as connection_stats_router
from theridion_sidecar.api.user_simulation import router as user_simulation_router
from theridion_sidecar.api.sla_check import router as sla_check_router
from theridion_sidecar.api.loadtest_compare import router as loadtest_compare_router
from theridion_sidecar.api.flow_graph import router as flow_graph_router
from theridion_sidecar.api.retry_tester import router as retry_tester_router
from theridion_sidecar.api.ratelimit_detect import router as ratelimit_detect_router
from theridion_sidecar.api.idempotency_check import router as idempotency_check_router
from theridion_sidecar.api.pagination_walker import router as pagination_walker_router
from theridion_sidecar.api.contract_drift import router as contract_drift_router
from theridion_sidecar.api.multi_env_runner import router as multi_env_runner_router
from theridion_sidecar.api.data_generator import router as data_generator_router
from theridion_sidecar.api.waterfall import router as waterfall_router
from theridion_sidecar.api.curl_log import router as curl_log_router
from theridion_sidecar.api.mock_diff import router as mock_diff_router
from theridion_sidecar.api.error_patterns import router as error_patterns_router
from theridion_sidecar.api.custom_dashboard import router as custom_dashboard_router
from theridion_sidecar.api.jwt_inspect import router as jwt_inspect_router
from theridion_sidecar.api.token_refresh import router as token_refresh_router
from theridion_sidecar.api.cors_test import router as cors_test_router
from theridion_sidecar.api.injection_scan import router as injection_scan_router
from theridion_sidecar.api.sensitive_data import router as sensitive_data_router
from theridion_sidecar.api.ws_security import router as ws_security_router
from theridion_sidecar.api.mtom import router as mtom_router
from theridion_sidecar.api.wsdl_refactor import router as wsdl_refactor_router
from theridion_sidecar.api.soap_coverage import router as soap_coverage_router
from theridion_sidecar.api.jdbc_query import router as jdbc_query_router
from theridion_sidecar.api.xsd_validator import router as xsd_validator_router
from theridion_sidecar.api.wsdl_mock_gen import router as wsdl_mock_gen_router
from theridion_sidecar.api.oauth1 import router as oauth1_router
from theridion_sidecar.api.visual_test_builder import router as visual_test_builder_router
from theridion_sidecar.api.data_loop import router as data_loop_router
from theridion_sidecar.api.flows import router as flows_router
from theridion_sidecar.api.monitors import router as monitors_router
from theridion_sidecar.api.webhooks import router as webhooks_router
from theridion_sidecar.api.body_modes import router as body_modes_router
from theridion_sidecar.api.cookie_manager import router as cookie_manager_router
from theridion_sidecar.api.request_console import router as request_console_router
from theridion_sidecar.api.visualizer import router as visualizer_router
from theridion_sidecar.api.keybindings import router as keybindings_router
from theridion_sidecar.api.collection_docs import router as collection_docs_router
from theridion_sidecar.api.api_catalog import router as api_catalog_router
from theridion_sidecar.api.api_governance import router as api_governance_router
from theridion_sidecar.api.api_versioning import router as api_versioning_router
from theridion_sidecar.api.openapi_sync import router as openapi_sync_router
from theridion_sidecar.api.collection_branching import router as collection_branching_router
from theridion_sidecar.api.project_encryption import router as project_encryption_router
from theridion_sidecar.api.secret_encryption import router as secret_encryption_router
from theridion_sidecar.api.secret_managers import router as secret_managers_router
from theridion_sidecar.api.pac_proxy import router as pac_proxy_router
from theridion_sidecar.api.cookie_scripting import router as cookie_scripting_router
from theridion_sidecar.api.junit_reporter import router as junit_reporter_router
from theridion_sidecar.api.cli_reporters import router as cli_reporters_router
from theridion_sidecar.api.team_workspaces import router as team_workspaces_router
from theridion_sidecar.api.integrations import router as integrations_router
from theridion_sidecar.api.healing import router as healing_router
from theridion_sidecar.api.mcp_server import router as mcp_server_router
from theridion_sidecar.api.bru_format import router as bru_format_router
from theridion_sidecar.api.yaml_collections import router as yaml_collections_router
from theridion_sidecar.api.composite_project import router as composite_project_router
from theridion_sidecar.api.conversational_ai import router as conversational_ai_router
from theridion_sidecar.api.vscode_api import router as vscode_api_router
from theridion_sidecar.api.agent_explorer import router as agent_explorer_router
from theridion_sidecar.api.replay import router as replay_router
from theridion_sidecar.api.contract_guard import router as contract_guard_router
from theridion_sidecar.api.variable_inspector import router as variable_inspector_router
from theridion_sidecar.api.semantic_diff import router as semantic_diff_router
from theridion_sidecar.api.owasp_scanner import router as owasp_scanner_router
from theridion_sidecar.api.har_export import router as har_export_router
from theridion_sidecar.api.postman_export import router as postman_export_router
from theridion_sidecar.api.sse_client import router as sse_client_router
from theridion_sidecar.api.api_changelog import router as api_changelog_router
from theridion_sidecar.api.regression_gen import router as regression_gen_router
from theridion_sidecar.api.dependency_resolver import router as dependency_resolver_router
from theridion_sidecar.api.history import router as history_router
from theridion_sidecar.api.openapi_import import router as openapi_import_router
from theridion_sidecar.api.pipeline import router as pipeline_router
from theridion_sidecar.api.certificates import router as certificates_router
from theridion_sidecar.api.reports import router as reports_router
from theridion_sidecar.api.response_compare import router as response_compare_router


class _TokenAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid X-Theridion-Token header.

    Only active when THERIDION_TOKEN env var is set.  /api/health is
    exempt so liveness probes keep working.
    """

    def __init__(self, app: FastAPI, token: str) -> None:  # type: ignore[override]
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path == "/api/health":
            return await call_next(request)
        provided = request.headers.get("X-Theridion-Token", "")
        if provided != self._token:
            return JSONResponse(
                status_code=401,
                content={"detail": "invalid or missing X-Theridion-Token"},
            )
        return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Theridion sidecar",
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
    )

    # We only ever bind to 127.0.0.1, so any HTTP origin reaching us is
    # already loopback-only. Match any localhost / 127.0.0.1 port via
    # regex so dev (1420), Playwright tests (1421), and the Vite fallback
    # (5173) all work without enumerating ports here. Tauri's custom
    # protocols are matched explicitly.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^(?:https?://(?:localhost|127\.0\.0\.1)(?::\d+)?"
            r"|tauri://localhost"
            r"|https://tauri\.localhost)$"
        ),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _token = os.environ.get("THERIDION_TOKEN")
    if _token:
        app.add_middleware(_TokenAuthMiddleware, token=_token)

    app.include_router(ai_router)
    app.include_router(health_router)
    app.include_router(requests_router)
    app.include_router(codegen_router)
    app.include_router(assertions_router)
    app.include_router(runner_router)
    app.include_router(scripts_router)
    app.include_router(importer_router)
    app.include_router(collections_router)
    app.include_router(environments_router)
    app.include_router(globals_router)
    app.include_router(kafka_router)
    app.include_router(graphql_router)
    app.include_router(soap_router)
    app.include_router(cookies_router)
    app.include_router(curl_router)
    app.include_router(websocket_router)
    app.include_router(diagnostics_router)
    app.include_router(multipart_router)
    app.include_router(oauth2_router)
    app.include_router(projects_router)
    app.include_router(grpc_router)
    app.include_router(mock_router)
    app.include_router(mock_record_router)
    app.include_router(mock_replay_router)
    app.include_router(chaining_router)
    app.include_router(loadtest_router)
    app.include_router(load_runner_router)
    app.include_router(extras_router)
    app.include_router(testgen_router)
    app.include_router(advanced_router)
    app.include_router(servicemap_router)
    app.include_router(apidocs_router)
    app.include_router(timeline_router)
    app.include_router(workspace_router)
    app.include_router(schema_router)
    app.include_router(envdiff_router)
    app.include_router(examples_router)
    app.include_router(favorites_router)
    app.include_router(batch_router)
    app.include_router(response_trends_router)
    app.include_router(security_audit_router)
    app.include_router(ssl_inspect_router)
    app.include_router(dns_inspect_router)
    app.include_router(compression_stats_router)
    app.include_router(redirect_chain_router)
    app.include_router(content_type_validator_router)
    app.include_router(loadtest_patterns_router)
    app.include_router(latency_histogram_router)
    app.include_router(throughput_timeline_router)
    app.include_router(connection_stats_router)
    app.include_router(user_simulation_router)
    app.include_router(sla_check_router)
    app.include_router(loadtest_compare_router)
    app.include_router(flow_graph_router)
    app.include_router(retry_tester_router)
    app.include_router(ratelimit_detect_router)
    app.include_router(idempotency_check_router)
    app.include_router(pagination_walker_router)
    app.include_router(contract_drift_router)
    app.include_router(multi_env_runner_router)
    app.include_router(data_generator_router)
    app.include_router(waterfall_router)
    app.include_router(curl_log_router)
    app.include_router(mock_diff_router)
    app.include_router(error_patterns_router)
    app.include_router(custom_dashboard_router)
    app.include_router(jwt_inspect_router)
    app.include_router(token_refresh_router)
    app.include_router(cors_test_router)
    app.include_router(injection_scan_router)
    app.include_router(sensitive_data_router)
    app.include_router(ws_security_router)
    app.include_router(mtom_router)
    app.include_router(wsdl_refactor_router)
    app.include_router(soap_coverage_router)
    app.include_router(jdbc_query_router)
    app.include_router(xsd_validator_router)
    app.include_router(wsdl_mock_gen_router)
    app.include_router(oauth1_router)
    app.include_router(visual_test_builder_router)
    app.include_router(data_loop_router)
    app.include_router(flows_router)
    app.include_router(monitors_router)
    app.include_router(webhooks_router)
    app.include_router(body_modes_router)
    app.include_router(cookie_manager_router)
    app.include_router(request_console_router)
    app.include_router(visualizer_router)
    app.include_router(keybindings_router)
    app.include_router(collection_docs_router)
    app.include_router(api_catalog_router)
    app.include_router(api_governance_router)
    app.include_router(api_versioning_router)
    app.include_router(openapi_sync_router)
    app.include_router(collection_branching_router)
    app.include_router(project_encryption_router)
    app.include_router(secret_encryption_router)
    app.include_router(secret_managers_router)
    app.include_router(pac_proxy_router)
    app.include_router(cookie_scripting_router)
    app.include_router(junit_reporter_router)
    app.include_router(cli_reporters_router)
    app.include_router(team_workspaces_router)
    app.include_router(integrations_router)
    app.include_router(healing_router)
    app.include_router(mcp_server_router)
    app.include_router(bru_format_router)
    app.include_router(yaml_collections_router)
    app.include_router(composite_project_router)
    app.include_router(conversational_ai_router)
    app.include_router(vscode_api_router)
    app.include_router(agent_explorer_router)
    app.include_router(replay_router)
    app.include_router(contract_guard_router)
    app.include_router(variable_inspector_router)
    app.include_router(semantic_diff_router)
    app.include_router(owasp_scanner_router)
    app.include_router(har_export_router)
    app.include_router(postman_export_router)
    app.include_router(sse_client_router)
    app.include_router(api_changelog_router)
    app.include_router(regression_gen_router)
    app.include_router(dependency_resolver_router)
    app.include_router(response_compare_router)
    app.include_router(pipeline_router)
    app.include_router(history_router)
    app.include_router(openapi_import_router)
    app.include_router(certificates_router)
    app.include_router(reports_router)
    return app


app = create_app()


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_pid_file(port: int) -> None:
    """Write `pid:port` to the storage dir so callers can locate the live
    sidecar. Best-effort: if we can't write it, log and continue."""
    pid_path = storage.home_dir() / "sidecar.pid"
    try:
        storage.home_dir().mkdir(parents=True, exist_ok=True)
        pid_path.write_text(f"{os.getpid()}:{port}\n", encoding="utf-8")
    except OSError as e:
        print(f"warning: could not write {pid_path}: {e}", file=sys.stderr)
        return

    def _cleanup() -> None:
        try:
            current = pid_path.read_text(encoding="utf-8").strip()
            # Only remove if it's still our entry — don't clobber a successor.
            if current.startswith(f"{os.getpid()}:"):
                pid_path.unlink(missing_ok=True)
        except OSError:
            pass

    atexit.register(_cleanup)


def main() -> None:
    port_env = os.environ.get("THERIDION_PORT")
    port = int(port_env) if port_env else _pick_free_port()
    _write_pid_file(port)
    # Print on a single line so the Tauri parent can parse it deterministically.
    # Includes pid so a misbehaving instance can be killed without grep
    # gymnastics.
    print(
        f"THERIDION_SIDECAR_READY pid={os.getpid()} port={port} "
        f"home={storage.home_dir()}",
        flush=True,
    )
    uvicorn.run(
        "theridion_sidecar.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    sys.exit(main())
