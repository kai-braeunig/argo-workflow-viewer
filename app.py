from flask import Flask, jsonify
from flask_cors import CORS
from kubernetes import client, config

# The Kubernetes namespace where Argo Workflows are deployed.
ARGO_NAMESPACE = "argo"

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing for the application.
CORS(app)

def build_tree(nodes, parent_id):
    """Recursively builds a hierarchical tree from a flat dictionary of Argo nodes."""
    tree = []
    # Identify all direct children of the given parent node.
    children_ids = nodes.get(parent_id, {}).get("children", [])
    
    for child_id in children_ids:
        node_info = nodes.get(child_id, {})
        if not node_info:
            continue
        
        # Construct a simplified node object for the frontend.
        node_obj = {
            "name": node_info.get("displayName", child_id),
            "status": node_info.get("phase", "Unknown"),
            "type": node_info.get("type", "Unknown"),
            "children": build_tree(nodes, child_id) # Recursively build the sub-tree.
        }
        tree.append(node_obj)
    return tree

@app.route("/api/workflow/<workflow_name>")
def get_workflow_hierarchy(workflow_name):
    """API endpoint to fetch a workflow and return its node hierarchy."""
    try:
        # Attempt to load the in-cluster configuration for a Kubernetes pod environment.
        config.load_incluster_config()
    except config.ConfigException:
        # If not in a cluster, fall back to the local kubeconfig file.
        config.load_kube_config()
        
    api = client.CustomObjectsApi()

    try:
        # Fetch the Argo Workflow Custom Resource from the Kubernetes API.
        wf = api.get_namespaced_custom_object(
            group="argoproj.io",
            version="v1alpha1",
            name=workflow_name,
            namespace=ARGO_NAMESPACE,
            plural="workflows",
        )

        if not wf or "status" not in wf or "nodes" not in wf:
            return jsonify({"error": "Workflow exists but has no status or nodes to display."}), 404

        # The root node ID for the hierarchy is the workflow's name.
        root_node_id = wf["metadata"]["name"]
        all_nodes = wf["status"]["nodes"]
        
        hierarchy = build_tree(all_nodes, root_node_id)
        
        return jsonify(hierarchy)

    except client.ApiException as e:
        if e.status == 404:
            return jsonify({"error": f"Workflow '{workflow_name}' not found in namespace '{ARGO_NAMESPACE}'."}), 404
        return jsonify({"error": f"Kubernetes API error: {e.reason}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    # Run the Flask server, making it accessible from any network interface.
    app.run(host='0.0.0.0', port=5000)
