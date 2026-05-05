import sys
sys.path.insert(0, "/opt/airflow")

from datetime import timedelta
from pathlib import Path
import pendulum
from airflow.sdk import dag, task
from airflow.providers.slack.notifications.slack_webhook import send_slack_webhook_notification
from airflow.providers.standard.sensors.filesystem import FileSensor

CONN_ID = "nyc_taxi_pg"
SQL_DIR = Path("/opt/airflow/sql")

# NOTIFICATION
slack_webhook_on_task_failure = send_slack_webhook_notification(
    slack_webhook_conn_id = "slack_webhook",
    text = """
:red_circle: *Task Failed* | `{{ dag.dag_id }}` | `{{ task.task_id }}`
*Date:* {{ ds }} | *Try:* {{ ti.try_number }}/{{ ti.max_tries + 1 }} | *Run:* `{{ run_id }}`
*Exception:* `{{ exception }}`
*Log:* {{ ti.log_url }}

""",
)


@dag(
    dag_id = "nyc_taxi_elt",
    schedule = "@monthly",
    start_date = pendulum.datetime(2026,2,1, tz = "UTC"),
    catchup = False,
    tags = ["nyc-taxi", "elt", "etl"],
    max_active_runs=1,
    default_args = {
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_retry_callback": slack_webhook_on_task_failure,
        "on_failure_callback": slack_webhook_on_task_failure,

    }
)
def nyc_taxi_elt():
    """
    NYC Taxi ELT/ETL pipeline.
    Pipeline path is controlled by Airflow Variable `pipeline_mode`:
      - "elt" (default): load raw -> transform in SQL
      - "etl": transform in Python -> load staging
    Both paths converge at staging_to_reporting.
    """

    # Helper
    def _get_config() -> dict:
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        from airflow.sdk import Variable

        conn = PostgresHook(CONN_ID).get_connection(CONN_ID)

        return {
        "db_host": conn.host,
        "db_port": conn.port,
        "db_name": conn.schema,
        "db_user": conn.login,
        "db_password": conn.password,
        "batch_size": int(Variable.get("batch_size", default=5000)),
        }
    
    def _run_sql(filename: str, source_file: str = None) -> None:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        sql = (SQL_DIR / filename).read_text(encoding="utf-8")
        parameters = {"source_file": source_file} if source_file else None
        PostgresHook(CONN_ID).run(sql, parameters=parameters)


    wait_for_file = FileSensor(
        task_id = "wait_for_file",
        filepath = "/opt/airflow/data/yellow_tripdata_{{ logical_date.strftime('%Y-%m') }}.parquet",
        poke_interval = 30,
        timeout=300,
        mode="poke",
        retries=0,
    )

    # Extract
    @task()
    def extract(**context) -> str:
        from src.extract import extract

        logical_date = context['logical_date']
        source_file = f"yellow_tripdata_{logical_date.strftime('%Y-%m')}.parquet"
        output_path = "/tmp/nyc_taxi_raw.parquet"

        df, _, _ = extract(source_file)
        df.to_parquet(output_path, index=False)

        return output_path
    

    # Branching
    @task.branch
    def branch() -> str:
        from airflow.sdk import Variable
        mode = Variable.get("pipeline_mode", default="elt")
        return "load_raw" if mode == "elt" else "transform"
    

    # ELT PATH
    @task
    def load_raw(parquet_path: str, **context) -> str:
        import pandas as pd
        from src.load import load

        logical_date = context['logical_date']
        source_file = f"yellow_tripdata_{logical_date.strftime('%Y-%m')}.parquet"

        df = pd.read_parquet(parquet_path)
        load(df, _get_config(), "raw", source_file)

        return "raw.yellow_trips"
    
    @task
    def raw_to_staging(upstream: str, **context) -> str:
        logical_date = context["logical_date"]
        source_file = f"yellow_tripdata_{logical_date.strftime('%Y-%m')}.parquet"
        _run_sql("raw_to_staging.sql", source_file=source_file)
        return "staging.yellow_trips"
    

    # ETL Path
    @task()
    def transform(parquet_path: str, **context) -> str:
        import pandas as pd
        from src.transform import transform
        # from src.validate import validate_dataframe

        logical_date = context["logical_date"]


        df = pd.read_parquet(parquet_path)
        df_clean = transform(df, 
                             source_year = logical_date.year,
                             source_month= logical_date.month)
        # validate_dataframe(df_clean, stage="transform")

        output_path  = "/tmp/nyc_taxi_transformed.parquet"
        df_clean.to_parquet(output_path , index=False)
        return output_path


    @task
    def load_staging(parquet_path: str, **context) -> str:
        import pandas as pd
        from src.load import load
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        logical_date = context['logical_date']
        source_file = f"yellow_tripdata_{logical_date.strftime('%Y-%m')}.parquet"

        df = pd.read_parquet(parquet_path)
        load(df, _get_config(), "staging", source_file)

        return "staging.yellow_trips"
    
    
    # Converge
    @task(trigger_rule="none_failed_min_one_success")
    def staging_to_reporting(**context) ->str:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        logical_date = context['logical_date']
        source_file = f"yellow_tripdata_{logical_date.strftime('%Y-%m')}.parquet"
        _run_sql("staging_to_reporting.sql", source_file)
        return "reporting.daily_metrics"

        
    # Wiring workflow
    # truncated = truncate_all()
    extracted = extract()
    b = branch()
    wait_for_file >> extracted >> b

    # ELT Path
    elt_loaded = load_raw(extracted)
    elt_staged = raw_to_staging(elt_loaded)

    # ETL Path
    etl_transformed = transform(extracted)
    etl_loaded = load_staging(etl_transformed)

    # Converge
    b >> [elt_loaded, etl_transformed]

    [elt_staged, etl_loaded] >> staging_to_reporting()

nyc_taxi_elt()