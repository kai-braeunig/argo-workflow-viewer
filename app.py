from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from kubernetes import client, config
import re

ARGO_NAMESPACE = "argo"
app = Flask(__name__)
CORS(app)

@app.route("/")
def serve_index():
    """Serves the main HTML page."""
    return send_from_directory('.', 'index.html')

@app.route("/api/workflows")
def list_workflows():
    """API endpoint to list all workflows, used for the search/clickable list."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    
    api = client.CustomObjectsApi()
    try:
        wf_list = api.list_namespaced_custom_object(
            group="argoproj.io", version="v1alpha1", namespace=ARGO_NAMESPACE, plural="workflows")
        
        # Extract relevant info from each workflow object
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

def build_tree(nodes, parent_id):
    """Recursively builds the node hierarchy for the visualization."""
    tree = []
    children_ids = nodes.get(parent_id, {}).get("children", [])
    
    for child_id in children_ids:
        node_info = nodes.get(child_id, {})
        if not node_info: continue
        
        display_name = node_info.get("displayName", child_id)
        # Hides intermediate step groups like "[0]" for a cleaner UI
        if re.match(r'^\[\d+\]$', display_name):
            tree.extend(build_tree(nodes, child_id))
        else:
            tree.append({
                "name": display_name, "status": node_info.get("phase", "Unknown"),
                "type": node_info.get("type", "Unknown"), "children": build_tree(nodes, child_id)
            })
    return tree

@app.route("/api/workflow/<workflow_name>")
def get_workflow_hierarchy(workflow_name):
    """API endpoint to get the detailed node structure of a single workflow."""
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

        root_node_id = wf["metadata"]["name"]
        all_nodes = wf["status"]["nodes"]
        hierarchy = build_tree(all_nodes, root_node_id)
        return jsonify(hierarchy)
    except client.ApiException as e:
        return jsonify({"error": f"Kubernetes API error: {e.reason}"}), 500
    except Exception as e:
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)