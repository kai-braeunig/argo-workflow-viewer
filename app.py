# Import necessary libraries from Flask and the official Kubernetes client.
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from kubernetes import client, config
import re
from datetime import datetime

# Define the namespace where Argo Workflows are installed.
ARGO_NAMESPACE = "argo"

# Initialize the Flask application.
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing to allow the frontend to call the backend.
CORS(app)

# Main route to serve the single-page HTML application.
@app.route("/")
def serve_index():
    # Serves the index.html file from the current directory.
    return send_from_directory('.', 'index.html')

# API endpoint to fetch a summary of all workflows.
@app.route("/api/workflows")
def list_workflows():
    try:
        # Load Kubernetes configuration. Handles running inside a pod or locally.
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    
    api = client.CustomObjectsApi()
    try:
        # Get all 'Workflow' custom resources from the Kubernetes API.
        wf_list = api.list_namespaced_custom_object(
            group="argoproj.io", version="v1alpha1", namespace=ARGO_NAMESPACE, plural="workflows")
        
        # Process the raw data into a clean list for the UI.
        all_workflows = [
            {
                "name": wf.get("metadata", {}).get("name"),
                "status": wf.get("status", {}).get("phase", "Pending")
            }
            for wf in wf_list.get("items", [])
        ]
        return jsonify(all_workflows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper function to convert Argo's flat node list into a nested tree.
def build_tree(nodes, parent_id):
    tree = []
    # Find all direct children of the current node.
    children_ids = nodes.get(parent_id, {}).get("children", [])
    
    for child_id in children_ids:
        node_info = nodes.get(child_id, {})
        if not node_info: continue
        
        display_name = node_info.get("displayName", child_id)
        # Filter out Argo's internal step-group nodes (e.g., "[0]") for a cleaner display.
        if re.match(r'^\[\d+\]$', display_name):
            tree.extend(build_tree(nodes, child_id))
        else:
            # Recursively build the tree for the current child node.
            tree.append({
                "name": display_name, "status": node_info.get("phase", "Unknown"),
                "type": node_info.get("type", "Unknown"), "children": build_tree(nodes, child_id)
            })
    return tree

# API endpoint to fetch the detailed hierarchy of a single workflow.
@app.route("/api/workflow/<workflow_name>")
def get_workflow_hierarchy(workflow_name):
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
        
    api = client.CustomObjectsApi()
    try:
        wf = api.get_namespaced_custom_object(
            group="argoproj.io", version="v1alpha1", name=workflow_name,
            namespace=ARGO_NAMESPACE, plural="workflows")

        if not wf or "status" not in wf or "nodes" not in wf.get("status", {}):
            return jsonify({"error": "Workflow status or nodes not available."}), 404
        
        # Extract and calculate metadata like start time and duration.
        status = wf.get("status", {})
        start_time = status.get("startedAt", "N/A")
        end_time = status.get("finishedAt", None)
        duration = "In Progress"
        if end_time:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            duration = str(end_dt - start_dt)

        # Build the node hierarchy.
        root_node_id = wf["metadata"]["name"]
        all_nodes = wf["status"]["nodes"]
        hierarchy = build_tree(all_nodes, root_node_id)
        
        # Return all relevant data to the frontend.
        return jsonify({
            "startTime": start_time,
            "duration": duration,
            "nodes": hierarchy
        })
    except client.ApiException as e:
        return jsonify({"error": f"Kubernetes API error: {e.reason}"}), 500
    except Exception as e:
        return jsonify({"error": "An internal server error occurred."}), 500

# Main entry point to run the Flask development server.
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)