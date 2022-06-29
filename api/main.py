from azure.cosmos import CosmosClient, exceptions as CosmosExp
from flask import Flask, request
from logging import getLogger
from token_credential import ClientAssertionCredential
from re import match
from os import getenv
from uuid import uuid4
from jwt import PyJWKClient, decode, exceptions as jwtExcp

# Scope required by API
SCOPE_REQUIRED_BY_API = 'VaccineID.Admin'

# Init as Flask app
global app
app = Flask(__name__)

@app.route('/patient', methods=['GET', 'POST'])
def patient():
    """Manage patient profiles"""
    # Get patient
    if request.method == 'GET':
        app.logger.info('getting patient...')

        # Validate JWT signature and required scope
        try:
            headers = request.headers
            token = headers.get('Authorization').split()[1]
            tokenValid = valid_jwt(token)

            if tokenValid:
                # JWT has required scope
                # Ensure id is in request params
                if 'id' in request.args:
                    id = request.args.get('id')
                    # Ensure id is valid UUID
                    uuidRegEx = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$"
                    if not match(uuidRegEx, id):
                        return 'Bad Request - Invalid ID', 400

                    # Find patient in db
                    try:
                        container = 'patients'
                        cosmosClient = db_client(container)
                        patient = cosmosClient.read_item(id, partition_key=id)
                        return {'id': patient['id'], 'name': patient['name'].title(),
                            'surname': patient['surname'].title(), 'dob': patient['dob'],
                                'immunizations': patient['immunizations']}

                    # Patient not in db error
                    except CosmosExp.CosmosResourceNotFoundError:
                        app.logger.info(f'patient ({id}) not found')
                        return 'Patient Not Found', 404

                    # Catch all other exceptions
                    except Exception as e:
                        app.logger.error(f'error getting patient from db - {e}')
                        return 'Internal Server Error', 500

                # Request missing id param
                else:
                    return 'Bad Request - Missing id', 400
    
            # Invalid/expired access token
            else:
                return 'Forbidden', 403

        # Malformed/Missing auth
        except:
            return 'Not Authorized', 401

    # Create new patient profile
    elif request.method == 'POST':
        app.logger.info('creating patient profile...')

        # Validate JWT signature and required scope
        try:
            headers = request.headers
            token = headers.get('Authorization').split()[1]
            tokenValid = valid_jwt(token)
            
            if tokenValid:
                # JWT has required scope
                # Init params from request body
                try:
                    patient = request.get_json()
                    # Ensure all params sent in request
                    params = ['name', 'surname', 'dob']
                    for param in params:
                        if param not in patient:
                            return f'Bad Request - Missing Required Parameter - {param}', 400
                    else:
                        name = patient['name']
                        surname = patient['surname']
                        dob = patient['dob']

                        # Ensure dob format is year-month-day
                        dateRegEx = "^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"
                        if not match(dateRegEx, dob):
                            return 'Bad Request - Invalid Date', 400

                # Bad request params
                except:
                    return 'Bad Request - Malformed/Missing Parameters', 400
                
                # Check if patient in db
                container = 'patients'
                cosmosClient = db_client(container)
                for patient in cosmosClient.query_items(
                    query=f'SELECT * FROM {container} patient WHERE \
                        patient.name="{name}" AND patient.surname="{surname}" \
                            AND patient.dob="{dob}"',
                    enable_cross_partition_query=True):
                        return 'Patient Profile Exists'
                else:
                    # Create new patient profile and return id
                    try: 
                        id = str(uuid4())
                        cosmosClient.upsert_item({
                                'id': id,
                                'name': name.upper(),
                                'surname': surname.upper(),
                                'dob': dob,
                                'immunizations': []
                            }
                        )
                        return {'id': id}, 201

                    # Catch all exceptions
                    except Exception as e:
                        app.logger.error(f'error creating patient - {e}')
                        return 'Internal Server Error', 500

            # Invalid/expired access token
            else:
                return 'Forbidden', 403

        # Malformed/Missing access token
        except:
            return 'Not Authorized', 401

@app.route('/patient/search', methods=['POST'])
def patient_search():
    """Search for patients in DB"""
    # Validate JWT signature and required scope
    try:
        headers = request.headers
        token = headers.get('Authorization').split()[1]
        tokenValid = valid_jwt(token)
        
        if tokenValid:
            # JWT has required scope
            # Init params from request body
            try:
                searchBody = request.get_json()
                # Ensure required params sent in request
                params = ['surname', 'dob']
                for param in params:
                    if param not in searchBody:
                        return f'Bad Request - Missing Required Parameter - {param}', 400
                else:
                    surname = searchBody['surname'].upper()
                    dob = searchBody['dob']  
                
                    # Ensure dob format is year-month-day
                    dateRegEx = "^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"
                    if not match(dateRegEx, dob):
                        return 'Bad Request - Invalid Date', 400

            except:
                return 'Bad Request - Malformed/Missing Parameters', 400
            
            # Query db
            patients = []
            container = 'patients'
            cosmosClient = db_client(container)
            for patient in cosmosClient.query_items(
                query=f'SELECT * FROM {container} patient WHERE patient.surname="{surname}" \
                    AND patient.dob="{dob}"',
                enable_cross_partition_query=True):
                    patients.append({
                        'id': patient['id'], 'name': patient['name'].title(),
                            'surname': patient['surname'].title(), 'dob': patient['dob']
                        })
            return {'patients': patients}
                    
        # Invalid/expired access token
        else:
            return 'Forbidden', 403

    # Malformed/Missing access token
    except:
        return 'Not Authorized', 401

