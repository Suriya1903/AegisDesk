from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "aegisdesk_http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "aegisdesk_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)
TICKETS_CREATED_TOTAL = Counter(
    "aegisdesk_tickets_created_total",
    "Total number of tickets created",
    ["source"],
)
TICKETS_UPDATED_TOTAL = Counter(
    "aegisdesk_tickets_updated_total",
    "Total number of tickets updated",
)
AI_ANALYSIS_TOTAL = Counter(
    "aegisdesk_ai_analysis_total",
    "Total number of AI analysis requests",
)
POLICY_DECISIONS_TOTAL = Counter(
    "aegisdesk_policy_decisions_total",
    "Total number of policy decisions",
    ["decision"],
)
AUTOMATION_EXECUTIONS_TOTAL = Counter(
    "aegisdesk_automation_executions_total",
    "Total number of self-heal automation executions",
    ["action", "result"],
)
