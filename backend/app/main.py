import os







from datetime import datetime, timedelta, timezone







from pathlib import Path







from typing import Any, Optional







import base64



import hashlib



import hmac



import secrets















from dotenv import load_dotenv







from fastapi import Depends, FastAPI, Header, HTTPException, Query







from fastapi.middleware.cors import CORSMiddleware



from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from starlette.middleware.base import BaseHTTPMiddleware

from starlette.responses import Response

from time import perf_counter







from pydantic import BaseModel, Field







import jwt



from jwt import InvalidTokenError







from pymongo import ASCENDING, DESCENDING, MongoClient







from pymongo.errors import PyMongoError















from app.ai_service import (







    ai_status,







    analyze_request,







)















from app.rag_service import (







    ensure_rag_ready,
    refresh_rag_index,







    knowledge_articles,







    rag_status,







    search_knowledge,







)







from app.policy_engine import (







    evaluate_policy,







    policy_status,







)



from app.servicenow_mock import (
    create_incident,
    create_service_request,
    get_incident,
    get_service_request,
    update_incident,
    update_service_request,
)

from app.self_heal_service import (
    ALLOWED_SELF_HEAL_ACTIONS,
    available_actions,
    execute_self_heal_action,
)

from app.metrics import (

    AI_ANALYSIS_TOTAL,

    AUTOMATION_EXECUTIONS_TOTAL,

    HTTP_REQUESTS_TOTAL,

    HTTP_REQUEST_DURATION_SECONDS,

    POLICY_DECISIONS_TOTAL,

    TICKETS_CREATED_TOTAL,

    TICKETS_UPDATED_TOTAL,

)



























PROJECT_ROOT = Path(__file__).resolve().parents[2]















ENV_FILE = (







    PROJECT_ROOT







    / "backend"







    / ".env"







)















load_dotenv(ENV_FILE)























MONGODB_URI = os.getenv(







    "MONGODB_URI"







)















MONGODB_DATABASE = os.getenv(







    "MONGODB_DATABASE",







    "aegisdesk",







)























if not MONGODB_URI:















    raise RuntimeError(







        "MONGODB_URI is missing. "







        "Add it to backend/.env before "







        "starting AegisDesk."







    )























mongo_client = MongoClient(







    MONGODB_URI,







    serverSelectionTimeoutMS=5000,







    connectTimeoutMS=5000,







)























database = mongo_client[







    MONGODB_DATABASE







]















tickets_collection = database[







    "tickets"







]















knowledge_collection = database[







    "knowledge"







]


dynamic_knowledge_collection = database[
    "knowledge_dynamic"
]











audit_collection = database[







    "ticket_audit"







]











users_collection = database[







    "users"







]























try:















    tickets_collection.create_index(







        [("ticket_id", ASCENDING)],







        unique=True,







        name="ticket_id_unique",







    )















    tickets_collection.create_index(







        [("created_at", DESCENDING)],







        name="created_at_desc",







    )















    tickets_collection.create_index(







        [("status", ASCENDING)],







        name="status_index",







    )















    knowledge_collection.create_index(







        [("article_id", ASCENDING)],







        unique=True,







        name="article_id_unique",







    )

    dynamic_knowledge_collection.create_index(
        [("article_id", ASCENDING)],
        unique=True,
        name="dynamic_article_id_unique",
    )

    dynamic_knowledge_collection.create_index(
        [("source_ticket_id", ASCENDING)],
        name="dynamic_source_ticket_index",
    )











    audit_collection.create_index(







        [("ticket_id", ASCENDING), ("timestamp", DESCENDING)],







        name="ticket_audit_history",







    )







    users_collection.create_index(



        [("username", ASCENDING)],



        unique=True,



        name="username_unique",



    )















except PyMongoError:















    pass























app = FastAPI(







    title="AegisDesk AI",







    description=(







        "AI-powered ITSM Helpdesk and "







        "Intelligent Automation Platform"







    ),







    version="1.4.0",







)























app.add_middleware(







    CORSMiddleware,















    allow_origins=[



        origin.strip()



        for origin in os.getenv(



            "AEGISDESK_CORS_ORIGINS",



            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",



        ).split(",")



        if origin.strip()



    ],















    allow_credentials=True,















    allow_methods=["*"],















    allow_headers=["*"],







)























# =========================================================





class PrometheusMiddleware(BaseHTTPMiddleware):

    """Collect HTTP request count and latency for Prometheus."""



    async def dispatch(self, request, call_next):

        # Do not count Prometheus scrapes as application traffic.

        if request.url.path == "/metrics":

            return await call_next(request)



        start = perf_counter()

        status_code = "500"



        try:

            response = await call_next(request)

            status_code = str(response.status_code)

            return response

        finally:

            duration = perf_counter() - start

            route = request.scope.get("route")

            path = getattr(route, "path", None) or request.url.path



            HTTP_REQUESTS_TOTAL.labels(

                method=request.method,

                path=path,

                status=status_code,

            ).inc()



            HTTP_REQUEST_DURATION_SECONDS.labels(

                method=request.method,

                path=path,

            ).observe(duration)





app.add_middleware(PrometheusMiddleware)





@app.get("/metrics", include_in_schema=False)

def metrics():

    return Response(

        content=generate_latest(),

        media_type=CONTENT_TYPE_LATEST,

    )





# AUTHENTICATION + RBAC



# =========================================================







JWT_SECRET = os.getenv("AEGISDESK_JWT_SECRET", "aegisdesk-development-secret-change-me")



JWT_ALGORITHM = "HS256"



JWT_EXPIRE_HOURS = int(os.getenv("AEGISDESK_JWT_EXPIRE_HOURS", "8"))



VALID_ROLES = {"employee", "agent", "admin"}











class LoginRequest(BaseModel):



    username: str = Field(..., min_length=3, max_length=100)



    password: str = Field(..., min_length=6, max_length=200)











class RoleUpdate(BaseModel):



    role: str = Field(..., min_length=5, max_length=20)











def hash_password(password: str, salt: Optional[bytes] = None) -> str:



    salt = salt or secrets.token_bytes(16)



    iterations = 240_000



    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)



    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"











def verify_password(password: str, encoded: str) -> bool:



    try:



        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)



        if scheme != "pbkdf2_sha256":



            return False



        salt = base64.urlsafe_b64decode(salt_b64.encode())



        expected = base64.urlsafe_b64decode(digest_b64.encode())



        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))



        return hmac.compare_digest(actual, expected)



    except (ValueError, TypeError):



        return False











