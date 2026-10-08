import { useEffect, useState } from "react";
import {
  Activity, AlertCircle, Bot, BookOpen, CheckCircle2, ChevronRight,
  CircleHelp, Clock3, FileText, LayoutDashboard, MessageSquare, Search,
  Send, Settings, ShieldCheck, Sparkles, Ticket, User, Wrench, XCircle,
  LogOut, Users, LockKeyhole,
} from "lucide-react";
import api from "./api";
import "./App.css";

const navigationItems = [
  { id: "home", label: "Employee Portal", icon: LayoutDashboard, roles: ["employee", "agent", "admin"] },
  { id: "chat", label: "AI Helpdesk", icon: MessageSquare, roles: ["employee", "agent", "admin"] },
  { id: "dashboard", label: "ITSM Dashboard", icon: Activity, roles: ["agent", "admin"] },
  { id: "analysis", label: "AI Analysis", icon: Sparkles, roles: ["agent", "admin"] },
  { id: "knowledge", label: "Knowledge Base", icon: BookOpen, roles: ["employee", "agent", "admin"] },
  { id: "admin-users", label: "User Management", icon: Users, roles: ["admin"] },
];

function App() {
  const [activePage, setActivePage] = useState("home");
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("aegisdesk_user") || "null");
    } catch {
      return null;
    }
  });
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("aegisdesk_token");
    if (!token) {
      setAuthLoading(false);
      return;
    }

    api.get("/api/auth/me")
      .then((response) => {
        setCurrentUser(response.data.user);
        localStorage.setItem("aegisdesk_user", JSON.stringify(response.data.user));
      })
      .catch(() => {
        localStorage.removeItem("aegisdesk_token");
        localStorage.removeItem("aegisdesk_user");
        setCurrentUser(null);
      })
      .finally(() => setAuthLoading(false));

    const handleUnauthorized = () => {
      localStorage.removeItem("aegisdesk_token");
      localStorage.removeItem("aegisdesk_user");
      setCurrentUser(null);
    };
    window.addEventListener("aegisdesk:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("aegisdesk:unauthorized", handleUnauthorized);
  }, []);

  const handleLogin = (user, token) => {
    localStorage.setItem("aegisdesk_token", token);
    localStorage.setItem("aegisdesk_user", JSON.stringify(user));
    setCurrentUser(user);
    setActivePage(user.role === "employee" ? "home" : "dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("aegisdesk_token");
    localStorage.removeItem("aegisdesk_user");
    setCurrentUser(null);
    setActivePage("home");
  };

  if (authLoading) {
    return <div className="auth-loading"><ShieldCheck size={30} /><span>Loading AegisDesk...</span></div>;
  }

  if (!currentUser) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  const allowedNavigation = navigationItems.filter((item) => item.roles.includes(currentUser.role));
  const safePage = allowedNavigation.some((item) => item.id === activePage) ? activePage : allowedNavigation[0]?.id || "home";

  const renderPage = () => {
    switch (safePage) {
      case "chat": return <AIHelpdesk currentUser={currentUser} />;
      case "dashboard": return <ITSMDashboard currentUser={currentUser} />;
      case "analysis": return <AIAnalysis />;
      case "knowledge": return <KnowledgeBase />;
      case "admin-users": return <AdminUsers />;
      default: return <EmployeePortal onNavigate={setActivePage} currentUser={currentUser} />;
    }
  };

  return (
    <div className="app-shell">
      <Sidebar activePage={safePage} onNavigate={setActivePage} currentUser={currentUser} onLogout={handleLogout} />
      <main className="main-content">
        <Header activePage={safePage} currentUser={currentUser} />
        <section className="page-container">{renderPage()}</section>
      </main>
    </div>
  );
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("employee");
  const [password, setPassword] = useState("Employee@123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.post("/api/auth/login", { username, password });
      onLogin(response.data.user, response.data.access_token);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <div className="auth-brand">
          <div className="brand-icon"><ShieldCheck size={28} /></div>
          <div><div className="brand-name">AegisDesk</div><div className="brand-subtitle">AI ITSM Platform</div></div>
        </div>
        <div className="auth-heading">
          <span className="section-kicker">SECURE ACCESS</span>
          <h1>Sign in to AegisDesk</h1>
          <p>Authenticate to access your role-based ITSM workspace.</p>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
          {error && <div className="auth-error"><AlertCircle size={16} />{error}</div>}
          <button className="auth-submit" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
        </form>
        <div className="demo-credentials">
          <strong>Demo accounts</strong>
          <span>Employee: <code>employee / Employee@123</code></span>
          <span>Agent: <code>agent / Agent@123</code></span>
          <span>Admin: <code>admin / Admin@123</code></span>
        </div>
      </div>
    </div>
  );
}

