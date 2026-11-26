import os, json, sqlite3, re
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g
import requests

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-this-for-production")
DB_PATH = os.path.join(os.path.dirname(__file__), "dreams.db")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            idea TEXT NOT NULL,
            category TEXT,
            budget TEXT,
            audience TEXT,
            blueprint TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")

def demo_blueprint(data):
    idea = data["idea"]
    title = (idea.strip().split(".")[0][:55] or "My Big Idea")
    budget = data.get("budget") or "Not specified"
    category = data.get("category") or "General"
    audience = data.get("audience") or "To be researched"
    return {
        "project_title": title,
        "executive_summary": f"This concept turns the idea “{idea[:240]}” into a practical first-stage venture. Start small, validate demand with real users, and expand only when evidence supports it. This is a demonstration blueprint; validate all assumptions before investing.",
        "problem": "Potential customers may be facing an unmet need, an inconvenient process, high costs, or a lack of accessible alternatives. Interview prospective users to confirm the exact pain point.",
        "solution": "Build a focused first version that solves one high-value problem exceptionally well. Test it with a small group, collect feedback, and improve the experience before scaling.",
        "business_model": ["Freemium or starter offering to reduce adoption friction", "Paid premium features or service packages", "Partnerships with relevant institutions or local businesses"],
        "budget_breakdown": [
            {"item":"Prototype / product development","amount":"30%","note":"Build only the essential first version."},
            {"item":"Marketing and user testing","amount":"20%","note":"Run small experiments and gather feedback."},
            {"item":"Operations and tools","amount":"20%","note":"Hosting, software and basic operations."},
            {"item":"Customer support / delivery","amount":"15%","note":"Onboarding and service delivery."},
            {"item":"Contingency reserve","amount":"15%","note":"Keep a buffer for unexpected costs."}
        ],
        "target_customers": [audience, "Early adopters who experience the problem regularly", "People reachable through focused online communities"],
        "marketing_strategy": ["Interview 10–15 potential users before launch.", "Create a simple landing page explaining the value proposition.", "Publish useful short-form content where the target audience already spends time.", "Ask early users for testimonials and referrals."],
        "action_plan": [
            {"week":"Week 1","tasks":["Interview potential users","Define the single most important problem","Research alternatives and competitors"]},
            {"week":"Week 2","tasks":["Sketch the user journey","Build a basic prototype","Prepare a simple landing page"]},
            {"week":"Week 3","tasks":["Test with 5–10 target users","Record friction points","Improve the core experience"]},
            {"week":"Week 4","tasks":["Run a small pilot","Measure sign-ups and engagement","Decide whether to iterate, launch or rethink"]}
        ],
        "risks": [
            {"risk":"Demand may be weaker than expected","mitigation":"Validate with interviews, waitlists and a small pilot before spending heavily."},
            {"risk":"Costs may exceed the available budget","mitigation":"Prioritize a minimum viable product and track every expense."},
            {"risk":"Competitors may offer similar solutions","mitigation":"Focus on a specific audience and a clear differentiator."}
        ],
        "success_metrics": ["Number of user interviews completed", "Pilot sign-ups and activation rate", "Repeat usage or repeat purchases", "Customer feedback and willingness to pay"],
        "assumptions": [f"Indicative budget provided: {budget}", f"Category selected: {category}", "Market size, costs, legal requirements and competitor details have not been independently verified."],
        "disclaimer": "Demo mode is active. Add a Gemini API key to generate a tailored plan with a real generative AI model. This plan is an idea-development aid, not financial, legal or investment advice."
    }

def call_gemini(data):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        result = demo_blueprint(data)
        result["disclaimer"] = "Demo mode is active because GEMINI_API_KEY is not configured. Add your key to enable real Gemini-generated plans."
        return result, True

    prompt = f"""
You are Dream-to-Reality AI, a practical startup and project planning assistant.
Create a realistic, useful first-draft blueprint. Do not invent verified market statistics,
competitor facts, legal requirements, or guaranteed financial outcomes. Label estimates
and assumptions clearly. Keep recommendations actionable and suitable for a student founder.
Return ONLY valid JSON with exactly these keys:
project_title (string), executive_summary (string), problem (string), solution (string),
business_model (array of strings), budget_breakdown (array of objects with item, amount, note),
target_customers (array of strings), marketing_strategy (array of strings),
action_plan (array of objects with week, tasks array), risks (array of objects with risk, mitigation),
success_metrics (array of strings), assumptions (array of strings), disclaimer (string).
User idea: {data['idea']}
Category: {data.get('category') or 'Not specified'}
Available budget: {data.get('budget') or 'Not specified'}
Target audience: {data.get('audience') or 'Not specified'}
Currency/context: INR / India unless user says otherwise.
Make budget amounts add up to 100% if using percentages. Do not promise success.
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    response = requests.post(
        url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents":[{"parts":[{"text":prompt}]}],
              "generationConfig":{"temperature":0.7,"responseMimeType":"application/json"}},
        timeout=90
    )
    if not response.ok:
        raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text[:500]}")
    payload = response.json()
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    # Be tolerant if a model wraps JSON in markdown fences.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    result = json.loads(text)
    return result, False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    idea = (data.get("idea") or "").strip()
    if len(idea) < 12:
        return jsonify(error="Please describe your idea in at least 12 characters."), 400
    if len(idea) > 4000:
        return jsonify(error="Please keep your idea under 4,000 characters."), 400
    try:
        blueprint, demo = call_gemini(data | {"idea": idea})
        title = str(blueprint.get("project_title") or "My Dream Project")[:100]
        db = get_db()
        cur = db.execute(
            "INSERT INTO projects(title,idea,category,budget,audience,blueprint,created_at) VALUES(?,?,?,?,?,?,?)",
            (title, idea, data.get("category",""), data.get("budget",""), data.get("audience",""),
             json.dumps(blueprint, ensure_ascii=False), datetime.now().isoformat(timespec="seconds"))
        )
        db.commit()
        return jsonify(id=cur.lastrowid, blueprint=blueprint, demo=demo)
    except requests.RequestException as e:
        return jsonify(error=f"Could not reach Gemini. Check your internet connection and API key. Details: {e}"), 502
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route("/api/projects")
def projects():
    rows = get_db().execute("SELECT id,title,category,created_at FROM projects ORDER BY id DESC LIMIT 30").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/projects/<int:project_id>")
def project_detail(project_id):
    row = get_db().execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        return jsonify(error="Project not found"), 404
    item = dict(row)
    item["blueprint"] = json.loads(item["blueprint"])
    return jsonify(item)

@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    db = get_db()
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    db.commit()
    return jsonify(ok=True)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