def public_user(user: dict) -> dict:



    return {



        "username": user.get("username"),



        "display_name": user.get("display_name", user.get("username")),



        "email": user.get("email", ""),



        "role": user.get("role", "employee"),



        "active": bool(user.get("active", True)),



    }











def seed_demo_users() -> None:



    now = datetime.now(timezone.utc)



    demo_users = [



        ("employee", "Employee User", "employee@aegisdesk.local", "employee", "Employee@123"),



        ("agent", "IT Support Agent", "agent@aegisdesk.local", "agent", "Agent@123"),



        ("admin", "AegisDesk Administrator", "admin@aegisdesk.local", "admin", "Admin@123"),



    ]



    for username, display_name, email, role, password in demo_users:



        if users_collection.find_one({"username": username}):



            continue



        users_collection.insert_one({



            "username": username,



            "display_name": display_name,



            "email": email,



            "role": role,



            "password_hash": hash_password(password),



            "active": True,



            "created_at": now,



            "updated_at": now,



        })











def create_access_token(user: dict) -> str:



    now = datetime.now(timezone.utc)



    payload = {



        "sub": user["username"],



        "role": user["role"],



        "display_name": user.get("display_name", user["username"]),



        "iat": now,



        "exp": now + timedelta(hours=JWT_EXPIRE_HOURS),



    }



    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)











def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:



    if not authorization or not authorization.lower().startswith("bearer "):



        raise HTTPException(status_code=401, detail="Authentication required.")



    token = authorization.split(" ", 1)[1].strip()



    try:



        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])



    except InvalidTokenError as exc:



        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.") from exc



    username = payload.get("sub")



    user = users_collection.find_one({"username": username}) if username else None



    if not user or not user.get("active", True):



        raise HTTPException(status_code=401, detail="User account is inactive or unavailable.")



    return user











def require_roles(*roles: str):



    def dependency(current_user: dict = Depends(get_current_user)) -> dict:



        if current_user.get("role") not in roles:



            raise HTTPException(status_code=403, detail=f"This action requires one of these roles: {', '.join(roles)}.")



        return current_user



    return dependency











def can_access_ticket(ticket: dict, current_user: dict) -> bool:



    if current_user.get("role") in {"agent", "admin"}:



        return True



    return ticket.get("user") in {current_user.get("username"), current_user.get("display_name"), "Employee"}











@app.post("/api/auth/login")



def login(payload: LoginRequest):



    username = payload.username.strip().lower()



    user = users_collection.find_one({"username": username})



    if not user or not user.get("active", True) or not verify_password(payload.password, user.get("password_hash", "")):



        raise HTTPException(status_code=401, detail="Invalid username or password.")



    return {



        "access_token": create_access_token(user),



        "token_type": "bearer",



        "expires_in": JWT_EXPIRE_HOURS * 3600,



        "user": public_user(user),



    }











@app.get("/api/auth/me")



def auth_me(current_user: dict = Depends(get_current_user)):



    return {"user": public_user(current_user)}











@app.get("/api/auth/users")



def list_users(current_user: dict = Depends(require_roles("admin"))):



    users = users_collection.find({}, {"password_hash": 0}).sort("username", ASCENDING)



    return {"count": users_collection.count_documents({}), "users": [serialize_document(u) for u in users]}











@app.patch("/api/auth/users/{username}/role")



def update_user_role(username: str, payload: RoleUpdate, current_user: dict = Depends(require_roles("admin"))):



    role = payload.role.strip().lower()



    if role not in VALID_ROLES:



        raise HTTPException(status_code=400, detail="Invalid role. Use employee, agent, or admin.")



    if username == current_user.get("username") and role != "admin":



        raise HTTPException(status_code=400, detail="An administrator cannot remove their own admin role.")



    result = users_collection.update_one({"username": username}, {"$set": {"role": role, "updated_at": datetime.now(timezone.utc)}})



    if result.matched_count == 0:



        raise HTTPException(status_code=404, detail=f"User {username} not found.")



    return {"message": "User role updated successfully", "user": public_user(users_collection.find_one({"username": username}))}











# =========================================================







# MODELS







# =========================================================























class TicketCreate(BaseModel):















    title: str = Field(







        ...,







        min_length=3,







        max_length=200,







    )















    description: str = Field(







        ...,







        min_length=5,







        max_length=5000,







    )















    category: str = Field(







        default="General",







        max_length=100,







    )















    subcategory: str = Field(







        default="General",







        max_length=100,







    )















    priority: str = Field(







        default="P3",







        max_length=10,







    )















    impact: str = Field(







        default="Individual",







        max_length=50,







    )















    urgency: str = Field(







        default="Medium",







        max_length=50,







    )















    user: str = Field(







        default="Employee",







        max_length=100,







    )















    assignment_group: str = Field(







        default="Service Desk",







        max_length=100,







    )















    source: str = Field(







        default="Employee Portal",







        max_length=100,







    )















    intent: str = Field(







        default="Incident",







        max_length=50,







    )















    ai_confidence: Optional[float] = Field(







        default=None,







        ge=0.0,







        le=1.0,







    )















    ai_grounded: Optional[bool] = None















    ai_recommendation: Optional[str] = Field(







        default=None,







        max_length=2000,







    )







    policy_decision: Optional[str] = Field(



        default=None,



        max_length=30,



    )







    policy_action: Optional[str] = Field(



        default=None,



        max_length=100,



    )







    policy_requires_human: Optional[bool] = None







    policy_version: Optional[str] = Field(



        default=None,



        max_length=20,



    )







    policy_reason: Optional[str] = Field(



        default=None,



        max_length=2000,



    )























class TicketUpdate(BaseModel):















    status: Optional[str] = Field(







        default=None,







        max_length=50,







    )















    priority: Optional[str] = Field(







        default=None,







        max_length=10,







    )















    assignment_group: Optional[str] = Field(







        default=None,







        max_length=100,







    )















    resolution: Optional[str] = Field(







        default=None,







        max_length=5000,







    )







    actor: Optional[str] = Field(



        default="Employee",



        max_length=100,



    )







    source: Optional[str] = Field(



        default="ITSM Dashboard",



        max_length=100,



    )























class AITicketCreate(BaseModel):







    query: str = Field(



        ...,



        min_length=3,



        max_length=2000,



    )







    title: Optional[str] = Field(



        default=None,



        min_length=3,



        max_length=200,



    )







    user: str = Field(



        default="Employee",



        max_length=100,



    )







    source: str = Field(



        default="AI Helpdesk",



        max_length=100,



    )







    top_k: int = Field(



        default=5,



        ge=1,



        le=10,



    )











