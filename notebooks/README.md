# HR Interview Orchestrator Demo Notebook 📋

This standalone Jupyter notebook demonstrates the key features of the HR Interview Orchestrator system without requiring the full application setup.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd notebooks
pip install -r requirements.txt
```

### 2. Launch Jupyter

```bash
jupyter notebook demo.ipynb
```

### 3. Run All Cells

The notebook is designed to run completely standalone with sample data.

## 📊 What the Demo Shows

### ✅ Features Demonstrated

1. **📄 Job Description Analysis**

   - Parse structured data from raw JD text
   - Extract title, location, requirements, preferences
   - Quality validation with scoring

2. **👥 Candidate Resume Analysis**

   - Parse candidate resumes with skill extraction
   - Score candidates against job requirements
   - Multi-factor scoring algorithm

3. **🏆 Candidate Ranking**

   - Rank candidates by match percentage
   - Detailed skill overlap analysis
   - Comparison tables with pandas

4. **❓ Interview Question Generation**

   - Generate relevant interview questions
   - Categorize by technical/behavioral
   - Fallback questions when question bank unavailable

5. **📊 Complete Pipeline Summary**

   - End-to-end hiring process metrics
   - Recommendations and next steps
   - Process optimization insights

6. **🔧 MCP Tool Integration**
   - Demonstrate internal MCP tool functionality
   - Show tool schema for external integrations
   - Export capabilities

### 🎯 Sample Data

The notebook includes realistic sample data:

- **Job Description**: Senior Full Stack Developer position
- **Candidates**: 3 candidates with varying skill levels
- **Questions**: Fallback interview questions for demonstration

### 📈 Expected Output

Running the notebook will show:

- Job quality score: ~85-100/100
- 3 candidates ranked by match percentage
- Top candidate: Usually Carol Davis (~70-80% match)
- 8 interview questions (technical + behavioral)
- Complete hiring pipeline summary

## 🔧 Customization

### Add Your Own Data

Replace the sample data in the notebook cells:

```python
# Replace sample_jd with your job description
sample_jd = """
Your actual job description here...
"""

# Replace candidates_data with your candidate resumes
candidates_data = [
    {
        "name": "Your Candidate",
        "resume": "Candidate resume text..."
    }
]
```

### Modify Scoring

Adjust the scoring weights in the imported `_score_candidate` function:

- Must-have skills: 70% weight
- Nice-to-have skills: 20% weight
- Experience bonus: 10% weight

### Question Bank

To use the real question bank:

1. Ensure `../data/question_bank.csv` exists
2. The notebook will automatically use it instead of fallback questions

## 🔗 Integration with Main System

This notebook uses the same core components as the full HR Interview Orchestrator:

- `src.tools.mcp_tool` - Internal MCP tool for JD parsing
- `src.tools.parser` - Resume and document parsing
- `src.agents._score_candidate` - Candidate scoring algorithm
- `src.state.JD`, `src.state.Candidate` - Data models

You can extend the notebook to:

- Connect to the full question bank
- Use LangSmith tracing
- Generate actual calendar invites
- Create Gmail drafts
- Export to various formats

## 📋 Requirements

- Python 3.8+
- Jupyter Notebook
- All dependencies in `requirements.txt`
- Access to parent directory (`../src/`) for imports

## 🎉 Standalone Features

The notebook is designed to work without:

- OpenAI API key (uses offline parsing)
- Question bank file (has fallback questions)
- Google integration (demonstration only)
- LangSmith setup (optional tracing)

Perfect for:

- **Demos**: Show HR teams the system capabilities
- **Development**: Test and iterate on algorithms
- **Education**: Learn how the system works
- **Prototyping**: Experiment with new features

---

**🎯 Ready to demonstrate AI-powered hiring!**
