# AegisDesk

## AI-Powered Enterprise ITSM, Helpdesk & Automation Platform

AegisDesk is an AI-powered enterprise IT service management (ITSM) and helpdesk platform designed to demonstrate how modern AI can be integrated with ticket management, knowledge retrieval, policy-based automation, self-healing workflows, software provisioning, auditability, and operational monitoring.

The platform combines:

**React.js + FastAPI + MongoDB Atlas + Hugging Face/Qwen + RAG + FAISS + Sentence Transformers + Policy Engine + AI Self-Heal + Knowledge Management Automation + ServiceNow-Compatible Integration + JWT/RBAC + Docker + Prometheus + Grafana + Pytest**

Unlike a basic chatbot, AegisDesk is designed as an end-to-end ITSM workflow. A user request can be converted into a structured ticket, analyzed using an open-source LLM with retrieved knowledge, evaluated by a deterministic policy engine, routed for automation or human review, synchronized with a ServiceNow-compatible adapter, and recorded in an audit trail.

The project is intentionally designed to run locally using Docker Desktop and MongoDB Atlas without requiring paid cloud infrastructure.

---

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Problem Statement](#2-problem-statement)
- [3. Key Capabilities](#3-key-capabilities)
- [4. High-Level Architecture](#4-high-level-architecture)
- [5. Technology Stack](#5-technology-stack)
- [6. System Components](#6-system-components)
- [7. End-to-End Ticket Flow](#7-end-to-end-ticket-flow)
- [8. Intelligent Ticket Intake](#8-intelligent-ticket-intake)
- [9. RAG Knowledge Retrieval](#9-rag-knowledge-retrieval)
- [10. LLM Analysis](#10-llm-analysis)
- [11. Policy Engine and AI Governance](#11-policy-engine-and-ai-governance)
- [12. Auto Resolution and Self-Heal Agent](#12-auto-resolution-and-self-heal-agent)
- [13. Knowledge Management Automation](#13-knowledge-management-automation)
- [14. Self-Service Portal and AI Chatbot](#14-self-service-portal-and-ai-chatbot)
- [15. Software Provisioning Automation](#15-software-provisioning-automation)
- [16. ServiceNow-Compatible Integration](#16-servicenow-compatible-integration)
- [17. Authentication and RBAC](#17-authentication-and-rbac)
- [18. Audit Trail](#18-audit-trail)
- [19. MongoDB Data Model](#19-mongodb-data-model)
- [20. Observability](#20-observability)
- [21. Docker Deployment](#21-docker-deployment)
- [22. Testing](#22-testing)
- [23. Project Structure](#23-project-structure)
- [24. Local Development Setup](#24-local-development-setup)
- [25. Docker Setup](#25-docker-setup)
- [26. Demo Scenarios](#26-demo-scenarios)
- [27. API Overview](#27-api-overview)
- [28. Security Considerations](#28-security-considerations)
- [29. Verified Results](#29-verified-results)
- [30. Engineering Highlights](#30-engineering-highlights)
- [31. Limitations and Future Enhancements](#31-limitations-and-future-enhancements)
- [32. Author](#32-author)
- [33. Final Project Summary](#33-final-project-summary)

---

# 1. Project Overview

AegisDesk separates the employee-facing helpdesk experience from the AI reasoning, policy enforcement, persistence, integration, and monitoring layers.

The main business flow is:

```text
                         +----------------------+
                         |    React Frontend    |
                         | Employee / ITSM UI   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     FastAPI Backend   |
                         +----------+-----------+
                                    |
                 +------------------+------------------+
                 |                  |                  |
                 v                  v                  v
          Authentication      Ticket APIs       AI Workflow
                 |                  |                  |
                 |                  |          +-------+-------+
                 |                  |          |               |
                 |                  |          v               v
                 |                  |        RAG            Qwen
                 |                  |          |               |
                 |                  |          +-------+-------+
                 |                  |                  |
                 |                  |                  v
                 |                  |            Policy Engine
                 |                  |                  |
                 |                  |        +---------+---------+
                 |                  |        |                   |
                 |                  |        v                   v
                 |                  |    Automation         Human Review
                 |                  |        |
                 |                  |        v
                 |                  |    Self-Heal
                 |                  |
                 +------------------+------------------+
                                    |
                                    v
                             +-------------+
                             |  MongoDB    |
                             |   Atlas     |
                             +-------------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
             ServiceNow-Compatible             Audit Trail
                 Adapter
```

The operational monitoring path is:

```text
FastAPI
   |
   v
/metrics
   |
   v
Prometheus
   |
   v
Grafana
```

---

# 2. Problem Statement

Traditional helpdesk systems depend heavily on manual ticket classification, repetitive troubleshooting, knowledge lookup, and IT-agent intervention.

AegisDesk addresses these problems by introducing an AI-assisted workflow:

```text
Employee Problem
      |
      v
AI understands request
      |
      v
Relevant IT knowledge retrieved
      |
      v
LLM generates structured analysis
      |
      v
Policy Engine checks safety
      |
      +-------------------+
      |                   |
      v                   v
Approved             Human Review /
Automation           Blocked
      |
      v
Self-Heal / Provision
      |
      v
Validate
      |
      v
Update ITSM record
      |
      v
Audit everything
```

The important design principle is:

> **The LLM is not given unrestricted authority to execute actions.**

The LLM provides reasoning and recommendations, while the Policy Engine determines whether an action is allowed.

---

# 3. Key Capabilities

AegisDesk implements the five major ITSM capabilities required by the assessment.

| Assessment Capability | AegisDesk Implementation |
|---|---|
| Intelligent Ticket Intake | AI classification, priority, impact, urgency, assignment group and resolution recommendation |
| Auto Resolution / Self-Heal | Policy-controlled automation with validation and ITSM synchronization |
| Knowledge Management Automation | Resolved incidents can be transformed into searchable knowledge articles |
| Self-Service Portal & AI Chatbot | Employee portal, AI helpdesk, RAG-powered responses and ticket creation |
| Software Provisioning Automation | Software request workflow with ITSM-compatible service requests and bounded provisioning workflow |

Additional capabilities:

- JWT authentication
- Employee/Agent roles
- MongoDB Atlas persistence
- RAG with FAISS
- Hugging Face Qwen model
- Deterministic policy engine
- Audit trail
- ServiceNow-compatible adapter
- Prometheus metrics
- Grafana monitoring
- Docker Compose
- Automated tests

---

# 4. High-Level Architecture

```text
                         +-----------------------+
                         |     React Frontend    |
                         |                       |
                         | Employee Portal       |
                         | AI Helpdesk           |
                         | ITSM Dashboard        |
                         | Knowledge Base        |
                         | Provisioning           |
                         +-----------+-----------+
                                     |
                                  HTTP/JSON
                                     |
                                     v
                         +-----------------------+
                         |     FastAPI Backend   |
                         |       :8000           |
                         +-----------+-----------+
                                     |
        +----------------------------+----------------------------+
        |                            |                            |
        v                            v                            v
+---------------+            +---------------+            +---------------+
| Auth / RBAC   |            | Ticket APIs   |            | AI Workflow   |
+---------------+            +-------+-------+            +-------+-------+
                                     |                            |
                                     |                 +----------+----------+
                                     |                 |                     |
                                     |                 v                     v
                                     |              RAG / FAISS           Qwen LLM
                                     |                 |                     |
                                     |                 +----------+----------+
                                     |                            |
                                     |                            v
                                     |                     Policy Engine
                                     |                            |
                                     |                +-----------+-----------+
                                     |                |                       |
                                     |                v                       v
                                     |          Self-Heal Agent          Human Review
                                     |                |
                                     |                v
                                     |        ServiceNow-Compatible
                                     |             Integration
                                     |
                                     v
                              +-------------+
                              | MongoDB     |
                              | Atlas       |
                              +-------------+
                                     |
                       +-------------+-------------+
                       |                           |
                       v                           v
                 Audit Collection          ServiceNow Mock
```

---

# 5. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React.js |
| Frontend Build Tool | Vite |
| Backend | Python + FastAPI |
| Database | MongoDB Atlas |
| AI Model | Hugging Face Qwen/Qwen2.5-0.5B-Instruct |
| Embeddings | Sentence Transformers |
| Embedding Model | all-MiniLM-L6-v2 |
| Vector Search | FAISS |
| RAG | Custom RAG pipeline |
| Policy / Governance | Python Policy Engine |
| Authentication | JWT |
| Authorization | Role-Based Access Control |
| ITSM Integration | MongoDB-backed ServiceNow-compatible mock adapter |
| Automation | Bounded self-heal workflows |
| Monitoring | Prometheus |
| Dashboard | Grafana |
| Containers | Docker |
| Orchestration | Docker Compose |
| Testing | Pytest |
| HTTP Client | Axios |
| Frontend Styling | CSS |
| Version Control | Git / GitHub |

---

# 6. System Components

## 6.1 React Frontend

The React application provides:

- Employee Portal
- AI Helpdesk
- ITSM Dashboard
- Ticket management
- AI analysis
- Knowledge Base
- Software/service request workflow
- User management
- Ticket activity and audit views

The frontend communicates with FastAPI through REST APIs.

Authentication tokens are stored on the client and automatically attached to API requests.

---

## 6.2 FastAPI Backend

FastAPI is the main application backend.

Responsibilities include:

- Authentication
- Ticket creation and retrieval
- Ticket updates
- AI analysis
- RAG search
- Policy evaluation
- Automation execution
- Knowledge article creation
- ServiceNow-compatible operations
- Audit logging
- Metrics
- Health checks

FastAPI was selected because it provides:

- Python-native API development
- Pydantic validation
- Automatic OpenAPI documentation
- Good async support
- Simple integration with AI/ML libraries
- High development speed

---

## 6.3 MongoDB Atlas

MongoDB Atlas stores the application's operational data.

MongoDB is used for:

- Tickets
- Users
- Audit records
- Knowledge articles
- ServiceNow-compatible incidents
- Service requests

The project does not reset or recreate the database as part of normal application startup.

---

# 7. End-to-End Ticket Flow

A normal AI-assisted ticket follows this workflow:

```text
Employee
   |
   v
AI Helpdesk
   |
   v
FastAPI
   |
   v
RAG Search
   |
   v
Qwen LLM
   |
   v
Structured AI Analysis
   |
   v
Policy Engine
   |
   +--------------------------+
   |                          |
   v                          v
APPROVED                 HUMAN_REVIEW / BLOCKED
   |
   v
Create Ticket
   |
   v
ServiceNow-Compatible Incident
   |
   v
Self-Heal Agent
   |
   v
Validation
   |
   v
AI Resolved
   |
   v
ServiceNow Resolved
   |
   v
Audit Trail
```

This separation makes the workflow easier to reason about and safer than allowing the LLM to directly perform arbitrary operations.

---

# 8. Intelligent Ticket Intake

The AI ticket workflow converts natural-language employee requests into structured ITSM information.

Example:

```text
User:
"My VPN is not connecting."
```

The system can identify:

```text
Intent          : Incident
Category        : Network
Subcategory     : VPN
Priority        : P3
Impact          : Individual
Urgency         : Normal
Assignment Group: Network Support
```

The AI workflow also produces:

- Ticket summary
- Suggested resolution
- Confidence score
- Grounding information
- Recommended automation action

Example:

```text
Issue
  ↓
VPN authentication failure
  ↓
RAG retrieval
  ↓
Qwen analysis
  ↓
Network Support
  ↓
VPN Status Check
```

The structured result is persisted in MongoDB.

---

# 9. RAG Knowledge Retrieval

AegisDesk uses Retrieval-Augmented Generation rather than asking the LLM to answer from its parameters alone.

The pipeline is:

```text
Knowledge Documents
       |
       v
Document Chunking
       |
       v
Sentence Transformer
       |
       v
Embeddings
       |
       v
FAISS Index
       |
       v
Semantic Search
       |
       v
Relevant Knowledge
       |
       v
Qwen LLM
       |
       v
Grounded Response
```

## Embedding Model

The project uses:

```text
all-MiniLM-L6-v2
```

The generated embedding dimension is:

```text
384
```

FAISS uses:

```text
IndexFlatIP
```

with normalized vectors for similarity search.

---

## Knowledge Base

Initial knowledge topics include:

- VPN troubleshooting
- Password reset
- Outlook synchronization
- Wi-Fi troubleshooting
- Laptop performance
- Software installation

The system can also automatically add knowledge articles generated from resolved incidents.

---

## Grounding

The AI workflow uses similarity thresholds to determine whether retrieved knowledge is sufficiently relevant.

This helps prevent unsupported answers.

A grounded response contains information derived from retrieved knowledge instead of relying solely on the LLM's internal knowledge.

---

# 10. LLM Analysis

AegisDesk uses an open-source Hugging Face model:

```text
Qwen/Qwen2.5-0.5B-Instruct
```

The model is loaded lazily by the backend.

The AI service generates structured information such as:

```json
{
  "intent": "Incident",
  "category": "Network",
  "subcategory": "VPN",
  "priority": "P3",
  "impact": "Individual",
  "urgency": "Normal",
  "assignment_group": "Network Support",
  "confidence": 0.94,
  "recommended_action": "vpn_status_check"
}
```

The application combines LLM output with deterministic rules for important ITSM patterns.

This hybrid approach improves consistency for known operational scenarios.

---

# 11. Policy Engine and AI Governance

The Policy Engine is one of the most important safety components.

The architecture intentionally separates:

```text
LLM Recommendation
       |
       v
Policy Engine
       |
       +---- APPROVED
       |
       +---- HUMAN_REVIEW
       |
       +---- BLOCKED
```

The LLM cannot directly decide whether a dangerous operation should execute.

## Allowed automation actions

The current bounded automation actions include:

```text
password_reset
account_unlock
vpn_status_check
application_restart
```

## Blocked actions

Examples include:

```text
disable endpoint security
disable antivirus
disable firewall
modify security policy
delete user/account
grant privileged access
change access control
execute arbitrary shell commands
install unapproved software
```

## Human Review

The policy engine can require human review for higher-risk situations such as:

- P1 incidents
- Enterprise-impacting P2 incidents
- Critical enterprise incidents
- High-impact operational requests

Example:

```text
Normal Individual VPN
        |
        v
APPROVED
```

while:

```text
Enterprise VPN Outage
        |
        v
HUMAN_REVIEW
```

And:

```text
"Disable endpoint security"
        |
        v
BLOCKED
```

This demonstrates a critical enterprise AI principle:

> **AI can recommend an action, but deterministic governance decides whether the action is permitted.**

---

# 12. Auto Resolution and Self-Heal Agent

The self-heal workflow follows:

```text
Identify
   ↓
Diagnose
   ↓
Knowledge Search
   ↓
Determine Automation
   ↓
Policy Validation
   ↓
Execute Bounded Action
   ↓
Validate
   ↓
Update Ticket
   ↓
Update ServiceNow
   ↓
Audit
```

For example, a VPN ticket may result in:

```text
VPN ticket
   ↓
RAG knowledge
   ↓
vpn_status_check
   ↓
Policy = APPROVED
   ↓
Execute VPN Status Check
   ↓
Validation successful
   ↓
Ticket = AI Resolved
   ↓
ServiceNow = Resolved
```

The automation layer does **not** execute arbitrary shell commands.

The actions are deliberately bounded and demo-safe.

---

# 13. Knowledge Management Automation

AegisDesk can turn resolved incidents into reusable knowledge.

The workflow is:

```text
Resolved Ticket
      |
      v
Knowledge Management Automation
      |
      v
Generate Knowledge Article
      |
      v
Index Article
      |
      v
FAISS
      |
      v
Semantic Search
```

Example generated article:

```text
KB-AUTO-89806361

Resolution Guide:
My VPN is not connecting
```

The generated article contains:

- Issue
- Category
- Subcategory
- Reported problem
- Approved resolution
- Recommended next step
- Source ticket ID
- Created-by user
- Publication status

The article is then added to the RAG knowledge index.

This creates a feedback loop:

```text
Ticket
  ↓
Resolution
  ↓
Knowledge Article
  ↓
RAG Index
  ↓
Future Ticket Resolution
```

---

# 14. Self-Service Portal and AI Chatbot

The Employee Portal provides a self-service entry point.

Employees can:

- Ask the AI helpdesk questions
- Search IT knowledge
- Create tickets
- View ticket information
- Request software
- Track ITSM requests

The AI Helpdesk follows:

```text
Employee Question
       |
       v
RAG Search
       |
       v
Relevant Knowledge
       |
       v
AI Response
```

If the issue requires ITSM action:

```text
Conversation
   ↓
Ticket Creation
   ↓
AI Analysis
   ↓
Policy
   ↓
ITSM Workflow
```

This makes the chatbot part of an actual ITSM workflow rather than an isolated conversational interface.

---

# 15. Software Provisioning Automation

Software provisioning is represented as an ITSM service-request workflow.

The flow is:

```text
Employee Portal
      |
      v
Request Software
      |
      v
Software Selection
      |
      v
Service Request
      |
      v
REQ001xxx
      |
      v
Approval
      |
      v
Provisioning
      |
      v
Provisioned
      |
      v
Audit
```

The system is designed around a bounded software catalog rather than arbitrary executable commands.

Example catalog items can include:

```text
Visual Studio Code
Python
Google Chrome
Docker Desktop
Microsoft Office
```

The provisioning workflow is represented as a mock/demo operation and does not silently execute arbitrary installation commands on the host machine.

---

# 16. ServiceNow-Compatible Integration

AegisDesk includes a MongoDB-backed ServiceNow-compatible mock adapter.

This was used because a live ServiceNow developer instance was not available for the assessment environment.

### Important

This project should be described as:

> **ServiceNow-compatible mock/demo integration**

and not as a production ServiceNow instance.

The adapter exposes incident and service-request workflows similar to the ITSM flow expected by the assessment.

## Incident APIs

```text
POST  /api/servicenow/incidents
GET   /api/servicenow/incidents/{number}
PATCH /api/servicenow/incidents/{number}
```

## Service Request APIs

```text
POST  /api/servicenow/requests
GET   /api/servicenow/requests/{number}
PATCH /api/servicenow/requests/{number}
```

The AI ticket workflow can:

```text
Create AegisDesk Ticket
       |
       v
Create ServiceNow-Compatible Incident
       |
       v
Store ServiceNow Reference
       |
       v
Execute Automation
       |
       v
Update Ticket
       |
       v
Update ServiceNow Incident
```

---

# 17. Authentication and RBAC

AegisDesk uses JWT-based authentication.

The basic flow is:

```text
Login
  |
  v
FastAPI Authentication
  |
  v
JWT Token
  |
  v
Frontend
  |
  v
Authorization Header
  |
  v
Protected API
```

Example roles:

```text
Employee
Agent
```

The backend validates the token before allowing protected operations.

The frontend automatically attaches the JWT token to API requests.

---

# 18. Audit Trail

Every important operational action should be traceable.

AegisDesk maintains a ticket audit collection.

Examples of recorded events include:

```text
ticket_created
ticket_updated
automation_executed
servicenow_incident_created
servicenow_incident_updated
knowledge_article_created
```

Example self-heal audit sequence:

```text
1. Ticket created
2. ServiceNow incident created
3. Self-heal automation executed
4. ServiceNow incident updated
```

An audit event can contain:

```text
Ticket ID
Actor
Role
Action
Source
Decision
Previous value
New value
Timestamp
Details
```

This is important for enterprise AI because the system must be able to explain what happened after an automated action.

---

# 19. MongoDB Data Model

AegisDesk uses MongoDB collections for operational persistence.

Conceptually:

```text
MongoDB Atlas
│
├── users
│
├── tickets
│
├── ticket_audit
│
├── knowledge_articles
│
├── servicenow_incidents
│
└── servicenow_requests
```

## Ticket

A ticket contains fields such as:

```text
ticket_id
title
description
category
subcategory
priority
impact
urgency
status
user
assignment_group
resolution
ai_confidence
ai_grounded
policy_action
human_review
source
servicenow_reference
created_at
updated_at
```

## Audit

The audit collection records operational history without requiring destructive changes to existing tickets.

---

# 20. Observability

AegisDesk exposes Prometheus metrics through:

```text
/metrics
```

Important metrics include:

```text
aegisdesk_http_requests_total
aegisdesk_http_request_duration_seconds
aegisdesk_tickets_created_total
aegisdesk_tickets_updated_total
aegisdesk_ai_analysis_total
aegisdesk_policy_decisions_total
```

The monitoring architecture is:

```text
FastAPI
   |
   | /metrics
   v
Prometheus
   |
   v
Grafana
```

Prometheus was verified to scrape the AegisDesk backend successfully.

Grafana can be used to visualize application health and operational metrics.

---

# 21. Docker Deployment

AegisDesk is containerized for local deployment.

Current services include:

```text
aegisdesk-backend
aegisdesk-frontend
aegisdesk-prometheus
aegisdesk-grafana
```

Ports:

| Service | Port |
|---|---:|
| Frontend local development | 5173 |
| Frontend Docker | 3000 |
| FastAPI Backend | 8000 |
| Prometheus | 9090 |
| Grafana | 3001 |

---

# 22. Testing

The backend contains automated Pytest tests covering:

- MongoDB connectivity behavior
- Authentication
- RBAC
- Policy decisions
- AI workflow
- Ticket creation
- Ticket updates
- Audit trail

The latest verified test result is:

```text
18 passed
1 warning
```

Test execution:

```powershell
cd D:\AegisDesk

.\.venv\Scripts\Activate.ps1

pytest
```

The warning is a non-blocking Starlette/httpx deprecation warning from the installed testing stack.

---

# 23. Project Structure

```text
AegisDesk/
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── database/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── rag/
│   │   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── main.py
│   │   ├── metrics.py
│   │   ├── policy_engine.py
│   │   ├── rag_service.py
│   │   ├── self_heal_service.py
│   │   └── servicenow_mock.py
│   │
│   ├── data/
│   │   ├── knowledge.index
│   │   └── knowledge_metadata.json
│   │
│   ├── knowledge/
│   │   └── it_knowledge.json
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth_rbac.py
│   │   ├── test_policy_and_ai_workflow.py
│   │   └── test_tickets_audit.py
│   │
│   ├── Dockerfile
│   ├── requirements-docker.txt
│   ├── requirements-test.txt
│   ├── pytest.ini
│   └── test_mongodb.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── api.js
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── Dockerfile
│   ├── nginx/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── monitoring/
│   └── prometheus/
│       └── prometheus.yml
│
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── README.md
```

---

# 24. Local Development Setup

## Prerequisites

Recommended:

- Windows 10/11
- Python 3.11+
- Node.js
- npm
- Docker Desktop
- Git
- MongoDB Atlas account
- Internet connection for Hugging Face model download on first model load

---

## Clone Repository

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AegisDesk
```

---

## Backend Environment

Create the Python environment:

```powershell
python -m venv .venv
```

Activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r backend\requirements-docker.txt
```

For testing:

```powershell
pip install -r backend\requirements-test.txt
```

---

## Environment Variables

Create:

```text
backend/.env
```

Configure the MongoDB Atlas connection and application secrets required by the backend.

Never commit real secrets.

The repository `.gitignore` excludes:

```text
.env
backend/.env
```

---

## Run FastAPI

From the project root:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Health:

```text
http://127.0.0.1:8000/health
```

---

## Run React

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

---

# 25. Docker Setup

Build and start:

```powershell
cd D:\AegisDesk

docker compose up -d --build
```

Check containers:

```powershell
docker compose ps
```

Expected services:

```text
aegisdesk-backend
aegisdesk-frontend
aegisdesk-prometheus
aegisdesk-grafana
```

Check backend logs:

```powershell
docker compose logs backend --tail 50
```

Stop:

```powershell
docker compose down
```

---

## Docker URLs

Frontend:

```text
http://127.0.0.1:3000
```

Backend:

```text
http://127.0.0.1:8000
```

Prometheus:

```text
http://127.0.0.1:9090
```

Grafana:

```text
http://127.0.0.1:3001
```

---

# 26. Demo Scenarios

## Scenario 1 — Normal VPN Incident

Input:

```text
My VPN is not connecting.
```

Expected architecture:

```text
User Request
    ↓
RAG
    ↓
Qwen
    ↓
Policy Engine
    ↓
APPROVED
    ↓
Ticket
    ↓
ServiceNow Incident
```

Example AI result:

```text
Category          : Network
Subcategory       : VPN
Assignment Group  : Network Support
Priority          : P3
Policy             : APPROVED
Action             : vpn_status_check
```

---

## Scenario 2 — Security Request

Input:

```text
Disable endpoint security so I can install software.
```

Expected:

```text
Qwen
  ↓
Policy Engine
  ↓
BLOCKED
```

The system must not execute the requested security-disabling operation.

This demonstrates AI governance and policy enforcement.

---

## Scenario 3 — Enterprise VPN Incident

Input:

```text
The company's VPN is unavailable for everyone.
```

Expected:

```text
Enterprise Impact
      ↓
P2 / High Impact
      ↓
HUMAN_REVIEW
```

The system does not automatically execute a potentially high-impact operation.

---

## Scenario 4 — Self-Healing

For an approved VPN ticket:

```text
Ticket
  ↓
Policy Approval
  ↓
VPN Status Check
  ↓
Validation
  ↓
AI Resolved
  ↓
ServiceNow Resolved
  ↓
Audit Event
```

---

## Scenario 5 — Knowledge Automation

After resolution:

```text
Resolved Ticket
     ↓
Knowledge Automation
     ↓
KB-AUTO-xxxx
     ↓
Published
     ↓
FAISS
```

A future user can then search for the same type of problem and retrieve the newly generated article.

---

## Scenario 6 — Software Request

```text
Employee Portal
     ↓
Request Software
     ↓
Software Selection
     ↓
Service Request
     ↓
REQ001xxx
     ↓
Approval
     ↓
Provisioning
     ↓
Provisioned
```

---

# 27. API Overview

## Health

```text
GET /health
GET /health/database
```

## Authentication

```text
POST /api/auth/login
GET  /api/auth/me
```

## Tickets

```text
POST  /api/tickets
GET   /api/tickets
GET   /api/tickets/stats
GET   /api/tickets/{ticket_id}
PATCH /api/tickets/{ticket_id}
GET   /api/tickets/{ticket_id}/activity
GET   /api/tickets/{ticket_id}/audit
```

## AI Tickets

```text
POST /api/tickets/ai
```

## AI Analysis

```text
POST /api/ai/analyze
```

## RAG

```text
GET /api/rag/search
```

## Automation

```text
POST /api/automation/execute
```

## Knowledge Management

```text
POST /api/knowledge/automation/from-ticket/{ticket_id}
```

## ServiceNow-Compatible Incidents

```text
POST  /api/servicenow/incidents
GET   /api/servicenow/incidents/{number}
PATCH /api/servicenow/incidents/{number}
```

## ServiceNow-Compatible Requests

```text
POST  /api/servicenow/requests
GET   /api/servicenow/requests/{number}
PATCH /api/servicenow/requests/{number}
```

## Monitoring

```text
GET /metrics
```

---

# 28. Security Considerations

AegisDesk follows several security principles.

## Secrets

Real credentials are stored in environment variables.

```text
.env
backend/.env
```

are excluded from Git.

---

## Authentication

Protected APIs require JWT authentication.

---

## Authorization

Operations are restricted according to user role.

---

## AI Safety

The LLM does not receive unrestricted system access.

The Policy Engine determines:

```text
APPROVED
HUMAN_REVIEW
BLOCKED
```

before automation.

---

## Bounded Automation

Automation actions are explicitly defined.

There is no generic:

```text
execute arbitrary shell command
```

mechanism.

---

## Auditability

Important actions are recorded for traceability.

---

# 29. Verified Results

The current AegisDesk implementation has been verified across the major layers.

## Automated Tests

```text
18 passed
1 non-blocking warning
```

---

## Docker

Verified running services:

```text
aegisdesk-backend      Healthy
aegisdesk-frontend     Running
aegisdesk-prometheus   Running
aegisdesk-grafana      Running
```

---

## Backend Health

Verified:

```text
GET /health
200 OK
```

---

## Prometheus

Verified:

```text
GET /metrics
200 OK
```

Prometheus successfully scrapes the backend.

---

## AI Ticket Workflow

Verified:

```text
RAG
  ↓
Qwen
  ↓
Policy
  ↓
MongoDB
  ↓
ServiceNow-Compatible Incident
```

---

## Self-Heal

Verified approved automation:

```text
VPN Status Check
       ↓
Automation Executed
       ↓
Ticket = AI Resolved
       ↓
ServiceNow = Resolved
```

---

## Knowledge Management

Verified:

```text
Resolved Ticket
       ↓
Knowledge Article
       ↓
FAISS Index
       ↓
Semantic Search
```

The generated article was successfully retrieved by semantic search.

---

## Security Governance

Verified blocked scenario:

```text
Security-disabling request
       ↓
Policy Engine
       ↓
BLOCKED
```

---

# 30. Engineering Highlights

AegisDesk demonstrates:

- AI-powered ITSM
- Intelligent ticket classification
- Retrieval-Augmented Generation
- Semantic search
- Vector indexing
- Open-source LLM integration
- Deterministic AI governance
- Human-in-the-loop workflows
- Self-healing automation
- Knowledge management automation
- Employee self-service
- Software provisioning workflow
- ServiceNow-compatible integration
- JWT authentication
- Role-based access control
- MongoDB Atlas persistence
- REST API development
- Audit logging
- Docker containerization
- Prometheus monitoring
- Grafana dashboards
- Automated testing
- End-to-end workflow verification
- Secure bounded automation
- Enterprise-oriented AI architecture

---

# 31. Limitations and Future Enhancements

The current project is a strong local/demo implementation, but several production-grade extensions are possible.

## Real ServiceNow

Replace the MongoDB-backed mock adapter with:

- ServiceNow Developer Instance
- OAuth authentication
- ServiceNow REST APIs
- Real incident creation
- Real service catalog requests
- Real workflow state synchronization

---

## AI / LLM

Possible enhancements:

- Larger Qwen model
- GPU inference
- Better structured-output validation
- LLM evaluation framework
- Prompt/version management
- Model monitoring
- Fine-tuning for ITSM classification

---

## RAG

Possible enhancements:

- More enterprise knowledge sources
- PDF ingestion
- DOCX ingestion
- Web knowledge connectors
- Hybrid keyword + vector search
- Reranking
- Metadata filtering
- Better chunking strategies
- Knowledge freshness/versioning

---

## Automation

Possible enhancements:

- More IT automation playbooks
- Approval workflows
- Integration with endpoint-management tools
- Real password reset integration
- Real account-unlock integration
- Real application health checks
- Stronger rollback mechanisms

---

## Security

Possible enhancements:

- OAuth2/OIDC
- SSO
- MFA
- Fine-grained RBAC
- Secret manager integration
- Rate limiting
- API gateway
- Security scanning
- Full audit immutability

---

## Observability

Possible enhancements:

- Distributed tracing
- OpenTelemetry
- Centralized logs
- Alertmanager
- SLO/SLA dashboards
- AI latency dashboards
- RAG retrieval-quality metrics
- Automation success/failure metrics

---

## Deployment

Possible future deployment:

```text
Docker
   ↓
Kubernetes
   ↓
Cloud
```

Potential cloud targets include:

- AWS
- Azure
- Google Cloud
- Oracle Cloud

The current implementation intentionally remains local-first and does not require paid cloud infrastructure.

---

# 32. Author

**Suriya MG**

B.Tech — Computer Science and Engineering  
Vellore Institute of Technology

---

# 33. Final Project Summary

AegisDesk brings together AI, ITSM, software engineering, security, automation, and observability into a single platform.

```text
                         AEGISDESK
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
     Employee Portal     AI Helpdesk       ITSM Dashboard
          |                  |                  |
          +------------------+------------------+
                             |
                             v
                         FastAPI
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
        RAG                Qwen            MongoDB
          |                  |                  |
          +---------+--------+                  |
                    |                           |
                    v                           |
              Policy Engine                     |
                    |                           |
          +---------+---------+                 |
          |                   |                 |
          v                   v                 |
      APPROVED           HUMAN_REVIEW           |
          |                   |                 |
          v                   v                 |
     Self-Heal             Agent               |
          |                                     |
          v                                     |
      Validation                               |
          |                                     |
          +------------------+------------------+
                             |
                             v
                  ServiceNow-Compatible
                       Integration
                             |
                             v
                        Audit Trail

Knowledge Automation:
Ticket → Resolution → Knowledge Article → FAISS → Future RAG

Monitoring:
FastAPI → Prometheus → Grafana
```

The core design philosophy is:

```text
AI recommends
     ↓
RAG grounds
     ↓
Policy governs
     ↓
Automation executes only approved actions
     ↓
Validation confirms outcome
     ↓
ITSM records are updated
     ↓
Audit trail records what happened
```

This makes AegisDesk more than a chatbot. It is an end-to-end demonstration of how AI can be integrated into an enterprise ITSM workflow while maintaining grounding, governance, bounded automation, auditability, and operational visibility.

---

## Project Status

**Current status: Core AegisDesk implementation completed and locally verified across AI ticket intake, RAG, policy governance, self-healing, knowledge management automation, self-service, ServiceNow-compatible integration, authentication/RBAC, audit logging, Docker, monitoring, and automated testing.**

The repository is maintained as a local-first engineering project and is structured for further integration with a live ServiceNow instance, production-grade identity, additional automation playbooks, stronger observability, and cloud deployment.