class AIAnalyzeRequest(BaseModel):















    query: str = Field(







        ...,







        min_length=3,







        max_length=2000,







    )















    top_k: int = Field(







        default=5,







        ge=1,







        le=10,







    )























class PolicyEvaluateRequest(BaseModel):











    analysis: dict[str, Any] = Field(







        default_factory=dict,







    )











    retrieval: dict[str, Any] = Field(







        default_factory=dict,







    )























class ServiceNowIncidentCreate(BaseModel):
    ticket_id: str = Field(..., min_length=3, max_length=50)


class ServiceNowIncidentUpdate(BaseModel):
    state: Optional[str] = Field(default=None, max_length=50)
    assignment_group: Optional[str] = Field(default=None, max_length=100)
    resolution: Optional[str] = Field(default=None, max_length=5000)


class ServiceNowRequestCreate(BaseModel):
    software: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=3, max_length=5000)


class ServiceNowRequestUpdate(BaseModel):
    state: Optional[str] = Field(default=None, max_length=50)
    provisioning_status: Optional[str] = Field(default=None, max_length=50)

class SelfHealExecuteRequest(BaseModel):
    ticket_id: str = Field(..., min_length=3, max_length=50)
    action: Optional[str] = Field(default=None, min_length=3, max_length=100)
    dry_run: bool = False


class KnowledgeArticleCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    category: str = Field(default="General", min_length=2, max_length=100)
    content: str = Field(..., min_length=50, max_length=10000)
    source: str = Field(default="AegisDesk Knowledge Management", max_length=200)



VALID_PRIORITIES = {







    "P1",







    "P2",







    "P3",







    "P4",







}























VALID_STATUSES = {







    "Open",







    "In Progress",







    "AI Resolved",







    "Resolved",







    "Escalated",







    "Closed",







}























# =========================================================







# HELPERS







# =========================================================























def now_utc() -> datetime:















    return datetime.now(







        timezone.utc







    )























def next_ticket_id() -> str:















    latest = tickets_collection.find_one(







        {







            "ticket_id": {







                "$regex": r"^INC\d+$"







            }







        },















        sort=[







            ("ticket_id", DESCENDING)







        ],















        projection={







            "ticket_id": 1







        },







    )















    if not latest:















        return "INC001001"















    try:















        number = (







            int(







                latest[







                    "ticket_id"







                ][3:]







            )







            + 1







        )















    except (







        KeyError,







        ValueError,







    ):















        number = 1001















    return f"INC{number:06d}"























def serialize_document(







    document: dict,







) -> dict:















    result = dict(







        document







    )















    result.pop(







        "_id",







        None,







    )















    for field in (







        "created_at",







        "updated_at",







    ):















        value = result.get(







            field







        )















        if isinstance(







            value,







            datetime,







        ):















            result[field] = (







                value.isoformat()







            )















    return result























def get_ticket_or_404(







    ticket_id: str,







) -> dict:















    ticket = (







        tickets_collection.find_one(







            {







                "ticket_id":







                    ticket_id







            }







        )







    )















    if not ticket:















        raise HTTPException(







            status_code=404,







            detail=(







                f"Ticket "







                f"{ticket_id} "







                f"not found"







            ),







        )















    return ticket



























# =========================================================



# AUDIT TRAIL



# =========================================================







def serialize_audit_event(document: dict) -> dict:



    result = dict(document)



    result.pop("_id", None)



    timestamp = result.get("timestamp")



    if isinstance(timestamp, datetime):



        result["timestamp"] = timestamp.isoformat()



    return result











def record_audit_event(



    ticket_id: str,



    event_type: str,



    actor: str,



    source: str,



    action: str,



    changes: Optional[dict] = None,



    details: Optional[str] = None,



) -> dict:



    event = {



        "ticket_id": ticket_id,



        "event_type": event_type,



        "actor": actor or "System",



        "source": source or "System",



        "action": action,



        "changes": changes or {},



        "details": details,



        "timestamp": now_utc(),



    }



    audit_collection.insert_one(event)



    return serialize_audit_event(event)











def backfill_audit_history() -> None:



    """



    Add a single immutable baseline event for tickets created before



    audit logging existed. This never modifies or deletes ticket data.



    """



    try:



        for ticket in tickets_collection.find(



            {},



            {



                "ticket_id": 1,



                "title": 1,



                "created_at": 1,



                "source": 1,



                "user": 1,



            },



        ):



            ticket_id = ticket.get("ticket_id")



            if not ticket_id:



                continue







            if audit_collection.count_documents(



                {"ticket_id": ticket_id}



            ) == 0:



                record_audit_event(



                    ticket_id=ticket_id,



                    event_type="ticket_created",



                    actor=ticket.get("user") or "System",



                    source=ticket.get("source") or "Legacy Ticket",



                    action="Ticket created",



                    details=(



                        "Baseline audit event created for an existing "



                        "ticket when audit history was enabled."



                    ),



                )



    except PyMongoError:



        # Audit logging must not prevent the application from starting.



        pass











def ticket_audit_history(ticket_id: str, limit: int = 100) -> list[dict]:



    get_ticket_or_404(ticket_id)



    events = (



        audit_collection.find({"ticket_id": ticket_id})



        .sort("timestamp", DESCENDING)



        .limit(limit)



    )



    return [serialize_audit_event(event) for event in events]











# Initialize RBAC demo users and baseline audit records.



seed_demo_users()



backfill_audit_history()











# =========================================================







# HEALTH







# =========================================================























@app.get("/")







def root():















    return {







        "application":







            "AegisDesk AI",















        "description":







            "AI-powered ITSM Helpdesk",















        "version":







            "1.2.0",















        "status":







            "running",







    }























@app.get("/health")







def health_check():















    return {







        "status":







            "healthy",















        "service":







            "aegisdesk-backend",







    }























@app.get("/health/database")







def database_health_check():















    try:















        mongo_client.admin.command(







            "ping"







        )















        return {







            "status":







                "healthy",















            "database":







                "mongodb-atlas",















            "connection":







                "successful",







        }















    except PyMongoError as exc:















        return {







            "status":







                "unhealthy",















            "database":







                "mongodb-atlas",















            "connection":







                "failed",















            "error":







                str(exc),







        }























@app.get("/health/ai")







def ai_health_check():















    try:















        return {







            "rag":







                rag_status(),















            "llm":







                ai_status(),







        }















    except Exception as exc:















        return {







            "status":







                "unavailable",















            "error":







                str(exc),







        }























