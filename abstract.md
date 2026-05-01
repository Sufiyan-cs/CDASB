<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

:root {
    --primary: #6366f1;
    --secondary: #ec4899;
    --dark: #0f172a;
    --light: #f8fafc;
    --accent: #10b981;
    --warning: #f59e0b;
}

body {
    font-family: 'Outfit', sans-serif;
    line-height: 1.6;
    color: var(--dark);
    max-width: 850px;
    margin: 0 auto;
    padding: 60px;
    background: #fff;
}

h1, h2, h3 {
    color: var(--dark);
    border-bottom: none;
    margin-top: 2rem;
}

h1 {
    font-size: 3rem;
    font-weight: 700;
    text-align: center;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}

.subtitle {
    text-align: center;
    font-size: 1.3rem;
    color: #64748b;
    margin-bottom: 3.5rem;
    font-weight: 300;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.5rem;
    color: var(--primary);
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 8px;
    margin-bottom: 1.5rem;
}

.content-box {
    background: #f8fafc;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 2rem;
    border: 1px solid #e2e8f0;
}

.tech-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
    margin-top: 1rem;
}

.tech-item {
    display: flex;
    justify-content: space-between;
    padding: 10px 15px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.tech-label {
    font-weight: 600;
    color: #475569;
}

.tech-value {
    color: var(--primary);
    font-weight: 700;
}

.problem-box {
    border-left: 5px solid var(--warning);
    background: #fffbeb;
}

.solution-box {
    border-left: 5px solid var(--accent);
    background: #f0fdf4;
}

.footer {
    margin-top: 4rem;
    text-align: center;
    font-size: 0.9rem;
    color: #94a3b8;
    border-top: 1px solid #f1f5f9;
    padding-top: 2rem;
}

strong {
    color: var(--dark);
}

ul {
    padding-left: 1.5rem;
}

li {
    margin-bottom: 0.5rem;
}
</style>

# CDASB: Interactive Version
<div class="subtitle">Conflict-Driven Autonomous System Builder</div>

<div class="section-title">🚀 Abstract</div>
<div class="content-box">
    The **Conflict-Driven Autonomous System Builder (CDASB)** is an advanced AI engineering platform designed to automate the end-to-end lifecycle of software development. By moving beyond simple code generation, CDASB implements a "Multi-Agent Dissent" architecture. It ingests complex requirements via natural language or documents (PDF/DOCX), plans architectural solutions, and iteratively builds, tests, and refines them through continuous internal debate. This system ensures that every line of code is challenged and optimized before delivery, providing a robust, human-validated final product.
</div>

<div class="section-title">⚠️ The Real-World Problem</div>
<div class="content-box problem-box">
    Most current AI-powered coding tools operate on a "Single-Output" basis, which leads to:
    <ul>
        <li><strong>Quality Gaps:</strong> AI often generates "hallucinated" or inefficient code that looks correct but fails in production.</li>
        <li><strong>Lack of Nuance:</strong> Standard prompts struggle to capture deep architectural constraints hidden in large PDF documents.</li>
        <li><strong>No Self-Correction:</strong> Autonomous systems often proceed with errors without a built-in mechanism for "second thoughts" or critical review.</li>
    </ul>
</div>

<div class="section-title">✅ The Solution</div>
<div class="content-box solution-box">
    CDASB solves these issues by embedding **Conflict** as a core operation:
    <ul>
        <li><strong>Structured Debate:</strong> Specialized agents (Critic/Optimizer) specifically look for flaws in the Planner's output.</li>
        <li><strong>Document Intelligence:</strong> Advanced extraction layers parse PDFs and DOCX files to find hidden requirements.</li>
        <li><strong>Human-in-the-Loop:</strong> The system presents a transparent reasoning chain and implementation plan for user approval before any code is executed.</li>
        <li><strong>Iterative Refinement:</strong> A continuous loop of <em>Code → Conflict → Test → Conflict → Improve</em> ensures maximum stability.</li>
    </ul>
</div>

<div class="section-title">🛠️ Technical Architecture</div>
<div class="tech-grid">
    <div class="tech-item">
        <span class="tech-label">Backend Language</span>
        <span class="tech-value">Python 3.12+</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">Backend Framework</span>
        <span class="tech-value">FastAPI</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">Frontend Stack</span>
        <span class="tech-value">React / Next.js 15</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">Styling</span>
        <span class="tech-value">Tailwind CSS</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">Database</span>
        <span class="tech-value">PostgreSQL</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">AI Logic</span>
        <span class="tech-value">NVIDIA AI (DeepSeek/Qwen)</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">Vector Store</span>
        <span class="tech-label" style="color:var(--primary)">ChromaDB / Pinecone</span>
    </div>
    <div class="tech-item">
        <span class="tech-label">Virtualization</span>
        <span class="tech-value">Docker Sandbox</span>
    </div>
</div>

<div class="section-title">🌐 Languages & Technologies</div>
<div class="content-box">
    <strong>Languages:</strong> Python, TypeScript, JavaScript, SQL, HTML, CSS.
    <br><br>
    <strong>Key Technologies:</strong> 
    LlamaIndex (for RAG), LangGraph (Agentic flows), Pydantic (validation), Shadcn/UI (Modern components), PyPDF2/Docx2txt (Extraction).
</div>

<div class="footer">
    CDASB Project Documentation • 2026 • Autonomous Engineering Team
</div>
