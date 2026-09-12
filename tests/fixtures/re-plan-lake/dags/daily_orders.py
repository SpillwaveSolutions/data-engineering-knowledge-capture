from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(dag_id="lumenfield_daily_orders", start_date=datetime(2026, 1, 1), schedule="@daily") as dag:
    BashOperator(task_id="dbt_run", bash_command="dbt run --select orders")