@app.get("/api/policy/status")







def policy_status_endpoint(current_user: dict = Depends(require_roles("agent", "admin"))):















    try:















        return policy_status()















    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=f"Policy status failed: {exc}",







        ) from exc























@app.post("/api/policy/evaluate")







def policy_evaluate(







    payload: PolicyEvaluateRequest,



    current_user: dict = Depends(require_roles("agent", "admin")),







):















    try:















        analysis = dict(payload.analysis)







        retrieval = dict(payload.retrieval)















        decision = evaluate_policy(







            analysis,







            retrieval,







        )















        POLICY_DECISIONS_TOTAL.labels(decision=str(decision.get("decision", "UNKNOWN"))).inc()



        return {







            "analysis": analysis,







            "retrieval": retrieval,







            "policy": decision,







        }















    except (TypeError, ValueError) as exc:















        raise HTTPException(







            status_code=400,







            detail=f"Policy evaluation failed: {exc}",







        ) from exc















    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=f"Policy evaluation failed: {exc}",







        ) from exc























@app.get("/database/info")







def database_info(current_user: dict = Depends(require_roles("admin"))):















    try:















        collections = (







            database







            .list_collection_names()







        )















        return {







            "database":







                database.name,















            "collections":







                collections,















            "collection_count":







                len(collections),







        }















    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=str(exc),







        ) from exc























# =========================================================







# TICKETS







# =========================================================























@app.post(







    "/api/tickets",







    status_code=201,







)







def create_ticket(







    payload: TicketCreate,







    current_user: dict = Depends(get_current_user),







):















    if (







        payload.priority







        not in VALID_PRIORITIES







    ):















        raise HTTPException(







            status_code=400,







            detail=(







                "Invalid priority. "







                "Use one of: "







                f"{sorted(VALID_PRIORITIES)}"







            ),







        )























    created = now_utc()























    ticket = {















        "ticket_id":







            next_ticket_id(),















        "title":







            payload.title.strip(),















        "description":







            payload.description.strip(),















        "category":







            payload.category.strip(),















        "subcategory":







            payload.subcategory.strip(),















        "priority":







            payload.priority,















        "impact":







            payload.impact.strip(),















        "urgency":







            payload.urgency.strip(),















        "status":







            "Open",















        "user":







            (



                current_user["username"]



                if current_user.get("role") == "employee"



                else payload.user.strip()



            ),















        "assignment_group":







            payload.assignment_group.strip(),















        "intent":







            payload.intent.strip(),















        "resolution":







            None,















        "ai_confidence":







            payload.ai_confidence,















        "ai_grounded":







            payload.ai_grounded,















        "ai_recommendation":







            (







                payload.ai_recommendation.strip()







                if payload.ai_recommendation







                else None







            ),







        "policy_decision":



            payload.policy_decision,







        "policy_action":



            payload.policy_action,







        "policy_requires_human":



            payload.policy_requires_human,







        "policy_version":



            payload.policy_version,







        "policy_reason":



            (



                payload.policy_reason.strip()



                if payload.policy_reason



                else None



            ),















        "source":







            payload.source.strip(),















        "servicenow_reference":







            None,















        "created_at":







            created,















        "updated_at":







            created,







    }























    try:















        tickets_collection.insert_one(







            ticket







        )

        TICKETS_CREATED_TOTAL.labels(source=ticket["source"]).inc()

















    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=(







                "Could not create ticket: "







                f"{exc}"







            ),







        ) from exc











    try:



        record_audit_event(



            ticket_id=ticket["ticket_id"],



            event_type="ticket_created",



            actor=current_user["username"],



            source=ticket["source"],



            action="Ticket created",



            details="Ticket created through the standard ITSM ticket API.",



        )



    except PyMongoError as exc:



        raise HTTPException(



            status_code=503,



            detail=f"Ticket created but audit logging failed: {exc}",



        ) from exc























    return {















        "message":







            "Ticket created successfully",















        "ticket":







            serialize_document(







                ticket







            ),







    }























@app.get("/api/tickets")







def list_tickets(







    status: Optional[str] = Query(







        default=None







    ),















    limit: int = Query(







        default=50,







        ge=1,







        le=200,







    ),







    current_user: dict = Depends(get_current_user),







):















    query = ({"status": status} if status else {})







    if current_user.get("role") == "employee":



        query["user"] = current_user["username"]























    try:















        tickets = (







            tickets_collection







            .find(query)







            .sort(







                "created_at",







                DESCENDING,







            )







            .limit(limit)







        )























        return {















            "count":







                tickets_collection







                .count_documents(







                    query







                ),















            "tickets": [







                serialize_document(







                    ticket







                )















                for ticket in tickets







            ],







        }























    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=str(exc),







        ) from exc























@app.get("/api/tickets/stats")







def ticket_stats(current_user: dict = Depends(get_current_user)):















    scope = {"user": current_user["username"]} if current_user.get("role") == "employee" else {}







    try:















        return {















            "total":







                tickets_collection







                .count_documents(scope),















            "open":







                tickets_collection







                .count_documents(







                    {







                        **scope,







                        "status": {







                            "$in": [







                                "Open",







                                "In Progress",







                            ]







                        }







                    }







                ),















            "ai_resolved":







                tickets_collection







                .count_documents(







                    {







                        "status":







                            "AI Resolved"







                    }







                ),















            "escalated":







                tickets_collection







                .count_documents(







                    {







                        "status":







                            "Escalated"







                    }







                ),







        }























    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=str(exc),







        ) from exc























@app.get(







    "/api/tickets/{ticket_id}"







)







def get_ticket(







    ticket_id: str,







    current_user: dict = Depends(get_current_user),







):















    try:







        ticket = get_ticket_or_404(ticket_id)



        if not can_access_ticket(ticket, current_user):



            raise HTTPException(status_code=403, detail="You do not have access to this ticket.")



        return {"ticket": serialize_document(ticket)}











    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=str(exc),







        ) from exc























@app.patch(



    "/api/tickets/{ticket_id}"



)