@app.route('/patient/<id>/record', methods=['POST'])
def patient_record(id):
    """Add patient immunization record"""
    app.logger.info(f'adding record for patient ({id})...')

    # Validate JWT signature and required scope
    try:
        headers = request.headers
        token = headers.get('Authorization').split()[1]
        tokenValid = valid_jwt(token)

        if tokenValid:
            # Verify api scope matches
            # Ensure id is valid UUID
            uuidRegEx = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$"
            if not match(uuidRegEx, id):
                return 'Bad Request - Invalid ID', 400

            # Init params from request body
            try:
                record = request.get_json()
                # Ensure all params sent in request
                paramsRequired = ['name', 'manufacturer', 'provider', 'date', 'lot']
                for param in paramsRequired:
                    if param not in record:
                        return f'Bad Request - Missing Required Parameter - {param}', 400

                # Ensure date format is year-month-day
                dateRegEx = "^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"
                if not match(dateRegEx, record['date']):
                    return 'Bad Request - Invalid Date', 400
            
            except:
                return 'Bad Request - Malformed/Missing Parameters', 400

            # Find patient in db
            try:
                container = 'patients'
                cosmosClient = db_client(container)                    
                patient = cosmosClient.read_item(id, partition_key=id)
                recordData = {'name': record['name'], 'manufacturer': record['manufacturer'], 
                    'provider': record['provider'], 'date': record['date'], 'lot': record['lot']}
                patient['immunizations'].append(recordData)
                cosmosClient.upsert_item(patient)
                return {'id': id}, 201

            # Patient not in db error
            except CosmosExp.CosmosResourceNotFoundError:
                app.logger.info(f'patient ({id}) not found')
                return 'Not Found', 404

            # Catch all other exceptions
            except Exception as e:
                app.logger.error(f'error getting patient from db - {e}')
                return 'Error', 500

        # Invalid/expired access token
        else:
            return 'Forbidden', 403

    # Malformed/Missing access token
    except:
        return 'Not Authorized', 401

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Ensure app can init db client
    try:
        container = 'patients'
        db_client(container)
        return {'status': 'online'}
    except:
        return {'status': 'error'}, 500

def db_client(containerName):
    """Init Cosmos DB client"""
    # Init params from environment
    azureClientId = getenv('AZURE_CLIENT_ID', '')
    azureTenantId = getenv('AZURE_TENANT_ID', '')
    azureAuthorityHost = getenv('AZURE_AUTHORITY_HOST', '')
    azureFederatedTokenFile = getenv('AZURE_FEDERATED_TOKEN_FILE', '')
    cosmosURL = getenv('COSMOS_URL', '')
    databaseName = getenv('COSMOS_DB', '')

    # Implement custom MSAL client assertion for workload identity federation
    # Assert K8s access token to get Azure resource access token
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/workload-identity-federation
    tokenCredential = ClientAssertionCredential(azureClientId, azureTenantId,
        azureAuthorityHost, azureFederatedTokenFile)

    # Init and return Cosmos client
    client = CosmosClient(cosmosURL, tokenCredential)
    database = client.get_database_client(databaseName)
    container = database.get_container_client(containerName)
    return container

def valid_jwt(token):
    """Validate JWT"""
    # Init params from environment
    tenantId = getenv('TENANT_ID', '')
    jwtAud = getenv('JWT_AUD', '')
    keysUrl = f"https://login.microsoftonline.com/{tenantId}/discovery/v2.0/keys"
    jwtIss = f"https://login.microsoftonline.com/{tenantId}/v2.0"
    jwksClient = PyJWKClient(keysUrl)
    signingKey = jwksClient.get_signing_key_from_jwt(token)

    # Decode JWT and verify required scope in token
    try:
        decodeJwt = decode(token, signingKey.key, algorithms=["RS256"], audience=jwtAud, issuer=jwtIss,
            options={"require": ["aud", "exp", "iss", "scp"], "verify_exp": True, "verify_iat": True, 
                "verify_nbf": True, "verify_iss": True, "verify_aud": True })
        if decodeJwt:
            if decodeJwt['scp'] == SCOPE_REQUIRED_BY_API:
                app.logger.info('got valid jwt and scope match')
                return True
    except jwtExcp as e:
        app.logger.info(f'jwt validation error - {e}')
        return False

if __name__ != '__main__':
    # Set Gunicorn as log handler
    gunicornLogger = getLogger('gunicorn.error')
    app.logger.handlers = gunicornLogger.handlers
    app.logger.setLevel(gunicornLogger.level)