from airflow.sdk import get_current_context

def on_task_failure(context: dict) -> None:
    dag_id = context['dag'].dag_id
    task_id = context['task'].task_id
    run_id = context['run_id']
    logical_date = context['logical_date']
    exception = context.get('exception', 'No Exception Information')


    from src.logger import get_logger
    logger = get_logger(__name__)
    logger.error(
    "TASK FAILURE ALERT | DAG: %s | Task: %s | Run: %s | Date: %s | Exception: %s",
    dag_id, task_id, run_id, logical_date, str(exception)
    )



# def slack_on_task_failure(context: dict) -> None