def update_ticket(



    ticket_id: str,



    payload: TicketUpdate,



    current_user: dict = Depends(require_roles("agent", "admin")),



):



    current = get_ticket_or_404(ticket_id)







    raw_updates = payload.model_dump(exclude_none=True)



    raw_updates.pop("actor", None)



    raw_updates.pop("source", None)



    actor = current_user["username"]



    source = "ITSM Dashboard"







    if not raw_updates:



        raise HTTPException(



            status_code=400,



            detail="At least one field must be supplied for update.",



        )







    if (



        "priority" in raw_updates



        and raw_updates["priority"] not in VALID_PRIORITIES



    ):



        raise HTTPException(



            status_code=400,



            detail="Invalid priority",



        )







    if (



        "status" in raw_updates



        and raw_updates["status"] not in VALID_STATUSES



    ):



        raise HTTPException(



            status_code=400,



            detail="Invalid status",



        )







    # Remove no-op updates so the audit trail records meaningful changes only.



    changes = {}



    for field, new_value in raw_updates.items():



        old_value = current.get(field)



        if old_value != new_value:



            changes[field] = {



                "from": old_value,



                "to": new_value,



            }







    if not changes:



        return {



            "message": "No changes detected",



            "ticket": serialize_document(current),



            "audit": [],



        }







    raw_updates["updated_at"] = now_utc()







    try:



        result = tickets_collection.update_one(



            {"ticket_id": ticket_id},



            {"$set": raw_updates},



        )







        if result.matched_count == 0:



            raise HTTPException(



                status_code=404,



                detail=f"Ticket {ticket_id} not found",



            )







        updated_ticket = get_ticket_or_404(ticket_id)







        event = record_audit_event(



            ticket_id=ticket_id,



            event_type="ticket_updated",



            actor=actor,



            source=source,



            action="Ticket updated",



            changes=changes,



            details=f"{len(changes)} field(s) changed.",



        )







        TICKETS_UPDATED_TOTAL.inc()



        return {



            "message": "Ticket updated successfully",



            "ticket": serialize_document(updated_ticket),



            "audit": event,



        }







    except PyMongoError as exc:



        raise HTTPException(



            status_code=503,



            detail=str(exc),



        ) from exc











@app.get("/api/tickets/{ticket_id}/activity")



def get_ticket_activity(



    ticket_id: str,



    limit: int = Query(default=100, ge=1, le=200),



    current_user: dict = Depends(get_current_user),



): 



    ticket = get_ticket_or_404(ticket_id)



    if not can_access_ticket(ticket, current_user):



        raise HTTPException(status_code=403, detail="You do not have access to this ticket activity.")



    try:



        events = ticket_audit_history(ticket_id, limit)



        return {



            "ticket_id": ticket_id,



            "count": len(events),



            "events": events,



        }



    except PyMongoError as exc:



        raise HTTPException(



            status_code=503,



            detail=str(exc),



        ) from exc











@app.get("/api/tickets/{ticket_id}/audit")



def get_ticket_audit(



    ticket_id: str,



    limit: int = Query(default=100, ge=1, le=200),



    current_user: dict = Depends(get_current_user),



): 



    ticket = get_ticket_or_404(ticket_id)



    if not can_access_ticket(ticket, current_user):



        raise HTTPException(status_code=403, detail="You do not have access to this ticket activity.")



    try:



        events = ticket_audit_history(ticket_id, limit)



        return {



            "ticket_id": ticket_id,



            "count": len(events),



            "events": events,



        }



    except PyMongoError as exc:



        raise HTTPException(



            status_code=503,



            detail=str(exc),



        ) from exc



















# =========================================================







# KNOWLEDGE







# =========================================================























@app.get("/api/knowledge")







def list_knowledge(current_user: dict = Depends(get_current_user)):















    try:















        articles = (







            knowledge_articles()







        )























        for article in articles:















            knowledge_collection.update_one(















                {







                    "article_id":







                        article[







                            "article_id"







                        ]







                },















                {







                    "$set":







                        article







                },















                upsert=True,







            )























        return {















            "count":







                len(articles),















            "articles":







                articles,







        }























    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=str(exc),







        ) from exc























    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=(







                "Knowledge load failed: "







                f"{exc}"







            ),







        ) from exc























@app.post(







    "/api/knowledge/sync"







)







def sync_knowledge_to_mongodb(current_user: dict = Depends(require_roles("admin"))):















    try:















        articles = (







            knowledge_articles()







        )























        for article in articles:















            knowledge_collection.update_one(















                {







                    "article_id":







                        article[







                            "article_id"







                        ]







                },















                {







                    "$set":







                        article







                },















                upsert=True,







            )























        return {















            "message":







                "Knowledge metadata synced",















            "articles_synced":







                len(articles),







        }























    except PyMongoError as exc:















        raise HTTPException(







            status_code=503,







            detail=str(exc),







        ) from exc























    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=(







                "Knowledge sync failed: "







                f"{exc}"







            ),







        ) from exc























# =========================================================







# KNOWLEDGE MANAGEMENT AUTOMATION
# =========================================================


@app.post("/api/knowledge/articles", status_code=201)
def create_knowledge_article(
    payload: KnowledgeArticleCreate,
    current_user: dict = Depends(require_roles("agent", "admin")),
):
    """Create and publish a knowledge article, then refresh the RAG index."""
    article_id = f"KB-AUTO-{secrets.token_hex(4).upper()}"
    created_at = now_utc()
    article = {
        "article_id": article_id,
        "title": payload.title.strip(),
        "category": payload.category.strip(),
        "source": payload.source.strip(),
        "content": payload.content.strip(),
        "status": "published",
        "created_by": current_user["username"],
        "created_at": created_at,
        "updated_at": created_at,
    }
    try:
        dynamic_knowledge_collection.insert_one(article)
        rag = refresh_rag_index()
        audit = record_audit_event(
            ticket_id=f"KB:{article_id}",
            event_type="knowledge_article_created",
            actor=current_user["username"],
            source="Knowledge Management",
            action="Knowledge article created and indexed",
            details=f"Published knowledge article {article_id} and refreshed the FAISS RAG index.",
        )
        return {"message": "Knowledge article created and indexed", "article": serialize_document(article), "rag": rag, "audit": audit}
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge article creation failed: {exc}") from exc


