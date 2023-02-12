import logging
import json

import azure.durable_functions as df


def orchestrator_function(context: df.DurableOrchestrationContext):
    body = context._input
    body = json.loads(body)
    logging.info(f"Input is: {body}")

    result = yield context.call_activity('artifax-ingest', body)

    return result


main = df.Orchestrator.create(orchestrator_function)
