import json
import pandas as pd
from typing import Optional
from app.llm.factory import get_client

def generate_chart_code(df: pd.DataFrame, question: str, provider: str = "local") -> Optional[str]:
    """
    Given a DataFrame schema and the user's intent, generates Python Plotly code.
    Assumes standard imports `import plotly.express as px` and `import plotly.graph_objects as go`.
    Assumes `df` is the available variable containing the pandas DataFrame.
    Returns the string representing the code to assign the chart to a variable named `fig`.
    """
    if df.empty or len(df.columns) < 2:
        return None # Can't generate meaningful visualizations for scalar or empty data

    schema_str = "\\n".join([f"- {col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)])
    
    system = (
        "You are a Data Visualization assistant. "
        "The user will provide a dataset schema and their original question. "
        "Your task is to generate Python code using `plotly.express` (as px) to visualize the data in a way that answers the question optimally. "
        "RULES:\\n"
        "1. Assume the dataset is already loaded in a variable named `df`.\\n"
        "2. Do NOT write `pd.read_csv()` or define `df`.\\n"
        "3. Assign the final plotly figure to a variable named `fig`.\\n"
        "4. Output ONLY the raw Python code. Do not use Markdown code blocks like ```python. Just the code strings.\\n"
        "5. If you cannot visualize it or it doesn't make sense, return exactly 'NONE'."
    )
    
    user_msg = f"User Question: {question}\\n\\nDataFrame Schema:\\n{schema_str}"

    client = get_client(provider)
    code = client.generate_text(system=system, user=user_msg).strip()
    
    if code == "NONE" or not code:
        return None
        
    # Clean up markdown formatting if the LLM leaked it despite instructions
    if code.startswith("```"):
        code = "\\n".join(code.split("\\n")[1:])
        if code.endswith("```"):
            code = code[:-3]
            
    return code