@app.post("/api/knowledge/automation/from-ticket/{ticket_id}", status_code=201)
def generate_knowledge_from_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_roles("agent", "admin")),
):
    """Turn a resolved ticket into a reusable published KB article."""
    ticket = get_ticket_or_404(ticket_id)
    if ticket.get("status") not in {"AI Resolved", "Resolved", "Closed"}:
        raise HTTPException(status_code=409, detail="Knowledge automation requires a resolved or closed ticket.")
    resolution = str(ticket.get("resolution") or "").strip()
    if not resolution:
        raise HTTPException(status_code=409, detail="The resolved ticket does not contain a resolution to convert into knowledge.")
    existing = dynamic_knowledge_collection.find_one({"source_ticket_id": ticket_id}, {"_id": 0})
    if existing:
        return {"message": "Knowledge article already exists for this ticket", "article": serialize_document(existing), "rag": rag_status()}
    title = f"Resolution Guide: {ticket.get('title', ticket_id)}"
    content = (
        f"Issue: {ticket.get('title', ticket_id)}\n\n"
        f"Category: {ticket.get('category', 'General')} / {ticket.get('subcategory', 'General')}\n\n"
        f"Reported problem: {ticket.get('description', '')}\n\n"
        f"Approved resolution: {resolution}\n\n"
        f"Recommended next step: {ticket.get('ai_recommendation') or resolution}"
    ).strip()
    article_id = f"KB-AUTO-{secrets.token_hex(4).upper()}"
    created_at = now_utc()
    article = {
        "article_id": article_id,
        "title": title,
        "category": ticket.get("category", "General"),
        "source": "AegisDesk Knowledge Management Automation",
        "content": content,
        "status": "published",
        "source_ticket_id": ticket_id,
        "created_by": current_user["username"],
        "created_at": created_at,
        "updated_at": created_at,
    }
    try:
        dynamic_knowledge_collection.insert_one(article)
        rag = refresh_rag_index()
        audit = record_audit_event(
            ticket_id=ticket_id,
            event_type="knowledge_article_created",
            actor=current_user["username"],
            source="Knowledge Management",
            action="Resolved ticket converted into knowledge article",
            details=f"Created and indexed {article_id} from resolved ticket {ticket_id}.",
        )
        return {"message": "Resolved ticket converted into knowledge article", "article": serialize_document(article), "rag": rag, "audit": audit}
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge automation failed: {exc}") from exc


# RAG







# =========================================================























@app.get("/api/rag/status")







def rag_status_endpoint(current_user: dict = Depends(get_current_user)):















    try:















        return rag_status()















    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=str(exc),







        ) from exc























@app.post("/api/rag/build")







def build_rag_index(current_user: dict = Depends(require_roles("admin"))):















    try:















        return refresh_rag_index()















    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=(







                "RAG index build failed: "







                f"{exc}"







            ),







        ) from exc























@app.get("/api/rag/search")







def rag_search(















    q: str = Query(







        ...,







        min_length=2,







        max_length=500,







    ),















    top_k: int = Query(







        default=5,







        ge=1,







        le=10,







    ),







    current_user: dict = Depends(get_current_user),







):















    try:















        results = search_knowledge(







            q,







            top_k=top_k,







        )























        return {















            "query":







                q,















            "count":







                len(results),















            "results":







                results,















            "grounded":







                bool(results),







        }























    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=(







                "RAG search failed: "







                f"{exc}"







            ),







        ) from exc























# =========================================================







# HUGGING FACE LLM + RAG ANALYSIS







# =========================================================























@app.post("/api/ai/analyze")







def ai_analyze(







    payload: AIAnalyzeRequest,



    current_user: dict = Depends(get_current_user),







):















    try:















        analysis = analyze_request(







            payload.query,







            top_k=payload.top_k,







        )















        # Keep this endpoint compatible if the AI service later







        # returns a Pydantic model instead of a dictionary.







        if hasattr(analysis, "model_dump"):







            analysis = analysis.model_dump()







        elif not isinstance(analysis, dict):







            analysis = dict(analysis)















        AI_ANALYSIS_TOTAL.inc()



        # The original request is required by deterministic







        # automation inference.







        analysis["query"] = payload.query















        retrieval = {







            "grounded": bool(







                analysis.get(







                    "grounded",







                    False,







                )







            ),







            "top_similarity": float(







                analysis.get(







                    "top_similarity",







                    0.0,







                )







                or 0.0







            ),







        }















        # Fallback for AI-service versions that expose the best







        # similarity only inside sources/results.







        if retrieval["top_similarity"] <= 0:















            sources = (







                analysis.get("sources")







                or analysis.get("results")







                or []







            )















            if sources:















                first_source = sources[0]















                if isinstance(







                    first_source,







                    dict,







                ):















                    retrieval["top_similarity"] = float(







                        first_source.get(







                            "similarity",







                            first_source.get(







                                "score",







                                0.0,







                            ),







                        )







                        or 0.0







                    )















        policy = evaluate_policy(







            analysis,







            retrieval,







        )















        POLICY_DECISIONS_TOTAL.labels(decision=str(policy.get("decision", "UNKNOWN"))).inc()



        analysis["policy"] = policy







        analysis["policy_decision"] = (







            policy["decision"]







        )







        analysis["policy_action"] = (







            policy["action"]







        )







        analysis["policy_requires_human"] = (







            policy["requires_human"]







        )















        return analysis























    except ValueError as exc:















        raise HTTPException(







            status_code=400,







            detail=str(exc),







        ) from exc























    except Exception as exc:















        raise HTTPException(







            status_code=500,







            detail=(







                "AI analysis failed: "







                f"{exc}"







            ),







        ) from exc











# =========================================================



# AI -> POLICY -> TICKET WORKFLOW



# =========================================================







def _normalise_ai_analysis(raw: dict, query: str) -> tuple[dict, dict]:



    data = dict(raw or {})







    nested = data.get("analysis")



    if isinstance(nested, dict):



        analysis = dict(nested)



    else:



        analysis = {}







    # Current ai_service exposes structured ITSM fields at the top level.



    # Supporting both forms keeps this endpoint compatible with the service.



    for key in (



        "answer",



        "intent",



        "category",



        "subcategory",



        "priority",



        "impact",



        "urgency",



        "assignment_group",



        "confidence",



        "recommended_action",



        "top_similarity",



        "grounded",



        "model",



    ):



        if key in data and key not in analysis:



            analysis[key] = data[key]







    analysis["query"] = query







    retrieval = data.get("retrieval")



    if not isinstance(retrieval, dict):



        retrieval = {}







    retrieval = dict(retrieval)



    retrieval["grounded"] = bool(



        data.get(



            "grounded",



            retrieval.get("grounded", False),



        )



    )







    top_similarity = float(



        data.get(



            "top_similarity",



            retrieval.get("top_similarity", 0.0),



        )



        or 0.0



    )



    retrieval["top_similarity"] = top_similarity







    return analysis, retrieval











