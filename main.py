import os
from flask import Flask, request, jsonify
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core import client_options as client_options_lib

app = Flask(__name__)

PROJECT_ID = "964262920962"
LOCATION = "us"
# List all possible ID variations
POSSIBLE_ENGINE_IDS = [
    "master-search-gie",
    "master_search_gie", 
    "master-search-gie_1765216371286",
    "master_search_gie_1765216371286"
]
SERVING_CONFIG_ID = "default_config"
API_ENDPOINT = "us-discoveryengine.googleapis.com"

# Override with environment variables
PROJECT_ID = os.environ.get('PROJECT_ID', PROJECT_ID)
LOCATION = os.environ.get('LOCATION', LOCATION)
SERVING_CONFIG_ID = os.environ.get('SERVING_CONFIG_ID', SERVING_CONFIG_ID)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Vertex AI Search API",
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "possible_engine_ids": POSSIBLE_ENGINE_IDS,
        "api_endpoint": API_ENDPOINT
    }), 200

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        query = data.get('query', '')
        page_size = data.get('page_size', 10)
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        client_options = client_options_lib.ClientOptions(api_endpoint=API_ENDPOINT)
        client = discoveryengine.SearchServiceClient(client_options=client_options)
        
        # Try all combinations of engine IDs and path types
        attempts = []
        last_error = None
        successful_config = None
        
        for engine_id in POSSIBLE_ENGINE_IDS:
            # Try as engine
            path = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{engine_id}/servingConfigs/{SERVING_CONFIG_ID}"
            attempts.append(path)
            
            try:
                print(f"Trying engine path: {path}")
                search_request = discoveryengine.SearchRequest(
                    serving_config=path,
                    query=query,
                    page_size=page_size
                )
                response = client.search(search_request)
                successful_config = {"path": path, "engine_id": engine_id, "type": "engine"}
                print(f"✅ SUCCESS with: {path}")
                break
            except Exception as e:
                print(f"❌ Failed: {path} - {str(e)[:100]}")
                last_error = e
            
            # Try as dataStore
            path = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{engine_id}/servingConfigs/{SERVING_CONFIG_ID}"
            attempts.append(path)
            
            try:
                print(f"Trying dataStore path: {path}")
                search_request = discoveryengine.SearchRequest(
                    serving_config=path,
                    query=query,
                    page_size=page_size
                )
                response = client.search(search_request)
                successful_config = {"path": path, "engine_id": engine_id, "type": "dataStore"}
                print(f"✅ SUCCESS with: {path}")
                break
            except Exception as e:
                print(f"❌ Failed: {path} - {str(e)[:100]}")
                last_error = e
        
        if successful_config is None:
            return jsonify({
                "error": "Could not find valid engine/dataStore ID",
                "last_error": str(last_error),
                "tried_paths": attempts
            }), 404
        
        # Format results
        results = []
        for result in response.results:
            document = result.document
            result_data = {"id": document.id, "name": document.name}
            
            if hasattr(document, 'derived_struct_data') and document.derived_struct_data:
                struct_data = document.derived_struct_data
                result_data["title"] = struct_data.get("title", "")
                result_data["link"] = struct_data.get("link", "")
                
                snippets = struct_data.get("snippets", [])
                if snippets:
                    result_data["snippet"] = snippets[0].get("snippet", "")
            
            if hasattr(document, 'struct_data') and document.struct_data:
                result_data["raw_data"] = dict(document.struct_data)
            
            results.append(result_data)
        
        return jsonify({
            "query": query,
            "results": results,
            "total_results": len(results),
            "successful_configuration": successful_config
        }), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__
        }), 500

@app.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "possible_engine_ids": POSSIBLE_ENGINE_IDS,
        "serving_config_id": SERVING_CONFIG_ID,
        "api_endpoint": API_ENDPOINT
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
