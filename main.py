import os
from flask import Flask, request, jsonify
from google.cloud import discoveryengine_v1 as discoveryengine

app = Flask(__name__)

# YOUR VERTEX AI SEARCH CONFIGURATION
# These are your specific details
PROJECT_ID = "964262920962"
LOCATION = "us"  # Your region
SEARCH_ENGINE_ID = "master-search-gie_1765216371286"  # Your Vertex AI app ID
SERVING_CONFIG_ID = "default_config"  # Standard default config

# You can also override these with environment variables if needed
PROJECT_ID = os.environ.get('PROJECT_ID', PROJECT_ID)
LOCATION = os.environ.get('LOCATION', LOCATION)
SEARCH_ENGINE_ID = os.environ.get('SEARCH_ENGINE_ID', SEARCH_ENGINE_ID)
SERVING_CONFIG_ID = os.environ.get('SERVING_CONFIG_ID', SERVING_CONFIG_ID)

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint - Test this first!"""
    return jsonify({
        "status": "healthy",
        "service": "Vertex AI Search API",
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "search_engine_id": SEARCH_ENGINE_ID
    }), 200

@app.route('/search', methods=['POST'])
def search():
    """
    Search endpoint for Vertex AI Search
    
    Request body example:
    {
        "query": "your search term",
        "page_size": 10  (optional, default is 10)
    }
    """
    try:
        # Get query from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        query = data.get('query', '')
        page_size = data.get('page_size', 10)  # Default to 10 results
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        # Create a client for Vertex AI Search
        client = discoveryengine.SearchServiceClient()
        
        # Build the full resource name for your search engine
        # Format: projects/{project}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/{config_id}
        serving_config = client.serving_config_path(
            project=PROJECT_ID,
            location=LOCATION,
            data_store=SEARCH_ENGINE_ID,
            serving_config=SERVING_CONFIG_ID
        )
        
        print(f"Using serving config: {serving_config}")  # For debugging in logs
        
        # Prepare the search request
        search_request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=page_size,
            # Optional: Add query expansion for better results
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            # Optional: Enable spell correction
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            )
        )
        
        # Perform the search
        response = client.search(search_request)
        
        # Format results
        results = []
        for result in response.results:
            document = result.document
            
            # Extract data from the document
            # The structure may vary based on your data source
            result_data = {
                "id": document.id,
                "name": document.name,
            }
            
            # Try to extract common fields from derived_struct_data
            if hasattr(document, 'derived_struct_data') and document.derived_struct_data:
                struct_data = document.derived_struct_data
                
                # Common fields (adjust based on your actual data structure)
                result_data["title"] = struct_data.get("title", "")
                result_data["link"] = struct_data.get("link", "")
                result_data["htmlTitle"] = struct_data.get("htmlTitle", "")
                
                # Extract snippets if available
                snippets = struct_data.get("snippets", [])
                if snippets and len(snippets) > 0:
                    result_data["snippet"] = snippets[0].get("snippet", "")
                    result_data["htmlSnippet"] = snippets[0].get("htmlSnippet", "")
            
            # Try to extract from struct_data (raw document data)
            if hasattr(document, 'struct_data') and document.struct_data:
                result_data["raw_data"] = dict(document.struct_data)
            
            results.append(result_data)
        
        # Build response
        response_data = {
            "query": query,
            "results": results,
            "total_results": len(results),
            "configuration": {
                "project_id": PROJECT_ID,
                "location": LOCATION,
                "search_engine_id": SEARCH_ENGINE_ID
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # Log the full error for debugging
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__
        }), 500

@app.route('/config', methods=['GET'])
def get_config():
    """Endpoint to check current configuration (for debugging)"""
    return jsonify({
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "search_engine_id": SEARCH_ENGINE_ID,
        "serving_config_id": SERVING_CONFIG_ID
    }), 200

if __name__ == '__main__':
    # Get port from environment variable (Cloud Run sets this)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"Starting server on port {port}")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"Search Engine ID: {SEARCH_ENGINE_ID}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
