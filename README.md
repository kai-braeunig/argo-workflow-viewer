# Argo Workflow Viewer

A functional, visually appealing, tree-based web application to display the hierarchical structure of Argo Workflows in real-time. This project was developed entirely within GitHub Codespaces.

## The Problem
The standard Argo Workflows UI is powerful, but visualizing deep or complex hierarchies can be cumbersome. This tool provides a simple, clean, and interactive alternative.

## Tech Stack
- **Backend**: Python (Flask)
- **Frontend**: HTML, CSS, JavaScript (no frameworks)
- **Environment**: GitHub Codespaces
- **Orchestration**: Kubernetes (Minikube) & Argo Workflows

## How to Run
1.  Open this repository in a GitHub Codespace.
2.  The environment will build automatically based on the `.devcontainer` configuration.
3.  The `postCreateCommand` will set up Minikube and Argo Workflows.
4.  Run the application with `python app.py`.