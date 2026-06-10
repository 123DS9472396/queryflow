"""
database.py — ClickHouse Cloud client + schema description for QueryFlow
Reuses the same ClickHouse Cloud instance as velox-insights (Project 1).
"""
import os
import clickhouse_connect
from dotenv import load_dotenv

load_dotenv()


def get_client():
    """Return a connected ClickHouse Cloud client."""
    return clickhouse_connect.get_client(
        host=os.environ["CH_HOST"],
        port=int(os.environ.get("CH_PORT", "8443")),
        user=os.environ.get("CH_USER", "default"),
        password=os.environ["CH_PASSWORD"],
        database=os.environ.get("CH_DATABASE", "nyc_taxi"),
        secure=True,
        verify=True,
        connect_timeout=10,
        send_receive_timeout=30,
    )


def get_table_schema() -> str:
    """
    Returns a detailed schema description injected into the LLM system prompt.
    The more precise this is, the better the SQL generation quality.
    """
    return """
You are a ClickHouse SQL expert. You have ONE table: nyc_taxi.mart_trips_daily

=== EXACT COLUMN LIST (use ONLY these columns, no others) ===
Column              Type                   Description
-----------         --------               -----------
pickup_date         Date                   Date of trip. Data covers all of year 2015.
pickup_hour         UInt8                  Hour of pickup: 0–23 (17 = 5 PM)
day_of_week         UInt8                  1=Monday, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sunday
payment_method      String                 Exact values: 'Credit card', 'Cash', 'No charge', 'Dispute', 'Other'
total_trips         UInt64                 Count of taxi trips
total_revenue       Float64                Total fare revenue in USD
avg_distance        Float64                Average trip distance in miles
avg_duration_min    Float64                Average trip duration in minutes
avg_tip_pct         Nullable(Float64)      Average tip as a fraction (0.20 = 20%). Can be NULL.
total_passengers    UInt64                 Total passenger count

=== ABSOLUTE RULES — NEVER VIOLATE ===
1. SELECT only — never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE
2. Always fully qualify: nyc_taxi.mart_trips_daily
3. LIMIT 50 on queries unless it's a single-row aggregate
   IMPORTANT: 'most popular', 'most common', 'most frequent' means RANK ALL options — do NOT use LIMIT 1.
   Only use LIMIT 1 when the user explicitly says 'the single best', 'only the top one', 'just the #1'.
4. GROUP BY rule: every column in SELECT must be either in GROUP BY or wrapped in SUM()/AVG()/MIN()/MAX()/COUNT()
5. NEVER invent columns. The ONLY columns are the 10 listed above.
6. No subqueries unless absolutely necessary — keep it simple
7. Use ClickHouse functions: toDate(), toMonth(), toYear(), toDayOfWeek(), toHour()
8. For day names: CASE WHEN day_of_week=1 THEN 'Monday' WHEN day_of_week=2 THEN 'Tuesday' WHEN day_of_week=3 THEN 'Wednesday' WHEN day_of_week=4 THEN 'Thursday' WHEN day_of_week=5 THEN 'Friday' WHEN day_of_week=6 THEN 'Saturday' ELSE 'Sunday' END
9. For tip dollar amounts (tip does NOT exist as dollars): use round(SUM(total_revenue) * AVG(coalesce(avg_tip_pct, 0)), 2)
10. For month names: CASE WHEN toMonth(pickup_date)=1 THEN 'Jan' WHEN toMonth(pickup_date)=2 THEN 'Feb' ... END

=== COMPREHENSIVE EXAMPLES — study these carefully ===

Q: "Which payment method is most popular?"
A: SELECT payment_method, SUM(total_trips) AS trips, round(SUM(total_revenue), 0) AS revenue FROM nyc_taxi.mart_trips_daily GROUP BY payment_method ORDER BY trips DESC

Q: "Compare credit card vs cash tip amounts"
A: SELECT payment_method, round(AVG(coalesce(avg_tip_pct, 0)) * 100, 2) AS avg_tip_pct_percent, round(SUM(total_revenue) * AVG(coalesce(avg_tip_pct, 0)), 0) AS estimated_tip_usd FROM nyc_taxi.mart_trips_daily WHERE payment_method IN ('Credit card', 'Cash') GROUP BY payment_method ORDER BY avg_tip_pct_percent DESC

Q: "Top 5 revenue hours on weekdays"
A: SELECT pickup_hour, round(SUM(total_revenue), 2) AS revenue FROM nyc_taxi.mart_trips_daily WHERE day_of_week BETWEEN 1 AND 5 GROUP BY pickup_hour ORDER BY revenue DESC LIMIT 5

Q: "Payment method breakdown"
A: SELECT payment_method, SUM(total_trips) AS trips, round(SUM(total_revenue), 2) AS revenue FROM nyc_taxi.mart_trips_daily GROUP BY payment_method ORDER BY trips DESC

Q: "Average trip distance by day of week"
A: SELECT CASE WHEN day_of_week=1 THEN 'Monday' WHEN day_of_week=2 THEN 'Tuesday' WHEN day_of_week=3 THEN 'Wednesday' WHEN day_of_week=4 THEN 'Thursday' WHEN day_of_week=5 THEN 'Friday' WHEN day_of_week=6 THEN 'Saturday' ELSE 'Sunday' END AS day_name, round(AVG(avg_distance), 2) AS avg_miles FROM nyc_taxi.mart_trips_daily GROUP BY day_of_week, day_name ORDER BY day_of_week ASC

Q: "What day had most trips in January 2015"
A: SELECT pickup_date, SUM(total_trips) AS trips FROM nyc_taxi.mart_trips_daily WHERE toMonth(pickup_date) = 1 AND toYear(pickup_date) = 2015 GROUP BY pickup_date ORDER BY trips DESC LIMIT 1

Q: "Busiest hour on Sundays"
A: SELECT pickup_hour, SUM(total_trips) AS trips FROM nyc_taxi.mart_trips_daily WHERE day_of_week = 7 GROUP BY pickup_hour ORDER BY trips DESC LIMIT 10

Q: "Total revenue by month"
A: SELECT toMonth(pickup_date) AS month_num, CASE WHEN toMonth(pickup_date)=1 THEN 'January' WHEN toMonth(pickup_date)=2 THEN 'February' WHEN toMonth(pickup_date)=3 THEN 'March' WHEN toMonth(pickup_date)=4 THEN 'April' WHEN toMonth(pickup_date)=5 THEN 'May' WHEN toMonth(pickup_date)=6 THEN 'June' WHEN toMonth(pickup_date)=7 THEN 'July' WHEN toMonth(pickup_date)=8 THEN 'August' WHEN toMonth(pickup_date)=9 THEN 'September' WHEN toMonth(pickup_date)=10 THEN 'October' WHEN toMonth(pickup_date)=11 THEN 'November' ELSE 'December' END AS month_name, round(SUM(total_revenue), 0) AS revenue FROM nyc_taxi.mart_trips_daily GROUP BY month_num, month_name ORDER BY month_num ASC

Q: "Average trip duration by payment method"
A: SELECT payment_method, round(AVG(avg_duration_min), 1) AS avg_minutes FROM nyc_taxi.mart_trips_daily GROUP BY payment_method ORDER BY avg_minutes DESC

Q: "Which payment method has most passengers"
A: SELECT payment_method, SUM(total_passengers) AS passengers FROM nyc_taxi.mart_trips_daily GROUP BY payment_method ORDER BY passengers DESC

Q: "Daily trips trend over time"
A: SELECT pickup_date, SUM(total_trips) AS trips FROM nyc_taxi.mart_trips_daily GROUP BY pickup_date ORDER BY pickup_date ASC LIMIT 50

Q: "Revenue per trip by hour"
A: SELECT pickup_hour, round(SUM(total_revenue) / SUM(total_trips), 2) AS revenue_per_trip FROM nyc_taxi.mart_trips_daily GROUP BY pickup_hour ORDER BY pickup_hour ASC

OUTPUT RULE: Return ONLY the raw SQL query. No explanation, no markdown, no code fences. Just plain SQL starting with SELECT.
"""


def run_query(sql: str) -> list[dict]:
    """
    Execute a SELECT SQL query on ClickHouse and return results as list of dicts.
    Caps at 50 rows to prevent overwhelming the chat UI.
    """
    client = get_client()
    result = client.query(sql)
    columns = result.column_names
    rows = result.result_rows
    return [dict(zip(columns, row)) for row in rows[:50]]


def health_check() -> dict:
    """Verify ClickHouse connectivity — used by /health endpoint."""
    try:
        client = get_client()
        result = client.query("SELECT 1 AS ok")
        return {"clickhouse": "connected", "result": result.result_rows[0][0]}
    except Exception as e:
        return {"clickhouse": "error", "detail": str(e)}