function Sidebar({ activePage, onNavigate, currentUser, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon"><ShieldCheck size={25} /></div>
        <div>
          <div className="brand-name">AegisDesk</div>
          <div className="brand-subtitle">AI ITSM Platform</div>
        </div>
      </div>
      <div className="sidebar-section-title">WORKSPACE</div>
      <nav className="navigation">
        {navigationItems.filter((item) => item.roles.includes(currentUser.role)).map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={19} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="sidebar-bottom">
        <button className="nav-item"><Settings size={19} /><span>Settings</span></button>
        <div className="user-card">
          <div className="user-avatar">{String(currentUser.display_name || currentUser.username).slice(0, 2).toUpperCase()}</div>
          <div className="user-details">
            <div className="user-name">{currentUser.display_name || currentUser.username}</div>
            <div className="user-role">{currentUser.role}</div>
          </div>
          <button className="logout-button" onClick={onLogout} title="Sign out"><LogOut size={16} /></button>
        </div>
      </div>
    </aside>
  );
}

function Header({ activePage, currentUser }) {
  const currentPage =
    navigationItems.find((item) => item.id === activePage)?.label ||
    "Employee Portal";

  return (
    <header className="top-header">
      <div>
        <div className="breadcrumb">AegisDesk AI / Workspace</div>
        <h1>{currentPage}</h1>
      </div>
      <div className="header-actions">
        <div className="system-status">
          <span className="status-dot" /> All systems operational
        </div>
        <button className="icon-button"><CircleHelp size={19} /></button>
        <div className="header-user"><span>{currentUser.display_name || currentUser.username}</span><small>{currentUser.role}</small></div>
        <div className="header-avatar">{String(currentUser.display_name || currentUser.username).slice(0, 2).toUpperCase()}</div>
      </div>
    </header>
  );
}

function EmployeePortal({ onNavigate, currentUser }) {
  const [request, setRequest] = useState("");
  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [databaseStatus, setDatabaseStatus] = useState("Checking...");
  const [aiStatus, setAiStatus] = useState("Checking...");
  const [stats, setStats] = useState({
    total: 0, open: 0, ai_resolved: 0, escalated: 0,
  });

  useEffect(() => {
    api.get("/health")
      .then((r) => setBackendStatus(r.data.status === "healthy" ? "Connected" : "Unavailable"))
      .catch(() => setBackendStatus("Unavailable"));

    api.get("/health/database")
      .then((r) => setDatabaseStatus(r.data.connection === "successful" ? "Connected" : "Unavailable"))
      .catch(() => setDatabaseStatus("Unavailable"));

    api.get("/api/rag/status")
      .then((r) => setAiStatus(r.data.status === "ready" ? "Ready" : "Available"))
      .catch(() => setAiStatus("Available"));

    api.get("/api/tickets/stats")
      .then((r) => setStats(r.data))
      .catch(() => {});
  }, []);

  const openHelpdesk = () => {
    onNavigate("chat");
  };

  const quickActions = [
    {
      title: "Report an IT Issue",
      description: "Submit an IT problem and create a real MongoDB-backed ticket.",
      icon: Ticket,
      action: openHelpdesk,
    },
    {
      title: "Ask the Knowledge Base",
      description: "Find answers from approved enterprise IT documentation.",
      icon: BookOpen,
      action: () => onNavigate("knowledge"),
    },
    {
      title: "Request Software",
      description: "Request approved software through the governed ITSM workflow.",
      icon: Wrench,
      action: openHelpdesk,
    },
  ];

  return (
    <div className="page-content">
      <section className="hero-section">
        <div className="hero-content">
          <div className="eyebrow"><Sparkles size={15} /> AI-POWERED ENTERPRISE SUPPORT</div>
          <h2>How can we help <span>today?</span></h2>
          <p>
            Describe your IT problem in natural language. AegisDesk retrieves
            approved enterprise knowledge, analyzes the request, applies policy
            and prepares the right ITSM next step.
          </p>

          <div className="hero-search">
            <MessageSquare size={21} />
            <input
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  openHelpdesk();
                }
              }}
              placeholder="Example: My VPN is not connecting..."
            />
            <button onClick={openHelpdesk}>
              <Send size={17} /> Ask AegisDesk
            </button>
          </div>

          <div className="suggestion-row">
            <span>Try:</span>
            <button onClick={() => { setRequest("My password has expired"); openHelpdesk(); }}>
              "My password has expired"
            </button>
            <button onClick={() => { setRequest("VPN is not connecting"); openHelpdesk(); }}>
              "VPN is not connecting"
            </button>
            <button onClick={() => { setRequest("I need Visual Studio Code"); openHelpdesk(); }}>
              "I need Visual Studio Code"
            </button>
          </div>
        </div>

        <div className="hero-agent-card">
          <div className="agent-orbit">
            <div className="agent-icon-large"><Bot size={42} /></div>
          </div>
          <div className="agent-card-title">AegisDesk AI Agent</div>
          <div className="agent-card-description">
            RAG retrieval, AI analysis, ITSM ticketing and policy-governed automation.
          </div>
          <div className="agent-capabilities">
            <span><CheckCircle2 size={15} /> RAG</span>
            <span><CheckCircle2 size={15} /> Qwen</span>
            <span><CheckCircle2 size={15} /> Policy</span>
            <span><CheckCircle2 size={15} /> ITSM</span>
          </div>
        </div>
      </section>

      <section className="section-header">
        <div>
          <div className="section-kicker">SELF SERVICE</div>
          <h3>What do you need?</h3>
        </div>
      </section>

      <section className="quick-actions">
        {quickActions.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.title} className="quick-action-card" onClick={item.action}>
              <div className="quick-action-icon"><Icon size={23} /></div>
              <div className="quick-action-content">
                <h4>{item.title}</h4>
                <p>{item.description}</p>
              </div>
              <ChevronRight size={19} className="quick-arrow" />
            </button>
          );
        })}
      </section>

      <section className="connection-status-panel">
        <ConnectionCard label="BACKEND" value={backendStatus} good={backendStatus === "Connected"} />
        <ConnectionCard label="DATABASE" value={databaseStatus} good={databaseStatus === "Connected"} />
        <ConnectionCard label="RAG ENGINE" value={aiStatus} good={aiStatus === "Ready" || aiStatus === "Available"} />
      </section>

      <section className="stats-grid">
        <StatCard icon={Ticket} value={stats.total} label="Total Tickets" trend="MongoDB Atlas" />
        <StatCard icon={Clock3} value={stats.open} label="Open Tickets" trend="Open + In Progress" />
        <StatCard icon={Sparkles} value={stats.ai_resolved} label="AI Resolved" trend="Governed workflow" />
        <StatCard icon={AlertCircle} value={stats.escalated} label="Escalated" trend="Human support" />
      </section>
    </div>
  );
}

