// Deprecated file: manual job templates removed
export const jobTemplates = {
  Backend: {
    title: "Backend",
    requirements: [
      { id: "programming_language", label: "Programlama Dili", keywords: ["Java", "C#", "Go", "Node.js", "Python"] },
      { id: "frameworks", label: "Çatılar", keywords: ["Spring", ".NET", "Django", "Express", "NestJS"] },
      { id: "databases", label: "Veritabanları", keywords: ["PostgreSQL", "MySQL", "MongoDB", "Redis"] },
      { id: "cloud", label: "Bulut & Konteyner", keywords: ["AWS", "Azure", "GCP", "Docker", "Kubernetes"] },
      { id: "testing", label: "Test & CI/CD", keywords: ["Unit", "Integration", "CI", "CD", "TDD"] },
    ],
    dialog: { max_questions: 8, language: "tr" },
    rubric_weights: { communication: 0.1, technical: 0.5, problem_solving: 0.25, cultural_fit: 0.1, alignment: 0.05 },
  },
  Frontend: {
    title: "Frontend",
    requirements: [
      { id: "javascript", label: "JavaScript/TypeScript", keywords: ["JS", "TS", "ES6", "TypeScript"] },
      { id: "react", label: "React Ekosistemi", keywords: ["React", "Next.js", "Redux", "Zustand"] },
      { id: "css", label: "Stil & UI", keywords: ["CSS", "Tailwind", "Sass", "Styled Components"] },
      { id: "testing", label: "Test Araçları", keywords: ["Jest", "RTL", "Cypress", "Playwright"] },
      { id: "build_tools", label: "Build Araçları", keywords: ["Webpack", "Vite", "Babel", "SWC"] },
    ],
    dialog: { max_questions: 7, language: "tr" },
    rubric_weights: { communication: 0.2, technical: 0.4, problem_solving: 0.2, cultural_fit: 0.1, alignment: 0.1 },
  },
  DevOps: {
    title: "DevOps",
    requirements: [
      { id: "cloud", label: "Bulut", keywords: ["AWS", "Azure", "GCP", "IAM", "VPC"] },
      { id: "iac", label: "IaC", keywords: ["Terraform", "Pulumi", "CloudFormation"] },
      { id: "containers", label: "Konteyner", keywords: ["Docker", "Kubernetes", "Helm"] },
      { id: "ci_cd", label: "CI/CD", keywords: ["GitHub Actions", "GitLab CI", "Jenkins", "ArgoCD"] },
      { id: "monitoring", label: "Gözlemlenebilirlik", keywords: ["Prometheus", "Grafana", "ELK", "OpenTelemetry"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.15, technical: 0.45, problem_solving: 0.25, cultural_fit: 0.1, alignment: 0.05 },
  },
  "Data/ML": {
    title: "Data/ML",
    requirements: [
      { id: "languages", label: "Diller", keywords: ["Python", "SQL", "R"] },
      { id: "frameworks", label: "ML Framework", keywords: ["Pandas", "NumPy", "scikit-learn", "TensorFlow", "PyTorch"] },
      { id: "data_eng", label: "Veri Müh.", keywords: ["Spark", "Airflow", "dbt", "ETL", "Kafka"] },
      { id: "ml", label: "ML Teknikleri", keywords: ["Regression", "Classification", "NLP", "CV"] },
      { id: "math", label: "İstatistik/Matematik", keywords: ["Statistics", "Linear Algebra", "Probability"] },
    ],
    dialog: { max_questions: 8, language: "tr" },
    rubric_weights: { communication: 0.1, technical: 0.45, problem_solving: 0.25, cultural_fit: 0.1, alignment: 0.1 },
  },
  QA: {
    title: "QA",
    requirements: [
      { id: "automation", label: "Test Otomasyon", keywords: ["Selenium", "Cypress", "Playwright"] },
      { id: "manual", label: "Manuel Test", keywords: ["Exploratory", "Regression", "Test Cases"] },
      { id: "api_testing", label: "API Test", keywords: ["Postman", "REST", "GraphQL"] },
      { id: "tools", label: "Araçlar", keywords: ["Jira", "TestRail", "Zephyr"] },
      { id: "bug_tracking", label: "Hata Yönetimi", keywords: ["Bug Tracking", "Root Cause", "Defect Lifecycle"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.2, technical: 0.35, problem_solving: 0.25, cultural_fit: 0.1, alignment: 0.1 },
  },
  Mobile: {
    title: "Mobile",
    requirements: [
      { id: "platform", label: "Platform", keywords: ["iOS", "Android"] },
      { id: "language", label: "Dil", keywords: ["Swift", "Kotlin", "Java", "Objective-C"] },
      { id: "framework", label: "Çatılar", keywords: ["React Native", "Flutter", "SwiftUI", "Jetpack Compose"] },
      { id: "store", label: "Store Süreçleri", keywords: ["App Store", "Play Store", "Review"] },
      { id: "testing", label: "Test", keywords: ["Unit", "UI Test", "Snapshot"] },
    ],
    dialog: { max_questions: 7, language: "tr" },
    rubric_weights: { communication: 0.2, technical: 0.4, problem_solving: 0.2, cultural_fit: 0.1, alignment: 0.1 },
  },
  PM: {
    title: "PM",
    requirements: [
      { id: "methodologies", label: "Yöntemler", keywords: ["Agile", "Scrum", "Kanban"] },
      { id: "tools", label: "Araçlar", keywords: ["Jira", "Asana", "Notion", "Linear"] },
      { id: "stakeholder", label: "Paydaş Yönetimi", keywords: ["Stakeholder", "Alignment", "Facilitation"] },
      { id: "roadmap", label: "Yol Haritası", keywords: ["Roadmap", "Prioritization", "Backlog"] },
      { id: "analytics", label: "Analitik", keywords: ["A/B", "Mixpanel", "Amplitude", "GA"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.35, technical: 0.15, problem_solving: 0.2, cultural_fit: 0.1, alignment: 0.2 },
  },
  HR: {
    title: "HR",
    requirements: [
      { id: "talent_acquisition", label: "Yetenek Kazanımı", keywords: ["Sourcing", "Interview", "ATS"] },
      { id: "labor_law", label: "İş Hukuku", keywords: ["Compliance", "Policies", "Payroll"] },
      { id: "performance", label: "Performans", keywords: ["OKR", "KPI", "Feedback"] },
      { id: "employee_relations", label: "Çalışan İlişkileri", keywords: ["Engagement", "Culture", "L&D"] },
      { id: "analytics", label: "HR Analitiği", keywords: ["People Analytics", "Survey", "Retention"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.4, technical: 0.05, problem_solving: 0.1, cultural_fit: 0.25, alignment: 0.2 },
  },
  Sales: {
    title: "Sales",
    requirements: [
      { id: "industry", label: "Sektör Bilgisi", keywords: ["SaaS", "B2B", "Enterprise", "SMB"] },
      { id: "crm", label: "CRM", keywords: ["Salesforce", "HubSpot", "Pipedrive"] },
      { id: "quota", label: "Kota & Pipeline", keywords: ["Quota", "Forecast", "Pipeline"] },
      { id: "negotiation", label: "Müzakere", keywords: ["Negotiation", "Closing", "Objection Handling"] },
      { id: "outreach", label: "Outreach", keywords: ["Email", "Cold Call", "Sequences"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.45, technical: 0.1, problem_solving: 0.1, cultural_fit: 0.15, alignment: 0.2 },
  },
  "Customer Success/Support": {
    title: "Customer Success/Support",
    requirements: [
      { id: "support_tools", label: "Destek Araçları", keywords: ["Zendesk", "Intercom", "Freshdesk"] },
      { id: "sla", label: "SLA & Süreç", keywords: ["SLA", "Escalation", "Ticketing"] },
      { id: "product_knowledge", label: "Ürün Bilgisi", keywords: ["Product", "Use Cases", "Troubleshooting"] },
      { id: "communication", label: "İletişim", keywords: ["Empathy", "Active Listening", "De-escalation"] },
      { id: "analytics", label: "Analitik", keywords: ["NPS", "CSAT", "Churn"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.45, technical: 0.05, problem_solving: 0.1, cultural_fit: 0.2, alignment: 0.2 },
  },
  Marketing: {
    title: "Marketing",
    requirements: [
      { id: "channels", label: "Kanallar", keywords: ["Paid", "Organic", "Social", "Email"] },
      { id: "content", label: "İçerik", keywords: ["Copywriting", "Storytelling", "Brand"] },
      { id: "analytics", label: "Analitik", keywords: ["GA", "Attribution", "CRO"] },
      { id: "seo_sem", label: "SEO/SEM", keywords: ["SEO", "SEM", "Keywords"] },
      { id: "tools", label: "Araçlar", keywords: ["HubSpot", "Marketo", "Hootsuite"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.35, technical: 0.1, problem_solving: 0.15, cultural_fit: 0.15, alignment: 0.25 },
  },
  Finance: {
    title: "Finance",
    requirements: [
      { id: "accounting", label: "Muhasebe", keywords: ["IFRS", "US GAAP", "Balance Sheet"] },
      { id: "analysis", label: "Finansal Analiz", keywords: ["FP&A", "Modeling", "Valuation"] },
      { id: "reporting", label: "Raporlama", keywords: ["Budget", "Forecast", "Variance"] },
      { id: "erp", label: "ERP", keywords: ["SAP", "Oracle", "Netsuite"] },
      { id: "compliance", label: "Uyum", keywords: ["Audit", "SOX", "Tax"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.2, technical: 0.25, problem_solving: 0.3, cultural_fit: 0.1, alignment: 0.15 },
  },
  Ops: {
    title: "Ops",
    requirements: [
      { id: "process", label: "Süreç İyileştirme", keywords: ["Lean", "Six Sigma", "Kaizen"] },
      { id: "tools", label: "Araçlar", keywords: ["Excel", "Sheets", "BI", "SQL"] },
      { id: "vendor", label: "Tedarikçi Yönetimi", keywords: ["Vendor", "Procurement", "SLAs"] },
      { id: "scheduling", label: "Planlama", keywords: ["Scheduling", "Capacity", "Forecasting"] },
      { id: "kpi", label: "KPI & Raporlama", keywords: ["KPI", "OKR", "Dashboard"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.25, technical: 0.15, problem_solving: 0.3, cultural_fit: 0.1, alignment: 0.2 },
  },
  Designer: {
    title: "Designer",
    requirements: [
      { id: "tools", label: "Tasarım Araçları", keywords: ["Figma", "Sketch", "Adobe XD"] },
      { id: "ux_process", label: "UX Süreci", keywords: ["Wireframe", "Prototype", "User Journey"] },
      { id: "research", label: "Araştırma", keywords: ["User Research", "Usability", "Interviews"] },
      { id: "portfolio", label: "Portfolyo", keywords: ["Case Study", "Visual", "Typography"] },
      { id: "collaboration", label: "İş Birliği", keywords: ["Design Systems", "Handoff", "Figma Tokens"] },
    ],
    dialog: { max_questions: 6, language: "tr" },
    rubric_weights: { communication: 0.3, technical: 0.2, problem_solving: 0.1, cultural_fit: 0.2, alignment: 0.2 },
  },
} as const;
export type JobTemplateKey = keyof typeof jobTemplates;


