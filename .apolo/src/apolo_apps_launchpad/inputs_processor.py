from apolo_app_types.helm.apps.launchpad import (
    LaunchpadChartValueProcessor,
)


class LaunchpadInputsProcessor(LaunchpadChartValueProcessor):
    # Most apps can simply inherit without overrides
    # Add custom logic here if needed to transform user inputs to Helm values
    pass