def build_ticket_from_ai_analysis(



    query: str,



    analysis: dict,



    policy: dict,



    user: str,



    source: str,



    title: Optional[str] = None,



) -> dict:



    created = now_utc()







    ticket = {



        "ticket_id": next_ticket_id(),



        "title": (title or query).strip(),



        "description": str(



            analysis.get(



                "answer",



                "Please follow the approved IT support procedure.",



            )



        ).strip(),



        "category": str(



            analysis.get("category", "General")



        ).strip(),



        "subcategory": str(



            analysis.get("subcategory", "General")



        ).strip(),



        "priority": str(



            analysis.get("priority", "P3")



        ).strip(),



        "impact": str(



            analysis.get("impact", "Individual")



        ).strip(),



        "urgency": str(



            analysis.get("urgency", "Medium")



        ).strip(),



        "status": "Open",



        "user": user.strip(),



        "assignment_group": str(



            analysis.get("assignment_group", "Service Desk")



        ).strip(),



        "intent": str(



            analysis.get("intent", "Incident")



        ).strip(),



        "resolution": None,



        "ai_confidence": float(



            analysis.get("confidence", 0.0) or 0.0



        ),



        "ai_grounded": bool(



            analysis.get("grounded", False)



        ),



        "ai_recommendation": str(



            analysis.get(



                "recommended_action",



                "Human review is required.",



            )



        ).strip(),



        "source": source.strip(),



        "servicenow_reference": None,



        "policy_decision": policy.get("decision"),



        "policy_action": policy.get("action"),



        "policy_requires_human": policy.get("requires_human"),



        "policy_version": policy.get("policy_version"),



        "policy_reason": policy.get("reason"),



        "created_at": created,



        "updated_at": created,



    }







    if ticket["priority"] not in VALID_PRIORITIES:



        ticket["priority"] = "P3"







    return ticket











@app.get("/api/automation/actions")
def get_automation_actions(
    current_user: dict = Depends(get_current_user),
):
    """Return the bounded self-heal actions supported by AegisDesk."""
    return {
        "mode": "safe_demo_automation",
        "arbitrary_command_execution": False,
        "actions": available_actions(),
    }


