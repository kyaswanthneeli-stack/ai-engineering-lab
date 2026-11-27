# RepoPilot v2.3.0 release candidate

This candidate adds a Docker-based web interface for the supervised calculator
repair demonstration. The web container only dispatches a fixed public fixture
to the project's GitHub Actions workflow. The workflow uses local Ollama and
runs the existing restricted verification sequence. Operator authorization is
required to start repairs.

The comparable SWE-bench Lite baseline remains 1/12 resolved. Before publishing
a stable tag, verify the deployed Space's health and one real browser-initiated
job through successful GitHub Actions verification. Use the Space's job report
and matching GitHub artifact as evidence.
