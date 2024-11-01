import aiohttp
import asyncio
import json
import warnings

# Suppress SSL warnings (use with caution; verify SSL in production)
warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made")

# Corrected API endpoint for the server
server_endpoint = 'panelurl'

# Session storage for authentication
session = None

async def authenticate():
    global session
    try:
        url = f"{server_endpoint}/login"
        username = ''
        password = ''

        if not username or not password:
            print("Username or password not set. Please check your credentials.")
            return None

        payload = {'username': username, 'password': password}
        session = aiohttp.ClientSession()
        async with session.post(url, json=payload, ssl=False) as response:
            if response.status == 200:
                response_json = await response.json()
                if response_json.get('success'):
                    print("Authenticated with supportzoom server.")
                    return session
                else:
                    print(f"Failed to authenticate: {response_json.get('msg')}")
                    await session.close()
                    return None
            else:
                print(f"Failed to authenticate: {response.status} - {response.reason}")
                await session.close()
                return None
    except Exception as e:
        print(f"Error in authenticate: {e}")
        return None

async def get_session():
    global session
    if session and not session.closed:
        return session
    else:
        if session:
            await session.close()
        return await authenticate()

async def make_authenticated_request(method, endpoint, payload=None):
    session = await get_session()
    if not session:
        print("Authentication failed. Exiting.")
        return None
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = f"{server_endpoint}{endpoint}"
    try:
        if method == 'GET':
            async with session.get(url, headers=headers, ssl=False) as response:
                return await response.json()
        elif method == 'POST':
            async with session.post(url, headers=headers, json=payload, ssl=False) as response:
                return await response.json()
    except Exception as e:
        print(f"Request error: {e}")
        return None

async def get_inbounds():
    try:
        endpoint = "/panel/api/inbounds/list"
        response_data = await make_authenticated_request('GET', endpoint)
        if response_data and response_data.get('success'):
            return response_data.get('obj', [])
        else:
            print(f"Failed to fetch inbounds: {response_data.get('msg', 'Unknown error') if response_data else 'No response data'}")
            return []
    except Exception as e:
        print(f"An error occurred while fetching inbounds: {e}")
        return []

async def update_inbound(inbound_id, inbound_payload):
    endpoint = f"/panel/api/inbounds/update/{inbound_id}"
    response_data = await make_authenticated_request('POST', endpoint, inbound_payload)
    if response_data and response_data.get('success'):
        print(f"Inbound '{inbound_payload['remark']}' updated successfully.")
        return True
    else:
        print(f"Failed to update inbound: {response_data.get('msg', 'Unknown error')}")
        return False

async def enable_sniffing_on_all_inbounds():
    try:
        inbounds = await get_inbounds()
        if not inbounds:
            print("No inbounds found.")
            return

        for inbound in inbounds:
            inbound_id = inbound.get('id')
            inbound_details = await make_authenticated_request('GET', f"/panel/api/inbounds/get/{inbound_id}")
            if not inbound_details or not inbound_details.get('success'):
                print(f"Failed to fetch inbound details for inbound {inbound_id}")
                continue

            # Copy current inbound settings to avoid overwriting
            inbound_payload = inbound_details['obj']

            # Convert the sniffing configuration to a JSON-encoded string
            sniffing_config = {
                "enabled": True,
                "destOverride": ["tls"],
                "metadataOnly": False,
                "routeOnly": False
            }
            inbound_payload['sniffing'] = json.dumps(sniffing_config)

            # Send the update request
            success = await update_inbound(inbound_id, inbound_payload)
            if success:
                print(f"Sniffing enabled for inbound '{inbound_payload['remark']}'.")
    except Exception as e:
        print(f"An error occurred while enabling sniffing on all inbounds: {e}")

    # Ensure to close the session properly
    if session:
        await session.close()

# Run the main function to enable sniffing on all inbounds
if __name__ == "__main__":
    asyncio.run(enable_sniffing_on_all_inbounds())