function AIHelpdesk({ currentUser }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [creating, setCreating] = useState(null);
  const [searching, setSearching] = useState(null);
  const [createdTickets, setCreatedTickets] = useState({});
  const [ticketResults, setTicketResults] = useState({});
  const [ragResults, setRagResults] = useState({});

  const sendMessage = () => {
    const text = message.trim();
    if (!text) return;

    setMessages((current) => [
      ...current,
      { id: `${Date.now()}-${Math.random()}`, text },
    ]);
    setMessage("");
  };

  const createAITicket = async (item) => {
    setCreating(item.id);

    try {
      const response = await api.post("/api/tickets/ai", {
        query: item.text,
        user: currentUser.username,
        source: "AI Helpdesk",
        top_k: 5,
      });

      setCreatedTickets((current) => ({
        ...current,
        [item.id]: response.data.ticket.ticket_id,
      }));

      setTicketResults((current) => ({
        ...current,
        [item.id]: response.data,
      }));
    } catch (error) {
      setCreatedTickets((current) => ({
        ...current,
        [item.id]: `ERROR: ${error.response?.data?.detail || "Unable to create AI ticket"}`,
      }));
    } finally {
      setCreating(null);
    }
  };

  const searchKnowledge = async (item) => {
    setSearching(item.id);

    try {
      const response = await api.get("/api/rag/search", {
        params: { q: item.text, top_k: 3 },
      });

      setRagResults((current) => ({
        ...current,
        [item.id]: response.data,
      }));
    } catch (error) {
      setRagResults((current) => ({
        ...current,
        [item.id]: {
          error: error.response?.data?.detail || "RAG search failed",
        },
      }));
    } finally {
      setSearching(null);
    }
  };

  return (
    <div className="page-content">
      <div className="page-title-row">
        <div>
          <div className="section-kicker">SELF-SERVICE</div>
          <h2>AI Helpdesk</h2>
          <p>Ask a question, retrieve knowledge, analyze the request and create a governed ITSM ticket.</p>
        </div>
        <div className="ai-badge">
          <span className="status-dot" /> RAG + Qwen + Policy Online
        </div>
      </div>

      <div className="helpdesk-layout">
        <section className="chat-panel">
          <div className="chat-header">
            <div className="chat-agent">
              <div className="small-agent-icon"><Bot size={19} /></div>
              <div>
                <strong>AegisDesk AI</strong>
                <span>IT Support & Governance Assistant</span>
              </div>
            </div>
          </div>

          <div className="chat-body">
            <div className="ai-message">
              <div className="message-avatar"><Bot size={17} /></div>
              <div className="message-bubble">
                <strong>Welcome to AegisDesk.</strong>
                <p>
                  Describe your IT issue. I can retrieve approved knowledge,
                  analyze the request with Qwen, apply the Policy Engine and
                  create a real MongoDB-backed governed ticket.
                </p>
                <div className="chat-suggestions">
                  <button onClick={() => setMessage("My VPN is not connecting")}>VPN issue</button>
                  <button onClick={() => setMessage("My password has expired")}>Password reset</button>
                  <button onClick={() => setMessage("The VPN is down for everyone in the company")}>Company VPN outage</button>
                  <button onClick={() => setMessage("Disable the antivirus and endpoint security so I can install this software")}>Security test</button>
                </div>
              </div>
            </div>

            {messages.map((item) => {
              const result = ragResults[item.id];
              const workflow = ticketResults[item.id];
              const created = createdTickets[item.id];

              return (
                <div className="conversation-block" key={item.id}>
                  <div className="user-message">
                    <div className="user-message-bubble">{item.text}</div>
                    <div className="message-avatar user-message-avatar"><User size={16} /></div>
                  </div>

                  <div className="rag-action-card">
                    <div>
                      <strong>Knowledge Retrieval</strong>
                      <p>Search approved enterprise documents with embeddings + FAISS.</p>
                    </div>
                    <button onClick={() => searchKnowledge(item)} disabled={searching === item.id}>
                      {searching === item.id ? "Searching..." : "Search Knowledge"}
                    </button>
                  </div>

                  {result && !result.error && (
                    <div className="rag-results-card">
                      <div className="rag-result-header">
                        <strong>Retrieved Sources</strong>
                        <span>{result.count} matches</span>
                      </div>
                      {result.results.map((source) => (
                        <div className="rag-result" key={source.chunk_id}>
                          <div className="source-icon"><FileText size={15} /></div>
                          <div>
                            <strong>{source.title}</strong>
                            <span>{source.category} · similarity {Math.round(source.similarity * 100)}%</span>
                            <p>{source.text}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {result?.error && <div className="error-banner">{result.error}</div>}

                  <div className="ticket-action-card">
                    <div>
                      <strong>AI-Governed ITSM Ticket</strong>
                      <p>RAG → Qwen → Policy Engine → MongoDB.</p>
                    </div>

                    {created ? (
                      <span className={created.startsWith("ERROR") ? "ticket-error" : "ticket-created"}>
                        {created.startsWith("ERROR") ? created : `Created ${created}`}
                      </span>
                    ) : (
                      <button onClick={() => createAITicket(item)} disabled={creating === item.id}>
                        {creating === item.id ? "Analyzing..." : "Analyze & Create AI Ticket"}
                      </button>
                    )}
                  </div>

                  {workflow && (
                    <WorkflowResult data={workflow} />
                  )}
                </div>
              );
            })}
          </div>

          <div className="chat-input-area">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendMessage();
              }}
              placeholder="Ask about VPN, passwords, Outlook, Wi-Fi, software..."
            />
            <button onClick={sendMessage}><Send size={17} /></button>
          </div>
        </section>

        <aside className="chat-info-panel">
          <div className="info-card">
            <div className="info-card-icon"><Sparkles size={20} /></div>
            <h3>Current AI pipeline</h3>
            <InfoItem title="1. Retrieve" description="MiniLM embeddings and FAISS find approved enterprise knowledge." />
            <InfoItem title="2. Analyze" description="Qwen classifies intent, category, priority, impact and urgency." />
            <InfoItem title="3. Govern" description="Policy Engine v1.1 evaluates grounding, confidence, impact and blocked requests." />
            <InfoItem title="4. Ticket" description="The governed result is persisted in MongoDB with audit fields." />
          </div>

          <div className="safety-card">
            <ShieldCheck size={19} />
            <div>
              <strong>Policy-controlled workflow</strong>
              <p>Approved actions are only candidates. Actual action execution remains disabled.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function WorkflowResult({ data }) {
  const policy = data.policy || {};
  const ticket = data.ticket || {};
  const decision = policy.decision || ticket.policy_decision || "UNKNOWN";

  const decisionClass =
    decision === "APPROVED"
      ? "approved"
      : decision === "BLOCKED"
        ? "blocked"
        : "human-review";

  return (
    <div className="workflow-result">
      <div className="workflow-header">
        <div>
          <span className="analysis-label">AI GOVERNANCE RESULT</span>
          <h3>Workflow completed</h3>
        </div>
        <span className={`policy-badge ${decisionClass}`}>
          {decision === "APPROVED" && <CheckCircle2 size={15} />}
          {decision === "HUMAN_REVIEW" && <AlertCircle size={15} />}
          {decision === "BLOCKED" && <XCircle size={15} />}
          {decision}
        </span>
      </div>

      <div className="workflow-steps">
        <WorkflowStep label="RAG" value="Completed" />
        <WorkflowStep label="Qwen" value="Completed" />
        <WorkflowStep label="Policy" value={decision} />
        <WorkflowStep label="Ticket" value={ticket.ticket_id || "Created"} />
      </div>

      <div className="ticket-detail-grid">
        <TicketDetail label="Ticket ID" value={ticket.ticket_id} />
        <TicketDetail label="Category" value={`${ticket.category || "-"} / ${ticket.subcategory || "-"}`} />
        <TicketDetail label="Priority" value={ticket.priority} />
        <TicketDetail label="Impact" value={ticket.impact} />
        <TicketDetail label="Urgency" value={ticket.urgency} />
        <TicketDetail label="Assignment" value={ticket.assignment_group} />
        <TicketDetail label="AI Confidence" value={formatConfidence(ticket.ai_confidence)} />
        <TicketDetail label="RAG Grounded" value={ticket.ai_grounded ? "Yes" : "No"} />
        <TicketDetail label="Policy Version" value={ticket.policy_version} />
        <TicketDetail label="Policy Action" value={ticket.policy_action || "None"} />
      </div>

      <div className={`policy-reason ${decisionClass}`}>
        <strong>Policy reason</strong>
        <p>{ticket.policy_reason || policy.reason || "No policy reason supplied."}</p>
      </div>

      {ticket.ai_recommendation && (
        <div className="recommendation-box">
          <strong>AI recommended action</strong>
          <p>{ticket.ai_recommendation}</p>
        </div>
      )}

      <div className="workflow-note">
        <ShieldCheck size={15} />
        Execution remains disabled. The Policy Engine only determines whether an action may proceed.
      </div>
    </div>
  );
}

function WorkflowStep({ label, value }) {
  return (
    <div className="workflow-step">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TicketDetail({ label, value }) {
  return (
    <div className="ticket-detail">
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function formatConfidence(value) {
  if (value === null || value === undefined) return "-";
  return `${Math.round(Number(value) * 100)}%`;
}

function ITSMDashboard({ currentUser }) {
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({ total: 0, open: 0, ai_resolved: 0, escalated: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [selectedTicket, setSelectedTicket] = useState(null);

  const handleTicketUpdated = (updatedTicket) => {
    setTickets((current) =>
      current.map((ticket) =>
        ticket.ticket_id === updatedTicket.ticket_id ? updatedTicket : ticket
      )
    );
    setSelectedTicket(updatedTicket);
    loadTickets();
  };

  const loadTickets = () => {
    setLoading(true);
    Promise.all([
      api.get("/api/tickets?limit=100"),
      api.get("/api/tickets/stats"),
    ])
      .then(([a, b]) => {
        setTickets(a.data.tickets || []);
        setStats(b.data);
        setError("");
      })
      .catch((e) => setError(e.response?.data?.detail || "Unable to load ticket data"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTickets();
  }, []);

  const governanceCounts = tickets.reduce(
    (acc, ticket) => {
      const decision = ticket.policy_decision || "UNASSESSED";
      if (decision === "APPROVED") acc.approved += 1;
      else if (decision === "HUMAN_REVIEW") acc.humanReview += 1;
      else if (decision === "BLOCKED") acc.blocked += 1;
      else acc.unassessed += 1;
      return acc;
    },
    { approved: 0, humanReview: 0, blocked: 0, unassessed: 0 }
  );

  const priorityCounts = tickets.reduce((acc, ticket) => {
    const priority = ticket.priority || "Unknown";
    acc[priority] = (acc[priority] || 0) + 1;
    return acc;
  }, {});

  const categoryCounts = tickets.reduce((acc, ticket) => {
    const category = ticket.category || "Unclassified";
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {});

  const aiTickets = tickets.filter((ticket) => typeof ticket.ai_confidence === "number");
  const averageConfidence = aiTickets.length
    ? Math.round((aiTickets.reduce((sum, ticket) => sum + Number(ticket.ai_confidence), 0) / aiTickets.length) * 100)
    : 0;
  const groundedTickets = tickets.filter((ticket) => ticket.ai_grounded === true).length;
  const groundedRate = tickets.length ? Math.round((groundedTickets / tickets.length) * 100) : 0;
  const humanReviewRate = tickets.length
    ? Math.round((governanceCounts.humanReview / tickets.length) * 100)
    : 0;

  const filteredTickets = tickets.filter((ticket) => {
    const decision = ticket.policy_decision || "UNASSESSED";
    const matchesFilter = filter === "ALL" || decision === filter;
    const needle = search.trim().toLowerCase();
    if (!needle) return matchesFilter;

    const haystack = [
      ticket.ticket_id,
      ticket.title,
      ticket.category,
      ticket.subcategory,
      ticket.priority,
      ticket.status,
      ticket.assignment_group,
      ticket.policy_decision,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return matchesFilter && haystack.includes(needle);
  });

  const totalGoverned = governanceCounts.approved + governanceCounts.humanReview + governanceCounts.blocked;
  const governanceRate = tickets.length ? Math.round((totalGoverned / tickets.length) * 100) : 0;

  return (
    <div className="page-content">
      <div className="page-title-row dashboard-page-title">
        <div>
          <div className="section-kicker">OPERATIONS</div>
          <h2>ITSM Dashboard</h2>
          <p>Live ticket operations, policy governance and AI workload from MongoDB Atlas.</p>
        </div>
        <button className="primary-button dashboard-refresh" onClick={loadTickets} disabled={loading}>
          <Activity size={17} /> {loading ? "Refreshing..." : "Refresh Data"}
        </button>
      </div>

      <section className="dashboard-stats">
        <DashboardMetric title="Total Tickets" value={stats.total} icon={Ticket} />
        <DashboardMetric title="Open" value={stats.open} icon={Clock3} />
        <DashboardMetric title="AI Resolved" value={stats.ai_resolved} icon={Sparkles} />
        <DashboardMetric title="Escalated" value={stats.escalated} icon={AlertCircle} />
      </section>

      <section className="governance-overview">
        <div className="dashboard-card governance-summary-card">
          <div className="card-heading">
            <div>
              <div className="card-eyebrow">POLICY ENGINE V1.1</div>
              <h3>Governance Overview</h3>
              <p>Decision distribution across all loaded MongoDB tickets</p>
            </div>
            <div className="governance-rate">{governanceRate}% governed</div>
          </div>

          <div className="governance-count-grid">
            <GovernanceCount title="Approved" value={governanceCounts.approved} icon={CheckCircle2} tone="approved" onClick={() => setFilter("APPROVED")} active={filter === "APPROVED"} />
            <GovernanceCount title="Human Review" value={governanceCounts.humanReview} icon={AlertCircle} tone="human-review" onClick={() => setFilter("HUMAN_REVIEW")} active={filter === "HUMAN_REVIEW"} />
            <GovernanceCount title="Blocked" value={governanceCounts.blocked} icon={XCircle} tone="blocked" onClick={() => setFilter("BLOCKED")} active={filter === "BLOCKED"} />
            <GovernanceCount title="Unassessed" value={governanceCounts.unassessed} icon={CircleHelp} tone="neutral" onClick={() => setFilter("UNASSESSED")} active={filter === "UNASSESSED"} />
          </div>

          <div className="governance-bar">
            <span className="governance-bar-approved" style={{ width: `${tickets.length ? (governanceCounts.approved / tickets.length) * 100 : 0}%` }} />
            <span className="governance-bar-review" style={{ width: `${tickets.length ? (governanceCounts.humanReview / tickets.length) * 100 : 0}%` }} />
            <span className="governance-bar-blocked" style={{ width: `${tickets.length ? (governanceCounts.blocked / tickets.length) * 100 : 0}%` }} />
          </div>
          <div className="governance-bar-legend">
            <span><i className="legend-approved" /> Approved</span>
            <span><i className="legend-review" /> Human Review</span>
            <span><i className="legend-blocked" /> Blocked</span>
          </div>
        </div>

        <div className="dashboard-card workload-card">
          <div className="card-heading">
            <div>
              <div className="card-eyebrow">WORKLOAD</div>
              <h3>Workload Distribution</h3>
              <p>Priority and category mix</p>
            </div>
          </div>
          <DistributionList title="Priority" values={priorityCounts} order={["P1", "P2", "P3", "P4"]} />
          <DistributionList title="Category" values={categoryCounts} />
        </div>
      </section>

      <section className="dashboard-card ai-signals-card">
        <div className="card-heading">
          <div>
            <div className="card-eyebrow">AI QUALITY SIGNALS</div>
            <h3>AI & RAG Health</h3>
            <p>Quality indicators calculated from the tickets currently loaded from MongoDB.</p>
          </div>
        </div>
        <div className="ai-signal-grid">
          <AISignal title="Average AI Confidence" value={`${averageConfidence}%`} description={`${aiTickets.length} AI-analyzed tickets`} icon={Sparkles} tone="blue" />
          <AISignal title="RAG Grounded" value={`${groundedRate}%`} description={`${groundedTickets} tickets grounded in knowledge`} icon={BookOpen} tone="green" />
          <AISignal title="Human Review Rate" value={`${humanReviewRate}%`} description={`${governanceCounts.humanReview} tickets awaiting review`} icon={AlertCircle} tone="amber" />
          <AISignal title="Policy Decisions" value={totalGoverned} description={`${governanceCounts.approved} approved · ${governanceCounts.blocked} blocked`} icon={ShieldCheck} tone="purple" />
        </div>
      </section>

      <section className="dashboard-card large-card ticket-operations-card">
        <div className="card-heading ticket-list-heading">
          <div>
            <div className="card-eyebrow">LIVE OPERATIONS</div>
            <h3>Ticket Operations</h3>
            <p>Click any ticket to inspect its ITSM, AI and governance details.</p>
          </div>
          <span className="live-label"><span className="status-dot" /> Live MongoDB</span>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="ticket-controls">
          <div className="ticket-filter-group">
            {[["ALL", "All"], ["APPROVED", "Approved"], ["HUMAN_REVIEW", "Human Review"], ["BLOCKED", "Blocked"], ["UNASSESSED", "Unassessed"]].map(([value, label]) => (
              <button key={value} className={`filter-button ${filter === value ? "active" : ""}`} onClick={() => setFilter(value)}>{label}</button>
            ))}
          </div>
          <div className="ticket-search">
            <Search size={15} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search ticket, category, status..." />
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Loading tickets...</div>
        ) : filteredTickets.length === 0 ? (
          <div className="empty-state">No tickets match the current filter.</div>
        ) : (
          <div className="ticket-table">
            <div className="ticket-table-header ticket-table-header-extended">
              <span>Ticket</span><span>Category</span><span>Priority</span><span>Status</span><span>Policy</span>
            </div>
            {filteredTickets.map((ticket) => (
              <button className="ticket-row ticket-row-extended ticket-row-button" key={ticket.ticket_id} onClick={() => setSelectedTicket(ticket)}>
                <div>
                  <strong>{ticket.ticket_id}</strong>
                  <span>{ticket.title}</span>
                </div>
                <span>{ticket.category || "-"} / {ticket.subcategory || "-"}</span>
                <PriorityBadge priority={ticket.priority} />
                <StatusBadge status={ticket.status} />
                <PolicyBadge decision={ticket.policy_decision} />
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-grid dashboard-grid-bottom">
        <div className="dashboard-card">
          <div className="card-heading"><div><h3>Policy Governance</h3><p>Current Policy Engine v1.1</p></div></div>
          <GovernanceItem title="Approved" description="Low-risk requests mapped to the approved automation allowlist." />
          <GovernanceItem title="Human Review" description="High-impact requests require human approval before automation." />
          <GovernanceItem title="Blocked" description="Security, access-control or prohibited actions are blocked." />
        </div>
        <div className="dashboard-card">
          <div className="card-heading"><div><h3>Approved Actions</h3><p>Allowlist exists; execution remains disabled</p></div></div>
          <AutomationItem title="Password Reset" status="Policy allowlist" />
          <AutomationItem title="Account Unlock" status="Policy allowlist" />
          <AutomationItem title="VPN Status Check" status="Policy allowlist" />
          <AutomationItem title="Application Restart" status="Policy allowlist" />
        </div>
      </section>

      {selectedTicket && (
        <TicketDetailModal
          ticket={selectedTicket}
          onClose={() => setSelectedTicket(null)}
          onUpdated={handleTicketUpdated}
        />
      )}
    </div>
  );
}

function AISignal({ title, value, description, icon: Icon, tone }) {
  return (
    <div className={`ai-signal ${tone}`}>
      <div className="ai-signal-icon"><Icon size={18} /></div>
      <div className="ai-signal-content"><span>{title}</span><strong>{value}</strong><small>{description}</small></div>
    </div>
  );
}

function TicketDetailModal({ ticket, onClose, onUpdated }) {
  const [form, setForm] = useState({
    status: ticket.status || "Open",
    priority: ticket.priority || "P3",
    assignment_group: ticket.assignment_group || "Service Desk",
    resolution: ticket.resolution || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    setForm({
      status: ticket.status || "Open",
      priority: ticket.priority || "P3",
      assignment_group: ticket.assignment_group || "Service Desk",
      resolution: ticket.resolution || "",
    });
    setEditMode(false);
    setError("");
  }, [ticket.ticket_id, ticket.updated_at]);

  const decision = ticket.policy_decision || "UNASSESSED";
  const decisionClass =
    decision === "APPROVED"
      ? "approved"
      : decision === "BLOCKED"
        ? "blocked"
        : decision === "HUMAN_REVIEW"
          ? "human-review"
          : "neutral";

  const saveChanges = async () => {
    setSaving(true);
    setError("");
    try {
      const response = await api.patch(`/api/tickets/${ticket.ticket_id}`, form);
      onUpdated(response.data.ticket);
      setEditMode(false);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to update ticket.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="ticket-modal-backdrop" onClick={onClose}>
      <div className="ticket-modal ticket-lifecycle-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ticket-modal-header">
          <div>
            <span className="analysis-label">INCIDENT / REQUEST DETAILS</span>
            <h3>{ticket.ticket_id}</h3>
            <p>{ticket.title}</p>
          </div>
          <div className="modal-header-actions">
            {!editMode && (
              <button className="secondary-button modal-edit-button" onClick={() => setEditMode(true)}>
                <Wrench size={14} /> Edit Ticket
              </button>
            )}
            <button className="modal-close" onClick={onClose} aria-label="Close"><XCircle size={20} /></button>
          </div>
        </div>

        <div className="modal-policy-strip">
          <span>Policy Decision</span>
          <PolicyBadge decision={decision} />
          <span className="modal-policy-version">Policy v{ticket.policy_version || "-"}</span>
        </div>

        {error && <div className="modal-error">{error}</div>}

        <div className="modal-section">
          <div className="modal-section-title">ITSM Classification</div>
          <div className="modal-grid">
            <TicketDetail label="Intent" value={ticket.intent} />
            <TicketDetail label="Category" value={ticket.category} />
            <TicketDetail label="Subcategory" value={ticket.subcategory} />
            <TicketDetail label="Impact" value={ticket.impact} />
            <TicketDetail label="Urgency" value={ticket.urgency} />
            <TicketDetail label="User" value={ticket.user} />
            <TicketDetail label="Source" value={ticket.source} />
            <TicketDetail label="Created" value={formatDate(ticket.created_at)} />
          </div>
        </div>

        <div className="modal-section">
          <div className="modal-section-title">Lifecycle Management</div>
          <div className="lifecycle-editor-grid">
            <EditableField
              label="Status"
              value={form.status}
              type="select"
              disabled={!editMode}
              options={["Open", "In Progress", "AI Resolved", "Resolved", "Escalated", "Closed"]}
              onChange={(value) => setForm((current) => ({ ...current, status: value }))}
            />
            <EditableField
              label="Priority"
              value={form.priority}
              type="select"
              disabled={!editMode}
              options={["P1", "P2", "P3", "P4"]}
              onChange={(value) => setForm((current) => ({ ...current, priority: value }))}
            />
            <EditableField
              label="Assignment Group"
              value={form.assignment_group}
              disabled={!editMode}
              onChange={(value) => setForm((current) => ({ ...current, assignment_group: value }))}
            />
          </div>
          <div className="resolution-editor">
            <label>Resolution / Work Notes</label>
            <textarea
              value={form.resolution}
              disabled={!editMode}
              onChange={(e) => setForm((current) => ({ ...current, resolution: e.target.value }))}
              placeholder="Enter the resolution, closure notes or work performed..."
              rows={4}
            />
          </div>

          {editMode && (
            <div className="lifecycle-actions">
              <button className="secondary-button" onClick={() => { setEditMode(false); setError(""); }} disabled={saving}>
                Cancel
              </button>
              <button className="primary-button" onClick={saveChanges} disabled={saving}>
                <CheckCircle2 size={15} /> {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          )}
        </div>

        <div className="modal-section">
          <div className="modal-section-title">AI & RAG</div>
          <div className="modal-grid">
            <TicketDetail label="AI Confidence" value={formatConfidence(ticket.ai_confidence)} />
            <TicketDetail label="RAG Grounded" value={ticket.ai_grounded === true ? "Yes" : ticket.ai_grounded === false ? "No" : "-"} />
            <TicketDetail label="AI Recommendation" value={ticket.ai_recommendation || "-"} />
            <TicketDetail label="AI Intent" value={ticket.intent || "-"} />
          </div>
        </div>

        <div className={`modal-policy-reason ${decisionClass}`}>
          <div className="modal-section-title">Policy Reason</div>
          <p>{ticket.policy_reason || "No policy reason recorded for this ticket."}</p>
          {ticket.policy_action && <div className="modal-action"><span>Policy Action</span><strong>{ticket.policy_action}</strong></div>}
        </div>

        <div className="modal-audit-grid">
          <TicketDetail label="Last Updated" value={formatDate(ticket.updated_at)} />
          <TicketDetail label="Resolution" value={ticket.resolution || "Not resolved yet"} />
        </div>

        <div className="modal-footer-note">
          <ShieldCheck size={15} />
          Ticket lifecycle changes are persisted through the FastAPI PATCH endpoint. Policy automation execution remains disabled.
        </div>
      </div>
    </div>
  );
}

function EditableField({ label, value, onChange, disabled, type = "text", options = [] }) {
  return (
    <label className="editable-field">
      <span>{label}</span>
      {type === "select" ? (
        <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
          {options.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} />
      )}
    </label>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function GovernanceCount({ title, value, icon: Icon, tone, onClick, active }) {
  return (
    <button className={`governance-count ${tone} ${active ? "active" : ""}`} onClick={onClick}>
      <div className="governance-count-icon"><Icon size={17} /></div>
      <div><span>{title}</span><strong>{value}</strong></div>
    </button>
  );
}

function DistributionList({ title, values, order = [] }) {
  const entries = order.length
    ? order.filter((key) => values[key]).map((key) => [key, values[key]])
    : Object.entries(values).sort((a, b) => b[1] - a[1]).slice(0, 4);

  const max = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <div className="distribution-block">
      <div className="distribution-title">{title}</div>
      {entries.length === 0 ? (
        <div className="distribution-empty">No data</div>
      ) : entries.map(([label, value]) => (
        <div className="distribution-row" key={label}>
          <div className="distribution-label"><span>{label}</span><strong>{value}</strong></div>
          <div className="distribution-track"><span style={{ width: `${(value / max) * 100}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }) {
  const normalized = String(status || "Unknown").toLowerCase().replace(/\s+/g, "-");
  const label = status || "Unknown";
  return <span className={`status-badge ${normalized}`}>{label}</span>;
}

function AIAnalysis() {
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/policy/status")
      .then((r) => setPolicy(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-content">
      <div className="page-title-row">
        <div>
          <div className="section-kicker">INTELLIGENCE</div>
          <h2>AI Analysis</h2>
          <p>RAG retrieval, Qwen classification and Policy Engine governance.</p>
        </div>
        <div className="confidence-badge"><Sparkles size={16} /> Governed AI Pipeline</div>
      </div>

      <div className="analysis-layout">
        <section className="analysis-main">
          <div className="analysis-card">
            <div className="analysis-card-header">
              <div>
                <span className="analysis-label">CURRENT MILESTONE</span>
                <h3>AI + Policy Ticket Workflow</h3>
              </div>
            </div>

            <div className="resolution-box">
              <CheckCircle2 size={21} />
              <div>
                <strong>RAG + Qwen + Policy Engine is active</strong>
                <p>
                  AegisDesk retrieves approved knowledge, classifies the request
                  and stores the resulting governance decision with the ticket.
                </p>
              </div>
            </div>
          </div>

          <div className="analysis-card">
            <div className="analysis-card-header">
              <div>
                <span className="analysis-label">PIPELINE</span>
                <h3>How AegisDesk makes a governed decision</h3>
              </div>
            </div>

            <div className="classification-grid">
              <AnalysisField label="Embedding Model" value="MiniLM-L6-v2" />
              <AnalysisField label="Vector Store" value="FAISS" />
              <AnalysisField label="LLM" value="Qwen 2.5 0.5B" />
              <AnalysisField label="Grounding" value="RAG Context" />
              <AnalysisField label="Classification" value="ITSM Fields" />
              <AnalysisField label="Policy Version" value={policy?.policy_version || "1.1"} />
              <AnalysisField label="Automation" value={policy?.automation_enabled ? "Enabled" : "Disabled"} />
              <AnalysisField label="Execution" value={policy?.execution_enabled ? "Enabled" : "Disabled"} />
            </div>
          </div>
        </section>

        <aside className="analysis-sidebar">
          <div className="analysis-side-card">
            <div className="side-card-title"><ShieldCheck size={18} /> Policy Engine</div>
            <PolicyStatusRow label="Status" value={loading ? "Loading..." : policy?.status || "Ready"} />
            <PolicyStatusRow label="Version" value={policy?.policy_version || "1.1"} />
            <PolicyStatusRow label="Min AI Confidence" value={policy ? policy.minimum_ai_confidence : "0.80"} />
            <PolicyStatusRow label="Min Grounding" value={policy ? policy.minimum_grounding_similarity : "0.30"} />
            <PolicyStatusRow label="P1 Review" value={policy?.human_review_for_p1 ? "Required" : "No"} />
            <PolicyStatusRow label="Enterprise P2 Review" value={policy?.human_review_for_enterprise_p2 ? "Required" : "No"} />
          </div>

          <div className="analysis-side-card">
            <div className="side-card-title"><Wrench size={18} /> Approved Actions</div>
            {(policy?.allowed_actions || []).map((action) => (
              <div className="knowledge-source" key={action.id}>
                <div className="source-icon"><CheckCircle2 size={16} /></div>
                <div>
                  <strong>{action.label}</strong>
                  <span>{action.risk} risk · execution disabled</span>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

function KnowledgeBase() {
  const [search, setSearch] = useState("");
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ragStatus, setRagStatus] = useState(null);
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/api/knowledge"),
      api.get("/api/rag/status"),
    ])
      .then(([a, b]) => {
        setArticles(a.data.articles || []);
        setRagStatus(b.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const runSearch = async () => {
    if (!search.trim()) {
      setResults([]);
      return;
    }

    setSearching(true);

    try {
      const r = await api.get("/api/rag/search", {
        params: { q: search, top_k: 5 },
      });
      setResults(r.data.results || []);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="page-content">
      <div className="page-title-row">
        <div>
          <div className="section-kicker">RAG KNOWLEDGE</div>
          <h2>Knowledge Base</h2>
          <p>Approved enterprise knowledge indexed for semantic retrieval.</p>
        </div>
        <div className="knowledge-count">
          <BookOpen size={17} /> {loading ? "..." : `${articles.length} Articles`}
        </div>
      </div>

      <div className="knowledge-engine-banner">
        <div>
          <strong>RAG Engine</strong>
          <span>
            {ragStatus?.status === "ready"
              ? `Ready · ${ragStatus.chunks} chunks · ${ragStatus.vector_dimension} dimensions`
              : "Ready to build on first search"}
          </span>
        </div>
        <button onClick={runSearch} disabled={searching}>
          {searching ? "Searching..." : "Semantic Search"}
        </button>
      </div>

      <div className="knowledge-search">
        <Search size={20} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
          placeholder="Search: VPN not connecting, password expired, Outlook sync..."
        />
        <button onClick={runSearch}><Search size={16} /></button>
      </div>

      {results.length > 0 && (
        <section className="rag-results-card knowledge-results">
          <div className="rag-result-header">
            <strong>Semantic Retrieval Results</strong>
            <span>{results.length} matches</span>
          </div>
          {results.map((source) => (
            <div className="rag-result" key={source.chunk_id}>
              <div className="source-icon"><FileText size={15} /></div>
              <div>
                <strong>{source.title}</strong>
                <span>{source.category} · similarity {Math.round(source.similarity * 100)}%</span>
                <p>{source.text}</p>
              </div>
            </div>
          ))}
        </section>
      )}

      <div className="knowledge-grid">
        {articles.map((article) => (
          <article className="knowledge-card" key={article.article_id}>
            <div className="knowledge-card-top">
              <div className="knowledge-icon"><FileText size={20} /></div>
              <span className="category-badge">{article.category}</span>
            </div>
            <h3>{article.title}</h3>
            <p>Approved source: {article.source}</p>
            <div className="knowledge-card-footer">
              <span>{article.article_id}</span>
              <span>Indexed for RAG</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadUsers = () => {
    setLoading(true);
    api.get("/api/auth/users")
      .then((response) => setUsers(response.data.users || []))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load users."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadUsers(); }, []);

  const changeRole = async (username, role) => {
    try {
      await api.patch(`/api/auth/users/${username}/role`, { role });
      loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to update role.");
    }
  };

  return (
    <div className="page-content">
      <div className="page-title-row">
        <div><div className="section-kicker">ADMINISTRATION</div><h2>User Management</h2><p>Manage AegisDesk roles using the RBAC policy.</p></div>
        <div className="knowledge-count"><Users size={17} /> {users.length} Users</div>
      </div>
      <section className="admin-rbac-banner">
        <ShieldCheck size={22} />
        <div><strong>Role-Based Access Control</strong><span>Employee · Agent · Admin</span></div>
      </section>
      {error && <div className="auth-error"><AlertCircle size={16} />{error}</div>}
      <section className="admin-users-card">
        {loading ? <div className="activity-empty">Loading users...</div> : users.map((user) => (
          <div className="admin-user-row" key={user.username}>
            <div className="user-avatar">{String(user.display_name || user.username).slice(0, 2).toUpperCase()}</div>
            <div className="admin-user-info"><strong>{user.display_name}</strong><span>{user.username} · {user.email}</span></div>
            <select value={user.role} onChange={(e) => changeRole(user.username, e.target.value)}>
              <option value="employee">Employee</option><option value="agent">Agent</option><option value="admin">Admin</option>
            </select>
            <span className={`role-badge ${user.role}`}>{user.role}</span>
          </div>
        ))}
      </section>
    </div>
  );
}

function ConnectionCard({ label, value, good }) {
  return (
    <div>
      <span className="connection-label">{label}</span>
      <strong className={good ? "connection-good" : "connection-pending"}>{value}</strong>
    </div>
  );
}

function StatCard({ icon: Icon, value, label, trend }) {
  return (
    <div className="stat-card">
      <div className="stat-icon"><Icon size={20} /></div>
      <div className="stat-content">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{trend}</small>
      </div>
    </div>
  );
}

function DashboardMetric({ title, value, icon: Icon }) {
  return (
    <div className="dashboard-metric">
      <div className="metric-icon"><Icon size={20} /></div>
      <div><span>{title}</span><strong>{value}</strong></div>
    </div>
  );
}

function InfoItem({ title, description }) {
  return (
    <div className="info-item">
      <CheckCircle2 size={17} />
      <div><strong>{title}</strong><p>{description}</p></div>
    </div>
  );
}

function AnalysisField({ label, value }) {
  return (
    <div className="analysis-field">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PolicyStatusRow({ label, value }) {
  return (
    <div className="policy-status-row">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  );
}

function KnowledgeSource({ title, score }) {
  return (
    <div className="knowledge-source">
      <div className="source-icon"><FileText size={16} /></div>
      <div><strong>{title}</strong><span>{score}</span></div>
      <CheckCircle2 size={16} />
    </div>
  );
}

function GovernanceItem({ title, description }) {
  return (
    <div className="governance-item">
      <div className={`governance-icon ${title.toLowerCase().replace(" ", "-")}`}>
        {title === "Approved" ? <CheckCircle2 size={16} /> : title === "Blocked" ? <XCircle size={16} /> : <AlertCircle size={16} />}
      </div>
      <div>
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
    </div>
  );
}

function AutomationItem({ title, status }) {
  return (
    <div className="automation-item">
      <div className="automation-item-icon"><Wrench size={16} /></div>
      <span>{title}</span>
      <small><span className="status-dot" />{status}</small>
    </div>
  );
}

function PriorityBadge({ priority }) {
  return <span className={`priority-badge ${String(priority).toLowerCase()}`}>{priority}</span>;
}

function PolicyBadge({ decision }) {
  if (!decision) return <span className="policy-badge neutral">-</span>;

  const cls =
    decision === "APPROVED"
      ? "approved"
      : decision === "BLOCKED"
        ? "blocked"
        : "human-review";

  return <span className={`policy-badge ${cls}`}>{decision}</span>;
}

export default App;
