import pandas as pd
import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeBetween
)
from src.logger import get_logger
from src.exceptions import TransformationError

logger = get_logger(__name__)

def validate_dataframe(df: pd.DataFrame, stage: str = "transform") -> None:
    """
    Run a Great Expectations suite against a dataframe.
    Raises TransformationError if any expectation fails.
    
    stage: label for logging: "extract" or "transform"
    """

    context = gx.get_context(mode="ephemeral" )

    # Define the data source
    data_source = context.data_sources.add_pandas("pandas_source")
    data_asset = data_source.add_dataframe_asset("dataframe_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("whole_dataframe")

    # Define expectations suite
    suite = context.suites.add(
        gx.ExpectationSuite(name="taxi_pipeline_suite")
    )
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="fare_amount"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="trip_distance"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="pickup_zone_id"))
    suite.add_expectation(ExpectColumnValuesToBeBetween(
        column="fare_amount", min_value=0, strict_min=True
    ))
    suite.add_expectation(ExpectColumnValuesToBeBetween(
        column="trip_distance", min_value=0, strict_min=True
    ))
    suite.add_expectation(ExpectColumnValuesToBeBetween(
        column="trip_duration_minutes", min_value=0, max_value=1440, strict_min=True
    ))


    # Define connection between data source and test
    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="taxi_validation",
            data=batch_definition,
            suite=suite
        )
    )

    # Run validator
    logger.info(f"GE validation is starting with {len(suite.expectations)} expectations")
    results = validation_definition.run(batch_parameters = {"dataframe": df})
    
    if not results["success"]:
        failed = [
            r["expectation_config"]["type"]
            for r in results["results"]
            if not r["success"]
        ]

        logger.error(f"GE validation failed at {stage} stage | Failed: {failed}")
        raise TransformationError(
            f"Data quality check failed at {stage} stage: {failed}"
        )
                        
    logger.info(f"GE validation passed at {stage} stage | {len(results['results'])} expectations checked")