@app.post("/api/automation/execute")
def execute_automation(
    payload: SelfHealExecuteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run an approved, allow-listed self-heal action for a ticket.

    Policy Engine remains the authorization gate.  The endpoint will never
    execute an action that is blocked, requires human review, or is not the
    exact policy action assigned to the ticket.
    """
    ticket = get_ticket_or_404(payload.ticket_id)

    if not can_access_ticket(ticket, current_user):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to automate this ticket.",
        )

    decision = str(ticket.get("policy_decision") or "").upper()
    policy_action = str(ticket.get("policy_action") or "").strip().lower()
    requires_human = bool(ticket.get("policy_requires_human", False))

    if decision != "APPROVED" or requires_human:
        raise HTTPException(
            status_code=409,
            detail=(
                "Automation is not permitted for this ticket. "
                f"Policy decision={decision or 'UNKNOWN'}, "
                f"requires_human={requires_human}."
            ),
        )

    requested_action = str(payload.action or policy_action).strip().lower()

    if not requested_action:
        raise HTTPException(
            status_code=409,
            detail="No approved automation action is attached to this ticket.",
        )

    if requested_action not in ALLOWED_SELF_HEAL_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported automation action '{requested_action}'. "
                f"Allowed actions: {', '.join(sorted(ALLOWED_SELF_HEAL_ACTIONS))}."
            ),
        )

    if policy_action != requested_action:
        raise HTTPException(
            status_code=409,
            detail=(
                "Requested automation action does not match the Policy Engine "
                f"decision. Ticket action='{policy_action}', requested='{requested_action}'."
            ),
        )

    if ticket.get("status") in {"AI Resolved", "Resolved", "Closed"} and not payload.dry_run:
        return {
            "message": "Ticket is already resolved; no duplicate automation executed.",
            "automation": {
                "success": True,
                "already_resolved": True,
                "action": requested_action,
                "ticket_id": ticket["ticket_id"],
            },
            "ticket": serialize_document(ticket),
        }

    try:
        automation = execute_self_heal_action(
            requested_action,
            ticket=ticket,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    AUTOMATION_EXECUTIONS_TOTAL.labels(
        action=requested_action,
        result="dry_run" if payload.dry_run else "success",
    ).inc()

    if payload.dry_run:
        audit = record_audit_event(
            ticket_id=ticket["ticket_id"],
            event_type="automation_dry_run",
            actor=current_user["username"],
            source="Self-Heal Agent",
            action="Self-heal validation executed",
            details=(
                f"Validated approved automation action '{requested_action}' "
                "without executing a side effect."
            ),
        )
        return {
            "message": "Automation validation completed",
            "automation": automation,
            "ticket": serialize_document(ticket),
            "audit": audit,
        }

    resolution = (
        f"AI Self-Heal Agent completed: {automation['result']} "
        f"Action: {automation['action_label']}."
    )
    updated_at = now_utc()

    result = tickets_collection.update_one(
        {"ticket_id": ticket["ticket_id"]},
        {
            "$set": {
                "status": "AI Resolved",
                "resolution": resolution,
                "updated_at": updated_at,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Ticket {payload.ticket_id} not found")

    updated_ticket = get_ticket_or_404(payload.ticket_id)

    # Synchronize the linked ServiceNow-compatible incident when one exists.
    service_now = None
    service_now_audit = None
    servicenow_reference = updated_ticket.get("servicenow_reference")
    if servicenow_reference:
        service_now = update_incident(
            database,
            servicenow_reference,
            state="Resolved",
            assignment_group=updated_ticket.get("assignment_group"),
            resolution=resolution,
        )
        if service_now:
            service_now_audit = record_audit_event(
                ticket_id=updated_ticket["ticket_id"],
                event_type="servicenow_incident_updated",
                actor=current_user["username"],
                source="Mock ServiceNow",
                action="ServiceNow incident resolved",
                changes={
                    "state": {"from": "In Progress", "to": "Resolved"},
                    "resolution": {"from": None, "to": resolution},
                },
                details=(
                    f"ServiceNow incident {servicenow_reference} synchronized "
                    "after successful self-heal automation."
                ),
            )

    audit = record_audit_event(
        ticket_id=updated_ticket["ticket_id"],
        event_type="automation_executed",
        actor=current_user["username"],
        source="Self-Heal Agent",
        action="AI self-heal automation executed",
        changes={
            "status": {"from": ticket.get("status"), "to": "AI Resolved"},
            "resolution": {"from": ticket.get("resolution"), "to": resolution},
        },
        details=(
            f"Approved low-risk automation '{requested_action}' executed by "
            "the bounded Self-Heal Agent. No arbitrary command execution was used."
        ),
    )

    return {
        "message": "Self-heal automation completed successfully",
        "automation": automation,
        "ticket": serialize_document(updated_ticket),
        "service_now": service_now,
        "servicenow_audit": service_now_audit,
        "audit": audit,
    }


@app.post("/api/servicenow/incidents", status_code=201)
def create_servicenow_incident(
    payload: ServiceNowIncidentCreate,
    current_user: dict = Depends(get_current_user),
):
    ticket = get_ticket_or_404(payload.ticket_id)

    # Reuse an existing linked incident instead of creating duplicates.
    existing_reference = ticket.get("servicenow_reference")
    if existing_reference:
        existing = get_incident(database, existing_reference)
        if existing:
            return {
                "message": "ServiceNow incident already linked",
                "incident": existing,
            }

    incident = create_incident(database, ticket)
    tickets_collection.update_one(
        {"ticket_id": payload.ticket_id},
        {
            "$set": {
                "servicenow_reference": incident["number"],
                "updated_at": now_utc(),
            }
        },
    )

    record_audit_event(
        ticket_id=payload.ticket_id,
        event_type="servicenow_incident_created",
        actor=current_user["username"],
        source="Mock ServiceNow",
        action="ServiceNow incident created",
        details=(
            f"Mock ServiceNow incident {incident['number']} "
            f"created from AegisDesk ticket."
        ),
    )

    return {
        "message": "ServiceNow incident created",
        "incident": incident,
    }


@app.get("/api/servicenow/incidents/{number}")
def read_servicenow_incident(
    number: str,
    current_user: dict = Depends(get_current_user),
):
    incident = get_incident(database, number)
    if not incident:
        raise HTTPException(
            status_code=404,
            detail=f"ServiceNow incident {number} not found",
        )
    return incident


@app.patch("/api/servicenow/incidents/{number}")
def patch_servicenow_incident(
    number: str,
    payload: ServiceNowIncidentUpdate,
    current_user: dict = Depends(get_current_user),
):
    incident = update_incident(
        database,
        number,
        state=payload.state,
        assignment_group=payload.assignment_group,
        resolution=payload.resolution,
    )
    if not incident:
        raise HTTPException(
            status_code=404,
            detail=f"ServiceNow incident {number} not found",
        )

    return {
        "message": "ServiceNow incident updated",
        "incident": incident,
    }


@app.post("/api/servicenow/requests", status_code=201)
def create_servicenow_request(
    payload: ServiceNowRequestCreate,
    current_user: dict = Depends(get_current_user),
):
    request = create_service_request(
        database,
        software=payload.software.strip(),
        user=current_user["username"],
        description=payload.description.strip(),
    )

    return {
        "message": "ServiceNow service request created",
        "request": request,
    }


@app.get("/api/servicenow/requests/{number}")
def read_servicenow_request(
    number: str,
    current_user: dict = Depends(get_current_user),
):
    request = get_service_request(database, number)
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"ServiceNow request {number} not found",
        )
    return request


@app.patch("/api/servicenow/requests/{number}")
def patch_servicenow_request(
    number: str,
    payload: ServiceNowRequestUpdate,
    current_user: dict = Depends(get_current_user),
):
    request = update_service_request(
        database,
        number,
        state=payload.state,
        provisioning_status=payload.provisioning_status,
    )
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"ServiceNow request {number} not found",
        )

    return {
        "message": "ServiceNow service request updated",
        "request": request,
    }


@app.post("/api/tickets/ai", status_code=201)



def create_ai_ticket(



    payload: AITicketCreate,



    current_user: dict = Depends(get_current_user),



):



    try:



        raw = analyze_request(



            payload.query,



            top_k=payload.top_k,



        )







        analysis, retrieval = _normalise_ai_analysis(



            raw,



            payload.query,



        )







        policy = evaluate_policy(



            analysis,



            retrieval,



        )







        POLICY_DECISIONS_TOTAL.labels(decision=str(policy.get("decision", "UNKNOWN"))).inc()



        ticket = build_ticket_from_ai_analysis(



            query=payload.query,



            analysis=analysis,



            policy=policy,



            user=current_user["username"],



            source=payload.source,



            title=payload.title,



        )







        tickets_collection.insert_one(ticket)



        TICKETS_CREATED_TOTAL.labels(source=ticket["source"]).inc()







        audit_event = record_audit_event(



            ticket_id=ticket["ticket_id"],



            event_type="ticket_created",



            actor=current_user["username"],



            source=payload.source,



            action="AI ticket created",



            details=(



                f"AI workflow completed: RAG → Qwen → "



                f"Policy Engine → MongoDB. "



                f"Policy decision: {policy.get('decision')}."



            ),



        )

        # Create a ServiceNow-compatible incident after the AegisDesk ticket
        # has been persisted successfully.
        servicenow_incident = create_incident(database, ticket)
        ticket["servicenow_reference"] = servicenow_incident["number"]
        ticket["updated_at"] = now_utc()

        tickets_collection.update_one(
            {"ticket_id": ticket["ticket_id"]},
            {
                "$set": {
                    "servicenow_reference": servicenow_incident["number"],
                    "updated_at": ticket["updated_at"],
                }
            },
        )

        servicenow_audit = record_audit_event(
            ticket_id=ticket["ticket_id"],
            event_type="servicenow_incident_created",
            actor=current_user["username"],
            source="Mock ServiceNow",
            action="ServiceNow incident created",
            details=(
                f"Mock ServiceNow incident {servicenow_incident['number']} "
                f"created from AI-generated ticket {ticket['ticket_id']}."
            ),
        )








        return {



            "message": "AI ticket created successfully",



            "workflow": {



                "rag": "completed",



                "llm": "completed",



                "policy_engine": "completed",



                "ticket_creation": "completed",
                "servicenow": "completed",



            },



            "analysis": analysis,



            "policy": policy,



            "ticket": serialize_document(ticket),



            "service_now": servicenow_incident,

            "servicenow_audit": servicenow_audit,

            "audit": audit_event,



        }







    except ValueError as exc:



        raise HTTPException(



            status_code=400,



            detail=str(exc),



        ) from exc



    except PyMongoError as exc:



        raise HTTPException(



            status_code=503,



            detail=f"AI ticket persistence failed: {exc}",



        ) from exc



    except Exception as exc:



        raise HTTPException(



            status_code=500,



            detail=f"AI ticket workflow failed: {exc}",



        ) from exc
