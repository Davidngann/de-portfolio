import sys
sys.path.insert(0, "/opt/airflow")

import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="test_slack",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
)
def test_slack():
    """
    Testing the slack webhook connection.
    """
    @task
    def send_test_message() -> str:
        from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

        hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")
        hook.send(text=":white_check_mark: *Slack connection test passed!* `slack_webhook` conn is working.")
        return "Message sent successfully"

    send_test_message()


test_slack()
