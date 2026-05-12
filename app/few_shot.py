def get_few_shot_examples() -> str:
    return """
Example 1 (Basic Join):
User: List doctors and their appointment counts
SQL: SELECT d.name, COUNT(a.id) FROM doctors d JOIN appointments a ON d.id = a.doctor_id GROUP BY d.id;

Example 2 (CTE and Window Function):
User: Show top 3 doctors by revenue in each specialty
SQL: WITH RankedDocs AS (
    SELECT d.specialty, d.name, SUM(b.amount) as revenue,
           ROW_NUMBER() OVER(PARTITION BY d.specialty ORDER BY SUM(b.amount) DESC) as rnk
    FROM doctors d JOIN billing b ON d.id = b.doctor_id GROUP BY d.id, d.specialty, d.name
)
SELECT specialty, name, revenue FROM RankedDocs WHERE rnk <= 3;
"""
