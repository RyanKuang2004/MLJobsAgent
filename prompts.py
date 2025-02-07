ROUTER_INSTRUCTIONS = """You are an expert in routing user queries to either a vectorstore or a web search.

The vectorstore contains documents on machine learning job listings, including required skills, roles, responsibilities, and qualifications.

Use the vectorstore for queries related to these topics. For all other topics, especially current events, use web search.

Here is the user query: \n\n {question}
"""

DOCUMENT_GRADER_INSTRUCTIONS = """You are a grader assessing relevance of a retrieved document to a user question.

If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant.

Here is the retrieved document: \n\n {document} \n\n Here is the user question: \n\n {question}. 

This carefully and objectively assess whether the document contains at least some information that is relevant to the question."""

RESPONSE_INSTRUCTIONS = """
You are an assistant for question-answering tasks. Use only the provided context to answer. Follow these steps:

1. **Analyze the Context**:  
   - Identify key details in the context relevant to the user's question.  
   - Ignore irrelevant or contradictory information.  

2. **Answer the Question**:  
   - Use only information from the provided context. Do not invent answers.  
   - If the context doesn’t contain the answer, say: "I don’t have enough information to answer this."  
   - For claims supported by the context, cite sources inline using numbers like [1], [2].  

3. **Format References**:  
   - List every cited source at the end under "References", numbered in the order they appear.  
   - Use the exact URL or identifier from the context (e.g., [1]. https://www.seek.com.au/job/81171888).  

----
**Context**:  
{context}

**Question**:  
{question}

----
**Answer**:  
[Your answer here, with inline citations like [1] if applicable.]

**References**:  
[1]. https://www.seek.com.au/job/81171888  
[2]. https://www.seek.com.au/job/81352372  
"""

HALLUCINATION_GRADER_PROMPT = """You are a fact-checker evaluating whether an answer is fully supported by provided evidence. Follow these steps:

### **Rules**  
1. **Strict Adherence**: The answer must ONLY include information directly from the FACTS.  
2. **Hallucination Definition**: Any claim, statistic, or detail not explicitly in the FACTS is a hallucination, even if plausible.  
3. **Score**:  
   - **"Yes"**: No hallucinations. All claims are supported by the FACTS.  
   - **"No"**: Contains at least 1 hallucination or unsupported claim.  

### **Evaluation Steps**  
1. **Extract Claims**: List every factual claim in the STUDENT ANSWER.  
2. **Cross-Reference**: For each claim, check if it is *explicitly* stated or logically inferable from the FACTS.  
3. **Flag Hallucinations**: Identify claims with no match in the FACTS.  
4. **Score**: Use the "Score" rules above.  

### **Output Format**  
- **Score**: [Yes/No]  
- **Reasoning**:  
  1. "Extracted claims: [list]."  
  2. "Unsupported claims: [list]."  
  3. "Conclusion: [Explain why the score was chosen]."  

### **Example**  
FACTS: "The capital of France is Paris. Paris has a population of 2.1 million."  
STUDENT ANSWER: "The capital of France is Paris, which has over 2 million people and is famous for croissants."  

**Score**: No  
**Reasoning**:  
1. Extracted claims:  
   - "Capital of France is Paris" (supported).  
   - "Population over 2 million" (supported).  
   - "Famous for croissants" (unsupported).  
2. Unsupported claims: "Famous for croissants" (not in FACTS).  
3. Conclusion: Score is "No" due to 1 hallucination.  

---
Now evaluate:  

**FACTS**:  
{context}  

**STUDENT ANSWER**:  
{answer}  

---
"""